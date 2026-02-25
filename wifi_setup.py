#!/usr/bin/env python3
"""
ELECTRONIC CLIKS SmartLock IoT Wi-Fi provisioning utility.
- If internet is already available, exits.
- If offline, starts temporary hotspot "SmartLock-Setup".
- Serves a Flask portal for SSID/password input.
- Writes credentials into /etc/wpa_supplicant/wpa_supplicant.conf.
- Connects to Wi-Fi and shuts hotspot down automatically.
"""

from __future__ import annotations

import argparse
import html
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import socket
import subprocess
import sys
import threading
import time

from flask import Flask, request

PROJECT_NAME = "electronicclicks"
HOTSPOT_SSID = "SmartLock-Setup"
HOTSPOT_PASSWORD = "electroniccliks"
WPA_SUPPLICANT_FILE = Path("/etc/wpa_supplicant/wpa_supplicant.conf")

app = Flask(__name__)
LOGGER = logging.getLogger(PROJECT_NAME + "_wifi")
WIFI_INTERFACE = ""
HOTSPOT_CONNECTION_NAME = ""


def _resolve_log_file() -> Path:
    preferred = Path("/var/log") / PROJECT_NAME / "wifi_setup.log"
    fallback = Path(__file__).resolve().parent / "logs" / "wifi_setup.log"

    for candidate in (preferred, fallback):
        try:
            candidate.parent.mkdir(parents=True, exist_ok=True)
            with open(candidate, "a", encoding="utf-8"):
                pass
            return candidate
        except OSError:
            continue

    return fallback


def setup_logger() -> None:
    LOGGER.setLevel(logging.INFO)
    if LOGGER.handlers:
        return

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = RotatingFileHandler(_resolve_log_file(), maxBytes=2 * 1024 * 1024, backupCount=3)
    file_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)

    LOGGER.addHandler(file_handler)
    LOGGER.addHandler(stream_handler)
    LOGGER.propagate = False


def run_command(command: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    LOGGER.info("Executing command: %s", " ".join(command))
    return subprocess.run(command, check=check, text=True, capture_output=True)


def is_internet_connected() -> bool:
    try:
        with socket.create_connection(("1.1.1.1", 53), timeout=3):
            return True
    except OSError:
        return False


def detect_wifi_interface() -> str:
    result = run_command(["nmcli", "-t", "-f", "DEVICE,TYPE", "device", "status"])
    for line in result.stdout.splitlines():
        parts = line.split(":")
        if len(parts) >= 2 and parts[1] == "wifi" and parts[0]:
            return parts[0]
    return ""


def get_active_connection_for_device(device: str) -> str:
    result = run_command(["nmcli", "-t", "-f", "NAME,DEVICE", "connection", "show", "--active"])
    for line in result.stdout.splitlines():
        parts = line.split(":")
        if len(parts) >= 2 and parts[1] == device:
            return parts[0]
    return ""


def start_hotspot() -> None:
    global HOTSPOT_CONNECTION_NAME

    run_command(["nmcli", "device", "set", WIFI_INTERFACE, "managed", "yes"], check=False)
    run_command(
        [
            "nmcli",
            "device",
            "wifi",
            "hotspot",
            "ifname",
            WIFI_INTERFACE,
            "ssid",
            HOTSPOT_SSID,
            "password",
            HOTSPOT_PASSWORD,
        ]
    )
    HOTSPOT_CONNECTION_NAME = get_active_connection_for_device(WIFI_INTERFACE) or "Hotspot"
    LOGGER.info("Hotspot '%s' started on %s", HOTSPOT_SSID, WIFI_INTERFACE)


def stop_hotspot() -> None:
    if HOTSPOT_CONNECTION_NAME:
        run_command(["nmcli", "connection", "down", HOTSPOT_CONNECTION_NAME], check=False)
        LOGGER.info("Hotspot connection '%s' stopped.", HOTSPOT_CONNECTION_NAME)


def escape_wpa(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def write_wifi_credentials(ssid: str, password: str) -> None:
    network_block = (
        "\nnetwork={\n"
        f'    ssid="{escape_wpa(ssid)}"\n'
        f'    psk="{escape_wpa(password)}"\n'
        "    key_mgmt=WPA-PSK\n"
        "}\n"
    )

    existing = ""
    if WPA_SUPPLICANT_FILE.exists():
        existing = WPA_SUPPLICANT_FILE.read_text(encoding="utf-8", errors="ignore")

    if f'ssid="{escape_wpa(ssid)}"' in existing:
        LOGGER.info("SSID already present in wpa_supplicant. Skipping file append.")
        return

    WPA_SUPPLICANT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(WPA_SUPPLICANT_FILE, "a", encoding="utf-8") as file_handle:
        file_handle.write(network_block)

    LOGGER.info("Wi-Fi credentials appended to %s", WPA_SUPPLICANT_FILE)


def connect_to_wifi(ssid: str, password: str) -> None:
    run_command(["nmcli", "connection", "delete", ssid], check=False)
    run_command(
        ["nmcli", "device", "wifi", "connect", ssid, "password", password, "ifname", WIFI_INTERFACE]
    )
    LOGGER.info("Connected to Wi-Fi SSID '%s'", ssid)


def schedule_shutdown() -> None:
    def _shutdown() -> None:
        time.sleep(2)
        LOGGER.info("Shutting down setup portal after successful provisioning.")
        stop_hotspot()
        time.sleep(1)
        os._exit(0)

    threading.Thread(target=_shutdown, daemon=True).start()


@app.route("/", methods=["GET", "POST"])
def portal() -> str:
    if request.method == "POST":
        ssid = (request.form.get("ssid") or "").strip()
        password = (request.form.get("password") or "").strip()

        if not ssid or not password:
            return render_form("SSID and password are required.", is_error=True)

        try:
            write_wifi_credentials(ssid, password)
            connect_to_wifi(ssid, password)
            schedule_shutdown()
            return render_form("Wi-Fi connected successfully. Hotspot is shutting down.")
        except Exception as exc:  # pylint: disable=broad-except
            LOGGER.exception("Wi-Fi provisioning failed: %s", exc)
            return render_form("Connection failed. Please verify credentials and retry.", is_error=True)

    return render_form()


def render_form(message: str = "", is_error: bool = False) -> str:
    safe_message = html.escape(message)
    color = "#b91c1c" if is_error else "#166534"
    return f"""
<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
  <title>ELECTRONIC CLIKS SmartLock Setup</title>
  <style>
    body {{ font-family: Arial, sans-serif; background: #f4f6f8; margin: 0; padding: 24px; }}
    .card {{ max-width: 480px; margin: 32px auto; background: #ffffff; border-radius: 10px; padding: 24px; box-shadow: 0 6px 20px rgba(0,0,0,0.08); }}
    h1 {{ font-size: 1.25rem; margin-top: 0; color: #0f172a; }}
    label {{ display: block; margin-top: 12px; font-weight: 600; color: #334155; }}
    input {{ width: 100%; padding: 10px; margin-top: 6px; border: 1px solid #cbd5e1; border-radius: 8px; }}
    button {{ margin-top: 18px; width: 100%; padding: 10px; border: 0; border-radius: 8px; background: #1d4ed8; color: white; font-weight: 600; cursor: pointer; }}
    .msg {{ margin-top: 14px; color: {color}; font-weight: 600; }}
    .sub {{ color: #475569; font-size: .95rem; margin-top: 0; }}
  </style>
</head>
<body>
  <div class=\"card\">
    <h1>ELECTRONIC CLIKS | SmartLock Wi-Fi Setup</h1>
    <p class=\"sub\">Connect your SmartLock device to your local Wi-Fi network.</p>
    <form method=\"post\">
      <label for=\"ssid\">Wi-Fi SSID</label>
      <input id=\"ssid\" name=\"ssid\" type=\"text\" required>
      <label for=\"password\">Wi-Fi Password</label>
      <input id=\"password\" name=\"password\" type=\"password\" required>
      <button type=\"submit\">Connect Device</button>
    </form>
    <div class=\"msg\">{safe_message}</div>
  </div>
</body>
</html>
"""


def main() -> int:
    global WIFI_INTERFACE

    setup_logger()
    LOGGER.info("=== ELECTRONIC CLIKS Wi-Fi setup start ===")

    if is_internet_connected():
        LOGGER.info("Internet already connected. Wi-Fi provisioning skipped.")
        return 0

    WIFI_INTERFACE = detect_wifi_interface()
    if not WIFI_INTERFACE:
        LOGGER.error("No Wi-Fi interface detected. Ensure NetworkManager is installed and enabled.")
        return 1

    start_hotspot()

    parser = argparse.ArgumentParser(description="SmartLock Wi-Fi provisioning portal")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=80)
    args = parser.parse_args()

    LOGGER.info("Portal started at http://%s:%s", args.host, args.port)
    app.run(host=args.host, port=args.port, debug=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
