FROM nvidia/cuda:11.8.0-devel-ubuntu20.04

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      python3-venv python3-pip python3-dev \
      nmap exploitdb git && \
    rm -rf /var/lib/apt/lists/*

# setup huggingface token
ARG HF_TOKEN
RUN pip3 install --upgrade pip && \
    pip3 install huggingface_hub && \
    mkdir -p /root/.huggingface && \
    echo "$HF_TOKEN" > /root/.huggingface/token

ENV HF_HOME=/root/.cache/huggingface/token
WORKDIR /app
COPY requirements.txt .
RUN python3 -m venv ./venv && \
    ./venv/bin/pip install -r requirements.txt

COPY manager.py .
COPY gemma.py .
COPY inference.py .
COPY nmap.py .

EXPOSE 5000
CMD ["bash", "-c", "echo 'nvidia-smi check:' && nvidia-smi && echo 'launching manager.py' && ./venv/bin/python manager.py"]

