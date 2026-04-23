#!/usr/bin/env bash
set -euo pipefail

IMAGE_NAME="${IMAGE_NAME:-gemma-chat}"
CONTAINER_NAME="${CONTAINER_NAME:-gemma-chat}"
PORT="${PORT:-5000}"
NETWORK_NAME="${NETWORK_NAME:-sydney-net}"
WEAVIATE_CONTAINER_NAME="${WEAVIATE_CONTAINER_NAME:-sydney-weaviate}"
WEAVIATE_IMAGE="${WEAVIATE_IMAGE:-semitechnologies/weaviate:1.24.10}"
WEAVIATE_PORT="${WEAVIATE_PORT:-8080}"
WEAVIATE_VOLUME="${WEAVIATE_VOLUME:-sydney-weaviate-data}"
LOCAL_MODEL_DIR="${LOCAL_MODEL_DIR:-$(pwd)/models/gemma-2-2b}"
CONTAINER_MODEL_DIR="${CONTAINER_MODEL_DIR:-/models/gemma-2-2b}"

if ! docker network inspect "${NETWORK_NAME}" >/dev/null 2>&1; then
  docker network create "${NETWORK_NAME}" >/dev/null
fi

if ! docker ps --format '{{.Names}}' | grep -qx "${WEAVIATE_CONTAINER_NAME}"; then
  if docker ps -a --format '{{.Names}}' | grep -qx "${WEAVIATE_CONTAINER_NAME}"; then
    docker rm "${WEAVIATE_CONTAINER_NAME}" >/dev/null
  fi

  docker run -d \
    --name "${WEAVIATE_CONTAINER_NAME}" \
    --network "${NETWORK_NAME}" \
    -p "${WEAVIATE_PORT}:8080" \
    -v "${WEAVIATE_VOLUME}:/var/lib/weaviate" \
    -e QUERY_DEFAULTS_LIMIT=25 \
    -e AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED=true \
    -e PERSISTENCE_DATA_PATH=/var/lib/weaviate \
    -e DEFAULT_VECTORIZER_MODULE=none \
    -e CLUSTER_HOSTNAME=node1 \
    "${WEAVIATE_IMAGE}" >/dev/null
  echo "Started Weaviate: http://localhost:${WEAVIATE_PORT}"
else
  echo "Using existing Weaviate container: ${WEAVIATE_CONTAINER_NAME}"
fi

if command -v curl >/dev/null 2>&1; then
  for _ in $(seq 1 30); do
    if curl -fsS "http://localhost:${WEAVIATE_PORT}/v1/.well-known/ready" >/dev/null 2>&1; then
      break
    fi
    sleep 1
  done
fi

DOCKER_ARGS=()
if command -v nvidia-smi >/dev/null 2>&1; then
  DOCKER_ARGS+=(--gpus all)
fi

if [ -n "${HF_TOKEN:-}" ]; then
  DOCKER_ARGS+=(-e "HF_TOKEN=${HF_TOKEN}")
  DOCKER_ARGS+=(-e "HUGGING_FACE_HUB_TOKEN=${HF_TOKEN}")
fi
if [ -n "${HUGGING_FACE_HUB_TOKEN:-}" ]; then
  DOCKER_ARGS+=(-e "HUGGING_FACE_HUB_TOKEN=${HUGGING_FACE_HUB_TOKEN}")
  DOCKER_ARGS+=(-e "HF_TOKEN=${HUGGING_FACE_HUB_TOKEN}")
fi
if [ -n "${CPU_MAX_NEW_TOKENS:-}" ]; then
  DOCKER_ARGS+=(-e "CPU_MAX_NEW_TOKENS=${CPU_MAX_NEW_TOKENS}")
fi
if [ -n "${CUDA_MAX_NEW_TOKENS:-}" ]; then
  DOCKER_ARGS+=(-e "CUDA_MAX_NEW_TOKENS=${CUDA_MAX_NEW_TOKENS}")
fi

if [ -d "${LOCAL_MODEL_DIR}" ]; then
  DOCKER_ARGS+=(-v "${LOCAL_MODEL_DIR}:${CONTAINER_MODEL_DIR}:ro")
  DOCKER_ARGS+=(-e "MODEL_NAME=${CONTAINER_MODEL_DIR}")
  echo "Using local model: ${LOCAL_MODEL_DIR}"
elif [ -n "${MODEL_NAME:-}" ]; then
  DOCKER_ARGS+=(-e "MODEL_NAME=${MODEL_NAME}")
elif [ -z "${HF_TOKEN:-}" ] && [ -z "${HUGGING_FACE_HUB_TOKEN:-}" ]; then
  echo "Warning: HF_TOKEN or HUGGING_FACE_HUB_TOKEN is not set."
  echo "No local model was found at ${LOCAL_MODEL_DIR}."
  echo "Sydney uses a gated Gemma model, so /generate will fail unless the model is cached or public access is available."
fi

DOCKER_ARGS+=(
  --rm
  --name "${CONTAINER_NAME}"
  --network "${NETWORK_NAME}"
  -e "WEAVIATE_URL=http://${WEAVIATE_CONTAINER_NAME}:8080"
  -p "${PORT}:5000"
  "${IMAGE_NAME}"
)

docker run "${DOCKER_ARGS[@]}"
