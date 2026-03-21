# Base: Official Fedora image from AWS Public ECR
FROM public.ecr.aws/docker/library/fedora:43

ENV OPENCODE_PORT=5000

# === Install useful Linux utilities + sudo ===
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

# === Create dev user ===
RUN useradd -m -s /bin/bash dev && \
    echo "dev ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers.d/dev && \
    mkdir -p /home/dev && \
    chmod 755 /home/dev

# === Switch to dev user ===
USER dev
ENV HOME=/home/dev \
    PATH="/home/dev/.opencode/bin:${PATH}"

# === Install opencode ===
RUN curl -fsSL https://opencode.ai/install | bash

# === Install Flask ===
RUN pip3 install flask

# === Write configure.py (Flask setup app - auto-exits after config) ===
RUN cat > /home/dev/configure.py <<'SCRIPT'
#!/usr/bin/env python3
import os, json, time, threading
from flask import Flask, request, render_template_string, jsonify

app = Flask(__name__)
CONFIG = "/home/dev/.config/opencode/opencode.json"
HTML = """<!DOCTYPE html><html><head><title>OpenCode Setup</title>
<style>body{font-family:system-ui,max-width:600px;margin:50px auto;padding:20px}
label{display:block;margin:15px 0 5px;font-weight:600}
input{width:100%;padding:10px;border:1px solid #ccc;border-radius:4px;font-size:14px}
button{margin:20px 0 0;padding:12px 24px;background:#0a84ff;color:#fff;border:none;border-radius:6px;cursor:pointer;font-size:16px}
#status{margin:20px 0;padding:12px;border-radius:4px;display:none}
.error{background:#ffdce0;color:#b00020}
.success{background:#d6f2d0;color:#006e00}</style></head><body>
<h1>OpenCode Setup</h1><form id="f">
<label>Base URL (e.g., http://127.0.0.1:8000/v1)</label>
<input id="u" name="baseURL" required placeholder="http://127.0.0.1:8000/v1">
<label>Model Name</label>
<input id="n" name="modelName" value="Qwen/Qwen3.5-35B-A3B-FP8" required>
<label>Display Name</label>
<input id="d" name="modelNameDisplay" value="Qwen3.5-35B-A3B (local)">
<label>Context Limit</label><input type="number" id="c" name="contextLimit" value="262144">
<label>Input Limit</label><input type="number" id="i" name="inputLimit" value="262144">
<label>Output Limit</label><input type="number" id="o" name="outputLimit" value="32768">
<button type="submit">Configure & Start</button></form><div id="s"></div>
<script>
document.getElementById("f").onsubmit=async e=>{
e.preventDefault();var d=document.getElementById("s");d.style.display="block";d.className="";d.textContent="Testing...";
const c={baseURL:document.getElementById("u").value,modelName:document.getElementById("n").value,
modelNameDisplay:document.getElementById("d").value,contextLimit:parseInt(document.getElementById("c").value),
inputLimit:parseInt(document.getElementById("i").value),outputLimit:parseInt(document.getElementById("o").value)};
fetch("/save",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(c)})
.then(r=>r.json()).then(j=>{if(j.success){d.className="success";d.textContent="✓ Success! OpenCode is starting...";}
else{d.className="error";d.textContent="✗ "+j.error}})
};
</script></body></html>"""

def mk_config(data):
    return{
        "$schema":"https://opencode.ai/config.json",
        "provider":{
            "local_inference":{
                "npm":"@ai-sdk/openai-compatible",
                "name":"llama-server",
                "options":{"baseURL":data["baseURL"]},
                "models":{
                    data["modelName"]:{
                        'name':data["modelNameDisplay"],
                        "limit":{"context":data["contextLimit"],"input":data["inputLimit"],"output":data["outputLimit"]},
                        "modalities":{"input":["text"],"output":["text"]},
                        "cost":{"input":0,"output":0}
                    }
                }
            }
        },
        "model":"local_inference/"+data["modelName"]
    }

@app.route("/")
def idx():return render_template_string(HTML)

@app.route("/save",methods=["POST"])
def save():
    try:
        cfg=mk_config(request.json)
        os.makedirs(os.path.dirname(CONFIG),exist_ok=True)
        with open(CONFIG,"w") as f:json.dump(cfg,f,indent=2)
        
        # Auto-exit Flask after successful save (gives browser time to show success)
        def shutdown():
            time.sleep(1.5)
            os._exit(0)
        threading.Thread(target=shutdown, daemon=True).start()
        
        return jsonify({"success":True})
    except Exception as e:return jsonify({"success":False,"error":str(e)})

if __name__=="__main__":
    os.makedirs(os.path.dirname(CONFIG),exist_ok=True)
    app.run(host="0.0.0.0",port=int(os.environ.get("OPENCODE_PORT",5000)),debug=False)
SCRIPT

# === Write startup script ===
RUN cat > /home/dev/start-opencode <<'SCRIPT'
#!/bin/bash
set -e
CONFIG="/home/dev/.config/opencode/opencode.json"

if [ -f "$CONFIG" ]; then
    echo "=== Config exists, skipping setup ==="
    opencode upgrade || true
    exec opencode web --port "${OPENCODE_PORT}" --hostname 0.0.0.0
fi

echo "=== Starting setup wizard (will auto-exit after you configure) ==="
python3 /home/dev/configure.py

echo "=== Config received - starting OpenCode ==="

# Smart wait: poll until port is actually free (usually <1s, never too short)
echo "=== Waiting for setup server to release port ${OPENCODE_PORT}... ==="
for i in {1..15}; do
    if ! curl -s --connect-timeout 0.3 --max-time 0.6 http://127.0.0.1:${OPENCODE_PORT} >/dev/null 2>&1; then
        echo "✓ Port released"
        break
    fi
    sleep 0.35
done

echo "=== Validating config ==="
opencode debug config > /dev/null 2>&1 || { echo "✗ Config validation failed"; exit 1; }

opencode upgrade || true
exec opencode web --port "${OPENCODE_PORT}" --hostname 0.0.0.0
SCRIPT

RUN chmod +x /home/dev/configure.py /home/dev/start-opencode

ENV HOME=/home/dev \
    OPENCODE_PORT=${OPENCODE_PORT} \
    PATH="/home/dev/.opencode/bin:${PATH}"

EXPOSE ${OPENCODE_PORT}

CMD ["/home/dev/start-opencode"]