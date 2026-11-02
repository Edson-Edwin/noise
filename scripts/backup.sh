#!/bin/sh
# Run from the project root. Does not delete or overwrite earlier backups.
set -eu
umask 077
mkdir -p backups
file="backups/noise-$(date -u +%Y%m%dT%H%M%SZ).dump"
test ! -e "$file"
trap 'rm -f "$file.partial"' EXIT HUP INT TERM
docker compose exec -T db pg_dump -U noise -d noise_monitor --format=custom --no-owner > "$file.partial"
mv "$file.partial" "$file"
echo "Backup saved to $file; copy it to private off-server storage."
