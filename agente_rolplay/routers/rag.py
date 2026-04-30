from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from agente_rolplay.agent.cli_tools import anthropic_completion, get_text_by_relevance
from agente_rolplay.config import GPT_ACTIONS_API_KEY
from agente_rolplay.agent.system_prompt import system_prompt_rag
from agente_rolplay.db.auth import get_current_user
from agente_rolplay.db.database import get_db
from agente_rolplay.db.models import Document, Profile, User

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
def list_kb_files(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List Knowledge Base files for the current user's org (org-scoped via DB)."""
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    docs = (
        db.query(Document)
        .filter(Document.org_id == profile.org_id, Document.location == "knowledgebase")
        .order_by(Document.created_at.desc())
        .all()
    )

    return [
        {
            "filename": doc.name,
            "public_id": doc.drive_file_id,
            "resource_type": doc.resource_type,
            "format": doc.file_type,
            "bytes": doc.file_size,
            "secure_url": doc.cloudinary_url,
            "created_at": doc.created_at.isoformat() if doc.created_at else None,
        }
        for doc in docs
    ]


@router.get("/api/rag/search")
def semantic_search(
    q: str,
    top_k: int = 5,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Semantic vector search over the org's knowledge base."""
    from agente_rolplay.storage.pinecone_client import search_knowledge_base

    if not q or len(q.strip()) < 2:
        raise HTTPException(status_code=400, detail="Query too short")

    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    org_id = str(profile.org_id)

    # Fetch many chunks so deduplication still yields enough unique files
    chunks = search_knowledge_base(q.strip(), top_k=top_k * 10, org_id=org_id)
    # Defensive: discard any chunk whose org_id doesn't match (belt-and-suspenders)
    chunks = [c for c in chunks if c.get("org_id") == org_id]

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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a file from Cloudinary and its vectors from Pinecone."""
    from agente_rolplay.storage.pinecone_client import delete_by_filename

    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    org_id = str(profile.org_id) if profile else None

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
    pinecone_result = delete_by_filename(pinecone_filename, org_id=org_id)
    if not pinecone_result.get("success"):
        errors.append(f"Pinecone: {pinecone_result.get('error')}")

    if errors:
        raise HTTPException(status_code=500, detail="; ".join(errors))

    return {"deleted": public_id}
