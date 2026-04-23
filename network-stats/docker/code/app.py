import os
import time
import subprocess
import json
import threading
from datetime import datetime
from flask import Flask, render_template, jsonify, request

app = Flask(__name__)
DATA_FILE = "/app/data/ping_data.json"
PING_TARGET = "1.1.1.1"
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

    now = datetime.now()
    windows = {
        "5m": 5 * 60,
        "15m": 15 * 60,
        "30m": 30 * 60,
        "1h": 60 * 60,
        "2h": 2 * 60 * 60,
    }

    def calc_stats(window_data):
        if not window_data:
            return {"count": 0, "packet_loss": None, "avg_ms": None, "min_ms": None, "max_ms": None}
        successful = [d for d in window_data if d.get("success")]
        failed = [d for d in window_data if not d.get("success")]
        if successful:
            return {
                "count": len(window_data),
                "packet_loss": round(len(failed) / len(window_data) * 100, 1),
                "avg_ms": round(sum(d["avg_ms"] for d in successful) / len(successful), 2),
                "min_ms": round(min(d["min_ms"] for d in successful), 2),
                "max_ms": round(max(d["max_ms"] for d in successful), 2),
            }
        return {
            "count": len(window_data),
            "packet_loss": 100.0,
            "avg_ms": None,
            "min_ms": None,
            "max_ms": None,
        }

    windows_stats = {}
    for name, seconds in windows.items():
        cutoff = now.timestamp() - seconds
        cutoff_dt = datetime.fromtimestamp(cutoff)
        window_data = [d for d in data if datetime.fromisoformat(d["timestamp"].replace("Z", "+00:00").replace("+00:00", "")) >= cutoff_dt]
        windows_stats[name] = calc_stats(window_data)

    return jsonify({
        "windows": windows_stats,
        "recent": data[-20:],
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
