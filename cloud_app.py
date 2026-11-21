import os
import json
import hmac
import threading
from datetime import datetime
from types import SimpleNamespace
from flask import Flask, request, jsonify, render_template, abort

app = Flask(__name__)

API_KEY = os.environ.get("REGISTRYWATCH_API_KEY")

DATA_DIR = "data"
EVENT_FILE = os.path.join(DATA_DIR, "cloud_events.jsonl")

os.makedirs(DATA_DIR, exist_ok=True)

lock = threading.Lock()


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


@app.route("/")
def home():
    recent_events = load_events()

    status = SimpleNamespace(
        running=False,
        baseline_exists=False,
        locations=5,
        event_count=len(load_events(100000)),
        last_scan=None,
        last_error=None
    )

    return render_template(
        "dashboard.html",
        status=status,
        events=recent_events
    )


@app.route("/api/ingest", methods=["POST"])
def ingest():
    if not API_KEY:
        return jsonify({"error": "Server API key not configured"}), 503

    supplied_key = request.headers.get("X-API-Key", "")

    if not hmac.compare_digest(supplied_key, API_KEY):
        abort(401)

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
        "event_count": len(load_events(100000)),
        "monitoring": "Windows agent"
    })


@app.route("/api/events")
def api_events():
    return jsonify(load_events())


if __name__ == "__main__":
    print(app.url_map)
    app.run(port=7000, debug=False)