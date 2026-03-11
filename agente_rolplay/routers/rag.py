from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from agente_rolplay.agent.cli_tools import anthropic_completion, get_text_by_relevance
from agente_rolplay.config import GPT_ACTIONS_API_KEY
from agente_rolplay.agent.system_prompt import system_prompt_rag

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
