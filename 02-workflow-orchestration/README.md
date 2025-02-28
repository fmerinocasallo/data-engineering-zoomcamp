# Using Kestra for NYC Taxi data orchestration

## Table of contents
1. [:timer_clock: Schedulers to check datasets availability](#kv-store)
2. [:timer_clock: Schedulers to ingest datasets into local database](#ingestion)


<div id="kv-store"></div>

## :timer_clock: Using job schedulers to check NYC Taxi datasets availability

The `02_postgres_taxi_kv.yaml` Kestra Flow ensures that the Kestra KV store is regularly updated with the latest available NYC taxi datasets from [a remote repository](https://github.com/DataTalksClub/nyc-tlc-data/?tab=readme-ov-file), enabling subsequent workflows to use this information for data processing and analysis.

This flow is scheduled to run weekly, specifically every Monday at midnight in the `Europe/Madrid` timezone.

This Kestra Flow is composed by the following tasks:

First, the **:mag_right: check_datasets** task executes a Python script (`scripts/check_datasets.py`) to verify which monthly datasets are available in [the remote repository](https://github.com/DataTalksClub/nyc-tlc-data/?tab=readme-ov-file).

The script's output includes lists of available taxi types, years, and months.

Note that we are interested in datasets associated with yellow and green taxis, and for hire vehicles.

#### :page_facing_up: FILE `./flows/02_postgres_taxi_kv.yaml`:

```
id: 02_postgres_taxi_kv
namespace: zoomcamp
description: |
  Weekly check (Madrid timezone at midnight) to verify which monthly datasets
  are available in the remote repository for yellow and green taxis, and for
  for hire vehicles, and update the KV store.

concurrency:
  limit: 1

triggers:
  - id: schedule
    type: io.kestra.plugin.core.trigger.Schedule
    cron: "0 0 * * 1"  # every Monday at midnight
    timezone: "Europe/Madrid"

tasks:
  - id: check_datasets
    type: io.kestra.plugin.scripts.python.Commands
    namespaceFiles:
      enabled: true
      include:
        - scripts/check_datasets.py
    commands:
      - python scripts/check_datasets.py
    logLevel: INFO

[...]
```

#### :page_facing_up: FILE `./scripts/check_datasets.py`:
```
#!/usr/bin/env python3

import json
import requests
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from itertools import product

from kestra import Kestra

[...]

logger = Kestra.logger()

def check_url(url):
    try:
        response = requests.head(url, timeout=10)
        success = response.status_code in (200, 302)
        logger.debug(f"Checked URL {url}: {'Found' if success else 'Not found'}")
        return success
    except requests.RequestException as e:
        logger.warning(f"Error checking URL {url}: {str(e)}")
        return False

def check_datasets():
    logger.info("Starting dataset availability check")
    start_year = 2019
    current_year = datetime.now().year
    taxis = ["yellow", "green", "fhv"]
    base_url = "https://github.com/DataTalksClub/nyc-tlc-data/releases/download"
    results = {taxi: {} for taxi in taxis}

    logger.info(f"Checking data from {start_year} to {current_year} for {', '.join(taxis)} taxis")

    # Generate all combinations of taxi, year, and month
    combinations = list(product(
        taxis,
        range(start_year, current_year + 1),
        range(1, 13)
    ))
    
    # Create URLs for all combinations
    urls = [
        (
            taxi,
            year,
            month,
            f"{base_url}/{taxi}/{taxi}_tripdata_{year}-{month:02d}.csv.gz"
        )
        for taxi, year, month in combinations
    ]

    logger.info(f"Generated {len(urls)} URLs to check")

    # Check URLs concurrently
    with ThreadPoolExecutor(max_workers=10) as executor:
        logger.info("Starting concurrent URL checks")
        future_to_url = {
            executor.submit(check_url, url): (taxi, year, month)
            for taxi, year, month, url in urls
        }

        completed = 0
        total = len(future_to_url)
        for future in as_completed(future_to_url):
            taxi, year, month = future_to_url[future]
            completed += 1
            
            if completed % 10 == 0:  # Log progress every 10 requests
                logger.info(f"Progress: {completed}/{total} URLs checked ({(completed/total)*100:.1f}%)")

            if future.result():
                if str(year) not in results[taxi]:
                    results[taxi][str(year)] = []
                results[taxi][str(year)].append(f"{month:02d}")

    # Clean up empty years
    results = {
        taxi: {year: sorted(months) for year, months in sorted(years.items()) if months}
        for taxi, years in results.items()
    }

    logger.info("Dataset check completed")
    for taxi, years in results.items():
        logger.info(f"Found {sum(len(months) for months in years.values())} datasets for {taxi} taxi")

    return results

if __name__ == "__main__":
    datasets = check_datasets()

    Kestra.outputs(
        {
            "taxis": json.dumps(list(datasets.keys())),
            "years": json.dumps(dict(zip(datasets.keys(), [list(datasets[k].keys()) for k in datasets.keys()]))),
            "months": json.dumps(datasets)
        }
    )
```

Next, the `update_kv_taxis` task updates the Kestra Key-Value (KV) store [^1] with the list of available taxi types obtained from the `check_datasets` task. The data is stored in JSON format under the key `taxis`.

#### :page_facing_up: FILE `./flows/02_postgres_taxi_kv.yaml`:
```
[...]

tasks:

  [...]

  - id: update_kv_taxis
    type: io.kestra.plugin.core.kv.Set
    key: taxis
    kvType: JSON
    value: "{{ outputs.check_datasets.vars.taxis }}"

  [...]
```

Then, the `update_kv_years` task updates the Kestra KV store with the list of available years obtained from the `check_datasets` task. The data is stored in JSON format under the key `years`.

#### :page_facing_up: FILE `./flows/02_postgres_taxi_kv.yaml`:
```
[...]

tasks:

  [...]

  - id: update_kv_years
    type: io.kestra.plugin.core.kv.Set
    key: years
    kvType: JSON
    value: "{{ outputs.check_datasets.vars.years }}"

  [...]
```

Finally, the `update_kv_months` task updates the Kestra KV store with the list of available months obtained from the `check_datasets` task. The data is stored in JSON format under the key `months`.

#### :page_facing_up: FILE `./flows/02_postgres_taxi_kv.yaml`:
```
[...]

tasks:

  [...]

  - id: update_kv_months
    type: io.kestra.plugin.core.kv.Set
    key: months
    kvType: JSON
    value: "{{ outputs.check_datasets.vars.months }}"
```

<div id="ingestion"></div>

## :timer_clock: Using job schedulers to ingest NYC Taxi datasets into PostgreSQL database

The `02_postgres_taxi_scheduled.yaml` Kestra Flow automates the process of ingesting NYC taxi datasets into a PostgreSQL database on a scheduled basis. It uses conditional tasks to handle different taxi types and ensures data integrity through staging tables and merge operations. The flow is designed to be triggered automatically, leveraging conditional logic based on user-defined inputs to process different types of taxi data (yellow, green, or fhv [for hire vehicles]). As a result, it enables regular updates to the taxi data in the database.

This Kestra Flow is composed by the following tasks:

First, the `set_label` task sets labels for the Kestra execution, including the filename and taxi type being processed. These labels are useful for tracking and filtering executions in the Kestra UI.

#### :page_facing_up: FILE `./flows/02_postgres_taxi_scheduled.yaml`:
```
id: 02_postgres_taxi_scheduled
namespace: zoomcamp
description: |
  Best to add a label `backfill:true` from the UI to track executions created via a backfill.
  CSV data used here comes from: https://github.com/DataTalksClub/nyc-tlc-data/releases

concurrency:
  limit: 1

inputs:
  - id: taxi
    type: SELECT
    displayName: Select taxi type
    values: [yellow, green, fhv]
    defaults: yellow

variables:
  file: "{{inputs.taxi}}_tripdata_{{trigger.date | date('yyyy-MM')}}.csv"
  staging_table: "public.{{inputs.taxi}}_tripdata_staging"
  table: "public.{{inputs.taxi}}_tripdata"
  data: "{{outputs.extract.outputFiles[inputs.taxi ~ '_tripdata_' ~ (trigger.date | date('yyyy-MM')) ~ '.csv']}}"

tasks:
  - id: set_label
    type: io.kestra.plugin.core.execution.Labels
    labels:
      file: "{{render(vars.file)}}"
      taxi: "{{inputs.taxi}}"

  [...]
```

Next, the `extract` task downloads and extracts the NYC taxi dataset in CSV format from a remote repository. The specific dataset is determined by the selected `taxi` type input and the scheduled execution date (`trigger.date`), which represents the month of the data to be processed.

#### :page_facing_up: FILE `./flows/02_postgres_taxi_scheduled.yaml`:
```
[...]

tasks:

  [...]

  - id: extract
    type: io.kestra.plugin.scripts.shell.Commands
    outputFiles:
      - "*.csv"
    taskRunner:
      type: io.kestra.plugin.core.runner.Process
    commands:
      - wget -qO- https://github.com/DataTalksClub/nyc-tlc-data/releases/download/{{inputs.taxi}}/{{render(vars.file)}}.gz | gunzip > {{render(vars.file)}}

  [...]
```
Then, we uses the `if` plugin [^2] to run different tasks based on the type of taxi (yellow, green, or for hire vehicle) previously selected.

_Note that we could alternative use conditional branching [^3]._

The `if_yellow_taxi` conditional task checks if the selected `taxi` type is `yellow`. If true, it executes the subsequent tasks specifically designed for processing yellow taxi data:

  1. `yellow_create_table`: This task creates the table in the PostgreSQL database to store yellow taxi trip data, if it does not already exist.

#### :page_facing_up: FILE `./flows/02_postgres_taxi_scheduled.yaml`:
```
[...]

tasks:

  [...]

  - id: if_yellow_taxi
    type: io.kestra.plugin.core.flow.If
    condition: "{{inputs.taxi == 'yellow'}}"
    then:
      - id: yellow_create_table
        type: io.kestra.plugin.jdbc.postgresql.Queries
        sql: |
          CREATE TABLE IF NOT EXISTS {{render(vars.table)}} (
              unique_row_id          text,
              filename               text,
              VendorID               text,
              tpep_pickup_datetime   timestamp,
              tpep_dropoff_datetime  timestamp,
              passenger_count        integer,
              trip_distance          double precision,
              RatecodeID             text,
              store_and_fwd_flag     text,
              PULocationID           text,
              DOLocationID           text,
              payment_type           integer,
              fare_amount            double precision,
              extra                  double precision,
              mta_tax                double precision,
              tip_amount             double precision,
              tolls_amount           double precision,
              improvement_surcharge  double precision,
              total_amount           double precision,
              congestion_surcharge   double precision
          );

    [...]

  [...]
```

  2. `yellow_create_staging_table`: This task creates the staging table in the PostgreSQL database to store monthly yellow taxi trip data, if it does not already exist.


#### :page_facing_up: FILE `./flows/02_postgres_taxi_scheduled.yaml`:
```
[...]

tasks:

  [...]

  - id: if_yellow_taxi
    type: io.kestra.plugin.core.flow.If
    condition: "{{inputs.taxi == 'yellow'}}"
    then:

      [...]

      - id: yellow_create_staging_table
        type: io.kestra.plugin.jdbc.postgresql.Queries
        sql: |
          CREATE TABLE IF NOT EXISTS {{render(vars.staging_table)}} (
              unique_row_id          text,
              filename               text,
              VendorID               text,
              tpep_pickup_datetime   timestamp,
              tpep_dropoff_datetime  timestamp,
              passenger_count        integer,
              trip_distance          double precision,
              RatecodeID             text,
              store_and_fwd_flag     text,
              PULocationID           text,
              DOLocationID           text,
              payment_type           integer,
              fare_amount            double precision,
              extra                  double precision,
              mta_tax                double precision,
              tip_amount             double precision,
              tolls_amount           double precision,
              improvement_surcharge  double precision,
              total_amount           double precision,
              congestion_surcharge   double precision
          );

    [...]

  [...]
```

  3. `yellow_truncate_staging_table`: This task truncates the yellow staging table in the PostgreSQL database, preparing it for new data ingestion.


#### :page_facing_up: FILE `./flows/02_postgres_taxi_scheduled.yaml`:
```
[...]

tasks:

  [...]

  - id: if_yellow_taxi
    type: io.kestra.plugin.core.flow.If
    condition: "{{inputs.taxi == 'yellow'}}"
    then:

      [...]

      - id: yellow_truncate_staging_table
        type: io.kestra.plugin.jdbc.postgresql.Queries
        sql: |
          TRUNCATE TABLE {{render(vars.staging_table)}};

    [...]

  [...]
```

  4. `yellow_copy_in_to_staging_table`: This task efficiently copies the downloaded CSV data into the yellow staging table in the PostgreSQL database.


#### :page_facing_up: FILE `./flows/02_postgres_taxi_scheduled.yaml`:
```
[...]

tasks:

  [...]

  - id: if_yellow_taxi
    type: io.kestra.plugin.core.flow.If
    condition: "{{inputs.taxi == 'yellow'}}"
    then:

      [...]

      - id: yellow_copy_in_to_staging_table
        type: io.kestra.plugin.jdbc.postgresql.CopyIn
        format: CSV
        from: "{{render(vars.data)}}"
        table: "{{render(vars.staging_table)}}"
        header: true
        columns: [VendorID,tpep_pickup_datetime,tpep_dropoff_datetime,passenger_count,trip_distance,RatecodeID,store_and_fwd_flag,PULocationID,DOLocationID,payment_type,fare_amount,extra,mta_tax,tip_amount,tolls_amount,improvement_surcharge,total_amount,congestion_surcharge]

    [...]

  [...]
```

  5. `yellow_add_unique_id_and_filename`: This task adds a unique row identifier and the source filename to each record in the yellow staging table to avoid duplicate rows.


#### :page_facing_up: FILE `./flows/02_postgres_taxi_scheduled.yaml`:
```
[...]

tasks:

  [...]

  - id: if_yellow_taxi
    type: io.kestra.plugin.core.flow.If
    condition: "{{inputs.taxi == 'yellow'}}"
    then:

      [...]

      - id: yellow_add_unique_id_and_filename
        type: io.kestra.plugin.jdbc.postgresql.Queries
        sql: |
          UPDATE {{render(vars.staging_table)}}
          SET 
            unique_row_id = md5(
              COALESCE(CAST(VendorID AS text), '') ||
              COALESCE(CAST(tpep_pickup_datetime AS text), '') || 
              COALESCE(CAST(tpep_dropoff_datetime AS text), '') || 
              COALESCE(PULocationID, '') || 
              COALESCE(DOLocationID, '') || 
              COALESCE(CAST(fare_amount AS text), '') || 
              COALESCE(CAST(trip_distance AS text), '')      
            ),
            filename = '{{render(vars.file)}}';

    [...]

  [...]
```

  6. `yellow_merge_data`: This task merges the data from the yellow staging table into the final destination table for yellow taxi trip data. It uses a `MERGE` statement to insert new records and avoid duplicates based on the unique row identifier.


#### :page_facing_up: FILE `./flows/02_postgres_taxi_scheduled.yaml`:
```
[...]

tasks:

  [...]

  - id: if_yellow_taxi
    type: io.kestra.plugin.core.flow.If
    condition: "{{inputs.taxi == 'yellow'}}"
    then:

      [...]

      - id: yellow_merge_data
        type: io.kestra.plugin.jdbc.postgresql.Queries
        sql: |
          MERGE INTO {{render(vars.table)}} AS T
          USING {{render(vars.staging_table)}} AS S
          ON T.unique_row_id = S.unique_row_id
          WHEN NOT MATCHED THEN
            INSERT (
              unique_row_id, filename, VendorID, tpep_pickup_datetime, tpep_dropoff_datetime,
              passenger_count, trip_distance, RatecodeID, store_and_fwd_flag, PULocationID,
              DOLocationID, payment_type, fare_amount, extra, mta_tax, tip_amount, tolls_amount,
              improvement_surcharge, total_amount, congestion_surcharge
            )
            VALUES (
              S.unique_row_id, S.filename, S.VendorID, S.tpep_pickup_datetime, S.tpep_dropoff_datetime,
              S.passenger_count, S.trip_distance, S.RatecodeID, S.store_and_fwd_flag, S.PULocationID,
              S.DOLocationID, S.payment_type, S.fare_amount, S.extra, S.mta_tax, S.tip_amount, S.tolls_amount,
              S.improvement_surcharge, S.total_amount, S.congestion_surcharge
            );

  [...]
```

The `if_green_taxi` conditional task checks if the selected `taxi` type is `green`. If true, it executes the subsequent tasks specifically designed for processing green taxi data, following the same structure we have already seen for the yellow taxi.

Lastly, the `if_fhv_taxi` conditional task checks if the selected `taxi` type is `fhv` (for hire vehicle). If true, it executes the subsequent tasks specifically designed for processing for hire vehicles data, following the same structure we have already seen for the yellow and green taxi.

_Note that in the for hire vehicle case, there are relevant differences because the data associated to this datasets is not identical to the yellow and green taxi, as you can see in the `fhv_create_table` task._

#### :page_facing_up: FILE `./flows/02_postgres_taxi_scheduled.yaml`:
```
[...]

tasks:

  [...]

  - id: if_fhv_taxi
    type: io.kestra.plugin.core.flow.If
    condition: "{{inputs.taxi == 'fhv'}}"
    then:
      - id: fhv_create_table
        type: io.kestra.plugin.jdbc.postgresql.Queries
        sql: |
          CREATE TABLE IF NOT EXISTS {{render(vars.table)}} (
              unique_row_id          text,
              filename               text,
              dispatching_base_num   text,
              pickup_datetime        timestamp,
              dropoff_datetime       timestamp,
              PULocationID           text,
              DOLocationID           text,
              sr_flag                integer,
              affiliated_base_number text
          );

    [...]

  [...]
```

[^1]: From Kestra official documentation: Key Value (KV) Store (accessed 07/02/2025): https://kestra.io/docs/concepts/kv-store
[^2]: From Kestra official documentation: If (accessed 07/02/2025): https://kestra.io/plugins/core/flow/io.kestra.plugin.core.flow.if
[^3]: From Kestra official documentation: Conditional Branching (accessed 07/02/2025): https://kestra.io/docs/how-to-guides/conditional-branching