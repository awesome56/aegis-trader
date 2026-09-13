"""SSRF-safe validation for custom provider base URLs."""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

from app.core.config import Settings, get_settings

_BLOCKED_HOSTNAMES = {
    "localhost",
    "metadata.google.internal",
    "metadata.google",
}


class UnsafeBaseUrlError(ValueError):
    """Raised when a base URL targets a non-public/disallowed host."""


def _is_public_ip(value: str) -> bool:
    try:
        ip = ipaddress.ip_address(value)
    except ValueError:
        return False
    return not (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def validate_base_url(url: str, settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    parsed = urlparse(url.strip())
    if parsed.scheme not in ("http", "https"):
        raise UnsafeBaseUrlError("base_url must use http or https")
    if parsed.scheme == "http" and not settings.AI_ALLOW_HTTP_BASE_URL:
        raise UnsafeBaseUrlError("base_url must use https (http is disabled)")
    host = parsed.hostname
    if not host:
        raise UnsafeBaseUrlError("base_url must include a host")

    # Explicit administrator opt-in permits private/loopback targets (e.g. a
    # self-hosted gateway). Disabled by default.
    if settings.AI_ALLOW_PRIVATE_BASE_URL:
        return url.strip()

    lowered = host.lower()
    if lowered in _BLOCKED_HOSTNAMES or lowered.endswith(".localhost"):
        raise UnsafeBaseUrlError("base_url host is not permitted")

    # Literal IP?
    try:
        ipaddress.ip_address(lowered)
        if not _is_public_ip(lowered):
            raise UnsafeBaseUrlError("base_url resolves to a private or reserved address")
        return url.strip()
    except ValueError:
        pass

    try:
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        infos = socket.getaddrinfo(lowered, port)
    except OSError as exc:
        raise UnsafeBaseUrlError("base_url host could not be resolved") from exc
    for info in infos:
        address = str(info[4][0])
        if not _is_public_ip(address):
            raise UnsafeBaseUrlError("base_url resolves to a private or reserved address")
    return url.strip()
