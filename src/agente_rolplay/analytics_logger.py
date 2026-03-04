import json
import os
import threading
from datetime import datetime
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

LOG_DIR = os.getenv("ANALYTICS_LOG_DIR", "./logs")
LOG_FILE = os.getenv("ANALYTICS_LOG_FILE", "chat_analytics.jsonl")

ANALYTICS_LOCK = threading.Lock()


def ensure_log_dir():
    """Create logs directory if it doesn't exist."""
    os.makedirs(LOG_DIR, exist_ok=True)


def get_log_path() -> str:
    """Get full path to log file."""
    return os.path.join(LOG_DIR, LOG_FILE)


def log_chat_interaction(
    phone_number: str,
    user_message: str,
    bot_response: str,
    message_type: str = "query",
    language: str = "es",
    metadata: Optional[dict] = None,
):
    """
    Log a chat interaction to JSON file.

    Args:
        phone_number: User's phone number
        user_message: What the user sent
        bot_response: Bot's response
        message_type: Type of message (greeting, query, document, help)
        language: Language used (es/en)
        metadata: Additional metadata (optional)
    """

    def _write():
        try:
            ensure_log_dir()
            log_path = get_log_path()

            entry = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "phone_number": phone_number,
                "user_message": user_message,
                "bot_response": bot_response,
                "message_type": message_type,
                "language": language,
            }

            if metadata:
                entry["metadata"] = metadata

            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")

        except Exception as e:
            print(f"Error writing to analytics log: {e}")

    thread = threading.Thread(target=_write, daemon=True)
    thread.start()


def log_greeting(phone_number: str, language: str = "es"):
    """Log a greeting interaction."""
    from src.agente_rolplay.greeting_handler import get_intro_message

    log_chat_interaction(
        phone_number=phone_number,
        user_message="[GREETING]",
        bot_response=get_intro_message(language),
        message_type="greeting",
        language=language,
    )


def log_help(phone_number: str, language: str = "es"):
    """Log a help/capabilities request."""
    from src.agente_rolplay.greeting_handler import get_capabilities_message

    log_chat_interaction(
        phone_number=phone_number,
        user_message="[HELP_REQUEST]",
        bot_response=get_capabilities_message(language),
        message_type="help",
        language=language,
    )


def get_analytics_summary(days: int = 7) -> dict:
    """
    Get analytics summary for the last N days.

    Args:
        days: Number of days to analyze

    Returns:
        dict with summary statistics
    """
    try:
        from datetime import timedelta

        log_path = get_log_path()

        if not os.path.exists(log_path):
            return {"error": "No analytics data found"}

        cutoff = datetime.utcnow() - timedelta(days=days)

        stats = {
            "total_messages": 0,
            "by_type": {},
            "by_language": {},
            "unique_users": set(),
            "by_day": {},
        }

        with open(log_path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    entry_time = datetime.fromisoformat(
                        entry["timestamp"].replace("Z", "+00:00")
                    )

                    if entry_time.replace(tzinfo=None) < cutoff:
                        continue

                    stats["total_messages"] += 1

                    msg_type = entry.get("message_type", "unknown")
                    stats["by_type"][msg_type] = stats["by_type"].get(msg_type, 0) + 1

                    lang = entry.get("language", "unknown")
                    stats["by_language"][lang] = stats["by_language"].get(lang, 0) + 1

                    phone = entry.get("phone_number", "")
                    if phone:
                        stats["unique_users"].add(phone)

                    day_key = entry_time.strftime("%Y-%m-%d")
                    stats["by_day"][day_key] = stats["by_day"].get(day_key, 0) + 1

                except Exception:
                    continue

        stats["unique_users"] = len(stats["unique_users"])

        return stats

    except Exception as e:
        return {"error": str(e)}


def get_user_history(phone_number: str, limit: int = 100) -> list:
    """
    Get chat history for a specific user.

    Args:
        phone_number: User's phone number
        limit: Maximum number of entries to return

    Returns:
        List of chat entries
    """
    try:
        log_path = get_log_path()

        if not os.path.exists(log_path):
            return []

        history = []

        with open(log_path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    if entry.get("phone_number") == phone_number:
                        history.append(entry)
                        if len(history) >= limit:
                            break
                except Exception:
                    continue

        return list(reversed(history))

    except Exception as e:
        print(f"Error getting user history: {e}")
        return []


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        if sys.argv[1] == "summary":
            days = int(sys.argv[2]) if len(sys.argv) > 2 else 7
            print(json.dumps(get_analytics_summary(days), indent=2, default=str))
        elif sys.argv[1] == "history" and len(sys.argv) > 2:
            phone = sys.argv[2]
            print(json.dumps(get_user_history(phone), indent=2, default=str))
    else:
        print("Usage:")
        print("  python analytics_logger.py summary [days]")
        print("  python analytics_logger.py history <phone_number>")
