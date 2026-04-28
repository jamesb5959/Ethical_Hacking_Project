#!/usr/bin/env bash
set -euo pipefail

IMAGE_NAME="${IMAGE_NAME:-gemma-chat}"
FRONTEND_DIR="${FRONTEND_DIR:-frontend}"

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is required. Install Docker, then run this script again." >&2
  exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "npm is required for the Svelte frontend. Install Node.js and npm, then run this script again." >&2
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  echo "Docker is not running or your user cannot access it." >&2
  exit 1
fi

if command -v nvidia-smi >/dev/null 2>&1 && ! docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu20.04 nvidia-smi >/dev/null 2>&1; then
  echo "NVIDIA GPU detected, but Docker GPU support is not ready."
  echo "Install NVIDIA Container Toolkit, restart Docker, then rerun this script."
  echo "Docs: https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html"
  exit 1
fi

docker build -t "${IMAGE_NAME}" .
docker pull semitechnologies/weaviate:1.24.10

if [ -d "${FRONTEND_DIR}" ]; then
  npm install --prefix "${FRONTEND_DIR}"
fi

echo "Built ${IMAGE_NAME}."
echo "Run it with: ./start.sh"
