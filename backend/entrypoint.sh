#!/bin/sh
set -e

echo "Waiting for database..."
python <<'PY'
import os
import sys
import time

from sqlalchemy import create_engine, text

url = os.environ["DATABASE_URL"]
for attempt in range(30):
    try:
        with create_engine(url).connect() as conn:
            conn.execute(text("SELECT 1"))
        print("Database is ready")
        break
    except Exception as exc:
        print(f"Attempt {attempt + 1}/30: {exc}")
        time.sleep(2)
else:
    sys.exit("Database is not available")
PY

echo "Running migrations..."
alembic upgrade head

echo "Initializing database (tables + seed)..."
python scripts/init_db.py

echo "Starting API server..."
echo "----------------------------------------"
echo "  Frontend:  http://localhost:5173/chat"
echo "  API:       http://localhost:8000/api/health"
echo "  Не открывайте 0.0.0.0 в браузере — это не работает!"
echo "----------------------------------------"
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
