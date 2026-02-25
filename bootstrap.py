#!/usr/bin/env python3
"""
ELECTRONIC CLIKS SmartLock IoT bootstrap launcher.
- Checks connectivity.
- Pulls latest GPIO runtime from GitLab when online.
- Falls back to local gpio_main.py when cloud code is unavailable.
- Executes selected GPIO script.
- Logs all actions for production operations.
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
from typing import Optional

import requests

PROJECT_NAME = "electronicclicks"
SCRIPT_DIR = Path(__file__).resolve().parent
LOCAL_GPIO_SCRIPT = SCRIPT_DIR / "gpio_main.py"
CLOUD_GPIO_SCRIPT = SCRIPT_DIR / "gpio_main_cloud.py"

PRIMARY_CLOUD_URL = os.getenv(
    "GITLAB_GPIO_RAW_URL",
    "https://raw.githubusercontent.com/hertz786/IOT/main/gpio_main.py",
)
ADDITIONAL_CLOUD_URLS = os.getenv(
    "CLOUD_GPIO_ADDITIONAL_URLS",
    "https://raw.githubusercontent.com/hertz786/IOT/master/gpio_main.py",
)
REQUEST_TIMEOUT_SECONDS = int(os.getenv("BOOTSTRAP_HTTP_TIMEOUT", "15"))
INTERNET_TEST_HOST = os.getenv("BOOTSTRAP_INET_HOST", "1.1.1.1")
INTERNET_TEST_PORT = int(os.getenv("BOOTSTRAP_INET_PORT", "53"))


def _resolve_log_file() -> Path:
    preferred = Path("/var/log") / PROJECT_NAME / "bootstrap.log"
    fallback = SCRIPT_DIR / "logs" / "bootstrap.log"

    for candidate in (preferred, fallback):
        try:
            candidate.parent.mkdir(parents=True, exist_ok=True)
            with open(candidate, "a", encoding="utf-8"):
                pass
            return candidate
        except OSError:
            continue

    return fallback


def _setup_logger() -> logging.Logger:
    logger = logging.getLogger(PROJECT_NAME)
    logger.setLevel(logging.INFO)

    if logger.handlers:
        return logger

    log_file = _resolve_log_file()
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = RotatingFileHandler(log_file, maxBytes=2 * 1024 * 1024, backupCount=5)
    file_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    logger.propagate = False

    logger.info("Bootstrap logger initialized at %s", log_file)
    return logger


LOGGER = _setup_logger()


def is_internet_reachable() -> bool:
    try:
        with socket.create_connection((INTERNET_TEST_HOST, INTERNET_TEST_PORT), timeout=3):
            LOGGER.info("Internet connectivity check succeeded.")
            return True
    except OSError as exc:
        LOGGER.warning("Internet connectivity check failed: %s", exc)
        return False


def _cloud_source_urls() -> list[str]:
    urls = [PRIMARY_CLOUD_URL.strip()]
    urls.extend(item.strip() for item in ADDITIONAL_CLOUD_URLS.split(",") if item.strip())
    seen = set()
    deduped = []
    for url in urls:
        if url and url not in seen:
            deduped.append(url)
            seen.add(url)
    return deduped


def _request_headers() -> dict[str, str]:
    token = os.getenv("CLOUD_BEARER_TOKEN") or os.getenv("GITHUB_TOKEN", "")
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}


def download_latest_gpio_script(url: str, output_path: Path) -> bool:
    LOGGER.info("Attempting cloud GPIO download from %s", url)
    try:
        response = requests.get(url, timeout=REQUEST_TIMEOUT_SECONDS, headers=_request_headers())
        response.raise_for_status()

        with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8") as temp_file:
            temp_file.write(response.text)
            temp_name = temp_file.name

        os.replace(temp_name, output_path)
        output_path.chmod(0o755)
        LOGGER.info("Cloud GPIO script downloaded to %s", output_path)
        return True
    except Exception as exc:  # pylint: disable=broad-except
        LOGGER.error("Cloud GPIO download failed: %s", exc)
        return False


def select_main_script() -> Optional[Path]:
    if is_internet_reachable():
        for cloud_url in _cloud_source_urls():
            if download_latest_gpio_script(cloud_url, CLOUD_GPIO_SCRIPT):
                LOGGER.info("Using cloud GPIO script: %s", CLOUD_GPIO_SCRIPT)
                return CLOUD_GPIO_SCRIPT
        LOGGER.warning("Cloud script unavailable, falling back to local GPIO script.")

    if LOCAL_GPIO_SCRIPT.exists():
        LOGGER.info("Using local fallback GPIO script: %s", LOCAL_GPIO_SCRIPT)
        return LOCAL_GPIO_SCRIPT

    LOGGER.critical("No runnable GPIO script found. Expected local script at %s", LOCAL_GPIO_SCRIPT)
    return None


def run_script(script_path: Path) -> int:
    LOGGER.info("Launching GPIO runtime: %s", script_path)
    try:
        completed = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=str(SCRIPT_DIR),
            check=False,
        )
        LOGGER.info("GPIO runtime exited with code %s", completed.returncode)
        return completed.returncode
    except Exception as exc:  # pylint: disable=broad-except
        LOGGER.exception("Failed to execute GPIO runtime: %s", exc)
        return 1


def main() -> int:
    LOGGER.info("=== ELECTRONIC CLIKS SmartLock bootstrap start ===")
    script_to_run = select_main_script()
    if script_to_run is None:
        LOGGER.critical("Bootstrap stopping because no GPIO script could be selected.")
        return 1

    exit_code = run_script(script_to_run)
    LOGGER.info("=== ELECTRONIC CLIKS SmartLock bootstrap stop (code=%s) ===", exit_code)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
