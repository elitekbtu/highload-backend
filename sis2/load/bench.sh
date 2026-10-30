#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

DURATION=${DURATION:-30s}
for run in single:500 batch:200 like:300; do
  scenario=${run%%:*}
  rate=${run##*:}
  for protocol in rest grpc; do
    echo "== $protocol $scenario @ $rate rps"
    docker compose --profile bench run --rm -q k6 run -q \
      -e SCENARIO="$scenario" -e RATE="$rate" -e DURATION="$DURATION" \
      --summary-export "/results/$protocol-$scenario.json" "/scripts/$protocol.js" >/dev/null
  done
done

uv run python load/summarize.py
