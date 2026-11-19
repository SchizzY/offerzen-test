#!/usr/bin/env bash
# Run the test suite. Needs Postgres and Valkey (./scripts/up.sh), not the API.
# Tests use their own database (<POSTGRES_DB>_test) and Valkey DB 1, so your
# dev data is left alone. Extra arguments go to pytest, e.g. -k duplicates.
source "$(dirname "$0")/lib.sh"

port_open "$POSTGRES_PORT" || { fail "Postgres isn't running on localhost:${POSTGRES_PORT}. Run ./scripts/up.sh"; exit 1; }
port_open "$VALKEY_PORT"   || { fail "Valkey isn't running on localhost:${VALKEY_PORT}. Run ./scripts/up.sh"; exit 1; }

title "Tests"
exec poetry run pytest "$@"
