#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Splunk custom command: generate an authenticated, short-lived AIOps URL."""

import json
import html
import os
import secrets
import ssl
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

from aiops_handoff_protocol import normalize_roles, sign_handoff


APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCAL_DIR = os.path.join(APP_ROOT, "local")


def _read_setting(environment_name, file_name, required=True, default=""):
    value = os.environ.get(environment_name, "").strip()
    if not value:
        path = os.path.join(LOCAL_DIR, file_name)
        try:
            with open(path, "r", encoding="utf-8") as setting_file:
                value = setting_file.read().strip()
        except FileNotFoundError:
            value = ""
    if not value:
        value = default
    if required and not value:
        raise RuntimeError(
            f"missing {environment_name}; configure local/{file_name}"
        )
    return value


def _get_setting(settings, *names):
    for name in names:
        value = settings.get(name)
        if value:
            return str(value).strip()
    return ""


def _parse_auth_string(auth_string):
    """Extract the user and session token passed by legacy Splunk commands."""
    raw_value = html.unescape(str(auth_string or "").strip())
    if not raw_value:
        return "", ""
    if not raw_value.startswith("<"):
        if raw_value.startswith("Splunk "):
            raw_value = raw_value[7:]
        return "", raw_value.strip()

    try:
        root = ET.fromstring(raw_value)
    except ET.ParseError as exc:
        raise RuntimeError(f"invalid Splunk authString XML: {exc}")

    values = {}
    for element in root.iter():
        local_name = element.tag.rsplit("}", 1)[-1].lower()
        text = (element.text or "").strip()
        if text:
            values[local_name] = text
    username = values.get("username") or values.get("userid") or ""
    session_key = (
        values.get("authtoken")
        or values.get("sessionkey")
        or values.get("token")
        or ""
    )
    return username, session_key


def _load_current_context(settings):
    """Resolve identity from Splunk's authenticated session, never from SPL input."""
    session_key = _get_setting(settings, "sessionKey", "session_key")
    auth_username, auth_token = _parse_auth_string(
        _get_setting(settings, "authString", "auth_string")
    )
    if not session_key:
        session_key = auth_token
    if not session_key:
        raise RuntimeError("Splunk did not pass a session token to the command")
    if session_key.startswith("Splunk "):
        session_key = session_key[7:]

    splunkd_uri = _get_setting(
        settings, "splunkdUri", "splunkd_uri", "serverUri", "server_uri"
    )
    if not splunkd_uri:
        splunkd_uri = _read_setting(
            "SPLUNKD_URI",
            "splunkd_url",
            required=False,
            default="https://127.0.0.1:8089",
        )

    endpoint = (
        splunkd_uri.rstrip("/")
        + "/services/authentication/current-context?output_mode=json"
    )
    auth_request = urllib.request.Request(
        endpoint,
        headers={"Authorization": f"Splunk {session_key}"},
        method="GET",
    )
    tls_context = None
    if endpoint.lower().startswith("https://"):
        verify_tls = os.environ.get("SPLUNK_VERIFY_TLS", "false").lower()
        if verify_tls not in {"1", "true", "yes", "on"}:
            tls_context = ssl._create_unverified_context()

    with urllib.request.urlopen(auth_request, timeout=10, context=tls_context) as response:
        payload = json.loads(response.read().decode("utf-8"))

    entries = payload.get("entry") or []
    if not entries:
        raise RuntimeError("Splunk current-context returned no user entry")
    content = entries[0].get("content") or {}
    username = str(content.get("username") or "").strip()
    roles = content.get("roles") or []
    if isinstance(roles, str):
        roles = roles.split(",")
    if not username:
        raise RuntimeError("Splunk current-context returned an empty username")
    if auth_username and username != auth_username:
        raise RuntimeError("Splunk authString user does not match current-context")
    return username, roles


def _validate_base_url(base_url):
    parsed = urllib.parse.urlsplit(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise RuntimeError("AIOPS_HANDOFF_BASE_URL must be an absolute HTTP(S) URL")
    if parsed.query or parsed.fragment:
        raise RuntimeError("AIOPS_HANDOFF_BASE_URL must not contain query or fragment")
    return base_url


def build_signed_url(*, base_url, secret, username, roles, now, ttl_seconds):
    ttl = int(ttl_seconds)
    if ttl < 30 or ttl > 300:
        raise RuntimeError("AIOPS_HANDOFF_TTL_SECONDS must be between 30 and 300")

    normalized_roles = normalize_roles(roles)
    exp = int(now) + ttl
    nonce = secrets.token_hex(16)
    signature = sign_handoff(
        secret, username, exp, nonce, normalized_roles
    )
    query = urllib.parse.urlencode({
        "v": "1",
        "user": username,
        "exp": str(exp),
        "nonce": nonce,
        "roles": normalized_roles,
        "sig": signature,
    })
    separator = "&" if "?" in base_url else "?"
    return f"{base_url}{separator}{query}", exp


def main():
    import splunk.Intersplunk

    try:
        results, _, settings = splunk.Intersplunk.getOrganizedResults()
        username, roles = _load_current_context(settings)
        secret = _read_setting("AIOPS_HANDOFF_SECRET", "hmac_secret")
        base_url = _validate_base_url(_read_setting(
            "AIOPS_HANDOFF_BASE_URL", "handoff_url"
        ))
        ttl_seconds = _read_setting(
            "AIOPS_HANDOFF_TTL_SECONDS",
            "ttl_seconds",
            required=False,
            default="90",
        )
        handoff_url, exp = build_signed_url(
            base_url=base_url,
            secret=secret,
            username=username,
            roles=roles,
            now=int(time.time()),
            ttl_seconds=ttl_seconds,
        )

        output = results[:1] if results else [{}]
        output[0]["handoff_url"] = handoff_url
        output[0]["handoff_user"] = username
        output[0]["handoff_exp"] = exp
        splunk.Intersplunk.outputResults(output)
    except Exception as exc:
        splunk.Intersplunk.generateErrorResults(
            f"aiopssignurl failed: {exc}"
        )


if __name__ == "__main__":
    main()
