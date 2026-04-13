import requests
from loguru import logger

API_BASE = "https://rolplay.pro/banco/get-sessions-list.php"
TIMEOUT = 10  # seconds


def fetch_latest_session_context(usecase_id: int) -> str | None:
    """
    Fetches all sessions for a use case and returns the raw content
    of the most recent one, or None on failure.
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
            parts.append(f"Elevator Pitch:\n{latest['elevator_pitch']}")
        if latest.get("closingretro"):
            parts.append(f"Evaluation Report:\n{latest['closingretro']}")

        return "\n\n".join(parts)
    except Exception as e:
        logger.error(f"usecase_api: failed to fetch id={usecase_id}: {e}")
        return None
