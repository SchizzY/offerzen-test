# Shared helpers for the scripts/*.sh files. Source it; don't run it.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# Load .env (if any) without overriding variables already set in the shell.
if [ -f .env ]; then
  while IFS= read -r line || [ -n "$line" ]; do
    line="${line%%#*}"                                   # strip comments
    case "$line" in *=*) ;; *) continue ;; esac
    key="$(printf '%s' "${line%%=*}" | tr -d '[:space:]')"
    value="${line#*=}"
    value="$(printf '%s' "$value" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//' -e 's/^"\(.*\)"$/\1/' -e "s/^'\(.*\)'$/\1/")"
    [ -n "$key" ] && [ -z "${!key+x}" ] && export "$key=$value"
  done < .env
fi

POSTGRES_PORT="${POSTGRES_PORT:-5433}"
VALKEY_PORT="${VALKEY_PORT:-6380}"
API_PORT="${API_PORT:-8000}"

export POSTGRES_PORT VALKEY_PORT API_PORT
export API_URL="${API_URL:-http://localhost:${API_PORT}}"

if [ -t 1 ] && [ -z "${NO_COLOR:-}" ]; then
  BOLD=$'\033[1m'; DIM=$'\033[2m'; RED=$'\033[31m'; GREEN=$'\033[32m'
  YELLOW=$'\033[33m'; CYAN=$'\033[36m'; RESET=$'\033[0m'
else
  BOLD=""; DIM=""; RED=""; GREEN=""; YELLOW=""; CYAN=""; RESET=""
fi

title() { printf '\n%s%s━━━ %s ━━━%s\n' "$BOLD" "$CYAN" "$*" "$RESET"; }
step()  { printf '\n%s▶ %s%s\n' "$BOLD" "$*" "$RESET"; }
info()  { printf '%s  %s%s\n' "$DIM" "$*" "$RESET"; }
ok()    { printf '%s✔ %s%s\n' "$GREEN" "$*" "$RESET"; }
warn()  { printf '%s! %s%s\n' "$YELLOW" "$*" "$RESET"; }
fail()  { printf '%s✘ %s%s\n' "$RED" "$*" "$RESET"; }

dc() { docker compose "$@"; }
# Run Python from the project's Poetry environment.
py() { poetry run python "$@"; }

require_tools() {
  local tool
  for tool in docker poetry curl; do
    command -v "$tool" >/dev/null 2>&1 || { fail "$tool is required but not installed"; exit 1; }
  done
}

health() { curl -s "${API_URL}/health" || echo '{"status":"unreachable"}'; }

# Is something accepting connections on this local port? Uses bash's built-in
# /dev/tcp, so no netcat is needed.
port_open() { (exec 3<>"/dev/tcp/127.0.0.1/$1") >/dev/null 2>&1; }

# Name of the running Docker container publishing a host port (empty if none).
# Works for compose containers and hand-made ones alike.
container_on_port() { docker ps --filter "publish=$1" --format '{{.Names}}' 2>/dev/null | head -n 1; }

# Is this container part of this repo's compose project?
is_compose_container() { dc ps -a --format '{{.Name}}' 2>/dev/null | grep -qx "$1"; }

# Wait until a container is ready: its healthcheck passes, or (if it has none)
# it is running and the port answers.
wait_ready() {
  local name="$1" port="$2" timeout="${3:-60}" status i=0
  while [ "$i" -lt "$timeout" ]; do
    status="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$name" 2>/dev/null || true)"
    if [ "$status" = "healthy" ] || { [ "$status" = "running" ] && port_open "$port"; }; then
      return 0
    fi
    sleep 1; i=$((i + 1))
  done
  fail "$name not ready after ${timeout}s"; docker logs --tail 20 "$name" 2>&1 | sed 's/^/  /'; return 1
}

# The simulations need Postgres, Valkey and the API all reachable. They don't
# care whether the containers came from this compose file or were made by hand.
require_up() {
  port_open "$POSTGRES_PORT" || { fail "Nothing is listening on localhost:${POSTGRES_PORT} (Postgres). Run ./scripts/up.sh"; exit 1; }
  port_open "$VALKEY_PORT"   || { fail "Nothing is listening on localhost:${VALKEY_PORT} (Valkey). Run ./scripts/up.sh"; exit 1; }
  if ! curl -sf "${API_URL}/health" >/dev/null 2>&1; then
    fail "The API isn't reachable at ${API_URL}. Start it with: ./scripts/serve.sh"; exit 1
  fi
  case "$(health)" in
    *'"database":"ok"'*) ;;
    *) fail "The API is up but can't reach Postgres: $(health)"; exit 1 ;;
  esac
}
