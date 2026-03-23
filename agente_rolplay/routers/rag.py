from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from agente_rolplay.agent.cli_tools import anthropic_completion, get_text_by_relevance
from agente_rolplay.config import GPT_ACTIONS_API_KEY
from agente_rolplay.agent.system_prompt import system_prompt_rag
from agente_rolplay.db.auth import get_current_user
from agente_rolplay.db.models import User

router = APIRouter()


@router.post("/api/v1/rag/query")
async def rag_query(request: Request, authorization: str = Header(None)):
    # Bearer auth for GPT
    if authorization != f"Bearer {GPT_ACTIONS_API_KEY}":
        raise HTTPException(status_code=401, detail="Unauthorized")

    body = await request.json()
    pregunta = body.get("question", "")

    if not pregunta:
        return JSONResponse({"error": "Falta 'question'"}, status_code=400)

    ans = (
        anthropic_completion(
            system_prompt=system_prompt_rag,
            messages=[{"role": "user", "content": pregunta}],
        )
        .content[0]
        .text.strip()
    )
    print(f"LLM response for query: {ans}")

    contexto = get_text_by_relevance(ans)

    return JSONResponse({"answer": contexto})


@router.get("/api/rag/files")
def list_kb_files(current_user: User = Depends(get_current_user)):
    try:
        import cloudinary.api

        def _fetch(resource_type: str):
            return cloudinary.api.resources(
                type="upload",
                resource_type=resource_type,
                prefix="knowledgebase/",
                max_results=100,
            ).get("resources", [])

        resources = _fetch("image") + _fetch("raw")
        files = [
            {
                "filename": r.get("public_id", "").split("/")[-1],
                "public_id": r.get("public_id"),
                "resource_type": r.get("resource_type"),
                "format": r.get("format"),
                "bytes": r.get("bytes"),
                "secure_url": r.get("secure_url"),
                "created_at": r.get("created_at"),
            }
            for r in resources
        ]
        return files
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/rag/search")
def semantic_search(
    q: str,
    top_k: int = 5,
    current_user: User = Depends(get_current_user),
):
    """Semantic vector search over the org's knowledge base."""
    from agente_rolplay.storage.pinecone_client import search_knowledge_base

    if not q or len(q.strip()) < 2:
        raise HTTPException(status_code=400, detail="Query too short")

    # Fetch many chunks so deduplication still yields enough unique files
    chunks = search_knowledge_base(q.strip(), top_k=top_k * 10)

    # Deduplicate by filename — keep highest-score chunk per file
    seen: dict = {}
    for r in chunks:
        fname = r.get("filename") or ""
        if fname not in seen or r["score"] > seen[fname]["score"]:
            seen[fname] = r

    # Return top_k unique files sorted by score
    unique = sorted(seen.values(), key=lambda x: x["score"], reverse=True)
    return unique[:top_k]


@router.delete("/api/rag/files")
def delete_kb_file(
    public_id: str,
    format: str = "",
    current_user: User = Depends(get_current_user),
):
    """Delete a file from Cloudinary and its vectors from Pinecone."""
    from agente_rolplay.storage.pinecone_client import delete_by_filename

    errors = []

    # Delete from Cloudinary (try both resource types; destroy silently ignores not-found)
    try:
        import cloudinary.uploader
        cloudinary.uploader.destroy(public_id, resource_type="image")
        cloudinary.uploader.destroy(public_id, resource_type="raw")
    except Exception as e:
        errors.append(f"Cloudinary: {e}")

    # Pinecone stores filenames with extension; Cloudinary public_id has no extension.
    # Reconstruct: "knowledgebase/my_doc" + format "pdf" → "my_doc.pdf"
    base_name = public_id.split("/")[-1]
    pinecone_filename = f"{base_name}.{format}" if format else base_name
    pinecone_result = delete_by_filename(pinecone_filename)
    if not pinecone_result.get("success"):
        errors.append(f"Pinecone: {pinecone_result.get('error')}")

    if errors:
        raise HTTPException(status_code=500, detail="; ".join(errors))

    return {"deleted": public_id}
