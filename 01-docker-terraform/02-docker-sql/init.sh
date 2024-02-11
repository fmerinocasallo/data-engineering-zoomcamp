#!/usr/bin/env bash
echo -n "Setting up postgres..."
cp /docker-entrypoint-initdb.d/{*.conf,server.*,client.*,root.crt} /var/lib/postgresql/data/
pg_ctl reload
echo "done"
