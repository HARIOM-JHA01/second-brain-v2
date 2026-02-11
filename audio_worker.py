"""
Celery worker para procesar notas de voz de WhatsApp en segundo plano.
Transcribe audio y alimenta la pipeline de chat existente.

Usage:
    celery -A audio_worker worker --loglevel=info --concurrency=1 --queues=audio
"""

from agente_roleplay import responder_usuario
from celery import Celery, Task
from chat_history import add_to_chat_history, get_chat_history
from datetime import datetime
from dotenv import load_dotenv
from procesa_mensajes import enviar_mensaje_twilio
from whisper import transcribe_audio_from_url

import json
import os
import redis
import logging

load_dotenv()

# ===== CONFIGURACIÓN =====
VOICE_NOTES_ENABLED = os.getenv("VOICE_NOTES_ENABLED", "false").lower() == "true"
REDIS_HOST = os.getenv("REDIS_HOST")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")

# Redis Broker para Celery
CELERY_BROKER_URL = f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/0"
CELERY_RESULT_BACKEND = f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/1"

# Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ===== CREAR APP CELERY =====
class ContextTask(Task):
    """Task que preserva contexto de Redis"""

    def __call__(self, *args, **kwargs):
        return self.run(*args, **kwargs)


app = Celery("audio_worker")
app.conf.broker_url = CELERY_BROKER_URL
app.conf.result_backend = CELERY_RESULT_BACKEND
app.conf.task_serializer = "json"
app.conf.accept_content = ["json"]
app.conf.result_serializer = "json"
app.conf.task_track_started = True
app.conf.task_time_limit = 5 * 60  # 5 minutos max
app.Task = ContextTask

# Redis client
redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    decode_responses=True,
    username="default",
    password=REDIS_PASSWORD,
)


@app.task(name="audio_worker.process_audio_job", bind=True, max_retries=2)
def process_audio_job(self, job_dict: dict) -> dict:
    """
    Procesa una nota de voz: descarga, transcribe, responde.

    Args:
        job_dict: {
            'media_url': str,
            'phone_number': str,
            'from': str (whatsapp:+5215512345678),
            'id_conversacion': str,
            'timestamp': int,
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
        logger.warning("🔇 VOICE_NOTES_ENABLED está deshabilitado")
        return {
            "status": "failed",
            "transcript": "",
            "reply_sent": False,
            "message_sid": job_dict.get("message_sid"),
            "error": "Feature disabled",
        }

    try:
        logger.info(f"🎙️ Procesando audio para: {job_dict.get('phone_number')}")

        # Extraer campos del job
        media_url = job_dict.get("media_url")
        phone_number = job_dict.get("phone_number")
        from_number = job_dict.get("from")
        id_conversacion = job_dict.get("id_conversacion")
        timestamp = job_dict.get("timestamp")
        user_data = job_dict.get("user_data", {})
        message_sid = job_dict.get("message_sid")

        # 1️⃣ TRANSCRIBIR AUDIO
        logger.info(f"📥 Transcribiendo audio...")
        transcription_result = transcribe_audio_from_url(
            media_url=media_url, phone=phone_number, provider="openai"
        )

        if not transcription_result.get("ok", False):
            error_msg = transcription_result.get("error", "Unknown error")
            logger.error(f"❌ Transcripción falló: {error_msg}")

            # Notificar al usuario del error
            try:
                enviar_mensaje_twilio(
                    from_number,
                    f"❌ No pude transcribir tu nota de voz. Error: {error_msg[:50]}",
                )
            except Exception as e:
                logger.error(f"⚠️ No se pudo enviar mensaje de error: {e}")

            return {
                "status": "failed",
                "transcript": "",
                "reply_sent": False,
                "message_sid": message_sid,
                "error": error_msg,
            }

        transcript_text = transcription_result.get("text", "")
        logger.info(f"✅ Transcripción exitosa: {transcript_text[:80]}...")

        # 2️⃣ INYECTAR EN PIPELINE DE CHAT
        logger.info(f"🔄 Inyectando transcripción en pipeline...")

        # Construir data compatible con responder_usuario
        data = {
            "id": message_sid,
            "from": from_number,
            "body": transcript_text,  # La transcripción es el "body"
            "fromMe": False,
            "type": "text",  # Tratar como texto después de transcribir
            "pushName": user_data.get("Usuario", ""),
            "timestamp": timestamp,
            "user_data": user_data,
            "media": media_url,
            "media_content_type": "audio/ogg",
        }

        # Obtener historial
        id_chat_history = f"fp-chatHistory:{from_number}"
        id_phone_number = f"fp-idPhone:{phone_number}"
        messages = get_chat_history(id_chat_history, telefono=phone_number)

        # 3️⃣ GENERAR RESPUESTA CON EL AGENTE
        logger.info(f"🤖 Generando respuesta...")
        answer_data = responder_usuario(
            messages,
            data,
            telefono=phone_number,
            id_conversacion=id_conversacion,
            id_phone_number=id_phone_number,
        )

        logger.info(
            f"✅ Respuesta generada: {str(answer_data.get('answer', ''))[:80]}..."
        )

        # 4️⃣ ENVIAR RESPUESTA AL USUARIO
        logger.info(f"📤 Enviando respuesta...")
        resultado_envio = enviar_mensaje_twilio(
            from_number, str(answer_data.get("answer", "Sin respuesta"))
        )

        if not resultado_envio.get("success", False):
            logger.error(
                f"⚠️ No se pudo enviar respuesta: {resultado_envio.get('error')}"
            )
            return {
                "status": "failed",
                "transcript": transcript_text,
                "reply_sent": False,
                "message_sid": message_sid,
                "error": f"Send failed: {resultado_envio.get('error')}",
            }

        # 5️⃣ REGISTRAR EN HISTORIAL DE CHAT
        logger.info(f"💾 Guardando en historial...")
        add_to_chat_history(id_chat_history, transcript_text, "user", phone_number)
        add_to_chat_history(
            id_chat_history, answer_data.get("answer", ""), "assistant", phone_number
        )

        logger.info(
            f"✅ Audio procesado y respondido exitosamente para: {phone_number}"
        )

        return {
            "status": "ok",
            "transcript": transcript_text,
            "reply_sent": True,
            "message_sid": message_sid,
            "error": None,
        }

    except Exception as e:
        logger.error(f"❌ Error procesando audio: {e}", exc_info=True)

        # Reintentar si no ha alcanzado el máximo
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
    Healthcheck task para monitorear el worker.
    """
    try:
        redis_client.ping()
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "voice_notes_enabled": VOICE_NOTES_ENABLED,
        }
    except Exception as e:
        logger.error(f"❌ Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


def main():
    """
    Punto de entrada para ejecutar el worker manualmente.

    Usage:
        python audio_worker.py  # Ejecuta worker indefinidamente
        python audio_worker.py --once  # Procesa un job y sale
    """
    import sys

    if "--once" in sys.argv:
        # Modo una sola ejecución (útil para CI/tests)
        logger.info("🔄 Ejecutando en modo --once (procesa un job y sale)...")

        # Intentar procesar un job de la queue
        try:
            job_json = redis_client.rpop("audio_queue")
            if job_json:
                job_dict = json.loads(job_json)
                logger.info(f"📌 Procesando job: {job_dict.get('message_sid')}")
                result = process_audio_job.apply_async(args=[job_dict])
                logger.info(f"✅ Job enviado a Celery: {result.id}")
            else:
                logger.info("⏭️  No hay jobs en la queue")
        except Exception as e:
            logger.error(f"❌ Error en modo --once: {e}")
    else:
        # Modo worker normal
        logger.info("🚀 Iniciando Celery worker...")
        logger.info(f"🎯 Broker: {CELERY_BROKER_URL}")
        logger.info(f"📋 Feature: VOICE_NOTES_ENABLED={VOICE_NOTES_ENABLED}")

        app.worker_main(
            argv=["worker", "--loglevel=info", "--concurrency=1", "--queues=audio"]
        )


if __name__ == "__main__":
    main()
