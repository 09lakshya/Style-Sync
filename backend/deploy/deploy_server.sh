#!/usr/bin/env bash
# Deploy (or redeploy) the backend from this machine to the server:
#   bash backend/deploy/deploy_server.sh [user@]<server-ip>     (user defaults to root)
# Copies backend/.env.production, pulls the latest main, rebuilds, restarts.
set -euo pipefail
TARGET="${1:?usage: deploy_server.sh [user@]<server-ip>}"
[[ "$TARGET" == *@* ]] || TARGET="root@$TARGET"
IP="${TARGET#*@}"
DOMAIN="${IP//./-}.sslip.io"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

scp -o StrictHostKeyChecking=accept-new "$ROOT/backend/.env.production" "$TARGET:/opt/stylesync/backend/.env.production"
ssh "$TARGET" "cd /opt/stylesync && git pull --ff-only && DOMAIN=$DOMAIN docker compose -f backend/deploy/docker-compose.yml up -d --build"

echo
echo "API:    https://$DOMAIN/api/v1"
echo "Health: https://$DOMAIN/health"
