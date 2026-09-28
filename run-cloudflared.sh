#!/usr/bin/env bash
set -eu
data_dir=${POLYSOCIAL_DATA_DIR:-$HOME/.local/share/polysocial}
. "$data_dir/cloudflared/tunnel.env"
tunnel_token="$CLOUDFLARE_TUNNEL_TOKEN"
unset CLOUDFLARE_TUNNEL_TOKEN
exec "$(dirname "$0")/.local-tools/cloudflared" tunnel --no-autoupdate run --token-file <(printf '%s' "$tunnel_token")
