#!/usr/bin/env bash
# Deploy (or redeploy) the backend from this machine to the server:
#   bash backend/deploy/deploy_server.sh <server-ip>
# Copies backend/.env.production, pulls the latest main, rebuilds, restarts.
set -euo pipefail
IP="${1:?usage: deploy_server.sh <server-ip>}"
DOMAIN="${IP//./-}.sslip.io"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

scp -o StrictHostKeyChecking=accept-new "$ROOT/backend/.env.production" "root@$IP:/opt/stylesync/backend/.env.production"
ssh "root@$IP" "cd /opt/stylesync && git pull --ff-only && DOMAIN=$DOMAIN docker compose -f backend/deploy/docker-compose.yml up -d --build"

echo
echo "API:    https://$DOMAIN/api/v1"
echo "Health: https://$DOMAIN/health"
