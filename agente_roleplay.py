# python3 agente_roleplay.py

from anthropic import Anthropic
from dotenv import load_dotenv
from function_tools import (
    get_text_by_relevance,
    get_mexico_city_time,
    # categorizador_datosCompletos, 
    anthropic_completion
)
from google_drive import subir_archivo_a_drive
from system_prompt import (
    PROMPT_CORE,
    system_prompt_rag
)
from tools import tools
from utils import get_metadata, save_metadata

import json
import os
import time

load_dotenv()

anthropic_api_key: str = os.getenv('ANTHROPIC_API_KEY')
MODEL_NAME = os.getenv('ANTHROPIC_MODEL_NAME')

client = Anthropic(api_key=anthropic_api_key)
WEBHOOK_RENDER = os.getenv('WEBHOOK_RENDER') if os.getenv('WEBHOOK_RENDER') != "zz" else ""

user_id = os.getenv('USER_ID') if os.getenv('USER_ID') is not None else "default_user"

# ----- ----- ----- FUNCIONES AUXILIARES DEL AGENTE ----- ----- -----

def construir_system_prompt(PROMPT_CORE=PROMPT_CORE):
    prompt = PROMPT_CORE
    prompt += f"\n\nFecha actual: {get_mexico_city_time()}"
    return prompt

# ----- ----- ----- FUNCIÓN PRINCIPAL DEL AGENTE ----- ----- -----

def responder_usuario(
    messages, 
    data, 
    telefono, 
    id_conversacion,
    id_phone_number,
    model_name=MODEL_NAME,
    user_id=user_id,
    anthropic_client=client,
    system_prompt_rag=system_prompt_rag
):
    start_time = time.time()
    
    
    # 2. Agregar mensaje del usuario
    new_messages = messages + [{"role": "user", "content": data["body"]}]

    
    # 5. Construir system prompt según fase
    system_prompt = construir_system_prompt()

    response = anthropic_client.messages.create(
            system=system_prompt,
            model=model_name,
            messages=new_messages,
            max_tokens=4096,
            tools=tools,
            tool_choice={"type": "any"}
    )
    print(f"RESPONSE : {response}")
    
    input_tokens = response.usage.input_tokens
    output_tokens = response.usage.output_tokens

    while response.stop_reason == 'tool_use':
        new_messages.append({"role": "assistant", "content": response.content})

        tool_use = next(block for block in response.content if block.type == "tool_use")
        tool_name = tool_use.name
        tool_input = tool_use.input

        if 'informacion_general' in tool_name.lower():
            print("Usando herramienta de información general")
            ans = anthropic_completion(
                system_prompt=system_prompt_rag,
                messages=[{"role": "user", "content": data["body"]}]
                # model=model_name,
                # max_tokens=1000,
                # temperature=0.1
            ).content[0].text.strip()
            print(f"Respuesta del RAG: {ans}")
            # content = str(get_text_by_relevance(tool_input['consulta']))
            content = str(get_text_by_relevance(ans))
            print(f"Contenido obtenido del RAG: {content}")

        elif 'actualizar_drive' in tool_name.lower():
            print("herramienta de actualizar drive")

            nombre_archivo = tool_input.get('nombre_archivo', 'UNKNOWN')
            tipo_documento = tool_input.get('tipo_documento', 'UNKNOWN')
            print(f"Nombre archivo: {nombre_archivo}, Tipo documento: {tipo_documento}")

            if 'UNKNOWN' in nombre_archivo.upper() or 'UNKNOWN' in tipo_documento.upper():
                content = "Error: Debes proporcionar tanto el nombre del archivo como el tipo de documento."
            else:
                from procesa_mensajes import r
        
                # Extraer teléfono del contexto (está en data o messages)
                telefono = data.get('from', '').replace('whatsapp:', '').replace('+', '')
                
                if telefono:
                    r.set(f"doc_nombre:{telefono}", nombre_archivo, ex=600)  # 5 minutos
                    r.set(f"doc_tipo:{telefono}", tipo_documento, ex=600)
                    print(f"💾 Guardado en Redis: {nombre_archivo}.{tipo_documento} para {telefono}")
                
                # content = f"Perfecto, el archivo se llamará '{nombre_archivo}.{tipo_documento}' y se guardará en '{nombre_carpeta}'. "
                # content += "Ahora envíame el documento por WhatsApp."
                content = f"Para subir el archivo '{nombre_archivo}.{tipo_documento}', "
                content += "por favor envíame el documento por aquí. Lo recibiré y lo subiré automáticamente a Google Drive. NO AGREGUES NINGUN TEXTO ADICIONAL DE ESTO , NO LE DIGAS SI LO PUEDES AYUDAR EN ALGO MAS HASTA QUE ENVIE EL ARCHIVO"

                # content = str(subir_archivo_a_drive(tool_input['nombre_archivo'], tool_input['tipo_documento']))
            print("content", content)

        elif 'saludar_cliente' in tool_name.lower():
            print("🤝 Procesando saludo inicial")
            saludo = tool_input.get('saludo', '')

            content = f"Saludo procesado correctamente. El cliente dijo: '{saludo}'. "
            content += "Ahora presenta las opciones al usuario de forma amigable."

        else: 
            content = anthropic_client.messages.create(
            system=system_prompt,
            model=model_name,
            messages=new_messages,
            max_tokens=4096,
            temperature=0.1
        ).content[0].text.strip()

        tool_response = {
            "role": "user",
            "content": [{
                "type": "tool_result",
                "tool_use_id": tool_use.id,
                "content": content
            }]
        }
        new_messages.append(tool_response)

        response = anthropic_client.messages.create(
            system=system_prompt,
            model=model_name,
            messages=new_messages,
            max_tokens=4096,
            tools=tools
        )
        input_tokens += response.usage.input_tokens
        output_tokens += response.usage.output_tokens

    print(f"📝 Respuesta generada por el agente: {response.content[0].text.strip()}")
    output = {
        "answer": response.content[0].text,
        "output": response.content,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "model_name": model_name,
        "fase_actual": "metadata['fase_actual']  # Para debugging"
    }

    end_time = time.time()
    print(f"⏱️ Tiempo de respuesta: {end_time - start_time:.2f}s ")

    return output

if __name__ == '__main__':

    # FLUJO PARA PROBAR EL AGENTE EN LOCAL
    messages=[]
    while True:
        query = input("\nUsuario (escribe 'salir' para terminar): ")

        if query.lower().strip() in ['salir']:
            print("¡Hasta luego!")
            break

        data = {
            'type': 'text',
            'body': query
        }

        answer = responder_usuario(
            messages=messages,
            data=data,
            telefono="5566098295",
            id_conversacion="1111"
        )

        print(f'Respuesta: {answer['answer']}')

        messages.append({
            'role': 'assistant',
            'content': answer['answer']
        })