#!/usr/bin/env bash
# Wipe orders, restore products to seed stock/prices, clear Valkey, reseed.
source "$(dirname "$0")/lib.sh"
require_up

title "Resetting to a clean, seeded state"
step "Reset"
py -m scripts.reset --yes
step "Seed"
py -m app.seed
ok "Environment reset"
