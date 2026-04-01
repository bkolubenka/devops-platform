#!/usr/bin/env python3
"""Update a Cloudflare A record with the current public IPv4 address.

This script is intended to run on a home VM behind the router. It keeps a DNS
record such as local.kydyrov.dev pointed at the current WAN IPv4 address by
calling the Cloudflare API.

The script uses only the Python standard library so it can run anywhere that
has Python 3 available.
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, replace
from typing import Any

API_BASE_URL = "https://api.cloudflare.com/client/v4"
DEFAULT_PUBLIC_IP_URL = "https://api.ipify.org?format=json"
DEFAULT_ZONE_NAME = "kydyrov.dev"
DEFAULT_RECORD_NAME = "local.kydyrov.dev"
DEFAULT_RECORD_TYPE = "A"
DEFAULT_TTL = 1
DEFAULT_TIMEOUT_SECONDS = 15


class CloudflareDDNSError(RuntimeError):
    pass


@dataclass(frozen=True)
class Settings:
    api_token: str
    zone_name: str
    record_name: str
    record_type: str
    ttl: int
    proxied: bool
    public_ip_url: str
    timeout_seconds: int


def parse_bool(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise argparse.ArgumentTypeError(f"Invalid boolean value: {value!r}")


def env(name: str, default: str | None = None, required: bool = False) -> str:
    value = os.environ.get(name, default)
    if required and not value:
        raise CloudflareDDNSError(f"Missing required environment variable: {name}")
    return value or ""


def load_settings() -> Settings:
    return Settings(
        api_token=env("CF_API_TOKEN", required=True),
        zone_name=env("CF_ZONE_NAME", DEFAULT_ZONE_NAME),
        record_name=env("CF_RECORD_NAME", DEFAULT_RECORD_NAME),
        record_type=env("CF_RECORD_TYPE", DEFAULT_RECORD_TYPE).upper(),
        ttl=int(env("CF_TTL", str(DEFAULT_TTL))),
        proxied=parse_bool(env("CF_PROXIED", "false")),
        public_ip_url=env("CF_PUBLIC_IP_URL", DEFAULT_PUBLIC_IP_URL),
        timeout_seconds=int(env("CF_TIMEOUT_SECONDS", str(DEFAULT_TIMEOUT_SECONDS))),
    )


def request_text(url: str, *, method: str = "GET", headers: dict[str, str] | None = None, payload: Any = None, timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS) -> str:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=body, headers=headers or {}, method=method)

    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            return response.read().decode("utf-8").strip()
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace").strip()
        raise CloudflareDDNSError(
            f"HTTP {exc.code} while calling {method} {url}: {error_body or exc.reason}"
        ) from exc
    except urllib.error.URLError as exc:
        raise CloudflareDDNSError(f"Failed to call {method} {url}: {exc.reason}") from exc


def request_json(url: str, *, method: str = "GET", headers: dict[str, str] | None = None, payload: Any = None, timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS) -> dict[str, Any]:
    raw = request_text(url, method=method, headers=headers, payload=payload, timeout_seconds=timeout_seconds)
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise CloudflareDDNSError(f"Expected JSON response from {url}, got: {raw!r}") from exc

    if not isinstance(parsed, dict):
        raise CloudflareDDNSError(f"Expected JSON object from {url}, got: {type(parsed).__name__}")

    return parsed


def cloudflare_headers(api_token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def cloudflare_api(settings: Settings, method: str, path: str, payload: Any = None) -> dict[str, Any]:
    response = request_json(
        f"{API_BASE_URL}{path}",
        method=method,
        headers=cloudflare_headers(settings.api_token),
        payload=payload,
        timeout_seconds=settings.timeout_seconds,
    )

    if not response.get("success", False):
        errors = response.get("errors", [])
        messages = "; ".join(
            error.get("message", str(error)) if isinstance(error, dict) else str(error)
            for error in errors
        )
        raise CloudflareDDNSError(messages or f"Cloudflare API call failed: {response}")

    return response


def fetch_public_ipv4(settings: Settings) -> str:
    raw = request_text(settings.public_ip_url, timeout_seconds=settings.timeout_seconds)
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = raw

    if isinstance(parsed, dict):
        for key in ("ip", "address", "ipv4"):
            if key in parsed and parsed[key]:
                raw_ip = str(parsed[key]).strip()
                break
        else:
            raise CloudflareDDNSError(
                f"Public IP response from {settings.public_ip_url} did not include an IP field: {parsed}"
            )
    else:
        raw_ip = str(parsed).strip()

    try:
        ip_obj = ipaddress.ip_address(raw_ip)
    except ValueError as exc:
        raise CloudflareDDNSError(
            f"Public IP endpoint returned an invalid IP address: {raw_ip!r}"
        ) from exc

    if ip_obj.version != 4:
        raise CloudflareDDNSError(f"Expected IPv4 address, got IPv{ip_obj.version}: {raw_ip}")

    return str(ip_obj)


def get_zone_id(settings: Settings) -> str:
    query = urllib.parse.urlencode({"name": settings.zone_name, "status": "active", "per_page": 1})
    response = cloudflare_api(settings, "GET", f"/zones?{query}")
    zones = response.get("result", [])

    if not zones:
        raise CloudflareDDNSError(f"Zone not found or not active: {settings.zone_name}")

    return zones[0]["id"]


def get_dns_record(settings: Settings, zone_id: str) -> dict[str, Any] | None:
    query = urllib.parse.urlencode(
        {
            "type": settings.record_type,
            "name": settings.record_name,
            "per_page": 100,
        }
    )
    response = cloudflare_api(settings, "GET", f"/zones/{zone_id}/dns_records?{query}")
    records = response.get("result", [])

    if not records:
        return None

    if len(records) > 1:
        raise CloudflareDDNSError(
            f"Multiple {settings.record_type} records found for {settings.record_name}; refusing to guess"
        )

    return records[0]


def upsert_dns_record(settings: Settings, zone_id: str, current_ip: str) -> tuple[str, dict[str, Any]]:
    record = get_dns_record(settings, zone_id)
    payload = {
        "type": settings.record_type,
        "name": settings.record_name,
        "content": current_ip,
        "ttl": settings.ttl,
        "proxied": settings.proxied,
    }

    if record is None:
        response = cloudflare_api(settings, "POST", f"/zones/{zone_id}/dns_records", payload)
        return "created", response["result"]

    if (
        record.get("content") == current_ip
        and int(record.get("ttl", settings.ttl)) == settings.ttl
        and bool(record.get("proxied", False)) == settings.proxied
    ):
        return "unchanged", record

    response = cloudflare_api(settings, "PUT", f"/zones/{zone_id}/dns_records/{record['id']}", payload)
    return "updated", response["result"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Update a Cloudflare A record from the current public IPv4.")
    parser.add_argument("--zone-name", default=None, help="Cloudflare zone name, e.g. kydyrov.dev")
    parser.add_argument("--record-name", default=None, help="DNS record name, e.g. local.kydyrov.dev")
    parser.add_argument("--record-type", default=None, help="DNS record type, default: A")
    parser.add_argument("--ttl", type=int, default=None, help="DNS TTL (1 means auto)")
    parser.add_argument("--proxied", action="store_true", help="Set Cloudflare proxy on for the record")
    parser.add_argument("--public-ip-url", default=None, help="Endpoint that returns the current public IP")
    parser.add_argument("--timeout-seconds", type=int, default=None, help="HTTP timeout for API calls")
    parser.add_argument("--dry-run", action="store_true", help="Show the action without updating Cloudflare")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    settings = load_settings()

    if args.zone_name:
        settings = replace(settings, zone_name=args.zone_name)
    if args.record_name:
        settings = replace(settings, record_name=args.record_name)
    if args.record_type:
        settings = replace(settings, record_type=args.record_type.upper())
    if args.ttl is not None:
        settings = replace(settings, ttl=args.ttl)
    if args.proxied:
        settings = replace(settings, proxied=True)
    if args.public_ip_url:
        settings = replace(settings, public_ip_url=args.public_ip_url)
    if args.timeout_seconds is not None:
        settings = replace(settings, timeout_seconds=args.timeout_seconds)

    current_ip = fetch_public_ipv4(settings)
    zone_id = get_zone_id(settings)
    record = get_dns_record(settings, zone_id)

    if record is not None:
        record_ip = record.get("content", "")
        record_proxied = bool(record.get("proxied", False))
        record_ttl = int(record.get("ttl", settings.ttl))
        if record_ip == current_ip and record_proxied == settings.proxied and record_ttl == settings.ttl:
            print(
                f"{settings.record_name} already points to {current_ip} (proxied={settings.proxied}, ttl={settings.ttl})"
            )
            return 0

    if args.dry_run:
        action = "create" if record is None else "update"
        print(
            f"Dry run: would {action} {settings.record_type} record {settings.record_name} in {settings.zone_name} to {current_ip}"
        )
        return 0

    action, result = upsert_dns_record(settings, zone_id, current_ip)
    print(
        f"{action.capitalize()}d {settings.record_type} record {result['name']} -> {result['content']} (proxied={result.get('proxied', False)}, ttl={result.get('ttl', settings.ttl)})"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except CloudflareDDNSError as exc:
        print(f"cloudflare-ddns: {exc}", file=sys.stderr)
        raise SystemExit(1)
