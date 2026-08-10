Create these files on the Splunk server; do not commit them:

1. hmac_secret
   The same random secret configured as AIOPS_HANDOFF_SECRET on the gateway.
   Use at least 32 random bytes (a 64-character hex value is recommended).

2. handoff_url
   Example: https://aiops.example.com/app/

3. ttl_seconds (optional)
   Default: 90. Supported range: 30-300 seconds.

4. splunkd_url (optional)
   Default: https://127.0.0.1:8089
