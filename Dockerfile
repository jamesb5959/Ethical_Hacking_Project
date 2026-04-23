FROM nvidia/cuda:11.8.0-devel-ubuntu20.04

ARG TARGETARCH

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      python3-venv python3-pip python3-dev \
      ca-certificates nmap git && \
    rm -rf /var/lib/apt/lists/*

RUN git clone --depth 1 https://gitlab.com/exploit-database/exploitdb.git /opt/exploitdb && \
    ln -sf /opt/exploitdb/searchsploit /usr/local/bin/searchsploit

ENV HF_HOME=/root/.cache/huggingface
ENV PATH="/app/venv/bin:${PATH}"

WORKDIR /app

COPY requirements.txt .
RUN python3 -m venv ./venv && \
    ./venv/bin/pip install --upgrade pip && \
    if [ "$TARGETARCH" = "amd64" ]; then \
      ./venv/bin/pip install --extra-index-url https://download.pytorch.org/whl/cu118 torch==2.0.1+cu118; \
    else \
      ./venv/bin/pip install torch; \
    fi && \
    ./venv/bin/pip install -r requirements.txt

COPY manager.py .
COPY config/ ./config/
COPY tools/ ./tools/
COPY weaviate/ ./weaviate/

EXPOSE 5000
CMD ["python", "manager.py"]
