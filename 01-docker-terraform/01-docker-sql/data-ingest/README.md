# NYC Taxi data

## TLC Trip Record Data

Yellow taxi trip records include fields capturing pick-up and drop-off dates/times, pick-up and drop-off locations, trip distances, itemized fares, rate types, payment types, and driver-reported passenger counts. The data used in the attached datasets were collected and provided to the NYC Taxi and Limousine Commission (TLC) by technology providers authorized under the Taxicab & Livery Passenger Enhancement Programs (TPEP/LPEP). The trip data was not created by the TLC, and TLC makes no representations as to the accuracy of these data.

## Additional information
For details about each column content, check [this file provided by the NYC Taxi and Limousine Comission](https://www.nyc.gov/assets/tlc/downloads/pdf/data_dictionary_trip_records_yellow.pdf).

Notes on the different surcharges included in the dataset [^1]:
- Improvement Surcharge: a 30-cent charge on all yellow and green taxis for the Taxi Improvement Fund, which helps pat for accessibility upgrades, including fulfilling the mandate to have enough accessible cabs on New York City streets.

- Congestion Surcharge (est. 2019): adds \$2.50 per ride in yellow taxis, \$2.75 per ride in green taxis and for-hire cars, and 75 cents per passenger for shared rides for all trips that start, end, or pass through Manhattan south of 96th Street.

- MTA State Surcharge (est. 2009): a 50-cent charge towards the MTA.

- Airport Access Fee: \$1.25 for taxi pickups only at LaGuardia and JFK airports and \$2.50 in for-hire drop-offs and pickups at LaGuardia, Newark, and JFK airports.

- Rush Hour Surcharge: metered-fare rides in yellow taxis and green taxis between 4 p.m. and 8 p.m. on weekdays (excluding holidays) cost an extra $1, which goes to the driver. 

- Overnight Surcharge: a 50-cent fee between 8 p.m. and 6 a.m. every day for rides in yellow taxis and metered-fare rides in green taxis. The money goes to the driver.

Note that some entries may be associated with refund operations where some columns/attributes (e.g., `fare_amount`, `tip_amount`, and `total_amount`) could include negative values. For example:

Index | VendorID | tpep_pickup_datetime | tpep_dropoff_datetime | passenger_count | trip_distance | RatecodeID | store_and_fwd_flag | PULocationID | DOLocationID | payment_type | fare_amount | extra | mta_tax | tip_amount | tolls_amount | improvement_surcharge | total_amount | congestion_surcharge | airport_fee |
|----------|----------|----------------------|-----------------------|-----------------|---------------|------------|--------------------|--------------|--------------|--------------|-------------|-------|---------|------------|--------------|-----------------------|--------------|----------------------|-------------|
| 33503    | 2        | 2021-01-02 13:04:07  | 2021-01-02 13:22:59   | 1.0             | 6.24          | 1.0        | N                  | 90           | 228          | 1            | -21.0       | 0.0   | -0.5    | -30.72     | -6.12        | -0.3                  | -61.14       | -2.5                 | NaN         |
| 33504    | 2        | 2021-01-02 13:04:07  | 2021-01-02 13:22:59   | 1.0             | 6.24          | 1.0        | N                  | 90           | 228          | 1            | 21.0        | 0.0   | 0.5     | 30.72      | 6.12         | 0.3                   | 61.14        | 2.5                  | NaN         |
| 1821     | 2        | 2021-01-01 01:14:13  | 2021-01-01 01:24:35   | 1.0             | 3.05          | 1.0        | N                  | 107          | 140          | 2            | -11.0       | -0.5  | -0.5    | 0.0        | 0.0          | -0.3                  | -14.8        | -2.5                 | NaN         |
| 1822     | 2        | 2021-01-01 01:14:13  | 2021-01-01 01:24:35   | 1.0             | 3.05          | 1.0        | N                  | 107          | 140          | 2            | 11.0        | 0.5   | 0.5     | 0.0        | 0.0          | 0.3                   | 14.8         | 2.5                  | NaN         |
772 | 2        | 2021-01-01 00:39:51  | 2021-01-01 00:43:1    | 1.0             | 0.28          | 1.0        | N                  | 236          | 236          | 3            | -4.0        | -0.5  | -0.5    | 0.0        | 0.0          | -0.3                  | -7.8         | -2.5                 | NaN         |
773 | 2        | 2021-01-01 00:39:51  | 2021-01-01 00:43:1    | 1.0             | 0.28          | 1.0        | N                  | 236          | 236          | 2            | 4.0         | 0.5   | 0.5     | 0.0        | 0.0          | 0.3                   | 7.9          | 2.5                  | NaN         |
813 | 2        | 2021-01-01 00:11:01  | 2021-01-01 00:13:56   | 1.0             | 1.13          | 1.0        | N                  | 263          | 75           | 4            | -5.0        | -0.5  | -0.5    | 0.0        | 0.0          | -0.3                  | -8.8         | -2.5                 | NaN         |
814 | 2        | 2021-01-01 00:11:01  | 2021-01-01 00:13:56   | 1.0             | 1.13          | 1.0        | N                  | 263          | 75           | 2            | 5.0         | 0.5   | 0.5     | 0.0        | 0.0          | 0.3                   | 8.8          | 2.5                  | NaN         |

Check the [Taxi Zone Lookup](taxi_zone_lookup.csv) to get the corresponding `Borough` and `Zone` for each `LocationID`.

[^1]: From FOX NY (accessed on 18/06/2024): https://www.fox5ny.com/news/nyc-taxi-uber-lyft-fhv-surcharges-fees
