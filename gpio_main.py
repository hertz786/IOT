#!/usr/bin/env python3
"""
Local fallback GPIO runtime for ELECTRONIC CLIKS SmartLock.
Replace this file with production relay/sensor logic as needed.
"""

from __future__ import annotations

import logging
import sys
import time


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | gpio_main | %(message)s",
    stream=sys.stdout,
)


def main() -> int:
    logging.info("Local fallback gpio_main.py started.")
    while True:
        logging.info("SmartLock heartbeat: GPIO service alive.")
        time.sleep(30)


if __name__ == "__main__":
    raise SystemExit(main())
