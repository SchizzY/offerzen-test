#!/usr/bin/env bash
# Unhappy path 1: the same order_ref submitted several times at once.
source "$(dirname "$0")/lib.sh"
require_up

title "Unhappy path: duplicate submissions"
info "13 requests for 6 order_refs, all released at the same instant."
info "Expect: each ref created once (201), every duplicate rejected (409),"
info "        stock deducted once per created order."

step "Firing the burst"
if py -m scripts.burst; then
  ok "Duplicates: PASS"
else
  fail "Duplicates: FAIL"; exit 1
fi
