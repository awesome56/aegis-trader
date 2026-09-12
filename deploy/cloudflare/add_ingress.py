#!/usr/bin/env python3
"""Idempotently add an ingress hostname to the server's cloudflared config.

Usage (on the server, with sudo):
    sudo python3 add_ingress.py rider.awesometech.com.ng http://localhost:8899
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

CONFIG = Path("/etc/cloudflared/config.yml")


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__)
        return 2

    hostname, service = sys.argv[1], sys.argv[2]
    text = CONFIG.read_text(encoding="utf-8")

    if re.search(rf"^\s*-\s*hostname:\s*{re.escape(hostname)}\s*$", text, re.MULTILINE):
        print(f"{hostname} already present; nothing to do")
        return 0

    lines = text.splitlines()
    catch_all = re.compile(r"^\s*-\s*service:\s*http_status:404")
    index = next((i for i, line in enumerate(lines) if catch_all.match(line)), len(lines))

    block = [
        "  # Aegis Trader API",
        f"  - hostname: {hostname}",
        f"    service: {service}",
        "",
    ]
    lines[index:index] = block

    from datetime import UTC, datetime

    stamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    backup = CONFIG.with_suffix(f".yml.bak.rider-{stamp}")
    backup.write_text(text, encoding="utf-8")
    CONFIG.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"added {hostname} -> {service} (backup: {backup})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
