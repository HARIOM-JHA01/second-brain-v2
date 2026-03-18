import os
from urllib.parse import quote

from dotenv import load_dotenv

load_dotenv()

# --- Anthropic ---
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ANTHROPIC_MODEL_NAME = os.getenv("ANTHROPIC_MODEL_NAME")

# --- OpenAI ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_EMBEDDINGS_MODEL = os.getenv("OPENAI_EMBEDDINGS_MODEL", "text-embedding-3-small")
VECTOR_DIMENSION = int(os.getenv("VECTOR_DIMENSION", 1024))
N_SIMILARITY = int(os.getenv("N_SIMILARITY", 3))

# --- Redis ---
_REDIS_URL = os.getenv("REDIS_URL")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_PASSWORD = (os.getenv("REDIS_PASSWORD") or "").strip() or None
REDIS_SSL = os.getenv("REDIS_SSL", "false").lower() == "true"

# Parse REDIS_URL if provided (e.g. Upstash rediss://default:pass@host:port)
if _REDIS_URL:
    from urllib.parse import urlparse as _urlparse  # noqa: PLC0415
    _parsed = _urlparse(_REDIS_URL)
    REDIS_HOST = _parsed.hostname
    REDIS_PORT = _parsed.port or 6379
    REDIS_PASSWORD = _parsed.password or None
    REDIS_SSL = _parsed.scheme == "rediss"


def build_redis_url(db: int) -> str:
    auth = f":{quote(REDIS_PASSWORD)}@" if REDIS_PASSWORD else ""
    scheme = "rediss" if REDIS_SSL else "redis"
    return f"{scheme}://{auth}{REDIS_HOST}:{REDIS_PORT}/{db}"


def redis_connection_kwargs() -> dict:
    """Common kwargs for redis.Redis with optional auth and TLS."""
    kwargs = {
        "host": REDIS_HOST,
        "port": REDIS_PORT,
        "decode_responses": True,
        "ssl": REDIS_SSL,
    }
    if REDIS_PASSWORD:
        kwargs["username"] = "default"
        kwargs["password"] = REDIS_PASSWORD
    return kwargs

# --- Pinecone ---
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_ENV = os.getenv("PINECONE_ENV", "us-east-1")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "knowledgebase")

# --- Twilio ---
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_SANDBOX_NUMBER = os.getenv("TWILIO_SANDBOX_NUMBER")

# --- Cloudinary ---
CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET")

# --- Database ---
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/agente_rolplay"
)

# --- Auth ---
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")

# --- Rolplay Admin ---
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@rolplay.ai")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "change-me-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

# --- App ---
GPT_ACTIONS_API_KEY = os.getenv("GPT_ACTIONS_API_KEY")
PORT = int(os.getenv("PORT", 5001))
VOICE_NOTES_ENABLED = os.getenv("VOICE_NOTES_ENABLED", "false").lower() == "true"
WEBHOOK_RENDER = os.getenv("WEBHOOK_RENDER")
USER_ID = os.getenv("USER_ID", "default_user")

# --- Analytics ---
ANALYTICS_LOG_DIR = os.getenv("ANALYTICS_LOG_DIR", "./logs")
ANALYTICS_LOG_FILE = os.getenv("ANALYTICS_LOG_FILE", "chat_analytics.jsonl")

# --- Chat History ---
CHAT_HISTORY_TTL = int(os.getenv("CHAT_HISTORY_TTL", 86400))        # 24 hours
MAX_MESSAGES_IN_MEMORY = int(os.getenv("MAX_MESSAGES_IN_MEMORY", 12))

# --- Rate Limiting ---
RATE_LIMIT_MAX_MESSAGES = int(os.getenv("RATE_LIMIT_MAX_MESSAGES", 10))
RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", 60))

# --- File Upload ---
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", 50))
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

# --- Redis TTLs ---
DEDUP_KEY_TTL = int(os.getenv("DEDUP_KEY_TTL", 600))               # 10 min
USER_SESSION_TTL = int(os.getenv("USER_SESSION_TTL", 600))          # 10 min
USER_LANG_TTL = int(os.getenv("USER_LANG_TTL", 86400))              # 24 hours
LAST_UPLOADED_FILE_TTL = int(os.getenv("LAST_UPLOADED_FILE_TTL", 86400 * 7))   # 7 days
FILE_METADATA_TTL = int(os.getenv("FILE_METADATA_TTL", 86400 * 30)) # 30 days
ACRONYM_PENDING_TTL = int(os.getenv("ACRONYM_PENDING_TTL", 300))    # 5 min

# --- Agent ---
AGENT_MAX_TOKENS = int(os.getenv("AGENT_MAX_TOKENS", 4096))
HAIKU_MODEL_NAME = os.getenv("HAIKU_MODEL_NAME", "claude-haiku-4-5-20251001")
IMAGE_DESCRIPTION_MAX_TOKENS = int(os.getenv("IMAGE_DESCRIPTION_MAX_TOKENS", 1024))
TWILIO_MESSAGE_MAX_LENGTH = int(os.getenv("TWILIO_MESSAGE_MAX_LENGTH", 1520))

# --- RAG ---
MIN_RELEVANCE_SCORE = float(os.getenv("MIN_RELEVANCE_SCORE", 0.35))
CHUNK_MAX_TOKENS = int(os.getenv("CHUNK_MAX_TOKENS", 7000))
CHUNK_OVERLAP_TOKENS = int(os.getenv("CHUNK_OVERLAP_TOKENS", 400))
