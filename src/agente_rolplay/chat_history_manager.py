# python3 chat_history.py

import json
import os
import redis
import tiktoken
from dotenv import load_dotenv

load_dotenv()

openai_api_key = os.getenv("OPENAI_API_KEY")

# Redis connection configuration
redis_host = os.getenv("REDIS_HOST")
redis_port = os.getenv("REDIS_PORT")
redis_password = os.getenv("REDIS_PASSWORD")

TIEMPO_NUEVO = int(os.getenv("TIEMPO_NUEVO")) if os.getenv("TIEMPO_NUEVO") else 60 * 10

redis_client = redis.Redis(
    host=redis_host,
    port=redis_port,
    decode_responses=True,
    username="default",
    password=redis_password,
)

MAX_MESSAGES_IN_MEMORY = 12  # Only last 15 messages by default


def add_to_chat_history(id_chat_history, message, role, phone):
    """
    Adds message to history in Redis
    """
    try:
        history = redis_client.get(id_chat_history)

        if history:
            history = json.loads(history)
        else:
            history = []

        history.append({"role": role, "content": message})

        # NEW: Keep only last MAX_MESSAGES_IN_MEMORY messages
        if len(history) > MAX_MESSAGES_IN_MEMORY:
            history = history[-MAX_MESSAGES_IN_MEMORY:]
            print(f"History truncated to {MAX_MESSAGES_IN_MEMORY} messages for {phone}")

        redis_client.set(id_chat_history, json.dumps(history), ex=3600)

    except Exception as e:
        print(f"Error adding message to history: {e}")


def get_chat_history(id_chat_history, phone=None, limit=MAX_MESSAGES_IN_MEMORY):
    """
    Gets chat history from Redis

    Args:
        id_chat_history: Chat ID
        phone: Phone number (optional, for logs)
        limit: Maximum number of messages to return (default: MAX_MESSAGES_IN_MEMORY)

    Returns:
        list: Last N messages from history
    """
    try:
        history = redis_client.get(id_chat_history)

        if history:
            history = json.loads(history)

            # NEW: Apply limit when returning
            if len(history) > limit:
                history = history[-limit:]
                print(
                    f"Returning last {limit} messages of {len(history)} total for {phone}"
                )

            return history

        return []

    except Exception as e:
        print(f"Error getting history: {e}")
        return []


def num_tokens(text, model="gpt-4o"):
    encoding = tiktoken.encoding_for_model(model)
    return len(encoding.encode(text))


def reset_chat_history(chat_history_id, redis_client=redis_client):
    """
    Deletes chat history from Redis (improved version)
    """
    # If doesn't have prefix, add it
    if not chat_history_id.startswith("fp-chatHistory:"):
        chat_history_id = f"fp-chatHistory:{chat_history_id}"

    # Check if exists before deleting
    exists = redis_client.exists(chat_history_id)

    if not exists:
        print(f"Key '{chat_history_id}' does NOT exist in Redis")

        # Search for similar keys
        phone = chat_history_id.replace("fp-chatHistory:", "")
        pattern = f"fp-chatHistory:*{phone}*"
        similar_keys = redis_client.keys(pattern)

        if similar_keys:
            print(f"Similar keys found:")
            for key in similar_keys:
                print(f"   - {key}")

            # Delete first match
            if similar_keys:
                ans = redis_client.delete(similar_keys[0])
                print(f"History '{similar_keys[0]}' deleted")
                return ans

        return 0

    # Delete
    ans = redis_client.delete(chat_history_id)

    if ans > 0:
        print(f"History '{chat_history_id}' reset successfully")
    else:
        print(f"Error deleting '{chat_history_id}'")

    return ans


def listar_chat_histories(redis_client=redis_client):
    """
    Lists all chat histories stored in Redis
    """
    # Search for all keys starting with 'fp-chatHistory:'
    pattern = "fp-chatHistory:*"
    keys = redis_client.keys(pattern)

    print(f"\n{'=' * 60}")
    print(f"TOTAL CHAT HISTORIES: {len(keys)}")
    print(f"{'=' * 60}\n")

    if not keys:
        print("No chat histories stored in Redis")
        return []

    for key in keys:
        # Get content
        content = redis_client.get(key)

        # Extract phone number
        phone = key.replace("fp-chatHistory:", "")

        # Count messages (if JSON list)
        try:
            messages = json.loads(content) if content else []
            num_messages = len(messages)
        except:
            num_messages = "N/A"

        print(f"Phone: {phone}")
        print(f"   Full key: {key}")
        print(f"   Messages: {num_messages}")
        print(f"   TTL: {redis_client.ttl(key)} seconds")
        print("-" * 60)

    return keys


# Alias for backward compatibility
list_chat_histories = listar_chat_histories

if __name__ == "__main__":
    reset_chat_history("5215566098295")
    # listar_chat_histories()
