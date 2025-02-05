## Module 2 Homework

ATTENTION: At the end of the submission form, you will be required to include a link to your GitHub repository or other public code-hosting site. This repository should contain your code for solving the homework. If your solution includes code that is not in file format, please include these directly in the README file of your repository.

> In case you don't get one option exactly, select the closest one 

For the homework, we'll be working with the _green_ taxi dataset located here:

`https://github.com/DataTalksClub/nyc-tlc-data/releases/tag/green/download`

To get a `wget`-able link, use this prefix (note that the link itself gives 404):

`https://github.com/DataTalksClub/nyc-tlc-data/releases/download/green/`

### Assignment

So far in the course, we processed data for the year 2019 and 2020. Your task is to extend the existing flows to include data for the year 2021.

![homework datasets](../../../02-workflow-orchestration/images/homework.png)

As a hint, Kestra makes that process really easy:
1. You can leverage the backfill functionality in the [scheduled flow](../../../02-workflow-orchestration/flows/06_gcp_taxi_scheduled.yaml) to backfill the data for the year 2021. Just make sure to select the time period for which data exists i.e. from `2021-01-01` to `2021-07-31`. Also, make sure to do the same for both `yellow` and `green` taxi data (select the right service in the `taxi` input).
2. Alternatively, run the flow manually for each of the seven months of 2021 for both `yellow` and `green` taxi data. Challenge for you: find out how to loop over the combination of Year-Month and `taxi`-type using `ForEach` task which triggers the flow for each combination using a `Subflow` task.

### Quiz Questions

Complete the Quiz shown below. It’s a set of 6 multiple-choice questions to test your understanding of workflow orchestration, Kestra and ETL pipelines for data lakes and warehouses.

1) Within the execution for `Yellow` Taxi data for the year `2020` and month `12`: what is the uncompressed file size (i.e. the output file `yellow_tripdata_2020-12.csv` of the `extract` task)?
- 128.3 MB
- 134.5 MB
- 364.7 MB
- 692.6 MB

#### Answer: 
- 128.3 MB

```
root@456791cbf8a3:/app# ls -lha storage/zoomcamp/02-postgres-taxi/executions/12kcGQLKXibVoGvgvwg1M1/tasks/extract/6zkqiulA09NhiUJfnEcoSw/2zhhMtlyqAjMrPTxMKgdkq-yellow_tripdata_2020-12.csv 
-rw-r--r-- 1 root root 129M Feb  5 20:54 storage/zoomcamp/02-postgres-taxi/executions/12kcGQLKXibVoGvgvwg1M1/tasks/extract/6zkqiulA09NhiUJfnEcoSw/2zhhMtlyqAjMrPTxMKgdkq-yellow_tripdata_2020-12.csv
```

2) What is the rendered value of the variable `file` when the inputs `taxi` is set to `green`, `year` is set to `2020`, and `month` is set to `04` during execution?
- `{{inputs.taxi}}_tripdata_{{inputs.year}}-{{inputs.month}}.csv` 
- `green_tripdata_2020-04.csv`
- `green_tripdata_04_2020.csv`
- `green_tripdata_2020.csv`

#### Answer:
- `green_tripdata_2020-04.csv`

"{{render(vars.file)}}" replaces the `{{inputs.taxi}}`, `{{inputs.year}}`, and `{{inputs.month}}` with their associated
values (i.e., `green`, `2020`, and `04` respectively).

3) How many rows are there for the `Yellow` Taxi data for all CSV files in the year 2020?
- 13,537.299
- 24,648,499
- 18,324,219
- 29,430,127

#### Answer:
- 24,648,499

I manually executed the flow for the `Yellow` taxi data for every month of 2020 using Kestra and counted the total number of rows in the `yellow_tripdata` table located in the `public` schema from the `kestra` database:

```
SELECT
    count(*)
FROM
    public.yellow_tripdata
```

4) How many rows are there for the `Green` Taxi data for all CSV files in the year 2020?
- 5,327,301
- 936,199
- 1,734,051
- 1,342,034

#### Answer: 
- 1,734,051

I manually executed the flow for the `Green` taxi data for every month of 2020 using Kestra and counted the total number of rows in the `green_tripdata` table located in the `public` schema from the `kestra` database:

```
SELECT
    count(*)
FROM
    public.green_tripdata
```

5) How many rows are there for the `Yellow` Taxi data for the March 2021 CSV file?
- 1,428,092
- 706,911
- 1,925,152
- 2,561,031

#### Answer:

- 1,925,152

I manually executed the flow for the `Yellow` taxi data for the month of March 2021 using Kestra and counted the total number of rows in the `yellow_tripdata` table located in the `public` schema from the `kestra` database:

```
SELECT
    count(*)
FROM
    public.yellow_tripdata
WHERE
    filename = 'yellow_tripdata_2021-03.csv'
```

6) How would you configure the timezone to New York in a Schedule trigger?
- Add a `timezone` property set to `EST` in the `Schedule` trigger configuration  
- Add a `timezone` property set to `America/New_York` in the `Schedule` trigger configuration
- Add a `timezone` property set to `UTC-5` in the `Schedule` trigger configuration
- Add a `location` property set to `New_York` in the `Schedule` trigger configuration  

#### Answer:
- Add a `timezone` property set to `America/New_York` in the `Schedule` trigger configuration

According to the [official documentation](https://kestra.io/docs/workflow-components/triggers/schedule-trigger), in a Scheduler trigger, the timezone to New York is set by adding a `timezone` property set to `America/New_York` in the `Schedule` trigger configuration. See the example below of a schedule that runs daily at midnight US Eeastern time:

```
triggers:
  - id: daily
    type: io.kestra.plugin.core.trigger.Schedule
    cron: "@daily"
    timezone: America/New_York
```

## Submitting the solutions

* Form for submitting: https://courses.datatalks.club/de-zoomcamp-2025/homework/hw2
* Check the link above to see the due date

## Solution

Will be added after the due date