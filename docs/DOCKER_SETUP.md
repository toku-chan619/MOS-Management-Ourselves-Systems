# Docker Setup Guide

This guide explains how to set up and run the MOS (Management Ourselves System) application using Docker.

---

## Prerequisites

Before you begin, make sure you have the following installed:

- **Docker** (20.10+)
- **Docker Compose** (2.0+)
- **Git** (for cloning the repository)

### Installing Docker

**Ubuntu/Debian:**
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
```

**macOS:**
Download and install [Docker Desktop for Mac](https://www.docker.com/products/docker-desktop/)

**Windows:**
Download and install [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/)

After installation, verify:
```bash
docker --version
docker-compose --version
```

---

## Initial Setup

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/MOS-Management-Ourselves-Systems.git
cd MOS-Management-Ourselves-Systems/backend
```

### 2. Configure Environment Variables

Copy the example environment file and configure it:

```bash
cp .env.example .env
```

**Edit `.env` and configure the following:**

#### Required Settings

```env
# Database Configuration
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_secure_password_here
POSTGRES_DB=mos
POSTGRES_PORT=5432
DATABASE_URL=postgresql+asyncpg://postgres:your_secure_password_here@db:5432/mos

# Redis Configuration
REDIS_URL=redis://redis:6379/0

# LLM Backend Configuration
LLM_BACKEND=openai_api
OPENAI_API_KEY=sk-your-openai-api-key-here
LLM_MODEL=gpt-4o-mini
PROMPT_VERSION=phase1-extract-v1

# Application Configuration
APP_BASE_URL=http://localhost:8000

# Timezone & Followup Schedule
TZ=Asia/Tokyo
FOLLOWUP_MORNING=09:00
FOLLOWUP_NOON=13:00
FOLLOWUP_EVENING=18:00

# Reminders & Notifications
REMINDER_SCAN_INTERVAL_MIN=10
RENDER_BATCH_SIZE=10

# CORS Configuration
CORS_ORIGINS=http://localhost:3000,http://localhost:8000
```

#### Important Notes

- **POSTGRES_PASSWORD**: Change from the default `postgres` to a secure password
- **DATABASE_URL**: Update the password in the connection string to match `POSTGRES_PASSWORD`
- **OPENAI_API_KEY**: Get your API key from [OpenAI Platform](https://platform.openai.com/api-keys)
- **LLM_BACKEND**: See [LLM_PROVIDERS.md](./LLM_PROVIDERS.md) for alternative backends (Claude CLI, Ollama)

---

## Building and Running

### 1. Build the Docker Images

```bash
docker-compose build
```

This will:
- Pull the PostgreSQL 16 and Redis 7 images
- Build the FastAPI application image
- Install all Python dependencies

### 2. Start All Services

```bash
docker-compose up -d
```

This starts the following services:
- **db**: PostgreSQL database (port 5432)
- **redis**: Redis cache (port 6379)
- **migration**: Runs database migrations (exits after completion)
- **api**: FastAPI web server (port 8000)
- **celery-worker**: Celery background worker

### 3. Check Service Status

```bash
docker-compose ps
```

You should see:
```
NAME                        STATUS              PORTS
backend-api-1              Up                  0.0.0.0:8000->8000/tcp
backend-celery-worker-1    Up
backend-db-1               Up (healthy)        0.0.0.0:5432->5432/tcp
backend-redis-1            Up (healthy)        0.0.0.0:6379->6379/tcp
backend-migration-1        Exited (0)
```

---

## Verification

### 1. Check API Health

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{"status": "ok"}
```

### 2. View Logs

**All services:**
```bash
docker-compose logs -f
```

**Specific service:**
```bash
docker-compose logs -f api
docker-compose logs -f celery-worker
docker-compose logs -f db
```

### 3. Test API Endpoints

**Create a test message:**
```bash
curl -X POST http://localhost:8000/api/chat/messages \
  -H "Content-Type: application/json" \
  -d '{"content": "明日までにレポートを完成させる"}'
```

Expected: Returns a message with extracted task drafts

**List tasks:**
```bash
curl http://localhost:8000/api/tasks
```

### 4. Check Database Migrations

```bash
docker-compose exec api alembic current
```

This should show the current migration version.

---

## Common Operations

### Stop Services

```bash
docker-compose down
```

### Stop and Remove All Data

**WARNING:** This will delete all database data!

```bash
docker-compose down -v
```

### Restart a Specific Service

```bash
docker-compose restart api
docker-compose restart celery-worker
```

### Rebuild After Code Changes

```bash
docker-compose down
docker-compose build
docker-compose up -d
```

### Run Database Migrations Manually

```bash
docker-compose exec api alembic upgrade head
```

### Access Database Shell

```bash
docker-compose exec db psql -U postgres -d mos
```

### Execute Commands in Container

```bash
# Python shell
docker-compose exec api python

# Bash shell
docker-compose exec api bash
```

### View Container Resource Usage

```bash
docker stats
```

---

## Running Tests

### Inside Container

```bash
docker-compose exec api pytest tests/ -v
```

### With Coverage

```bash
docker-compose exec api pytest tests/ --cov=app --cov-report=html
```

---

## Troubleshooting

### Problem: Database connection errors

**Symptoms:**
```
sqlalchemy.exc.OperationalError: could not connect to server
```

**Solutions:**
1. Check if database is healthy:
   ```bash
   docker-compose ps db
   ```
2. Check database logs:
   ```bash
   docker-compose logs db
   ```
3. Ensure `DATABASE_URL` in `.env` uses `db:5432` (not `localhost:5432`)
4. Restart services:
   ```bash
   docker-compose restart
   ```

---

### Problem: Migration fails

**Symptoms:**
```
ERROR [alembic.runtime.migration] Can't locate revision
```

**Solutions:**
1. Check current migration state:
   ```bash
   docker-compose exec api alembic current
   docker-compose exec api alembic history
   ```
2. Reset to clean state (CAUTION: loses data):
   ```bash
   docker-compose down -v
   docker-compose up -d
   ```

---

### Problem: API returns 500 errors

**Symptoms:**
```json
{"detail": "Internal Server Error"}
```

**Solutions:**
1. Check API logs:
   ```bash
   docker-compose logs api | tail -50
   ```
2. Common causes:
   - Missing `OPENAI_API_KEY` in `.env`
   - Invalid database configuration
   - Redis connection issues
3. Verify environment variables are loaded:
   ```bash
   docker-compose exec api env | grep -E '(OPENAI|DATABASE|REDIS)'
   ```

---

### Problem: Celery worker not processing tasks

**Symptoms:**
- Followup runs not executing
- Background tasks stuck

**Solutions:**
1. Check worker logs:
   ```bash
   docker-compose logs celery-worker
   ```
2. Verify Redis connection:
   ```bash
   docker-compose exec redis redis-cli ping
   ```
3. Restart worker:
   ```bash
   docker-compose restart celery-worker
   ```

---

### Problem: Port already in use

**Symptoms:**
```
Error starting userland proxy: listen tcp 0.0.0.0:8000: bind: address already in use
```

**Solutions:**
1. Find process using the port:
   ```bash
   sudo lsof -i :8000
   ```
2. Stop the conflicting process or change port in `docker-compose.yml`:
   ```yaml
   ports:
     - "8001:8000"  # Use port 8001 instead
   ```

---

### Problem: Out of disk space

**Symptoms:**
```
no space left on device
```

**Solutions:**
1. Remove unused Docker resources:
   ```bash
   docker system prune -a --volumes
   ```
2. Check Docker disk usage:
   ```bash
   docker system df
   ```

---

## Production Deployment Considerations

### Security

1. **Change default passwords**:
   - Set strong `POSTGRES_PASSWORD`
   - Use secrets management (Docker Secrets, Kubernetes Secrets)

2. **Disable debug mode**:
   ```yaml
   # In docker-compose.yml, remove --reload flag
   command: uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

3. **Use HTTPS**:
   - Add reverse proxy (nginx, Traefik, Caddy)
   - Configure SSL certificates

4. **Restrict CORS**:
   ```env
   CORS_ORIGINS=https://yourdomain.com
   ```

### Performance

1. **Resource limits** (add to docker-compose.yml):
   ```yaml
   api:
     deploy:
       resources:
         limits:
           cpus: '1'
           memory: 1G
         reservations:
           memory: 512M
   ```

2. **Database backup**:
   ```bash
   docker-compose exec db pg_dump -U postgres mos > backup.sql
   ```

3. **Persistent logs**:
   ```yaml
   api:
     logging:
       driver: "json-file"
       options:
         max-size: "10m"
         max-file: "3"
   ```

### Monitoring

1. **Health checks**: Already configured in `docker-compose.yml`

2. **Prometheus metrics**: Consider adding prometheus exporter

3. **Log aggregation**: Use ELK stack or similar

---

## Docker Compose Service Overview

| Service | Image | Purpose | Ports |
|---------|-------|---------|-------|
| **db** | postgres:16 | PostgreSQL database | 5432 |
| **redis** | redis:7 | Cache and message broker | 6379 |
| **api** | Custom (FastAPI) | REST API server | 8000 |
| **celery-worker** | Custom (Celery) | Background task worker | - |
| **migration** | Custom (Alembic) | Database migration runner | - |

---

## Alternative LLM Backends

MOS supports multiple LLM backends. See [LLM_PROVIDERS.md](./LLM_PROVIDERS.md) for:

- **Claude CLI**: Use Anthropic's Claude without API keys
- **Ollama**: Run local LLMs (free, offline)
- **Azure OpenAI**: Enterprise OpenAI deployment

To switch backends, update `LLM_BACKEND` in `.env` and restart:
```bash
docker-compose restart api
```

---

## Next Steps

After successfully running MOS with Docker:

1. **Explore the API**: Check out the interactive API docs at http://localhost:8000/docs
2. **Set up the frontend**: See frontend setup guide (if available)
3. **Configure followup schedule**: Adjust `FOLLOWUP_MORNING`, `FOLLOWUP_NOON`, `FOLLOWUP_EVENING` times
4. **Test with real data**: Start sending chat messages and creating tasks

---

## Getting Help

- **GitHub Issues**: Report bugs or request features
- **Logs**: Always check logs first (`docker-compose logs`)
- **Documentation**: See `/docs` directory for more guides

For development setup without Docker, see the main [README.md](../README.md).
