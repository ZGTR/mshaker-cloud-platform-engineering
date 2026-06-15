#!/usr/bin/env bash
# Synthetic load generator: hammers /load to drive CPU up so the HPA scales the
# agent-state Deployment.
#   - local:  kubectl -n agents port-forward svc/agent-state 8080:80  -> http://localhost:8080
#   - cloud:  use the LoadBalancer external hostname/IP               -> http://<lb>/load
set -euo pipefail

URL="${1:-http://localhost:8080/load?ms=300}"
CONCURRENCY="${2:-20}"
DURATION="${3:-120}"   # seconds

echo "Load test -> $URL  (concurrency=$CONCURRENCY, duration=${DURATION}s)"
end=$(( $(date +%s) + DURATION ))

worker() {
  while [ "$(date +%s)" -lt "$end" ]; do
    curl -s -o /dev/null "$URL" || true
  done
}

for _ in $(seq "$CONCURRENCY"); do
  worker &
done
wait
echo "Done."
