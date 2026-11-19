#!/usr/bin/env bash
# Unhappy path 2: the stock side is interrupted (worker paused), orders keep being
# accepted, and stock catches up exactly once the worker resumes.
source "$(dirname "$0")/lib.sh"
require_up

# Never leave the stock worker paused, even if this script fails or is interrupted.
trap 'py -m scripts.stock_worker resume >/dev/null 2>&1 || true' EXIT

title "Unhappy path: stock outage, then catch-up"
info "Pause the stock worker, submit orders, check they're accepted but stock waits,"
info "resume, check stock catches up exactly: nothing missed, nothing twice, never < 0."

if py -m scripts.stock_outage; then
  ok "Stock outage: PASS"
else
  fail "Stock outage: FAIL"; exit 1
fi
