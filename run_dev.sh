#!/usr/bin/env bash
# Local dev: backend on :8000, Vite UI on :5173 (proxying /api). Uses SQLite unless backend/.env says otherwise.
set -e
cd "$(dirname "$0")"
[ -f backend/.env ] || cp backend/.env.example backend/.env
(cd backend && pip install -q -r requirements.txt && uvicorn app.main:app --reload --port 8000) &
(cd frontend && npm install --no-audit --no-fund && npm run dev) &
wait
