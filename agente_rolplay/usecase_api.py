import re

import requests
from loguru import logger

API_BASE = "https://rolplay.pro/banco/get-sessions-list.php"
TIMEOUT = 10  # seconds


def _strip_html(html: str) -> str:
    """Remove HTML tags and collapse whitespace."""
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&#?\w+;", "", text)  # remaining HTML entities
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def fetch_latest_session_context(usecase_id: int) -> str | None:
    """
    Fetches all sessions for a use case and returns a plain-text
    summary of the most recent one, or None on failure.
    """
    try:
        resp = requests.get(API_BASE, params={"id": usecase_id}, timeout=TIMEOUT)
        resp.raise_for_status()
        sessions = resp.json()
        if not sessions:
            logger.warning(f"usecase_api: no sessions returned for id={usecase_id}")
            return None

        # Sort by date_created descending, pick latest
        sessions.sort(key=lambda s: s.get("date_created", ""), reverse=True)
        latest = sessions[0]

        parts = [
            f"Session ID: {latest.get('id')}",
            f"Date: {latest.get('date_created')}",
        ]
        if latest.get("elevator_pitch"):
            parts.append(f"Elevator Pitch: {_strip_html(latest['elevator_pitch'])}")
        if latest.get("closingretro"):
            stripped = _strip_html(latest["closingretro"])
            parts.append(f"Evaluation Report:\n{stripped}")

        return "\n\n".join(parts)
    except Exception as e:
        logger.error(f"usecase_api: failed to fetch id={usecase_id}: {e}")
        return None
