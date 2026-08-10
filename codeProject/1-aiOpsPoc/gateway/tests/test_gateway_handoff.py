import os
import sys
import tempfile
import time
import unittest
from urllib.parse import urlencode


GATEWAY_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, GATEWAY_DIR)

import gateway  # noqa: E402
from handoff_auth import SQLiteNonceStore, sign_handoff  # noqa: E402


class GatewayHandoffIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.secret = "integration-secret-" + ("b" * 48)
        gateway.AIOPS_HANDOFF_SECRET = self.secret
        gateway.HANDOFF_NONCE_STORE = SQLiteNonceStore(
            os.path.join(self.temp_dir.name, "nonces.sqlite3")
        )
        gateway.AIOPS_HANDOFF_MAX_TTL_SECONDS = 120
        gateway.AIOPS_HANDOFF_CLOCK_SKEW_SECONDS = 5
        gateway.JWT_SECRET = "jwt-test-secret-" + ("c" * 48)
        gateway.AUTH_COOKIE_SECURE = False
        gateway.ALLOW_LEGACY_SPLUNK_USER = False
        gateway.ALLOW_SPLUNK_TOKEN_QUERY = False
        gateway.AIOPS_ALLOWED_ROLES = set()
        gateway.app.config.update(TESTING=True)
        self.client = gateway.app.test_client()

    def tearDown(self):
        self.temp_dir.cleanup()

    def _signed_path(self, user="john", nonce=None):
        now = int(time.time())
        exp = now + 90
        nonce = nonce or "1234567890abcdef1234567890abcdef"
        roles = "power,user"
        signature = sign_handoff(
            self.secret, user, exp, nonce, roles
        )
        return "/app/?" + urlencode({
            "v": "1",
            "user": user,
            "exp": exp,
            "nonce": nonce,
            "roles": roles,
            "sig": signature,
        })

    def test_valid_handoff_sets_cookie_and_opens_app(self):
        response = self.client.get(self._signed_path())
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/app/")
        self.assertIn("auth_token=", response.headers["Set-Cookie"])
        self.assertIn("HttpOnly", response.headers["Set-Cookie"])
        self.assertEqual(response.headers["Referrer-Policy"], "no-referrer")

        app_response = self.client.get("/app/")
        self.assertEqual(app_response.status_code, 200)

    def test_tampered_user_is_rejected(self):
        signed_path = self._signed_path(user="john").replace(
            "user=john", "user=admin"
        )
        response = self.client.get(signed_path)
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.get_json()["code"], "signature")

    def test_replayed_link_is_rejected(self):
        signed_path = self._signed_path()
        self.assertEqual(self.client.get(signed_path).status_code, 302)
        response = self.client.get(signed_path)
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.get_json()["code"], "replay")

    def test_legacy_username_parameter_is_disabled(self):
        response = self.client.get("/app/?splunk_user=admin")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.get_json()["code"], "legacy_disabled")

    def test_role_allow_list_is_enforced(self):
        gateway.AIOPS_ALLOWED_ROLES = {"admin"}
        response = self.client.get(self._signed_path())
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.get_json()["code"], "forbidden_role")


if __name__ == "__main__":
    unittest.main()
