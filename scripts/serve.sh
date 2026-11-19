#!/usr/bin/env bash
# Run the API with auto-reload (Ctrl+C to stop).
#
# --timeout-graceful-shutdown: event streams (/events/stream) never finish on
# their own, so without a deadline a reload or Ctrl+C waits for every consumer to
# disconnect. After the deadline open streams are closed; SSE clients reconnect
# with Last-Event-ID and resume without gaps.
source "$(dirname "$0")/lib.sh"

title "API on ${API_URL}  (docs: ${API_URL}/docs)"
exec poetry run uvicorn app.main:app --host 127.0.0.1 --port "${API_PORT}" --reload \
  --timeout-graceful-shutdown "${GRACEFUL_SHUTDOWN_SECONDS:-3}"
