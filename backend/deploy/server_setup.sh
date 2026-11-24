#!/usr/bin/env bash
# One-time setup on a fresh Ubuntu server, run as root:
#   bash server_setup.sh
# Installs Docker, adds swap (building torch needs it on a 2 GB server),
# opens the firewall for SSH/HTTP/HTTPS, and clones the repo to /opt/stylesync.
set -euo pipefail

if ! command -v docker >/dev/null; then
  curl -fsSL https://get.docker.com | sh
fi

if ! swapon --show | grep -q /swapfile; then
  fallocate -l 2G /swapfile
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

if [ ! -d /opt/stylesync ]; then
  git clone https://github.com/09lakshya/Style-Sync.git /opt/stylesync
fi
echo "Setup done."
