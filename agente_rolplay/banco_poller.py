"""
banco_poller.py

Polls the Banco sessions API on a configurable interval, finds the latest
session completed by a Salinas user (banco_user_id != null), and sends a
formatted WhatsApp report to the configured phone number via Twilio.

Also stores the session plain-text in Redis so the recipient can ask
natural-language questions about it and get AI answers.
"""

import json
import logging
import re
import threading
import time
from html import unescape

import redis
import requests
from anthropic import Anthropic

from agente_rolplay.config import (
    ANTHROPIC_API_KEY,
    BANCO_API_URL,
    BANCO_POLL_INTERVAL,
    BANCO_POLL_PHONE,
    HAIKU_MODEL_NAME,
    redis_connection_kwargs,
)
from agente_rolplay.messaging.twilio_client import send_twilio_message

_anthropic = Anthropic(api_key=ANTHROPIC_API_KEY)

logger = logging.getLogger(__name__)

BANCO_LAST_SENT_KEY = "banco:last_sent_id"
BANCO_SESSION_CONTEXT_TTL = 86400  # 24 hours


# ---------------------------------------------------------------------------
# HTML → plain text
# ---------------------------------------------------------------------------

def _html_to_text(html: str) -> str:
    """Strip all HTML and return full plain-text content."""
    # Remove <style> and <script> blocks entirely ([\s\S] matches \r and \n)
    html = re.sub(
        r"<(style|script)[^>]*>[\s\S]*?</(style|script)>",
        "",
        html,
        flags=re.IGNORECASE,
    )
    # Closing block tags → newline so sections are separated
    html = re.sub(
        r"</(p|h[1-6]|div|li|td|th|tr|thead|tbody|section|article)>",
        "\n",
        html,
        flags=re.IGNORECASE,
    )
    # <br> → newline
    html = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
    # Strip all remaining tags
    text = re.sub(r"<[^>]+>", "", html)
    # Decode HTML entities (&amp; &eacute; &#x27; etc.)
    text = unescape(text)
    # Collapse horizontal whitespace, normalise blank lines
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# ---------------------------------------------------------------------------
# Session helpers
# ---------------------------------------------------------------------------

def _get_latest_salinas_session(sessions: list) -> dict | None:
    """Return the session with the highest id where banco_user_id is not None."""
    salinas = [s for s in sessions if s.get("banco_user_id") is not None]
    if not salinas:
        return None
    return max(salinas, key=lambda s: s["id"])


def _summarize(plain_text: str, emp_name: str) -> str:
    """Use Claude Haiku to produce a concise WhatsApp-friendly summary."""
    try:
        resp = _anthropic.messages.create(
            model=HAIKU_MODEL_NAME,
            max_tokens=600,
            messages=[{
                "role": "user",
                "content": (
                    f"Resume esta evaluación de sesión de coaching para {emp_name} "
                    "en un mensaje corto para WhatsApp (texto plano, sin HTML, sin markdown "
                    "excepto *negrita* para títulos de sección). Cubre: resultado general, "
                    "aprendizajes clave, principales áreas de mejora y recomendación principal. "
                    "Sé conciso — máximo 150 palabras. Responde siempre en español.\n\n"
                    f"{plain_text}"
                ),
            }],
        )
        return resp.content[0].text.strip()
    except Exception:
        logger.exception("Summarization failed, using full plain text")
        return plain_text


def _format_whatsapp_message(record: dict) -> str:
    emp_name = record.get("banco_emp_name", "Unknown")
    emp_id = record.get("banco_emp_id", "N/A")
    date_str = (record.get("date_created") or "")[:10]
    session_id = record.get("id")

    plain = _html_to_text(record.get("closingretro", ""))
    summary = _summarize(plain, emp_name)

    header = (
        f"*Session Report #{session_id}*\n"
        f"Employee: {emp_name} (ID: {emp_id})\n"
        f"Date: {date_str}\n"
        f"{'─' * 28}\n\n"
    )
    return header + summary


# ---------------------------------------------------------------------------
# Polling loop
# ---------------------------------------------------------------------------

def _poll_loop(redis_client: redis.Redis) -> None:
    bare_phone = BANCO_POLL_PHONE.lstrip("+")
    logger.info(
        "Banco poller started — interval=%ss, phone=%s",
        BANCO_POLL_INTERVAL,
        BANCO_POLL_PHONE,
    )

    while True:
        try:
            resp = requests.get(BANCO_API_URL, timeout=15)
            resp.raise_for_status()
            sessions = resp.json()

            latest = _get_latest_salinas_session(sessions)
            if latest is None:
                logger.debug("No salinas sessions found yet.")
            else:
                last_sent_raw = redis_client.get(BANCO_LAST_SENT_KEY)
                last_sent_id = int(last_sent_raw) if last_sent_raw else -1

                if latest["id"] > last_sent_id:
                    logger.info(
                        "New salinas session id=%s — sending to %s",
                        latest["id"],
                        BANCO_POLL_PHONE,
                    )

                    msg = _format_whatsapp_message(latest)
                    send_twilio_message(f"whatsapp:{BANCO_POLL_PHONE}", msg)

                    # Store plain-text context for Q&A
                    context = {
                        "id": latest["id"],
                        "emp_name": latest.get("banco_emp_name"),
                        "emp_id": latest.get("banco_emp_id"),
                        "date": (latest.get("date_created") or "")[:10],
                        "plain_text": _html_to_text(latest.get("closingretro", "")),
                    }
                    redis_client.set(
                        f"banco:session_context:{bare_phone}",
                        json.dumps(context),
                        ex=BANCO_SESSION_CONTEXT_TTL,
                    )
                    redis_client.set(BANCO_LAST_SENT_KEY, str(latest["id"]))
                    logger.info("Session #%s sent and context stored.", latest["id"])
                else:
                    logger.debug(
                        "No new session. Latest id=%s, last_sent=%s",
                        latest["id"],
                        last_sent_id,
                    )
        except Exception:
            logger.exception("Banco poller error")

        time.sleep(BANCO_POLL_INTERVAL)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def start_poller() -> None:
    """Start the banco polling loop in a background daemon thread."""
    redis_client = redis.Redis(**redis_connection_kwargs())
    thread = threading.Thread(
        target=_poll_loop,
        args=(redis_client,),
        daemon=True,
        name="banco-poller",
    )
    thread.start()
    logger.info("Banco poller thread started.")
