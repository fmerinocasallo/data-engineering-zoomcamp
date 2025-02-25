## Module 4 Homework

For this homework, you will need the following datasets:
* [Green Taxi dataset (2019 and 2020)](https://github.com/DataTalksClub/nyc-tlc-data/releases/tag/green)
* [Yellow Taxi dataset (2019 and 2020)](https://github.com/DataTalksClub/nyc-tlc-data/releases/tag/yellow)
* [For Hire Vehicle dataset (2019)](https://github.com/DataTalksClub/nyc-tlc-data/releases/tag/fhv)

### Before you start

1. Make sure you, **at least**, have them in GCS with a External Table **OR** a Native Table - use whichever method you prefer to accomplish that (Workflow Orchestration with [pandas-gbq](https://cloud.google.com/bigquery/docs/samples/bigquery-pandas-gbq-to-gbq-simple), [dlt for gcs](https://dlthub.com/docs/dlt-ecosystem/destinations/filesystem), [dlt for BigQuery](https://dlthub.com/docs/dlt-ecosystem/destinations/bigquery), [gsutil](https://cloud.google.com/storage/docs/gsutil), etc)
2. You should have exactly `7,778,101` records in your Green Taxi table
3. You should have exactly `109,047,518` records in your Yellow Taxi table
4. You should have exactly `43,244,696` records in your FHV table
5. Build the staging models for green/yellow as shown in [here](../../../04-analytics-engineering/taxi_rides_ny/models/staging/)
6. Build the dimension/fact for taxi_trips joining with `dim_zones`  as shown in [here](../../../04-analytics-engineering/taxi_rides_ny/models/core/fact_trips.sql)

**Note**: If you don't have access to GCP, you can spin up a local Postgres instance and ingest the datasets above


### Question 1: Understanding dbt model resolution

Provided you've got the following sources.yaml
```yaml
version: 2

sources:
  - name: raw_nyc_tripdata
    database: "{{ env_var('DBT_BIGQUERY_PROJECT', 'dtc_zoomcamp_2025') }}"
    schema:   "{{ env_var('DBT_BIGQUERY_SOURCE_DATASET', 'raw_nyc_tripdata') }}"
    tables:
      - name: ext_green_taxi
      - name: ext_yellow_taxi
```

with the following env variables setup where `dbt` runs:
```shell
export DBT_BIGQUERY_PROJECT=myproject
export DBT_BIGQUERY_DATASET=my_nyc_tripdata
```

What does this .sql model compile to?
```sql
select * 
from {{ source('raw_nyc_tripdata', 'ext_green_taxi' ) }}
```

- `select * from dtc_zoomcamp_2025.raw_nyc_tripdata.ext_green_taxi`
- `select * from dtc_zoomcamp_2025.my_nyc_tripdata.ext_green_taxi`
- `select * from myproject.raw_nyc_tripdata.ext_green_taxi`
- `select * from myproject.my_nyc_tripdata.ext_green_taxi`
- `select * from dtc_zoomcamp_2025.raw_nyc_tripdata.green_taxi`

#### Answer:
:white_check_mark: `select * from myproject.raw_nyc_tripdata.ext_green_taxi`

Note that:
1. `env_var('DBT_BIGQUERY_PROJECT', 'dtc_zoomcamp_2025')` compiles to `myproject` because of `export DBT_BIGQUERY_PROJECT=myproject`.
2. `env_var('DBT_BIGQUERY_SOURCE_DATASET', 'raw_nyc_tripdata')` compiles to `raw_nyc_tripdata` because `DBT_BIGQUERY_SOURCE_DATASET` is not defined.

### Question 2: dbt Variables & Dynamic Models

Say you have to modify the following dbt_model (`fct_recent_taxi_trips.sql`) to enable Analytics Engineers to dynamically control the date range. 

- In development, you want to process only **the last 7 days of trips**
- In production, you need to process **the last 30 days** for analytics

```sql
select *
from {{ ref('fact_taxi_trips') }}
where pickup_datetime >= CURRENT_DATE - INTERVAL '30' DAY
```

What would you change to accomplish that in a such way that command line arguments takes precedence over ENV_VARs, which takes precedence over DEFAULT value?

- Add `ORDER BY pickup_datetime DESC` and `LIMIT {{ var("days_back", 30) }}`
- Update the WHERE clause to `pickup_datetime >= CURRENT_DATE - INTERVAL '{{ var("days_back", 30) }}' DAY`
- Update the WHERE clause to `pickup_datetime >= CURRENT_DATE - INTERVAL '{{ env_var("DAYS_BACK", "30") }}' DAY`
- Update the WHERE clause to `pickup_datetime >= CURRENT_DATE - INTERVAL '{{ var("days_back", env_var("DAYS_BACK", "30")) }}' DAY`
- Update the WHERE clause to `pickup_datetime >= CURRENT_DATE - INTERVAL '{{ env_var("DAYS_BACK", var("days_back", "30")) }}' DAY`

#### Answer:
:white_check_mark: Update the WHERE clause to `pickup_datetime >= CURRENT_DATE - INTERVAL '{{ var("days_back", env_var("DAYS_BACK", "30")) }}' DAY`.

### Question 3: dbt Data Lineage and Execution

Considering the data lineage below **and** that taxi_zone_lookup is the **only** materialization build (from a .csv seed file):

![image](./homework_q2.png)

Select the option that does **NOT** apply for materializing `fct_taxi_monthly_zone_revenue`:

- `dbt run`
- `dbt run --select +models/core/dim_taxi_trips.sql+ --target prod`
- `dbt run --select +models/core/fct_taxi_monthly_zone_revenue.sql`
- `dbt run --select +models/core/`
- `dbt run --select models/staging/+`

#### Answer:
:white_check_mark: `dbt run --select models/staging/+`

Note that `fct_taxi_monthly_zone_revenue.sql` is not located in the `models/staging` directory but in `models/core/`.

### Question 4: dbt Macros and Jinja

Consider you're dealing with sensitive data (e.g.: [PII](https://en.wikipedia.org/wiki/Personal_data)), that is **only available to your team and very selected few individuals**, in the `raw layer` of your DWH (e.g: a specific BigQuery dataset or PostgreSQL schema), 

 - Among other things, you decide to obfuscate/masquerade that data through your staging models, and make it available in a different schema (a `staging layer`) for other Data/Analytics Engineers to explore

- And **optionally**, yet  another layer (`service layer`), where you'll build your dimension (`dim_`) and fact (`fct_`) tables (assuming the [Star Schema dimensional modeling](https://www.databricks.com/glossary/star-schema)) for Dashboarding and for Tech Product Owners/Managers

You decide to make a macro to wrap a logic around it:

```sql
{% macro resolve_schema_for(model_type) -%}

    {%- set target_env_var = 'DBT_BIGQUERY_TARGET_DATASET'  -%}
    {%- set stging_env_var = 'DBT_BIGQUERY_STAGING_DATASET' -%}

    {%- if model_type == 'core' -%} {{- env_var(target_env_var) -}}
    {%- else -%}                    {{- env_var(stging_env_var, env_var(target_env_var)) -}}
    {%- endif -%}

{%- endmacro %}
```

And use on your staging, dim_ and fact_ models as:
```sql
{{ config(
    schema=resolve_schema_for('core'), 
) }}
```

That all being said, regarding macro above, **select all statements that are true to the models using it**:
- Setting a value for  `DBT_BIGQUERY_TARGET_DATASET` env var is mandatory, or it'll fail to compile
- Setting a value for `DBT_BIGQUERY_STAGING_DATASET` env var is mandatory, or it'll fail to compile
- When using `core`, it materializes in the dataset defined in `DBT_BIGQUERY_TARGET_DATASET`
- When using `stg`, it materializes in the dataset defined in `DBT_BIGQUERY_STAGING_DATASET`, or defaults to `DBT_BIGQUERY_TARGET_DATASET`
- When using `staging`, it materializes in the dataset defined in `DBT_BIGQUERY_STAGING_DATASET`, or defaults to `DBT_BIGQUERY_TARGET_DATASET`

#### Answer(s):
:white_check_mark: Setting a value for  `DBT_BIGQUERY_TARGET_DATASET` env var is mandatory, or it'll fail to compile.
:white_check_mark: When using `core`, it materializes in the dataset defined in `DBT_BIGQUERY_TARGET_DATASET`.
:white_check_mark: When using `stg`, it materializes in the dataset defined in `DBT_BIGQUERY_STAGING_DATASET`, or defaults to `DBT_BIGQUERY_TARGET_DATASET`.
:white_check_mark: When using `staging`, it materializes in the dataset defined in `DBT_BIGQUERY_STAGING_DATASET`, or defaults to `DBT_BIGQUERY_TARGET_DATASET`.

## Serious SQL

Alright, in module 1, you had a SQL refresher, so now let's build on top of that with some serious SQL.

These are not meant to be easy - but they'll boost your SQL and Analytics skills to the next level.  
So, without any further do, let's get started...

You might want to add some new dimensions `year` (e.g.: 2019, 2020), `quarter` (1, 2, 3, 4), `year_quarter` (e.g.: `2019/Q1`, `2019/Q2`), and `month` (e.g.: 1, 2, ..., 12), **extracted from pickup_datetime**, to your `fct_taxi_trips` OR `dim_taxi_trips.sql` models to facilitate filtering your queries


### Question 5: Taxi Quarterly Revenue Growth

1. Create a new model `fct_taxi_trips_quarterly_revenue.sql`
2. Compute the Quarterly Revenues for each year for based on `total_amount`
3. Compute the Quarterly YoY (Year-over-Year) revenue growth 
  * e.g.: In 2020/Q1, Green Taxi had -12.34% revenue growth compared to 2019/Q1
  * e.g.: In 2020/Q4, Yellow Taxi had +34.56% revenue growth compared to 2019/Q4

Considering the YoY Growth in 2020, which were the yearly quarters with the best (or less worse) and worst results for green, and yellow

- green: {best: 2020/Q2, worst: 2020/Q1}, yellow: {best: 2020/Q2, worst: 2020/Q1}
- green: {best: 2020/Q2, worst: 2020/Q1}, yellow: {best: 2020/Q3, worst: 2020/Q4}
- green: {best: 2020/Q1, worst: 2020/Q2}, yellow: {best: 2020/Q2, worst: 2020/Q1}
- green: {best: 2020/Q1, worst: 2020/Q2}, yellow: {best: 2020/Q1, worst: 2020/Q2}
- green: {best: 2020/Q1, worst: 2020/Q2}, yellow: {best: 2020/Q3, worst: 2020/Q4}

#### Answer:
:white_check_mark: green: {best: 2020/Q1, worst: 2020/Q2}, yellow: {best: 2020/Q1, worst: 2020/Q2}

```
-- Step 1: Add new dimensions (year, quarter, month)
ALTER TABLE public.green_tripdata
ADD COLUMN year INT,
ADD COLUMN quarter INT,
ADD COLUMN month INT;

UPDATE public.green_tripdata
SET year = EXTRACT(YEAR FROM lpep_pickup_datetime),
    quarter = EXTRACT(QUARTER FROM lpep_pickup_datetime),
    month = EXTRACT(MONTH FROM lpep_pickup_datetime);

-- Step 2: Compute Quarterly Revenues for each year
WITH GreenTaxiTrips AS (
	SELECT
		*,
		row_number() over(partition by vendorid, lpep_pickup_datetime) as rn
	FROM
		public.green_tripdata
	WHERE
		vendorid IS NOT NULL
        AND (PULocationID != '264')
        AND (DOLocationID != '264')
),

QuarterlyRevenue AS (
    SELECT
        year,
        quarter,
        SUM(total_amount) AS quarterly_revenue
    FROM
        GreenTaxiTrips
	WHERE
		rn = 1
    GROUP BY
        year,
        quarter
),

-- Step 3: Compute Quarterly YoY Revenue Growth using LAG function
LaggedQuarterlyRevenue AS (
    SELECT
        year,
        quarter,
        quarterly_revenue,
        LAG(quarterly_revenue, 4, 0) OVER (ORDER BY year, quarter) AS previous_year_quarterly_revenue
    FROM
        QuarterlyRevenue
),

YoYGrowth AS (
    SELECT
        year,
        quarter,
        quarterly_revenue,
        (quarterly_revenue - previous_year_quarterly_revenue) * 100.0 / NULLIF(previous_year_quarterly_revenue, 0) AS yoy_growth_percentage
    FROM
        LaggedQuarterlyRevenue
    WHERE year = 2020 -- Filter for 2020 data after calculating YoY growth
),

RankedYoYGrowth AS (
  SELECT
        year,
        quarter,
        quarterly_revenue,
        yoy_growth_percentage,
        RANK() OVER (ORDER BY yoy_growth_percentage DESC NULLS LAST) as yoy_growth_rank  -- Rank from best (highest growth) to worst (lowest growth)
    FROM
        YoYGrowth
    WHERE yoy_growth_percentage IS NOT NULL -- Exclude NULLs for ranking
)

SELECT
        year,
        quarter,
        (ROUND(yoy_growth_percentage::numeric, 2) || ' %') as yoy_growth_percentage,
		yoy_growth_rank
FROM RankedYoYGrowth
ORDER BY yoy_growth_rank; -- Order chronologically for easy understanding
```

| year | quarter | yoy_growth_percentage | yoy_growth_rank |
|---|---|---|---|
| 2020 | 1 | -56.39 % | 1 |
| 2020 | 4 | -84.28 % | 2 |
| 2020 | 3 | -86.50 % | 3 |
| 2020 | 2 | -92.76 % | 4 |

```
-- Step 1: Add new dimensions (year, quarter, month)
ALTER TABLE public.yellow_tripdata
ADD COLUMN year INT,
ADD COLUMN quarter INT,
ADD COLUMN month INT;

UPDATE public.yellow_tripdata
SET year = EXTRACT(YEAR FROM tpep_pickup_datetime),
    quarter = EXTRACT(QUARTER FROM tpep_pickup_datetime),
    month = EXTRACT(MONTH FROM tpep_pickup_datetime);

-- Step 2: Compute Quarterly Revenues for each year
WITH YellowTaxiTrips AS (
	SELECT
		*,
		row_number() over(partition by vendorid, tpep_pickup_datetime) as rn
	FROM
		public.yellow_tripdata
	WHERE
		vendorid IS NOT NULL
        AND (PULocationID != '264')
        AND (DOLocationID != '264')
),

QuarterlyRevenue AS (
    SELECT
        year,
        quarter,
        SUM(total_amount) AS quarterly_revenue
    FROM
        YellowTaxiTrips
	WHERE
		rn = 1
    GROUP BY
        year,
        quarter
),

-- Step 3: Compute Quarterly YoY Revenue Growth using LAG function
LaggedQuarterlyRevenue AS (
    SELECT
        year,
        quarter,
        quarterly_revenue,
        LAG(quarterly_revenue, 4, 0) OVER (ORDER BY year, quarter) AS previous_year_quarterly_revenue
    FROM
        QuarterlyRevenue
),

YoYGrowth AS (
    SELECT
        year,
        quarter,
        quarterly_revenue,
        (quarterly_revenue - previous_year_quarterly_revenue) * 100.0 / NULLIF(previous_year_quarterly_revenue, 0) AS yoy_growth_percentage
    FROM
        LaggedQuarterlyRevenue
    WHERE year = 2020 -- Filter for 2020 data after calculating YoY growth
),

RankedYoYGrowth AS (
  SELECT
        year,
        quarter,
        quarterly_revenue,
        yoy_growth_percentage,
        RANK() OVER (ORDER BY yoy_growth_percentage DESC NULLS LAST) as yoy_growth_rank  -- Rank from best (highest growth) to worst (lowest growth)
    FROM
        YoYGrowth
    WHERE yoy_growth_percentage IS NOT NULL -- Exclude NULLs for ranking
)

SELECT
        year,
        quarter,
        (ROUND(yoy_growth_percentage::numeric, 2) || ' %') as yoy_growth_percentage,
		yoy_growth_rank
FROM RankedYoYGrowth
ORDER BY yoy_growth_rank; -- Order chronologically for easy understanding
```

| year | quarter | yoy_growth_percentage | yoy_growth_rank |
|---|---|---|---|
| 2020 | 1 | "-21.21 %" | 1 |
| 2020 | 4 | "-70.43 %" | 2 |
| 2020 | 3 | "-78.03 %" | 3 |
| 2020 | 2 | "-92.26 %" | 4 |

### Question 6: P97/P95/P90 Taxi Monthly Fare

1. Create a new model `fct_taxi_trips_monthly_fare_p95.sql`
2. Filter out invalid entries (`fare_amount > 0`, `trip_distance > 0`, and `payment_type_description in ('Cash', 'Credit Card')`)
3. Compute the **continous percentile** of `fare_amount` partitioning by service_type, year and and month

Now, what are the values of `p97`, `p95`, `p90` for Green Taxi and Yellow Taxi, in April 2020?

- green: {p97: 55.0, p95: 45.0, p90: 26.5}, yellow: {p97: 52.0, p95: 37.0, p90: 25.5}
- green: {p97: 55.0, p95: 45.0, p90: 26.5}, yellow: {p97: 31.5, p95: 25.5, p90: 19.0}
- green: {p97: 40.0, p95: 33.0, p90: 24.5}, yellow: {p97: 52.0, p95: 37.0, p90: 25.5}
- green: {p97: 40.0, p95: 33.0, p90: 24.5}, yellow: {p97: 31.5, p95: 25.5, p90: 19.0}
- green: {p97: 55.0, p95: 45.0, p90: 26.5}, yellow: {p97: 52.0, p95: 25.5, p90: 19.0}

#### Answer:
:white_check_mark: green: {p97: 55.0, p95: 45.0, p90: 26.5}, yellow: {p97: 31.5, p95: 25.5, p90: 19.0}

```
WITH GreenTaxiTrips AS (
    SELECT
        *,
        row_number() over(partition by vendorid, lpep_pickup_datetime) as rn
    FROM
        public.green_tripdata
    WHERE
        vendorid IS NOT NULL
        AND (PULocationID != '264')
        AND (DOLocationID != '264')
),

ValidTrips AS (
    SELECT
        year,
        month,
        fare_amount
    FROM
        GreenTaxiTrips
    WHERE
        (rn = 1)
        AND (year = 2020)
        AND (month = 4)
        AND (fare_amount > 0)
        AND (trip_distance > 0)
        AND (payment_type IN (1, 2)) -- Filter for valid trips (Credit Card or Cash)
)

SELECT
    PERCENTILE_CONT(0.97) WITHIN GROUP (ORDER BY fare_amount) AS p97,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY fare_amount) AS p95,
    PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY fare_amount) AS p90
FROM
    ValidTrips
WHERE
    (year = 2020)
    AND (month = 4);
```

| p97 | p95 | p90 |
|---|---|---|
| 55 | 45.5 | 27 |

```
WITH YellowTaxiTrips AS (
    SELECT
        *,
        row_number() over(partition by vendorid, tpep_pickup_datetime) as rn
    FROM
        public.yellow_tripdata
    WHERE
        vendorid IS NOT NULL
        AND (PULocationID != '264')
        AND (DOLocationID != '264')
),

ValidTrips AS (
    SELECT
        year,
        month,
        fare_amount
    FROM
        YellowTaxiTrips
    WHERE
        (rn = 1)
        AND (year = 2020)
        AND (month = 4)
        AND (fare_amount > 0)
        AND (trip_distance > 0)
        AND (payment_type IN (1, 2)) -- Filter for valid trips (Credit Card or Cash)
)

SELECT
    PERCENTILE_CONT(0.97) WITHIN GROUP (ORDER BY fare_amount) AS p97,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY fare_amount) AS p95,
    PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY fare_amount) AS p90
FROM
    ValidTrips
WHERE
    (year = 2020)
    AND (month = 4);
```

| p97 | p95 | p90 |
|---|---|---|
| 32.5 | 26 | 19 |

### Question 7: Top #Nth longest P90 travel time Location for FHV

Prerequisites:
* Create a staging model for FHV Data (2019), and **DO NOT** add a deduplication step, just filter out the entries where `where dispatching_base_num is not null`
* Create a core model for FHV Data (`dim_fhv_trips.sql`) joining with `dim_zones`. Similar to what has been done [here](../../../04-analytics-engineering/taxi_rides_ny/models/core/fact_trips.sql)
* Add some new dimensions `year` (e.g.: 2019) and `month` (e.g.: 1, 2, ..., 12), based on `pickup_datetime`, to the core model to facilitate filtering for your queries

Now...
1. Create a new model `fct_fhv_monthly_zone_traveltime_p90.sql`
2. For each record in `dim_fhv_trips.sql`, compute the [timestamp_diff](https://cloud.google.com/bigquery/docs/reference/standard-sql/timestamp_functions#timestamp_diff) in seconds between dropoff_datetime and pickup_datetime - we'll call it `trip_duration` for this exercise
3. Compute the **continous** `p90` of `trip_duration` partitioning by year, month, pickup_location_id, and dropoff_location_id

For the Trips that **respectively** started from `Newark Airport`, `SoHo`, and `Yorkville East`, in November 2019, what are **dropoff_zones** with the 2nd longest p90 trip_duration ?

- LaGuardia Airport, Chinatown, Garment District
- LaGuardia Airport, Park Slope, Clinton East
- LaGuardia Airport, Saint Albans, Howard Beach
- LaGuardia Airport, Rosedale, Bath Beach
- LaGuardia Airport, Yorkville East, Greenpoint

#### Answer:
:white_check_mark: LaGuardia Airport (LocationID = '1'), Chinatown (LocationID = '211'), Garment District (LocationID = '262')

```
-- Step 1: Add new dimensions (year, quarter, month)
ALTER TABLE public.fhv_tripdata
ADD COLUMN year INT,
ADD COLUMN month INT;

UPDATE public.fhv_tripdata
SET year = EXTRACT(YEAR FROM pickup_datetime),
    month = EXTRACT(MONTH FROM pickup_datetime);

WITH TripDurations AS (
    SELECT
        year,
        month,
        PULocationID,
        DOLocationID,
        dropoff_datetime,
        pickup_datetime,
        EXTRACT(EPOCH FROM (dropoff_datetime - pickup_datetime)) AS trip_duration  -- Trip duration in seconds
    FROM
        public.fhv_tripdata
    WHERE
        dispatching_base_num IS NOT NULL
        AND PULocationID != '264'
        AND DOLocationID != '264'
),

TripDurationsP90 AS (
    SELECT
        year,
        month,
        PULocationID,
        DOLocationID,
        percentile_cont(0.9) WITHIN GROUP (ORDER BY trip_duration) AS trip_duration_p90
    FROM 
        TripDurations
    WHERE 
        PULocationID IN ('1', '211', '262')
        AND (year = 2019)
        AND (month = 11)
    GROUP BY
        year,
        month,
        PULocationID,
        DOLocationID
    ORDER BY
        year,
        month,
        PULocationID,
        DOLocationID
),

RankedTripDurations AS (
    SELECT 
        PULocationID,
        DOLocationID,
        trip_duration_p90,
        RANK() OVER (PARTITION BY PULocationID ORDER BY trip_duration_p90 DESC) AS rnk
    FROM 
        TripDurationsP90
)

SELECT
    PULocationID,
    DOLocationID
FROM 
    RankedTripDurations
WHERE 
    rnk = 2
ORDER BY
    PULocationID,
    DOLocationID;

```

| PULocationID | DOLocationID |
|---|---|
| 1 | 138 |
| 211 | 45 |
| 262 | 100 |

## Submitting the solutions

* Form for submitting: https://courses.datatalks.club/de-zoomcamp-2025/homework/hw4


## Solution 

* To be published after deadline