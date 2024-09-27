# Using PostgreSQL to store NYC Taxi data

## Table of contents
1. [`PostgreSQL` Server (`pg-server`) as a Service](#pg-server)
2. [Securing communications from and to the PostgreSQL server](#secure-comms)
    1. [:key: SCRAM-SHA-256 password authentication](#scram-auth)
        1. [Update PostgreSQL configuration to enforce hashed-based authentication](#pg-conf-scram-auth)
    2. [:closed_lock_with_key: SSL/TLS encryption for communications with the PostgreSQL server](#pg-server-tls)
        1. [Create a self-signed root certificate authority (CA)](#ca-cert)
        2. [Create a server certificate signed by the new CA](#server-cert)
        3. [Create client certificates signed by the new CA](#client-cert)
        4. [Update PostgreSQL configuration to enforce certificate-based TLS authentication](#pg-conf-tls)
    3. [:file_folder: Initialize `PostgreSQL` database](#init-sql)

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