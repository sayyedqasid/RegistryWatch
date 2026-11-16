# RegistryWatch — Windows Registry Changes Monitoring System

A defensive cybersecurity project that takes a baseline of selected Windows Registry startup locations, checks for added/removed/changed values, logs events, and displays them in a local Flask dashboard.

## Requirements
- Windows 10/11 and Python 3.10+
- VS Code recommended
- Flask (installed from requirements.txt)

## Run it in VS Code
1. Extract this ZIP to a folder.
2. In VS Code choose **File → Open Folder** and select `RegistryWatch_Project`.
3. Choose **Terminal → New Terminal**.
4. Run:
   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install -r requirements.txt
   python app.py
   ```
   If PowerShell blocks activation, use:
   ` .\.venv\Scripts\python.exe -m pip install -r requirements.txt`
   then launch with ` .\.venv\Scripts\python.exe app.py`.
5. Open `http://127.0.0.1:5000` and click **Start monitoring**.

## How it works
- Reads a small set of startup-related registry paths with read access.
- First scan stores a baseline in `data/baseline.json`.
- Every five seconds, it compares the current registry values with the baseline.
- Added, removed, and changed values are recorded in `logs/events.jsonl`.
- The dashboard displays recent events.

## Safety and limitations
- This tool is read-only; it does not modify registry keys or values.
- Some HKLM locations may show “access denied”. Start normally first; use Administrator privileges only if needed and understood.
- A detected change is not proof of malware. Software updates and legitimate installers can also change registry values.
- The tool monitors only its configured locations and is not a full EDR product.
- The web server listens only on `127.0.0.1`, not the local network.

## Suggested demo
1. Start monitoring and let the first scan create the baseline.
2. Use a Windows test machine/VM for any experiments.
3. Wait five seconds and review events.
4. Explain why each alert requires investigation rather than automatic assumptions.

## Project structure
- `app.py` — Flask dashboard routes
- `registry_monitor.py` — read-only scan, baseline, comparison, event log
- `templates/dashboard.html` — dashboard page
- `static/style.css` — styling
- `data/` — baseline generated at runtime
- `logs/` — event history generated at runtime
