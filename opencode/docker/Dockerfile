# Base: Official Fedora image from AWS Public ECR
FROM public.ecr.aws/docker/library/fedora:43

ENV OPENCODE_PORT=5000

# === Install useful Linux utilities + sudo (for the sudoers rule you have) ===
RUN dnf install -y \
    git \
    curl \
    wget \
    unzip \
    ca-certificates \
    sudo \
    gcc \
    gcc-c++ \
    make \
    python3 \
    python3-pip \
    nodejs \
    npm \
    jq \
    && dnf clean all

# === Startup script: update OpenCode + launch web UI ===
COPY <<'EOSTART' /usr/local/bin/start-opencode
#!/bin/bash
set -e

echo "=== Updating OpenCode to latest version ==="
opencode upgrade || true

echo "=== Starting OpenCode Web UI on port ${OPENCODE_PORT} ==="
exec opencode web \
  --port "${OPENCODE_PORT}" \
  --hostname 0.0.0.0
EOSTART

RUN chmod +x /usr/local/bin/start-opencode

# Create non-root user
RUN useradd -m -s /bin/bash dev && \
    echo "dev ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers.d/dev

USER dev
WORKDIR /workspace

# Make sure OpenCode binary will be in PATH
ENV HOME=/home/dev \
    PATH="/home/dev/.opencode/bin:${PATH}"

# === Install OpenCode ===
RUN curl -fsSL https://opencode.ai/install | bash

# === Add opencode.json configuration file (FIXED with absolute path) ===
RUN mkdir -p /home/dev/.config/opencode
COPY <<'EOF' /home/dev/.config/opencode/opencode.json
{
  "$schema": "https://opencode.ai/config.json",
  "provider": {
    "llama.cpp": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "llama-server (local)",
      "options": {
        "baseURL": "http://10.12.0.57:8080/v1"
      },
      "models": {
        "unsloth/Qwen3.5-35B-A3B-GGUF:Q8_0": {
          "name": "Qwen3.5-35B-A3B (local) + Vision",
          "limit": {
            "context": 262144,
            "input": 262144,
            "output": 32768
          },
          "modalities": {
            "input": ["text", "image"],
            "output": ["text"]
          },
          "cost": {
            "input": 0,
            "output": 0
          }
        }
      }
    }
  },
  "model": "llama.cpp/Qwen3.5-35B-A3B"
}
EOF

EXPOSE ${OPENCODE_PORT}

CMD ["/usr/local/bin/start-opencode"]