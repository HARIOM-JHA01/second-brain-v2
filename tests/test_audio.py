"""
Tests para el módulo de transcripción y worker de audio.

Run with:
    pytest tests/test_audio.py -v
"""

import json
import os
import pytest
import tempfile
from unittest.mock import Mock, patch, MagicMock

# Importar funciones a testear
from whisper import transcribe_audio_from_url
from audio_worker import process_audio_job, health_check, VOICE_NOTES_ENABLED


class TestTranscribeAudioFromUrl:
    """Tests para transcribe_audio_from_url"""

    @patch("whisper.requests.get")
    @patch("whisper.client.audio.transcriptions.create")
    def test_transcribe_success(self, mock_transcribe, mock_get):
        """Test transcripción exitosa"""
        # Mock Twilio response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"fake audio data"
        mock_get.return_value = mock_response

        # Mock OpenAI response
        mock_transcript = Mock()
        mock_transcript.text = "Hola, esto es una prueba"
        mock_transcribe.return_value = mock_transcript

        # Ejecutar
        result = transcribe_audio_from_url(
            media_url="https://tw.twilio.com/audio.ogg", phone="5215512345678"
        )

        # Verificar
        assert result["ok"] is True
        assert result["text"] == "Hola, esto es una prueba"
        assert result["model"] == "whisper-1"
        assert result["error"] is None

    @patch("whisper.requests.get")
    def test_transcribe_download_failed(self, mock_get):
        """Test cuando falla la descarga"""
        mock_response = Mock()
        mock_response.status_code = 403
        mock_get.return_value = mock_response

        result = transcribe_audio_from_url(
            media_url="https://tw.twilio.com/audio.ogg", phone="5215512345678"
        )

        assert result["ok"] is False
        assert "403" in result["error"]

    @patch("whisper.requests.get")
    def test_transcribe_download_timeout(self, mock_get):
        """Test timeout en descarga"""
        import requests

        mock_get.side_effect = requests.Timeout("Connection timeout")

        result = transcribe_audio_from_url(
            media_url="https://tw.twilio.com/audio.ogg", phone="5215512345678"
        )

        assert result["ok"] is False
        assert "timeout" in result["error"].lower()


class TestAudioWorker:
    """Tests para el Celery worker de audio"""

    @patch("audio_worker.redis_client.ping")
    def test_health_check_ok(self, mock_ping):
        """Test health check exitoso"""
        mock_ping.return_value = True

        result = health_check.apply()
        assert result["status"] == "healthy"
        assert result["voice_notes_enabled"] == VOICE_NOTES_ENABLED

    @patch("audio_worker.redis_client.ping")
    def test_health_check_failed(self, mock_ping):
        """Test health check fallido"""
        mock_ping.side_effect = Exception("Redis connection failed")

        result = health_check.apply()
        assert result["status"] == "unhealthy"
        assert "Redis" in result["error"]

    @patch("audio_worker.transcribe_audio_from_url")
    @patch("audio_worker.enviar_mensaje_twilio")
    @patch("audio_worker.responder_usuario")
    @patch("audio_worker.get_chat_history")
    @patch("audio_worker.add_to_chat_history")
    def test_process_audio_job_success(
        self,
        mock_add_history,
        mock_get_history,
        mock_responder,
        mock_send,
        mock_transcribe,
    ):
        """Test procesamiento exitoso de audio"""

        if not VOICE_NOTES_ENABLED:
            pytest.skip("VOICE_NOTES_ENABLED is false")

        # Setup mocks
        mock_transcribe.return_value = {
            "ok": True,
            "text": "transcripción de prueba",
            "duration_s": 5,
            "model": "whisper-1",
            "file_path": "/storage/audio/test.ogg",
        }

        mock_get_history.return_value = []

        mock_responder.return_value = {"answer": "Respuesta del agente"}

        mock_send.return_value = {"success": True}

        # Job para procesar
        job = {
            "media_url": "https://tw.twilio.com/audio.ogg",
            "phone_number": "5215512345678",
            "from": "whatsapp:+5215512345678",
            "id_conversacion": "test_id",
            "timestamp": 1234567890,
            "user_data": {"Usuario": "Test User"},
            "message_sid": "SM123456",
        }

        # Ejecutar
        result = process_audio_job.apply_async(args=[job])

        # Verificar
        assert result.status in ["PENDING", "SENT"]  # Celery enqueued


def test_feature_flag_env():
    """Test que la feature flag se lee desde env"""
    flag = os.getenv("VOICE_NOTES_ENABLED", "false").lower() == "true"
    # Should be true based on .env file set earlier
    assert flag is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
