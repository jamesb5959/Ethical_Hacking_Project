import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

WEAVIATE_URL = os.environ.get("WEAVIATE_URL", "http://localhost:8080").rstrip("/")
CLASS_NAME = os.environ.get("WEAVIATE_CLASS", "SydneyMemory")
VECTOR_SIZE = 64
REQUEST_TIMEOUT = 5


@dataclass
class MemoryItem:
    title: str
    content: str
    kind: str = "note"
    source: str = "user"


def is_enabled() -> bool:
    return os.environ.get("WEAVIATE_ENABLED", "1") != "0"


def _request(method: str, path: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    data = None
    headers = {"Content-Type": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(
        f"{WEAVIATE_URL}{path}",
        data=data,
        headers=headers,
        method=method,
    )
    with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
        body = resp.read().decode("utf-8")
        return json.loads(body) if body else {}


def _vectorize(text: str) -> List[float]:
    vector = [0.0] * VECTOR_SIZE
    words = [word.lower() for word in text.split() if word.strip()]
    for word in words:
        digest = hashlib.sha256(word.encode("utf-8")).digest()
        index = int.from_bytes(digest[:2], "big") % VECTOR_SIZE
        sign = 1.0 if digest[2] % 2 == 0 else -1.0
        vector[index] += sign

    magnitude = sum(value * value for value in vector) ** 0.5
    if magnitude:
        vector = [value / magnitude for value in vector]
    return vector


def ensure_schema() -> None:
    if not is_enabled():
        return

    try:
        _request("GET", f"/v1/schema/{CLASS_NAME}")
        return
    except urllib.error.HTTPError as exc:
        if exc.code != 404:
            raise

    _request(
        "POST",
        "/v1/schema",
        {
            "class": CLASS_NAME,
            "vectorizer": "none",
            "properties": [
                {"name": "title", "dataType": ["text"]},
                {"name": "content", "dataType": ["text"]},
                {"name": "kind", "dataType": ["text"]},
                {"name": "source", "dataType": ["text"]},
                {"name": "created_at", "dataType": ["number"]},
            ],
        },
    )


def save_memory(item: MemoryItem) -> Dict[str, Any]:
    ensure_schema()
    payload = {
        "class": CLASS_NAME,
        "properties": {
            "title": item.title,
            "content": item.content,
            "kind": item.kind,
            "source": item.source,
            "created_at": time.time(),
        },
        "vector": _vectorize(f"{item.title}\n{item.content}"),
    }
    return _request("POST", "/v1/objects", payload)


def search_memory(query: str, limit: int = 3) -> List[Dict[str, Any]]:
    if not query.strip() or not is_enabled():
        return []

    ensure_schema()
    safe_limit = max(1, min(int(limit), 25))
    vector = json.dumps(_vectorize(query))
    query_text = f"""
        query SearchMemory {{
          Get {{
            {CLASS_NAME}(nearVector: {{vector: {vector}}}, limit: {safe_limit}) {{
              title
              content
              kind
              source
              created_at
              _additional {{ distance }}
            }}
          }}
        }}
        """
    gql = {
        "query": query_text,
    }
    result = _request("POST", "/v1/graphql", gql)
    if result.get("errors"):
        raise RuntimeError(result["errors"])

    matches = result.get("data", {}).get("Get", {}).get(CLASS_NAME)
    return matches or []


def upload_text(filename: str, content: str, chunk_chars: int = 2000) -> int:
    saved = 0
    for index in range(0, len(content), chunk_chars):
        chunk = content[index:index + chunk_chars].strip()
        if not chunk:
            continue
        part = (index // chunk_chars) + 1
        save_memory(
            MemoryItem(
                title=f"{filename} part {part}",
                content=chunk,
                kind="file",
                source=filename,
            )
        )
        saved += 1
    return saved
