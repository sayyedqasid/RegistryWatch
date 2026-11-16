"""Read-only monitor for selected Windows Registry startup locations."""
import json, os, platform, threading, time
from datetime import datetime

try:
    import winreg
except ImportError:
    winreg = None

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, "data")
LOGS = os.path.join(ROOT, "logs")
BASELINE = os.path.join(DATA, "baseline.json")
EVENT_LOG = os.path.join(LOGS, "events.jsonl")
os.makedirs(DATA, exist_ok=True)
os.makedirs(LOGS, exist_ok=True)

LOCATIONS = [
    ("HKCU", r"Software\\Microsoft\\Windows\\CurrentVersion\\Run"),
    ("HKCU", r"Software\\Microsoft\\Windows\\CurrentVersion\\RunOnce"),
    ("HKLM", r"Software\\Microsoft\\Windows\\CurrentVersion\\Run"),
    ("HKLM", r"Software\\Microsoft\\Windows\\CurrentVersion\\RunOnce"),
    ("HKLM", r"Software\\Microsoft\\Windows NT\\CurrentVersion\\Winlogon"),
]
running = False
worker = None
stop_event = threading.Event()
last_scan = None
last_error = None

def now():
    return datetime.now().astimezone().isoformat(timespec="seconds")

def read_key(root_name, path):
    if winreg is None:
        raise RuntimeError("RegistryWatch works on Windows only.")
    root = winreg.HKEY_CURRENT_USER if root_name == "HKCU" else winreg.HKEY_LOCAL_MACHINE
    result = {}
    try:
        with winreg.OpenKey(root, path, 0, winreg.KEY_READ) as key:
            i = 0
            while True:
                try:
                    name, value, kind = winreg.EnumValue(key, i)
                    result[name] = {"data": str(value), "type": int(kind)}
                    i += 1
                except OSError:
                    break
    except FileNotFoundError:
        result["__status__"] = "not found"
    except PermissionError:
        result["__status__"] = "access denied"
    except OSError as exc:
        result["__status__"] = "read error: " + str(exc)
    return result

def snapshot():
    return {root + "\\\\" + path: read_key(root, path) for root, path in LOCATIONS}

def record(event):
    event["timestamp"] = now()
    with open(EVENT_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\\n")

def load_events(limit=100):
    if not os.path.exists(EVENT_LOG):
        return []
    result = []
    with open(EVENT_LOG, encoding="utf-8") as f:
        for line in f:
            try: result.append(json.loads(line))
            except json.JSONDecodeError: pass
    return list(reversed(result[-limit:]))

def events():
    return load_events()

def scan():
    global last_scan, last_error
    current = snapshot()
    if not os.path.exists(BASELINE):
        with open(BASELINE, "w", encoding="utf-8") as f:
            json.dump({"created": now(), "snapshot": current}, f, indent=2)
        record({"kind":"baseline_created","severity":"info","location":"configured locations",
                "name":"","old_value":"","new_value":"Initial baseline saved"})
        last_scan, last_error = now(), None
        return
    with open(BASELINE, encoding="utf-8") as f:
        old = json.load(f).get("snapshot", {})
    for location in sorted(set(old) | set(current)):
        before, after = old.get(location, {}), current.get(location, {})
        old_names = set(before) - {"__status__"}
        new_names = set(after) - {"__status__"}
        for name in sorted(new_names - old_names):
            record({"kind":"value_added","severity":"warning","location":location,"name":name,
                    "old_value":"","new_value":after[name].get("data","")})
        for name in sorted(old_names - new_names):
            record({"kind":"value_removed","severity":"warning","location":location,"name":name,
                    "old_value":before[name].get("data",""),"new_value":""})
        for name in sorted(old_names & new_names):
            if before[name] != after[name]:
                record({"kind":"value_changed","severity":"warning","location":location,"name":name,
                        "old_value":before[name].get("data",""),"new_value":after[name].get("data","")})
        if before.get("__status__") != after.get("__status__") and (
            before.get("__status__") or after.get("__status__")):
            record({"kind":"key_status_changed","severity":"info","location":location,"name":"__status__",
                    "old_value":before.get("__status__","readable"),
                    "new_value":after.get("__status__","readable")})
    with open(BASELINE, "w", encoding="utf-8") as f:
        json.dump({"created": now(), "snapshot": current}, f, indent=2)
    last_scan, last_error = now(), None

def loop():
    global running, last_error
    running = True
    while not stop_event.is_set():
        try:
            scan()
        except Exception as exc:
            last_error = str(exc)
        stop_event.wait(5)
    running = False

def start():
    global worker
    if winreg is None:
        global last_error
        last_error = "Windows only: run this project on Windows 10/11."
        return
    if worker and worker.is_alive():
        return
    stop_event.clear()
    worker = threading.Thread(target=loop, daemon=True)
    worker.start()

def stop():
    stop_event.set()

def status():
    return {"platform":platform.system(), "running":running,
            "baseline_exists":os.path.exists(BASELINE), "last_scan":last_scan,
            "last_error":last_error, "locations":len(LOCATIONS),
            "event_count":len(load_events(100000))}
