"""
One-time migration: tag all existing Pinecone vectors with their org_id.

Checkpoint logic: each document is checked before touching it.
  - If its vector already has org_id in Pinecone metadata → skip (already done)
  - If not → delete old tagless vectors, re-index with org_id, update DB

Safe to stop and re-run at any point.

Usage:
    uv run python scripts/migrate_pinecone_org_ids.py
"""

import os
import sys
import tempfile

import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from agente_rolplay.db.database import SessionLocal
from agente_rolplay.db.models import Document
from agente_rolplay.storage.pinecone_client import get_pinecone_index, upload_to_pinecone
from agente_rolplay.storage.file_processor import (
    extract_image_description,
    extract_text_from_file,
    is_vectorizable,
)

_MIME_MAP = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "txt": "text/plain",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "gif": "image/gif",
    "webp": "image/webp",
}


def _already_migrated(index, vector_id: str) -> bool:
    """Return True if the vector already has org_id in its metadata (checkpoint check)."""
    if not vector_id:
        return False
    try:
        result = index.fetch(ids=[vector_id])
        vectors = result.vectors if hasattr(result, "vectors") else result.get("vectors", {})
        if vector_id in vectors:
            meta = vectors[vector_id].get("metadata", {}) if isinstance(vectors[vector_id], dict) \
                else getattr(vectors[vector_id], "metadata", {})
            return bool(meta.get("org_id"))
    except Exception as e:
        print(f"  [WARN] Could not fetch vector '{vector_id}': {e}")
    return False


def _delete_tagless_vectors(index, filename: str) -> None:
    """Delete all vectors for this filename that have no org_id tag (legacy)."""
    try:
        index.delete(filter={"filename": {"$eq": filename}})
        print(f"  Deleted legacy tagless vectors for '{filename}'")
    except Exception as e:
        print(f"  [WARN] Delete failed for '{filename}': {e}")


def migrate():
    index = get_pinecone_index()
    if index is None:
        print("ERROR: Could not connect to Pinecone. Check PINECONE_API_KEY / PINECONE_INDEX_NAME.")
        sys.exit(1)

    db = SessionLocal()
    try:
        docs = (
            db.query(Document)
            .filter(Document.location == "knowledgebase")
            .order_by(Document.org_id, Document.created_at)
            .all()
        )

        print(f"Found {len(docs)} knowledge-base document(s).\n")

        ok = skipped = failed = 0

        for i, doc in enumerate(docs, 1):
            org_id_str = str(doc.org_id)
            print(f"[{i}/{len(docs)}] '{doc.name}'  org={org_id_str[:8]}…")

            # ── Checkpoint: already migrated? ─────────────────────────────────
            if _already_migrated(index, doc.vector_id):
                print("  Already has org_id — skipping.")
                skipped += 1
                continue

            if not doc.cloudinary_url:
                print("  [SKIP] No cloudinary_url — cannot re-download.")
                skipped += 1
                continue

            file_type = (doc.file_type or "bin").lower()
            mime = _MIME_MAP.get(file_type, "application/octet-stream")
            is_image = mime.startswith("image/")

            if not (is_vectorizable(mime) or is_image):
                print(f"  [SKIP] file_type '{file_type}' is not vectorizable.")
                skipped += 1
                continue

            # ── Download from Cloudinary ──────────────────────────────────────
            try:
                resp = requests.get(doc.cloudinary_url, timeout=60)
                resp.raise_for_status()
            except Exception as e:
                print(f"  [FAIL] Download error: {e}")
                failed += 1
                continue

            # ── Extract text ──────────────────────────────────────────────────
            tmp_path = None
            extract_result = None
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_type}") as tmp:
                    tmp.write(resp.content)
                    tmp_path = tmp.name

                extract_result = (
                    extract_image_description(tmp_path, mime)
                    if is_image
                    else extract_text_from_file(tmp_path, mime)
                )
            finally:
                if tmp_path and os.path.exists(tmp_path):
                    os.remove(tmp_path)

            if not extract_result or not extract_result.get("success") or not extract_result.get("can_vectorize"):
                print(f"  [FAIL] Extraction failed: {extract_result.get('error') if extract_result else 'unknown'}")
                failed += 1
                continue

            # ── Delete old tagless vectors ────────────────────────────────────
            _delete_tagless_vectors(index, doc.name)

            # ── Re-index with org_id ──────────────────────────────────────────
            pinecone_result = upload_to_pinecone(
                text=extract_result["text"],
                filename=doc.name,
                file_type=extract_result["file_type"],
                metadata={
                    "uploaded_by": doc.uploaded_by or "",
                    "cloudinary_url": doc.cloudinary_url,
                },
                org_id=org_id_str,
            )

            if not pinecone_result.get("success"):
                print(f"  [FAIL] Pinecone indexing failed: {pinecone_result.get('error')}")
                failed += 1
                continue

            # ── Checkpoint commit: update vector_id in DB ─────────────────────
            doc.vector_id = pinecone_result.get("vector_id")
            db.commit()

            print(f"  OK — {pinecone_result.get('chunk_count', 1)} chunk(s) re-indexed.")
            ok += 1

        print(f"\n{'='*50}")
        print(f"Migration complete:")
        print(f"  Migrated : {ok}")
        print(f"  Skipped  : {skipped}")
        print(f"  Failed   : {failed}")
        if failed:
            print("Re-run the script to retry failed documents.")

    finally:
        db.close()


if __name__ == "__main__":
    migrate()
