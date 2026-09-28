#!/usr/bin/env bash
set -eu
if [[ ${EUID:-$(id -u)} -ne 0 ]]; then
  echo "Run with sudo: sudo ./deploy/uninstall-services.sh" >&2
  exit 1
fi
units=(polysocial-tunnel.service polysocial-health.timer polysocial-backup.timer polysocial.service)
systemctl disable --now "${units[@]}" 2>/dev/null || true
for unit in polysocial.service polysocial-tunnel.service polysocial-health.service polysocial-health.timer polysocial-recover.service polysocial-backup.service polysocial-backup.timer; do
  rm -f "/etc/systemd/system/$unit"
done
systemctl daemon-reload
echo "Services removed. User data was preserved."
