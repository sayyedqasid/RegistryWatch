from flask import Flask, render_template, jsonify, redirect
from registry_monitor import status, events, start, stop

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("dashboard.html", status=status(), events=events())

@app.route("/api/status")
def api_status():
    return jsonify(status())

@app.route("/api/events")
def api_events():
    return jsonify(events())

@app.route("/start", methods=["POST"])
def start_route():
    start()
    return redirect("/")

@app.route("/stop", methods=["POST"])
def stop_route():
    stop()
    return redirect("/")

if __name__ == "__main__":
    print("Open http://127.0.0.1:7000")
    app.run(host="127.0.0.1", port=7000, debug=False)
