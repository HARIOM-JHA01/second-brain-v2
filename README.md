# Second Brain — WhatsApp AI Agent

An AI-powered WhatsApp agent for Rolplay. Users send messages via WhatsApp; the agent responds using Anthropic Claude with RAG over an organization's knowledge base.

---

## Features

- Conversational AI via WhatsApp (Twilio)
- Knowledge base queries using RAG (Pinecone + OpenAI embeddings)
- Document and image ingestion via WhatsApp (stored in Cloudinary, indexed in Pinecone)
- Voice note transcription via OpenAI Whisper (async via Celery)
- Bilingual support (Spanish / English, auto-detected per message)
- Role-based permission system tied to WhatsApp phone numbers
- Dashboard with user, role, and document management
- Conversation history in Redis (TTL 1h, max 12 messages)
- Message deduplication to prevent double-processing

---

## Architecture

```
POST /api/v1/webhook  (Twilio)
    → routers/webhook.py
    → messaging/process_messages.py
    → messaging/message_processor.py
         ├── Greeting / help      → messaging/greeting_handler.py
         ├── KB inventory query   → Redis set count
         ├── File upload intent   → prompt user to send file
         ├── Audio message        → Celery → messaging/audio_worker.py → messaging/whisper_service.py
         ├── Document / Image     → storage/cloudinary_storage.py + storage/pinecone_client.py
         └── Text                 → agent/roleplay_agent.py
                                       → Anthropic Claude (tool_choice=any)
                                       → tools: informacion_general, actualizar_drive, saludar_cliente
                                       → informacion_general → storage/pinecone_client.search_knowledge_base()
```

### Data Stores

| Store | Purpose |
|-------|---------|
| Redis | Chat history, deduplication keys, session state, KB file set, language preference |
| Pinecone | Vector embeddings for RAG (7000-token chunks, 400-token overlap) |
| Cloudinary | Uploaded files and images (`knowledgebase` folder) |
| PostgreSQL | Users, organizations, profiles, roles, documents |

---

## Project Structure

```
agente_rolplay/
├── config.py               Environment variables (single source of truth)
├── main.py                 FastAPI app, middleware, router registration
├── agent/
│   ├── roleplay_agent.py   Claude agent loop with tool handling
│   ├── cli_tools.py        Anthropic / OpenAI / Pinecone helper utilities
│   ├── system_prompt.py    System prompts for the agent
│   └── tools.py            Claude tool definitions (informacion_general, etc.)
├── messaging/
│   ├── message_processor.py   Core message routing logic
│   ├── process_messages.py    Alias layer (Spanish-named exports)
│   ├── twilio_client.py       Send messages and download media via Twilio
│   ├── greeting_handler.py    Pattern-based greeting and help detection
│   ├── audio_worker.py        Celery worker for async audio processing
│   ├── whisper_service.py     OpenAI Whisper transcription
│   └── chat_history_manager.py  Redis-backed conversation history
├── storage/
│   ├── cloudinary_storage.py  File and image upload to Cloudinary
│   ├── pinecone_client.py     Vector DB: embed, upload, search
│   ├── file_processor.py      Text extraction from PDF, DOCX, PPTX, XLSX
│   └── analytics_logger.py    JSONL chat interaction logging
├── db/
│   ├── database.py            SQLAlchemy engine and session factory
│   ├── models.py              User, Organization, Profile, Role, Document
│   ├── schemas.py             Pydantic request / response schemas
│   ├── auth.py                JWT auth and password hashing
│   └── whatsapp_auth.py       Phone-based user lookup and permission gating
└── routers/
    ├── webhook.py             POST /api/v1/webhook, /api/v1/webhook/status
    ├── rag.py                 POST /api/v1/rag/query
    ├── pages.py               Dashboard and static pages
    ├── auth.py                Login, signup
    ├── users.py               User management
    └── roles.py               Role management
```

---

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager
- Redis and PostgreSQL running locally — see [DEVELOPMENT.md](DEVELOPMENT.md)
- Twilio account with WhatsApp Sandbox configured
- Anthropic, OpenAI, Pinecone, and Cloudinary API keys

---

## Setup

**1. Install dependencies**

```bash
uv sync
```

**2. Configure environment variables**

Copy the example and fill in values:

```bash
cp .env.example .env
```

See the [Environment Variables](#environment-variables) section for all required keys.

**3. Start Redis and PostgreSQL**

See [DEVELOPMENT.md](DEVELOPMENT.md) for Docker and local setup instructions.

**4. Run the server**

```bash
uv run uvicorn agente_rolplay.main:app --reload --host 0.0.0.0 --port 5001
```

**5. Run the Celery worker** (required for voice note processing)

```bash
celery -A agente_rolplay.messaging.audio_worker worker --loglevel=info --concurrency=1 --queues=audio
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/webhook` | Incoming Twilio WhatsApp messages |
| `POST` | `/api/v1/webhook/status` | Twilio message status callbacks |
| `POST` | `/api/v1/rag/query` | External RAG query (Bearer auth) |
| `GET` | `/health` | Health check |
| `GET` | `/` | Landing page |
| `GET` | `/dashboard` | Admin dashboard |
| `POST` | `/auth/login` | User login |
| `POST` | `/auth/signup` | User signup |

---

## Environment Variables

```dotenv
# Anthropic
ANTHROPIC_API_KEY=
ANTHROPIC_MODEL_NAME=claude-3-5-sonnet-20241022

# OpenAI (Whisper transcription + Pinecone embeddings)
OPENAI_API_KEY=
OPENAI_EMBEDDINGS_MODEL=text-embedding-3-small
VECTOR_DIMENSION=1024
N_SIMILARITY=3

# Twilio
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_SANDBOX_NUMBER=whatsapp:+14155238886

# Redis
REDIS_HOST=
REDIS_PORT=6379
REDIS_PASSWORD=

# PostgreSQL
DATABASE_URL=postgresql://user:password@localhost:5432/rolplay_db

# Pinecone
PINECONE_API_KEY=
PINECONE_INDEX_NAME=knowledgebase
PINECONE_ENV=us-east-1

# Cloudinary
CLOUDINARY_CLOUD_NAME=
CLOUDINARY_API_KEY=
CLOUDINARY_API_SECRET=

# Auth
SECRET_KEY=                         # JWT signing secret

# Feature flags
VOICE_NOTES_ENABLED=false           # Enable Celery audio processing
PORT=5001

# RAG endpoint auth
GPT_ACTIONS_API_KEY=                # Bearer token for /api/v1/rag/query
```

---

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run a specific file
pytest tests/test_message_processor_upload_state.py -v
```

---

## Permission System

Users are identified by their WhatsApp phone number (`Profile.whatsapp_number`). Roles carry JSON permission sets:

| Permission | Description |
|------------|-------------|
| `query:financial` | Access to financial knowledge |
| `query:strategic` | Access to strategic knowledge |
| `query:sensitive` | Access to sensitive knowledge |
| `document:read` | Read documents |
| `document:upload` | Upload documents to knowledge base |
| `user:manage` | Manage users and roles |

Each incoming query is classified by Claude (claude-3-haiku) to determine if it requires a restricted permission.
