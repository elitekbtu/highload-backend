#!/bin/sh
set -e
if [ ! -s "$PGDATA/PG_VERSION" ]; then
  mkdir -p "$PGDATA"
  until pg_basebackup -h "$PRIMARY_HOST" -U "$POSTGRES_USER" -D "$PGDATA" -R -X stream -c fast; do
    sleep 1
  done
  chmod 0700 "$PGDATA"
fi
exec postgres -c config_file=/etc/postgresql/postgresql.conf
