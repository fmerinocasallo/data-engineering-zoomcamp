# syntax=docker/dockerfile:1
FROM postgres:alpine3.19

ENV POSTGRES_DB=de_zoomcamp
ENV POSTGRES_USER=postgres
ENV POSTGRES_PASSWORD=postgres

COPY --chown=postgres:postgres pg_hba.conf postgresql.conf \
     certs/localhost/server.* \
     certs/localhost/client.* \
     certs/root.crt \
     init-db.sql \
     init.sh \
     /docker-entrypoint-initdb.d/
