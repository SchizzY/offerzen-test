#!/usr/bin/env bash
# Stop Postgres and Valkey. Pass --wipe to also delete their data volumes.
source "$(dirname "$0")/lib.sh"

if [ "${1:-}" = "--wipe" ]; then
  title "Stopping Postgres and Valkey and deleting all data"
  dc down -v
  ok "Stopped; volumes deleted"
else
  title "Stopping Postgres and Valkey"
  dc down
  ok "Stopped (data kept; use --wipe to delete it)"
fi
