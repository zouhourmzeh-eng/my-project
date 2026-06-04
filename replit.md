# QMS / SMQ — Quality Management System

## Overview

Production-ready, cloud-deployable Quality Management System for QMS consultants.
Two independent deployable units:

- `backend/` — FastAPI (async) + SQLAlchemy 2.0 + Alembic + PostgreSQL
- `frontend/` — React + Vite + TypeScript + Tailwind + React Query

## Stack

- **Backend**: FastAPI · SQLAlchemy 2.0 (async) · Alembic · Pydantic v2 · python-jose · passlib[bcrypt] · boto3 · websockets
- **Frontend**: React 18 · Vite · TypeScript · Tailwind · React Query · Axios · React Router
- **DB**: PostgreSQL (Supabase / Neon)
- **Storage**: S3 / Cloudflare R2 (pre-signed PUT + server passthrough)
- **Auth**: JWT access + refresh, bcrypt, RBAC (consultant / assistant / rmq)
- **Real-time**: WebSockets per-document chat + per-user notifications

## Deployment targets

- Backend → Render (`backend/render.yaml`) / Railway / Fly.io (`backend/Dockerfile`)
- Frontend → Vercel (`frontend/vercel.json`) / Netlify

See `README.md` for the full step-by-step deploy guide and `backend/.env.example`,
`frontend/.env.example` for required env vars.

## Local dev

- Backend: `cd backend && pip install -r requirements.txt && alembic upgrade head && uvicorn app.main:app --reload`
- Frontend: `cd frontend && npm install && npm run dev`

## Notes

- Replit-monorepo TypeScript artifacts (`artifacts/api-server`, `artifacts/mockup-sandbox`)
  are scaffolding from the workspace template and are not part of this product.
- Auto-generated API docs at `/docs` (Swagger) and `/redoc`.
