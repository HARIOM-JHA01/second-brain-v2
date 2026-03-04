from datetime import datetime
import json
import os
import time
import redis
from dotenv import load_dotenv

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
    is_english,
)
from src.agente_rolplay.analytics_logger import log_chat_interaction
from src.agente_rolplay.supabase_storage import upload_file as upload_to_supabase
from src.agente_rolplay.cloudinary_storage import upload_file_to_cloudinary
from src.agente_rolplay.twilio_client import extract_phone_from_twilio

load_dotenv(override=True)

redis_host = os.getenv("REDIS_HOST")
redis_port = os.getenv("REDIS_PORT")
redis_password = os.getenv("REDIS_PASSWORD")

VOICE_NOTES_ENABLED = os.getenv("VOICE_NOTES_ENABLED", "false").lower() == "true"

r = redis.Redis(
    host=redis_host,
    port=redis_port,
    decode_responses=True,
    username="default",
    password=redis_password,
)


def process_incoming_messages_functional(form_data, redis_client=r):
    print("TWILIO FORM DATA:", form_data)
    TEMP_DIR = "./temp_uploads"
    os.makedirs(TEMP_DIR, exist_ok=True)

    from_number = form_data.get("From", "")
    to_number = form_data.get("To", "")
    body = form_data.get("Body", "")
    message_sid = form_data.get("MessageSid", "")
    num_media = int(form_data.get("NumMedia", 0))

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
            from audio_worker import process_audio_job

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

        expected_name_key = f"doc_nombre:{phone_number}"
        expected_type_key = f"doc_tipo:{phone_number}"

        desired_name = redis_client.get(expected_name_key)
        desired_type = redis_client.get(expected_type_key)

        if desired_name and desired_type:
            base_name = desired_name
            extension = desired_type
            print(f"Using user name: {base_name}.{extension}")

            redis_client.delete(expected_name_key)
            redis_client.delete(expected_type_key)
        else:
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_name = f"document_{phone_number}_{timestamp_str}"

            extensions = {
                "application/pdf": "pdf",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
                "application/vnd.openxmlformats-officedocument.presentationml.presentation": "pptx",
                "image/jpeg": "jpg",
                "image/png": "png",
            }

            extension = extensions.get(media_content_type, "bin")

        send_twilio_message(
            from_number, f"Uploading '{base_name}.{extension}' to Google Drive..."
        )

        temp_path = download_document_from_twilio(
            media_url=media_url, file_name=base_name, file_type=extension
        )

        if not temp_path:
            send_twilio_message(
                from_number, "Sorry, there was an error downloading your document."
            )
            redis_client.set(dedup_key, "exists", ex=600)
            return "DocumentError"

        result = upload_to_supabase(
            local_file_path=temp_path,
            folder_id="1M0TmERmETfEM8flmzwGgfKC7IkrVZaoD",
        )

        try:
            os.remove(temp_path)
            print(f"Temporary file deleted: {temp_path}")
        except Exception:
            pass

        if result and result.get("success"):
            message = f"Document '{base_name}.{extension}' uploaded successfully!\n\n"
            message += f"Link: {result['web_view_link']}"

            send_twilio_message(from_number, message)

        else:
            error_message = result.get("error", "Unknown") if result else "Unknown"
            send_twilio_message(
                from_number, f"Error uploading to Drive: {error_message}"
            )

        redis_client.set(dedup_key, "exists", ex=600)
        return "DocumentProcessed"

    if message_type == "image":
        print(f"Image received: {media_url}")

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

        result = upload_to_supabase(
            local_file_path=temp_path,
        )

        try:
            os.remove(temp_path)
            print(f"Temporary file deleted: {temp_path}")
        except Exception:
            pass

        if result and result.get("success"):
            message = f"Image '{base_name}.{extension}' uploaded to Knowledge Base!\n"
            message += f"Link: {result['web_view_link']}"

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
        phone=phone_number,
        id_conversacion=id_conversacion,
        id_phone_number=id_phone_number,
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

    lang_key = f"user:lang:{phone_number}"
    stored_lang = redis_client.get(lang_key)
    current_lang = stored_lang if stored_lang else "es"

    if body and body.strip():
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
            from audio_worker import process_audio_job

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

        expected_name_key = f"doc_nombre:{phone_number}"
        expected_type_key = f"doc_tipo:{phone_number}"

        desired_name = redis_client.get(expected_name_key)
        desired_type = redis_client.get(expected_type_key)

        if desired_name and desired_type:
            base_name = desired_name
            extension = desired_type
            print(f"Using user name: {base_name}.{extension}")

            redis_client.delete(expected_name_key)
            redis_client.delete(expected_type_key)
        else:
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_name = f"document_{phone_number}_{timestamp_str}"

            extensions = {
                "application/pdf": "pdf",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
                "application/vnd.openxmlformats-officedocument.presentationml.presentation": "pptx",
                "image/jpeg": "jpg",
                "image/png": "png",
            }

            extension = extensions.get(media_content_type, "bin")

        send_twilio_message(
            from_number, f"Uploading '{base_name}.{extension}' to Google Drive..."
        )

        temp_path = download_document_from_twilio(
            media_url=media_url, file_name=base_name, file_type=extension
        )

        if not temp_path:
            send_twilio_message(
                from_number, "Sorry, there was an error downloading your document."
            )
            redis_client.set(dedup_key, "exists", ex=600)
            return "DocumentError"

        result = upload_to_supabase(
            ruta_archivo_local=temp_path,
            folder_id="1M0TmERmETfEM8flmzwGgfKC7IkrVZaoD",
        )

        qdrant_ok = False
        if result and result.get("success"):
            from src.agente_rolplay.tools import agregar_documento_a_qdrant

            qdrant_ok = agregar_documento_a_qdrant(
                file_id=result["file_id"],
                mime_type=media_content_type,
                nombre=f"{base_name}.{extension}",
                ruta=f"Second Brain/{base_name}.{extension}",
                ruta_temporal=temp_path,
            )

        try:
            os.remove(temp_path)
            print(f"Temporary file deleted: {temp_path}")
        except Exception:
            pass

        if result and result.get("success"):
            message = f"Document '{base_name}.{extension}' uploaded!\n"
            if qdrant_ok:
                message += "Already available for queries\n"
            message += f"Link: {result['web_view_link']}"

            send_twilio_message(from_number, message)
        else:
            error_message = result.get("error", "Unknown") if result else "Unknown"
            send_twilio_message(
                from_number, f"Error uploading to Drive: {error_message}"
            )

        redis_client.set(dedup_key, "exists", ex=600)
        return "DocumentProcessed"

    if message_type == "image":
        print(f"Image received: {media_url}")

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
