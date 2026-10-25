#!/bin/sh
cd "$(dirname "$0")" || exit 1
if [ ! -x .venv/bin/python ]; then
  echo 'Run the setup steps in README.md first.'
  exit 1
fi
exec .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8080
