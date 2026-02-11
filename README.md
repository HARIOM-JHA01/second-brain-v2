# Second Brain Roleplay - WhatsApp Bot with Voice Note Support

An AI-powered conversational agent for WhatsApp. Supports text messages and **voice notes (audio)** with automatic transcription using OpenAI Whisper.

## 🚀 Features

- ✅ Text messaging via WhatsApp
- 🎙️ **Voice notes (OpenAI Whisper transcription)**
- 🔄 Asynchronous processing with Celery + Redis
- 💾 Permanent audio and transcription storage
- 📊 Persistent chat history
- 🧠 Intelligent responses powered by Claude (Anthropic)
- 🔐 Secure document integration (Google Drive, Supabase)
- 🎯 Feature flag for safe rollout

---

## 📁 Project Structure

```
agente_roleplay/
├── app.py                      # FastAPI web server & Twilio webhook
├── audio_worker.py             # Celery async task worker for voice processing
├── procesa_mensajes.py         # Message routing & orchestration
├── whisper.py                  # OpenAI Whisper transcription module
├── agente_roleplay.py          # Claude agent response generation
├── chat_history.py             # Chat persistence layer
├── function_tools.py           # Tool definitions for Claude
├── google_drive.py             # Google Drive integration
├── utilities.py                # Helper functions
├── run_audio_worker.py         # Celery worker launcher script
├── requirements.txt            # Python dependencies
├── .env.example                # Environment variables template
├── README.md                   # This file
├── storage/
│   └── audio/                  # Permanent audio storage
├── temp_uploads/               # Temporary upload directory
├── metadata/                   # Metadata files for tracking
└── tests/
    └── test_audio.py           # Unit tests for audio processing
```

---

## 🛠️ Prerequisites

- **Python 3.9+**
- **Redis** (for Celery broker & caching)
- **uv** (Python package manager)
- **Twilio WhatsApp Sandbox** (configured)
- **OpenAI API Key** (for Whisper transcription)
- **Anthropic API Key** (for Claude responses)

---

## 📋 Local Setup

### 1. Clone and install dependencies

```bash
uv sync
```

### 2. Setup environment variables

```bash
cp .env.example .env
```

Then fill in your `.env` file with actual values:

```dotenv
# Twilio
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_SANDBOX_NUMBER=whatsapp:+14155238886

# OpenAI (Whisper)
OPENAI_API_KEY=sk-proj-...

# Anthropic (Claude)
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL_NAME=claude-3-5-sonnet-20241022

# Redis
REDIS_HOST=your-redis-host.redis.cloud.com
REDIS_PORT=12345
REDIS_PASSWORD=your_redis_password

# Voice Notes Feature
VOICE_NOTES_ENABLED=true
AUDIO_STORAGE_PATH=./storage/audio
AUDIO_RETENTION_DAYS=30

# Other services (Supabase, Qdrant, Google Drive, etc.)
SUPABASE_URL=...
SUPABASE_API_KEY=...
```

### 3. Run the application

**Terminal 1 - Start FastAPI server:**

```bash
uv run uvicorn app:app --reload --host 0.0.0.0 --port 5001
```

**Terminal 2 - Start Celery worker (in another terminal):**

```bash
python run_audio_worker.py
```

The app will now:

- Listen for Twilio webhooks on `http://localhost:5001/api/v1/webhook`
- Process voice notes asynchronously via Celery
- Store transcriptions and audio files locally

---

## 🌐 API Endpoints

### Twilio Webhook (Incoming Messages)

```http
POST /api/v1/webhook
Content-Type: application/x-www-form-urlencoded

From=whatsapp:+5215512345678
To=whatsapp:+14155238886
Body=Hello
MessageSid=SM123456
NumMedia=1
MediaUrl0=https://media.twilio.com/...
MediaContentType0=audio/ogg
```

**Response:** `200 OK`

Processing is fully asynchronous (ACK sent immediately, work queued to Celery).

---

## 🎙️ Voice Notes Processing Flow

```
User sends voice note via WhatsApp
    ↓
Twilio webhook → /api/v1/webhook
    ↓
procesar_mensajes_entrantes() detects media_type='audio'
    ↓
1. Send immediate ACK: "🎙️ Processing your voice note..."
    ↓
2. Enqueue job to Celery 'audio' queue
    ↓
Celery worker (audio_worker.py) processes asynchronously:
  • Download audio from Twilio URL (with authentication)
  • Transcribe using OpenAI Whisper API
  • Store audio to ./storage/audio/{phone}_{timestamp}.ogg
  • Inject transcription into chat pipeline
  • Call responder_usuario() → generate response
  • Send response back via Twilio
  • Log chat history to database
    ↓
User receives response: "{Transcription} → Agent's response"
```

### Example User Interaction

```
User: [sends voice: "What's your name?"]
    ↓
Bot ACK: "🎙️ Got your voice note, processing..."
    ↓
[Worker transcribes in background, ~10-30 seconds]
    ↓
Bot Response: "Your note said: 'What's your name?'
I'm your roleplay agent! Nice to meet you. 😊"
```

---

## 🧪 Testing

### Run unit tests

```bash
pytest tests/test_audio.py -v
```

**Test coverage includes:**

- `test_transcribe_success` — Successful transcription
- `test_transcribe_download_failed` — Download failure handling
- `test_process_audio_job_success` — Full job processing
- `test_health_check_ok` — Worker health check

### Manual end-to-end test

1. Start the app and worker (see "Run the application" above)
2. Send a voice note via Twilio Sandbox
3. Verify ACK arrives within 2-3 seconds
4. Wait 10-30 seconds for processing
5. Receive final response with transcription + reply

---

## 🏗️ Architecture Overview

### Components

| Component           | Role                                        | Technology                              |
| ------------------- | ------------------------------------------- | --------------------------------------- |
| **FastAPI Server**  | HTTP webhook endpoint, routes Twilio events | `app.py`, Uvicorn                       |
| **Celery Worker**   | Async job processing (transcribe → respond) | `audio_worker.py`                       |
| **Redis**           | Message broker for Celery, caching          | Redis Cloud/local                       |
| **Whisper Module**  | Audio transcription                         | `whisper.py` + OpenAI API               |
| **Agent Responder** | Response generation                         | `agente_roleplay.py` + Anthropic Claude |
| **Chat History**    | Persistence layer                           | `chat_history.py` + Supabase            |

### Data Flow

```
Twilio Input
    ↓
[FastAPI webhook receives message]
    ↓
[procesa_mensajes.py parses & routes]
         ↙        ↘
    Text        Audio
     ↓            ↓
  Direct      Celery
 Response     Queue
     ↘        ↙
   [Chat History]
     ↓
  [Claude responds]
     ↓
  [Twilio sends reply]
```

---

## 🔧 Environment Variables Reference

```dotenv
# Twilio Configuration
TWILIO_ACCOUNT_SID=          # Your Twilio account SID
TWILIO_AUTH_TOKEN=           # Your Twilio auth token
TWILIO_SANDBOX_NUMBER=       # Sandbox WhatsApp number (e.g., whatsapp:+14155238886)

# OpenAI
OPENAI_API_KEY=sk-proj-...   # API key for Whisper transcription

# Anthropic
ANTHROPIC_API_KEY=sk-ant-... # API key for Claude
ANTHROPIC_MODEL_NAME=claude-3-5-sonnet-20241022

# Redis (Celery Broker)
REDIS_HOST=                  # Redis host (e.g., redis-cloud.com)
REDIS_PORT=                  # Redis port (default: 6379)
REDIS_PASSWORD=              # Redis password (if required)

# Voice Notes
VOICE_NOTES_ENABLED=true     # Enable/disable voice note processing (feature flag)
AUDIO_STORAGE_PATH=./storage/audio  # Where to store audio files
AUDIO_RETENTION_DAYS=30      # Auto-cleanup days (future)

# Database & Vector Search
SUPABASE_URL=                # Supabase project URL
SUPABASE_API_KEY=            # Supabase API key
QDRANT_URL=http://localhost:6333  # Qdrant vector DB
QDRANT_API_KEY=              # Qdrant API key (if required)

# Google Drive
GOOGLE_DRIVE_FOLDER_ID=      # Google Drive folder ID for documents
GOOGLE_APPLICATION_CREDENTIALS=./DRIVE_CREDENTIALS.json
```

---

## Monitoring & Logs

### Health Check

```bash
curl -X GET http://localhost:5001/health
```

### View Worker Logs

```bash
# If running in foreground
uv run celery -A audio_worker worker --loglevel=debug

```

### Redis Queue Status

```bash
redis-cli -h YOUR_REDIS_HOST -p YOUR_REDIS_PORT -a YOUR_PASSWORD

# Check queued jobs
LLEN audio_queue

# Inspect job details
LRANGE audio_queue 0 -1
```

### Performance Metrics

**Expected latencies:**

- **ACK response:** 1-2 seconds
- **Whisper transcription:** 5-15 seconds (depends on audio duration)
- **Agent response generation:** 5-10 seconds
- **Total end-to-end:** 15-40 seconds

---

## 🐛 Troubleshooting

### "VOICE_NOTES_ENABLED is false"

**Symptom:** User receives _"Voice notes are not enabled yet"_

**Fix:** In `.env`, set:

```dotenv
VOICE_NOTES_ENABLED=true
```

Restart both the server and worker.

### "ConnectionError: Error enqueueing to Celery"

**Symptom:** Jobs not processing; queued in Redis but worker doesn't pick them up

**Debug steps:**

```bash
# Check Redis connectivity
redis-cli -h $REDIS_HOST -p $REDIS_PORT -a $REDIS_PASSWORD ping

# Verify worker is running
ps aux | grep audio_worker

# Restart worker
python run_audio_worker.py
```

### "Twilio download failed: 403 Forbidden"

**Cause:** Twilio media URLs expire in ~15 minutes. Worker latency exceeded timeout.

**Solutions:**

- Ensure Redis is responsive (check latency: `redis-cli --latency`)
- Increase Celery concurrency if CPU allows: `--concurrency=4`
- Implement retry logic with exponential backoff

### "OpenAI API timeout (429 or 500)"

**Symptom:** Whisper transcription fails intermittently

**Solutions:**

- Check OpenAI API status: https://status.openai.com
- Increase timeout in `whisper.py`: `timeout=60` (default: 30)
- Add retry logic for rate limits

### Job stuck in Redis queue

**Debug:**

```bash
redis-cli
> LLEN audio_queue          # Check queue length
> LINDEX audio_queue 0      # View first job (if any)
> DEL audio_queue           # Clear stuck jobs (careful!)
```

---
