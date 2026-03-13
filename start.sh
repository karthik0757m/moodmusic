#!/bin/bash
# Use Railway's PORT or default to 8080
PORT=${PORT:-8080}
echo "Starting server on port $PORT"
gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120 --log-level info
