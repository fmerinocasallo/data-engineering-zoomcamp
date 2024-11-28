#!/usr/bin/env python
# coding: utf-8
import csv
from datetime import datetime
from dateutil.relativedelta import relativedelta
from io import StringIO
import logging
from os import PathLike
from pathlib import Path
from re import match
from typing import Callable, Dict, Literal, Tuple

import click
import pandas as pd
from pathvalidate import sanitize_filepath
import requests
import sqlalchemy as sa
import validators


PATH_BASE = Path("/home/fmerinocasallo/app")

PATHS = {
    "data": PATH_BASE/"data",
    "passwd": PATH_BASE/"passwd",
    "certs": PATH_BASE/"certs",
}

MIN_PORT, MAX_PORT = 1024, 65535


def init_logger() -> logging.Logger:
    logger = logging.getLogger(name="data-manager")
    logger.setLevel(logging.INFO)
    console_handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger


_logger = init_logger()


# Alternative to_sql() *method* for DBs that support COPY FROM
def psql_insert_copy(table, conn, keys, data_iter):
    """
    Execute SQL statement inserting data

    Parameters
    ----------
    table : pandas.io.sql.SQLTable
    conn : sqlalchemy.engine.Engine or sqlalchemy.engine.Connection
    keys : list of str
        Column names
    data_iter : Iterable that iterates the values to be inserted
    """
    # gets a DBAPI connection that can provide a cursor
    dbapi_conn = conn.connection
    with dbapi_conn.cursor() as cur:
        s_buf = StringIO()
        writer = csv.writer(s_buf)
        writer.writerows(data_iter)
        s_buf.seek(0)

        columns = ', '.join(['"{}"'.format(k) for k in keys])
        if table.schema:
            table_name = '{}.{}'.format(table.schema, table.name)
        else:
            table_name = table.name

        sql = 'COPY {} ({}) FROM STDIN WITH CSV'.format(
            table_name, columns)
        cur.copy_expert(sql=sql, file=s_buf)


def data_download(url: str, fname: str | bytes | PathLike, chunk_size: int) -> None:
    """
    Downloads tabular data (NYC taxi trips; PARQUET format) from remote location and store it locally.

    Args:
        url: Tabular data (NYC taxi trips; PARQUET format) remote repository.
        fname: Local path where tabular data (NYC taxi trips) will be stored (PARQUET format).
        chunk_size: Chunk size used during local storage.

    Raises:
        ConnectionError: If unable to download tabular data (NYC taxi trips) from remote location.
    """
    response = requests.get(url, stream=True)
    response.raise_for_status()

    fname = PATHS["data"]/Path(fname).name
    with open(fname, "wb") as file:
        for data in response.iter_content(chunk_size):
            if data:
                file.write(data)
            else:
                pass

    _logger.info(f"NYC taxi tabular data downloaded from {url} and saved locally in {fname}.")

    return None


def data_read(fname: str | bytes | PathLike) -> pd.DataFrame:
    """
    Returns NYC taxi tabular data read from given local path (PARQUET | CSV format).

    Args:
        fname: Local path where NYC taxi tabular data is stored (PARQUET | CSV format).

    Returns:
        NYC taxi tabular data read from given local path.

    Raises:
        ValueError: If provided `fname` is not stored in a supported format (PARQUET | CSV).
    """
    if Path(fname).suffix == ".parquet":
        data = pd.read_parquet(PATHS["data"]/Path(fname).name)
    elif Path(fname).suffix == ".csv":
        data = pd.read_csv(PATHS["data"]/Path(fname).name)
    else:
        raise ValueError(f"Invalid file extension ({Path(fname).suffix}). Supported extensions: PARQUET | CSV.")

    _logger.info(f"NYC taxi tabular data read from {PATHS['data']/Path(fname).name}")

    return data


def data_clean(data: pd.DataFrame, dates: Tuple[datetime, datetime]) -> pd.DataFrame:
    """
    Return cleaned tabular data (NYC taxi trips).

    Args:
        data: Tabular data (NYC taxi trips) to be cleaned.
        dates: time period boundaries for the tabular data (NYC taxi trips) recorded.
    """
    # Discard `store_and_fwd_flag` details because of its lack of relevance.
    del data["store_and_fwd_flag"]

    # Originally stored as 'airport_fee', later on as 'Airport_fee'.
    if "Airport_fee" in data:
        data["airport_fee"] = data["Airport_fee"]
        del data["Airport_fee"]
    else:
        pass

    # Check number of unique values per column/attribute and identify potential categorical values.
    for column in data.columns:
        if data[column].nunique() < 10:
            _logger.debug(f"Column {column} includes {data[column].nunique()} unique values ({data[column].unique()}).")
        else:
            _logger.debug(f"Column {column} includes {data[column].nunique()} unique values.")

    # Compute delta time (time elapsed between pickup and dropoff).
    data["dt"] = (
        data["tpep_dropoff_datetime"]
        - data["tpep_pickup_datetime"]
    )

    data["avg_speed"] = (
        data["trip_distance"]
        / (data["dt"]/pd.Timedelta(hours=1))
    )

    # Reorder columns/attributes based on its relevance.
    data = data[
        [
            "tpep_pickup_datetime",
            "tpep_dropoff_datetime",
            "dt",
            "trip_distance",
            "avg_speed",
            "PULocationID",
            "DOLocationID",
            "RatecodeID",
            "passenger_count",
            "total_amount",
            "fare_amount",
            "tip_amount",
            "tolls_amount",
            "extra",
            "mta_tax",
            "improvement_surcharge",
            "congestion_surcharge",
            "airport_fee",
            "payment_type",
            "VendorID",
        ]
    ].copy()

    # Discard trips considered bad data.

    # Note that we cannot discuss with the business experts how to identify bad data and, therefore, our hability to do
    # so is limited. Next, we propose several scenarios that could identify bad data using our shallow understanding in
    # this sector.

    # - Discard trips outside the analyzed time period and those with invalid pickup and dropoff datetimes.
    data.drop(
        data[
            (data["tpep_dropoff_datetime"] <= data["tpep_pickup_datetime"])
            | (data["tpep_pickup_datetime"] < dates[0])
            | (data["tpep_pickup_datetime"] >= dates[1])
            | (data["tpep_dropoff_datetime"] < dates[0])
            | (data["tpep_dropoff_datetime"] >= dates[1])
        ].index,
        inplace=True,
    )

    # - Discard trips with invalid `VendorID` values.
    data.drop(data[data["VendorID"] == 6].index, inplace=True)

    # - Discard trips with invalid `RatecodeID` values and convert to `int64` this column/attribute.
    data.drop(
        data[
            (data["RatecodeID"].isna())
            | (data["RatecodeID"] == 99.0)
        ].index,
        inplace=True,
    )

    data["RatecodeID"] = data["RatecodeID"].astype("int64")

    # - By law, a maximum of 4 passengers are allowed in standard NYC taxis. A child under 7 is allowed to sit on a
    #     passenger's lap in the rear seat in addition to the passenger limit. Therefore, discard trips with more than 5
    #     passengers. Also, discard trips with no passengers.
    data.drop(data[(data["passenger_count"] > 5) | (data["passenger_count"] == 0)].index, inplace=True)
    data["passenger_count"] = data["passenger_count"].astype("int64")

    # - Discard trips with negative or nil distance.
    data.drop(data[data["trip_distance"] <= 0].index, inplace=True)

    # - Discard trips with a negligible duration (lower than 1 minute).
    data.drop(data[data["dt"]/pd.Timedelta(minutes=1) < 1].index, inplace=True)

    # - Discard trips with a negative average speed (i.e., the trip distance or duration is negative).
    data.drop(data[data["avg_speed"] < 0].index, inplace=True)

    # - Discard trips from or to outside NYC with an average speed higher than 75 mph (max freeway speed limit in the
    #     surrounding states).
    data.drop(
        data[
            (data["avg_speed"] > 75)
            & (
                (data["PULocationID"] > 263)
                | (data["DOLocationID"] > 263)
            )
        ].index,
        inplace=True,
    )

    # - Discard trips within NYC with an average speed higher than 50 mph (max speed limit in NYC).
    data.drop(
        data[
            (data["avg_speed"] > 50)
            & (
                (data["PULocationID"] < 264)
                & (data["DOLocationID"] < 264)
            )
        ].index,
        inplace=True,
    )

    # - Discard trips taking more than 1 hour at an average speed lower than 3 mph, as it is assumed these slow trips
    #     cannot even be associated with traffic jams, even in NYC.
    data.drop(
        data[
            (data["dt"]/pd.Timedelta(hours=1) > 1)
            & (data["avg_speed"] < 3)
        ].index,
        inplace=True,
    )

    data[
        [
            "PULocationID",
            "DOLocationID",
            "RatecodeID",
            "passenger_count",
            "payment_type",
            "VendorID",
        ]
    ] = data[
        [
            "PULocationID",
            "DOLocationID",
            "RatecodeID",
            "passenger_count",
            "payment_type",
            "VendorID",
        ]
    ].astype("int32")

    # Reset index after data processing.
    data.reset_index(drop=True, inplace=True)

    _logger.info("Tabular data (NYC taxi) cleaned.")

    return data


def data_ingest(
        data_trips: pd.DataFrame,
        data_zones: pd.DataFrame,
        pg_params: Dict[str, str],
) -> None:
    """
    Ingests NYC taxi tabular data into a PostgreSQL database.

    Args:
        data: NYC taxi trips tabular data to be ingested into a PostgreSQL database.
        data: NYC taxi trips tabular data to be ingested into a PostgreSQL database.
        pg_params: PostgreSQL database connection parameters.

    Raises:
        ValueError: If provided `pg_params['method']` is unsupported.
    """

    table_trips_dtypes = {
        "tpep_pickup_datetime": sa.types.TIMESTAMP,
        "tpep_dropoff_datetime": sa.types.TIMESTAMP,
        "dt": sa.types.BIGINT,
        "trip_distance": sa.types.REAL,
        "avg_speed": sa.types.REAL,
        "PULocationID": sa.types.INTEGER,
        "DOLocationID": sa.types.INTEGER,
        "RatecodeID": sa.types.INTEGER,
        "passenger_count": sa.types.INTEGER,
        "total_amount": sa.types.REAL,
        "fare_amount": sa.types.REAL,
        "tip_amount": sa.types.REAL,
        "tolls_amount": sa.types.REAL,
        "extra": sa.types.REAL,
        "mta_tax": sa.types.REAL,
        "improvement_surcharge": sa.types.REAL,
        "congestion_surcharge": sa.types.REAL,
        "airport_fee": sa.types.REAL,
        "payment_type": sa.types.INTEGER,
        "VendorID": sa.types.INTEGER,
    }

    table_zones_dtypes = {
        "LocationID": sa.types.INTEGER,
        "Borough": sa.types.String(15),
        "Zone": sa.types.String(45),
        "service_zone": sa.types.String(15),
    }

    # Define the SQLAlchemy engine to enable communications between a client and the given PostgreSQL database.
    url = (
        f"postgresql://{pg_params['username']}:{pg_params['passwd']}"
        f"@{pg_params['host']}:{pg_params['port']}/{pg_params['db']}"
    )
    connect_args = {
        "sslmode": "require",
        "sslrootcert": str(PATHS["certs"]/"server-ca.crt"),
        "sslcert": str(PATHS["certs"]/"fmerinocasallo_writer.crt"),
        "sslkey": str(PATHS["certs"]/"fmerinocasallo_writer.key"),
    }

    engine = sa.create_engine(url=url, connect_args=connect_args)
    _logger.info("SQLAlchemy engine created successfully.")

    chunk_size = int(pg_params["chunk_size"])

    if pg_params["method"] == "psql_insert_copy":
        method = psql_insert_copy
    elif pg_params["method"] == "None":
        method = None
    elif pg_params["method"] == "multi":
        pass
    else:
        raise ValueError(f"Invalid method ({pg_params['method']})")

    # Create a new table to store NYC taxi trips tabular data.
    data_trips.head(n=0).to_sql(
        name=pg_params["table_trips_name"],
        con=engine,
        schema=pg_params["schema"],
        if_exists="replace",
        index=False,
        chunksize=chunk_size,
        method=method,
        dtype=table_trips_dtypes,
    )
    _logger.info(f"New table {pg_params['schema']}.{pg_params['table_trips_name']} created in PostgreSQL database.")

    # Create a new table to store NYC taxi zones tabular data.
    data_zones.head(n=0).to_sql(
        name=pg_params["table_zones_name"],
        con=engine,
        schema=pg_params["schema"],
        if_exists="replace",
        index=False,
        chunksize=chunk_size,
        method=method,
        dtype=table_zones_dtypes,
    )
    _logger.info(f"New table {pg_params['schema']}.{pg_params['table_zones_name']} created in PostgreSQL database.")

    # Import NYC taxi (monthly) trips tabular data into the newly created table.
    data_trips.to_sql(
        name=pg_params["table_trips_name"],
        con=engine,
        schema=pg_params["schema"],
        if_exists="append",
        index=False,
        chunksize=chunk_size,
        method=method,
        dtype=table_trips_dtypes,
    )

    # Import NYC taxi zones tabular data into the newly created table.
    data_zones.to_sql(
        name=pg_params["table_zones_name"],
        con=engine,
        schema=pg_params["schema"],
        if_exists="append",
        index=False,
        chunksize=chunk_size,
        method=method,
        dtype=table_zones_dtypes,
    )

    _logger.info(f"Tabular data (NYC taxi trips & zones) ingested into PostgreSQL database `{pg_params['db']}`.")

    # Grant SELECT permissions (ro) to the `reader` role for the newly created table. Otherwise, `reader`s won't be able
    # to access it.
    query_trips = f"GRANT SELECT ON TABLE {pg_params['schema']}.{pg_params['table_trips_name']} TO reader"
    query_zones = f"GRANT SELECT ON TABLE {pg_params['schema']}.{pg_params['table_zones_name']} TO reader"
    with engine.connect() as conn:
        conn.execute(sa.text(query_trips))
        conn.execute(sa.text(query_zones))
        conn.commit()

    _logger.info(
        "Granted `SELECT` permissions to role `reader` in PostgreSQL new tables "
        f"`{pg_params['schema']}.{pg_params['table_trips_name']}` "
        f"and `{pg_params['schema']}.{pg_params['table_zones_name']}`."
    )

    return None


@click.command()
@click.option(
    '--url-trips',
    type=click.STRING,
    required=True,
    help='Remote url containing NYC taxi trips tabular data to be ingested into a PostgreSQL database.')
@click.option(
    '--url-zones',
    type=click.STRING,
    required=True,
    help='Remote url containing NYC taxi zones tabular data to be ingested into a PostgreSQL database')
@click.option(
    '--fname-trips',
    type=click.Path(resolve_path=True, path_type=Path),
    required=True,
    help='Filename of the to-be-created local copy for NYC taxi trips tabular data.',
)
@click.option(
    '--fname-zones',
    type=click.Path(resolve_path=True, path_type=Path),
    required=True,
    help='Filename of the to-be-created local copy for NYC taxi zones tabular data.',
)
@click.option(
    '--username',
    type=click.STRING,
    required=True,
    help='PostgreSQL username used during data ingestion.',
)
@click.option(
    '--password',
    type=click.Path(exists=True, resolve_path=True, path_type=Path),
    required=True,
    help='PostgreSQL password used during data ingestion.',
)
@click.option(
    '--host',
    type=click.STRING,
    required=True,
    help='PostgreSQL server hostname.',
)
@click.option(
    '--port',
    type=click.INT,
    required=True,
    help='PostgreSQL server port.',
)
@click.option(
    '--db',
    type=click.STRING,
    required=True,
    help='PostgreSQL database destination.',
)
@click.option(
    '--schema',
    type=click.STRING,
    required=True,
    help='PostgreSQL schema destination.',
)
@click.option(
    '--table-trips',
    type=click.STRING,
    required=True,
    help='PostgreSQL table to-be-ingested with imported NYC taxi trips tabular data from remote location (url-trips).',
)
@click.option(
    '--table-zones',
    type=click.STRING,
    required=True,
    help='PostgreSQL table to-be-ingested with imported NYC taxi zones tabular data from remote location (url-zones).',
)
@click.option(
    '--chunk-size-dw',
    type=click.INT,
    default=1024,
    help='Chunk size to-be-used during data downloading.',
)
@click.option(
    '--chunk-size-sql',
    type=click.INT,
    default=1024,
    help='Chunk size to-be-used during data ingestion.',
)
@click.option(
    '--method-sql',
    type=click.Choice(['multi', 'psql_insert_copy', 'None']),
    default="psql_insert_copy",
    help='Controls the SQL insertion clause used.',
)
def main(
    url_trips: str,
    url_zones: str,
    fname_trips: str | bytes | PathLike,
    fname_zones: str | bytes | PathLike,
    username: str,
    password: str | bytes | PathLike,
    host: str,
    port: int,
    db: str,
    schema: str,
    table_trips: str,
    table_zones: str,
    chunk_size_dw: int,
    chunk_size_sql: int,
    method_sql: str,
) -> None:
    """
    Ingest tabular data (NYC taxi trips) into a PostgreSQL database from a remote location (url).

    Args:
        url_trips: Remote url containing NYC taxi trips tabular data to be ingested into a PostgreSQL database.
        url_zones: Remote url containing NYC taxi zones tabular data to be ingested into a PostgreSQL database.
        fname_trips: Filename of the to-be-created local copy for NYC taxi trips tabular data.
        fname_zones: Filename of the to-be-created local copy for NYC taxi zones tabular data.
        username: PostgreSQL username used during data ingestion.
        password: PostgreSQL password used during data ingestion.
        host: PostgreSQL server hostname.
        port: PostgreSQL server port.
        db: PostgreSQL database destination.
        schema: PostgreSQL schema destination.
        table_trips: PostgreSQL table to-be-ingested with imported NYC taxi trips tabular data from `url-trips`.
        table_zones: PostgreSQL table to-be-ingested with imported NYC taxi trips tabular data from `url-zones`.
        chunk_size_dw: Chunk size to-be-used during data downloading.
        chunk_size_sql: Chunk size to-be-used during data ingestion.
        method_sql: Controls the SQL insertion clause used.
    """
    if not validators.url(url_trips):
        raise ValueError(f"[FATAL] url is invalid ({url_trips}). Exiting...")
    else:
        pass

    if not validators.url(url_zones):
        raise ValueError(f"[FATAL] url is invalid ({url_zones}). Exiting...")
    else:
        pass

    fname_trips = sanitize_filepath(fname_trips)
    fname_zones = sanitize_filepath(fname_zones)

    password = open(password).readline().rstrip()

    if not validators.hostname(host, may_have_port=False):
        raise ValueError(f"[FATAL] host is invalid ({host}). Exiting...")
    else:
        pass

    if not (MIN_PORT < port < MAX_PORT):
        raise ValueError(f"[FATAL] port is invalid ({port}). Exiting...")

    db = db.lower()
    if not bool(match("[0-9a-z_]{2,24}$", db)):
        raise ValueError(f"[FATAL] db is invalid ({db}). Exiting...")
    else:
        pass

    schema = schema.lower()
    if not bool(match("[0-9a-z_]{2,24}$", schema)):
        raise ValueError(f"[FATAL] schema is invalid ({schema}). Exiting...")
    else:
        pass

    table_trips_name = table_trips.lower()
    if not bool(match("[0-9a-z_]{2,24}$", table_trips_name)):
        raise ValueError(f"[FATAL] table is invalid ({table_trips_name}). Exiting...")
    else:
        pass

    table_zones_name = table_zones.lower()
    if not bool(match("[0-9a-z_]{2,24}$", table_zones_name)):
        raise ValueError(f"[FATAL] table is invalid ({table_zones_name}). Exiting...")
    else:
        pass

    data_download(url_trips, fname_trips, chunk_size=chunk_size_dw)
    data_download(url_zones, fname_zones, chunk_size=chunk_size_dw)

    data_trips = data_read(fname_trips)
    data_zones = data_read(fname_zones)

    date_start = [int(x) for x in Path(url_trips).stem.split("_")[2].split("-")]
    dates = [
        datetime(year=date_start[0], month=date_start[1], day=1),
        datetime(year=date_start[0], month=date_start[1], day=1) + relativedelta(months=+1),
    ]

    data_trips = data_clean(data_trips, dates)

    pg_params = {
        "username": username,
        "passwd": password,
        "host": host,
        "port": port,
        "db": db,
        "schema": schema,
        "table_trips_name": table_trips_name,
        "table_zones_name": table_zones_name,
        "chunk_size": str(chunk_size_sql),
        "method": method_sql,
    }

    print(f"pg_params: {pg_params}", flush=True)

    data_ingest(data_trips, data_zones, pg_params)

    return None


if __name__ == "__main__":
    main()
