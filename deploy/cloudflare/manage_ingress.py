#!/usr/bin/env python3
"""Manage ingress hostnames in the server's cloudflared config.

Usage (on the server, with sudo):
    sudo python3 manage_ingress.py add    <hostname> <service> [comment]
    sudo python3 manage_ingress.py remove <hostname>
    sudo python3 manage_ingress.py rename <old-hostname> <new-hostname> [service]

Examples:
    sudo python3 manage_ingress.py add traderbackend.awesometech.com.ng http://localhost:8899
    sudo python3 manage_ingress.py remove old.awesometech.com.ng
"""

from __future__ import annotations

import argparse
import re
from datetime import UTC, datetime
from pathlib import Path

CONFIG = Path("/etc/cloudflared/config.yml")
CATCH_ALL = re.compile(r"^\s*-\s*service:\s*http_status:404")
HOSTNAME_LINE = r"^\s*-\s*hostname:\s*{host}\s*$"


def _backup(text: str) -> Path:
    stamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    backup = CONFIG.with_suffix(f".yml.bak.ingress-{stamp}")
    backup.write_text(text, encoding="utf-8")
    return backup


def _write(text: str) -> None:
    CONFIG.write_text(text, encoding="utf-8")


def _block_index(lines: list[str], hostname: str) -> int | None:
    pattern = re.compile(HOSTNAME_LINE.format(host=re.escape(hostname)))
    for i, line in enumerate(lines):
        if pattern.match(line):
            return i
    return None


def add(hostname: str, service: str, comment: str) -> int:
    text = CONFIG.read_text(encoding="utf-8")
    if re.search(HOSTNAME_LINE.format(host=re.escape(hostname)), text, re.MULTILINE):
        print(f"{hostname} already present; nothing to do")
        return 0
    lines = text.splitlines()
    index = next((i for i, line in enumerate(lines) if CATCH_ALL.match(line)), len(lines))
    lines[index:index] = [f"  # {comment}", f"  - hostname: {hostname}", f"    service: {service}", ""]
    backup = _backup(text)
    _write("\n".join(lines) + "\n")
    print(f"added {hostname} -> {service} (backup: {backup})")
    return 0


def remove(hostname: str) -> int:
    text = CONFIG.read_text(encoding="utf-8")
    lines = text.splitlines()
    index = _block_index(lines, hostname)
    if index is None:
        print(f"{hostname} not present; nothing to do")
        return 0
    # Remove the hostname line and its indented service line, plus a preceding comment.
    start = index
    end = index + 1
    while end < len(lines) and lines[end].startswith("    ") and not lines[end].startswith("  - "):
        end += 1
    if start > 0 and lines[start - 1].strip().startswith("#"):
        start -= 1
    del lines[start:end]
    backup = _backup(text)
    _write("\n".join(lines) + "\n")
    print(f"removed {hostname} (backup: {backup})")
    return 0


def rename(old: str, new: str, service: str | None) -> int:
    text = CONFIG.read_text(encoding="utf-8")
    if not re.search(HOSTNAME_LINE.format(host=re.escape(old)), text, re.MULTILINE):
        print(f"{old} not present; adding {new} instead")
        return add(new, service or "http://localhost:8899", "Aegis Trader API")
    lines = text.splitlines()
    index = _block_index(lines, old)
    assert index is not None
    lines[index] = lines[index].replace(old, new)
    if service:
        lines[index + 1] = f"    service: {service}"
    backup = _backup(text)
    _write("\n".join(lines) + "\n")
    print(f"renamed {old} -> {new} (backup: {backup})")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_add = sub.add_parser("add")
    p_add.add_argument("hostname")
    p_add.add_argument("service")
    p_add.add_argument("--comment", default="Aegis Trader API")

    p_remove = sub.add_parser("remove")
    p_remove.add_argument("hostname")

    p_rename = sub.add_parser("rename")
    p_rename.add_argument("old")
    p_rename.add_argument("new")
    p_rename.add_argument("--service", default=None)

    args = parser.parse_args()
    if args.command == "add":
        return add(args.hostname, args.service, args.comment)
    if args.command == "remove":
        return remove(args.hostname)
    return rename(args.old, args.new, args.service)


if __name__ == "__main__":
    raise SystemExit(main())
