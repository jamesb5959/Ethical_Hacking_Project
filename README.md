# Ethical_Hacking_Project

## Repository Structure

```
├── config/
│   └── sys_msg.txt         # System prompt for Sydney
├── src/
│   └── main.rs             # Rust terminal UI
├── tools/
│   ├── nmap.py             # Nmap tool
│   ├── searchsploit.py     # SearchSploit tool
│   ├── gemma.py            # Sydney agent implementation
│   └── inference.py        # Response-generation helper
├── weaviate/
│   └── memory.py           # Local Weaviate memory helper
├── manager.py              # Flask API server (entrypoint)
├── requirements.txt        # Python dependencies
├── Dockerfile              # Container build instructions
├── install.sh              # Builds Docker image
├── start.sh                # Runs container
└── download_gemma.sh       # Downloads Gemma model into models/
```

## Installation

1. **Download Sydney's Gemma model**

   Sydney uses the gated Gemma model from Hugging Face. Accept access to `google/gemma-2-2b`, create a read token, then run:

   ```bash
   HF_TOKEN="your_hugging_face_token" ./download_gemma.sh
   ```

2. **Run install script**

   ```bash
   ./install.sh
   ```

3. **Run the container**

   ```bash
   HF_TOKEN="your_hugging_face_token" ./start.sh
   ```

   This also starts a local Weaviate container for Sydney's memory.

4. **Run the Rust terminal UI**

   ```bash
   cargo run --manifest-path Cargo.toml
   ```

   TUI controls:

   * `i` - type a prompt
   * `s` - save the latest response to Weaviate
   * `u` - upload a text file path to Weaviate
   * `q` - quit

## Mac Support

The Dockerfile supports Mac builds by avoiding the missing `exploitdb` apt package and installing SearchSploit from the Exploit-DB git repository instead.

On Mac, Docker runs CPU-only. Linux/WSL systems with NVIDIA support can still use GPU runtime support through `start.sh`.

## Configuration

* **System Prompt**: Modify `config/sys_msg.txt` to update tool descriptions and behavior.
* Sydney’s Flask API will be available on `http://localhost:5000`.
* Weaviate will be available on `http://localhost:8080`.
* **Environment Variables**:

  * `HF_TOKEN` - Hugging Face access token used to download and run Sydney's Gemma model.
  * `HUGGING_FACE_HUB_TOKEN` - Alternative Hugging Face token variable.
  * `PORT` - Optional host port override for `start.sh`.
  * `WEAVIATE_PORT` - Optional Weaviate host port override.
  * `WEAVIATE_ENABLED` - Set to `0` to skip memory retrieval.
  * `GEMMA_API_URL` - Optional API URL override for the Rust UI.
