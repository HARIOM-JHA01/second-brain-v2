# python3 roleplay_agent.py

from anthropic import Anthropic
from agente_rolplay.agent.cli_tools import (
    get_mexico_city_time,
    anthropic_completion,
)
from agente_rolplay.config import (
    ANTHROPIC_API_KEY,
    ANTHROPIC_MODEL_NAME,
    USER_ID,
    WEBHOOK_RENDER as WEBHOOK_RENDER_RAW,
    AGENT_MAX_TOKENS,
    MIN_RELEVANCE_SCORE,
)
from agente_rolplay.storage.pinecone_client import search_knowledge_base
from agente_rolplay.agent.system_prompt import PROMPT_CORE, system_prompt_rag
from agente_rolplay.agent.tools import tools

import re
import time

MODEL_NAME = ANTHROPIC_MODEL_NAME

_NO_CONTEXT_CONTENT = (
    "NO_CONTEXT_FOUND: The knowledge base contains no relevant information for this query "
    "(no documents matched or all similarity scores were below the relevance threshold).\n\n"
    "MANDATORY: Do NOT speculate, invent, or infer an answer. "
    "Tell the user honestly that this information is not available in the knowledge base. "
    "Suggest they upload the relevant document so you can answer accurately next time."
)

client = Anthropic(api_key=ANTHROPIC_API_KEY)
WEBHOOK_RENDER = WEBHOOK_RENDER_RAW if WEBHOOK_RENDER_RAW != "zz" else ""

user_id = USER_ID

# ----- ----- ----- AGENT HELPER FUNCTIONS ----- ----- -----


def construir_system_prompt(
    PROMPT_CORE=PROMPT_CORE,
    response_language: str = "es",
    session_facts: list = None,
):
    prompt = PROMPT_CORE
    if session_facts:
        facts_block = "\n\n# SESSION FACTS (user-provided corrections — treat as ground truth)\n"
        for fact in session_facts:
            facts_block += f"- {fact}\n"
        prompt += facts_block
    if response_language == "en":
        prompt += (
            "\n\nLANGUAGE OVERRIDE: The user is speaking English. "
            "You must answer in English."
        )
    else:
        prompt += (
            "\n\nLANGUAGE OVERRIDE: El usuario está hablando en español. "
            "Debes responder en español."
        )
    prompt += f"\n\nCurrent date: {get_mexico_city_time()}"
    return prompt


# ----- ----- ----- MAIN AGENT FUNCTION ----- ----- -----


def generate_coaching_report(
    history: list,
    scenario_name: str,
    lang: str = "es",
    anthropic_client=client,
    model_name=MODEL_NAME,
    ai_provider: str = "anthropic",
    ai_model: str = None,
) -> str:
    """Generate a structured coaching report from the session history."""
    if lang == "en":
        report_prompt = (
            f"You are a professional coaching evaluator. Review the following coaching session "
            f"for the scenario '{scenario_name}' and generate a detailed report.\n\n"
            "Format the report with these sections:\n"
            "📊 **Summary** — Brief overview of the session\n"
            "✅ **Strengths** — What the user did well\n"
            "📈 **Areas for Improvement** — Specific areas to work on\n"
            "💡 **Key Takeaways** — Main lessons from this session\n"
            "⭐ **Score** — Overall performance score out of 10 with justification\n\n"
            "Conversation transcript:\n"
        )
    else:
        report_prompt = (
            f"Eres un evaluador profesional de coaching. Revisa la siguiente sesión de coaching "
            f"para el escenario '{scenario_name}' y genera un reporte detallado.\n\n"
            "Formatea el reporte con estas secciones:\n"
            "📊 **Resumen** — Visión general breve de la sesión\n"
            "✅ **Fortalezas** — Lo que el usuario hizo bien\n"
            "📈 **Áreas de Mejora** — Áreas específicas en las que trabajar\n"
            "💡 **Puntos Clave** — Lecciones principales de esta sesión\n"
            "⭐ **Puntuación** — Puntuación general de desempeño sobre 10 con justificación\n\n"
            "Transcripción de la conversación:\n"
        )

    for msg in history:
        role_label = "Usuario" if msg["role"] == "user" else "Coach (IA)"
        if lang == "en":
            role_label = "User" if msg["role"] == "user" else "Coach (AI)"
        content = msg["content"]
        if isinstance(content, list):
            content = " ".join(
                block.get("text", "") if isinstance(block, dict) else str(block)
                for block in content
            )
        report_prompt += f"\n{role_label}: {content}"

    from agente_rolplay.agent.provider_adapter import create_message
    effective_model = ai_model or model_name
    return create_message(
        provider=ai_provider,
        model=effective_model,
        system="You are a professional coaching evaluator.",
        messages=[{"role": "user", "content": report_prompt}],
        max_tokens=2048,
    )


def responder_usuario(
    messages,
    data,
    telefono,
    id_conversacion,
    id_phone_number,
    response_language="es",
    session_facts=None,
    coaching_system_prompt: str = None,
    model_name=MODEL_NAME,
    user_id=user_id,
    anthropic_client=client,
    system_prompt_rag=system_prompt_rag,
    ai_provider: str = "anthropic",
    ai_model: str = None,
):
    start_time = time.time()

    # 2. Add user message
    new_messages = messages + [{"role": "user", "content": data["body"]}]

    # 5. Build system prompt according to phase
    if coaching_system_prompt:
        lang_override = (
            "Respond in English." if response_language == "en" else "Responde en español."
        )
        system_prompt = (
            coaching_system_prompt
            + f"\n\nLANGUAGE OVERRIDE: {lang_override}"
            + f"\n\nCurrent date: {get_mexico_city_time()}"
            + "\n\nFORMATTING: You are replying on WhatsApp. Never use markdown (no **, no ##, no backticks). "
            "For bold use single asterisks *like this*. For lists use plain numbers (1. 2. 3.) or dashes (-). "
            "Write conversationally and keep each message concise."
        )
    else:
        system_prompt = construir_system_prompt(
            response_language=response_language,
            session_facts=session_facts,
        )

    # For non-Anthropic providers in the coaching path, bypass the tool-call loop
    if coaching_system_prompt and ai_provider != "anthropic":
        from agente_rolplay.agent.provider_adapter import create_message
        effective_model = ai_model or model_name
        answer_text = create_message(
            provider=ai_provider,
            model=effective_model,
            system=system_prompt,
            messages=new_messages,
            max_tokens=AGENT_MAX_TOKENS,
        )
        return {
            "answer": answer_text,
            "output": None,
            "input_tokens": 0,
            "output_tokens": 0,
            "model_name": effective_model,
            "fase_actual": "coaching",
        }

    response = anthropic_client.messages.create(
        system=system_prompt,
        model=model_name,
        messages=new_messages,
        max_tokens=AGENT_MAX_TOKENS,
        tools=tools,
        tool_choice={"type": "any"},
    )
    print(f"RESPONSE : {response}")

    input_tokens = response.usage.input_tokens
    output_tokens = response.usage.output_tokens

    while response.stop_reason == "tool_use":
        new_messages.append({"role": "assistant", "content": response.content})

        tool_use = next(block for block in response.content if block.type == "tool_use")
        tool_name = tool_use.name
        tool_input = tool_use.input

        if "informacion_general" in tool_name.lower():
            print("Using general information tool")
            raw_query = tool_input.get("consulta") or data.get("body", "")
            optimized_query = raw_query

            try:
                optimized_query = (
                    anthropic_completion(
                        system_prompt=system_prompt_rag,
                        messages=[{"role": "user", "content": raw_query}],
                    )
                    .content[0]
                    .text.strip()
                )
            except Exception:
                optimized_query = raw_query

            text_lower = raw_query.lower()
            filename_filter = None
            file_match = re.search(r"\b[\w\-. ]+\.(pdf|docx|pptx|txt|xlsx)\b", raw_query, re.I)
            if file_match:
                filename_filter = file_match.group(0).strip()
            elif any(
                marker in text_lower
                for marker in ["this document", "this file", "that document", "that file"]
            ):
                filename_filter = data.get("last_uploaded_filename")

            results = search_knowledge_base(
                query=optimized_query,
                top_k=5,
                filename_filter=filename_filter,
            )

            if not results and optimized_query != raw_query:
                results = search_knowledge_base(
                    query=raw_query,
                    top_k=5,
                    filename_filter=filename_filter,
                )

            # Drop results below relevance threshold to prevent hallucination
            results = [r for r in results if r.get("score", 0) >= MIN_RELEVANCE_SCORE]

            # If optimized query yielded nothing above threshold, retry with raw query
            if not results and optimized_query != raw_query:
                fallback = search_knowledge_base(
                    query=raw_query,
                    top_k=5,
                    filename_filter=filename_filter,
                )
                results = [r for r in fallback if r.get("score", 0) >= MIN_RELEVANCE_SCORE]

            print(f"Content obtained from RAG ({len(results)} above threshold): {results}")

            if not results:
                content = _NO_CONTEXT_CONTENT
            else:
                lines = []
                for item in results:
                    filename = item.get("filename", "document")
                    score = item.get("score", 0)

                    # Build citation string
                    if item.get("page_range"):
                        citation = f"{filename}, {item['page_range']}"
                    elif item.get("chunk_count", 1) > 1:
                        citation = f"{filename}, chunk {item.get('chunk_index', 0) + 1} of {item['chunk_count']}"
                    else:
                        citation = filename

                    line = (
                        f"- [{citation}] (score {score:.3f}): "
                        f"{item.get('text_preview', '')[:260]}"
                    )
                    if item.get("cloudinary_url"):
                        line += f"\n  Image URL: {item['cloudinary_url']}"
                    lines.append(line)
                content = "\n".join(lines)

        elif "actualizar_drive" in tool_name.lower():
            print("Drive update tool")

            file_name = tool_input.get("nombre_archivo", "UNKNOWN")
            document_type = tool_input.get("tipo_documento", "UNKNOWN")
            print(f"File name: {file_name}, Document type: {document_type}")

            if "UNKNOWN" in file_name.upper() or "UNKNOWN" in document_type.upper():
                content = "Error: Debes proporcionar tanto el nombre del archivo como el tipo de documento."
            else:
                from agente_rolplay.messaging.process_messages import r

                # Extract phone from context (it's in data or messages)
                telefono = (
                    data.get("from", "").replace("whatsapp:", "").replace("+", "")
                )

                if telefono:
                    r.set(f"doc_nombre:{telefono}", file_name, ex=600)  # 5 minutes
                    r.set(f"doc_tipo:{telefono}", document_type, ex=600)
                    print(f"Saved to Redis: {file_name}.{document_type} for {telefono}")

                # content = f"Perfecto, the file will be named '{nombre_archivo}.{tipo_documento}' and saved in '{nombre_carpeta}'. "
                # content += "Now send me the document via WhatsApp."
                content = f"To upload the file '{file_name}.{document_type}', "
                content += "please send me the document here. I will receive it and upload it to Google Drive automatically. DO NOT ADD ANY ADDITIONAL TEXT ABOUT THIS, DO NOT TELL ME YOU CAN HELP WITH SOMETHING ELSE UNTIL I SEND THE FILE"

                # content = str(subir_archivo_a_drive(tool_input['nombre_archivo'], tool_input['tipo_documento']))
            print("content", content)

        elif "saludar_cliente" in tool_name.lower():
            print("Processing initial greeting")
            greeting = tool_input.get("saludo", "")

            content = f"Greeting processed correctly. The client said: '{greeting}'. "
            content += "Now present the options to the user in a friendly way."

        else:
            content = (
                anthropic_client.messages.create(
                    system=system_prompt,
                    model=model_name,
                    messages=new_messages,
                    max_tokens=AGENT_MAX_TOKENS,
                    temperature=0.1,
                )
                .content[0]
                .text.strip()
            )

        tool_response = {
            "role": "user",
            "content": [
                {"type": "tool_result", "tool_use_id": tool_use.id, "content": content}
            ],
        }
        new_messages.append(tool_response)

        response = anthropic_client.messages.create(
            system=system_prompt,
            model=model_name,
            messages=new_messages,
            max_tokens=AGENT_MAX_TOKENS,
            tools=tools,
        )
        input_tokens += response.usage.input_tokens
        output_tokens += response.usage.output_tokens

    print(f"Response generated by agent: {response.content[0].text.strip()}")
    output = {
        "answer": response.content[0].text,
        "output": response.content,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "model_name": model_name,
        "fase_actual": "metadata['fase_actual']  # For debugging",
    }

    end_time = time.time()
    print(f"Response time: {end_time - start_time:.2f}s ")

    return output


if __name__ == "__main__":
    # FLOW TO TEST THE AGENT LOCALLY
    messages = []
    while True:
        query = input("\nUser (type 'exit' to finish): ")

        if query.lower().strip() in ["exit", "salir"]:
            print("Goodbye!")
            break

        data = {"type": "text", "body": query}

        answer = responder_usuario(
            messages=messages, data=data, telefono="5566098295", id_conversacion="1111"
        )

        print(f"Answer: {answer['answer']}")

        messages.append({"role": "assistant", "content": answer["answer"]})
