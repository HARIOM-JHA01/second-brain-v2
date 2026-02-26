# python3 process_messages.py

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
from datetime import datetime
from dotenv import load_dotenv
from src.agente_rolplay.supabase_storage import upload_file as upload_to_supabase
from src.agente_rolplay.cloudinary_storage import upload_file_to_cloudinary
from src.agente_rolplay.helpers import borrar_metadata
from twilio.rest import Client

import json
import os
import redis
import requests
import time

load_dotenv(override=True)

# VOICE NOTES FEATURE FLAG
VOICE_NOTES_ENABLED = os.getenv("VOICE_NOTES_ENABLED", "false").lower() == "true"

# Twilio credentials
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_SANDBOX_NUMBER = os.getenv("TWILIO_SANDBOX_NUMBER")

# Redis
redis_host = os.getenv("REDIS_HOST")
redis_port = os.getenv("REDIS_PORT")
redis_password = os.getenv("REDIS_PASSWORD")

# Twilio client
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# Redis client
r = redis.Redis(
    host=redis_host,
    port=redis_port,
    decode_responses=True,
    username="default",
    password=redis_password,
)


def download_document_from_twilio(media_url, file_name, file_type):
    """
    Download a document from Twilio and save it temporarily

    Args:
        media_url (str): URL of the file in Twilio
        file_name (str): Desired name for the file
        file_type (str): Extension (xlsx, pdf, docx, etc)

    Returns:
        str: Path to temporary file or None if failed
    """
    try:
        print(f"Downloading from Twilio: {media_url}")

        # Download with Twilio authentication
        response = requests.get(
            media_url, auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN), timeout=30
        )

        if response.status_code != 200:
            print(f"Error downloading: Status {response.status_code}")
            return None

        # Create temp directory if it doesn't exist
        temp_dir = "./temp_uploads"
        os.makedirs(temp_dir, exist_ok=True)

        # Full file name
        full_name = f"{file_name}.{file_type}"
        temp_path = os.path.join(temp_dir, full_name)

        # Save file
        with open(temp_path, "wb") as f:
            f.write(response.content)

        size_kb = len(response.content) / 1024
        print(f"File downloaded: {temp_path} ({size_kb:.2f} KB)")

        return temp_path

    except Exception as e:
        print(f"Error downloading file: {e}")
        return None


def send_twilio_message(phone, text, max_retries=3):
    """
    Send WhatsApp message using Twilio
    phone must be in format: whatsapp:+5215512345678
    """
    for attempt in range(max_retries):
        try:
            print(
                f"Sending message with Twilio (attempt {attempt + 1}/{max_retries}): {text[:50]}..."
            )
            print(f"From: {TWILIO_SANDBOX_NUMBER}")  # For debug
            print(f"To: {phone}")  # For debug

            message = twilio_client.messages.create(
                from_=TWILIO_SANDBOX_NUMBER,  # Use global variable, NOT parameter
                body=text,
                to=phone,
            )

            print(f"Message sent successfully. SID: {message.sid}")
            return {
                "success": True,
                "response": {"sid": message.sid, "status": message.status},
            }

        except Exception as e:
            print(f"ERROR ON ATTEMPT {attempt + 1}/{max_retries}: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(3 * (attempt + 1))
                continue
            else:
                print(f"FINAL ERROR after {max_retries} attempts: {str(e)}")
                return {"success": False, "error": str(e)}

    return {"success": False, "error": "Failed after all retries"}


def send_twilio_document(phone, document_url, caption=""):
    """
    Send a document using Twilio
    """
    try:
        print(f"Sending document: {document_url}")

        message = twilio_client.messages.create(
            from_=TWILIO_SANDBOX_NUMBER,  # Global variable
            body=caption if caption else "Here is your document",
            media_url=[document_url],
            to=phone,
        )

        print(f"Document sent. SID: {message.sid}")
        return {"success": True, "response": {"sid": message.sid}}

    except Exception as e:
        print(f"ERROR sending document: {str(e)}")
        return {"success": False, "error": str(e)}


def extract_phone_from_twilio(from_field):
    """
    Extract phone number from Twilio format
    Input: whatsapp:+5215512345678
    Output: 5215512345678
    """
    if not from_field:
        return ""

    # Remove whatsapp: prefix
    phone = from_field.replace("whatsapp:", "")
    # Remove + symbol
    phone = phone.replace("+", "")

    return phone


def process_incoming_messages_functional(form_data, redis_client=r):
    """
    Process incoming Twilio WhatsApp messages
    form_data comes as dictionary with Twilio fields
    """
    print("TWILIO FORM DATA:", form_data)
    TEMP_DIR = "./temp_uploads"
    os.makedirs(TEMP_DIR, exist_ok=True)

    # Extract important fields from Twilio
    from_number = form_data.get("From", "")  # whatsapp:+5215512345678
    to_number = form_data.get("To", "")  # whatsapp:+14155238886
    body = form_data.get("Body", "")
    message_sid = form_data.get("MessageSid", "")
    num_media = int(form_data.get("NumMedia", 0))

    # Extract clean phone number
    phone_number = extract_phone_from_twilio(from_number)
    print(f"PHONE NUMBER: {phone_number}")

    if not phone_number:
        print("Could not extract phone number")
        return "NoCommand"

    # Current timestamp (Twilio doesn't send timestamp in form data)
    timestamp = int(time.time())

    # DEDUPLICATION BY PHONE + MESSAGE_SID
    dedup_key = f"msg:twilio:{message_sid}"

    if redis_client.exists(dedup_key):
        print(f"Duplicate message detected: {dedup_key}")
        return "NoCommand"

    print(f"Processing new message: {dedup_key}")

    # Determine message type
    message_type = "text"
    media_url = ""
    media_content_type = ""

    if num_media > 0:
        media_url = form_data.get("MediaUrl0", "")
        media_content_type = form_data.get("MediaContentType0", "")

        # Classify message type by content type
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

    # Data structure compatible with existing code
    data = {
        "id": message_sid,
        "from": from_number,
        "to": to_number,
        "body": body,
        "fromMe": False,  # Twilio only sends incoming messages
        "type": message_type,
        "pushName": form_data.get("ProfileName", ""),
        "timestamp": timestamp,
        "media": media_url,
        "media_content_type": media_content_type,
    }

    print("PROCESSED DATA:", data)

    # COMMAND: DELETE MEMORY
    if body and "borrar memoria" in body.lower():
        print(f"Executing memory deletion for: {phone_number}")
        reset_chat_history(phone_number)
        result = send_twilio_message(from_number, "Your memory has been deleted.")
        if result.get("success", False):
            redis_client.set(dedup_key, "exists", ex=600)
            print(f"Memory deletion processed: {dedup_key}")
        return result

    # Process audio messages (with Celery and immediate ACK)
    if message_type == "audio":
        # If feature is disabled, just save as reference
        if not VOICE_NOTES_ENABLED:
            print(f"VOICE_NOTES_ENABLED=false, ignoring audio for: {phone_number}")
            send_twilio_message(
                from_number,
                "Voice notes are not enabled yet. Please send a text message.",
            )
            return "FeatureDisabled"

        # Deduplication
        audio_dedup_key = f"audio_queued:{phone_number}:{timestamp}"
        if redis_client.exists(audio_dedup_key):
            print(f"Audio already queued previously: {audio_dedup_key}")
            return "NoCommand"

        redis_client.set(audio_dedup_key, "queued", ex=300)

        # SEND IMMEDIATE ACK
        print(f"Sending immediate ACK to user...")
        ack_result = send_twilio_message(
            from_number,
            "I received your voice note. I'm transcribing it, give me a few seconds...",
        )

        # If ACK can't be sent, abort
        if not ack_result.get("success", False):
            print(f"Could not send ACK: {ack_result.get('error')}")
            return "ACKFailed"

        # PREPARE JOB FOR CELERY
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

        # QUEUE TO CELERY (+ Redis fallback)
        try:
            from audio_worker import process_audio_job

            result = process_audio_job.apply_async(
                args=[audio_job],
                queue="audio",
                expires=3600,  # Expires in 1 hour
            )
            print(f"Audio queued to Celery: {result.id}")
        except Exception as e:
            print(f"Error enqueueing to Celery: {e}, using Redis fallback")
            redis_client.lpush("audio_queue", json.dumps(audio_job))

        return "AudioQueued"

    # Process document messages
    if message_type == "document":
        print(f"Document received: {media_url}")

        # ==============================================================================

        # CHECK IF USER ALREADY GAVE A NAME
        expected_name_key = f"doc_nombre:{phone_number}"
        expected_type_key = f"doc_tipo:{phone_number}"

        desired_name = redis_client.get(expected_name_key)
        desired_type = redis_client.get(expected_type_key)

        # If there's a saved name, use it
        if desired_name and desired_type:
            base_name = desired_name
            extension = desired_type
            print(f"Using user name: {base_name}.{extension}")

            # Clean up after use
            redis_client.delete(expected_name_key)
            redis_client.delete(expected_type_key)
        else:
            # Generate automatic name
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

        # Notify user
        send_twilio_message(
            from_number, f"Uploading '{base_name}.{extension}' to Google Drive..."
        )

        # Download file from Twilio
        temp_path = download_document_from_twilio(
            media_url=media_url, file_name=base_name, file_type=extension
        )

        if not temp_path:
            send_twilio_message(
                from_number, "Sorry, there was an error downloading your document."
            )
            redis_client.set(dedup_key, "exists", ex=600)
            return "DocumentError"

        # Upload to Supabase Storage

        folder_id = "1M0TmERmETfEM8flmzwGgfKC7IkrVZaoD"

        result = upload_to_supabase(
            local_file_path=temp_path,
            folder_id=folder_id,
        )

        # Clean up temporary file
        try:
            os.remove(temp_path)
            print(f"Temporary file deleted: {temp_path}")
        except:
            pass

        # Respond to user
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

    # Process image messages (upload to Supabase like documents)
    if message_type == "image":
        print(f"Image received: {media_url}")

        # Generate automatic name
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = f"image_{phone_number}_{timestamp_str}"

        extensions = {
            "image/jpeg": "jpg",
            "image/png": "png",
            "image/gif": "gif",
            "image/webp": "webp",
        }
        extension = extensions.get(media_content_type, "jpg")

        # Notify user
        send_twilio_message(from_number, f"Uploading image to Knowledge Base...")

        # Download file from Twilio
        temp_path = download_document_from_twilio(
            media_url=media_url, file_name=base_name, file_type=extension
        )

        if not temp_path:
            send_twilio_message(
                from_number, "Sorry, there was an error downloading your image."
            )
            redis_client.set(dedup_key, "exists", ex=600)
            return "ImageError"

        # Upload to Supabase Storage
        result = upload_to_supabase(
            local_file_path=temp_path,
        )

        # Clean up temporary file
        try:
            os.remove(temp_path)
            print(f"Temporary file deleted: {temp_path}")
        except:
            pass

        # Respond to user
        if result and result.get("success"):
            message = f"Image '{base_name}.{extension}' uploaded to Knowledge Base!\n"
            message += f"Link: {result['web_view_link']}"

            send_twilio_message(from_number, message)
        else:
            error_message = result.get("error", "Unknown") if result else "Unknown"
            send_twilio_message(from_number, f"Error uploading image: {error_message}")

        redis_client.set(dedup_key, "exists", ex=600)
        return "ImageProcessed"

        # ==============================================================================

    # Check if number exists in cache
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

    # ID for chat history
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
    except:
        print("ERROR PRINTING USER CONVERSATION DICT")

    # Get history and generate response
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
    except:
        print("ERROR PRINTING ASSISTANT CONVERSATION DICT")

    # Send response to user via Twilio
    send_result = send_twilio_message(from_number, str(answer_data["answer"]))

    # Only complete if send was successful
    if not send_result.get("success", False):
        print(
            f"WARNING: Message not sent. Error: {send_result.get('error', 'Unknown')}"
        )
        return "SendError"

    # Only if send was successful, mark as processed
    redis_client.set(dedup_key, "exists", ex=600)
    print(f"Message marked as processed: {dedup_key}")

    # Add to chat history
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

    # Extract important fields from Twilio
    from_number = form_data.get("From", "")  # whatsapp:+5215512345678
    to_number = form_data.get("To", "")  # whatsapp:+14155238886
    body = form_data.get("Body", "")
    message_sid = form_data.get("MessageSid", "")
    num_media = int(form_data.get("NumMedia", 0))

    # Extract clean phone number
    phone_number = extract_phone_from_twilio(from_number)
    print(f"PHONE NUMBER: {phone_number}")

    if not phone_number:
        print("Could not extract phone number")
        return "NoCommand"

    # Current timestamp (Twilio doesn't send timestamp in form data)
    timestamp = int(time.time())

    # DEDUPLICATION BY PHONE + MESSAGE_SID
    dedup_key = f"msg:twilio:{message_sid}"

    if redis_client.exists(dedup_key):
        print(f"Duplicate message detected: {dedup_key}")
        return "NoCommand"

    print(f"Processing new message: {dedup_key}")

    # Get or default language preference for this user
    lang_key = f"user:lang:{phone_number}"
    stored_lang = redis_client.get(lang_key)
    current_lang = stored_lang if stored_lang else "es"

    # Check for greeting or help (only for text messages without media)
    if body and body.strip():
        is_greet = is_greeting(body)
        is_help_req = is_help(body)

        if is_greet or is_help_req:
            # Detect language and update preference
            if is_english(body):
                current_lang = "en"
                redis_client.set(lang_key, "en", ex=86400)  # 24 hours

            # Determine which message to send
            if is_greet:
                response_text = get_intro_message(current_lang)
                msg_type = "greeting"
            else:  # is_help_req
                response_text = get_capabilities_message(current_lang)
                msg_type = "help"

            # Send response
            send_result = send_twilio_message(from_number, response_text)

            if send_result.get("success", False):
                # Log to analytics
                log_chat_interaction(
                    phone_number=phone_number,
                    user_message=body,
                    bot_response=response_text,
                    message_type=msg_type,
                    language=current_lang,
                )
                # Mark as processed
                redis_client.set(dedup_key, "exists", ex=600)
                print(f"Greeting/Help response sent: {msg_type}")
                return "Success"
            else:
                print(f"Failed to send greeting response: {send_result.get('error')}")

    # Determine message type
    message_type = "text"
    media_url = ""
    media_content_type = ""

    if num_media > 0:
        media_url = form_data.get("MediaUrl0", "")
        media_content_type = form_data.get("MediaContentType0", "")

        # Classify message type by content type
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

    # Data structure compatible with existing code
    data = {
        "id": message_sid,
        "from": from_number,
        "to": to_number,
        "body": body,
        "fromMe": False,  # Twilio only sends incoming messages
        "type": message_type,
        "pushName": form_data.get("ProfileName", ""),
        "timestamp": timestamp,
        "media": media_url,
        "media_content_type": media_content_type,
    }

    print("PROCESSED DATA:", data)

    # COMMAND: DELETE MEMORY
    if body and "borrar memoria" in body.lower():
        print(f"Executing memory deletion for: {phone_number}")
        reset_chat_history(phone_number)
        result = send_twilio_message(from_number, "Your memory has been deleted.")
        if result.get("success", False):
            redis_client.set(dedup_key, "exists", ex=600)
            print(f"Memory deletion processed: {dedup_key}")
        return result

    # Variables for the rest of the flow
    id_phone_number = f"fp-idPhone:{phone_number}"
    id_conversacion = (
        f"fp-idPhone:{phone_number}_{datetime.now().strftime('%Y-%m-%d_%H:%M')}"
    )

    # Process audio messages (with Celery and immediate ACK)
    if message_type == "audio":
        # If feature is disabled, just save as reference
        if not VOICE_NOTES_ENABLED:
            print(f"VOICE_NOTES_ENABLED=false, ignoring audio for: {phone_number}")
            send_twilio_message(
                from_number,
                "Voice notes are not enabled yet. Please send a text message.",
            )
            return "FeatureDisabled"

        # Deduplication
        audio_dedup_key = f"audio_queued:{phone_number}:{timestamp}"
        if redis_client.exists(audio_dedup_key):
            print(f"Audio already queued previously: {audio_dedup_key}")
            return "NoCommand"

        redis_client.set(audio_dedup_key, "queued", ex=300)

        # SEND IMMEDIATE ACK
        print(f"Sending immediate ACK to user...")
        ack_result = send_twilio_message(
            from_number,
            "I received your voice note. I'm transcribing it, give me a few seconds...",
        )

        # If ACK can't be sent, abort
        if not ack_result.get("success", False):
            print(f"Could not send ACK: {ack_result.get('error')}")
            return "ACKFailed"

        # PREPARE JOB FOR CELERY
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

        # QUEUE TO CELERY (+ Redis fallback)
        try:
            from audio_worker import process_audio_job

            result = process_audio_job.apply_async(
                args=[audio_job],
                queue="audio",
                expires=3600,  # Expires in 1 hour
            )
            print(f"Audio queued to Celery: {result.id}")
        except Exception as e:
            print(f"Error enqueueing to Celery: {e}, using Redis fallback")
            redis_client.lpush("audio_queue", json.dumps(audio_job))

        return "AudioQueued"

        # Process document messages
        print(f"Document received: {media_url}")

        # CHECK IF USER ALREADY GAVE A NAME
        expected_name_key = f"doc_nombre:{phone_number}"
        expected_type_key = f"doc_tipo:{phone_number}"

        desired_name = redis_client.get(expected_name_key)
        desired_type = redis_client.get(expected_type_key)

        # If there's a saved name, use it
        if desired_name and desired_type:
            base_name = desired_name
            extension = desired_type
            print(f"Using user name: {base_name}.{extension}")

            # Clean up after use
            redis_client.delete(expected_name_key)
            redis_client.delete(expected_type_key)
        else:
            # Generate automatic name
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

        # Notify user
        send_twilio_message(
            from_number, f"Uploading '{base_name}.{extension}' to Google Drive..."
        )

        # Download file from Twilio
        temp_path = download_document_from_twilio(
            media_url=media_url, file_name=base_name, file_type=extension
        )

        if not temp_path:
            send_twilio_message(
                from_number, "Sorry, there was an error downloading your document."
            )
            redis_client.set(dedup_key, "exists", ex=600)
            return "DocumentError"

        # Upload to Supabase Storage

        result = upload_to_supabase(
            ruta_archivo_local=temp_path,
            folder_id="1M0TmERmETfEM8flmzwGgfKC7IkrVZaoD",
        )

        # ADD TO QDRANT
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

        # Clean up temporary file
        try:
            os.remove(temp_path)
            print(f"Temporary file deleted: {temp_path}")
        except:
            pass

        # Respond to user
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

    # Process image messages (upload to Supabase like documents)
    if message_type == "image":
        print(f"Image received: {media_url}")

        # Generate automatic name
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = f"image_{phone_number}_{timestamp_str}"

        extensions = {
            "image/jpeg": "jpg",
            "image/png": "png",
            "image/gif": "gif",
            "image/webp": "webp",
        }
        extension = extensions.get(media_content_type, "jpg")

        # Notify user
        send_twilio_message(from_number, f"Uploading image to Knowledge Base...")

        # Download file from Twilio
        temp_path = download_document_from_twilio(
            media_url=media_url, file_name=base_name, file_type=extension
        )

        if not temp_path:
            send_twilio_message(
                from_number, "Sorry, there was an error downloading your image."
            )
            redis_client.set(dedup_key, "exists", ex=600)
            return "ImageError"

        # Upload to Cloudinary
        result = upload_file_to_cloudinary(temp_path, folder="knowledgebase")

        # Clean up temporary file
        try:
            os.remove(temp_path)
            print(f"Temporary file deleted: {temp_path}")
        except:
            pass

        # Respond to user
        if result and result.get("success"):
            message = f"Image uploaded to Knowledge Base! ✅"

            send_twilio_message(from_number, message)
        else:
            error_message = result.get("error", "Unknown") if result else "Unknown"
            send_twilio_message(from_number, f"Error uploading image: {error_message}")

        redis_client.set(dedup_key, "exists", ex=600)
        return "ImageProcessed"

    # Check if number exists in cache
    if not redis_client.exists(id_phone_number):
        user_data = {"Usuario": "", "Telefono": phone_number}
        data["user_data"] = user_data
        redis_client.set(id_phone_number, json.dumps(user_data), ex=600)
    else:
        print(id_phone_number)
        data["user_data"] = json.loads(redis_client.get(id_phone_number))
        print(data["user_data"])

    # ID for chat history
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
    except:
        print("ERROR PRINTING USER CONVERSATION DICT")

    # Get history and generate response
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
    except:
        print("ERROR PRINTING ASSISTANT CONVERSATION DICT")

    answer_text = str(answer_data["answer"])

    # LIMIT TO 1600 CHARACTERS (WhatsApp allows up to 1600)
    MAX_LENGTH = 1520  # Leave margin

    if len(answer_text) > MAX_LENGTH:
        answer_text = (
            answer_text[:MAX_LENGTH]
            + "\n\n... (truncated response)\nAsk a more specific question for details."
        )
        print(
            f"Response truncated from {len(answer_data['answer'])} to {MAX_LENGTH} characters"
        )

    # Send response to user via Twilio
    send_result = send_twilio_message(
        from_number,
        answer_text,
    )

    # Only complete if send was successful
    if not send_result.get("success", False):
        print(
            f"WARNING: Message not sent. Error: {send_result.get('error', 'Unknown')}"
        )
        return "SendError"

    # Log to analytics
    log_chat_interaction(
        phone_number=phone_number,
        user_message=body,
        bot_response=answer_text,
        message_type="query",
        language=current_lang,
    )

    # Only if send was successful, mark as processed
    redis_client.set(dedup_key, "exists", ex=600)
    print(f"Message marked as processed: {dedup_key}")

    # Add to chat history
    add_to_chat_history(chat_history_id, body, "user", phone_number)
    add_to_chat_history(
        chat_history_id, answer_data["answer"], "assistant", phone_number
    )

    print("Processing completed successfully.")
    return "Success"


# Backward compatibility aliases
enviar_mensaje_twilio = send_twilio_message
enviar_documento_twilio = send_twilio_document
descargar_documento_de_twilio = download_document_from_twilio
procesar_mensajes_entrantes = process_incoming_messages
procesar_mensajes_entrantes_funcional = process_incoming_messages_functional
