# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
uv sync

# Run the FastAPI server
uv run uvicorn agente_rolplay.main:app --reload --host 0.0.0.0

# Run tests
pytest tests/ -v

# Run a single test file
pytest tests/test_message_processor_upload_state.py -v
```

## Architecture Overview

This is a WhatsApp AI agent ("Second Brain") for Rolplay. Users interact via WhatsApp; messages arrive via Twilio webhooks, get routed to an Anthropic Claude agent with RAG capabilities, and responses go back via Twilio.

### Request Flow

```
POST /api/v1/webhook (Twilio form data)
    → main.py
    → process_messages.py (alias layer)
    → message_processor.process_incoming_messages()
         ├── Greeting/help → greeting_handler.py (static responses)
         ├── KB inventory query → Redis set count
         ├── File upload intent → ask user to send file
         ├── Audio → Celery queue → audio_worker.py → whisper_service.py
         ├── Document/Image → cloudinary_storage.py + pinecone_client.py
         └── Text → roleplay_agent.responder_usuario()
                          → Anthropic Claude (tool_choice=any)
                          → tools: informacion_general, actualizar_drive, saludar_cliente
                          → informacion_general triggers RAG: pinecone_client.search_knowledge_base()
```

### Key Files

| File | Role |
|------|------|
| `agente_rolplay/main.py` | FastAPI app, webhook endpoints, Google Drive OAuth, dashboard pages |
| `agente_rolplay/message_processor.py` | Core message routing logic; two variants: `process_incoming_messages` (with auth) and `process_incoming_messages_functional` (without) |
| `agente_rolplay/process_messages.py` | Thin alias layer re-exporting from `message_processor` and `twilio_client` with Spanish names |
| `agente_rolplay/roleplay_agent.py` | Anthropic Claude agent loop; handles tool calls |
| `agente_rolplay/tools.py` | Claude tool definitions: `informacion_general`, `actualizar_drive`, `saludar_cliente` |
| `agente_rolplay/pinecone_client.py` | Pinecone vector DB; embeddings via OpenAI `text-embedding-3-small` |
| `agente_rolplay/cloudinary_storage.py` | File/image upload to Cloudinary |
| `agente_rolplay/chat_history_manager.py` | Conversation history stored in Redis (TTL 1h, max 12 messages) |
| `agente_rolplay/audio_worker.py` | Celery task: download audio → Whisper transcription → agent → reply |
| `agente_rolplay/whatsapp_auth.py` | WhatsApp user lookup by phone number; LLM-based query classification for permission gating |
| `agente_rolplay/greeting_handler.py` | Pattern-based greeting/help detection; bilingual (ES/EN) static messages |
| `agente_rolplay/database.py` | SQLAlchemy engine + `get_db()` dependency |
| `agente_rolplay/models.py` | SQLAlchemy models: `User`, `Organization`, `Profile`, `Role`, `Document` |
| `agente_rolplay/auth.py` | JWT auth (python-jose), password hashing (passlib/bcrypt) |
| `agente_rolplay/routers/` | FastAPI routers for auth, users, roles |
| `agente_rolplay/file_processor.py` | Text extraction from PDF, DOCX, PPTX, XLSX for vectorization |

### Data Stores

- **Redis**: Chat history (`fp-chatHistory:{from_number}`), deduplication keys (`msg:twilio:{sid}`), user session data (`fp-idPhone:{phone}`), file metadata (`file_metadata:{filename}`), KB file set (`all_uploaded_files`), pending upload state, language preference
- **Pinecone**: Vector embeddings for RAG (chunked with tiktoken, 7000 token chunks, 400 token overlap)
- **Cloudinary**: Uploaded files and images (folder: `knowledgebase`)
- **PostgreSQL**: Users, organizations, profiles, roles, documents (via SQLAlchemy)

### Permission System

Users are looked up by normalized WhatsApp phone number from `Profile.whatsapp_number`. Roles carry JSON permissions: `query:financial`, `query:strategic`, `query:sensitive`, `document:read`, `document:upload`, `user:manage`. Each incoming query is classified by Claude (claude-3-haiku) to determine if it hits a restricted category.

### Environment Variables

```dotenv
# Required
ANTHROPIC_API_KEY=
ANTHROPIC_MODEL_NAME=claude-3-5-sonnet-20241022
OPENAI_API_KEY=                    # For Whisper transcription + Pinecone embeddings
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_SANDBOX_NUMBER=whatsapp:+14155238886
REDIS_HOST=
REDIS_PORT=
REDIS_PASSWORD=
DATABASE_URL=postgresql://...
PINECONE_API_KEY=
PINECONE_INDEX_NAME=knowledgebase
PINECONE_ENV=us-east-1
CLOUDINARY_CLOUD_NAME=
CLOUDINARY_API_KEY=
CLOUDINARY_API_SECRET=

# Feature flags
VOICE_NOTES_ENABLED=false          # Enable voice note transcription via Celery
TIEMPO_NUEVO=600                   # Session timeout in seconds
```

### Message Deduplication

Redis key `msg:twilio:{MessageSid}` with 600s TTL prevents duplicate processing. Audio jobs also use `audio_queued:{phone}:{timestamp}` with 300s TTL.

### Bilingual Support

Language is detected per-message and stored in Redis (`user:lang:{phone}`). `greeting_handler.is_english()` uses word set intersection heuristics. The system prompt receives a language override directive accordingly.
