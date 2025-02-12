## Module 3 Homework

ATTENTION: At the end of the submission form, you will be required to include a link to your GitHub repository or other public code-hosting site. 
This repository should contain your code for solving the homework. If your solution includes code that is not in file format (such as SQL queries or 
shell commands), please include these directly in the README file of your repository.

**IMPORTANT NOTE**: For this homework we will be using the Yellow Taxi Trip Records for **January 2024 - June 2024 NOT the entire year of data** Parquet Files from the New York City Taxi Data found [here](https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page).

If you are using orchestration such as Kestra, Mage, Airflow or Prefect etc. do not load the data into Big Query using the orchestrator.</br> 
Stop with loading the files into a bucket.

**Load Script:** You can manually download the parquet files and upload them to your GCS Bucket or you can use the linked script [here](./load_yellow_taxi_data.py).

You will simply need to generate a Service Account with GCS Admin Priveleges or be authenticated with the Google SDK and update the bucket name in the script to the name of your bucket.

Nothing is fool proof so make sure that all 6 files show in your GCS Bucket before begining

**NOTE**: You will need to use the PARQUET option files when creating an External Table.

**BIG QUERY SETUP**: Create an external table using the Yellow Taxi Trip Records. Create a (regular/materialized) table in BQ using the Yellow Taxi Trip Records (do not partition or cluster this table).

```
-- Create an external table referring to the Yellow Taxi Trip Records from GCS Bucket
CREATE OR REPLACE EXTERNAL TABLE `<GCP_DATASET>.yellow_tripdata_external`
OPTIONS (
  format = 'PARQUET',
  uris = ['gs://<GCP_BUCKET>/yellow_tripdata_2024-*.parquet']
);

-- Check external table with the Yellow Taxi Trip Records from GCS Bucket
SELECT * FROM `<GCP_DATASET>.yellow_tripdata_external` LIMIT 10;

-- Create a non-partitioned table using the Yellow Taxi Trip Records from the External Table
CREATE OR REPLACE TABLE `<GCP_DATASET>.yellow_tripdata_non_partitioned` AS
SELECT * FROM `<GCP_DATASET>.yellow_tripdata_external`;
```

## Question 1:
Question 1: What is count of records for the 2024 Yellow Taxi Data?
- 65,623
- 840,402
- 20,332,093
- 85,431,289

#### Answer:

- 20,332,093

## Question 2:
Write a query to count the distinct number of PULocationIDs for the entire dataset on both the tables.

What is the **estimated amount** of data that will be read when this query is executed on the External Table and the Table?

- 18.82 MB for the External Table and 47.60 MB for the Materialized Table
- 0 MB for the External Table and 155.12 MB for the Materialized Table
- 2.14 GB for the External Table and 0MB for the Materialized Table
- 0 MB for the External Table and 0MB for the Materialized Table

#### Answer:

- 0 MB for the External Table and 155.12 MB for the Materialized Table

```
-- Count distinct PULocationIDs from external table
SELECT COUNT(DISTINCT PULocationID) as distinct_locations 
FROM `<GCP_DATASET>.yellow_tripdata_external`;

-- Count distinct PULocationIDs from materialized table
SELECT COUNT(DISTINCT PULocationID) as distinct_locations
FROM `<GCP_DATASET>.yellow_tripdata_non_partitioned`;
```

## Question 3:
Write a query to retrieve the PULocationID from the table (not the external table) in BigQuery. Now write a query to retrieve the PULocationID and DOLocationID on the same table. Why are the estimated number of Bytes different?
- BigQuery is a columnar database, and it only scans the specific columns requested in the query. Querying two columns (PULocationID, DOLocationID) requires reading more data than querying one column (PULocationID), leading to a higher estimated number of bytes processed.
- BigQuery duplicates data across multiple storage partitions, so selecting two columns instead of one requires scanning the table twice, doubling the estimated bytes processed.
- BigQuery automatically caches the first queried column, so adding a second column increases processing time but does not affect the estimated bytes scanned.
- When selecting multiple columns, BigQuery performs an implicit join operation between them, increasing the estimated bytes processed

#### Answer:

- BigQuery is a columnar database, and it only scans the specific columns requested in the query. Querying two columns (PULocationID, DOLocationID) requires reading more data than querying one column (PULocationID), leading to a higher estimated number of bytes processed.

```
-- Query for PULocationID only
SELECT PULocationID 
FROM `<GCP_DATASET>.yellow_tripdata_non_partitioned`;

-- Query for both PULocationID and DOLocationID
SELECT PULocationID, DOLocationID
FROM `<GCP_DATASET>.yellow_tripdata_non_partitioned`;
```

## Question 4:
How many records have a fare_amount of 0?
- 128,210
- 546,578
- 20,188,016
- 8,333


#### Answer:

- 8,333

```
-- Query to count records with fare_amount of 0
SELECT COUNT(*) as zero_fare_count
FROM `<GCP_DATASET>.yellow_tripdata_non_partitioned`
WHERE fare_amount = 0;
```

## Question 5:
What is the best strategy to make an optimized table in Big Query if your query will always filter based on tpep_dropoff_datetime and order the results by VendorID (Create a new table with this strategy)
- Partition by tpep_dropoff_datetime and Cluster on VendorID
- Cluster on by tpep_dropoff_datetime and Cluster on VendorID
- Cluster on tpep_dropoff_datetime Partition by VendorID
- Partition by tpep_dropoff_datetime and Partition by VendorID


#### Answer:

- Partition by tpep_dropoff_datetime and Cluster on VendorID.

To create a new table with this strategy, you would first partition the table by tpep_dropoff_datetime and then cluster it on VendorID. This approach allows for efficient querying by filtering on tpep_dropoff_datetime and ordering by VendorID:

```
-- Create a partitioned table
CREATE OR REPLACE TABLE `<GCP_DATASET>.yellow_tripdata_partitioned`
PARTITION BY DATE(tpep_dropoff_datetime)
AS
SELECT
  *
FROM
  `<GCP_DATASET>.yellow_tripdata_external`;

-- Create a clustered table
CREATE OR REPLACE TABLE `<GCP_DATASET>.yellow_tripdata_partitioned_clustered`
PARTITION BY DATE(tpep_dropoff_datetime)
CLUSTER BY VendorID
AS
SELECT
  *
FROM
  `<GCP_DATASET>.yellow_tripdata_partitioned`;
```

## Question 6:
Write a query to retrieve the distinct VendorIDs between tpep_dropoff_datetime
2024-03-01 and 2024-03-15 (inclusive)

Use the materialized table you created earlier in your from clause and note the estimated bytes. Now change the table in the from clause to the partitioned table you created for question 5 and note the estimated bytes processed. What are these values?

Choose the answer which most closely matches.

- 12.47 MB for non-partitioned table and 326.42 MB for the partitioned table
- 310.24 MB for non-partitioned table and 26.84 MB for the partitioned table
- 5.87 MB for non-partitioned table and 0 MB for the partitioned table
- 310.31 MB for non-partitioned table and 285.64 MB for the partitioned table


#### Answer:

- 310.24 MB for non-partitioned table and 26.84 MB for the partitioned table

```
-- Query for non-partitioned table
SELECT COUNT(DISTINCT VendorID) as distinct_vendors
FROM `<GCP_DATASET>.yellow_tripdata_non_partitioned`
WHERE DATE(tpep_dropoff_datetime) BETWEEN '2024-03-01' AND '2024-03-15';

-- Query for partitioned table
SELECT COUNT(DISTINCT VendorID) as distinct_vendors
FROM `<GCP_DATASET>.yellow_tripdata_partitioned`
WHERE DATE(tpep_dropoff_datetime) BETWEEN '2024-03-01' AND '2024-03-15';
```

## Question 7: 
Where is the data stored in the External Table you created?

- Big Query
- Container Registry
- GCP Bucket
- Big Table

#### Answer:

- GCP Bucket

## Question 8:
It is best practice in Big Query to always cluster your data:
- True
- False

#### Answer:

- False

Clustering is not always beneficial, it depends on the query pattern. You should only cluster if you are going to be filtering on the clustered column.

[More info about BigQuery Clustered Tables](https://cloud.google.com/bigquery/docs/clustered-tables).

In particular, see [when to use BigQuery Clustering](https://cloud.google.com/bigquery/docs/clustered-tables#when_to_use_clustering).

Note that [you can combine clustering with partitioning to achieve fine-grained sorting for further query optimization](https://cloud.google.com/bigquery/docs/clustered-tables#combine-clustered-partitioned-tables).

## (Bonus: Not worth points) Question 9:
No Points: Write a `SELECT count(*)` query FROM the materialized table you created. How many bytes does it estimate will be read? Why?

#### Answer:

There is no need to read any bytes from the materialized table because the query will return the number of rows in the table directly.

```
-- Query to count records from materialized table
SELECT COUNT(*) as total_records
FROM `<GCP_DATASET>.yellow_tripdata_non_partitioned`;
```

## Submitting the solutions

Form for submitting: https://courses.datatalks.club/de-zoomcamp-2025/homework/hw3