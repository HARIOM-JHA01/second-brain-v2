# Development Setup

This guide covers local environment setup for Redis and PostgreSQL, which are required to run the project.

---

## Option 1: Docker (Recommended)

```bash
# Start Redis
docker run -d \
  --name agente-rolplay-redis \
  -p 6379:6379 \
  -e REDIS_PASSWORD=password \
  redis:alpine

# Start PostgreSQL
docker run -d \
  --name agente-rolplay-postgres \
  -p 5432:5432 \
  -e POSTGRES_USER=rolplay_user \
  -e POSTGRES_PASSWORD=rolplay_pass \
  -e POSTGRES_DB=rolplay_db \
  postgres:15-alpine
```

Verify containers are running:

```bash
docker ps
docker logs agente-rolplay-redis
docker logs agente-rolplay-postgres
```

Stop and remove:

```bash
docker stop agente-rolplay-redis agente-rolplay-postgres
docker rm agente-rolplay-redis agente-rolplay-postgres
```

---

## Option 2: Homebrew (macOS)

```bash
brew install redis postgresql

brew services start redis
brew services start postgresql
```

Create the database and user:

```bash
psql postgres
```

```sql
CREATE USER rolplay_user WITH PASSWORD 'rolplay_pass';
CREATE DATABASE rolplay_db OWNER rolplay_user;
\q
```

---

## Option 3: apt (Ubuntu/Debian)

```bash
sudo apt update
sudo apt install -y redis-server postgresql postgresql-contrib
```

Set a Redis password:

```bash
sudo nano /etc/redis/redis.conf
# Set: requirepass password
sudo systemctl restart redis
```

Create the database and user:

```bash
sudo su - postgres
createuser --interactive -P rolplay_user
createdb -O rolplay_user rolplay_db
exit
```

---

## Verify Connections

```bash
# Redis
redis-cli -h localhost -p 6379 -a password ping
# Expected: PONG

# PostgreSQL
psql -h localhost -p 5432 -U rolplay_user -d rolplay_db -c "SELECT version();"
```

---

## Matching .env Values

```dotenv
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=password

DATABASE_URL=postgresql://rolplay_user:rolplay_pass@localhost:5432/rolplay_db
```

---

## Troubleshooting

**Port already in use:**
```bash
lsof -ti :6379 | xargs kill -9   # Redis
lsof -ti :5432 | xargs kill -9   # PostgreSQL
```

**Password authentication failed:** Verify the password in `.env` matches what you configured above.

**Connection refused:** Ensure the service is running — `docker ps` or `brew services list`.

---

## Running the Application

### Hot Reload Development

Run backend and frontend in separate terminals:

```bash
# Terminal 1 - Backend (port 8000)
uv run uvicorn agente_rolplay.main:app --reload

# Terminal 2 - Frontend (port 5173)
cd frontend && npm run dev
```

Access the app at: http://localhost:5173/app/

The frontend proxy forwards `/api` and `/auth` requests to the backend.

### Production Build

```bash
# Build frontend
cd frontend && npm run build

# Copy build to backend static folder
cp -r frontend/dist/* agente_rolplay/static/react/

# Run production server
uv run uvicorn agente_rolplay.main:app --host 0.0.0.0
```

### Frontend Structure

```
frontend/
├── src/
│   ├── api/           # API clients (client.ts, auth.ts, users.ts, etc.)
│   ├── components/    # UI components (ui/, layout/, charts/)
│   ├── contexts/      # React contexts (AuthContext, ThemeContext)
│   ├── pages/         # Page components
│   ├── locales/       # i18n translations (es.json, en.json)
│   ├── types/         # TypeScript types
│   └── utils/         # Utilities (date.ts)
├── vite.config.ts     # Vite config with proxy setup
└── tailwind.config.js # Tailwind theme
```
