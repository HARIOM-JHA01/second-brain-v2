"""
Celery worker to process WhatsApp voice notes in the background.
Transcribes audio and feeds the existing chat pipeline.

Usage:
    celery -A audio_worker worker --loglevel=info --concurrency=1 --queues=audio
"""

from agente_rolplay.agent.roleplay_agent import responder_usuario
from celery import Celery, Task
from agente_rolplay.messaging.chat_history_manager import (
    add_to_chat_history,
    get_chat_history,
)
from datetime import datetime
from agente_rolplay.messaging.process_messages import enviar_mensaje_twilio
from agente_rolplay.messaging.whisper_service import transcribe_audio_from_url
from agente_rolplay.storage.analytics_logger import log_message_to_db

import json
import redis
import logging
import time

from agente_rolplay.config import (
    build_redis_url,
    redis_connection_kwargs,
    VOICE_NOTES_ENABLED,
)

# ===== CONFIGURATION =====
CELERY_BROKER_URL = build_redis_url(0)
CELERY_RESULT_BACKEND = build_redis_url(1)

# Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ===== CREATE CELERY APP =====
class ContextTask(Task):
    """Task that preserves Redis context"""

    def __call__(self, *args, **kwargs):
        return self.run(*args, **kwargs)


app = Celery("audio_worker")
app.conf.broker_url = CELERY_BROKER_URL
app.conf.result_backend = CELERY_RESULT_BACKEND
app.conf.task_serializer = "json"
app.conf.accept_content = ["json"]
app.conf.result_serializer = "json"
app.conf.task_track_started = True
app.conf.task_time_limit = 5 * 60  # 5 minutes max
app.Task = ContextTask

# Redis client
redis_client = redis.Redis(
    **redis_connection_kwargs(),
)


def _process_audio_inline(job_dict: dict) -> dict:
    """
    Process a voice note synchronously (no Celery). Called from a background thread.
    Transcribes audio and feeds the existing chat pipeline.
    """
    if not VOICE_NOTES_ENABLED:
        logger.warning("VOICE_NOTES_ENABLED is disabled")
        return {"status": "failed", "error": "Feature disabled"}

    try:
        media_url = job_dict.get("media_url")
        phone_number = job_dict.get("phone_number")
        from_number = job_dict.get("from")
        id_conversacion = job_dict.get("id_conversacion")
        timestamp = job_dict.get("timestamp")
        user_data = job_dict.get("user_data", {})
        message_sid = job_dict.get("message_sid")

        logger.info(f"Processing audio inline for: {phone_number}")

        transcription_result = transcribe_audio_from_url(
            media_url=media_url, phone=phone_number, provider="openai"
        )

        if not transcription_result.get("ok", False):
            error_msg = transcription_result.get("error", "Unknown error")
            logger.error(f"Transcription failed: {error_msg}")
            try:
                enviar_mensaje_twilio(
                    from_number,
                    f"❌ No pude transcribir tu nota de voz. Error: {error_msg[:50]}",
                )
            except Exception as e:
                logger.error(f"Could not send error message: {e}")
            return {"status": "failed", "error": error_msg}

        transcript_text = transcription_result.get("text", "")
        logger.info(f"Transcription: {transcript_text[:80]}...")

        data = {
            "id": message_sid,
            "from": from_number,
            "body": transcript_text,
            "fromMe": False,
            "type": "text",
            "pushName": user_data.get("Usuario", ""),
            "timestamp": timestamp,
            "user_data": user_data,
            "media": media_url,
            "media_content_type": "audio/ogg",
        }

        id_chat_history = f"fp-chatHistory:{from_number}"
        id_phone_number = f"fp-idPhone:{phone_number}"
        messages = get_chat_history(id_chat_history, phone=phone_number)

        _t0 = time.time()
        answer_data = responder_usuario(
            messages,
            data,
            telefono=phone_number,
            id_conversacion=id_conversacion,
            id_phone_number=id_phone_number,
        )
        _response_ms = int((time.time() - _t0) * 1000)

        resultado_envio = enviar_mensaje_twilio(
            from_number, str(answer_data.get("answer", "Sin respuesta"))
        )

        if not resultado_envio.get("success", False):
            logger.error(f"Could not send response: {resultado_envio.get('error')}")

        add_to_chat_history(id_chat_history, transcript_text, "user", phone_number)
        add_to_chat_history(
            id_chat_history, answer_data.get("answer", ""), "assistant", phone_number
        )

        log_message_to_db(phone_number, message_type="audio", is_voice_note=True, response_time_ms=_response_ms)
        logger.info(f"Audio processed successfully for: {phone_number}")
        return {"status": "ok", "transcript": transcript_text}

    except Exception as e:
        logger.error(f"Error processing audio inline: {e}", exc_info=True)
        return {"status": "failed", "error": str(e)}


@app.task(name="audio_worker.process_audio_job", bind=True, max_retries=2)
def process_audio_job(self, job_dict: dict) -> dict:
    """
    Process a voice note: download, transcribe, respond.

    Args:
        job_dict: {
            'media_url': str,
            'phone_number': str,
            'from': str (whatsapp:+521551234567id_conversacion': str,
           8),
            ' 'timestamp': int,
            'user_data': dict,
            'message_sid': str
        }

    Returns:
        {
            'status': 'ok' | 'failed',
            'transcript': str,
            'reply_sent': bool,
            'message_sid': str,
            'error': Optional[str]
        }
    """

    if not VOICE_NOTES_ENABLED:
        logger.warning("VOICE_NOTES_ENABLED is disabled")
        return {
            "status": "failed",
            "transcript": "",
            "reply_sent": False,
            "message_sid": job_dict.get("message_sid"),
            "error": "Feature disabled",
        }

    try:
        logger.info(f"Processing audio for: {job_dict.get('phone_number')}")

        # Extract fields from job
        media_url = job_dict.get("media_url")
        phone_number = job_dict.get("phone_number")
        from_number = job_dict.get("from")
        id_conversacion = job_dict.get("id_conversacion")
        timestamp = job_dict.get("timestamp")
        user_data = job_dict.get("user_data", {})
        message_sid = job_dict.get("message_sid")

        # 1. TRANSCRIBE AUDIO
        logger.info("Transcribing audio...")
        transcription_result = transcribe_audio_from_url(
            media_url=media_url, phone=phone_number, provider="openai"
        )

        if not transcription_result.get("ok", False):
            error_msg = transcription_result.get("error", "Unknown error")
            logger.error(f"Transcription failed: {error_msg}")

            # Notify user of error
            try:
                enviar_mensaje_twilio(
                    from_number,
                    f"❌ No pude transcribir tu nota de voz. Error: {error_msg[:50]}",
                )
            except Exception as e:
                logger.error(f"Could not send error message: {e}")

            return {
                "status": "failed",
                "transcript": "",
                "reply_sent": False,
                "message_sid": message_sid,
                "error": error_msg,
            }

        transcript_text = transcription_result.get("text", "")
        logger.info(f"Transcription successful: {transcript_text[:80]}...")

        # 2. INJECT INTO CHAT PIPELINE
        logger.info("Injecting transcription into pipeline...")

        # Build data compatible with responder_usuario
        data = {
            "id": message_sid,
            "from": from_number,
            "body": transcript_text,  # The transcription is the "body"
            "fromMe": False,
            "type": "text",  # Treat as text after transcribing
            "pushName": user_data.get("Usuario", ""),
            "timestamp": timestamp,
            "user_data": user_data,
            "media": media_url,
            "media_content_type": "audio/ogg",
        }

        # Get history
        id_chat_history = f"fp-chatHistory:{from_number}"
        id_phone_number = f"fp-idPhone:{phone_number}"
        messages = get_chat_history(id_chat_history, phone=phone_number)

        # 3. GENERATE RESPONSE WITH AGENT
        logger.info("Generating response...")
        _t0 = time.time()
        answer_data = responder_usuario(
            messages,
            data,
            telefono=phone_number,
            id_conversacion=id_conversacion,
            id_phone_number=id_phone_number,
        )
        _response_ms = int((time.time() - _t0) * 1000)

        logger.info(f"Response generated: {str(answer_data.get('answer', ''))[:80]}...")

        # 4. SEND RESPONSE TO USER
        logger.info("Sending response...")
        resultado_envio = enviar_mensaje_twilio(
            from_number, str(answer_data.get("answer", "Sin respuesta"))
        )

        if not resultado_envio.get("success", False):
            logger.error(f"Could not send response: {resultado_envio.get('error')}")
            log_message_to_db(phone_number, message_type="audio", is_voice_note=True, response_time_ms=_response_ms, is_error=True)
            return {
                "status": "failed",
                "transcript": transcript_text,
                "reply_sent": False,
                "message_sid": message_sid,
                "error": f"Send failed: {resultado_envio.get('error')}",
            }

        # 5. SAVE TO CHAT HISTORY
        logger.info("Saving to history...")
        add_to_chat_history(id_chat_history, transcript_text, "user", phone_number)
        add_to_chat_history(
            id_chat_history, answer_data.get("answer", ""), "assistant", phone_number
        )

        log_message_to_db(phone_number, message_type="audio", is_voice_note=True, response_time_ms=_response_ms)
        logger.info(f"Audio processed and responded successfully for: {phone_number}")

        return {
            "status": "ok",
            "transcript": transcript_text,
            "reply_sent": True,
            "message_sid": message_sid,
            "error": None,
        }

    except Exception as e:
        logger.error(f"Error processing audio: {e}", exc_info=True)

        # Retry if max not reached
        try:
            raise self.retry(exc=e, countdown=5)
        except Exception:
            return {
                "status": "failed",
                "transcript": "",
                "reply_sent": False,
                "message_sid": job_dict.get("message_sid"),
                "error": str(e),
            }


@app.task(name="audio_worker.health_check")
def health_check() -> dict:
    """
    Healthcheck task to monitor the worker.
    """
    try:
        redis_client.ping()
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "voice_notes_enabled": VOICE_NOTES_ENABLED,
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


def main():
    """
    Entry point to run the worker manually.

    Usage:
        python audio_worker.py  # Runs worker indefinitely
        python audio_worker.py --once  # Processes one job and exits
    """
    import sys

    if "--once" in sys.argv:
        # Single execution mode (useful for CI/tests)
        logger.info("Running in --once mode (processes one job and exits)...")

        # Try to process a job from the queue
        try:
            job_json = redis_client.rpop("audio_queue")
            if job_json:
                job_dict = json.loads(job_json)
                logger.info(f"Processing job: {job_dict.get('message_sid')}")
                result = process_audio_job.apply_async(args=[job_dict])
                logger.info(f"Job sent to Celery: {result.id}")
            else:
                logger.info("No jobs in the queue")
        except Exception as e:
            logger.error(f"Error in --once mode: {e}")
    else:
        # Normal worker mode
        logger.info("Starting Celery worker...")
        logger.info(f"Broker: {CELERY_BROKER_URL}")
        logger.info(f"Feature: VOICE_NOTES_ENABLED={VOICE_NOTES_ENABLED}")

        app.worker_main(
            argv=["worker", "--loglevel=info", "--concurrency=1", "--queues=audio"]
        )


if __name__ == "__main__":
    main()
