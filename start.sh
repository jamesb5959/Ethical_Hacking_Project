#!/usr/bin/env bash
set -euo pipefail

IMAGE_NAME="${IMAGE_NAME:-gemma-chat}"
CONTAINER_NAME="${CONTAINER_NAME:-gemma-chat}"
PORT="${PORT:-5000}"
LOCAL_MODEL_DIR="${LOCAL_MODEL_DIR:-$(pwd)/models/gemma-2-2b}"
CONTAINER_MODEL_DIR="${CONTAINER_MODEL_DIR:-/models/gemma-2-2b}"

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

if [ -d "${LOCAL_MODEL_DIR}" ]; then
  DOCKER_ARGS+=(-v "${LOCAL_MODEL_DIR}:${CONTAINER_MODEL_DIR}:ro")
  DOCKER_ARGS+=(-e "MODEL_NAME=${CONTAINER_MODEL_DIR}")
  echo "Using local model: ${LOCAL_MODEL_DIR}"
elif [ -n "${MODEL_NAME:-}" ]; then
  DOCKER_ARGS+=(-e "MODEL_NAME=${MODEL_NAME}")
elif [ -z "${HF_TOKEN:-}" ] && [ -z "${HUGGING_FACE_HUB_TOKEN:-}" ]; then
  echo "Warning: HF_TOKEN or HUGGING_FACE_HUB_TOKEN is not set."
  echo "No local model was found at ${LOCAL_MODEL_DIR}."
  echo "Gemma is gated, so /generate will fail unless the model is cached or public access is available."
fi

DOCKER_ARGS+=(
  --rm
  --name "${CONTAINER_NAME}"
  -p "${PORT}:5000"
  "${IMAGE_NAME}"
)

docker run "${DOCKER_ARGS[@]}"
