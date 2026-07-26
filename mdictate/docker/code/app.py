#!/usr/bin/env python3
"""
mdictate — LAN speech-to-text web UI.
Browser records audio, Flask proxies to a whisper.cpp server, returns text.

Serves HTTPS by default with a self-signed cert so Chrome/Firefox expose
getUserMedia on http(s)://LAN-IP addresses (secure context required).
"""

import os
import socket
import subprocess
import tempfile
from urllib.parse import urlparse

import requests
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

DEFAULT_WHISPER_URL = os.environ.get(
    "DEFAULT_WHISPER_URL", "http://localhost:8025"
).strip() or "http://localhost:8025"
WHISPER_MODEL = os.environ.get("WHISPER_MODEL", "whisper-large-v3").strip() or "whisper-large-v3"
HOST = os.environ.get("STT_HOST", "0.0.0.0")
PORT = int(os.environ.get("STT_PORT", "5000"))

# HTTPS on by default for local-network mic access. Set STT_SSL=0 for plain HTTP.
_ssl_env = os.environ.get("STT_SSL", "1").strip().lower()
SSL_ENABLED = _ssl_env not in ("0", "false", "no", "off")

# Log full transcript text. Off by default (can be noisy / sensitive).
# Enable with: STT_LOG_HEARD=1
_log_heard_env = os.environ.get("STT_LOG_HEARD", "0").strip().lower()
LOG_HEARD = _log_heard_env in ("1", "true", "yes", "on")


def _normalize_whisper_url(raw: str) -> str:
    """Accept host:port or full URL; always return scheme + host (+ port)."""
    u = (raw or "").strip()
    if not u:
        u = DEFAULT_WHISPER_URL
    if not u.startswith(("http://", "https://")):
        u = "http://" + u
    return u.rstrip("/")


def _whisper_url_ok(url: str) -> bool:
    try:
        p = urlparse(url)
        return p.scheme in ("http", "https") and bool(p.netloc)
    except Exception:
        return False


def _normalize_transcript(text: str) -> str:
    """Collapse whisper.cpp sentence/segment newlines into a single paragraph."""
    if not text:
        return ""
    t = text.replace("\r\n", "\n").replace("\r", "\n")
    t = " ".join(t.split())  # all whitespace (incl. newlines) → single spaces
    return t.strip()


def _lan_ipv4_addrs():
    """Best-effort list of non-loopback IPv4 addresses on this host."""
    addrs = set()
    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
            ip = info[4][0]
            if not ip.startswith("127."):
                addrs.add(ip)
    except Exception:
        pass
    # Also probe via UDP connect (does not send packets) for the preferred outbound IP
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        if ip and not ip.startswith("127."):
            addrs.add(ip)
    except Exception:
        pass
    return sorted(addrs)


@app.route("/")
def index():
    return render_template(
        "index.html",
        default_whisper_url=DEFAULT_WHISPER_URL,
    )


@app.route("/api/transcribe", methods=["POST"])
def transcribe():
    """
    Accept audio file + optional whisper_url, forward to whisper.cpp
    OpenAI-compatible /v1/audio/transcriptions endpoint.
    """
    if "file" not in request.files and "audio" not in request.files:
        return jsonify({"error": "No audio file provided (field: file or audio)"}), 400

    audio = request.files.get("file") or request.files.get("audio")
    if not audio or not audio.filename:
        return jsonify({"error": "Empty audio upload"}), 400

    whisper_url = _normalize_whisper_url(
        request.form.get("whisper_url")
        or request.args.get("whisper_url")
        or DEFAULT_WHISPER_URL
    )
    if not _whisper_url_ok(whisper_url):
        return jsonify({"error": f"Invalid whisper URL: {whisper_url}"}), 400

    model = (request.form.get("model") or WHISPER_MODEL).strip() or WHISPER_MODEL
    language = (request.form.get("language") or "en").strip() or "en"

    suffix = os.path.splitext(audio.filename)[1] or ".wav"
    if len(suffix) > 8:
        suffix = ".wav"

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp_path = tmp.name
            audio.save(tmp_path)

        endpoint = f"{whisper_url}/v1/audio/transcriptions"
        print(f"📤 Transcribing via {endpoint} (model={model})...")

        with open(tmp_path, "rb") as f:
            files = {"file": (os.path.basename(tmp_path), f, "application/octet-stream")}
            data = {
                "model": model,
                "language": language,
                "temperature": "0.0",
                "response_format": "json",
            }
            r = requests.post(endpoint, files=files, data=data, timeout=120)

        if r.status_code != 200:
            detail = (r.text or "")[:300]
            print(f"Whisper {r.status_code}: {detail}")
            return jsonify({
                "error": f"whisper.cpp returned {r.status_code}",
                "detail": detail,
                "whisper_url": whisper_url,
            }), 502

        payload = r.json() if r.content else {}
        text = _normalize_transcript(payload.get("text") or "")
        if LOG_HEARD:
            print(f"🗣️  Heard: {text[:120]}{'...' if len(text) > 120 else ''}")
        # else: keep quiet by default — re-enable with STT_LOG_HEARD=1
        return jsonify({
            "text": text,
            "whisper_url": whisper_url,
        })
    except requests.exceptions.ConnectionError as e:
        print("STT connection error:", e)
        return jsonify({
            "error": f"Could not reach whisper.cpp at {whisper_url}",
            "detail": str(e),
        }), 502
    except requests.exceptions.Timeout:
        return jsonify({"error": "whisper.cpp request timed out"}), 504
    except Exception as e:
        print("STT error:", e)
        return jsonify({"error": str(e)}), 500
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass


@app.route("/api/health")
def health():
    return jsonify({"ok": True, "ssl": SSL_ENABLED})


def _write_openssl_config(path: str, lan_ips: list) -> None:
    """openssl.cnf with SAN for localhost + LAN IPs (needed for modern browsers)."""
    alt = [
        "DNS:localhost",
        "DNS:*.localhost",
        "IP:127.0.0.1",
        "IP:0:0:0:0:0:0:0:1",
    ]
    for ip in lan_ips:
        alt.append(f"IP:{ip}")
    alt_str = ", ".join(alt)
    content = f"""[req]
default_bits = 2048
prompt = no
default_md = sha256
distinguished_name = dn
x509_extensions = v3_req

[dn]
CN = mdictate
O = localdev

[v3_req]
subjectAltName = {alt_str}
basicConstraints = CA:FALSE
keyUsage = digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth
"""
    with open(path, "w") as f:
        f.write(content)


def _ssl_context():
    """Self-signed cert for LAN mic access, or None for plain HTTP."""
    if not SSL_ENABLED:
        return None

    cert_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".ssl")
    cert_file = os.path.join(cert_dir, "cert.pem")
    key_file = os.path.join(cert_dir, "key.pem")
    conf_file = os.path.join(cert_dir, "openssl.cnf")
    lan_ips = _lan_ipv4_addrs()

    need_new = not (os.path.isfile(cert_file) and os.path.isfile(key_file))
    # If cert exists but LAN IPs changed, regenerate so SANs stay valid.
    ips_stamp = os.path.join(cert_dir, "lan_ips.txt")
    ips_blob = "\n".join(lan_ips)
    if not need_new and os.path.isfile(ips_stamp):
        try:
            with open(ips_stamp) as f:
                if f.read().strip() != ips_blob:
                    need_new = True
                    print("🔐 LAN IPs changed — regenerating TLS cert SANs")
        except Exception:
            pass
    elif not need_new and lan_ips:
        need_new = True

    if need_new:
        os.makedirs(cert_dir, exist_ok=True)
        _write_openssl_config(conf_file, lan_ips)
        try:
            subprocess.run(
                [
                    "openssl", "req", "-x509", "-newkey", "rsa:2048",
                    "-keyout", key_file, "-out", cert_file,
                    "-days", "3650", "-nodes",
                    "-config", conf_file,
                    "-extensions", "v3_req",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            with open(ips_stamp, "w") as f:
                f.write(ips_blob)
            print(f"🔐 Created self-signed cert in {cert_dir}")
            if lan_ips:
                print(f"   SANs include LAN IP(s): {', '.join(lan_ips)}")
        except FileNotFoundError:
            print("⚠️  openssl not found — trying Flask adhoc SSL")
            return "adhoc"
        except subprocess.CalledProcessError as e:
            print("⚠️  openssl cert generation failed, trying Flask adhoc SSL")
            if e.stderr:
                print("   ", e.stderr.strip()[:200])
            return "adhoc"

    return (cert_file, key_file)


def _print_urls(scheme: str) -> None:
    print(f"🎤 mdictate web UI ({scheme.upper()})")
    print(f"   Local:   {scheme}://127.0.0.1:{PORT}/")
    for ip in _lan_ipv4_addrs():
        print(f"   LAN:     {scheme}://{ip}:{PORT}/")
    if scheme == "https":
        print("   First visit: accept the self-signed certificate warning (Advanced → Proceed)")
        print("   Mic requires HTTPS on LAN IPs (or use localhost over HTTP with STT_SSL=0)")
    else:
        print("   Plain HTTP: mic only works on localhost/127.0.0.1 (not raw LAN IPs)")
    print(f"   Default whisper.cpp: {DEFAULT_WHISPER_URL}")
    print("   (whisper is external — set URL in the UI if not reachable at the default)")


if __name__ == "__main__":
    ssl_ctx = _ssl_context()
    scheme = "https" if ssl_ctx else "http"
    _print_urls(scheme)
    app.run(host=HOST, port=PORT, debug=False, ssl_context=ssl_ctx)
