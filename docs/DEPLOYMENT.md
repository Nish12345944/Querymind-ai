# Deployment Guide

This guide covers deploying QueryMind AI to production using Render (free tier).

---

## Backend — Render Web Service

1. Go to [render.com](https://render.com) → New → Web Service
2. Connect your GitHub repo
3. Set the following:

| Setting | Value |
|---|---|
| Root directory | `backend` |
| Runtime | Python 3 |
| Build command | `pip install -r requirements.txt` |
| Start command | `uvicorn main:app --host 0.0.0.0 --port $PORT` |

4. Add environment variables in the Render dashboard:

```
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/novamart
GROQ_API_KEY=your_groq_api_key
API_KEY=your_secret_api_key
FRONTEND_URL=https://your-frontend.onrender.com
```

5. Deploy. Note your backend URL (e.g. `https://querymind-backend-xxxx.onrender.com`).

6. After first deploy, index the schema:

```bash
curl -X POST https://your-backend.onrender.com/rag/index \
  -H "X-API-Key: your_api_key"
```

---

## Frontend — Render Static Site

1. Go to Render → New → Static Site
2. Connect your GitHub repo
3. Set the following:

| Setting | Value |
|---|---|
| Root directory | `frontend` |
| Build command | `npm install && npm run build` |
| Publish directory | `dist` |

4. Add environment variables:

```
VITE_API_BASE_URL=https://your-backend.onrender.com
VITE_API_KEY=your_secret_api_key
```

5. Deploy.

---

## Production Database

QueryMind requires a PostgreSQL database with the NovaMart schema loaded.

Options:
- **Render PostgreSQL** — free tier available, add as a linked service
- **Supabase** — free tier with 500 MB storage
- **Neon** — serverless PostgreSQL, generous free tier

After provisioning, load the NovaMart schema:

```bash
pg_restore -d your_connection_string novamart_backup.dump
```

Verify connectivity:

```bash
curl https://your-backend.onrender.com/database/test \
  -H "X-API-Key: your_api_key"
```

Expected response:
```json
{ "status": "connected", "database": "novamart" }
```

---

## Verify Production Deployment

```bash
# 1. Liveness
curl https://your-backend.onrender.com/health

# 2. Readiness
curl https://your-backend.onrender.com/ready

# 3. Query
curl -X POST https://your-backend.onrender.com/query/ \
  -H "X-API-Key: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{"question": "How many customers are there?"}'
```

---

## Production CORS

Set `FRONTEND_URL` in the backend environment to your production frontend URL.
This is automatically added to the CORS allowlist in `main.py`.

```
FRONTEND_URL=https://querymind-frontend-xxxx.onrender.com
```

---

## Docker (self-hosted)

```bash
cp backend/.env.example backend/.env
# Fill in all values in backend/.env

VITE_API_BASE_URL=http://your-server-ip:8000 docker compose up -d --build
```
