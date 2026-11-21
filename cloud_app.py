import os
import json
import hmac
import threading
from datetime import datetime
from types import SimpleNamespace

from flask import Flask, request, jsonify, render_template, abort, redirect

app = Flask(__name__)

API_KEY = os.environ.get("REGISTRYWATCH_API_KEY")

DATA_DIR = "data"
EVENT_FILE = os.path.join(DATA_DIR, "cloud_events.jsonl")

os.makedirs(DATA_DIR, exist_ok=True)

lock = threading.Lock()

# Agent control state
monitoring_command = "stop"
agent_running = False
last_scan = None
baseline_exists = False


def authenticate_agent():
    if not API_KEY:
        abort(503)

    supplied_key = request.headers.get("X-API-Key", "")

    if not hmac.compare_digest(supplied_key, API_KEY):
        abort(401)


def load_events(limit=100):
    if not os.path.exists(EVENT_FILE):
        return []

    result = []

    with lock:
        with open(EVENT_FILE, encoding="utf-8") as file:
            for line in file:
                try:
                    result.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

    return list(reversed(result[-limit:]))


def event_count():
    if not os.path.exists(EVENT_FILE):
        return 0

    with lock:
        with open(EVENT_FILE, encoding="utf-8") as file:
            return sum(1 for line in file if line.strip())


@app.route("/")
def home():
    status = SimpleNamespace(
        running=agent_running,
        baseline_exists=baseline_exists,
        locations=5,
        event_count=event_count(),
        last_scan=last_scan,
        last_error=None
    )

    return render_template(
        "dashboard.html",
        status=status,
        events=load_events()
    )


@app.route("/start", methods=["POST"])
def start_monitoring():
    global monitoring_command

    monitoring_command = "start"

    return redirect("/")


@app.route("/stop", methods=["POST"])
def stop_monitoring():
    global monitoring_command

    monitoring_command = "stop"

    return redirect("/")


@app.route("/api/agent/command", methods=["GET"])
def agent_command():
    authenticate_agent()

    return jsonify({
        "command": monitoring_command
    })


@app.route("/api/agent/status", methods=["POST"])
def agent_status():
    global agent_running, last_scan, baseline_exists

    authenticate_agent()

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "Invalid JSON"}), 400

    agent_running = bool(data.get("running", False))
    last_scan = data.get("last_scan")
    baseline_exists = bool(data.get("baseline_exists", False))

    return jsonify({"message": "Status updated"})


@app.route("/api/ingest", methods=["POST"])
def ingest():
    authenticate_agent()

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "Invalid JSON"}), 400

    data["received_at"] = datetime.now().astimezone().isoformat()

    with lock:
        with open(EVENT_FILE, "a", encoding="utf-8") as file:
            file.write(json.dumps(data) + "\n")

    return jsonify({"message": "Event received"}), 201


@app.route("/api/status")
def api_status():
    return jsonify({
        "platform": "Cloud",
        "event_count": event_count(),
        "monitoring": "Windows agent",
        "agent_running": agent_running,
        "command": monitoring_command
    })


@app.route("/api/events")
def api_events():
    return jsonify(load_events())


print(app.url_map)


if __name__ == "__main__":
    app.run(port=7000, debug=False)