"""Signed Splunk handoff validation and browser session helpers."""

import base64
import binascii
import hashlib
import hmac
import json
import os
import re
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path


PROTOCOL_VERSION = "1"
_NONCE_RE = re.compile(r"^[0-9a-f]{32,64}$")
_SIGNATURE_RE = re.compile(r"^[0-9a-f]{64}$")
_ROLE_RE = re.compile(r"^[A-Za-z0-9_.:@-]{1,128}$")


class HandoffVerificationError(ValueError):
    """The signed handoff URL cannot be trusted."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class AuthenticatedUser:
    username: str
    roles: tuple[str, ...]


class SQLiteNonceStore:
    """Atomically prevents a signed handoff URL from being used twice."""

    def __init__(self, database_path: Path):
        self.database_path = Path(database_path)

    def consume(self, nonce: str, expires_at: int, now: int) -> bool:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.database_path, timeout=5)
        try:
            connection.execute("PRAGMA busy_timeout = 5000")
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "CREATE TABLE IF NOT EXISTS used_nonces "
                "(nonce TEXT PRIMARY KEY, expires_at INTEGER NOT NULL)"
            )
            connection.execute("DELETE FROM used_nonces WHERE expires_at < ?", (now,))
            try:
                connection.execute(
                    "INSERT INTO used_nonces (nonce, expires_at) VALUES (?, ?)",
                    (nonce, expires_at),
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
    secret: str,
    version: str,
    user: str,
    exp: str,
    nonce: str,
    signature: str,
    roles: str,
    max_ttl_seconds: int,
    clock_skew_seconds: int,
    nonce_store: SQLiteNonceStore,
) -> AuthenticatedUser:
    """Verify the byte-for-byte HMAC protocol used by aiopssignurl."""
    if version != PROTOCOL_VERSION:
        raise HandoffVerificationError("version", "unsupported handoff version")
    if not user or user != user.strip() or len(user) > 256:
        raise HandoffVerificationError("user", "invalid handoff user")
    if any(ord(char) < 32 or ord(char) == 127 for char in user):
        raise HandoffVerificationError("user", "invalid handoff user")
    if not _NONCE_RE.fullmatch(nonce or ""):
        raise HandoffVerificationError("nonce", "invalid nonce")
    if not _SIGNATURE_RE.fullmatch(signature or ""):
        raise HandoffVerificationError("signature", "invalid signature format")

    try:
        expires_at = int(exp)
    except (TypeError, ValueError) as exc:
        raise HandoffVerificationError("exp", "invalid expiration timestamp") from exc

    now = int(time.time())
    skew = max(0, int(clock_skew_seconds))
    max_ttl = max(1, int(max_ttl_seconds))
    if now > expires_at + skew:
        raise HandoffVerificationError("expired", "handoff link has expired")
    if expires_at - now > max_ttl + skew:
        raise HandoffVerificationError("exp", "expiration is too far in the future")

    try:
        normalized_roles = normalize_roles(roles)
        expected = sign_handoff(secret, user, expires_at, nonce, normalized_roles)
    except ValueError as exc:
        raise HandoffVerificationError("configuration", str(exc)) from exc
    if not hmac.compare_digest(expected, signature):
        raise HandoffVerificationError("signature", "signature mismatch")
    if not nonce_store.consume(nonce, expires_at + skew, now):
        raise HandoffVerificationError("replay", "handoff link was already used")

    return AuthenticatedUser(
        username=user,
        roles=tuple(normalized_roles.split(",")) if normalized_roles else tuple(),
    )


def sign_handoff(secret: str, user: str, exp: int, nonce: str, roles: str = "") -> str:
    return hmac.new(
        _secret_bytes(secret),
        _canonical_message(user, exp, nonce, roles),
        hashlib.sha256,
    ).hexdigest()


def create_session_token(secret: str, user: AuthenticatedUser, hours: int) -> str:
    """Create a tamper-proof cookie value; permissions remain server-side."""
    payload = {
        "u": user.username,
        "r": list(user.roles),
        "exp": int(time.time()) + max(1, int(hours)) * 3600,
    }
    encoded = _base64url(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signature = hmac.new(_secret_bytes(secret), encoded.encode("ascii"), hashlib.sha256).hexdigest()
    return f"{encoded}.{signature}"


def read_session_token(secret: str, token: str | None) -> AuthenticatedUser | None:
    if not token or "." not in token:
        return None
    encoded, signature = token.rsplit(".", 1)
    if not _SIGNATURE_RE.fullmatch(signature):
        return None
    expected = hmac.new(_secret_bytes(secret), encoded.encode("ascii"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        return None
    try:
        payload = json.loads(_base64url_decode(encoded))
        expires_at = int(payload.get("exp", 0))
        username = str(payload.get("u", ""))
        roles = tuple(normalize_roles(payload.get("r", [])).split(","))
    except (ValueError, TypeError, UnicodeError, binascii.Error, json.JSONDecodeError):
        return None
    if expires_at < int(time.time()) or not username:
        return None
    return AuthenticatedUser(username=username, roles=roles)


def normalize_roles(roles: str | list[str] | tuple[str, ...]) -> str:
    values = roles.split(",") if isinstance(roles, str) else list(roles or [])
    normalized = []
    for role in values:
        value = str(role).strip()
        if not value:
            continue
        if not _ROLE_RE.fullmatch(value):
            raise ValueError("invalid role name")
        normalized.append(value)
    return ",".join(sorted(set(normalized)))


def _canonical_message(user: str, exp: int, nonce: str, roles: str) -> bytes:
    return "\n".join((
        "aiops-handoff-v1",
        str(user),
        str(int(exp)),
        str(nonce),
        normalize_roles(roles),
    )).encode("utf-8")


def _secret_bytes(secret: str) -> bytes:
    value = str(secret or "").encode("utf-8")
    if len(value) < 32:
        raise ValueError("secret must contain at least 32 bytes")
    return value


def _base64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _base64url_decode(value: str) -> bytes:
    padded = value + "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(padded.encode("ascii"))
