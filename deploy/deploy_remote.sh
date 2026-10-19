#!/usr/bin/env bash
# Deploy the watch-board image to a fresh Ubuntu server (e.g. the platform's NHN Cloud instance).
#
#   deploy/deploy_remote.sh <host-ip> <path/to/key.pem> [ssh-user]
#
# 1. builds the context locally (deploy/build_context.py: HEAD + trimmed HRFCO series),
# 2. copies it and installs Docker on the server when missing,
# 3. builds Dockerfile.deploy there and (re)starts the container on port 80,
# 4. smoke-tests /api/health, /api/watch/facility-risk and /api/watch/validation-cases.
#
# API keys never leave this machine through the script: put them once in /etc/floodops.env on the server
# (HRFCO_API_KEY, KMA_API_HUB_KEY, ...; root-only, `chmod 600`). The container reads that file with --env-file.
set -euo pipefail

HOST="${1:?host ip}"
KEY="${2:?path to .pem}"
USER_NAME="${3:-ubuntu}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CONTEXT="$(mktemp -d)/floodops-deploy-context.tar.gz"
SSH=(ssh -i "$KEY" -o StrictHostKeyChecking=accept-new "$USER_NAME@$HOST")

python "$ROOT/deploy/build_context.py" "$CONTEXT"
scp -i "$KEY" -o StrictHostKeyChecking=accept-new "$CONTEXT" "$USER_NAME@$HOST:/tmp/floodops-deploy-context.tar.gz"

"${SSH[@]}" 'bash -s' <<'REMOTE'
set -euo pipefail
if ! command -v docker >/dev/null; then
  curl -fsSL https://get.docker.com | sudo sh
fi
sudo test -f /etc/floodops.env || { echo "missing /etc/floodops.env (HRFCO_API_KEY, KMA_API_HUB_KEY ...)"; exit 1; }
rm -rf ~/floodops-build && mkdir -p ~/floodops-build && tar -xzf /tmp/floodops-deploy-context.tar.gz -C ~/floodops-build
sudo docker build -f ~/floodops-build/Dockerfile.deploy -t floodops:deploy ~/floodops-build
sudo docker rm -f floodops >/dev/null 2>&1 || true
sudo docker run -d --name floodops --restart unless-stopped -p 80:8000 --env-file /etc/floodops.env \
  -v floodops-local:/app/data/local -v floodops-interim:/app/data/interim floodops:deploy
for i in $(seq 1 60); do curl -fsS http://127.0.0.1/api/health >/dev/null 2>&1 && break; sleep 2; done
REMOTE

for path in "/api/health" "/api/watch/facility-risk?limit=1" "/api/watch/validation-cases" "/watch-board-integration.html"; do
  printf '%-40s %s\n' "$path" "$(curl -s -o /dev/null -w '%{http_code}' -m 60 "http://$HOST$path")"
done
