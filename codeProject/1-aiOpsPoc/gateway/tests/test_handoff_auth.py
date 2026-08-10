import importlib
import os
import sys
import tempfile
import unittest
from unittest import mock
from urllib.parse import parse_qs, urlsplit


GATEWAY_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_DIR = os.path.dirname(GATEWAY_DIR)
SPLUNK_BIN_DIR = os.path.join(
    PROJECT_DIR, "splunk_app", "aiops_handoff", "bin"
)
sys.path.insert(0, GATEWAY_DIR)
sys.path.insert(0, SPLUNK_BIN_DIR)

from handoff_auth import (  # noqa: E402
    HandoffVerificationError,
    SQLiteNonceStore,
    sign_handoff,
    verify_handoff,
)


class HandoffAuthTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.store = SQLiteNonceStore(
            os.path.join(self.temp_dir.name, "nonces.sqlite3")
        )
        self.secret = "test-secret-" + ("a" * 52)
        self.now = 1_718_001_200

    def tearDown(self):
        self.temp_dir.cleanup()

    def _parameters(self, **overrides):
        values = {
            "version": "1",
            "user": "john",
            "exp": str(self.now + 90),
            "nonce": "0123456789abcdef0123456789abcdef",
            "roles": "user,power",
        }
        values.update(overrides)
        values["signature"] = sign_handoff(
            self.secret,
            values["user"],
            values["exp"],
            values["nonce"],
            values["roles"],
        )
        return values

    def _verify(self, parameters):
        return verify_handoff(
            secret=self.secret,
            now=self.now,
            max_ttl_seconds=120,
            clock_skew_seconds=5,
            nonce_store=self.store,
            **parameters,
        )

    def test_valid_signature_returns_user_and_normalized_roles(self):
        verified = self._verify(self._parameters(roles="user,power,user"))
        self.assertEqual(verified.user, "john")
        self.assertEqual(verified.roles, ("power", "user"))

    def test_modified_user_is_rejected(self):
        parameters = self._parameters()
        parameters["user"] = "admin"
        with self.assertRaises(HandoffVerificationError) as raised:
            self._verify(parameters)
        self.assertEqual(raised.exception.code, "signature")

    def test_expired_link_is_rejected(self):
        parameters = self._parameters(exp=str(self.now - 10))
        with self.assertRaises(HandoffVerificationError) as raised:
            self._verify(parameters)
        self.assertEqual(raised.exception.code, "expired")

    def test_far_future_expiration_is_rejected(self):
        parameters = self._parameters(exp=str(self.now + 600))
        with self.assertRaises(HandoffVerificationError) as raised:
            self._verify(parameters)
        self.assertEqual(raised.exception.code, "exp")

    def test_nonce_cannot_be_replayed(self):
        parameters = self._parameters()
        self._verify(parameters)
        with self.assertRaises(HandoffVerificationError) as raised:
            self._verify(parameters)
        self.assertEqual(raised.exception.code, "replay")

    def test_splunk_signer_and_gateway_use_same_protocol(self):
        splunk_protocol = importlib.import_module("aiops_handoff_protocol")
        expected = sign_handoff(
            self.secret,
            "alice@example.com",
            self.now + 90,
            "fedcba9876543210fedcba9876543210",
            ["user", "power"],
        )
        actual = splunk_protocol.sign_handoff(
            self.secret,
            "alice@example.com",
            self.now + 90,
            "fedcba9876543210fedcba9876543210",
            ["power", "user"],
        )
        self.assertEqual(actual, expected)

    def test_splunk_command_builds_gateway_compatible_url(self):
        command = importlib.import_module("aiops_sign_url")
        original_token_hex = command.secrets.token_hex
        command.secrets.token_hex = lambda _: "abcdef0123456789abcdef0123456789"
        try:
            signed_url, _ = command.build_signed_url(
                base_url="https://aiops.example.com/app/",
                secret=self.secret,
                username="alice@example.com",
                roles=["user", "power"],
                now=self.now,
                ttl_seconds=90,
            )
        finally:
            command.secrets.token_hex = original_token_hex

        parsed = urlsplit(signed_url)
        query = {key: values[0] for key, values in parse_qs(parsed.query).items()}
        verified = self._verify({
            "version": query["v"],
            "user": query["user"],
            "exp": query["exp"],
            "nonce": query["nonce"],
            "roles": query["roles"],
            "signature": query["sig"],
        })
        self.assertEqual(verified.user, "alice@example.com")
        self.assertEqual(verified.roles, ("power", "user"))

    def test_splunk_legacy_auth_string_is_supported(self):
        command = importlib.import_module("aiops_sign_url")
        username, session_key = command._parse_auth_string(
            "&lt;auth&gt;&lt;username&gt;john&lt;/username&gt;"
            "&lt;authToken&gt;session-123&lt;/authToken&gt;&lt;/auth&gt;"
        )
        self.assertEqual(username, "john")
        self.assertEqual(session_key, "session-123")

    def test_splunk_auth_string_can_query_current_context(self):
        command = importlib.import_module("aiops_sign_url")

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *_):
                return False

            def read(self):
                return (
                    b'{"entry":[{"content":{"username":"john",'
                    b'"roles":["user","power"]}}]}'
                )

        settings = {
            "authString": (
                "<auth><username>john</username>"
                "<authToken>session-123</authToken></auth>"
            )
        }
        with mock.patch.object(
            command.urllib.request, "urlopen", return_value=FakeResponse()
        ) as urlopen:
            username, roles = command._load_current_context(settings)

        self.assertEqual(username, "john")
        self.assertEqual(roles, ["user", "power"])
        requested_url = urlopen.call_args.args[0].full_url
        self.assertTrue(requested_url.startswith("https://127.0.0.1:8089/"))


if __name__ == "__main__":
    unittest.main()
