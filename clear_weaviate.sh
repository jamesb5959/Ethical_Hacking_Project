#!/usr/bin/env bash
set -euo pipefail

WEAVIATE_URL="${WEAVIATE_URL:-http://localhost:8080}"
WEAVIATE_CLASS="${WEAVIATE_CLASS:-SydneyMemory}"

if ! command -v curl >/dev/null 2>&1; then
  echo "curl is required to clear Weaviate." >&2
  exit 1
fi

if ! curl -fsS "${WEAVIATE_URL}/v1/.well-known/ready" >/dev/null 2>&1; then
  echo "Weaviate is not reachable at ${WEAVIATE_URL}." >&2
  echo "Start it with ./start.sh, then rerun this script." >&2
  exit 1
fi

status="$(curl -sS -o /tmp/clear_weaviate_response.txt -w "%{http_code}" \
  -X DELETE "${WEAVIATE_URL}/v1/schema/${WEAVIATE_CLASS}")"

if [ "${status}" = "200" ]; then
  echo "Cleared Weaviate class ${WEAVIATE_CLASS}."
elif [ "${status}" = "404" ]; then
  echo "Weaviate class ${WEAVIATE_CLASS} does not exist. Nothing to clear."
else
  echo "Failed to clear Weaviate class ${WEAVIATE_CLASS}. HTTP ${status}" >&2
  cat /tmp/clear_weaviate_response.txt >&2
  exit 1
fi

rm -f /tmp/clear_weaviate_response.txt
