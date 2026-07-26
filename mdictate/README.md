# mdictate

LAN browser speech-to-text for k3s.

Hold a button (or Space) to record → Flask proxies audio to a **whisper.cpp** server → text is appended in the buffer and copied to the clipboard.

**whisper.cpp is not deployed in Kubernetes.** Run it manually on a GPU host (same node or another machine on the LAN).

## Architecture

```
Phone / laptop on LAN
        │  mic → 16 kHz mono WAV
        │  https://<k3s-node-ip>:<NodePort>/
        ▼
mdictate pod (Flask, HTTPS)  ──proxies──▶  whisper.cpp (:8025, manual)
        │
        ▼
JSON { text }  →  UI buffer + clipboard
```

The whisper.cpp address is set in the web UI (and pre-filled via `DEFAULT_WHISPER_URL` at deploy time). Flask proxies so the browser does not need CORS access to whisper.

## Requirements

**k3s node (UI):**
- k3s, docker/podman (for `build_and_deploy_k3s.sh`)
- Run deploy as root (same pattern as `scratchpad/`)

**whisper host (STT):**
- NVIDIA GPU + driver (`nvidia-smi`)
- Build tools for whisper.cpp (cmake, cuda toolkit, etc.)

## 1. Start whisper.cpp (manual)

On the GPU machine:

```bash
./whisper/start_whisper_cuda.sh
```

First run clones [whisper.cpp](https://github.com/ggml-org/whisper.cpp), builds with CUDA, downloads `large-v3-turbo-q8_0`, and listens on `0.0.0.0:8025` with path `/v1/audio/transcriptions`.

Later runs reuse the existing build under `whisper/whisper.cpp/`.

Confirm it is reachable from the k3s node (if whisper is on another host, use that host’s LAN IP):

```bash
curl -sS -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8025/
```

## 2. Deploy mdictate on k3s

On the k3s server, as root:

```bash
cd mdictate
./build_and_deploy_k3s.sh
```

This builds the image, imports it into k3s containerd, and applies the Deployment + NodePort Service in namespace `mdictate`.

Optional: set the default whisper URL baked into the pod (also overridable in the UI):

```bash
default_whisper_url=http://10.12.0.51:8025 ./build_and_deploy_k3s.sh
```

If unset, the script picks the node’s first non-loopback IPv4 and uses `http://<that-ip>:8025`.

After deploy, the script prints the NodePort. Open:

```text
https://<k3s-node-ip>:<NodePort>/
```

Accept the self-signed certificate warning once (**Advanced → Proceed**). Browsers only allow the microphone on HTTPS (or localhost). Use the **https** URL (not `http://`).

## Usage

1. Open the HTTPS NodePort URL on a phone or laptop on the LAN.
2. Confirm **// whisper host** points at a reachable whisper.cpp (e.g. `http://10.12.0.51:8025`) and click **SET**.
3. Hold **REC / HOLD** or hold **Space**, speak, release.
4. Text is **appended** to the buffer (blank line between recordings) and the full buffer is copied when possible.
5. **[ COPY ALL ]** / **[ CLEAR ]** as needed.

## Why HTTPS?

Chrome and other browsers only expose `getUserMedia` in a **secure context**. On a LAN IP that means `https://…`. Plain HTTP on a NodePort IP fails with `mediaDevices` undefined. The container serves HTTPS with a self-signed cert by default (`STT_SSL=1`).

## Environment (container)

| Variable              | Default                   | Meaning                                      |
|-----------------------|---------------------------|----------------------------------------------|
| `STT_HOST`            | `0.0.0.0`           | Bind address                                   |
| `STT_PORT`            | `5000`              | HTTPS listen port (Service port name: `https`) |
| `STT_SSL`             | `1`                 | HTTPS; set `0` for plain HTTP                  |
| `DEFAULT_WHISPER_URL` | set at deploy       | UI default whisper base URL                    |
| `WHISPER_MODEL`       | `whisper-large-v3`  | Model name sent to whisper.cpp                 |
| `STT_LOG_HEARD`       | `0`                 | Log transcript text; set `1` to enable         |

## API

### `POST /api/transcribe`

Multipart form: `file` (audio), optional `whisper_url`, `model`, `language`.

### `GET /api/health`

```json
{ "ok": true, "ssl": true }
```

## Layout

```
mdictate/
├── README.md
├── build_and_deploy_k3s.sh   # build image → k3s import → apply
├── docker/
│   ├── Dockerfile
│   └── code/
│       ├── app.py
│       ├── requirements.txt
│       └── templates/
│           └── index.html
├── k3s/
│   └── deploy.yaml
└── whisper/
    └── start_whisper_cuda.sh # manual whisper.cpp (not in k8s)
```

## Notes

- Pod network cannot use the host’s `localhost` for whisper; use a LAN/host IP in the UI or `default_whisper_url`.
- whisper must listen on `0.0.0.0` (the start script does) if clients or pods reach it by host IP.
- Newlines inside a single whisper response are collapsed to spaces; blank lines between separate recordings are intentional.
