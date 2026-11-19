#!/usr/bin/env bash
# Create .env from .env.example for you to fill in.
#   ./scripts/init-env.sh           refuses if .env already exists
#   ./scripts/init-env.sh --force   replaces it (the old one is kept as .env.bak)
source "$(dirname "$0")/lib.sh"

title "Creating .env"
if [ -f .env ] && [ "${1:-}" != "--force" ]; then
  fail ".env already exists. Edit it directly, or run with --force to start again."
  exit 1
fi
if [ -f .env ]; then
  cp .env .env.bak
  warn "Existing .env backed up to .env.bak"
fi
cp .env.example .env
ok "Created .env from .env.example"
info "Fill in your details:   ${EDITOR:-nano} .env"
info "Postgres credentials apply when the database is first created."
info "Then:                   ./scripts/up.sh"
