#!/usr/bin/env bash
set -euo pipefail

MODEL_ID="${MODEL_ID:-google/gemma-2-2b}"
MODELS_DIR="${MODELS_DIR:-models}"
MODEL_DIR="${MODEL_DIR:-${MODELS_DIR}/gemma-2-2b}"

mkdir -p "${MODELS_DIR}"

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required to download ${MODEL_ID}." >&2
  exit 1
fi

if ! python3 -c "import huggingface_hub" >/dev/null 2>&1; then
  echo "Installing huggingface_hub locally for the download helper..."
  python3 -m pip install --user huggingface_hub
fi

echo "Downloading ${MODEL_ID} into ${MODEL_DIR}"
echo "This model is gated by Hugging Face. If unauthenticated access fails,"
echo "accept access on the model page and rerun with HF_TOKEN set."

python3 - <<'PY'
import os
import sys

from huggingface_hub import snapshot_download
from huggingface_hub.errors import GatedRepoError, HfHubHTTPError, LocalEntryNotFoundError

model_id = os.environ.get("MODEL_ID", "google/gemma-2-2b")
model_dir = os.environ.get("MODEL_DIR", "models/gemma-2-2b")
token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")

try:
    path = snapshot_download(
        repo_id=model_id,
        local_dir=model_dir,
        token=token,
    )
except GatedRepoError:
    print(
        "\nDownload failed: this Gemma repo is gated.\n"
        f"1. Request or accept access at https://huggingface.co/{model_id}\n"
        "2. Create a Hugging Face access token.\n"
        "3. Rerun: HF_TOKEN=hf_... ./download_gemma.sh\n",
        file=sys.stderr,
    )
    sys.exit(1)
except LocalEntryNotFoundError as exc:
    print(
        "\nDownload failed before any model files were available locally.\n"
        "For Gemma this usually means the token cannot access the gated repo.\n"
        f"1. Accept access at https://huggingface.co/{model_id}\n"
        "2. If using a fine-grained token, enable access to public gated repositories.\n"
        "3. Rerun: HF_TOKEN=hf_... ./download_gemma.sh\n"
        f"\nOriginal error: {exc}\n",
        file=sys.stderr,
    )
    sys.exit(1)
except HfHubHTTPError as exc:
    print(
        "\nDownload failed.\n"
        "If this is a 403 for a fine-grained token, enable access to public gated repositories.\n"
        f"\nOriginal error: {exc}\n",
        file=sys.stderr,
    )
    sys.exit(1)

print(f"Downloaded model files to {path}")
PY
