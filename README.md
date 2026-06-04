# QMS / SMQ — Quality Management System

A production-ready, cloud-deployable Quality Management System for QMS consultants.

- **Backend:** FastAPI (async) + SQLAlchemy 2.0 + Alembic + PostgreSQL
- **Frontend:** React + Vite + TypeScript + Tailwind + React Query
- **Auth:** JWT (access + refresh) + bcrypt + Role-Based Access Control
- **Real-time:** WebSockets (chat + notifications)
- **Storage:** S3 / Cloudflare R2 (pre-signed uploads + server passthrough)

---

## 📁 Project structure

```
backend/                 FastAPI service (deploy to Render / Railway / Fly.io)
  app/
    api/                 Routers (auth, projects, processes, documents, messages,
                         notifications, uploads, dashboard, ws)
    core/                Settings, JWT, password hashing
    db/                  Async SQLAlchemy engine
    models/              ORM models
    schemas/             Pydantic schemas
    services/            S3 + audit log helpers
    websockets/          Connection manager
  alembic/               Migrations
  Dockerfile · render.yaml · requirements.txt
frontend/                React + Vite app (deploy to Vercel / Netlify)
```

---

## ✨ Features

- **Auth**: register / login / refresh / `/me`, JWT access + refresh, bcrypt hashing.
- **RBAC**: 3 roles — `consultant` (full access), `assistant`, `rmq` (limited).
- **Projects**: company, role, sector, product, market (CE / FDI / FDA…), standards, members.
- **Processes**: per project, with file upload (PDF / DOC).
- **SMQ Documents**: title, description, status (`draft → validated → approved`), version history.
- **Real-time chat per document** via WebSocket, with file attachments and timestamps.
- **Notifications**: real-time updates for messages, uploads, status changes.
- **Dashboard**: project / document counters, items to validate, recent activity.
- **Audit log** of every meaningful action (entity, actor, timestamp, detail).
- **Auto-generated OpenAPI docs** at `/docs` (Swagger) and `/redoc`.

---

## 🚀 Deployment

### 1. Database — Supabase or Neon

1. Create a Postgres database on [Supabase](https://supabase.com/) or [Neon](https://neon.tech/).
2. Copy the connection string and convert it to async format:
   ```
   postgresql+asyncpg://USER:PASSWORD@HOST:5432/DBNAME
   ```
   (For Supabase, use the **direct** connection string and keep `?sslmode=require` if shown.)

### 2. Object storage — Cloudflare R2 (recommended) or AWS S3

1. Create a bucket (e.g. `qms-documents`).
2. Create an API token / access key with read+write to the bucket.
3. Configure **CORS** on the bucket so the frontend can `PUT` files directly:
   ```json
   [{ "AllowedOrigins": ["https://your-frontend.vercel.app"],
      "AllowedMethods": ["PUT", "GET"],
      "AllowedHeaders": ["*"], "MaxAgeSeconds": 3600 }]
   ```

### 3. Backend — Render

1. Push this repo to GitHub.
2. In Render → **New Web Service** → connect the repo. Render auto-detects `backend/render.yaml`.
3. Root directory: `backend`.
4. Set environment variables (see `backend/.env.example`):
   - `DATABASE_URL`
   - `SECRET_KEY` (long random string — Render can generate one)
   - `CORS_ORIGINS` = `https://your-frontend.vercel.app`
   - `S3_BUCKET`, `S3_REGION`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`,
     `S3_ENDPOINT_URL` (e.g. `https://<account>.r2.cloudflarestorage.com`),
     `S3_PUBLIC_URL` (e.g. `https://pub-xxxx.r2.dev`)
5. Build: `pip install -r requirements.txt`.
   Start: `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT`.

#### Railway / Fly.io

The provided `Dockerfile` works on both. Just set the same env vars.

### 4. Frontend — Vercel

1. Vercel → **Import Project** → set root directory to `frontend`.
2. Build command: `npm run build` · Output directory: `dist`.
3. Environment variables:
   - `VITE_API_URL=https://your-api.onrender.com/api`
   - `VITE_WS_URL=wss://your-api.onrender.com/api`
4. Deploy. The included `vercel.json` ensures SPA routes work.

---

## 🛠 Local development

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # edit DATABASE_URL etc.
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend
npm install
cp .env.example .env
npm run dev
```

Open http://localhost:5173 — register a **Consultant** account first to unlock all features.

---

## 🔐 Security notes

- Passwords are stored only as bcrypt hashes.
- JWT access tokens are short-lived (30 min) with longer refresh tokens (7 days).
- All inputs are validated by Pydantic v2 — protects against malformed data and helps prevent injection.
- SQLAlchemy uses parameterised queries — no SQL injection.
- React escapes by default — no raw HTML rendering.
- CORS is restricted to the origins in `CORS_ORIGINS`.
- WebSocket connections require a valid JWT in the query string.
- Every state change is recorded in `audit_logs`.

---

## 📑 API documentation

Once the backend is running, open:

- Swagger UI: `https://<api-host>/docs`
- ReDoc: `https://<api-host>/redoc`
- OpenAPI JSON: `https://<api-host>/openapi.json`

---

## 🗄 Database schema

Tables: `users`, `projects`, `project_members`, `processes`, `documents`,
`document_versions`, `messages`, `attachments`, `notifications`, `audit_logs`.
Full DDL lives in `backend/alembic/versions/0001_initial.py`.

To create a new migration after model changes:

```bash
cd backend
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```
