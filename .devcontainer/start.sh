#!/usr/bin/env bash
# Start both backend and frontend for Codespaces/dev
set -e

echo "Starting ViableOS..."

# Backend
cd /workspaces/ViableOS
uvicorn viableos.api.main:app --host 0.0.0.0 --port 8000 &
echo "Backend started on :8000"

# Wait for backend to be ready
for i in $(seq 1 15); do
  curl -sf http://localhost:8000/health &>/dev/null && break
  sleep 1
done

# Frontend
cd /workspaces/ViableOS/frontend
npx vite --host 0.0.0.0 &
echo "Frontend started on :5173"

echo ""
echo "ViableOS is running!"
echo "  Frontend: http://localhost:5173"
echo "  API:      http://localhost:8000"
echo ""

# Keep alive
wait
