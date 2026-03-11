"""
Audio transcription module using OpenAI Whisper API.
Converts WhatsApp voice notes to text.
"""

from openai import OpenAI

import os
import requests
import tempfile
import time
import traceback

from src.agente_rolplay.config import OPENAI_API_KEY, TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN

client = OpenAI(api_key=OPENAI_API_KEY)


def transcribe_audio_from_url(
    media_url: str,
    phone: str,
    provider: str = "openai",
    dest_dir: str = "./storage/audio",
    timeout: int = 180,
) -> dict:
    """
    Transcribe audio from a Twilio media URL using OpenAI Whisper API.

    Args:
        media_url (str): Twilio encrypted media URL
        phone (str): Phone number for metadata/organization
        provider (str): Transcription provider ('openai' supported)
        dest_dir (str): Directory to store audio files
        timeout (int): Request timeout in seconds (default: 180s for Whisper API)

    Returns:
        dict: {
            'text': str (transcription text or error message),
            'duration_s': int (audio duration),
            'model': str (model used),
            'ok': bool (success flag),
            'error': Optional[str] (error message if ok=False),
            'file_path': str (stored audio file path if retained)
        }

    Example:
        result = transcribe_audio_from_url(
            media_url='https://api.twilio.com/...',
            phone='5215512345678'
        )
    """
    temp_file_path = None
    stored_file_path = None

    try:
        print(f"Starting transcription for: {phone}")
        start_time = time.time()

        # 1. DOWNLOAD AUDIO FROM TWILIO
        print(f"Downloading audio from: {media_url[:60]}...")
        response = requests.get(
            media_url, auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN), timeout=30
        )

        if response.status_code != 200:
            error_msg = f"Twilio download failed: {response.status_code}"
            print(f"Error: {error_msg}")
            return {
                "text": f"Error descargando audio: {response.status_code}",
                "duration_s": 0,
                "model": "whisper-1",
                "ok": False,
                "error": error_msg,
            }

        # 2. SAVE TEMPORARILY
        audio_data = response.content
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp_file:
            tmp_file.write(audio_data)
            temp_file_path = tmp_file.name

        print(
            f"Temporary audio saved: {temp_file_path} ({len(audio_data) / 1024:.1f} KB)"
        )

        # 3. ESTIMATE DURATION (without librosa to reduce deps)
        try:
            # Simple approximation: 128 kbps * 1024 bytes/sec
            duration_seconds = max(1, (len(audio_data) / (128 * 1024)))
            duration_seconds = int(duration_seconds)
        except Exception:
            duration_seconds = 0

        print(f"Estimated duration: {duration_seconds}s")

        # 4. TRANSCRIBE WITH WHISPER
        print("Sending to OpenAI Whisper for transcription...")
        with open(temp_file_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1", file=audio_file, timeout=timeout
            )

        transcript_text = transcript.text.strip()
        print(f"Transcription successful: {transcript_text[:80]}...")

        # 5. SAVE AUDIO PERMANENTLY (if configured)
        os.makedirs(dest_dir, exist_ok=True)
        timestamp_str = time.strftime("%Y%m%d_%H%M%S")

        try:
            stored_file_path = os.path.join(dest_dir, f"{phone}_{timestamp_str}.ogg")

            with open(stored_file_path, "wb") as f:
                f.write(audio_data)

            print(f"Permanent audio stored: {stored_file_path}")
        except Exception as e:
            print(f"Warning: Could not save audio permanently: {e}")
            stored_file_path = None

        elapsed = time.time() - start_time
        print(f"Transcription completed in {elapsed:.2f}s")

        return {
            "text": transcript_text,
            "duration_s": duration_seconds,
            "model": "whisper-1",
            "ok": True,
            "error": None,
            "file_path": stored_file_path,
        }

    except requests.Timeout:
        error = "Twilio download timeout (30s)"
        print(f"Error: {error}")
        return {
            "text": "Error: descarga del audio expiró.",
            "duration_s": 0,
            "model": "whisper-1",
            "ok": False,
            "error": error,
        }

    except Exception as e:
        error = f"{type(e).__name__}: {str(e)}"
        print(f"Error in transcription: {error}")
        traceback.print_exc()
        return {
            "text": "Error procesando tu audio. Intenta de nuevo.",
            "duration_s": 0,
            "model": "whisper-1",
            "ok": False,
            "error": error,
        }

    finally:
        # CLEANUP TEMPORARY FILE
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
                print(f"Temporary file removed: {temp_file_path}")
            except Exception as e:
                print(f"Warning: Could not clean up temp file: {e}")
