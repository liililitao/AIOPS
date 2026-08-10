#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AIOps handoff HMAC protocol and replay protection."""

import hashlib
import hmac
import os
import re
import sqlite3
from dataclasses import dataclass


PROTOCOL_VERSION = "1"
_NONCE_RE = re.compile(r"^[0-9a-f]{32,64}$")
_SIGNATURE_RE = re.compile(r"^[0-9a-f]{64}$")
_ROLE_RE = re.compile(r"^[A-Za-z0-9_.:@-]{1,128}$")


class HandoffVerificationError(ValueError):
    """Raised when a signed handoff request is invalid or cannot be verified."""

    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class VerifiedHandoff:
    user: str
    roles: tuple
    exp: int
    nonce: str


def _secret_bytes(secret):
    if isinstance(secret, bytes):
        value = secret
    else:
        value = str(secret or "").encode("utf-8")
    if len(value) < 32:
        raise ValueError("AIOPS_HANDOFF_SECRET must contain at least 32 bytes")
    return value


def normalize_roles(roles):
    """Return a stable, validated comma-separated role list."""
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
    """Build the byte-for-byte message signed by Splunk and the gateway."""
    normalized_roles = normalize_roles(roles)
    return "\n".join((
        "aiops-handoff-v1",
        str(user),
        str(int(exp)),
        str(nonce),
        normalized_roles,
    )).encode("utf-8")


def sign_handoff(secret, user, exp, nonce, roles=""):
    """Create a lowercase hex HMAC-SHA256 signature."""
    return hmac.new(
        _secret_bytes(secret),
        canonical_message(user, exp, nonce, roles),
        hashlib.sha256,
    ).hexdigest()


class SQLiteNonceStore:
    """One-time nonce store shared by gateway workers on the same host."""

    def __init__(self, database_path):
        self.database_path = os.path.abspath(database_path)

    def consume(self, nonce, expires_at, now):
        """Atomically store a nonce. Return False if it was already consumed."""
        parent = os.path.dirname(self.database_path)
        if parent:
            os.makedirs(parent, exist_ok=True)

        connection = sqlite3.connect(self.database_path, timeout=5)
        try:
            connection.execute("PRAGMA busy_timeout = 5000")
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "CREATE TABLE IF NOT EXISTS used_nonces ("
                "nonce TEXT PRIMARY KEY, expires_at INTEGER NOT NULL)"
            )
            connection.execute(
                "DELETE FROM used_nonces WHERE expires_at < ?", (int(now),)
            )
            try:
                connection.execute(
                    "INSERT INTO used_nonces (nonce, expires_at) VALUES (?, ?)",
                    (nonce, int(expires_at)),
                )
            except sqlite3.IntegrityError:
                connection.rollback()
                return False
            connection.commit()
            return True
        finally:
            connection.close()


def verify_handoff(
    *,
    secret,
    version,
    user,
    exp,
    nonce,
    signature,
    roles="",
    now,
    max_ttl_seconds,
    clock_skew_seconds,
    nonce_store,
):
    """Validate a signed handoff and consume its nonce exactly once."""
    if version != PROTOCOL_VERSION:
        raise HandoffVerificationError("version", "unsupported handoff version")

    if not user or user != user.strip() or len(user) > 256:
        raise HandoffVerificationError("user", "invalid handoff user")
    if any(ord(char) < 32 or ord(char) == 127 for char in user):
        raise HandoffVerificationError("user", "invalid handoff user")

    try:
        exp_value = int(exp)
    except (TypeError, ValueError):
        raise HandoffVerificationError("exp", "invalid expiration timestamp")

    now_value = int(now)
    skew = max(0, int(clock_skew_seconds))
    max_ttl = max(1, int(max_ttl_seconds))
    if now_value > exp_value + skew:
        raise HandoffVerificationError("expired", "handoff link has expired")
    if exp_value - now_value > max_ttl + skew:
        raise HandoffVerificationError("exp", "expiration is too far in the future")

    if not _NONCE_RE.fullmatch(nonce or ""):
        raise HandoffVerificationError("nonce", "invalid nonce")
    if not _SIGNATURE_RE.fullmatch(signature or ""):
        raise HandoffVerificationError("signature", "invalid signature format")

    try:
        normalized_roles = normalize_roles(roles)
        expected = sign_handoff(secret, user, exp_value, nonce, normalized_roles)
    except ValueError as exc:
        raise HandoffVerificationError("configuration", str(exc))

    if not hmac.compare_digest(expected, signature):
        raise HandoffVerificationError("signature", "signature mismatch")

    try:
        consumed = nonce_store.consume(nonce, exp_value + skew, now_value)
    except (OSError, sqlite3.Error) as exc:
        raise HandoffVerificationError(
            "nonce_store", f"nonce store unavailable: {exc}"
        )
    if not consumed:
        raise HandoffVerificationError("replay", "handoff link was already used")

    role_values = tuple(normalized_roles.split(",")) if normalized_roles else tuple()
    return VerifiedHandoff(
        user=user,
        roles=role_values,
        exp=exp_value,
        nonce=nonce,
    )
