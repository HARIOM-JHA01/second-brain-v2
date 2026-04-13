from datetime import datetime
import json
import os
import re
import time
import redis
from anthropic import Anthropic

from agente_rolplay.messaging.twilio_client import (
    send_twilio_message,
    download_document_from_twilio,
    get_media_content_length,
)
from agente_rolplay.agent.roleplay_agent import responder_usuario
from agente_rolplay.messaging.chat_history_manager import (
    add_to_chat_history,
    get_chat_history,
    reset_chat_history,
    store_session_fact,
    get_session_facts,
    clear_session_facts,
)
from agente_rolplay.messaging.greeting_handler import (
    is_greeting,
    is_help,
    is_reset_request,
    is_session_fact,
    detect_ambiguous_acronym,
    get_intro_message,
    get_capabilities_message,
    get_file_upload_message,
    get_reset_confirmation,
    get_menu_message,
    get_beta_support_message,
    is_menu_selection,
    is_coaching_report_request,
    is_coaching_exit,
    is_english,
    detect_language,
)
from agente_rolplay.storage.analytics_logger import (
    log_chat_interaction,
    log_message_to_db,
    log_whatsapp_message_to_db,
)
from agente_rolplay.storage.cloudinary_storage import upload_file_to_cloudinary
from agente_rolplay.messaging.twilio_client import extract_phone_from_twilio
from agente_rolplay.storage.pinecone_client import upload_to_pinecone
from agente_rolplay.storage.file_processor import (
    extract_text_from_file,
    extract_image_description,
    get_file_extension,
    is_vectorizable,
    get_file_type_category,
)

from agente_rolplay.config import (
    ANTHROPIC_API_KEY,
    VOICE_NOTES_ENABLED,
    MAX_FILE_SIZE_BYTES,
    RATE_LIMIT_MAX_MESSAGES,
    RATE_LIMIT_WINDOW_SECONDS,
    ACRONYM_PENDING_TTL,
    DEDUP_KEY_TTL,
    USER_SESSION_TTL,
    USER_LANG_TTL,
    LAST_UPLOADED_FILE_TTL,
    FILE_METADATA_TTL,
    TWILIO_MESSAGE_MAX_LENGTH,
    redis_connection_kwargs,
)

r = redis.Redis(**redis_connection_kwargs())

MENU_OPTIONS_KEY = "admin:menu_options"  # Redis key: JSON {"1":true,"2":true,...}

COACHING_MENU_TTL = 300  # 5 min — waiting for 1/2/3/4 reply
COACHING_SCENARIO_TTL = 300  # 5 min — waiting for scenario number
COACHING_SESSION_TTL = 7200  # 2 h  — active coaching session
COACHING_HISTORY_TTL = 7200  # 2 h  — coaching conversation history

FILE_TOO_LARGE_MSG = {
    "es": "Lo siento, el archivo es demasiado grande. El tamaño máximo permitido es 50 MB.",
    "en": "Sorry, the file is too large. The maximum allowed size is 50 MB.",
}
RATE_LIMIT_MSG = {
    "es": "Has enviado demasiados mensajes. Por favor espera un momento e intenta de nuevo.",
    "en": "You've sent too many messages. Please wait a moment and try again.",
}
PASSWORD_PROTECTED_MSG = (
    "🔒 The file is password protected. Please remove the password and send it again.\n\n"
    "El archivo está protegido con contraseña. Por favor elimina la contraseña e inténtalo de nuevo."
)
ACRONYM_CLARIFICATION_MSG = {
    "es": (
        "Encontré el acrónimo *{acronym}* en tu mensaje y puede tener varios significados. "
        "¿A cuál te refieres?\n{options}\n\n"
        "O si es otro, escríbeme qué significa y respondo de inmediato."
    ),
    "en": (
        "I noticed the acronym *{acronym}* in your message — it can mean a few different things. "
        "Which one did you mean?\n{options}\n\n"
        "Or just tell me what it stands for and I'll answer right away."
    ),
}


_AI_CONFIG_KEY = "admin:ai_config"
_DEFAULT_AI_CONFIG = {"provider": "anthropic", "model": "claude-sonnet-4-6"}


def _get_ai_config(redis_client) -> dict:
    """Return {'provider': str, 'model': str} from Redis. Falls back to Anthropic defaults."""
    import json as _json
    try:
        raw = redis_client.get(_AI_CONFIG_KEY)
        if raw:
            cfg = _json.loads(raw)
            if isinstance(cfg, dict) and "provider" in cfg and "model" in cfg:
                return cfg
    except Exception:
        pass
    return _DEFAULT_AI_CONFIG.copy()


def _get_enabled_menu_options(redis_client) -> set:
    """Return the set of enabled menu option keys e.g. {'1','2','3','4'}.
    Defaults to all enabled when the key is absent."""
    import json as _json
    raw = redis_client.get(MENU_OPTIONS_KEY)
    if not raw:
        return {"1", "2", "3", "4"}
    try:
        state = _json.loads(raw)
        return {k for k, v in state.items() if v}
    except Exception:
        return {"1", "2", "3", "4"}


def _compose_coaching_prompt(scenario, db) -> str:
    from agente_rolplay.db.models import CoachingScenarioReferenceFile
    from agente_rolplay.usecase_api import fetch_latest_session_context

    system_prompt = scenario.system_prompt

    # API-driven scenario: fetch latest live session data
    if scenario.usecase_api_id:
        context = fetch_latest_session_context(scenario.usecase_api_id)
        if context:
            return (
                f"{system_prompt}\n\n"
                "LATEST PRACTICE SESSION DATA (fetched live):\n"
                "Use the following data from the user's most recent coaching session "
                "as the basis for this conversation.\n"
                "<session_data>\n"
                f"{context}\n"
                "</session_data>"
            )
        else:
            print(f"usecase_api: no context for id={scenario.usecase_api_id}, using base prompt")
            return system_prompt

    # Standard scenario: reference files uploaded by admin
    ref_files = (
        db.query(CoachingScenarioReferenceFile)
        .filter(CoachingScenarioReferenceFile.scenario_id == scenario.id)
        .all()
    )

    if not ref_files:
        return system_prompt

    reference_parts = []
    for f in ref_files:
        text = (f.file_text or "").strip()
        if text:
            reference_parts.append(f"=== Reference File: {f.file_name} ===\n{text}")

    if not reference_parts:
        return system_prompt

    combined = "\n\n".join(reference_parts)
    return (
        f"{system_prompt}\n\n"
        "REFERENCE MATERIAL (uploaded by admin):\n"
        "Use this material as factual grounding for this coaching scenario. "
        "If a user asks something not covered by this material, say that clearly.\n"
        "<reference_material>\n"
        f"{combined}\n"
        "</reference_material>"
    )


def _is_rate_limited(phone_number: str, redis_client) -> bool:
    """
    Sliding-window rate limiter: max RATE_LIMIT_MAX_MESSAGES per RATE_LIMIT_WINDOW_SECONDS.
    Returns True if the user has exceeded the limit.
    """
    key = f"rate_limit:{phone_number}"
    count = redis_client.get(key)
    if count is None:
        redis_client.setex(key, RATE_LIMIT_WINDOW_SECONDS, 1)
        return False
    if int(count) >= RATE_LIMIT_MAX_MESSAGES:
        return True
    redis_client.incr(key)
    return False


def _should_refresh_language(text: str) -> bool:
    """Refresh language only when message has alphabetic content."""
    if not text:
        return False
    # Keep current language for menu choices like "1", "\"1\"", "option 1", etc.
    if is_menu_selection(text):
        return False
    return bool(re.search(r"[A-Za-zÀ-ÿ]", text))


def _clear_coaching_state(phone: str, redis_client) -> None:
    """Clear all Redis keys related to coaching flow for a phone number."""
    redis_client.delete(f"coaching:session:{phone}")
    redis_client.delete(f"coaching:history:{phone}")
    redis_client.delete(f"coaching:scenario_pending:{phone}")
    redis_client.delete(f"coaching:menu_pending:{phone}")


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


def get_knowledge_base_file_count(org_id: str) -> int:
    """Get total files in the KB for the given org (scoped to org)."""
    try:
        from agente_rolplay.db.database import SessionLocal
        from agente_rolplay.db.models import Document

        db = SessionLocal()
        try:
            return db.query(Document).filter(Document.org_id == org_id).count()
        finally:
            db.close()
    except Exception:
        return 0


def get_knowledge_base_count_message(org_id: str, lang: str) -> str:
    """Build user-facing KB count response, scoped to org."""
    count = get_knowledge_base_file_count(org_id)
    if lang == "en":
        return f"There are currently {count} file(s) in your organization's Knowledge Base."
    return (
        f"Actualmente hay {count} archivo(s) en el Knowledge Base de tu organización."
    )


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
    redis_client.set(file_key, json.dumps(metadata), ex=FILE_METADATA_TTL)
    redis_client.sadd("all_uploaded_files", filename)


def store_image_metadata(
    phone_number: str,
    filename: str,
    cloudinary_url: str,
    redis_client,
    vector_id: str = None,
    vectorized: bool = False,
):
    """Store image metadata so image uploads are counted in KB inventory."""
    metadata = {
        "filename": filename,
        "original_name": filename,
        "cloudinary_url": cloudinary_url,
        "uploaded_at": datetime.utcnow().isoformat() + "Z",
        "uploaded_by": phone_number,
        "file_category": "image",
        "vector_id": vector_id,
        "vectorized": vectorized,
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

    file_size = get_media_content_length(media_url)
    if file_size and file_size > MAX_FILE_SIZE_BYTES:
        send_twilio_message(from_number, FILE_TOO_LARGE_MSG["es"])
        redis_client.set(dedup_key, "exists", ex=DEDUP_KEY_TTL)
        return "FileTooLarge"

    send_twilio_message(from_number, f"Uploading '{filename}'...")

    temp_path = download_document_from_twilio(
        media_url=media_url, file_name=base_name, file_type=extension
    )

    if not temp_path:
        send_twilio_message(
            from_number, "Sorry, there was an error downloading your file."
        )
        redis_client.set(dedup_key, "exists", ex=DEDUP_KEY_TTL)
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

            if extract_result.get("password_protected"):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass
                send_twilio_message(from_number, PASSWORD_PROTECTED_MSG)
                redis_client.set(dedup_key, "exists", ex=DEDUP_KEY_TTL)
                return "PasswordProtected"

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
        # Persist Document record so the dashboard can show org-scoped files
        try:
            from agente_rolplay.db.database import get_db
            from agente_rolplay.db.models import Document, Profile
            from agente_rolplay.db.whatsapp_auth import normalize_whatsapp_number

            db = next(get_db())
            try:
                normalized_phone = normalize_whatsapp_number(phone_number)
                profile = (
                    db.query(Profile)
                    .filter(Profile.whatsapp_number == normalized_phone)
                    .first()
                )
                if profile:
                    db.add(
                        Document(
                            org_id=profile.org_id,
                            name=filename,
                            drive_file_id=upload_result.get("public_id"),
                        )
                    )
                    db.commit()
            finally:
                db.close()
        except Exception as _doc_err:
            print(f"Warning: could not write Document record: {_doc_err}")

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
        redis_client.set(
            f"last_uploaded_file:{phone_number}", filename, ex=LAST_UPLOADED_FILE_TTL
        )
        log_message_to_db(phone_number, message_type="document")

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

    redis_client.set(dedup_key, "exists", ex=DEDUP_KEY_TTL)
    return "FileProcessed"


# ── Coaching helpers ──────────────────────────────────────────────────────────


def _org_has_active_scenarios(org_id) -> bool:
    """Return True if the org has at least one active coaching scenario."""
    if not org_id:
        return False
    try:
        from agente_rolplay.db.database import get_db
        from agente_rolplay.db.models import CoachingScenario

        db = next(get_db())
        try:
            count = (
                db.query(CoachingScenario)
                .filter(
                    CoachingScenario.org_id == org_id,
                    CoachingScenario.is_active == True,
                )
                .count()
            )
            return count > 0
        finally:
            db.close()
    except Exception as e:
        print(f"_org_has_active_scenarios error: {e}")
        return False


def _start_coaching_scenario_selection(
    phone: str, from_number: str, org_id, redis_client, dedup_key: str, lang: str
) -> str:
    """Show numbered scenario list and store it in Redis for selection."""
    try:
        from agente_rolplay.db.database import get_db
        from agente_rolplay.db.models import CoachingScenario

        db = next(get_db())
        try:
            scenarios = (
                db.query(CoachingScenario)
                .filter(
                    CoachingScenario.org_id == org_id,
                    CoachingScenario.is_active == True,
                )
                .order_by(CoachingScenario.name)
                .all()
            )
        finally:
            db.close()
    except Exception as e:
        print(f"_start_coaching_scenario_selection error: {e}")
        scenarios = []

    if not scenarios:
        msg = (
            "There are no active coaching scenarios available."
            if lang == "en"
            else "No hay escenarios de coaching activos disponibles."
        )
        send_twilio_message(from_number, msg)
        redis_client.set(dedup_key, "exists", ex=DEDUP_KEY_TTL)
        return "Success"

    scenario_list = [
        {
            "id": str(s.id),
            "name": s.name,
            "description": s.description or "",
            "system_prompt": s.system_prompt,
        }
        for s in scenarios
    ]
    redis_client.set(
        f"coaching:scenario_pending:{phone}",
        json.dumps(scenario_list),
        ex=COACHING_SCENARIO_TTL,
    )

    if lang == "en":
        lines = ["Select a coaching scenario:\n"]
        for i, s in enumerate(scenario_list, 1):
            line = f"{i}. *{s['name']}*"
            if s["description"]:
                line += f" — {s['description']}"
            lines.append(line)
        lines.append("\nReply with the number of the scenario.")
    else:
        lines = ["Elige un escenario de coaching:\n"]
        for i, s in enumerate(scenario_list, 1):
            line = f"{i}. *{s['name']}*"
            if s["description"]:
                line += f" — {s['description']}"
            lines.append(line)
        lines.append("\nResponde con el número del escenario.")

    send_twilio_message(from_number, "\n".join(lines))
    redis_client.set(dedup_key, "exists", ex=DEDUP_KEY_TTL)
    return "Success"


def _handle_scenario_selection(
    phone: str,
    from_number: str,
    body: str,
    pending_raw: str,
    org_id,
    redis_client,
    dedup_key: str,
    lang: str,
) -> str:
    """Handle user picking a scenario number."""
    scenario_list = json.loads(pending_raw)
    try:
        idx = int(body.strip()) - 1
        if idx < 0 or idx >= len(scenario_list):
            raise ValueError
    except (ValueError, TypeError):
        # Invalid selection — resend list
        if lang == "en":
            lines = ["Please reply with a number from the list:\n"]
        else:
            lines = ["Por favor responde con un número de la lista:\n"]
        for i, s in enumerate(scenario_list, 1):
            line = f"{i}. *{s['name']}*"
            if s["description"]:
                line += f" — {s['description']}"
            lines.append(line)
        redis_client.set(
            f"coaching:scenario_pending:{phone}", pending_raw, ex=COACHING_SCENARIO_TTL
        )
        send_twilio_message(from_number, "\n".join(lines))
        redis_client.set(dedup_key, "exists", ex=DEDUP_KEY_TTL)
        return "Success"

    chosen = scenario_list[idx]
    redis_client.delete(f"coaching:scenario_pending:{phone}")

    scenario_prompt = ""
    reference_file_name = None
    try:
        from agente_rolplay.db.database import get_db
        from agente_rolplay.db.models import CoachingScenario
        import uuid as _uuid

        db = next(get_db())
        try:
            scenario = (
                db.query(CoachingScenario)
                .filter(CoachingScenario.id == _uuid.UUID(chosen["id"]))
                .first()
            )
            if scenario:
                scenario_id = str(scenario.id)
                scenario_prompt = _compose_coaching_prompt(scenario, db)
        finally:
            db.close()
    except Exception as e:
        print(f"Error loading scenario prompt context: {e}")
    if not scenario_prompt:
        scenario_prompt = chosen.get("system_prompt") or ""

    # Create DB record
    session_id = None
    try:
        from agente_rolplay.db.database import get_db
        from agente_rolplay.db.models import CoachingSession
        import uuid as _uuid

        db = next(get_db())
        try:
            session = CoachingSession(
                org_id=org_id,
                phone_number=phone,
                scenario_id=_uuid.UUID(chosen["id"]),
                scenario_name=chosen["name"],
            )
            db.add(session)
            db.commit()
            db.refresh(session)
            session_id = str(session.id)
        finally:
            db.close()
    except Exception as e:
        print(f"Error creating CoachingSession: {e}")
        import uuid as _uuid

        session_id = str(_uuid.uuid4())

    session_data = {
        "session_id": session_id,
        "scenario_id": chosen["id"],
        "scenario_name": chosen["name"],
        "system_prompt": scenario_prompt,
        "reference_file_name": reference_file_name,
        "org_id": str(org_id) if org_id else None,
        "started_at": datetime.utcnow().isoformat(),
    }
    history_key = f"coaching:history:{phone}"
    redis_client.set(
        f"coaching:session:{phone}", json.dumps(session_data), ex=COACHING_SESSION_TTL
    )
    redis_client.set(history_key, json.dumps([]), ex=COACHING_HISTORY_TTL)

    if lang == "en":
        msg = (
            f"🎯 *Coaching session started!*\n\n"
            f"Scenario: *{chosen['name']}*\n\n"
            f"The coach will start now.\n\n"
            f"_To end the session, type 'exit'. To get your report, type 'report'._"
        )
    else:
        msg = (
            f"🎯 *¡Sesión de coaching iniciada!*\n\n"
            f"Escenario: *{chosen['name']}*\n\n"
            f"El coach comenzará ahora.\n\n"
            f"_Para terminar la sesión escribe 'salir'. Para obtener tu reporte escribe 'reporte'._"
        )
    send_twilio_message(from_number, msg)

    # Auto-start the roleplay with the coach's opening turn.
    kickoff_instruction = (
        "Start this roleplay now as the scenario counterpart. "
        "Send the very first message to open the conversation naturally, "
        "in 1-3 sentences, and end with one focused question."
        if lang == "en"
        else "Inicia este roleplay ahora como la contraparte del escenario. "
        "Envía el primer mensaje para abrir la conversación de forma natural, "
        "en 1-3 oraciones, y termina con una pregunta concreta."
    )
    id_phone_number = f"fp-idPhone:{phone}"
    id_conversacion = f"fp-idPhone:{phone}_{datetime.now().strftime('%Y-%m-%d_%H:%M')}"
    kickoff_data = {
        "body": kickoff_instruction,
        "type": "text",
        "from": f"whatsapp:+{phone}",
    }

    _ai_cfg = _get_ai_config(redis_client)
    kickoff_reply = ""
    kickoff_ms = None
    try:
        _t0 = time.time()
        kickoff_answer = responder_usuario(
            messages=[],
            data=kickoff_data,
            telefono=phone,
            id_conversacion=id_conversacion,
            id_phone_number=id_phone_number,
            response_language=lang,
            coaching_system_prompt=session_data["system_prompt"],
            ai_provider=_ai_cfg["provider"],
            ai_model=_ai_cfg["model"],
        )
        kickoff_ms = int((time.time() - _t0) * 1000)
        kickoff_reply = str(kickoff_answer.get("answer", "")).strip()
    except Exception as e:
        print(f"Error generating coaching opener: {e}")

    if not kickoff_reply:
        kickoff_reply = (
            "Thanks for joining. Let's begin: what's the most important outcome you want from this conversation today?"
            if lang == "en"
            else "Gracias por unirte. Empecemos: ¿cuál es el resultado más importante que quieres lograr en esta conversación hoy?"
        )

    send_twilio_message(from_number, kickoff_reply)
    redis_client.set(
        history_key,
        json.dumps([{"role": "assistant", "content": kickoff_reply}]),
        ex=COACHING_HISTORY_TTL,
    )
    redis_client.set(
        f"coaching:session:{phone}", json.dumps(session_data), ex=COACHING_SESSION_TTL
    )
    log_message_to_db(phone, message_type="text", response_time_ms=kickoff_ms)

    redis_client.set(dedup_key, "exists", ex=DEDUP_KEY_TTL)
    return "Success"


def _handle_coaching_turn(
    phone: str,
    from_number: str,
    body: str,
    session: dict,
    redis_client,
    dedup_key: str,
    lang: str,
) -> str:
    """Process one user turn inside an active coaching session."""
    history_key = f"coaching:history:{phone}"
    history_raw = redis_client.get(history_key)
    history = json.loads(history_raw) if history_raw else []

    history.append({"role": "user", "content": body})

    id_phone_number = f"fp-idPhone:{phone}"
    id_conversacion = f"fp-idPhone:{phone}_{datetime.now().strftime('%Y-%m-%d_%H:%M')}"

    data = {"body": body, "type": "text", "from": f"whatsapp:+{phone}"}
    _ai_cfg = _get_ai_config(redis_client)
    _t0 = time.time()
    answer_data = responder_usuario(
        messages=history,
        data=data,
        telefono=phone,
        id_conversacion=id_conversacion,
        id_phone_number=id_phone_number,
        response_language=lang,
        coaching_system_prompt=session["system_prompt"],
        ai_provider=_ai_cfg["provider"],
        ai_model=_ai_cfg["model"],
    )
    _response_ms = int((time.time() - _t0) * 1000)

    reply = str(answer_data["answer"])
    history.append({"role": "assistant", "content": reply})

    redis_client.set(history_key, json.dumps(history), ex=COACHING_HISTORY_TTL)
    redis_client.set(
        f"coaching:session:{phone}", json.dumps(session), ex=COACHING_SESSION_TTL
    )

    send_twilio_message(from_number, reply)
    log_message_to_db(phone, message_type="text", response_time_ms=_response_ms)
    redis_client.set(dedup_key, "exists", ex=DEDUP_KEY_TTL)
    return "Success"


def _end_coaching_session(
    phone: str,
    from_number: str,
    session: dict,
    redis_client,
    dedup_key: str,
    generate_report: bool,
    lang: str,
) -> str:
    """End a coaching session, optionally generating a report first."""
    history_key = f"coaching:history:{phone}"
    session_key = f"coaching:session:{phone}"

    if generate_report:
        history_raw = redis_client.get(history_key)
        history = json.loads(history_raw) if history_raw else []

        if lang == "en":
            send_twilio_message(from_number, "⏳ Generating your coaching report…")
        else:
            send_twilio_message(from_number, "⏳ Generando tu reporte de coaching…")

        try:
            from agente_rolplay.agent.roleplay_agent import generate_coaching_report

            _ai_cfg = _get_ai_config(redis_client)
            report = generate_coaching_report(
                history=history,
                scenario_name=session.get("scenario_name", ""),
                lang=lang,
                ai_provider=_ai_cfg["provider"],
                ai_model=_ai_cfg["model"],
            )
        except Exception as e:
            print(f"Error generating coaching report: {e}")
            report = (
                "Sorry, there was an error generating the report."
                if lang == "en"
                else "Lo siento, hubo un error al generar el reporte."
            )

        send_twilio_message(from_number, report)

        # Persist report to DB
        try:
            from agente_rolplay.db.database import get_db
            from agente_rolplay.db.models import CoachingSession
            import uuid as _uuid

            db = next(get_db())
            try:
                cs = (
                    db.query(CoachingSession)
                    .filter(CoachingSession.id == _uuid.UUID(session["session_id"]))
                    .first()
                )
                if cs:
                    cs.ended_at = datetime.utcnow()
                    cs.report_text = report
                    db.commit()
            finally:
                db.close()
        except Exception as e:
            print(f"Error persisting coaching report: {e}")
    else:
        # Just end the session
        msg = (
            "👋 Coaching session ended. Come back anytime!"
            if lang == "en"
            else "👋 Sesión de coaching finalizada. ¡Vuelve cuando quieras!"
        )
        send_twilio_message(from_number, msg)

        try:
            from agente_rolplay.db.database import get_db
            from agente_rolplay.db.models import CoachingSession
            import uuid as _uuid

            db = next(get_db())
            try:
                cs = (
                    db.query(CoachingSession)
                    .filter(CoachingSession.id == _uuid.UUID(session["session_id"]))
                    .first()
                )
                if cs:
                    cs.ended_at = datetime.utcnow()
                    db.commit()
            finally:
                db.close()
        except Exception as e:
            print(f"Error updating CoachingSession ended_at: {e}")

    redis_client.delete(session_key)
    redis_client.delete(history_key)
    redis_client.set(dedup_key, "exists", ex=DEDUP_KEY_TTL)
    return "Success"


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
    lang_key = f"user:lang:{phone_number}"
    current_lang = redis_client.get(lang_key) or "es"
    if body and body.strip() and _should_refresh_language(body):
        current_lang = detect_language(body)
        redis_client.set(lang_key, current_lang, ex=USER_LANG_TTL)

    if body and body.strip() and num_media == 0:
        if is_knowledge_base_inventory_query(body):
            from agente_rolplay.db.whatsapp_auth import lookup_whatsapp_user

            _wa_user = lookup_whatsapp_user(phone_number)
            _org_id = _wa_user.get("org_id") if _wa_user else None
            response_text = get_knowledge_base_count_message(_org_id, "en")
            send_twilio_message(from_number, response_text)
            redis_client.set(dedup_key, "exists", ex=DEDUP_KEY_TTL)
            return "Success"

        if redis_client.get(file_upload_pending_key) == "pending":
            if is_knowledge_base_inventory_query(body):
                redis_client.delete(file_upload_pending_key)
            else:
                send_twilio_message(
                    from_number, "Please send me the file you want to upload."
                )
                redis_client.set(dedup_key, "exists", ex=DEDUP_KEY_TTL)
                return "Success"

        upload_intent = detect_file_upload_intent(body, phone_number)
        if upload_intent:
            redis_client.set(file_upload_pending_key, "pending", ex=DEDUP_KEY_TTL)
            send_twilio_message(
                from_number, "Please send me the file you want to upload."
            )
            redis_client.set(dedup_key, "exists", ex=DEDUP_KEY_TTL)
            return "Success"

    # ── Coaching state checks (functional variant) ────────────────────────────
    if body and body.strip() and num_media == 0:
        _scenario_pending_raw_f = redis_client.get(
            f"coaching:scenario_pending:{phone_number}"
        )
        if _scenario_pending_raw_f:
            from agente_rolplay.db.whatsapp_auth import lookup_whatsapp_user as _lwa

            _wa_u = _lwa(phone_number)
            _oid = _wa_u.get("org_id") if _wa_u else None
            return _handle_scenario_selection(
                phone=phone_number,
                from_number=from_number,
                body=body,
                pending_raw=_scenario_pending_raw_f,
                org_id=_oid,
                redis_client=redis_client,
                dedup_key=dedup_key,
                lang=current_lang,
            )

        _menu_pending_key = f"coaching:menu_pending:{phone_number}"
        _menu_pending = redis_client.get(_menu_pending_key)

        _session_raw_f = redis_client.get(f"coaching:session:{phone_number}")
        if _session_raw_f and not _menu_pending:
            _session_f = json.loads(_session_raw_f)
            if is_coaching_exit(body):
                return _end_coaching_session(
                    phone=phone_number,
                    from_number=from_number,
                    session=_session_f,
                    redis_client=redis_client,
                    dedup_key=dedup_key,
                    generate_report=False,
                    lang=current_lang,
                )
            if is_coaching_report_request(body):
                return _end_coaching_session(
                    phone=phone_number,
                    from_number=from_number,
                    session=_session_f,
                    redis_client=redis_client,
                    dedup_key=dedup_key,
                    generate_report=True,
                    lang=current_lang,
                )
            return _handle_coaching_turn(
                phone=phone_number,
                from_number=from_number,
                body=body,
                session=_session_f,
                redis_client=redis_client,
                dedup_key=dedup_key,
                lang=current_lang,
            )

        if _menu_pending:
            selection_f = is_menu_selection(body)
            redis_client.delete(_menu_pending_key)
            if selection_f == "2":
                redis_client.set(file_upload_pending_key, "pending", ex=DEDUP_KEY_TTL)
                send_twilio_message(
                    from_number, "Please send me the file you want to upload."
                )
                redis_client.set(dedup_key, "exists", ex=DEDUP_KEY_TTL)
                return "Success"
            elif selection_f == "3":
                _clear_coaching_state(phone_number, redis_client)
                from agente_rolplay.db.whatsapp_auth import (
                    lookup_whatsapp_user as _lwa2,
                )

                _wa_u2 = _lwa2(phone_number)
                _oid2 = _wa_u2.get("org_id") if _wa_u2 else None
                return _start_coaching_scenario_selection(
                    phone=phone_number,
                    from_number=from_number,
                    org_id=_oid2,
                    redis_client=redis_client,
                    dedup_key=dedup_key,
                    lang=current_lang,
                )
            elif selection_f == "4":
                send_twilio_message(from_number, get_beta_support_message(current_lang))
                redis_client.set(
                    f"coaching:menu_pending:{phone_number}", "1", ex=COACHING_MENU_TTL
                )
                redis_client.set(dedup_key, "exists", ex=DEDUP_KEY_TTL)
                return "Success"
            elif selection_f != "1":
                send_twilio_message(from_number, get_menu_message(current_lang, _get_enabled_menu_options(redis_client)))
                redis_client.set(
                    f"coaching:menu_pending:{phone_number}", "1", ex=COACHING_MENU_TTL
                )
                redis_client.set(dedup_key, "exists", ex=DEDUP_KEY_TTL)
                return "Success"
            # selection_f == "1": fall through to normal agent
    # ─────────────────────────────────────────────────────────────────────────

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

    if body and is_reset_request(body):
        print(f"Executing memory deletion for: {phone_number}")
        _clear_coaching_state(phone_number, redis_client)
        reset_chat_history(phone_number)
        clear_session_facts(phone_number)
        lang = detect_language(body)
        confirmation = get_reset_confirmation(lang)
        result = send_twilio_message(from_number, confirmation)
        if result.get("success", False):
            redis_client.set(dedup_key, "exists", ex=DEDUP_KEY_TTL)
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
            redis_client.set(id_phone_number, json.dumps(user_data), ex=DEDUP_KEY_TTL)
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

        import threading
        from agente_rolplay.messaging.audio_worker import _process_audio_inline

        thread = threading.Thread(
            target=_process_audio_inline, args=(audio_job,), daemon=True
        )
        thread.start()
        print(f"Audio processing started in background thread for: {phone_number}")

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

        file_size = get_media_content_length(media_url)
        if file_size and file_size > MAX_FILE_SIZE_BYTES:
            send_twilio_message(from_number, FILE_TOO_LARGE_MSG["es"])
            redis_client.set(dedup_key, "exists", ex=DEDUP_KEY_TTL)
            return "FileTooLarge"

        send_twilio_message(from_number, "Uploading image to Knowledge Base...")

        temp_path = download_document_from_twilio(
            media_url=media_url, file_name=base_name, file_type=extension
        )

        if not temp_path:
            send_twilio_message(
                from_number, "Sorry, there was an error downloading your image."
            )
            redis_client.set(dedup_key, "exists", ex=DEDUP_KEY_TTL)
            return "ImageError"

        result = upload_file_to_cloudinary(temp_path, folder="knowledgebase")

        vector_id = None
        vectorized = False
        vision_result = None
        filename = f"{base_name}.{extension}"

        if result and result.get("success"):
            vision_result = extract_image_description(temp_path, media_content_type)
            if vision_result.get("success") and vision_result.get("can_vectorize"):
                print(f"Vectorizing image: {filename}")
                pinecone_result = upload_to_pinecone(
                    text=vision_result["text"],
                    filename=filename,
                    file_type="image",
                    metadata={
                        "uploaded_by": phone_number,
                        "cloudinary_url": result.get("secure_url"),
                    },
                )
                if pinecone_result.get("success"):
                    vector_id = pinecone_result.get("vector_id")
                    vectorized = True
                    print(f"Image vectorized: {filename} id={vector_id}")
            else:
                print(f"Image vision extraction failed: {vision_result.get('error')}")

        try:
            os.remove(temp_path)
            print(f"Temporary file deleted: {temp_path}")
        except Exception:
            pass

        if result and result.get("success"):
            store_image_metadata(
                phone_number=phone_number,
                filename=filename,
                cloudinary_url=result.get("secure_url"),
                redis_client=redis_client,
                vector_id=vector_id,
                vectorized=vectorized,
            )
            redis_client.set(
                f"last_uploaded_file:{phone_number}", filename, ex=86400 * 7
            )
            log_message_to_db(phone_number, message_type="image")
            message = f"Image '{base_name}.{extension}' uploaded to Knowledge Base!\n"
            message += f"Link: {result['secure_url']}"

            send_twilio_message(from_number, message)

            # Record upload in chat history so Claude has context for follow-up questions
            chat_history_id = f"fp-chatHistory:{from_number}"
            add_to_chat_history(
                chat_history_id, f"[Sent image: {filename}]", "user", phone_number
            )
            log_whatsapp_message_to_db(phone_number, "user", f"[Sent image: {filename}]", "image")
            bot_history_msg = f"Image '{filename}' uploaded to Knowledge Base."
            if vectorized and vision_result and vision_result.get("text"):
                bot_history_msg += f" Description: {vision_result['text'][:400]}"
            add_to_chat_history(
                chat_history_id, bot_history_msg, "assistant", phone_number
            )
            log_whatsapp_message_to_db(phone_number, "assistant", bot_history_msg, "image")
        else:
            error_message = result.get("error", "Unknown") if result else "Unknown"
            send_twilio_message(from_number, f"Error uploading image: {error_message}")

        redis_client.set(dedup_key, "exists", ex=DEDUP_KEY_TTL)
        return "ImageProcessed"

    if message_type in ("video", "media"):
        print(f"Unsupported media type received: {media_content_type}")
        send_twilio_message(
            from_number,
            "Sorry, I can't process that file type. I currently support:\n"
            "• Images (JPG, PNG, GIF, WebP)\n"
            "• Documents (PDF, DOCX, PPTX, TXT)\n"
            "• Voice notes\n\n"
            "Please send one of those formats.",
        )
        redis_client.set(dedup_key, "exists", ex=DEDUP_KEY_TTL)
        return "UnsupportedMedia"

    id_phone_number = f"fp-idPhone:{phone_number}"
    id_conversacion = (
        f"fp-idPhone:{phone_number}_{datetime.now().strftime('%Y-%m-%d_%H:%M')}"
    )

    if not redis_client.exists(id_phone_number):
        user_data = {"Usuario": "", "Telefono": phone_number}
        data["user_data"] = user_data
        redis_client.set(id_phone_number, json.dumps(user_data), ex=DEDUP_KEY_TTL)
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

    if _is_rate_limited(phone_number, redis_client):
        print(f"Rate limit exceeded for {phone_number}")
        lang = detect_language(body) if body else "es"
        send_twilio_message(from_number, RATE_LIMIT_MSG[lang])
        redis_client.set(dedup_key, "exists", ex=DEDUP_KEY_TTL)
        return "RateLimited"

    # Acronym disambiguation
    _acronym_pending_key = f"pending_acronym:{phone_number}"
    _pending_acronym = redis_client.get(_acronym_pending_key)

    if _pending_acronym:
        # User is responding to our clarification request — enrich the original query
        _pending = json.loads(_pending_acronym)
        _original_msg = _pending["original_message"]
        _acronym = _pending["acronym"]
        _enriched = f"{_original_msg} [{_acronym} = {body}]"
        data["body"] = _enriched
        body = _enriched
        redis_client.delete(_acronym_pending_key)
        print(f"Acronym '{_acronym}' clarified for {phone_number}: {body[:100]}")
    elif body:
        _acronym, _meanings = detect_ambiguous_acronym(body, ANTHROPIC_API_KEY)
        if _acronym:
            _pending_data = {"original_message": body, "acronym": _acronym}
            redis_client.setex(
                _acronym_pending_key, ACRONYM_PENDING_TTL, json.dumps(_pending_data)
            )
            _options = "\n".join(f"• {m}" for m in _meanings)
            _lang = detect_language(body)
            _clarification = ACRONYM_CLARIFICATION_MSG[_lang].format(
                acronym=_acronym, options=_options
            )
            send_twilio_message(from_number, _clarification)
            redis_client.set(dedup_key, "exists", ex=DEDUP_KEY_TTL)
            return "AcronymClarification"

    if body and is_session_fact(body):
        store_session_fact(phone_number, body)
        print(f"Session fact stored for {phone_number}: {body[:80]}")

    session_facts = get_session_facts(phone_number)
    messages = get_chat_history(chat_history_id, phone=phone_number)
    _t0 = time.time()
    answer_data = responder_usuario(
        messages,
        data,
        telefono=phone_number,
        id_conversacion=id_conversacion,
        id_phone_number=id_phone_number,
        response_language=current_lang,
        session_facts=session_facts or None,
    )
    _response_ms = int((time.time() - _t0) * 1000)
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
        log_message_to_db(
            phone_number,
            message_type="text",
            response_time_ms=_response_ms,
            is_error=True,
        )
        return "SendError"

    log_message_to_db(
        phone_number,
        message_type="text",
        is_rag_query=bool(answer_data.get("used_rag", False)),
        response_time_ms=_response_ms,
    )

    redis_client.set(dedup_key, "exists", ex=DEDUP_KEY_TTL)
    print(f"Message marked as processed: {dedup_key}")

    add_to_chat_history(chat_history_id, body, "user", phone_number)
    log_whatsapp_message_to_db(phone_number, "user", body, msg_type)
    add_to_chat_history(
        chat_history_id, answer_data["answer"], "assistant", phone_number
    )
    log_whatsapp_message_to_db(phone_number, "assistant", answer_data["answer"])

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

    # --- Banco Q&A: handle messages from the configured banco poll phone ---
    from agente_rolplay.config import BANCO_POLL_PHONE

    _banco_bare = BANCO_POLL_PHONE.lstrip("+")
    _banco_match = phone_number == _banco_bare or (
        len(phone_number) >= 10
        and len(_banco_bare) >= 10
        and phone_number[-10:] == _banco_bare[-10:]
    )
    print(
        f"[BANCO] incoming phone={phone_number!r} | banco_bare={_banco_bare!r} | match={_banco_match}"
    )
    if _banco_match and body and body.strip():
        _ctx_raw = redis_client.get(f"banco:session_context:{_banco_bare}")
        print(
            f"[BANCO] context key=banco:session_context:{_banco_bare} | found={_ctx_raw is not None}"
        )
        if _ctx_raw:
            _ctx = json.loads(_ctx_raw)
            _banco_system_prompt = (
                "You are a helpful AI assistant. The user received a coaching session evaluation report "
                "and is asking questions about it. Answer clearly and concisely based only on the "
                "report content below. If the answer is not in the report, say so.\n\n"
                f"Employee: {_ctx.get('emp_name')} (ID: {_ctx.get('emp_id')})\n"
                f"Date: {_ctx.get('date')}\n\n"
                f"Report:\n{_ctx.get('plain_text', '')}"
            )
            _banco_data = {"body": body, "type": "text", "from": from_number}
            _dedup_key = f"msg:twilio:{message_sid}"
            if redis_client.exists(_dedup_key):
                return "NoCommand"
            _banco_answer = responder_usuario(
                messages=[],
                data=_banco_data,
                telefono=phone_number,
                id_conversacion=f"banco:{phone_number}",
                id_phone_number=f"fp-idPhone:{phone_number}",
                coaching_system_prompt=_banco_system_prompt,
            )
            send_twilio_message(from_number, str(_banco_answer["answer"]))
            redis_client.set(_dedup_key, "exists", ex=DEDUP_KEY_TTL)
            return "BancoQA"
    # --- end Banco Q&A ---

    try:
        from agente_rolplay.db.whatsapp_auth import (
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
    current_lang = redis_client.get(lang_key) or "es"
    if body and body.strip() and _should_refresh_language(body):
        current_lang = detect_language(body)
        redis_client.set(lang_key, current_lang, ex=USER_LANG_TTL)

    if body and body.strip():
        if is_knowledge_base_inventory_query(body):
            org_id = whatsapp_user.get("org_id") if whatsapp_user else None
            response_text = get_knowledge_base_count_message(org_id, current_lang)
            send_result = send_twilio_message(from_number, response_text)
            if send_result.get("success", False):
                log_chat_interaction(
                    phone_number=phone_number,
                    user_message=body,
                    bot_response=response_text,
                    message_type="kb_inventory",
                    language=current_lang,
                )
                redis_client.set(dedup_key, "exists", ex=DEDUP_KEY_TTL)
                return "Success"

        is_greet = is_greeting(body)
        is_help_req = is_help(body)

        if is_greet or is_help_req:
            if is_english(body):
                current_lang = "en"
                redis_client.set(lang_key, "en", ex=86400)

            if is_greet:
                org_id = whatsapp_user.get("org_id") if whatsapp_user else None
                if org_id and _org_has_active_scenarios(org_id):
                    _enabled_opts = _get_enabled_menu_options(redis_client)

                    # Single option enabled — go straight to it, no menu needed
                    if len(_enabled_opts) == 1:
                        _only = next(iter(_enabled_opts))
                        redis_client.set(dedup_key, "exists", ex=DEDUP_KEY_TTL)
                        if _only == "2":
                            redis_client.set(f"file_upload_pending:{phone_number}", "pending", ex=DEDUP_KEY_TTL)
                            send_twilio_message(from_number, get_file_upload_message(current_lang))
                            return "Success"
                        elif _only == "3":
                            _clear_coaching_state(phone_number, redis_client)
                            return _start_coaching_scenario_selection(
                                phone=phone_number,
                                from_number=from_number,
                                org_id=org_id,
                                redis_client=redis_client,
                                dedup_key=dedup_key,
                                lang=current_lang,
                            )
                        elif _only == "4":
                            send_twilio_message(from_number, get_beta_support_message(current_lang))
                            return "Success"
                        # _only == "1": fall through to normal agent below

                    # Multiple options — show the menu
                    response_text = get_menu_message(current_lang, _enabled_opts)
                    msg_type = "greeting"
                    send_result = send_twilio_message(from_number, response_text)
                    if send_result.get("success", False):
                        redis_client.set(
                            f"coaching:menu_pending:{phone_number}",
                            "1",
                            ex=COACHING_MENU_TTL,
                        )
                        log_chat_interaction(
                            phone_number=phone_number,
                            user_message=body,
                            bot_response=response_text,
                            message_type=msg_type,
                            language=current_lang,
                        )
                        log_message_to_db(phone_number, message_type=msg_type)
                        redis_client.set(dedup_key, "exists", ex=DEDUP_KEY_TTL)
                        return "Success"
                else:
                    response_text = get_intro_message(current_lang)
                    msg_type = "greeting"
                    send_result = send_twilio_message(from_number, response_text)
                    if send_result.get("success", False):
                        log_chat_interaction(
                            phone_number=phone_number,
                            user_message=body,
                            bot_response=response_text,
                            message_type=msg_type,
                            language=current_lang,
                        )
                        log_message_to_db(phone_number, message_type=msg_type)
                        redis_client.set(dedup_key, "exists", ex=DEDUP_KEY_TTL)
                        return "Success"
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
                    log_message_to_db(phone_number, message_type=msg_type)
                    redis_client.set(dedup_key, "exists", ex=DEDUP_KEY_TTL)
                    print(f"Help response sent: {msg_type}")
                    return "Success"
                else:
                    print(f"Failed to send help response: {send_result.get('error')}")

        # ── Coaching state checks ──────────────────────────────────────────────

        # 1. User is selecting a scenario
        _scenario_pending_raw = redis_client.get(
            f"coaching:scenario_pending:{phone_number}"
        )
        if _scenario_pending_raw:
            org_id = whatsapp_user.get("org_id") if whatsapp_user else None
            return _handle_scenario_selection(
                phone=phone_number,
                from_number=from_number,
                body=body,
                pending_raw=_scenario_pending_raw,
                org_id=org_id,
                redis_client=redis_client,
                dedup_key=dedup_key,
                lang=current_lang,
            )

        # 2. Active coaching session
        _menu_pending_key = f"coaching:menu_pending:{phone_number}"
        _menu_pending = redis_client.get(_menu_pending_key)

        _session_raw = redis_client.get(f"coaching:session:{phone_number}")
        if _session_raw and not _menu_pending:
            _session = json.loads(_session_raw)
            if is_coaching_exit(body):
                return _end_coaching_session(
                    phone=phone_number,
                    from_number=from_number,
                    session=_session,
                    redis_client=redis_client,
                    dedup_key=dedup_key,
                    generate_report=False,
                    lang=current_lang,
                )
            if is_coaching_report_request(body):
                return _end_coaching_session(
                    phone=phone_number,
                    from_number=from_number,
                    session=_session,
                    redis_client=redis_client,
                    dedup_key=dedup_key,
                    generate_report=True,
                    lang=current_lang,
                )
            return _handle_coaching_turn(
                phone=phone_number,
                from_number=from_number,
                body=body,
                session=_session,
                redis_client=redis_client,
                dedup_key=dedup_key,
                lang=current_lang,
            )

        # 3. User is picking from 1/2/3 menu
        if _menu_pending:
            selection = is_menu_selection(body)
            _enabled_opts = _get_enabled_menu_options(redis_client)
            if selection and selection not in _enabled_opts:
                selection = None  # treat disabled option as invalid
            redis_client.delete(_menu_pending_key)
            if selection == "1":
                pass  # fall through to normal agent
            elif selection == "2":
                file_upload_pending_key = f"file_upload_pending:{phone_number}"
                redis_client.set(file_upload_pending_key, "pending", ex=DEDUP_KEY_TTL)
                upload_msg = get_file_upload_message(current_lang)
                send_twilio_message(from_number, upload_msg)
                redis_client.set(dedup_key, "exists", ex=DEDUP_KEY_TTL)
                return "Success"
            elif selection == "3":
                _clear_coaching_state(phone_number, redis_client)
                org_id = whatsapp_user.get("org_id") if whatsapp_user else None
                return _start_coaching_scenario_selection(
                    phone=phone_number,
                    from_number=from_number,
                    org_id=org_id,
                    redis_client=redis_client,
                    dedup_key=dedup_key,
                    lang=current_lang,
                )
            elif selection == "4":
                send_twilio_message(from_number, get_beta_support_message(current_lang))
                redis_client.set(
                    f"coaching:menu_pending:{phone_number}", "1", ex=COACHING_MENU_TTL
                )
                redis_client.set(dedup_key, "exists", ex=DEDUP_KEY_TTL)
                return "Success"
            else:
                # Invalid reply — resend menu
                send_twilio_message(from_number, get_menu_message(current_lang, _get_enabled_menu_options(redis_client)))
                redis_client.set(
                    f"coaching:menu_pending:{phone_number}", "1", ex=COACHING_MENU_TTL
                )
                redis_client.set(dedup_key, "exists", ex=DEDUP_KEY_TTL)
                return "Success"

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
                redis_client.set(dedup_key, "exists", ex=DEDUP_KEY_TTL)
                return "Success"
            elif user_response == "rename":
                redis_client.delete(pending_action_key)
                send_twilio_message(
                    from_number, "OK, what name would you like to give this file?"
                )
                redis_client.set(pending_rename_key, "waiting_for_name", ex=300)
                redis_client.set(dedup_key, "exists", ex=DEDUP_KEY_TTL)
                return "Success"
            else:
                send_twilio_message(
                    from_number, "Please respond with 'update' or 'rename'."
                )
                redis_client.set(dedup_key, "exists", ex=DEDUP_KEY_TTL)
                return "Success"

        if redis_client.get(pending_rename_key) == "waiting_for_name":
            new_filename = body.strip()
            if "." not in new_filename:
                send_twilio_message(
                    from_number, "Please include the file extension (e.g., report.pdf)"
                )
                redis_client.set(dedup_key, "exists", ex=DEDUP_KEY_TTL)
                return "Success"

            redis_client.set(f"pending_rename:{phone_number}", new_filename, ex=300)
            redis_client.delete(pending_rename_key)
            send_twilio_message(
                from_number, f"Got it! Now send me the file '{new_filename}'."
            )
            redis_client.set(dedup_key, "exists", ex=DEDUP_KEY_TTL)
            return "Success"

        file_upload_pending_key = f"file_upload_pending:{phone_number}"
        if num_media == 0:
            if redis_client.get(file_upload_pending_key) == "pending":
                if is_knowledge_base_inventory_query(body):
                    redis_client.delete(file_upload_pending_key)
                else:
                    upload_msg = get_file_upload_message(current_lang)
                    send_twilio_message(from_number, upload_msg)
                    redis_client.set(dedup_key, "exists", ex=DEDUP_KEY_TTL)
                    return "Success"

            upload_intent = detect_file_upload_intent(body, phone_number)
            if upload_intent:
                redis_client.set(file_upload_pending_key, "pending", ex=DEDUP_KEY_TTL)
                upload_msg = get_file_upload_message(current_lang)
                send_twilio_message(from_number, upload_msg)
                redis_client.set(dedup_key, "exists", ex=DEDUP_KEY_TTL)
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

    if body and is_reset_request(body):
        print(f"Executing memory deletion for: {phone_number}")
        _clear_coaching_state(phone_number, redis_client)
        reset_chat_history(phone_number)
        clear_session_facts(phone_number)
        lang = detect_language(body)
        confirmation = get_reset_confirmation(lang)
        result = send_twilio_message(from_number, confirmation)
        if result.get("success", False):
            redis_client.set(dedup_key, "exists", ex=DEDUP_KEY_TTL)
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
            redis_client.set(id_phone_number, json.dumps(user_data), ex=DEDUP_KEY_TTL)
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

        import threading
        from agente_rolplay.messaging.audio_worker import _process_audio_inline

        thread = threading.Thread(
            target=_process_audio_inline, args=(audio_job,), daemon=True
        )
        thread.start()
        print(f"Audio processing started in background thread for: {phone_number}")

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

        file_size = get_media_content_length(media_url)
        if file_size and file_size > MAX_FILE_SIZE_BYTES:
            send_twilio_message(from_number, FILE_TOO_LARGE_MSG["es"])
            redis_client.set(dedup_key, "exists", ex=DEDUP_KEY_TTL)
            return "FileTooLarge"

        send_twilio_message(from_number, "Uploading image to Knowledge Base...")

        temp_path = download_document_from_twilio(
            media_url=media_url, file_name=base_name, file_type=extension
        )

        if not temp_path:
            send_twilio_message(
                from_number, "Sorry, there was an error downloading your image."
            )
            redis_client.set(dedup_key, "exists", ex=DEDUP_KEY_TTL)
            return "ImageError"

        result = upload_file_to_cloudinary(temp_path, folder="knowledgebase")

        vector_id = None
        vectorized = False
        vision_result = None
        filename = f"{base_name}.{extension}"

        if result and result.get("success"):
            vision_result = extract_image_description(temp_path, media_content_type)
            if vision_result.get("success") and vision_result.get("can_vectorize"):
                print(f"Vectorizing image: {filename}")
                pinecone_result = upload_to_pinecone(
                    text=vision_result["text"],
                    filename=filename,
                    file_type="image",
                    metadata={
                        "uploaded_by": phone_number,
                        "cloudinary_url": result.get("secure_url"),
                    },
                )
                if pinecone_result.get("success"):
                    vector_id = pinecone_result.get("vector_id")
                    vectorized = True
                    print(f"Image vectorized: {filename} id={vector_id}")
            else:
                print(f"Image vision extraction failed: {vision_result.get('error')}")

        try:
            os.remove(temp_path)
            print(f"Temporary file deleted: {temp_path}")
        except Exception:
            pass

        if result and result.get("success"):
            store_image_metadata(
                phone_number=phone_number,
                filename=filename,
                cloudinary_url=result.get("secure_url"),
                redis_client=redis_client,
                vector_id=vector_id,
                vectorized=vectorized,
            )
            redis_client.set(
                f"last_uploaded_file:{phone_number}", filename, ex=86400 * 7
            )
            message = "Image uploaded to Knowledge Base! ✅"

            send_twilio_message(from_number, message)

            # Save Document record so dashboard Knowledge Base page shows the image
            try:
                from agente_rolplay.db.database import get_db
                from agente_rolplay.db.models import Document, Profile
                from agente_rolplay.db.whatsapp_auth import normalize_whatsapp_number

                _norm = normalize_whatsapp_number(phone_number)
                _db = next(get_db())
                try:
                    _profile = (
                        _db.query(Profile)
                        .filter(Profile.whatsapp_number == _norm)
                        .first()
                    )
                    if _profile:
                        _db.add(
                            Document(
                                org_id=_profile.org_id,
                                name=filename,
                                drive_file_id=result.get("public_id"),
                            )
                        )
                        _db.commit()
                finally:
                    _db.close()
            except Exception as _doc_err:
                print(f"Warning: could not write Document record for image: {_doc_err}")

            log_message_to_db(phone_number, message_type="image")

            # Record upload in chat history so Claude has context for follow-up questions
            chat_history_id = f"fp-chatHistory:{from_number}"
            add_to_chat_history(
                chat_history_id, f"[Sent image: {filename}]", "user", phone_number
            )
            log_whatsapp_message_to_db(phone_number, "user", f"[Sent image: {filename}]", "image")
            bot_history_msg = f"Image '{filename}' uploaded to Knowledge Base."
            if vectorized and vision_result and vision_result.get("text"):
                bot_history_msg += f" Description: {vision_result['text'][:400]}"
            add_to_chat_history(
                chat_history_id, bot_history_msg, "assistant", phone_number
            )
            log_whatsapp_message_to_db(phone_number, "assistant", bot_history_msg, "image")
        else:
            error_message = result.get("error", "Unknown") if result else "Unknown"
            send_twilio_message(from_number, f"Error uploading image: {error_message}")

        redis_client.set(dedup_key, "exists", ex=DEDUP_KEY_TTL)
        return "ImageProcessed"

    if message_type in ("video", "media"):
        print(f"Unsupported media type received: {media_content_type}")
        send_twilio_message(
            from_number,
            "Sorry, I can't process that file type. I currently support:\n"
            "• Images (JPG, PNG, GIF, WebP)\n"
            "• Documents (PDF, DOCX, PPTX, TXT)\n"
            "• Voice notes\n\n"
            "Please send one of those formats.",
        )
        redis_client.set(dedup_key, "exists", ex=DEDUP_KEY_TTL)
        return "UnsupportedMedia"

    if not redis_client.exists(id_phone_number):
        user_data = {"Usuario": "", "Telefono": phone_number}
        data["user_data"] = user_data
        redis_client.set(id_phone_number, json.dumps(user_data), ex=DEDUP_KEY_TTL)
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
        from agente_rolplay.db.whatsapp_auth import (
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
                    redis_client.set(dedup_key, "exists", ex=DEDUP_KEY_TTL)
                    return "Blocked"
    except Exception as e:
        print(f"Error checking permissions: {e}")

    if _is_rate_limited(phone_number, redis_client):
        print(f"Rate limit exceeded for {phone_number}")
        lang = detect_language(body) if body else "es"
        send_twilio_message(from_number, RATE_LIMIT_MSG[lang])
        redis_client.set(dedup_key, "exists", ex=DEDUP_KEY_TTL)
        return "RateLimited"

    # Acronym disambiguation
    _acronym_pending_key = f"pending_acronym:{phone_number}"
    _pending_acronym = redis_client.get(_acronym_pending_key)

    if _pending_acronym:
        # User is responding to our clarification request — enrich the original query
        _pending = json.loads(_pending_acronym)
        _original_msg = _pending["original_message"]
        _acronym = _pending["acronym"]
        _enriched = f"{_original_msg} [{_acronym} = {body}]"
        data["body"] = _enriched
        body = _enriched
        redis_client.delete(_acronym_pending_key)
        print(f"Acronym '{_acronym}' clarified for {phone_number}: {body[:100]}")
    elif body:
        _acronym, _meanings = detect_ambiguous_acronym(body, ANTHROPIC_API_KEY)
        if _acronym:
            _pending_data = {"original_message": body, "acronym": _acronym}
            redis_client.setex(
                _acronym_pending_key, ACRONYM_PENDING_TTL, json.dumps(_pending_data)
            )
            _options = "\n".join(f"• {m}" for m in _meanings)
            _lang = detect_language(body)
            _clarification = ACRONYM_CLARIFICATION_MSG[_lang].format(
                acronym=_acronym, options=_options
            )
            send_twilio_message(from_number, _clarification)
            redis_client.set(dedup_key, "exists", ex=DEDUP_KEY_TTL)
            return "AcronymClarification"

    if body and is_session_fact(body):
        store_session_fact(phone_number, body)
        print(f"Session fact stored for {phone_number}: {body[:80]}")

    session_facts = get_session_facts(phone_number)
    messages = get_chat_history(chat_history_id, phone=phone_number)
    answer_data = responder_usuario(
        messages,
        data,
        telefono=phone_number,
        id_conversacion=id_conversacion,
        id_phone_number=id_phone_number,
        response_language=current_lang,
        session_facts=session_facts or None,
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

    if len(answer_text) > TWILIO_MESSAGE_MAX_LENGTH:
        answer_text = (
            answer_text[:TWILIO_MESSAGE_MAX_LENGTH]
            + "\n\n... (truncated response)\nAsk a more specific question for details."
        )
        print(
            f"Response truncated from {len(answer_data['answer'])} to {TWILIO_MESSAGE_MAX_LENGTH} characters"
        )

    send_result = send_twilio_message(
        from_number,
        answer_text,
    )

    if not send_result.get("success", False):
        print(
            f"WARNING: Message not sent. Error: {send_result.get('error', 'Unknown')}"
        )
        log_message_to_db(phone_number, message_type="text", is_error=True)
        return "SendError"

    log_chat_interaction(
        phone_number=phone_number,
        user_message=body,
        bot_response=answer_text,
        message_type="query",
        language=current_lang,
    )
    log_message_to_db(
        phone_number,
        message_type="text",
        is_rag_query=bool(answer_data.get("used_rag", False)),
    )

    redis_client.set(dedup_key, "exists", ex=DEDUP_KEY_TTL)
    print(f"Message marked as processed: {dedup_key}")

    add_to_chat_history(chat_history_id, body, "user", phone_number)
    log_whatsapp_message_to_db(phone_number, "user", body)
    add_to_chat_history(
        chat_history_id, answer_data["answer"], "assistant", phone_number
    )
    log_whatsapp_message_to_db(phone_number, "assistant", answer_data["answer"])

    print("Processing completed successfully.")
    return "Success"
