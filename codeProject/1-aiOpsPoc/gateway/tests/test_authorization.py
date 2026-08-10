import os
import sys
import tempfile
import unittest


GATEWAY_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, GATEWAY_DIR)

from authorization import ALERT_RULE_APPLICATIONS, AuthorizationStore  # noqa: E402


class AuthorizationStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.store = AuthorizationStore(
            os.path.join(self.temp_dir.name, "authorization.sqlite3")
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_admin_can_access_any_task(self):
        task = {"payload": {"alertname": "unmapped-alert"}}
        self.assertTrue(self.store.user_access("admin").is_admin)
        self.assertTrue(self.store.can_access_task("admin", task))

    def test_user_can_only_access_granted_application(self):
        self.store.grant("Alice", "iwe")
        iwe_task = {"payload": {"alertname": "app_alert_iwe_Login_Failed"}}
        wecall_task = {
            "payload": {"alertname": "app_alert_wecall_Password_Verification_Failed"}
        }

        self.assertTrue(self.store.can_access_task("alice", iwe_task))
        self.assertFalse(self.store.can_access_task("alice", wecall_task))
        self.assertFalse(self.store.can_access_task("unassigned", iwe_task))

    def test_all_sixteen_rule_mappings_resolve_to_an_application(self):
        self.assertEqual(len(ALERT_RULE_APPLICATIONS), 16)
        for alert_name, application_code in ALERT_RULE_APPLICATIONS:
            task = {"payload": {"alertname": alert_name}}
            self.assertEqual(
                self.store.resolve_task_application(task), application_code
            )

    def test_service_alias_supports_future_rules_without_name_mapping(self):
        self.store.grant("bob", "pmt")
        task = {"payload": {"alertname": "new-pmt-alert", "service": "PMT for S&D"}}
        self.assertTrue(self.store.can_access_task("bob", task))


if __name__ == "__main__":
    unittest.main()
