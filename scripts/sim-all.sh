#!/usr/bin/env bash
# Reset, then run every scenario and print a summary.
source "$(dirname "$0")/lib.sh"
require_up

names=(); results=()
run() {
  local name="$1"; shift
  if "$@"; then results+=("PASS"); else results+=("FAIL"); fi
  names+=("$name")
}

run "Reset + seed"                             ./scripts/reset.sh
run "Unhappy path 1: duplicate submissions"    ./scripts/sim-duplicates.sh
run "Unhappy path 2: stock outage + catch-up"  ./scripts/sim-stock-outage.sh

title "Summary"
failed=0
for i in "${!names[@]}"; do
  if [ "${results[$i]}" = "PASS" ]; then ok "${names[$i]}"; else fail "${names[$i]}"; failed=1; fi
done
exit "$failed"
