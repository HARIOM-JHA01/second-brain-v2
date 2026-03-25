"""
Celery worker to process WhatsApp voice notes in the background.
Transcribes audio and feeds the existing chat pipeline.

Usage:
    celery -A audio_worker worker --loglevel=info --concurrency=1 --queues=audio
"""

from celery import Celery, Task
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

    # Extract from_number before try so it's available in the except block
    from_number = job_dict.get("from")

    try:
        media_url = job_dict.get("media_url")
        phone_number = job_dict.get("phone_number")
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

        from agente_rolplay.messaging.message_processor import process_incoming_messages
        transcribed_sid = f"{message_sid}:tx" if message_sid else f"audio-tx-{int(time.time())}"
        transcribed_form_data = {
            "From": from_number,
            "To": job_dict.get("to", ""),
            "Body": transcript_text,
            "MessageSid": transcribed_sid,
            "NumMedia": "0",
            "ProfileName": user_data.get("Usuario", ""),
        }
        _t0 = time.time()
        process_incoming_messages(transcribed_form_data, redis_client=redis_client)
        _response_ms = int((time.time() - _t0) * 1000)

        log_message_to_db(phone_number, message_type="audio", is_voice_note=True, response_time_ms=_response_ms)
        logger.info(f"Audio processed successfully for: {phone_number}")
        return {"status": "ok", "transcript": transcript_text}

    except Exception as e:
        logger.error(f"Error processing audio inline: {e}", exc_info=True)
        if from_number:
            try:
                enviar_mensaje_twilio(
                    from_number,
                    "❌ There was an error processing your voice note. Please try again or send a text message.",
                )
            except Exception:
                pass
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

        # 2. INJECT TRANSCRIPTION INTO THE STANDARD MESSAGE PIPELINE
        logger.info("Injecting transcription into standard message pipeline...")
        from agente_rolplay.messaging.message_processor import process_incoming_messages
        transcribed_sid = f"{message_sid}:tx" if message_sid else f"audio-tx-{int(time.time())}"
        transcribed_form_data = {
            "From": from_number,
            "To": job_dict.get("to", ""),
            "Body": transcript_text,
            "MessageSid": transcribed_sid,
            "NumMedia": "0",
            "ProfileName": user_data.get("Usuario", ""),
        }
        _t0 = time.time()
        process_incoming_messages(transcribed_form_data, redis_client=redis_client)
        _response_ms = int((time.time() - _t0) * 1000)

        log_message_to_db(phone_number, message_type="audio", is_voice_note=True, response_time_ms=_response_ms)
        logger.info(f"Audio processed and routed successfully for: {phone_number}")

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
