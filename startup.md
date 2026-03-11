# Startup Guide for Redis and Postgres

This guide provides commands to start Redis and Postgres locally for the `agente_rolplay` project.

## Prerequisites

Ensure you have the following installed on your system:

- Docker (for containerized setup)
- Or Redis and Postgres installed locally

---

## Option 1: Docker-based Setup (Recommended)

### Start Redis and Postgres containers

```bash
# Start Redis container (port 6379)
docker run -d \
  --name agente-rolplay-redis \
  -p 6379:6379 \
  -e REDIS_PASSWORD=password \
  redis:alpine

# Start Postgres container (port 5432)
docker run -d \
  --name agente-rolplay-postgres \
  -p 5432:5432 \
  -e POSTGRES_USER=rolplay_user \
  -e POSTGRES_PASSWORD=rolplay_pass \
  -e POSTGRES_DB=rolplay_db \
  postgres:15-alpine
```

### Verify containers are running

```bash
# List running containers
docker ps

# Check Redis container logs
docker logs agente-rolplay-redis

# Check Postgres container logs
docker logs agente-rolplay-postgres
```

### Stop containers

```bash
# Stop both containers
docker stop agente-rolplay-redis agente-rolplay-postgres

# Remove containers (optional)
docker rm agente-rolplay-redis agente-rolplay-postgres
```

---

## Option 2: Local Installation (MacOS with Homebrew)

### Install Redis and Postgres

```bash
# Install Redis
brew install redis

# Install Postgres
brew install postgresql
```

### Start services

```bash
# Start Redis service
brew services start redis

# Start Postgres service
brew services start postgresql
```

### Create Postgres database and user

```bash
# Connect to Postgres (default user)
psql postgres

# Create user
CREATE USER rolplay_user WITH PASSWORD 'rolplay_pass';

# Create database
CREATE DATABASE rolplay_db OWNER rolplay_user;

# Exit psql
\q
```

### Verify connections

```bash
# Check Redis connection
redis-cli -h localhost -p 6379 -a password ping

# Check Postgres connection
psql -h localhost -p 5432 -U rolplay_user -d rolplay_db -c "SELECT version();"
```

### Stop services

```bash
# Stop Redis service
brew services stop redis

# Stop Postgres service
brew services stop postgresql
```

---

## Option 3: Local Installation (Linux)

### Install Redis and Postgres (Ubuntu/Debian)

```bash
# Update package lists
sudo apt update

# Install Redis
sudo apt install -y redis-server

# Install Postgres
sudo apt install -y postgresql postgresql-contrib
```

### Configure Redis password

```bash
# Edit Redis configuration file
sudo nano /etc/redis/redis.conf

# Find and uncomment/change the line:
# requirepass foobared
# to
requirepass password

# Restart Redis
sudo systemctl restart redis
```

### Create Postgres database and user

```bash
# Switch to postgres user
sudo su - postgres

# Create user
createuser --interactive -P rolplay_user
# Enter password: rolplay_pass

# Create database
createdb -O rolplay_user rolplay_db

# Exit postgres user
exit
```

### Verify connections

```bash
# Check Redis connection
redis-cli -h localhost -p 6379 -a password ping

# Check Postgres connection
psql -h localhost -p 5432 -U rolplay_user -d rolplay_db -c "SELECT version();"
```

---

## Verify Services are Running

### Redis Health Check

```bash
# Ping Redis
redis-cli -h localhost -p 6379 -a password ping
# Should return: PONG

# Check info
redis-cli -h localhost -p 6379 -a password info Server
```

### Postgres Health Check

```bash
# Check connection and version
psql -h localhost -p 5432 -U rolplay_user -d rolplay_db -c "SELECT version();"

# List databases
psql -h localhost -p 5432 -U rolplay_user -l
```

---

## Project Configuration

The project uses the following environment variables (already configured in `.env`):

```bash
# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=password

# Postgres
DATABASE_URL=postgresql://rolplay_user:rolplay_pass@localhost:5432/rolplay_db
```

---

## Troubleshooting

### Common Issues

1. **Port already in use:**
   - Check which process is using the port: `lsof -ti :6379` (Redis) or `lsof -ti :5432` (Postgres)
   - Kill the process: `kill -9 <PID>`

2. **Connection refused:**
   - Ensure the service is running
   - Check firewall settings

3. **Password authentication failed:**
   - Verify the password in `.env` matches the one you configured

---

## Next Steps

Once Redis and Postgres are running, you can start the application:

```bash
# Sync dependencies
uv sync

# Start the FastAPI server
uv run uvicorn src.agente_rolplay.main:app --reload --host 0.0.0.0 --port 5001

# In another terminal, start the Celery worker
uv run python scripts/run_audio_worker.py
```
