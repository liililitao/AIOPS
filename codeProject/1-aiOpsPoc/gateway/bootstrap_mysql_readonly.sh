#!/usr/bin/env bash
# Run once as root on the MySQL server. It asks for passwords interactively;
# neither password is stored in this script or printed by the migration tool.
set -euo pipefail

readonly CLIENT_IP="123.151.211.130"
readonly IMPORT_FILE="/home/adminboll/aiops_authorization_mysql.sql"

if [[ $(id -u) -ne 0 ]]; then
  echo "Run with: sudo bash $0" >&2
  exit 1
fi
if [[ ! -r "$IMPORT_FILE" ]]; then
  echo "Migration file not found: $IMPORT_FILE" >&2
  exit 1
fi

read -r -s -p "Set MySQL root password: " ROOT_PASSWORD
echo
read -r -s -p "Set read-only password for boll: " BOLL_PASSWORD
echo
if [[ ${#ROOT_PASSWORD} -lt 16 || ${#BOLL_PASSWORD} -lt 16 ]]; then
  echo "Each password must be at least 16 characters." >&2
  exit 1
fi
if [[ "$ROOT_PASSWORD" == *"'"* || "$BOLL_PASSWORD" == *"'"* ]]; then
  echo "Passwords must not contain a single quote (')." >&2
  exit 1
fi

mysql --protocol=socket < "$IMPORT_FILE"
mysql --protocol=socket <<SQL
ALTER USER 'root'@'localhost' IDENTIFIED WITH caching_sha2_password BY '${ROOT_PASSWORD}';
CREATE USER IF NOT EXISTS 'boll'@'${CLIENT_IP}' IDENTIFIED WITH caching_sha2_password BY '${BOLL_PASSWORD}';
ALTER USER 'boll'@'${CLIENT_IP}' IDENTIFIED WITH caching_sha2_password BY '${BOLL_PASSWORD}';
GRANT SELECT ON aiops.* TO 'boll'@'${CLIENT_IP}';
FLUSH PRIVILEGES;
SQL

if command -v firewall-cmd >/dev/null 2>&1 && firewall-cmd --state >/dev/null 2>&1; then
  firewall-cmd --permanent --add-rich-rule="rule family='ipv4' source address='${CLIENT_IP}' port port='3306' protocol='tcp' accept"
  firewall-cmd --reload
fi

echo "MySQL migration complete. boll is read-only and restricted to ${CLIENT_IP}:3306."
