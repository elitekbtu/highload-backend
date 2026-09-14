#!/bin/sh
set -eu
cd /app

if [ ! -f certs/cert.pem ] || [ ! -f certs/key.pem ]; then
  python scripts/key_generate.py
fi

hypercorn servers.app:app --config hypercorn.toml &

i=0
while [ "$i" -lt 30 ]; do
  if python -c "import socket; socket.create_connection(('127.0.0.1', 8443), 1).close()" 2>/dev/null; then
    break
  fi
  i=$((i + 1))
  sleep 0.2
done

exec caddy run --config Caddyfile --adapter caddyfile
