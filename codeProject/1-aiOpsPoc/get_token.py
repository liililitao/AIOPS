import os

import requests
import urllib3
urllib3.disable_warnings()
r = requests.post(
    'https://127.0.0.1:8089/services/auth/login',
    data={"username": os.getenv("SPLUNK_USERNAME", ""), "password": os.getenv("SPLUNK_PASSWORD", "")},
    verify=False
)
print(r.text[:500] if r.status_code != 200 else r.text)
