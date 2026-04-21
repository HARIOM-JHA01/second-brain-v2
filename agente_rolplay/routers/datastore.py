"""
Data Store + Knowledge Base management API.

Data Store  — staging area: all new uploads land here; files are NOT indexed.
Knowledge Base — indexed files: admin explicitly promotes files here (triggers Pinecone indexing).

Endpoints:
  GET  /api/datastore                   — list org Data Store files
  POST /api/datastore/upload            — web admin upload (multipart)
  DELETE /api/datastore/{doc_id}        — delete from Data Store
  POST /api/datastore/{doc_id}/promote  — move to KB (index)
  GET  /api/knowledgebase               — list org KB files
  POST /api/knowledgebase/{doc_id}/demote — move back to Data Store (un-index)
  DELETE /api/knowledgebase/{doc_id}    — delete from KB
  POST /api/chat/query                  — query KB via chat
"""

import os
import tempfile
import uuid as _uuid

import requests
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from agente_rolplay.db.auth import get_current_user
from agente_rolplay.db.database import get_db
from agente_rolplay.db.models import Document, Profile, User

router = APIRouter()


# ── helpers ──────────────────────────────────────────────────────────────────


def _get_org_id(current_user: User, db: Session) -> _uuid.UUID:
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile.org_id


def _get_doc(doc_id: str, org_id, location: str, db: Session) -> Document:
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if str(doc.org_id) != str(org_id):
        raise HTTPException(status_code=403, detail="Access denied")
    if doc.location != location:
        raise HTTPException(
            status_code=400,
            detail=f"Document is not in {location}",
        )
    return doc


def _cloudinary_delete(public_id: str):
    """Try to delete a file from Cloudinary (both resource types, silent on not-found)."""
    try:
        import cloudinary.uploader
        cloudinary.uploader.destroy(public_id, resource_type="image")
        cloudinary.uploader.destroy(public_id, resource_type="raw")
    except Exception as e:
        print(f"Warning: Cloudinary delete failed for {public_id}: {e}")


def _doc_response(doc: Document) -> dict:
    return {
        "id": str(doc.id),
        "name": doc.name,
        "drive_file_id": doc.drive_file_id,
        "cloudinary_url": doc.cloudinary_url,
        "file_type": doc.file_type,
        "file_size": doc.file_size,
        "resource_type": doc.resource_type,
        "uploaded_by": doc.uploaded_by,
        "upload_source": doc.upload_source,
        "location": doc.location,
        "vector_id": doc.vector_id,
        "created_at": doc.created_at.isoformat() if doc.created_at else None,
    }


# ── Data Store ────────────────────────────────────────────────────────────────


@router.get("/api/datastore")
def list_datastore(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org_id = _get_org_id(current_user, db)
    docs = (
        db.query(Document)
        .filter(Document.org_id == org_id, Document.location == "datastore")
        .order_by(Document.created_at.desc())
        .all()
    )
    return [_doc_response(d) for d in docs]


@router.post("/api/datastore/upload")
async def upload_to_datastore(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from agente_rolplay.storage.cloudinary_storage import upload_file_to_cloudinary

    org_id = _get_org_id(current_user, db)

    original_name = file.filename or "upload"
    _, ext = os.path.splitext(original_name)
    ext_clean = ext.lstrip(".").lower() if ext else "bin"

    # Write to temp file
    suffix = f".{ext_clean}" if ext_clean else ""
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        result = upload_file_to_cloudinary(tmp_path, folder="datastore")
    finally:
        try:
            os.remove(tmp_path)
        except Exception:
            pass

    if not result or not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Upload failed") if result else "Upload failed",
        )

    doc = Document(
        org_id=org_id,
        name=original_name,
        drive_file_id=result.get("public_id"),
        location="datastore",
        cloudinary_url=result.get("secure_url"),
        file_type=ext_clean,
        file_size=result.get("bytes"),
        resource_type=result.get("resource_type"),
        uploaded_by="admin",
        upload_source="web",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return _doc_response(doc)


@router.delete("/api/datastore/{doc_id}")
def delete_from_datastore(
    doc_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org_id = _get_org_id(current_user, db)
    doc = _get_doc(doc_id, org_id, "datastore", db)

    if doc.drive_file_id:
        _cloudinary_delete(doc.drive_file_id)

    db.delete(doc)
    db.commit()
    return {"deleted": doc_id}


@router.post("/api/datastore/{doc_id}/promote")
def promote_to_kb(
    doc_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Move a file from Data Store → Knowledge Base (triggers Pinecone indexing)."""
    from agente_rolplay.storage.cloudinary_storage import upload_file_to_cloudinary
    from agente_rolplay.storage.file_processor import (
        extract_image_description,
        extract_text_from_file,
        is_vectorizable,
    )
    from agente_rolplay.storage.pinecone_client import upload_to_pinecone

    org_id = _get_org_id(current_user, db)
    doc = _get_doc(doc_id, org_id, "datastore", db)

    if not doc.cloudinary_url:
        raise HTTPException(status_code=400, detail="Document has no cloudinary_url")

    # Download file to temp location
    try:
        resp = requests.get(doc.cloudinary_url, timeout=60)
        resp.raise_for_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not download file: {e}")

    file_type = doc.file_type or "bin"
    suffix = f".{file_type}"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(resp.content)
        tmp_path = tmp.name

    try:
        # Determine MIME type for extraction helpers
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
        mime = _MIME_MAP.get(file_type.lower(), "application/octet-stream")
        is_image = mime.startswith("image/")

        if is_image:
            extract_result = extract_image_description(tmp_path, mime)
        elif is_vectorizable(mime):
            extract_result = extract_text_from_file(tmp_path, mime)
        else:
            raise HTTPException(
                status_code=400,
                detail=f"File type '{file_type}' cannot be indexed",
            )

        if not extract_result.get("success") or not extract_result.get("can_vectorize"):
            raise HTTPException(
                status_code=422,
                detail=extract_result.get("error", "Text extraction failed"),
            )

        pinecone_result = upload_to_pinecone(
            text=extract_result["text"],
            filename=doc.name,
            file_type=extract_result["file_type"],
            metadata={
                "uploaded_by": doc.uploaded_by or "",
                "cloudinary_url": doc.cloudinary_url,
            },
        )

        if not pinecone_result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=pinecone_result.get("error", "Pinecone indexing failed"),
            )

    finally:
        try:
            os.remove(tmp_path)
        except Exception:
            pass

    # All good — update DB
    doc.location = "knowledgebase"
    doc.vector_id = pinecone_result.get("vector_id")
    db.commit()
    db.refresh(doc)
    return _doc_response(doc)


# ── Knowledge Base ────────────────────────────────────────────────────────────


@router.get("/api/knowledgebase")
def list_knowledgebase(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org_id = _get_org_id(current_user, db)
    docs = (
        db.query(Document)
        .filter(Document.org_id == org_id, Document.location == "knowledgebase")
        .order_by(Document.created_at.desc())
        .all()
    )
    return [_doc_response(d) for d in docs]


@router.post("/api/knowledgebase/{doc_id}/demote")
def demote_to_datastore(
    doc_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Move a file from Knowledge Base → Data Store (removes from Pinecone)."""
    from agente_rolplay.storage.pinecone_client import delete_by_filename

    org_id = _get_org_id(current_user, db)
    doc = _get_doc(doc_id, org_id, "knowledgebase", db)

    if doc.name:
        delete_by_filename(doc.name)

    doc.location = "datastore"
    doc.vector_id = None
    db.commit()
    db.refresh(doc)
    return _doc_response(doc)


@router.delete("/api/knowledgebase/{doc_id}")
def delete_from_kb(
    doc_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a file completely from Knowledge Base (Cloudinary + Pinecone + DB)."""
    from agente_rolplay.storage.pinecone_client import delete_by_filename

    org_id = _get_org_id(current_user, db)
    doc = _get_doc(doc_id, org_id, "knowledgebase", db)

    if doc.drive_file_id:
        _cloudinary_delete(doc.drive_file_id)

    if doc.name:
        delete_by_filename(doc.name)

    db.delete(doc)
    db.commit()
    return {"deleted": doc_id}


# ── Web Chat ──────────────────────────────────────────────────────────────────


class ChatQueryRequest(BaseModel):
    question: str
    history: list = []  # [{"role": "user"|"assistant", "content": "..."}]


class ChatTitleRequest(BaseModel):
    question: str
    answer: str


@router.post("/api/chat/title")
def generate_chat_title(
    body: ChatTitleRequest,
    current_user: User = Depends(get_current_user),
):
    """Generate a short descriptive title for a chat session from the first exchange."""
    from agente_rolplay.agent.provider_adapter import _get_anthropic
    from agente_rolplay.config import HAIKU_MODEL_NAME

    prompt = (
        f"User asked: {body.question}\n\n"
        f"Assistant answered: {body.answer[:300]}\n\n"
        "Write a short title (4-7 words) that captures the core topic of this conversation. "
        "No quotes, no punctuation at the end, just the title."
    )
    try:
        client = _get_anthropic()
        resp = client.messages.create(
            model=HAIKU_MODEL_NAME,
            system="You generate short, clear chat titles. Reply with only the title, nothing else.",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=20,
        )
        title = resp.content[0].text.strip().strip('"').strip("'")
        return {"title": title}
    except Exception:
        return {"title": None}


@router.post("/api/chat/query")
def chat_query(
    body: ChatQueryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Query the Knowledge Base via chat (RAG + Claude)."""
    from agente_rolplay.agent.provider_adapter import create_message
    from agente_rolplay.config import HAIKU_MODEL_NAME
    from agente_rolplay.storage.pinecone_client import search_knowledge_base
    from agente_rolplay.messaging.message_processor import is_knowledge_base_inventory_query

    if not body.question or not body.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    # Short-circuit inventory queries — count from DB, not RAG chunks
    if is_knowledge_base_inventory_query(body.question.strip()):
        org_id = _get_org_id(current_user, db)
        count = (
            db.query(Document)
            .filter(Document.org_id == org_id, Document.location == "knowledgebase")
            .count()
        )
        return {
            "answer": f"There are currently {count} file(s) in your Knowledge Base.",
            "sources": [],
        }

    chunks = search_knowledge_base(body.question.strip(), top_k=15)

    sources = []
    context_parts = []
    seen_files: set = set()
    for chunk in chunks:
        fname = chunk.get("filename", "")
        score = chunk.get("score", 0)
        page_range = chunk.get("page_range", "")
        text_preview = chunk.get("text_preview", "")

        if fname not in seen_files:
            seen_files.add(fname)
            sources.append(
                {"filename": fname, "score": round(score, 3), "page_range": page_range}
            )

        label = fname
        if page_range:
            label += f" ({page_range})"
        context_parts.append(f"[{label}]\n{text_preview}")

    context_text = "\n\n---\n\n".join(context_parts) if context_parts else ""

    system_prompt = (
        "You are a helpful assistant for an organization. "
        "Answer questions using ONLY the knowledge base context provided below. "
        "If the answer is not found in the context, say so clearly. "
        "Be concise and accurate.\n\n"
        "Knowledge Base Context:\n"
        f"{context_text}"
    )

    # Build messages: history + current question
    messages = list(body.history)
    messages.append({"role": "user", "content": body.question.strip()})

    try:
        answer = create_message(
            provider="anthropic",
            model=HAIKU_MODEL_NAME,
            system=system_prompt,
            messages=messages,
            max_tokens=1000,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI call failed: {e}")

    return {
        "answer": answer,
        "sources": sources[:5],
    }


@router.post("/api/chat/stream")
async def chat_stream(
    body: ChatQueryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Streaming SSE version of chat_query."""
    import json
    from fastapi.responses import StreamingResponse
    from agente_rolplay.storage.pinecone_client import search_knowledge_base
    from agente_rolplay.messaging.message_processor import is_knowledge_base_inventory_query
    from agente_rolplay.config import HAIKU_MODEL_NAME

    if not body.question or not body.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    # Inventory short-circuit
    if is_knowledge_base_inventory_query(body.question.strip()):
        org_id = _get_org_id(current_user, db)
        count = (
            db.query(Document)
            .filter(Document.org_id == org_id, Document.location == "knowledgebase")
            .count()
        )
        answer = f"There are currently **{count}** file(s) in your Knowledge Base."

        def _inventory():
            yield f"data: {json.dumps({'type': 'sources', 'sources': []})}\n\n"
            yield f"data: {json.dumps({'type': 'text', 'text': answer})}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        return StreamingResponse(_inventory(), media_type="text/event-stream")

    chunks = search_knowledge_base(body.question.strip(), top_k=15)

    sources = []
    context_parts = []
    seen_files: set = set()
    for chunk in chunks:
        fname = chunk.get("filename", "")
        score = chunk.get("score", 0)
        page_range = chunk.get("page_range", "")
        text_preview = chunk.get("text_preview", "")
        if fname not in seen_files:
            seen_files.add(fname)
            sources.append({"filename": fname, "score": round(score, 3), "page_range": page_range})
        label = fname + (f" ({page_range})" if page_range else "")
        context_parts.append(f"[{label}]\n{text_preview}")

    context_text = "\n\n---\n\n".join(context_parts) if context_parts else ""
    system_prompt = (
        "You are a helpful assistant for an organization. "
        "Answer questions using ONLY the knowledge base context provided below. "
        "If the answer is not found in the context, say so clearly. "
        "Be concise and accurate. Use markdown formatting where helpful.\n\n"
        "Knowledge Base Context:\n"
        f"{context_text}"
    )

    messages = list(body.history)
    messages.append({"role": "user", "content": body.question.strip()})
    sources_top5 = sources[:5]

    def _generate():
        from agente_rolplay.agent.provider_adapter import _get_anthropic
        yield f"data: {json.dumps({'type': 'sources', 'sources': sources_top5})}\n\n"
        try:
            client = _get_anthropic()
            with client.messages.stream(
                model=HAIKU_MODEL_NAME,
                system=system_prompt,
                messages=messages,
                max_tokens=1500,
            ) as stream:
                for text in stream.text_stream:
                    yield f"data: {json.dumps({'type': 'text', 'text': text})}\n\n"
        except Exception as exc:
            yield f"data: {json.dumps({'type': 'error', 'message': str(exc)})}\n\n"
        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(_generate(), media_type="text/event-stream")
