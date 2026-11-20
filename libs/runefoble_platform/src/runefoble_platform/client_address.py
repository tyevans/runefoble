"""Client address for rate limits, read through trusted proxies only (ADR-0023 d).

A proxy such as Traefik appends the address of its peer to `X-Forwarded-For`. The header counts
only when the direct peer is a trusted proxy. Walking the header from the right, the first
address that is not a trusted proxy is the client. A client can prepend any value to the
header, so the leftmost values are never used. When the peer is not trusted, the header is
ignored, so a client cannot choose its own rate-limit key.
"""

from __future__ import annotations

from ipaddress import IPv4Network, IPv6Network, ip_address, ip_network

Network = IPv4Network | IPv6Network
UNKNOWN_CLIENT = "unknown"


def parse_trusted_proxies(raw: str) -> tuple[Network, ...]:
    """Parse a comma-separated list of CIDR networks. A bad entry raises ValueError."""
    networks: list[Network] = []
    for item in raw.split(","):
        text = item.strip()
        if text:
            networks.append(ip_network(text, strict=False))
    return tuple(networks)


def client_address(
    peer: str | None, forwarded_for: str | None, trusted: tuple[Network, ...]
) -> str:
    """Return the address that a rate limit counts for this request."""
    if peer is None:
        return UNKNOWN_CLIENT
    peer_ip = _parse(peer)
    if peer_ip is None or not _is_trusted(peer_ip, trusted) or not forwarded_for:
        return peer
    for entry in reversed(forwarded_for.split(",")):
        candidate = _parse(entry.strip())
        if candidate is None:
            return peer
        if not _is_trusted(candidate, trusted):
            return str(candidate)
    return peer


def _parse(text: str):
    try:
        return ip_address(text)
    except ValueError:
        return None


def _is_trusted(address, trusted: tuple[Network, ...]) -> bool:
    return any(address in network for network in trusted)
