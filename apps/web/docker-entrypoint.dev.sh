#!/bin/sh
# Reinstall dependencies when package-lock.json changed since they were
# installed (node_modules lives in a Docker volume that survives rebuilds).
set -e

stamp=node_modules/.package-lock.sha256
if [ ! -f "$stamp" ] || ! sha256sum -c "$stamp" >/dev/null 2>&1; then
  echo "package-lock.json changed: running npm ci..."
  npm ci --no-audit --no-fund --ignore-scripts
  sha256sum package-lock.json > "$stamp"
fi

# Voice model for spoken answers (61 MB, downloaded once into public/models;
# afterwards only the checksum is verified).
node scripts/setup-voice-assets.mjs

exec "$@"
