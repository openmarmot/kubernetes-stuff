import os
import time
import subprocess
import json
import threading
from datetime import datetime
from flask import Flask, render_template, jsonify, request

app = Flask(__name__)
DATA_FILE = "/app/data/ping_data.json"
PING_TARGET = "8.8.8.8"
PING_INTERVAL = 300
PING_COUNT = 4


def ensure_data_file():
    if not os.path.exists(DATA_FILE):
        os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
        with open(DATA_FILE, "w") as f:
            json.dump([], f)


def load_ping_data():
    ensure_data_file()
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return []


def save_ping_data(data):
    ensure_data_file()
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)


def run_ping():
    try:
        result = subprocess.run(
            ["ping", "-c", str(PING_COUNT), "-W", "5", PING_TARGET],
            capture_output=True,
            text=True,
            timeout=10
        )
        output = result.stdout

        stats_line = [line for line in output.split("\n") if "min/avg/max" in line]
        if stats_line:
            stats = stats_line[0].split("=")[1].strip().split("/")
            min_ms = float(stats[0])
            avg_ms = float(stats[1])
            max_ms = float(stats[2])
            return {
                "timestamp": datetime.now().isoformat(),
                "target": PING_TARGET,
                "min_ms": min_ms,
                "avg_ms": avg_ms,
                "max_ms": max_ms,
                "success": True,
                "packets_sent": PING_COUNT,
                "packets_received": PING_COUNT if result.returncode == 0 else 0
            }
    except Exception:
        pass

    return {
        "timestamp": datetime.now().isoformat(),
        "target": PING_TARGET,
        "success": False,
        "packets_sent": PING_COUNT,
        "packets_received": 0
    }


def ping_worker():
    while True:
        data = run_ping()
        all_data = load_ping_data()
        all_data.append(data)
        all_data = all_data[-1000:]
        save_ping_data(all_data)
        time.sleep(PING_INTERVAL)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/stats")
def stats():
    data = load_ping_data()
    if not data:
        return jsonify({"message": "No ping data available yet", "data": []})

    successful = [d for d in data if d.get("success")]
    failed = [d for d in data if not d.get("success")]

    if successful:
        avg_ms = sum(d["avg_ms"] for d in successful) / len(successful)
        min_ms = min(d["min_ms"] for d in successful)
        max_ms = max(d["max_ms"] for d in successful)
        packet_loss = (len(failed) / len(data)) * 100 if data else 0
    else:
        avg_ms = min_ms = max_ms = 0
        packet_loss = 100 if data else 0

    return jsonify({
        "summary": {
            "total_checks": len(data),
            "successful": len(successful),
            "failed": len(failed),
            "packet_loss_percent": round(packet_loss, 2),
            "avg_latency_ms": round(avg_ms, 2),
            "min_latency_ms": round(min_ms, 2),
            "max_latency_ms": round(max_ms, 2)
        },
        "data": data[-100:]
    })


@app.route("/api/ping_now", methods=["POST"])
def ping_now():
    data = run_ping()
    all_data = load_ping_data()
    all_data.append(data)
    save_ping_data(all_data)
    return jsonify(data)


if __name__ == "__main__":
    threading.Thread(target=ping_worker, daemon=True).start()
    app.run(host="0.0.0.0", port=5000, debug=False)