# manager.py

from flask import Flask, request, jsonify
from tools.gemma import handle_prompt

app = Flask(__name__)

@app.route("/generate", methods=["POST"])
def generate():
    data = request.json or {}
    prompt = data.get("prompt", "").strip()
    print(f"[manager] got prompt: {prompt!r}", flush=True)

    try:
        response_text = handle_prompt(prompt)
    except Exception as e:
        print(f"[manager] error calling Gemma: {e}", flush=True)
        return jsonify({"error": str(e)}), 500

    print(f"[manager] sending response: {response_text!r}", flush=True)
    return jsonify({"response": response_text})

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)

