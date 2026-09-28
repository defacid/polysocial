#!/usr/bin/env bash
set -eu

project_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
config_file="$project_dir/install.env"
if [[ -f "$config_file" ]]; then
  while IFS='=' read -r key value; do
    [[ -z "$key" || "$key" == \#* ]] && continue
    case "$key" in
      POLYSOCIAL_SERVICE_USER|POLYSOCIAL_PUBLIC_ORIGIN|POLYSOCIAL_PORT|POLYSOCIAL_DATA_DIR)
        printf -v "$key" '%s' "$value"
        ;;
      *) echo "Ignoring unknown setting: $key" >&2 ;;
    esac
  done < "$config_file"
fi

service_user=${POLYSOCIAL_SERVICE_USER:-${SUDO_USER:-$(id -un)}}
public_origin=${POLYSOCIAL_PUBLIC_ORIGIN:-}
port=${POLYSOCIAL_PORT:-5500}
service_home=$(getent passwd "$service_user" | cut -d: -f6)
if [[ -z "$service_home" ]]; then
  echo "Could not determine the home directory for $service_user" >&2
  exit 1
fi
data_dir=${POLYSOCIAL_DATA_DIR:-$service_home/.local/share/polysocial}

if [[ ! "$port" =~ ^[0-9]{2,5}$ ]]; then
  echo "POLYSOCIAL_PORT must be a numeric TCP port" >&2
  exit 1
fi
for value in "$project_dir" "$service_user" "$public_origin" "$data_dir"; do
  if [[ "$value" == *'|'* || "$value" == *$'\n'* ]]; then
    echo "Configuration values may not contain | or newlines" >&2
    exit 1
  fi
done

render_unit() {
  local source=$1 target=$2
  sed -e "s|@PROJECT_DIR@|$project_dir|g" \
      -e "s|@SERVICE_USER@|$service_user|g" \
      -e "s|@PUBLIC_ORIGIN@|$public_origin|g" \
      -e "s|@PORT@|$port|g" \
      -e "s|@DATA_DIR@|$data_dir|g" \
      "$source" > "$target"
  chmod 0644 "$target"
}

install -d -o "$service_user" -g "$service_user" -m 0700 "$data_dir" "$data_dir/credentials" "$data_dir/cloudflared"
find "$data_dir" -type f -exec chmod 0600 {} +
chown -R "$service_user:$service_user" "$data_dir"
render_unit "$project_dir/deploy/polysocial.service" /etc/systemd/system/polysocial.service
render_unit "$project_dir/deploy/polysocial-tunnel.service" /etc/systemd/system/polysocial-tunnel.service
render_unit "$project_dir/deploy/polysocial-health.service" /etc/systemd/system/polysocial-health.service
install -m 0644 "$project_dir/deploy/polysocial-health.timer" /etc/systemd/system/polysocial-health.timer
install -m 0644 "$project_dir/deploy/polysocial-recover.service" /etc/systemd/system/polysocial-recover.service
systemctl daemon-reload
systemctl enable polysocial.service polysocial-health.timer
systemctl restart polysocial.service
if [[ -x "$project_dir/.local-tools/cloudflared" && -f "$data_dir/cloudflared/tunnel.env" ]]; then
  systemctl enable polysocial-tunnel.service
  systemctl restart polysocial-tunnel.service
else
  systemctl disable --now polysocial-tunnel.service 2>/dev/null || true
  echo "Cloudflare Tunnel not configured; installed local service only."
fi
systemctl restart polysocial-health.timer
systemctl --no-pager --full status polysocial.service polysocial-health.timer
