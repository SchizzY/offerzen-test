#!/usr/bin/env bash
# Run the example consumer: prints order events from the SSE stream as they happen.
#   ./scripts/consume.sh                 resume from the saved cursor (Ctrl+C to stop)
#   ./scripts/consume.sh --from-start    replay every event
source "$(dirname "$0")/lib.sh"
require_up

title "Order event consumer  (${API_URL}/events/stream)"
exec poetry run python -m scripts.consume_orders "$@"
