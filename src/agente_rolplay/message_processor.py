from datetime import datetime
import json
import os
import re
import time
import redis
from anthropic import Anthropic

from src.agente_rolplay.twilio_client import (
    send_twilio_message,
    download_document_from_twilio,
)
from src.agente_rolplay.roleplay_agent import responder_usuario
from src.agente_rolplay.chat_history_manager import (
    add_to_chat_history,
    get_chat_history,
    reset_chat_history,
)
from src.agente_rolplay.greeting_handler import (
    is_greeting,
    is_help,
    get_intro_message,
    get_capabilities_message,
    get_file_upload_message,
    is_english,
)
from src.agente_rolplay.analytics_logger import log_chat_interaction
from src.agente_rolplay.cloudinary_storage import upload_file_to_cloudinary
from src.agente_rolplay.twilio_client import extract_phone_from_twilio
from src.agente_rolplay.pinecone_client import upload_to_pinecone
from src.agente_rolplay.file_processor import (
    extract_text_from_file,
    get_file_extension,
    is_vectorizable,
    get_file_type_category,
)

from src.agente_rolplay.config import (
    ANTHROPIC_API_KEY,
    REDIS_HOST,
    REDIS_PASSWORD,
    REDIS_PORT,
    VOICE_NOTES_ENABLED,
)

r = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    decode_responses=True,
    username="default",
    password=REDIS_PASSWORD,
)


def is_knowledge_base_inventory_query(user_message: str) -> bool:
    """Return True when the user asks to count/list files in the knowledge base."""
    if not user_message:
        return False

    normalized = re.sub(r"[^a-z0-9áéíóúñü]+", " ", user_message.lower())
    normalized = " ".join(normalized.split())

    inventory_patterns = [
        "how many files",
        "number of files",
        "count files",
        "list files",
        "files in knowledge base",
        "knowledge base files",
        "cuantos archivos",
        "cuántos archivos",
        "numero de archivos",
        "número de archivos",
        "cantidad de archivos",
        "listar archivos",
        "archivos en knowledge base",
        "archivos del knowledge base",
        "knowledgebase files",
        "files in knowledgebase",
        "knowledgebase count",
        "cuantos archivos hay",
        "cuántos archivos hay",
        "how many documents",
        "number of documents",
        "count documents",
        "documents in knowledge base",
        "knowledge base documents",
        "knowledgebase documents",
        "documents in knowledgebase",
        "cuántos documentos",
        "cuantos documentos",
        "numero de documentos",
        "número de documentos",
        "documentos en knowledge base",
        "documentos del knowledge base",
    ]

    return any(pattern in normalized for pattern in inventory_patterns)


def get_knowledge_base_file_count(redis_client) -> int:
    """Get total files known in KB metadata store."""
    try:
        return int(redis_client.scard("all_uploaded_files"))
    except Exception:
        return 0


def get_knowledge_base_count_message(redis_client, lang: str) -> str:
    """Build user-facing KB count response."""
    count = get_knowledge_base_file_count(redis_client)
    if lang == "en":
        return f"There are currently {count} file(s) in the Knowledge Base."
    return f"Actualmente hay {count} archivo(s) en el Knowledge Base."


def detect_file_upload_intent(user_message: str, phone_number: str) -> bool:
    """
    Detect if user wants to upload a file using LLM.

    Returns True if intent is file upload, False otherwise.
    """
    if is_knowledge_base_inventory_query(user_message):
        return False

    try:
        client = Anthropic(api_key=ANTHROPIC_API_KEY)

        prompt = f"""Classify the user's message intent. 
Message: "{user_message}"

Reply with ONLY ONE WORD:
- "upload" if the user wants to upload, send, or share a file/document
- "other" for anything else (questions, greetings, general conversation)

Examples:
- "How many files are there in the Knowledge Base?" -> other
- "List files in the Knowledge Base" -> other
- "I want to upload a file" -> upload

Do not explain, just reply with one word."""

        response = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=10,
            messages=[{"role": "user", "content": prompt}],
        )

        intent = response.content[0].text.strip().lower()
        print(f"Detected intent: {intent} for message: {user_message[:50]}...")

        return intent == "upload"

    except Exception as e:
        print(f"Error detecting intent: {e}")
        fallback_keywords = [
            "upload",
            "subir",
            "enviar archivo",
            "send file",
            "compartir archivo",
            "share document",
            "mándame el archivo",
            "send me",
            "aquí está",
            "here is",
            "attached",
            "adjunto",
        ]
        user_lower = user_message.lower()
        return any(keyword in user_lower for keyword in fallback_keywords)


def check_filename_exists(filename: str, redis_client) -> bool:
    """Check if a filename already exists in our records."""
    all_files_key = "all_uploaded_files"
    return redis_client.sismember(all_files_key, filename)


def store_file_metadata(filename: str, metadata: dict, redis_client):
    """Store file metadata in Redis."""
    file_key = f"file_metadata:{filename}"
    redis_client.set(file_key, json.dumps(metadata), ex=86400 * 30)
    redis_client.sadd("all_uploaded_files", filename)


def store_image_metadata(
    phone_number: str,
    filename: str,
    cloudinary_url: str,
    redis_client,
):
    """Store image metadata so image uploads are counted in KB inventory."""
    metadata = {
        "filename": filename,
        "original_name": filename,
        "cloudinary_url": cloudinary_url,
        "uploaded_at": datetime.utcnow().isoformat() + "Z",
        "uploaded_by": phone_number,
        "file_category": "image",
        "vector_id": None,
        "vectorized": False,
    }
    store_file_metadata(filename, metadata, redis_client)


def handle_file_upload(
    from_number: str,
    phone_number: str,
    media_url: str,
    media_content_type: str,
    original_filename: str,
    redis_client,
    dedup_key: str,
):
    """
    Handle file upload: download, upload to Cloudinary, vectorize, store metadata.
    """
    extension = get_file_extension(media_content_type)
    if original_filename:
        filename = os.path.basename(original_filename).replace("/", "_")
        name_no_ext, ext_from_name = os.path.splitext(filename)
        if ext_from_name:
            base_name = name_no_ext
            extension = ext_from_name.lstrip(".").lower()
        else:
            base_name = name_no_ext
            filename = f"{base_name}.{extension}"
    else:
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = f"file_{phone_number}_{timestamp_str}"
        filename = f"{base_name}.{extension}"

    file_category = get_file_type_category(media_content_type)

    print(f"Processing file upload: {filename}")

    existing_file_key = f"pending_rename:{phone_number}"
    pending_rename = redis_client.get(existing_file_key)

    if pending_rename:
        filename = pending_rename
        base_name = os.path.splitext(filename)[0]
        extension = os.path.splitext(filename)[1][1:]
        redis_client.delete(existing_file_key)
        print(f"Using renamed file: {filename}")

    send_twilio_message(from_number, f"Uploading '{filename}'...")

    temp_path = download_document_from_twilio(
        media_url=media_url, file_name=base_name, file_type=extension
    )

    if not temp_path:
        send_twilio_message(
            from_number, "Sorry, there was an error downloading your file."
        )
        redis_client.set(dedup_key, "exists", ex=600)
        return "DownloadError"

    # If Twilio returns a real filename in headers, keep metadata/user messaging aligned.
    downloaded_name = os.path.basename(temp_path)
    if downloaded_name and downloaded_name != filename:
        filename = downloaded_name
        base_name, detected_ext = os.path.splitext(downloaded_name)
        if detected_ext:
            extension = detected_ext.lstrip(".").lower()

    upload_result = upload_file_to_cloudinary(temp_path, folder="knowledgebase")

    vector_id = None
    vectorized = False

    if upload_result and upload_result.get("success"):
        if is_vectorizable(media_content_type):
            print(f"Vectorizing file: {filename}")
            extract_result = extract_text_from_file(temp_path, media_content_type)

            if extract_result.get("success") and extract_result.get("can_vectorize"):
                pinecone_result = upload_to_pinecone(
                    text=extract_result["text"],
                    filename=filename,
                    file_type=extract_result["file_type"],
                    metadata={
                        "uploaded_by": phone_number,
                        "cloudinary_url": upload_result.get("secure_url"),
                    },
                )

                if pinecone_result.get("success"):
                    vector_id = pinecone_result.get("vector_id")
                    vectorized = True
                    print(f"File vectorized successfully: {vector_id}")
        else:
            print(f"File type {media_content_type} is not vectorizable")

    try:
        os.remove(temp_path)
        print(f"Temporary file deleted: {temp_path}")
    except Exception:
        pass

    if upload_result and upload_result.get("success"):
        metadata = {
            "filename": filename,
            "original_name": filename,
            "cloudinary_url": upload_result.get("secure_url"),
            "uploaded_at": datetime.utcnow().isoformat() + "Z",
            "uploaded_by": phone_number,
            "file_category": file_category,
            "vector_id": vector_id,
            "vectorized": vectorized,
        }

        store_file_metadata(filename, metadata, redis_client)
        redis_client.set(f"last_uploaded_file:{phone_number}", filename, ex=86400 * 7)

        message = f"File '{filename}' uploaded successfully!\n\n"
        if vectorized:
            message += "✅ Content indexed and available for queries"
        else:
            message += "📎 File stored (not searchable as text)"

        send_twilio_message(from_number, message)
    else:
        error_msg = (
            upload_result.get("error", "Unknown error") if upload_result else "Unknown"
        )
        send_twilio_message(from_number, f"Error uploading file: {error_msg}")

    redis_client.set(dedup_key, "exists", ex=600)
    return "FileProcessed"


def ask_about_existing_file(
    filename: str, from_number: str, redis_client, phone_number: str
):
    """Ask user what to do with existing file."""
    message = f"File '{filename}' already exists. What would you like to do?\n\n"
    message += "1. Send 'update' to replace the existing file\n"
    message += "2. Send a new name to rename this file"

    send_twilio_message(from_number, message)

    redis_client.set(f"pending_file_action:{phone_number}", filename, ex=300)


def process_incoming_messages_functional(form_data, redis_client=r):
    print("TWILIO FORM DATA:", form_data)
    TEMP_DIR = "./temp_uploads"
    os.makedirs(TEMP_DIR, exist_ok=True)

    from_number = form_data.get("From", "")
    to_number = form_data.get("To", "")
    body = form_data.get("Body", "")
    message_sid = form_data.get("MessageSid", "")
    num_media = int(form_data.get("NumMedia", 0))
    original_filename = (
        form_data.get("MediaFileName0")
        or form_data.get("MediaFilename0")
        or form_data.get("Filename")
        or ""
    ).strip()

    phone_number = extract_phone_from_twilio(from_number)
    print(f"PHONE NUMBER: {phone_number}")

    if not phone_number:
        print("Could not extract phone number")
        return "NoCommand"

    timestamp = int(time.time())

    dedup_key = f"msg:twilio:{message_sid}"

    if redis_client.exists(dedup_key):
        print(f"Duplicate message detected: {dedup_key}")
        return "NoCommand"

    print(f"Processing new message: {dedup_key}")

    file_upload_pending_key = f"file_upload_pending:{phone_number}"
    current_lang = "en" if is_english(body) else "es"

    if body and body.strip() and num_media == 0:
        if is_knowledge_base_inventory_query(body):
            response_text = get_knowledge_base_count_message(redis_client, "en")
            send_twilio_message(from_number, response_text)
            redis_client.set(dedup_key, "exists", ex=600)
            return "Success"

        if redis_client.get(file_upload_pending_key) == "pending":
            if is_knowledge_base_inventory_query(body):
                redis_client.delete(file_upload_pending_key)
            else:
                send_twilio_message(
                    from_number, "Please send me the file you want to upload."
                )
                redis_client.set(dedup_key, "exists", ex=600)
                return "Success"

        upload_intent = detect_file_upload_intent(body, phone_number)
        if upload_intent:
            redis_client.set(file_upload_pending_key, "pending", ex=600)
            send_twilio_message(
                from_number, "Please send me the file you want to upload."
            )
            redis_client.set(dedup_key, "exists", ex=600)
            return "Success"

    message_type = "text"
    media_url = ""
    media_content_type = ""

    if num_media > 0:
        media_url = form_data.get("MediaUrl0", "")
        media_content_type = form_data.get("MediaContentType0", "")

        if "image" in media_content_type:
            message_type = "image"
        elif "audio" in media_content_type or "ogg" in media_content_type:
            message_type = "audio"
        elif "video" in media_content_type:
            message_type = "video"
        elif "application" in media_content_type or "pdf" in media_content_type:
            message_type = "document"
        else:
            message_type = "media"

        print(f"Media detected: {message_type} - {media_url}")

    data = {
        "id": message_sid,
        "from": from_number,
        "to": to_number,
        "body": body,
        "fromMe": False,
        "type": message_type,
        "pushName": form_data.get("ProfileName", ""),
        "timestamp": timestamp,
        "media": media_url,
        "media_content_type": media_content_type,
    }

    print("PROCESSED DATA:", data)

    if body and "borrar memoria" in body.lower():
        print(f"Executing memory deletion for: {phone_number}")
        reset_chat_history(phone_number)
        result = send_twilio_message(from_number, "Your memory has been deleted.")
        if result.get("success", False):
            redis_client.set(dedup_key, "exists", ex=600)
            print(f"Memory deletion processed: {dedup_key}")
        return result

    if message_type == "audio":
        if not VOICE_NOTES_ENABLED:
            print(f"VOICE_NOTES_ENABLED=false, ignoring audio for: {phone_number}")
            send_twilio_message(
                from_number,
                "Voice notes are not enabled yet. Please send a text message.",
            )
            return "FeatureDisabled"

        audio_dedup_key = f"audio_queued:{phone_number}:{timestamp}"
        if redis_client.exists(audio_dedup_key):
            print(f"Audio already queued previously: {audio_dedup_key}")
            return "NoCommand"

        redis_client.set(audio_dedup_key, "queued", ex=300)

        print("Sending immediate ACK to user...")
        ack_result = send_twilio_message(
            from_number,
            "I received your voice note. I'm transcribing it, give me a few seconds...",
        )

        if not ack_result.get("success", False):
            print(f"Could not send ACK: {ack_result.get('error')}")
            return "ACKFailed"

        id_phone_number = f"fp-idPhone:{phone_number}"
        id_conversacion = (
            f"fp-idPhone:{phone_number}_{datetime.now().strftime('%Y-%m-%d_%H:%M')}"
        )

        if not redis_client.exists(id_phone_number):
            user_data = {"Usuario": "", "Telefono": phone_number}
            redis_client.set(id_phone_number, json.dumps(user_data), ex=600)
        else:
            user_data = json.loads(redis_client.get(id_phone_number))

        audio_job = {
            "media_url": media_url,
            "phone_number": phone_number,
            "from": from_number,
            "id_conversacion": id_conversacion,
            "timestamp": timestamp,
            "user_data": user_data,
            "message_sid": message_sid,
        }

        try:
            from src.agente_rolplay.audio_worker import process_audio_job

            result = process_audio_job.apply_async(
                args=[audio_job],
                queue="audio",
                expires=3600,
            )
            print(f"Audio queued to Celery: {result.id}")
        except Exception as e:
            print(f"Error enqueueing to Celery: {e}, using Redis fallback")
            redis_client.lpush("audio_queue", json.dumps(audio_job))

        return "AudioQueued"

    if message_type == "document":
        print(f"Document received: {media_url}")
        redis_client.delete(file_upload_pending_key)

        return handle_file_upload(
            from_number=from_number,
            phone_number=phone_number,
            media_url=media_url,
            media_content_type=media_content_type,
            original_filename=original_filename,
            redis_client=redis_client,
            dedup_key=dedup_key,
        )

    if message_type == "image":
        print(f"Image received: {media_url}")
        redis_client.delete(file_upload_pending_key)

        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = f"image_{phone_number}_{timestamp_str}"

        extensions = {
            "image/jpeg": "jpg",
            "image/png": "png",
            "image/gif": "gif",
            "image/webp": "webp",
        }
        extension = extensions.get(media_content_type, "jpg")

        send_twilio_message(from_number, "Uploading image to Knowledge Base...")

        temp_path = download_document_from_twilio(
            media_url=media_url, file_name=base_name, file_type=extension
        )

        if not temp_path:
            send_twilio_message(
                from_number, "Sorry, there was an error downloading your image."
            )
            redis_client.set(dedup_key, "exists", ex=600)
            return "ImageError"

        result = upload_file_to_cloudinary(temp_path, folder="knowledgebase")

        try:
            os.remove(temp_path)
            print(f"Temporary file deleted: {temp_path}")
        except Exception:
            pass

        if result and result.get("success"):
            filename = f"{base_name}.{extension}"
            store_image_metadata(
                phone_number=phone_number,
                filename=filename,
                cloudinary_url=result.get("secure_url"),
                redis_client=redis_client,
            )
            redis_client.set(
                f"last_uploaded_file:{phone_number}", filename, ex=86400 * 7
            )
            message = f"Image '{base_name}.{extension}' uploaded to Knowledge Base!\n"
            message += f"Link: {result['secure_url']}"

            send_twilio_message(from_number, message)
        else:
            error_message = result.get("error", "Unknown") if result else "Unknown"
            send_twilio_message(from_number, f"Error uploading image: {error_message}")

        redis_client.set(dedup_key, "exists", ex=600)
        return "ImageProcessed"

    id_phone_number = f"fp-idPhone:{phone_number}"
    id_conversacion = (
        f"fp-idPhone:{phone_number}_{datetime.now().strftime('%Y-%m-%d_%H:%M')}"
    )

    if not redis_client.exists(id_phone_number):
        user_data = {"Usuario": "", "Telefono": phone_number}
        data["user_data"] = user_data
        redis_client.set(id_phone_number, json.dumps(user_data), ex=600)
    else:
        print(id_phone_number)
        data["user_data"] = json.loads(redis_client.get(id_phone_number))
        print(data["user_data"])
    data["last_uploaded_filename"] = redis_client.get(
        f"last_uploaded_file:{phone_number}"
    )

    chat_history_id = f"fp-chatHistory:{from_number}"

    user_conversation_dict = {
        "session_id": str(chat_history_id),
        "phone_number": phone_number,
        "message": body,
        "role": "user",
        "type": message_type,
    }

    try:
        print("USER CONVERSATION DICT", user_conversation_dict)
    except Exception:
        print("ERROR PRINTING USER CONVERSATION DICT")

    messages = get_chat_history(chat_history_id, phone=phone_number)
    answer_data = responder_usuario(
        messages,
        data,
        telefono=phone_number,
        id_conversacion=id_conversacion,
        id_phone_number=id_phone_number,
        response_language=current_lang,
    )
    print("--------------------------")
    print("ANSWER DATA", answer_data)
    print("--------------------------")

    assistant_conversation_dict = {
        "session_id": str(chat_history_id),
        "phone_number": phone_number,
        "message": str(answer_data["answer"]),
        "role": "assistant",
        "type": "text",
    }

    try:
        print("ASSISTANT CONVERSATION DICT", assistant_conversation_dict)
    except Exception:
        print("ERROR PRINTING ASSISTANT CONVERSATION DICT")

    send_result = send_twilio_message(from_number, str(answer_data["answer"]))

    if not send_result.get("success", False):
        print(
            f"WARNING: Message not sent. Error: {send_result.get('error', 'Unknown')}"
        )
        return "SendError"

    redis_client.set(dedup_key, "exists", ex=600)
    print(f"Message marked as processed: {dedup_key}")

    add_to_chat_history(chat_history_id, body, "user", phone_number)
    add_to_chat_history(
        chat_history_id, answer_data["answer"], "assistant", phone_number
    )

    print("Processing completed successfully.")
    return "Success"


def process_incoming_messages(form_data, redis_client=r):
    print("TWILIO FORM DATA:", form_data)
    TEMP_DIR = "./temp_uploads"
    os.makedirs(TEMP_DIR, exist_ok=True)

    from_number = form_data.get("From", "")
    to_number = form_data.get("To", "")
    body = form_data.get("Body", "")
    message_sid = form_data.get("MessageSid", "")
    num_media = int(form_data.get("NumMedia", 0))
    original_filename = (
        form_data.get("MediaFileName0")
        or form_data.get("MediaFilename0")
        or form_data.get("Filename")
        or ""
    ).strip()

    phone_number = extract_phone_from_twilio(from_number)
    print(f"PHONE NUMBER: {phone_number}")

    if not phone_number:
        print("Could not extract phone number")
        return "NoCommand"

    try:
        from src.agente_rolplay.whatsapp_auth import (
            lookup_whatsapp_user,
            check_query_permission,
            BLOCKED_RESPONSE,
        )

        whatsapp_user = lookup_whatsapp_user(phone_number)
        if whatsapp_user is None:
            print(f"Unauthorized WhatsApp user: {phone_number}")
            send_twilio_message(
                from_number,
                "You don't have access. Please contact your organization administrator.",
            )
            return "Unauthorized"

        print(
            f"WhatsApp user: {whatsapp_user.get('username')} - Role: {whatsapp_user.get('role_name')} - Org: {whatsapp_user.get('org_name')}"
        )

        redis_client.set(
            f"whatsapp_user:{phone_number}", json.dumps(whatsapp_user), ex=86400
        )
    except Exception as e:
        print(f"Error checking WhatsApp user: {e}")

    timestamp = int(time.time())

    dedup_key = f"msg:twilio:{message_sid}"

    if redis_client.exists(dedup_key):
        print(f"Duplicate message detected: {dedup_key}")
        return "NoCommand"

    print(f"Processing new message: {dedup_key}")

    lang_key = f"user:lang:{phone_number}"
    stored_lang = redis_client.get(lang_key)
    current_lang = stored_lang if stored_lang else "es"

    if body and body.strip():
        if is_english(body):
            current_lang = "en"
            redis_client.set(lang_key, "en", ex=86400)

        if is_knowledge_base_inventory_query(body):
            response_text = get_knowledge_base_count_message(redis_client, current_lang)
            send_result = send_twilio_message(from_number, response_text)
            if send_result.get("success", False):
                log_chat_interaction(
                    phone_number=phone_number,
                    user_message=body,
                    bot_response=response_text,
                    message_type="kb_inventory",
                    language=current_lang,
                )
                redis_client.set(dedup_key, "exists", ex=600)
                return "Success"

        is_greet = is_greeting(body)
        is_help_req = is_help(body)

        if is_greet or is_help_req:
            if is_english(body):
                current_lang = "en"
                redis_client.set(lang_key, "en", ex=86400)

            if is_greet:
                response_text = get_intro_message(current_lang)
                msg_type = "greeting"
            else:
                response_text = get_capabilities_message(current_lang)
                msg_type = "help"

            send_result = send_twilio_message(from_number, response_text)

            if send_result.get("success", False):
                log_chat_interaction(
                    phone_number=phone_number,
                    user_message=body,
                    bot_response=response_text,
                    message_type=msg_type,
                    language=current_lang,
                )
                redis_client.set(dedup_key, "exists", ex=600)
                print(f"Greeting/Help response sent: {msg_type}")
                return "Success"
            else:
                print(f"Failed to send greeting response: {send_result.get('error')}")

        pending_action_key = f"pending_file_action:{phone_number}"
        pending_rename_key = f"pending_rename:{phone_number}"

        if redis_client.exists(pending_action_key):
            existing_filename = redis_client.get(pending_action_key)
            user_response = body.strip().lower()

            if user_response == "update":
                redis_client.delete(pending_action_key)
                redis_client.set(
                    f"pending_file_action:{phone_number}:action", "update", ex=300
                )
                send_twilio_message(
                    from_number, "OK, send me the new file to replace the existing one."
                )
                redis_client.set(dedup_key, "exists", ex=600)
                return "Success"
            elif user_response == "rename":
                redis_client.delete(pending_action_key)
                send_twilio_message(
                    from_number, "OK, what name would you like to give this file?"
                )
                redis_client.set(pending_rename_key, "waiting_for_name", ex=300)
                redis_client.set(dedup_key, "exists", ex=600)
                return "Success"
            else:
                send_twilio_message(
                    from_number, "Please respond with 'update' or 'rename'."
                )
                redis_client.set(dedup_key, "exists", ex=600)
                return "Success"

        if redis_client.get(pending_rename_key) == "waiting_for_name":
            new_filename = body.strip()
            if "." not in new_filename:
                send_twilio_message(
                    from_number, "Please include the file extension (e.g., report.pdf)"
                )
                redis_client.set(dedup_key, "exists", ex=600)
                return "Success"

            redis_client.set(f"pending_rename:{phone_number}", new_filename, ex=300)
            redis_client.delete(pending_rename_key)
            send_twilio_message(
                from_number, f"Got it! Now send me the file '{new_filename}'."
            )
            redis_client.set(dedup_key, "exists", ex=600)
            return "Success"

        file_upload_pending_key = f"file_upload_pending:{phone_number}"
        if num_media == 0:
            if redis_client.get(file_upload_pending_key) == "pending":
                if is_knowledge_base_inventory_query(body):
                    redis_client.delete(file_upload_pending_key)
                else:
                    upload_msg = get_file_upload_message(current_lang)
                    send_twilio_message(from_number, upload_msg)
                    redis_client.set(dedup_key, "exists", ex=600)
                    return "Success"

            upload_intent = detect_file_upload_intent(body, phone_number)
            if upload_intent:
                redis_client.set(file_upload_pending_key, "pending", ex=600)
                upload_msg = get_file_upload_message(current_lang)
                send_twilio_message(from_number, upload_msg)
                redis_client.set(dedup_key, "exists", ex=600)
                return "Success"

    message_type = "text"
    media_url = ""
    media_content_type = ""

    if num_media > 0:
        media_url = form_data.get("MediaUrl0", "")
        media_content_type = form_data.get("MediaContentType0", "")

        if "image" in media_content_type:
            message_type = "image"
        elif "audio" in media_content_type or "ogg" in media_content_type:
            message_type = "audio"
        elif "video" in media_content_type:
            message_type = "video"
        elif "application" in media_content_type or "pdf" in media_content_type:
            message_type = "document"
        else:
            message_type = "media"

        print(f"Media detected: {message_type} - {media_url}")

    data = {
        "id": message_sid,
        "from": from_number,
        "to": to_number,
        "body": body,
        "fromMe": False,
        "type": message_type,
        "pushName": form_data.get("ProfileName", ""),
        "timestamp": timestamp,
        "media": media_url,
        "media_content_type": media_content_type,
    }

    print("PROCESSED DATA:", data)

    if body and "borrar memoria" in body.lower():
        print(f"Executing memory deletion for: {phone_number}")
        reset_chat_history(phone_number)
        result = send_twilio_message(from_number, "Your memory has been deleted.")
        if result.get("success", False):
            redis_client.set(dedup_key, "exists", ex=600)
            print(f"Memory deletion processed: {dedup_key}")
        return result

    id_phone_number = f"fp-idPhone:{phone_number}"
    id_conversacion = (
        f"fp-idPhone:{phone_number}_{datetime.now().strftime('%Y-%m-%d_%H:%M')}"
    )

    if message_type == "audio":
        if not VOICE_NOTES_ENABLED:
            print(f"VOICE_NOTES_ENABLED=false, ignoring audio for: {phone_number}")
            send_twilio_message(
                from_number,
                "Voice notes are not enabled yet. Please send a text message.",
            )
            return "FeatureDisabled"

        audio_dedup_key = f"audio_queued:{phone_number}:{timestamp}"
        if redis_client.exists(audio_dedup_key):
            print(f"Audio already queued previously: {audio_dedup_key}")
            return "NoCommand"

        redis_client.set(audio_dedup_key, "queued", ex=300)

        print("Sending immediate ACK to user...")
        ack_result = send_twilio_message(
            from_number,
            "I received your voice note. I'm transcribing it, give me a few seconds...",
        )

        if not ack_result.get("success", False):
            print(f"Could not send ACK: {ack_result.get('error')}")
            return "ACKFailed"

        if not redis_client.exists(id_phone_number):
            user_data = {"Usuario": "", "Telefono": phone_number}
            redis_client.set(id_phone_number, json.dumps(user_data), ex=600)
        else:
            user_data = json.loads(redis_client.get(id_phone_number))

        audio_job = {
            "media_url": media_url,
            "phone_number": phone_number,
            "from": from_number,
            "id_conversacion": id_conversacion,
            "timestamp": timestamp,
            "user_data": user_data,
            "message_sid": message_sid,
        }

        try:
            from src.agente_rolplay.audio_worker import process_audio_job

            result = process_audio_job.apply_async(
                args=[audio_job],
                queue="audio",
                expires=3600,
            )
            print(f"Audio queued to Celery: {result.id}")
        except Exception as e:
            print(f"Error enqueueing to Celery: {e}, using Redis fallback")
            redis_client.lpush("audio_queue", json.dumps(audio_job))

        return "AudioQueued"

    if message_type == "document":
        print(f"Document received: {media_url}")
        redis_client.delete(f"file_upload_pending:{phone_number}")

        return handle_file_upload(
            from_number=from_number,
            phone_number=phone_number,
            media_url=media_url,
            media_content_type=media_content_type,
            original_filename=original_filename,
            redis_client=redis_client,
            dedup_key=dedup_key,
        )

    if message_type == "image":
        print(f"Image received: {media_url}")
        redis_client.delete(f"file_upload_pending:{phone_number}")

        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = f"image_{phone_number}_{timestamp_str}"

        extensions = {
            "image/jpeg": "jpg",
            "image/png": "png",
            "image/gif": "gif",
            "image/webp": "webp",
        }
        extension = extensions.get(media_content_type, "jpg")

        send_twilio_message(from_number, "Uploading image to Knowledge Base...")

        temp_path = download_document_from_twilio(
            media_url=media_url, file_name=base_name, file_type=extension
        )

        if not temp_path:
            send_twilio_message(
                from_number, "Sorry, there was an error downloading your image."
            )
            redis_client.set(dedup_key, "exists", ex=600)
            return "ImageError"

        result = upload_file_to_cloudinary(temp_path, folder="knowledgebase")

        try:
            os.remove(temp_path)
            print(f"Temporary file deleted: {temp_path}")
        except Exception:
            pass

        if result and result.get("success"):
            filename = f"{base_name}.{extension}"
            store_image_metadata(
                phone_number=phone_number,
                filename=filename,
                cloudinary_url=result.get("secure_url"),
                redis_client=redis_client,
            )
            redis_client.set(
                f"last_uploaded_file:{phone_number}", filename, ex=86400 * 7
            )
            message = "Image uploaded to Knowledge Base! ✅"

            send_twilio_message(from_number, message)
        else:
            error_message = result.get("error", "Unknown") if result else "Unknown"
            send_twilio_message(from_number, f"Error uploading image: {error_message}")

        redis_client.set(dedup_key, "exists", ex=600)
        return "ImageProcessed"

    if not redis_client.exists(id_phone_number):
        user_data = {"Usuario": "", "Telefono": phone_number}
        data["user_data"] = user_data
        redis_client.set(id_phone_number, json.dumps(user_data), ex=600)
    else:
        print(id_phone_number)
        data["user_data"] = json.loads(redis_client.get(id_phone_number))
        print(data["user_data"])
    data["last_uploaded_filename"] = redis_client.get(
        f"last_uploaded_file:{phone_number}"
    )

    chat_history_id = f"fp-chatHistory:{from_number}"

    user_conversation_dict = {
        "session_id": str(chat_history_id),
        "phone_number": phone_number,
        "message": body,
        "role": "user",
        "type": message_type,
    }

    try:
        print("USER CONVERSATION DICT", user_conversation_dict)
    except Exception:
        print("ERROR PRINTING USER CONVERSATION DICT")

    permission_check_result = None
    try:
        from src.agente_rolplay.whatsapp_auth import (
            check_query_permission,
            BLOCKED_RESPONSE,
        )

        whatsapp_user_data = redis_client.get(f"whatsapp_user:{phone_number}")
        if whatsapp_user_data:
            whatsapp_user = json.loads(whatsapp_user_data)
            if body and body.strip():
                permission_check_result = check_query_permission(whatsapp_user, body)

                if not permission_check_result.get("allowed"):
                    print(
                        f"Query blocked for {phone_number}: {permission_check_result.get('query_type')}"
                    )
                    send_twilio_message(from_number, BLOCKED_RESPONSE)
                    redis_client.set(dedup_key, "exists", ex=600)
                    return "Blocked"
    except Exception as e:
        print(f"Error checking permissions: {e}")

    messages = get_chat_history(chat_history_id, phone=phone_number)
    answer_data = responder_usuario(
        messages,
        data,
        telefono=phone_number,
        id_conversacion=id_conversacion,
        id_phone_number=id_phone_number,
        response_language=current_lang,
    )
    print("--------------------------")
    print("ANSWER DATA", answer_data)
    print("--------------------------")

    assistant_conversation_dict = {
        "session_id": str(chat_history_id),
        "phone_number": phone_number,
        "message": str(answer_data["answer"]),
        "role": "assistant",
        "type": "text",
    }

    try:
        print("ASSISTANT CONVERSATION DICT", assistant_conversation_dict)
    except Exception:
        print("ERROR PRINTING ASSISTANT CONVERSATION DICT")

    answer_text = str(answer_data["answer"])

    MAX_LENGTH = 1520

    if len(answer_text) > MAX_LENGTH:
        answer_text = (
            answer_text[:MAX_LENGTH]
            + "\n\n... (truncated response)\nAsk a more specific question for details."
        )
        print(
            f"Response truncated from {len(answer_data['answer'])} to {MAX_LENGTH} characters"
        )

    send_result = send_twilio_message(
        from_number,
        answer_text,
    )

    if not send_result.get("success", False):
        print(
            f"WARNING: Message not sent. Error: {send_result.get('error', 'Unknown')}"
        )
        return "SendError"

    log_chat_interaction(
        phone_number=phone_number,
        user_message=body,
        bot_response=answer_text,
        message_type="query",
        language=current_lang,
    )

    redis_client.set(dedup_key, "exists", ex=600)
    print(f"Message marked as processed: {dedup_key}")

    add_to_chat_history(chat_history_id, body, "user", phone_number)
    add_to_chat_history(
        chat_history_id, answer_data["answer"], "assistant", phone_number
    )

    print("Processing completed successfully.")
    return "Success"
