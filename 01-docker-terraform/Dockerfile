# syntax=docker/dockerfile:1
FROM python:3.9

RUN pip install --upgrade pip

RUN useradd --create-home --shell /bin/bash fmerinocasallo
USER fmerinocasallo

WORKDIR /home/fmerinocasallo/app
COPY --chown=fmerinocasallo:fmerinocasallo random_series.py data-pipeline.sh requirements.txt ./

ENV PATH="/home/fmerinocasallo/.local/bin:${PATH}"

ENTRYPOINT [ "bash", "data-pipeline.sh", "-d", "15" ]
