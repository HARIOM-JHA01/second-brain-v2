import os

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
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")

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
