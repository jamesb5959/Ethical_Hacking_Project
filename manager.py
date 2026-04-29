from flask import Flask, request, jsonify
from tools.gemma import handle_prompt
from weaviate import MemoryItem, save_memory, search_memory, upload_text

app = Flask(__name__)


def build_memory_context(prompt):
    try:
        memories = search_memory(prompt, limit=3)
    except Exception as e:
        print(f"[manager] memory search skipped: {e}", flush=True)
        return ""

    blocks = []
    for item in memories:
        title = item.get("title", "Untitled")
        kind = item.get("kind", "memory")
        content = item.get("content", "")
        blocks.append(f"[{kind}] {title}\n{content}")
    return "\n\n".join(blocks)

@app.route("/generate", methods=["POST"])
def generate():
    data = request.get_json(silent=True) or {}
    prompt = data.get("prompt", "").strip()
    print(f"[manager] got prompt: {prompt!r}", flush=True)

    if not prompt:
        return jsonify({"error": "prompt is required"}), 400

    try:
        context = build_memory_context(prompt)
        response_text = handle_prompt(prompt, context=context)
    except Exception as e:
        print(f"[manager] error calling Sydney: {e}", flush=True)
        return jsonify({"error": str(e)}), 500

    print(f"[manager] sending response: {response_text!r}", flush=True)
    return jsonify({"response": response_text})


@app.route("/memory/save", methods=["POST"])
def memory_save():
    data = request.get_json(silent=True) or {}
    prompt = data.get("prompt", "").strip()
    response = data.get("response", "").strip()
    title = data.get("title", prompt[:80] or "Saved memory").strip()
    kind = data.get("kind", "workflow").strip()

    content = data.get("content", "").strip()
    if not content:
        content = f"Prompt:\n{prompt}\n\nResponse:\n{response}".strip()
    if not content:
        return jsonify({"error": "content, prompt, or response is required"}), 400

    try:
        result = save_memory(MemoryItem(title=title, content=content, kind=kind, source="tui"))
    except Exception as e:
        print(f"[manager] error saving memory: {e}", flush=True)
        return jsonify({"error": str(e)}), 500

    return jsonify({"saved": True, "id": result.get("id")})


@app.route("/memory/search", methods=["GET"])
def memory_search():
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"error": "q is required"}), 400

    try:
        results = search_memory(query, limit=5)
    except Exception as e:
        print(f"[manager] error searching memory: {e}", flush=True)
        return jsonify({"error": str(e)}), 500

    return jsonify({"results": results})


@app.route("/memory/upload", methods=["POST"])
def memory_upload():
    if request.files:
        file = next(iter(request.files.values()))
        filename = file.filename or "upload.txt"
        content = file.read().decode("utf-8", errors="replace")
    else:
        data = request.get_json(silent=True) or {}
        filename = data.get("filename", "upload.txt")
        content = data.get("content", "")

    if not content.strip():
        return jsonify({"error": "file content is required"}), 400

    try:
        chunks = upload_text(filename, content)
    except Exception as e:
        print(f"[manager] error uploading memory: {e}", flush=True)
        return jsonify({"error": str(e)}), 500

    return jsonify({"uploaded": True, "chunks": chunks})

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5000)
