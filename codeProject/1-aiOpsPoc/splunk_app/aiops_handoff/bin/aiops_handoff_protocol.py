#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared wire-format helpers for the Splunk side of the AIOps handoff."""

import hashlib
import hmac
import re


_ROLE_RE = re.compile(r"^[A-Za-z0-9_.:@-]{1,128}$")


def _secret_bytes(secret):
    if isinstance(secret, bytes):
        value = secret
    else:
        value = str(secret or "").encode("utf-8")
    if len(value) < 32:
        raise ValueError("AIOPS_HANDOFF_SECRET must contain at least 32 bytes")
    return value


def normalize_roles(roles):
    if isinstance(roles, str):
        values = roles.split(",") if roles else []
    else:
        values = list(roles or [])

    normalized = []
    for role in values:
        role = str(role).strip()
        if not role:
            continue
        if not _ROLE_RE.fullmatch(role):
            raise ValueError("invalid role name")
        normalized.append(role)
    return ",".join(sorted(set(normalized)))


def canonical_message(user, exp, nonce, roles=""):
    return "\n".join((
        "aiops-handoff-v1",
        str(user),
        str(int(exp)),
        str(nonce),
        normalize_roles(roles),
    )).encode("utf-8")


def sign_handoff(secret, user, exp, nonce, roles=""):
    return hmac.new(
        _secret_bytes(secret),
        canonical_message(user, exp, nonce, roles),
        hashlib.sha256,
    ).hexdigest()

