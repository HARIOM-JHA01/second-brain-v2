# python3 utils.py

from datetime import datetime

import json
import os
import redis
import requests
import tiktoken

from src.agente_rolplay.config import (
    REDIS_HOST,
    REDIS_PASSWORD,
    REDIS_PORT,
    WEBHOOK_RENDER,
)

redis_metadata_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    decode_responses=True,
    username="default",
    password=REDIS_PASSWORD,
)

# NEW: TTL of 24 hours (instead of 10 minutes)
METADATA_TTL = 86400  # 24 hours in seconds


def enviar_imagen_ultramsg(
    phone,
    image_url,
    caption=None,
    msgID=None,
    INSTANCIA_ULTRAMSG=None,
    token_ultramsg=None,
):
    """
    Sends an image via UltraMSG using their REST API.

    Parameters:
    - phone (str): destination number in full international format, including +
                   e.g. "+5219991234567"
    - image_url (str): public URL of the image
    - caption (str): optional text to show as image caption
    - msgID (str): optional, ID of the message being replied to
    """

    phone = f"521{phone}"

    if not phone.startswith("+"):
        phone = f"+{phone}"

    url = f"https://api.ultramsg.com/{INSTANCIA_ULTRAMSG}/messages/image"

    # Use caption if provided, otherwise leave empty
    caption = caption or ""

    # Build payload as plain string
    payload = f"token={token_ultramsg}&to={phone}&image={image_url}&caption={caption}"
    payload = payload.encode("utf8").decode("iso-8859-1")

    headers = {"content-type": "application/x-www-form-urlencoded"}

    response = requests.request("POST", url, data=payload, headers=headers)

    print(response.status_code, response.text)
    return response


def extract_phone_from_ultra_msg(data_from: str) -> str:
    at_position = data_from.find("@")
    return data_from[at_position - 10 : at_position]


def num_tokens_from_string(string: str, encoding_name: str) -> int:
    encoding = tiktoken.get_encoding("cl100k_base")

    if isinstance(string, str):
        tokens = len(encoding.encode(string))
    elif isinstance(string, list):
        tokens = sum(len(encoding.encode(t)) for t in string)

    return tokens


# NEW VERSION WITH REDIS + AUTO-REFRESH
def get_metadata(phone):
    """
    Gets metadata from Redis with auto-refresh of TTL
    If not exists, creates default metadata
    """
    # Clean phone number
    phone_clean = phone.replace("@s.whatsapp.net", "")
    if phone_clean.startswith("521"):
        phone_clean = phone_clean[3:]  # Remove 521 prefix

    key = f"metadata:{phone_clean}"

    try:
        # Try to get from Redis
        data = redis_metadata_client.get(key)

        if data:
            metadata = json.loads(data)

            # AUTO-REFRESH: Extend TTL every time it's accessed
            redis_metadata_client.expire(key, METADATA_TTL)

            print(
                f"Metadata recovered from Redis: {phone_clean} | Phase: {metadata.get('fase_actual')}"
            )
            return metadata

        # If not exists, create default metadata
        print(f"No metadata exists for {phone_clean}, creating new...")

    except Exception as e:
        print(f"Error getting metadata from Redis: {e}")

    # Default metadata
    default_metadata = {
        "fase_actual": 1,
        "problema_mencionado": False,
        "problema_identificado": False,
        "problema_detalle": "",
        "producto_presentado_tecnico": False,
        "metricas_mostradas": False,
        "opcion_elegida": None,
        "timestamp_fase_3a": None,
        "nombre_usuario": None,
        "created_at": datetime.now().isoformat(),
    }

    # Save initial metadata to Redis
    save_metadata(phone, default_metadata)
    return default_metadata


# NEW VERSION WITH REDIS
def save_metadata(phone, metadata):
    """
    Saves metadata to Redis with 24 hour TTL
    Also maintains backup in local file
    """
    # Clean phone number
    phone_clean = phone.replace("@s.whatsapp.net", "")
    if phone_clean.startswith("521"):
        phone_clean = phone_clean[3:]  # Remove 521 prefix

    key = f"metadata:{phone_clean}"

    # Add last update timestamp
    metadata["updated_at"] = datetime.now().isoformat()

    try:
        # Save to Redis with 24 hour TTL
        redis_metadata_client.set(key, json.dumps(metadata), ex=METADATA_TTL)

        print(
            f"Metadata saved to Redis: {phone_clean} | Phase: {metadata.get('fase_actual')} | TTL: 24h"
        )

    except Exception as e:
        print(f"ERROR saving metadata to Redis: {e}")

    # BACKUP: Also save to local file as fallback
    try:
        os.makedirs("metadata", exist_ok=True)
        metadata_file = f"metadata/metadata_{phone_clean}.json"
        with open(metadata_file, "w") as f:
            json.dump(metadata, f, indent=2)
        print(f"Local backup saved: {metadata_file}")
    except Exception as e:
        print(f"Error saving local backup: {e}")


def agregar_prompt(prefix, text, file="system_prompt.py"):
    variable_name = f"PROMPT_{prefix.upper()}"

    formatted_prompt = f'\n{variable_name} = """\n{text}\n"""\n'

    with open(file, "a", encoding="utf-8") as f:
        f.write(formatted_prompt)

    print(f"Prompt added: {variable_name}")


# UPDATED: Delete from Redis and file
def borrar_metadata(phone, metadata_dir="metadata"):
    """
    Deletes metadata from Redis AND local file
    """
    # Clean the number
    phone_clean = phone.replace("@s.whatsapp.net", "")
    if phone_clean.startswith("521"):
        phone_clean = phone_clean[3:]

    success = False

    # 1. Delete from Redis
    try:
        key = f"metadata:{phone_clean}"
        deleted = redis_metadata_client.delete(key)
        if deleted:
            print(f"Metadata deleted from Redis: {phone_clean}")
            success = True
        else:
            print(f"No metadata found in Redis for: {phone_clean}")
    except Exception as e:
        print(f"Error deleting from Redis: {e}")

    # 2. Delete local file (backup)
    possible_names = [
        f"metadata_{phone_clean}.json",
        f"metadata_521{phone_clean}.json",
    ]

    file_found = None
    for name in possible_names:
        filepath = os.path.join(metadata_dir, name)
        if os.path.exists(filepath):
            file_found = filepath
            break

    if file_found:
        try:
            os.remove(file_found)
            print(f"Local file deleted: {file_found}")
            success = True
        except Exception as e:
            print(f"Error deleting file: {e}")
    else:
        print(f"No local file found for: {phone_clean}")

    return success


if __name__ == "__main__":
    # agregar_prompt(
    #     prefijo="TEST_1",
    #     texto="""
    #     INSTRUCCIONES PARA SALUDO INICIAL
    #     Tu objetivo: Saludar + preguntar por el problema
    #     ...
    #     """
    # )
    # export_logs_to_txt(
    #     # phone_number="5513805760",
    #     phone_number="9765455060",
    #     # phone_number="9095535860",
    #     agent_name="Agrobotanix",
    #     output_dir="logs_exports"
    # )
    print("Done")
