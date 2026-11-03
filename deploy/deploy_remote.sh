#!/usr/bin/env bash
# Deploy the four-tab ops app (Dockerfile.ops) to the platform's NHN Cloud server behind Caddy.
#
#   deploy/deploy_remote.sh <host-ip> <path/to/key.pem> [ssh-user]
#
# 1. builds the context locally (deploy/build_context.py: HEAD + trimmed HRFCO series),
# 2. copies it and installs Docker on the server when missing,
# 3. builds Dockerfile.ops there as floodops:ops-<commit>-relay,
# 4. keeps the running container as floodops-prev (stopped, restart=no) and starts the new one on 127.0.0.1:8000,
# 5. rolls back to floodops-prev when /health does not answer within two minutes.
#
# Caddy on the server terminates HTTPS for floodops.duckdns.org and proxies to 127.0.0.1:8000; this script
# does not touch it. API keys never leave this machine through the script: put them once in /etc/floodops.env
# on the server (HRFCO_API_KEY, HRFCO_API_BASE, KMA_API_HUB_KEY, ...; root-only, `chmod 600`).
set -euo pipefail

HOST="${1:?host ip}"
KEY="${2:?path to .pem}"
USER_NAME="${3:-ubuntu}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TAG="floodops:ops-$(git -C "$ROOT" rev-parse --short HEAD)-relay"
CONTEXT="$(mktemp -d)/floodops-deploy-context.tar.gz"
SSH=(ssh -i "$KEY" -o StrictHostKeyChecking=accept-new "$USER_NAME@$HOST")

python "$ROOT/deploy/build_context.py" "$CONTEXT"
scp -i "$KEY" -o StrictHostKeyChecking=accept-new "$CONTEXT" "$USER_NAME@$HOST:/tmp/floodops-deploy-context.tar.gz"

"${SSH[@]}" "TAG='$TAG' bash -s" <<'REMOTE'
set -euo pipefail
if ! command -v docker >/dev/null; then
  curl -fsSL https://get.docker.com | sudo sh
fi
sudo test -f /etc/floodops.env || { echo "missing /etc/floodops.env (HRFCO_API_KEY, KMA_API_HUB_KEY ...)"; exit 1; }
rm -rf ~/floodops-build && mkdir -p ~/floodops-build && tar -xzf /tmp/floodops-deploy-context.tar.gz -C ~/floodops-build
sudo docker build -q -f ~/floodops-build/Dockerfile.ops -t "$TAG" ~/floodops-build

sudo docker rm -f floodops-prev >/dev/null 2>&1 || true
if sudo docker inspect floodops >/dev/null 2>&1; then
  sudo docker stop floodops >/dev/null
  sudo docker rename floodops floodops-prev
  sudo docker update --restart=no floodops-prev >/dev/null
fi
sudo docker run -d --name floodops --restart unless-stopped -p 127.0.0.1:8000:8000 --env-file /etc/floodops.env \
  -v floodops-local:/app/data/local -v floodops-interim:/app/data/interim "$TAG" >/dev/null

for i in $(seq 1 60); do curl -fsS -m 5 http://127.0.0.1:8000/health >/dev/null 2>&1 && break; sleep 2; done
if ! curl -fsS -m 5 http://127.0.0.1:8000/health >/dev/null 2>&1; then
  echo "health failed, rolling back to floodops-prev"
  sudo docker logs --tail 30 floodops || true
  sudo docker rm -f floodops >/dev/null
  if sudo docker inspect floodops-prev >/dev/null 2>&1; then
    sudo docker rename floodops-prev floodops
    sudo docker update --restart=unless-stopped floodops >/dev/null
    sudo docker start floodops >/dev/null
  fi
  exit 1
fi
for path in "/health" "/api/twin/mode" "/api/watch/facility-risk?limit=1" "/api/watch/validation-cases" "/public/watch-board-integration.html"; do
  printf '%-40s %s\n' "$path" "$(curl -s -o /dev/null -w '%{http_code}' -m 60 "http://127.0.0.1:8000$path")"
done
sudo docker ps --format '{{.Names}} | {{.Image}} | {{.Status}}'
REMOTE
