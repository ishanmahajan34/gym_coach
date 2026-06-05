FROM python:3.11-slim

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir .

EXPOSE 8000

# Use $PORT so Render can override; create /data in case disk isn't mounted (local dev)
CMD mkdir -p /data && exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
