#!/usr/bin/env bash

# Create image from Dockerfile
docker build -t de_zoomcamp:postgres .
# Create Docker Volume for data retention after the Docker image shuts down
docker volume create --name data-postgres-nyc-taxi -d local
# Run Docker image using the created Docker Volume
# docker run --rm --name postgres -v data-postgres-nyc-taxi:/var/lib/postgresql/data -p 10864:10864 de_zoomcamp:postgres
docker run --rm --name postgres --network="host" -v data-postgres-nyc-taxi:/var/lib/postgresql/data de_zoomcamp:postgres
