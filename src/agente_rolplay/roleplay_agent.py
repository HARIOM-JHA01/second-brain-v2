# python3 roleplay_agent.py

from anthropic import Anthropic
from dotenv import load_dotenv
from src.agente_rolplay.cli_tools import (
    get_text_by_relevance,
    get_mexico_city_time,
    anthropic_completion,
)
from src.agente_rolplay.google_drive import subir_archivo_a_drive
from src.agente_rolplay.system_prompt import PROMPT_CORE, system_prompt_rag
from src.agente_rolplay.tools import tools
from src.agente_rolplay.helpers import get_metadata, save_metadata

import json
import os
import time

load_dotenv()

anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY")
MODEL_NAME = os.getenv("ANTHROPIC_MODEL_NAME")

client = Anthropic(api_key=anthropic_api_key)
WEBHOOK_RENDER = (
    os.getenv("WEBHOOK_RENDER") if os.getenv("WEBHOOK_RENDER") != "zz" else ""
)

user_id = os.getenv("USER_ID") if os.getenv("USER_ID") is not None else "default_user"

# ----- ----- ----- AGENT HELPER FUNCTIONS ----- ----- -----


def construir_system_prompt(PROMPT_CORE=PROMPT_CORE):
    prompt = PROMPT_CORE
    prompt += f"\n\nCurrent date: {get_mexico_city_time()}"
    return prompt


# ----- ----- ----- MAIN AGENT FUNCTION ----- ----- -----


def responder_usuario(
    messages,
    data,
    telefono,
    id_conversacion,
    id_phone_number,
    model_name=MODEL_NAME,
    user_id=user_id,
    anthropic_client=client,
    system_prompt_rag=system_prompt_rag,
):
    start_time = time.time()

    # 2. Add user message
    new_messages = messages + [{"role": "user", "content": data["body"]}]

    # 5. Build system prompt according to phase
    system_prompt = construir_system_prompt()

    response = anthropic_client.messages.create(
        system=system_prompt,
        model=model_name,
        messages=new_messages,
        max_tokens=4096,
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
            ans = (
                anthropic_completion(
                    system_prompt=system_prompt_rag,
                    messages=[{"role": "user", "content": data["body"]}],
                    # model=model_name,
                    # max_tokens=1000,
                    # temperature=0.1
                )
                .content[0]
                .text.strip()
            )
            print(f"RAG response: {ans}")
            # content = str(get_text_by_relevance(tool_input['consulta']))
            content = str(get_text_by_relevance(ans))
            print(f"Content obtained from RAG: {content}")

        elif "actualizar_drive" in tool_name.lower():
            print("Drive update tool")

            file_name = tool_input.get("nombre_archivo", "UNKNOWN")
            document_type = tool_input.get("tipo_documento", "UNKNOWN")
            print(f"File name: {file_name}, Document type: {document_type}")

            if "UNKNOWN" in file_name.upper() or "UNKNOWN" in document_type.upper():
                content = "Error: Debes proporcionar tanto el nombre del archivo como el tipo de documento."
            else:
                from src.agente_rolplay.process_messages import r

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
                    max_tokens=4096,
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
            max_tokens=4096,
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
