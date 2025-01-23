#!/bin/zsh

for chunk_size_dw (10 100 1000 10000 100000 1000000 10000000 100000000)
do
    for chunk_size_sql (10 100 1000 10000 100000 1000000 10000000 100000000)
    do
        for method ("multi" "psql_insert_copy" "None")
        do
            echo "chunk_size_dw=${chunk_size_dw} - chunk_size_sql=${chunk_size_sql} - method=${method}"
            tex_mem python ../data-manager.py \
                --url=https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2021-01.parquet \
                --fname=../data/yellow_tripdata_2021-01.parquet \
                --username=fmerinocasallo_writer \
                --password=../../pg-server/passwds/pg-fmerinocasallo_writer-passwd.txt \
                --host=172.19.0.70 \
                --port=10864 \
                --db=de_zoomcamp \
                --schema=nyc_taxi \
                --table=yellow_taxi_trips \
                --chunk-size-dw=${chunk_size_dw} \
                --chunk-size-sql=${chunk_size_sql} \
                --method-sql=${method} \
            | grep "Took"
        done
    done
done