#!/usr/bin/env sh

echo -n "Setting up SSL/TLS certificates for secured (encrypted) comms with" \
        " pgAdmin web app... "

SRC_DIR=/run/secrets

# Copy SSL/TLS certificates to access pgAdmin website using HTTPS instead of HTTP
# and ensure they have the required ownership and permissions

cp ${SRC_DIR}/pgadmin-server.crt /certs/server.cert
cp ${SRC_DIR}/pgadmin-server.key /certs/server.key

chown pgadmin:root /certs/server.*

chmod 640 /certs/server.cert
chmod 600 /certs/server.key

echo "done"

echo -n "Setting up PassFile & SSL/TLS certificates for secured (encrypted)" \
        " comms with the PostgreSQL server... "

DST_DIR=/var/lib/pgadmin/storage/${PGADMIN_USER_CONFIG_DIR}
CERT_DIR=${DST_DIR}/.postgresql

# Copy .pgpass file and SSL/TLS certificates to its expected PATH and ensure
# they have the required ownership and permissions so that pgAdmin can
# automatically logging in in the PostgreSQL server as a valid user through
# SSL/TLS comms

# mkdir -p {DST_DIR}
mkdir -p ${CERT_DIR}

cp ${SRC_DIR}/pgadmin-passfile ${DST_DIR}/.pgpass

chown -R pgadmin:root ${DST_DIR}
chmod 600 ${DST_DIR}/.pgpass

cp ${SRC_DIR}/pgadmin-ca.crt ${CERT_DIR}/
cp ${SRC_DIR}/pgadmin-fmerinocasallo_*.crt ${CERT_DIR}/
cp ${SRC_DIR}/pgadmin-fmerinocasallo_*.key ${CERT_DIR}/

chmod 640 ${CERT_DIR}/*.crt
chmod 600 ${CERT_DIR}/*.key

echo "done"

sh /entrypoint.sh
