#!/usr/bin/env bash
# Start Postgres + Valkey in Docker, install dependencies, migrate, seed.
#
# If Postgres and Valkey are already running on the expected ports (for example
# containers you created by hand), they are reused instead of started again.
source "$(dirname "$0")/lib.sh"
require_tools

title "Setting up"
step "Postgres (localhost:${POSTGRES_PORT}) and Valkey (localhost:${VALKEY_PORT})"

start_compose=0
for entry in "postgres:${POSTGRES_PORT}" "valkey:${VALKEY_PORT}"; do
  service="${entry%%:*}"; port="${entry##*:}"
  holder="$(container_on_port "$port")"
  if [ -n "$holder" ] && ! is_compose_container "$holder"; then
    ok "$service: reusing running container '$holder' on port $port"
  elif [ -z "$holder" ] && port_open "$port"; then
    fail "$service: port $port is taken by something that isn't a Docker container."
    info "Free the port, or pick another one, e.g.: $(printf '%s' "$service" | tr '[:lower:]' '[:upper:]')_PORT=$((port + 1)) ./scripts/up.sh"
    exit 1
  else
    start_compose=1
  fi
done

if [ "$start_compose" = 1 ]; then
  for service in postgres valkey; do
    port="$POSTGRES_PORT"; [ "$service" = valkey ] && port="$VALKEY_PORT"
    holder="$(container_on_port "$port")"
    if [ -z "$holder" ] || is_compose_container "$holder"; then
      dc up -d "$service" >/dev/null 2>&1 || { dc up -d "$service"; exit 1; }
      wait_ready "$(dc ps --format '{{.Name}}' "$service")" "$port" 90
      ok "$service: running from docker-compose.yml on port $port"
    fi
  done
fi

step "Installing Python dependencies (Poetry)"
poetry install --no-root --quiet
ok "Dependencies installed"

step "Applying migrations"
poetry run alembic upgrade head 2>&1 | grep -E "Running|ERROR" | sed 's/^INFO  \[alembic.runtime.migration\] /  /' || true
ok "Database at latest migration"

step "Seeding products and sample orders"
py -m app.seed

ok "Ready"
info "Start the API:   ./scripts/serve.sh"
info "Then simulate:   ./scripts/sim-all.sh"
