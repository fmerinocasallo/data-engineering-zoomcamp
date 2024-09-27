FROM python:3.12.4-slim-bookworm

RUN pip install --upgrade pip
RUN groupadd --gid 1000 fmerinocasallo \
    && useradd --uid 1000 --gid fmerinocasallo --shell /bin/bash fmerinocasallo
USER fmerinocasallo

WORKDIR /home/fmerinocasallo/app
COPY --chown=fmerinocasallo:fmerinocasallo data_manager.py data-ingest.sh requirements.txt ./
RUN mkdir -p data certs passwd

ENV PATH="/home/fmerinocasallo/.local/bin:${PATH}"

ENTRYPOINT ["/bin/bash", \
            "data-ingest.sh", \
            "--url-trips", "https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2021-01.parquet", \
            "--url-zones", "https://d37ci6vzurychx.cloudfront.net/misc/taxi_zone_lookup.csv", \
            "--fname-trips", "yellow_tripdata_2021-01.parquet", \
            "--fname-zones", "taxi_zone_lookup.csv", \
            "--user", "fmerinocasallo_writer", \
            "--password", "./passwd/passwd.txt", \
            "--host", "172.19.0.70", \
            "--port", "10864", \
            "--db", "de_zoomcamp", \
            "--schema", "nyc_taxi", \
            "--table-trips", "yellow_taxi_trips", \
            "--table-zones", "zones"]
