# Using PostgreSQL to store NYC Taxi data

## Table of contents
1. [`PostgreSQL` Server (`pg-server`) as a Service](#pg-server)
2. [`pgAdmin` Service](#pgadmin)
3. [Securing communications from and to the PostgreSQL server](#secure-comms)
    1. [:key: SCRAM-SHA-256 password authentication](#scram-auth)
        1. [Update PostgreSQL configuration to enforce hashed-based authentication](#pg-conf-scram-auth)
    2. [:closed_lock_with_key: SSL/TLS encryption for communications with the PostgreSQL server](#pg-server-tls)
        1. [Create a self-signed root certificate authority (CA)](#ca-cert)
        2. [Create a server certificate signed by the new CA](#server-cert)
        3. [Create client certificates signed by the new CA](#client-cert)
        4. [Update PostgreSQL configuration to enforce certificate-based TLS authentication](#pg-conf-tls)
    3. [:closed_lock_with_key: Setting up `pgAdmin` to use SSL/TLS communications](#pgadmin-tls)
        1. [Setting up SSL/TLS in `pgAdmin`](#ssl-pgadmin)
        2. [Setting up SSL/TLS certificates location, ownership, and permissions](#pgadmin-loc-own-perm)
        3. [Setting up `pgAdmin` environment variables](#pgadmin-vars)
    4. [:file_folder: Initialize `PostgreSQL` database](#init-sql)

<div id="pg-server"></div>

## `PostgreSQL` Server (`pg-server`) as a Service

We use `Docker Compose` to define the `postgres-server` service and the required associated resources (i.e., `configs`, `volumes`, `secrets`, and `networks`).

#### :page_facing_up: FILE `./docker-compose.yml`:
```
name: de_zoomcamp
services:
  pg-server:
    image: postgres:alpine
    container_name: "pg-server"
    user: "postgres:postgres"
    restart: unless-stopped
    command: postgres -c config_file=/etc/postgresql/postgresql.conf
    configs:
      - source: pg-init_db.sql
        target: /docker-entrypoint-initdb.d/init-db.sql
      - source: pg-entrypoint.sh
        target: /docker-entrypoint-initdb.d/entrypoint.sh
      - source: pg-pg_hba.conf
        target: /etc/postgresql/pg_hba.conf
      - source: pg-postgresql.conf
        target: /etc/postgresql/postgresql.conf
    environment:
      POSTGRES_USER_FILE: /run/secrets/pg-user
      POSTGRES_PASSWORD_FILE: /run/secrets/pg-password
      POSTGRES_DB_FILE: /run/secrets/pg-db
    secrets:
      - pg-user
      - pg-password
      - pg-db
      - pg-ca.crt
      - pg-server.crt
      - pg-server.key
    volumes:
      - type: volume
        source: pg-data
        target: /var/lib/postgresql/data
    ports:
      - mode: ingress
        target: ${POSTGRES_PORT:-5432}
        published: ${POSTGRES_PORT:-5432}
        protocol: tcp
    networks:
      postgres_net:
        ipv4_address: ${POSTGRES_IP_ADDR:-172.19.0.1}
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -p ${POSTGRES_PORT}"]
      interval: 10s
      timeout: 5s
      retries: 3

  [...]

configs:
  pg-init_db.sql:
    file: ./pg-server/init/init-db.sql
  pg-entrypoint.sh:
    file: ./pg-server/init/entrypoint.sh
  pg-pg_hba.conf:
    file: ./pg-server/conf/pg_hba.conf
  pg-postgresql.conf:
    file: ./pg-server/conf/postgresql.conf
  [...]

volumes:
  pg-data:
  [...]

secrets:
  pg-user:
    file: ./pg-server/conf/pg_user
  pg-password:
    file: ./pg-server/conf/pg_password
  pg-db:
    file: ./pg-server/conf/pg_db
  pg-ca.crt:
    file: ./pg-server/certs/ca/client/client-ca.crt
  pg-server.crt:
    file: ./pg-server/certs/server/server.crt
  pg-server.key:
    file: ./pg-server/certs/server/server.key
  [...]

networks:
  postgres_net:
    driver: bridge
    ipam:
      config:
        - subnet: 172.19.0.0/24
          gateway: 172.19.0.1
```

It is worth noticing that:
- We use a non-root user (`postgres`) to limit root access [^1], which is crucial for enhancing security by minimizing potential attack surfaces.
- We use `Docker configs` to store non-sensitive information outside a service's image or running containers. In this case, such non-sensitive information includes `PostgreSQL` configuration files `pg_hba.conf` and `postgresql.conf`, and initilizing scripts `init-db.sql` and `entrypoint.sh`.
- We use `Docker secrets` to securely transfer sensitive data, such as user credentials (e.g., `pg-user` and `pg-password`) and certificates (e.g., `pg-server.crt` and `pg-server.key`), to specific `Docker containers`.
- We create a `named volume` (`pg-data`) to allow for persistent data in `/var/lib/postgresql/data`.
- We create a `user-defined bridge` network [^2] named `postgres_net`, providing a scoped network in which only containers attached to that network are able to communicate.
- We assign a static IP address to the `pg-server` service (`172.19.0.70`). Beware of assigning static IP addresses to `Docker containers` if more than one are running the very same `Docker image`.
- We define the following file `.env`, with additional environment variables for the `pg-server` service:

#### :page_facing_up: FILE `./.env`:
```
# PostgreSQL settings
POSTGRES_IP_ADDR=172.19.0.70
POSTGRES_PORT=10864

[...]
```
- We will use port `10864` instead of the default `5432` (security by obscurity [^3]).
Therefore, we update the `./pgconf/postgresql.conf` file to effectively change `PostgreSQL` port:

#### :page_facing_up: FILE `./pgconf/postgresql.conf`:
```
port = 10864
```

<div id="pgadmin"></div>

## `pgAdmin` Service

We use `Docker Compose` to define the `pgadmin` service and the required associated resources (i.e., `configs`, `volumes`, `secrets`, and `networks`).

#### :page_facing_up: FILE `./docker-compose.yml`:
```
name: de_zoomcamp
services:
  [...]

  pgadmin:
    container_name: "pgadmin"
    restart: unless-stopped
    build:
      context: ./pgadmin
      dockerfile: pgadmin-1.Dockerfile
    entrypoint: >
      /bin/sh -c "
        /pgadmin4/entrypoint.sh
      "
    configs:
      - source: pgadmin-entrypoint.sh
        target: /pgadmin4/entrypoint.sh
      - source: pgadmin-servers.json
        target: /pgadmin4/servers.json
    environment:
      - PGADMIN_DEFAULT_EMAIL=${PGADMIN_DEFAULT_EMAIL:-user@pgadmin.com}
      - PGADMIN_DEFAULT_PASSWORD=${PGADMIN_DEFAULT_PASSWORD:-user_password}
      - PGADMIN_USER_CONFIG_DIR=${PGADMIN_USER_CONFIG_DIR:-user_pgadmin.com}
      - PGADMIN_LISTEN_PORT=${PGADMIN_LISTEN_PORT:-80}
      - PGADMIN_SERVER_JSON_FILE=${PGADMIN_SERVER_JSON_FILE}
      - PGADMIN_ENABLE_TLS=${PGADMIN_ENABLE_TLS:-}
    secrets:
      - pgadmin-ca.crt
      - pgadmin-server.crt
      - pgadmin-server.key
      - pgadmin-fmerinocasallo_writer.crt
      - pgadmin-fmerinocasallo_writer.key
      - pgadmin-fmerinocasallo_reader.crt
      - pgadmin-fmerinocasallo_reader.key
      - pgadmin-passfile
    volumes:
      - type: volume
        source: pgadmin-data
        target: /var/lib/pgadmin
    ports:
      - mode: ingress
        target: ${PGADMIN_LISTEN_PORT:-80}
        published: ${PGADMIN_LISTEN_PORT:-80}
        protocol: tcp
    networks:
      postgres_net:
        ipv4_address: ${PGADMIN_IP_ADDR:-172.19.0.2}
    depends_on:
      pg-server:
        condition: service_healthy

configs:
  [...]
  pgadmin-entrypoint.sh:
    file: ./pgadmin/init/entrypoint.sh
  pgadmin-servers.json:
    file: ./pgadmin/conf/servers.json

volumes:
  [...]
  pgadmin-data:

secrets:
  [...]
  pgadmin-ca.crt:
    file: ./pgadmin/certs/ca/server/server-ca.crt
  pgadmin-server.crt:
    file: ./pgadmin/certs/server/server.crt
  pgadmin-server.key:
    file: ./pgadmin/certs/server/server.key
  pgadmin-fmerinocasallo_writer.crt:
    file: ./pgadmin/certs/client/writer/fmerinocasallo_writer.crt
  pgadmin-fmerinocasallo_writer.key:
    file: ./pgadmin/certs/client/writer/fmerinocasallo_writer.key
  pgadmin-fmerinocasallo_reader.crt:
    file: ./pgadmin/certs/client/reader/fmerinocasallo_reader.crt
  pgadmin-fmerinocasallo_reader.key:
    file: ./pgadmin/certs/client/reader/fmerinocasallo_reader.key
  pgadmin-passfile:
    file: ./pgadmin/passwds/.pgpass

networks:
  postgres_net:
    driver: bridge
    ipam:
      config:
        - subnet: 172.19.0.0/24
          gateway: 172.19.0.1
```

It is worth noticing that:
- The official `dpage/pgadmin4` switch to the non-root user (`pgadmin`) in one of the last layers of the `Docker image` [^4].
- There is no `pgadmin` group. Instead, some files and directories, such as `/var/lib/pgadmin/` and `/pgadmin4/entrypoint.sh` are owned by `pgadmin:root`.
- We use `Docker configs` [^5] to store non-sensitive information outside a service's image or running containers.
In this case, such non-sensitive information includes `pgAdmin` configuration file `servers.json` and initilizing script  `entrypoint.sh`.
- We use `Docker secrets` to securely transfer sensitive data, such as user credentials and certificates, to specific `Docker containers` (e.g., `server.cert`, `fmerinocasallo_reader.key`).
- We create a `named volume` (`pgadmin-data`) to allow for persistent data in `/var/lib/pgadmin`.
- We use the aforementioned `user-defined bridge` network [^2] named `postgres_net`, providing a scoped network in which only containers attached to that network (i.e., those running the `pg-server` or `pgadmin` services) are able to communicate.
- We assign a static IP address to the `pgadmin` service (`172.19.0.50`). Beware of assigning static IP addresses to `Docker containers` if more than one are running the very same `Docker image`.
- We define the following file `.env`, with additional environment variables, some of them required by `pgAdmin`:

#### :page_facing_up: FILE `./.env`:
```
[...]

# pgAdmin settings
PGADMIN_IP_ADDR=172.19.0.50
PGADMIN_DEFAULT_EMAIL=pgadmin@pgadmin.com
PGADMIN_DEFAULT_PASSWORD=####
PGADMIN_USER_CONFIG_DIR=pgadmin_pgadmin.com
PGADMIN_ENABLE_TLS=True
PGADMIN_LISTEN_PORT=10100
PGADMIN_SERVER_JSON_FILE=/pgadmin4/servers.json
PGADMIN_CONFIG_CONSOLE_LOG_LEVEL=10
```

We want to enable secured commuinications with the `pgAdmin` web app using the encrypted protocol `HTTPS` instead of `HTTP`.
In HTTPS, the communication protocol is encrypted using TLS (previously SSL), which requires SSL/TLS certificates.
As these certificates are considered sensitive data, we want to use `Docker secrets` to securely transfer them at startup, from `host` to the `Docker container` running the `pgadmin`service.
`pgAdmin` expects to find these certificates in `/certs/server.cert` and `/certs/server.key` [^6].
However, `Docker` official documentation does not include any option to mount `Docker secrets` in a target location different than the default `/run/secrets/<ID_DOCKER_SECRET>`.
As a result, we opted to define a custom `Docker image` (based on the official one: `dpage/pgadmin4`) so we can create the `/certs/` directory, which will be, later on, populated with the required SSL/TLS certificates by a custom `entrypoint.sh` script.

_Note that other alternatives to transfer these certificates at startup, such as using `Docker configs` or `Docker bind mounts`, would allow to automatically mount these SSL/TLS certificates in the target directory (`/certs/server.cert` and `/certs/server.key`). However, these options are considered unsecured and, therefore, not suitable for sensitive information as these certificates._

See [SSL/TLS encrypted comms with the PostgreSQL server](#tls-encryption) for more details about how to create self-signed certificates, and set up the `pg-server` and `pgAdmin` services to use these SSL/TLS certificates to secure communications with the `PostgreSQL` server run by the `pg-server` service.

Next, we include the definition of our custom `Docker image` in `./pgadmin/pgadmin-1.Dockerfile` and the fragment of our custom
`entrypoint.sh` in charge of populating the `/certs/` directory with the appropriate SSL/TLS certificates:

#### :page_facing_up: FILE `./pgadmin/pgadmin-1.Dockerfile` (custom `Docker image`):
```
FROM dpage/pgadmin4:latest

USER root
RUN mkdir /certs \
    && chown pgadmin:root /certs
USER pgadmin

ENTRYPOINT ["/entrypoint.sh"]
```

#### :page_facing_up: FILE `./pgadmin/init/entrypoint.sh` (custom `entrypoint.sh`):
```
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

[...]
```

**Update**: Although not mentioned in the `Docker` official documentation, `Docker secrets` do accept the `target` feature [^7]. 

By using the `target` feature of `Docker secrets`, we could use an alternative definition of our custom `Docker image` in `./pgadmin/pgadmin-2.Dockerfile`.
This time, we just need to create the `/var/lib/pgadmin/storage/${PGADMIN_USER_CONFIG_DIR}/.postgresql` in advance so that this branch of the file system is owned by `pgadmin:root` instead of the default owner (`root:root`).
Otherwise, the `pgAdmin` service would complain about not being able to read and write in `/var/lib/pgadmin/storage/` during startup.

:raising_hand_man: Please, let me know if you know how to enable SSL/TLS encryption in `pgAdmin` using the official `Docker image` (`dpage/pgadmin4`).

#### :page_facing_up: FILE `./pgadmin/pgadmin-2.Dockerfile` (custom `Docker image`):
```
FROM dpage/pgadmin4:latest

ARG PGADMIN_USER_CONFIG_DIR=user_pgadmin.com

USER pgadmin
RUN mkdir -p /var/lib/pgadmin/storage/${PGADMIN_USER_CONFIG_DIR}/.postgresql \
    && chown pgadmin:root /var/lib/pgadmin/storage/${PGADMIN_USER_CONFIG_DIR}/.postgresql

ENTRYPOINT ["/entrypoint.sh"]
```

We would need to adapt our `docker-compose.yml` file as follows:

#### :page_facing_up: FILE `./docker-compose.yml`:
```
name: de_zoomcamp
services:
  [...]

  pgadmin:
    container_name: "pgadmin"
    user: "pgadmin:root"
    restart: unless-stopped
    build:
      context: ./pgadmin
      dockerfile: pgadmin-2.Dockerfile
      args:
        - PGADMIN_USER_CONFIG_DIR=$PGADMIN_USER_CONFIG_DIR
    configs:
      - source: pgadmin-servers.json
        target: /pgadmin4/servers.json
    environment:
      - PGADMIN_DEFAULT_EMAIL=${PGADMIN_DEFAULT_EMAIL:-user@pgadmin.com}
      - PGADMIN_DEFAULT_PASSWORD=${PGADMIN_DEFAULT_PASSWORD:-user_password}
      - PGADMIN_USER_CONFIG_DIR=${PGADMIN_USER_CONFIG_DIR:-user_pgadmin.com}
      - PGADMIN_LISTEN_PORT=${PGADMIN_LISTEN_PORT:-80}
      - PGADMIN_SERVER_JSON_FILE=${PGADMIN_SERVER_JSON_FILE}
      - PGADMIN_ENABLE_TLS=${PGADMIN_ENABLE_TLS:-}
    secrets:
      - source: pgadmin-server.crt
        target: /certs/server.cert
      - source: pgadmin-server.key
        target: /certs/server.key
      - source: pgadmin-ca.crt
        target: /var/lib/pgadmin/storage/${PGADMIN_USER_CONFIG_DIR}/.postgresql/server-ca.crt
      - source: pgadmin-fmerinocasallo_writer.crt
        target: /var/lib/pgadmin/storage/${PGADMIN_USER_CONFIG_DIR}/.postgresql/fmerinocasallo_writer.crt
      - source: pgadmin-fmerinocasallo_writer.key
        target: /var/lib/pgadmin/storage/${PGADMIN_USER_CONFIG_DIR}/.postgresql/fmerinocasallo_writer.key
      - source: pgadmin-fmerinocasallo_reader.crt
        target: /var/lib/pgadmin/storage/${PGADMIN_USER_CONFIG_DIR}/.postgresql/fmerinocasallo_reader.crt
      - source: pgadmin-fmerinocasallo_reader.key
        target: /var/lib/pgadmin/storage/${PGADMIN_USER_CONFIG_DIR}/.postgresql/fmerinocasallo_reader.key
      - source: pgadmin-passfile
        target: /var/lib/pgadmin/storage/${PGADMIN_USER_CONFIG_DIR}/.pgpass
    volumes:
      - type: volume
        source: pgadmin-data
        target: /var/lib/pgadmin
    ports:
      - mode: ingress
        target: ${PGADMIN_LISTEN_PORT:-80}
        published: ${PGADMIN_LISTEN_PORT:-80}
        protocol: tcp
    networks:
      postgres_net:
        ipv4_address: ${PGADMIN_IP_ADDR:-172.19.0.2}
    depends_on:
      pg-server:
        condition: service_healthy

configs:
  [...]
  pgadmin-servers.json:
    file: ./pgadmin/conf/servers.json

volumes:
  [...]
  pgadmin-data:

secrets:
  [...]
  pgadmin-ca.crt:
    file: ./pgadmin/certs/ca/server/server-ca.crt
  pgadmin-server.crt:
    file: ./pgadmin/certs/server/server.crt
  pgadmin-server.key:
    file: ./pgadmin/certs/server/server.key
  pgadmin-fmerinocasallo_writer.crt:
    file: ./pgadmin/certs/client/writer/fmerinocasallo_writer.crt
  pgadmin-fmerinocasallo_writer.key:
    file: ./pgadmin/certs/client/writer/fmerinocasallo_writer.key
  pgadmin-fmerinocasallo_reader.crt:
    file: ./pgadmin/certs/client/reader/fmerinocasallo_reader.crt
  pgadmin-fmerinocasallo_reader.key:
    file: ./pgadmin/certs/client/reader/fmerinocasallo_reader.key
  pgadmin-passfile:
    file: ./pgadmin/passwds/.pgpass

networks:
  postgres_net:
    driver: bridge
    ipam:
      config:
        - subnet: 172.19.0.0/24
          gateway: 172.19.0.1
```

_Note that this alternative would not require a custom `entrypoint.sh` script as before._

<div id="secure-comms"></div>

# Securing communications from and to the PostgreSQL server

We will enforce a secure and cryptographically-hased-based password authentication method and TSL/SSL encryption acting
as additional security layers to communications from and to the `PostgreSQL` server.
Finally, will change the default port used by the PostgreSQL, a classic example of security by obscurity (not free from criticism) [^3].

Notes based on the official PostgreSQL documentation [^8][^9][^10].


<div id="scram-auth"></div>

## `SCRAM-SHA-256` password authentication

The `SCRAM-SHA-256` password authentication method performs SCRAM-SHA-256 authentication, as described in
[RFC 7677](https://datatracker.ietf.org/doc/html/rfc7677).
It is a challenge-response scheme that prevents password sniffing on untrusted connections.
The `SCRAM-SHA-256` password authentication method supports storing passwords on the server in a cryptographically hashed form that is thought to be secure.

Although `SCRAM-SHA-256` authentication is not supported by older client libraries, this is the most secure of the
currently provided methods.

Using `SCRAM-SHA-256` enforce a cryptographically-hased-based password authentication method.
In SCRAM authentication, the client does the encryption work in order to produce the proof of identity. As a result, this method
offers additional protection against distributed denial-of-service (DDoS) attacks by preventing a CPU overload of the
PostgreSQL server to compute password hashes.

<div id="pg-conf-scram-auth"></div>

### Update PostgreSQL configuration to enforce hashed-based authentication

We update our `pgconf/postgresql.conf` file to include the following key configuration parameters.

#### :page_facing_up: FILE `./pgconf/postgresql.conf`:
```
password_encryption = scram-sha-256
scram_iterations = 4096
```

<div id="pg-server-tls"></div>

We update our `pgconf/pg_hba.conf` file to perform SCRAM-SHA-256 authentication to verify the user's password.

#### :page_facing_up: FILE `./pgconf/pg_hba.conf`:
```
# TYPE  DATABASE        USER                    ADDRESS                 AUTH-METHOD     AUTH-OPTIONS

# IPv4 local connections:
host    de_zoomcamp     postgres                127.0.0.1/32  scram-sha-256
host    de_zoomcamp     fmerinocasallo_writer   127.0.0.1/32  scram-sha-256
host    de_zoomcamp     fmerinocasallo_reader   127.0.0.1/32  scram-sha-256

# IPv4 connections from Docker's custom network:
host    de_zoomcamp     fmerinocasallo_writer   172.19.0.1/32 scram-sha-256
host    de_zoomcamp     fmerinocasallo_reader   172.19.0.1/32 scram-sha-256
```

_Note that, we are also limiting which users can authenticate (`postgres`, `fmerinocasallo_writer`, and `fmerinocasallo_reader`), to which database can they connect (`de_zoomcamp`), and from which IP addresses can they establish a connection (`127.0.0.1/32` and `172.19.0.1/32`). It is also worth highlightning that we do only allow login attempts from the `postgres` superuser to the `de_zoomcamp` database and from localhost (i.e., `127.0.0.1/32`). Conversely, login attempts from `fmerinocasallo_writer` and `fmerinocasallo_reader` are allow not only from `127.0.0.1/32` but also `172.19.0.1/32` (i.e., the `host` machine)._

A more tight control over authentication, enforcing password-based SCRAM-SHA-256 for client-server communication, enhances the database’s defense against unauthorized access and data
breaches.

## :lock: SSL/TLS encrypted communications with the PostgreSQL server

By default, PostgreSQL uses unencrypted connections.
For more secured connections, you can enable Transport Layer Security (TLS) support on the PostgreSQL server and configure your clients to establish encrypted connections.

PostgreSQL offers native support for SSL/TLS connections, which encrypts communications between client and server for increased security.
However, there are some requirements:
- OpenSSL must be installed on both client and server systems.
- Support in PostgreSQL must be enabled at build time.

The terms `SSL` and `TLS` are often used interchangeably when referring to a secure encrypted connection using a TLS protocol.
SSL protocols are the precursors to TLS protocols.
_Note that the term `SSL` is still used for encrypted connections even though SSL protocols are no longer supported._

<div id="ca-cert"></div>

### Create a self-signed root certificate authority (CA)

Create a couple of self-signed root certificate authority (CAs) for testing, valid por 3650 days, replacing
`172.19.0.70` (server) and `172.19.0.1` (host/client) with the corresponding IP addresses.

Start by creating two certificate signing request (CSR) and public/private key files:

#### :computer: Executed commands in terminal
```
openssl req -new -nodes -text -out security/certs/ca/postgres_net/pg/server/server-ca.csr \
  -keyout pg-server/certs/ca/server/server-ca.key -subj "/CN=172.19.0.70"
chmod og-rwx pg-server/certs/ca/server/server-ca.key

openssl req -new -nodes -text -out pg-server/certs/ca/client/client-ca.csr \
  -keyout pg-server/certs/ca/client/client-ca.key -subj "/CN=172.19.0.1"
chmod og-rwx pg-server/certs/ca/client/client-ca.key
```

_Note that we have explicitly lock down the private keys (`client-ca.key` and `server-ca.key`)._

Then, sign the CSRs with the key files to create two root CAs (using the default OpenSSL configuration
file location on Linux):

#### :computer: Executed commands in terminal
```
openssl x509 -req -in pg-server/certs/ca/server/server-ca.csr -text -days 3650 \
  -extfile /etc/ssl/openssl.cnf -extensions v3_ca \
  -signkey pg-server/certs/ca/server/server-ca.key \
  -out pg-server/certs/ca/server/server-ca.crt

openssl x509 -req -in pg-server/certs/ca/client/client-ca.csr -text -days 3650 \
  -extfile /etc/ssl/openssl.cnf -extensions v3_ca \
  -signkey pg-server/certs/ca/client/client-ca.key \
  -out pg-server/certs/ca/client/client-ca.crt
```

The `pg-server/certs/ca/server/server-ca.crt` file should be stored on the client so the client can
verify that the server’s certificate was signed by its trusted root certificate. Conversely,
the `pg-server/certs/ca/server/server-ca.key` file should be stored offline for use in creating future
certificates.

The `pg-server/certs/ca/client/client-ca.crt` file should be stored on the server so the server can
verify that the client's certificate was signed by its trusted root certificate. Conversely,
the `pg-server/certs/ca/client/client-ca.key` file should be stored offline for use in creating future
certificates.

_Note that, while a self-signed certificate can be used for testing, a certificate signed by a CA (usually an enterprise-wide root CA) should be used in production._

<div id="server-cert"></div>

### Create a server certificate signed by the new certificate authority

Create a simple self-signed (by the new root CA) certificate for the server, valid for 365 days, replacing `172.19.0.70`
with the server IP address.

#### :computer: Executed commands in terminal
```
openssl req -new -nodes -text -out pg-server/certs/server/server.csr \
  -keyout pg-server/certs/server/server.key \
  -subj "/CN=172.19.0.70"
chmod og-rwx pg-server/certs/server/server.key
openssl x509 -req -in pg-server/certs/server/server.csr -text -days 365 \
  -CA pg-server/certs/ca/server/server-ca.crt \
  -CAkey pg-server/certs/ca/server/server-ca.key \
  -CAcreateserial -out pg-server/certs/server/server.crt
```

Files `server.crt` and `server.key`, should be stored on the server.
_Note that we have explicitly lock down the server's private key._

<div id="client-cert"></div>

### Create client certificates

Create a simple self-signed (by the new root CA) certificate for the client's different users (superuser: `postgres`,
read-write: `fmerinocasallo_writer`, read-only: `fmerinocasallo_reader`), valid for 365 days, replacing `postgres`,
`fmerinocasallo_writer` and `fmerinocasallo_reader` with the appropriate usernames in the database.

#### :computer: Executed commands in terminal
```
openssl req -new -nodes -text -out host/certs/client/superuser/postgres.csr \
  -keyout host/certs/client/superuser/postgres.key -subj "/CN=postgres"
chmod og-rwx host/certs/client/superuser/postgres.key
openssl x509 -req -in host/certs/client/superuser/postgres.csr -text -days 365 \
  -CA pg-server/certs/ca/client/client-ca.crt \
  -CAkey pg-server/certs/ca/client/client-ca.key \
  -CAcreateserial -out host/certs/client/superuser/postgres.crt

openssl req -new -nodes -text -out host/certs/client/writer/fmerinocasallo_writer.csr \
  -keyout host/certs/client/writer/fmerinocasallo_writer.key \
  -subj "/CN=fmerinocasallo_writer"
chmod og-rwx host/certs/client/writer/fmerinocasallo_writer.key
openssl x509 -req -in host/certs/client/writer/fmerinocasallo_writer.csr -text -days 365 \
  -CA pg-server/certs/ca/client/client-ca.crt \
  -CAkey pg-server/certs/ca/client/client-ca.key \
  -CAcreateserial -out host/certs/client/writer/fmerinocasallo_writer.crt

openssl req -new -nodes -text -out host/certs/client/reader/fmerinocasallo_reader.csr \
  -keyout host/certs/client/reader/fmerinocasallo_reader.key \
  -subj "/CN=fmerinocasallo_reader"
chmod og-rwx host/certs/client/reader/fmerinocasallo_reader.key
openssl x509 -req -in host/certs/client/reader/fmerinocasallo_reader.csr -text -days 365 \
  -CA pg-server/certs/ca/client/client-ca.crt \
  -CAkey pg-server/certs/ca/client/client-ca.key \
  -CAcreateserial -out host/certs/client/reader/fmerinocasallo_reader.crt
```

_Note that we have explicitly lock down the client's private keys (`host/certs/client/superuser/postgres.key`, `host/certs/client/writer/fmerinocasallo_writer.key` and `host/certs/client/reader/fmerinocasallo_reader.key`)._

<div id="pg-conf-tls"></div>

### Update PostgreSQL configuration to enforce certificate-based TLS authentication

We update our `pgconf/postgresql.conf` file to include the following key configuration parameters.

#### :page_facing_up: FILE `./pgconf/postgresql.conf`:
```
ssl = on # this enables TLS
ssl_cert_file = '/run/secrets/pg_server.crt' # this specifies the location of the server certificate
ssl_key_file = '/run/secrets/pg_server.key' # this specifies the location of the server private key
ssl_ca_file = '/run/secrets/pg_ca.crt' # this specifies which CA certificate to trust (client-ca.crt)

# This setting is on by default but it’s always a good idea to
# be explicit when it comes to security.
ssl_prefer_server_ciphers = on

# TLS 1.3 will give the strongest security and is advised when
# controlling both server and clients.
ssl_min_protocol_version = 'TLSv1.3'
```

_Note that we enforce TLSv1.3 for the strongest security._

We also update our `pgconf/pg_hba.conf` file to require the client to supply a trusted SSL/TLS certificate.

#### :page_facing_up: FILE `./pgconf/pg_hba.conf`:
```
# TYPE  DATABASE        USER                    ADDRESS                 AUTH-METHOD     AUTH-OPTIONS

# IPv4 local connections:
hostssl de_zoomcamp     postgres                127.0.0.1/32  scram-sha-256   clientcert=verify-full
hostssl de_zoomcamp     fmerinocasallo_writer   127.0.0.1/32  scram-sha-256   clientcert=verify-full
hostssl de_zoomcamp     fmerinocasallo_reader   127.0.0.1/32  scram-sha-256   clientcert=verify-full

# IPv4 connections from Docker's custom network:
hostssl de_zoomcamp     fmerinocasallo_writer   172.19.0.1/32 scram-sha-256   clientcert=verify-full
hostssl de_zoomcamp     fmerinocasallo_reader   172.19.0.1/32 scram-sha-256   clientcert=verify-full
```

By using a `hostssl` entry with `clientcert=verify-full`, the server will:
- Verify that the client's certificate is signed by one of the trusted certificate authorities.
- Check whether the username or its mapping matches the CN (Common Name) of the provided certificate.

Intermediate certificates that chain up to existing root certificates can also appear in the `ssl_ca_file` file if you
wish to avoid storing them on clients (assuming the root and intermediate certificates were created with `v3_ca`
extensions).

A more tight control over authentication, enforcing certificate-based SSL/TLS
encryption for client-server communication, enhances the database’s defense against unauthorized access and data
breaches.

<div id="pgadmin-tls"></div>

## Setting up `pgAdmin` to use SSL/TLS communications

Now, our `PostgreSQL` server requires encrypted communications.
Therefore, we must set up our `pgAdmin` service to use SSL/TLS certificates to communicate with the `pg-server` service.
In this case, where `pgAdmin` is installed in Server mode (the default mode), the following fields consider their base
directory `<STORAGE_DIR>/<USERNAME>/`[^11][^12][^13]:
- `passfile`
- `sslcert`
- `sslkey`
- `sslrootcert`

where `<STORAGE_DIR>` points to `/var/lib/pgadmin/storage/` by default and `<USERNAME>` refers to the
`${PGADMIN_DEFAULT_EMAIL}` environment variable but replacing `_` by `@` (e.g., `foo_bar.org` instead of `foo@bar.org`).
Next, we include the default values for some of the aforementioned fields:
- `sslcert`: `<STORAGE_DIR>/<USERNAME>/.postgresql/postgresql.crt`
- `sslkey`: `<STORAGE_DIR>/<USERNAME>/.postgresql/postgresql.key`
- `sslrootcert`: `~/.postgresql/root.crt`

We are interested in executing queries from users `fmerinocasallo_writer` and `fmerinocasallo_reader` from our
`pgAdmin` server through encrypted communications with our `PostgreSQL` server.
Therefore, we will automatically add two different `Servers` in `pgAdmin` through a `servers.json` file:

#### :page_facing_up: FILE `./pgadmin/conf/servers.json`:
```
{
    "Servers": {
        "1": {
            "Name": "PostgreSQL Server [Read&Write]",
            "Group": "Servers",
            "Host": "172.19.0.70",
            "HostAddr": "172.19.0.70",
            "Port": 10864,
            "Username": "fmerinocasallo_writer",
            "Comment": "Read&Write user",
            "MaintenanceDB": "de_zoomcamp",
            "DBRestriction": "de_zoomcamp",
            "ConnectionParameters": {
            	"passfile": "/.pgpass",
            	"sslmode": "require",
            	"sslcert": "/.postgresql/pgadmin_fmerinocasallo_writer.crt",
            	"sslkey": "/.postgresql/pgadmin_fmerinocasallo_writer.key",
            	"sslrootcert": "/.postgresql/pgadmin_ca.crt"
	        }
        },
        "2": {
            "Name": "PostgreSQL Server [Read-Only]",
            "Group": "Servers",
            "Host": "172.19.0.70",
            "HostAddr": "172.19.0.70",
            "Port": 10864,
            "Username": "fmerinocasallo_reader",
            "Comment": "Read-only user",
            "MaintenanceDB": "de_zoomcamp",
            "DBRestriction": "de_zoomcamp",
	        "ConnectionParameters": {
            	"passfile": "/.pgpass",
            	"sslmode": "require",
            	"sslcert": "/.postgresql/pgadmin_fmerinocasallo_reader.crt",
            	"sslkey": "/.postgresql/pgadmin_fmerinocasallo_reader.key",
            	"sslrootcert": "/.postgresql/pgadmin_ca.crt"
	        }
        }
    }
}
```

It is worth to mention that:
- We have defined the `${PGADMIN_SERVER_JSON_FILE}` environment variable in the `./.env` file so that it stores the location of this `servers.json` file.
- Although we are using absolute paths for fields `passfile`, `sslcert`, `sslkey`, and `sslrootcert`, `pgAdmin` expects these files not in the root directory of the filesystem (`/`) but in the base directory previously mentioned.
For our specific case, the base directory is `/var/lib/pgadmin/storage/pgadmin_pgadmin.com`. As a result, `pgAdmin`expects to find the `sslrootcert` in `/var/lib/pgadmin/storage/pgadmin_pgadmin.com/.postgresql/pgadmin_ca.crt`.

<div id="pgadmin-loc-own-perm"></div>

### Setting up SSL/TLS certificates location, ownership, and permissions

The required SSL/TLS certificates enabling encrypted communications between the `pgAdmin` and `PostgreSQL` server are 
loaded into the `Docker container` as `secrets` for security purposes.
Thus, they are initially located in the `/run/secrets/` directory of the `Docker` container.
However, as previously discussed, `pgAdmin` expects them to find them in `<STORAGE_DIR>/<USERNAME>/.postgresql/`.
Therefore, we change the `ENTRYPOINT` of the `Docker image` we will use to run `pgAdmin` using `Docker containers`.
Now, we will run a custom `entrypoint.sh` shell script to make sure the `passfile` and SSL/TLS certificates (e.g., `pgadmin_fmerinocasallo_writer.crt`, `pgadmin_fmerinocasallo_reader.key`, and `server-ca.crt`) are in the right directory, owned by the right user and group (`pgadmin:root`), and have the right permissions.

#### :page_facing_up: FILE `./pgadmin/init/entrypoint.sh`:
```
#!/usr/bin/env sh

echo -n "Setting up PassFile & SSL/TLS certificates for secured" \
"(encrypted) comms with the PostgreSQL server... "

SRC_DIR=/run/secrets
DST_DIR=/var/lib/pgadmin/storage/${PGADMIN_USER_CONFIG_DIR}

PASS_FILE=${DST_DIR}/.pgpass
CERT_DIR=${DST_DIR}/.postgresql

# Create file structure required to support SSL/TLS comms with the PostgreSQL
# server
mkdir -p ${CERT_DIR}

# Copy .pgpass file and SSL/TLS certificates to its final destination so that
# pgAdmin can automatically logging in in the PostgreSQL server as a valid user
# through SSL/TLS comms
cp ${SRC_DIR}/pgadmin_passfile ${PASS_FILE}
find ${SRC_DIR} -name \*.crt -exec cp '{}' /${CERT_DIR} \; -o -name \*.key -exec cp '{}' ${CERT_DIR} \;

# Make sure the new file structure has the required ownership and permissions
chown -R pgadmin:root ${DST_DIR}
chmod 600 ${PASS_FILE}
find ${CERT_DIR} -name \*.crt -exec chmod 640 '{}' \; -o -name \*.key -exec chmod 600 '{}' \;

echo "done"

sh /entrypoint.sh
```

_Note that we end our custom `entrypoint.sh` shell script by calling the original `entrypoint.sh` included in the official `pgAdmin` `Docker` image._

<div id="pgadmin-vars"></div>

### Setting up `pgAdmin` environment variables

As previously mentioned, we need to declare several environment variables for our `pgAdmin` service.
Therefore, we include the following declarations in a `.env` file:

#### :page_facing_up: FILE `./.env`:
```
# pgAdmin settings
PGADMIN_DEFAULT_EMAIL=pgadmin@pgadmin.com
PGADMIN_DEFAULT_PASSWORD=XXXX
PGADMIN_USER_CONFIG_DIR=pgadmin_pgadmin.com
PGADMIN_ENABLE_TLS=True
PGADMIN_LISTEN_PORT=10100
PGADMIN_SERVER_JSON_FILE=/pgadmin4/servers.json
PGADMIN_CONFIG_CONSOLE_LOG_LEVEL=10
```

These will enforce secured communications between the browser and the `pgAdmin` service (`PGADMIN_ENABLE_TLS=True`) and modify its listening port (`PGADMIN_LISTEN_PORT=10100`; Security through obscurity [^3]).

See the official `pgAdmin` documentation for more information about these and other variables accepted by  the `Docker container` at startup [^14].

<div id="init-sql"></div>

## :file_folder: Initialize `PostgreSQL`'s DB through the `init.sql` script

First, we delete the default `public` SCHEMA (we won't be using it) and create a new `nyc_taxi`SCHEMA.

#### :page_facing_up: FILE `./pg-server/init/init-db.sql`:
```
-- Update schemas in the current database (de_zoomcamp)
DROP SCHEMA IF EXISTS public CASCADE;
CREATE SCHEMA nyc_taxi;

[...]
```

Next, we update the `postgres` (superuser) password using the aforementioned SCRAM-SHA-256 authentication method.

#### :page_facing_up: FILE `./pg-server/init/init-db.sql`:
```
[...]

-- Update password from postgres (superuser)
ALTER USER postgres WITH ENCRYPTED PASSWORD 'SCRAM-SHA-256$4096:2e6SBLkCNpp+FljVIo5vrw==$2+9d4e1jr+i27dnxoEnIH28fdAhRmJvYsNCGkiW0LV4=:4YlfgP03ujA+BT0q2QudXoTa4BAFTpVp4Rj7w3n????=';

[...]
```

Then, we create a new `writer` role, with read and write permissions in the newly created `de_zoomcamp` database.

#### :page_facing_up: FILE `./pg-server/init/init-db.sql`:
```
[...]

-- Create a new writer role (read & write)
CREATE ROLE writer NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOLOGIN NOREPLICATION NOBYPASSRLS;
GRANT CONNECT, CREATE ON DATABASE de_zoomcamp TO writer;
GRANT USAGE, CREATE ON SCHEMA nyc_taxi TO writer;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA nyc_taxi TO writer;

[...]
```

Conversely, the new `reader` role is read-only, which drastically reduce what this role is allow to do in the
`de_zoomcamp` database.

#### :page_facing_up: FILE `./pg-server/init/init-db.sql`:
```
[...]

-- Create a new reader role (read-only)
CREATE ROLE reader NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOLOGIN NOREPLICATION NOBYPASSRLS;
GRANT CONNECT ON DATABASE de_zoomcamp TO reader;
GRANT USAGE ON SCHEMA nyc_taxi TO reader;
GRANT SELECT ON ALL TABLES IN SCHEMA nyc_taxi TO reader;

[...]
```

Finally, create two new users (`fmerinocasallo_writer` and `fmerinocasallo_reader`) with the corresponding SCRAM-based
password and grant the `writer` role to the former and the `reader` role to the latter.

#### :page_facing_up: FILE `./pg-server/init/init-db.sql`:
```
[...]

-- Create a new user (fmerinocasallo_writer) and grant read & write access to
-- all already created tables in the `nyc_taxi` schema
CREATE USER fmerinocasallo_writer WITH ENCRYPTED PASSWORD 'SCRAM-SHA-256$4096:uMOkAQtSqAJPKkji13KPXw==$zXz1/xO0Cg8sFm4dPIvxOJ9aO3RUqV5855Yfi/88lK4=:/Fjc1UjOOLHDmQZoqutpmFKne63CBO22ehWGIRg####=';
GRANT writer TO fmerinocasallo_writer;

-- Create a new user (fmerinocasallo_reader) and grant read-only access to all already
-- created tables in the `nyc_taxi` schema
CREATE USER fmerinocasallo_reader WITH ENCRYPTED PASSWORD 'SCRAM-SHA-256$4096:8z57J5HjIF2XAoJqM7axwg==$xjrHp0IfcQ6qRb1Cnezz769zns/FvIvJxa9x+UVnwVw=:ZlUtYDmeJbHa99p6/aOqYuV8f6EZjAJe6vwHiAk####=';
GRANT reader TO fmerinocasallo_reader;
```

Creating multiple roles (`writer` and `reader`) with different privileges (i.e., read & write vs read-only) also hardens
security and establish strict controls over what authenticated users can do.
It also limits database access for specific users.


[^1]: From Docker official blog: Understanding the Docker USER Instruction (accessed 23/08/2024): https://www.docker.com/blog/understanding-the-docker-user-instruction/
[^2]: From Docker official documentation: Bridge network driver (accessed 23/08/2024): https://docs.docker.com/engine/network/drivers/bridge/
[^3]: From Wikipedia's entry about Security by obscurity (accessed on 29/08/2024): https://en.wikipedia.org/wiki/Security_through_obscurity
[^4]: From Docker Hub. dpage/pgadmin4:latest (accessed 23/08/2024): https://hub.docker.com/layers/dpage/pgadmin4/latest/images/sha256-e77d1cd589e52a74088fd9ecda60898dd113bd41c4b3fb6fe5b71f32935e8634?context=explore
[^5]: From Docker official documentation: Store configuration data using Docker Configs (accessed 27/08/2024): https://docs.docker.com/engine/swarm/configs/
[^6]: From pgAdmin 4 8.11 documentation » Getting Started » Deployment » Container Deployment (accessed on 22/08/2024): https://www.pgadmin.org/docs/pgadmin4/latest/container_deployment.html
[^7]: From Docker official repo (GitHub) Issues Tracker: Docker secret custom directory #4101 (accessed 28/08/2024): https://github.com/docker/docs/issues/4101
[^8]: From chapter 20.3. Connections and Authentication (accessed on 22/06/2024):
https://www.postgresql.org/docs/current/runtime-config-connection.html
[^9]: From chapter 21.5. Password Authentication (accessed on 22/06/2024):
https://www.postgresql.org/docs/current/auth-password.html
[^10]: From chapter 19.9. Secure TCP/IP Connections with SSL (accessed on 22/06/2024): https://www.postgresql.org/docs/current/ssl-tcp.html
[^11]: From pgAdmin 4 8.11 documentation » Managing Database Objects » Subscription Dialog (accessed on 22/08/2024):
https://www.pgadmin.org/docs/pgadmin4/latest/subscription_dialog.html
[^12]: From Docker official repo (GitHub) Issues Tracker: External database with PGPASS file not working #6741 (accessed 22/08/2024): https://github.com/pgadmin-org/pgadmin4/issues/6741#issuecomment-1722212595
[^13]: _Note that if `pgAdmin` is installed in Desktop mode, the base directory of the aforementioned fields would be:
`~/` (the `$HOME` directory of the current user)._
[^14]: From pgAdmin 4 8.11 documentation » Getting Started » Deployment » Container Deployment (accessed on 27/08/2024): https://www.pgadmin.org/docs/pgadmin4/latest/container_deployment.html#environment-variables
