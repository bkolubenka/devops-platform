#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="/usr/local/lib/devops-platform-ddns"
SYSTEMD_DIR="/etc/systemd/system"
ENV_FILE="/etc/default/cloudflare-ddns"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run this installer as root or with sudo."
  exit 1
fi

install -d -m 0755 "$INSTALL_DIR"
install -m 0644 "$SCRIPT_DIR/cloudflare_ddns.py" "$INSTALL_DIR/cloudflare_ddns.py"
install -m 0644 "$SCRIPT_DIR/cloudflare-ddns.service" "$SYSTEMD_DIR/cloudflare-ddns.service"
install -m 0644 "$SCRIPT_DIR/cloudflare-ddns.timer" "$SYSTEMD_DIR/cloudflare-ddns.timer"

if [[ ! -f "$ENV_FILE" ]]; then
  install -m 0600 "$SCRIPT_DIR/cloudflare-ddns.env.example" "$ENV_FILE"
  echo "Created $ENV_FILE from the example file. Fill in CF_API_TOKEN before enabling the timer."
fi

systemctl daemon-reload

if grep -Eq '^CF_API_TOKEN=[^[:space:]]+' "$ENV_FILE"; then
  systemctl enable --now cloudflare-ddns.timer
  echo "Cloudflare DDNS timer enabled and started."
else
  echo "Edit $ENV_FILE, then run: sudo systemctl enable --now cloudflare-ddns.timer"
fi
