import re
import uuid
from datetime import datetime
from typing import Optional

# Matches page markers embedded by _extract_from_pdf: <<PAGE:5>>
_PDF_PAGE_MARKER = re.compile(r"<<PAGE:(\d+)>>")

from agente_rolplay.config import (
    OPENAI_API_KEY,
    OPENAI_EMBEDDINGS_MODEL,
    PINECONE_API_KEY,
    PINECONE_ENV,
    PINECONE_INDEX_NAME,
    VECTOR_DIMENSION,
    CHUNK_MAX_TOKENS,
    CHUNK_OVERLAP_TOKENS,
)

pinecone_client = None
pinecone_index = None


def chunk_text_for_embedding(
    text: str, max_tokens: int = None, overlap_tokens: int = None
) -> list[str]:
    """
    Split text into token-safe chunks for embedding models with context limits.
    """
    if max_tokens is None:
        max_tokens = CHUNK_MAX_TOKENS
    if overlap_tokens is None:
        overlap_tokens = CHUNK_OVERLAP_TOKENS

    if not text:
        return []

    try:
        import tiktoken

        encoding = tiktoken.get_encoding("cl100k_base")
        token_ids = encoding.encode(text)

        if len(token_ids) <= max_tokens:
            return [text]

        chunks = []
        step = max_tokens - overlap_tokens
        if step <= 0:
            step = max_tokens

        for start in range(0, len(token_ids), step):
            end = start + max_tokens
            chunk_token_ids = token_ids[start:end]
            if not chunk_token_ids:
                continue
            chunks.append(encoding.decode(chunk_token_ids))

        return chunks
    except Exception:
        # Fallback: conservative character chunking when tokenizer is unavailable
        max_chars = 24000
        overlap_chars = 2000
        chunks = []
        step = max_chars - overlap_chars
        for start in range(0, len(text), step):
            chunks.append(text[start : start + max_chars])
        return chunks


def get_pinecone_index():
    """Get or initialize Pinecone index."""
    global pinecone_client, pinecone_index

    if pinecone_index is not None:
        return pinecone_index

    try:
        from pinecone import Pinecone

        pinecone_client = Pinecone(api_key=PINECONE_API_KEY)
        pinecone_index = pinecone_client.Index(PINECONE_INDEX_NAME)
        print(f"Connected to Pinecone index: {PINECONE_INDEX_NAME}")
        return pinecone_index
    except Exception as e:
        print(f"Error connecting to Pinecone: {e}")
        return None


def upload_to_pinecone(
    text: str,
    filename: str,
    file_type: str,
    metadata: Optional[dict] = None,
) -> dict:
    """
    Upload text chunk to Pinecone with metadata.

    Args:
        text: Text content to vectorize
        filename: Original filename
        file_type: File extension (pdf, docx, pptx, txt)
        metadata: Additional metadata

    Returns:
        dict with success status and vector_id or error
    """
    try:
        from openai import OpenAI

        index = get_pinecone_index()
        if index is None:
            return {"success": False, "error": "Pinecone not available"}

        client = OpenAI(api_key=OPENAI_API_KEY)

        vector_id = str(uuid.uuid4())
        uploaded_at = datetime.utcnow().isoformat() + "Z"

        chunks = chunk_text_for_embedding(text=text)
        if not chunks:
            return {"success": False, "error": "No text to embed"}

        vectors = []
        vector_ids = []
        total_chunks = len(chunks)

        for chunk_index, chunk_text in enumerate(chunks):
            chunk_vector_id = f"{vector_id}_{chunk_index}"
            vector_ids.append(chunk_vector_id)

            # Extract page numbers from PDF markers, then strip markers for clean embedding
            page_numbers = [int(p) for p in _PDF_PAGE_MARKER.findall(chunk_text)]
            clean_chunk = _PDF_PAGE_MARKER.sub("", chunk_text).strip()

            text_preview = clean_chunk[:1000] if len(clean_chunk) > 1000 else clean_chunk

            vector_metadata = {
                "filename": filename,
                "file_type": file_type,
                "uploaded_at": uploaded_at,
                "text_preview": text_preview,
                "chunk_index": chunk_index,
                "chunk_count": total_chunks,
            }

            if page_numbers:
                page_start = min(page_numbers)
                page_end = max(page_numbers)
                vector_metadata["page_start"] = page_start
                vector_metadata["page_end"] = page_end
                vector_metadata["page_range"] = (
                    f"p. {page_start}" if page_start == page_end else f"pp. {page_start}–{page_end}"
                )

            if metadata:
                vector_metadata.update(metadata)

            embedding_response = client.embeddings.create(
                model=OPENAI_EMBEDDINGS_MODEL,
                input=clean_chunk or chunk_text,
                dimensions=VECTOR_DIMENSION,
            )
            embedding = embedding_response.data[0].embedding

            vectors.append(
                {
                    "id": chunk_vector_id,
                    "values": embedding,
                    "metadata": vector_metadata,
                }
            )

        index.upsert(vectors=vectors)

        print(
            f"Uploaded to Pinecone: {len(vector_ids)} chunk(s) for file {filename} with base id {vector_id}"
        )
        return {
            "success": True,
            "vector_id": vector_ids[0],
            "vector_ids": vector_ids,
            "chunk_count": total_chunks,
            "uploaded_at": uploaded_at,
        }

    except Exception as e:
        print(f"Error uploading to Pinecone: {e}")
        return {"success": False, "error": str(e)}


def search_knowledge_base(
    query: str,
    top_k: int = 5,
    filename_filter: Optional[str] = None,
) -> list:
    """
    Search the knowledge base for relevant documents.

    Args:
        query: Search query text
        top_k: Number of results to return
        filename_filter: Optional filename to filter results

    Returns:
        List of matching documents with metadata
    """
    try:
        from openai import OpenAI

        index = get_pinecone_index()
        if index is None:
            print("Pinecone not available for search")
            return []

        client = OpenAI(api_key=OPENAI_API_KEY)

        embedding_response = client.embeddings.create(
            model=OPENAI_EMBEDDINGS_MODEL,
            input=query,
            dimensions=VECTOR_DIMENSION,
        )
        query_embedding = embedding_response.data[0].embedding

        filter_dict = {}
        if filename_filter:
            filter_dict["filename"] = {"$eq": filename_filter}

        search_params = {
            "vector": query_embedding,
            "top_k": top_k,
            "include_metadata": True,
        }

        if filter_dict:
            search_params["filter"] = filter_dict

        results = index.query(**search_params)

        matches = []
        for match in results.matches:
            entry = {
                "id": match.id,
                "score": match.score,
                "filename": match.metadata.get("filename"),
                "file_type": match.metadata.get("file_type"),
                "uploaded_at": match.metadata.get("uploaded_at"),
                "text_preview": match.metadata.get("text_preview", ""),
                "chunk_index": match.metadata.get("chunk_index"),
                "chunk_count": match.metadata.get("chunk_count"),
            }
            if match.metadata.get("page_range"):
                entry["page_range"] = match.metadata["page_range"]
                entry["page_start"] = match.metadata.get("page_start")
                entry["page_end"] = match.metadata.get("page_end")
            cloudinary_url = match.metadata.get("cloudinary_url")
            if cloudinary_url:
                entry["cloudinary_url"] = cloudinary_url
            matches.append(entry)

        print(f"Search returned {len(matches)} results for query: {query[:50]}...")
        return matches

    except Exception as e:
        print(f"Error searching Pinecone: {e}")
        return []


def delete_from_pinecone(vector_id: str) -> dict:
    """
    Delete a vector from Pinecone.

    Args:
        vector_id: ID of the vector to delete

    Returns:
        dict with success status
    """
    try:
        index = get_pinecone_index()
        if index is None:
            return {"success": False, "error": "Pinecone not available"}

        index.delete(ids=[vector_id])
        print(f"Deleted vector from Pinecone: {vector_id}")
        return {"success": True}

    except Exception as e:
        print(f"Error deleting from Pinecone: {e}")
        return {"success": False, "error": str(e)}


def delete_by_filename(filename: str) -> dict:
    """
    Delete all vectors associated with a filename.

    Args:
        filename: Name of the file whose vectors should be deleted

    Returns:
        dict with success status and count of deleted vectors
    """
    try:
        index = get_pinecone_index()
        if index is None:
            return {"success": False, "error": "Pinecone not available"}

        index.delete(filter={"filename": {"$eq": filename}})
        print(f"Deleted vectors for filename: {filename}")
        return {"success": True}

    except Exception as e:
        print(f"Error deleting from Pinecone: {e}")
        return {"success": False, "error": str(e)}
