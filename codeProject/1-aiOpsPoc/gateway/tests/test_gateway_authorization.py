import json
import os
import sys
import tempfile
import unittest
from unittest import mock


GATEWAY_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, GATEWAY_DIR)

import gateway  # noqa: E402
from authorization import AuthorizationStore  # noqa: E402


class _FakeRaw:
    def __init__(self, headers=None):
        self.headers = headers or {"Content-Type": "application/json"}


class _FakeResponse:
    def __init__(self, status_code, body):
        self.status_code = status_code
        self._body = body
        self.content = json.dumps(body).encode("utf-8")
        self.raw = _FakeRaw({
            "Content-Type": "application/json",
            "Content-Length": str(len(self.content)),
        })

    def json(self):
        return self._body


class GatewayAuthorizationTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        gateway.AUTHORIZATION_STORE = AuthorizationStore(
            os.path.join(self.temp_dir.name, "authorization.sqlite3")
        )
        gateway.AUTHORIZATION_STORE.grant("alice", "iwe")
        gateway.JWT_SECRET = "jwt-test-secret-" + ("a" * 48)
        gateway.AIOPS_ALLOWED_ROLES = set()
        gateway.app.config.update(TESTING=True)
        self.client = gateway.app.test_client()
        self.client.set_cookie("auth_token", gateway.create_jwt("alice", []))

    def tearDown(self):
        gateway.AUTHORIZATION_STORE = None
        self.temp_dir.cleanup()

    def test_task_list_hides_unassigned_applications(self):
        upstream = _FakeResponse(200, {
            "count": 2,
            "items": [
                {
                    "id": "iwe-task",
                    "payload": {"alertname": "app_alert_iwe_Login_Failed"},
                },
                {
                    "id": "wecall-task",
                    "payload": {
                        "alertname": "app_alert_wecall_Password_Verification_Failed"
                    },
                },
            ],
        })

        with mock.patch.object(gateway.requests, "request", return_value=upstream) as mocked:
            response = self.client.get("/api/v1/incidents/tasks?limit=20")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["count"], 1)
        self.assertEqual(response.get_json()["items"][0]["id"], "iwe-task")
        self.assertEqual(
            mocked.call_args.kwargs["headers"]["X-AIOPS-Authenticated-User"], "alice"
        )

    def test_task_detail_is_hidden_when_application_is_not_granted(self):
        upstream = _FakeResponse(200, {
            "id": "wecall-task",
            "payload": {
                "alertname": "app_alert_wecall_Password_Verification_Failed"
            },
        })

        with mock.patch.object(gateway.requests, "get", return_value=upstream):
            response = self.client.get("/api/v1/incidents/tasks/wecall-task")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_json()["code"], "alert_not_found")


if __name__ == "__main__":
    unittest.main()
