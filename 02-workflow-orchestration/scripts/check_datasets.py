#!/usr/bin/env python3
import json
import requests
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from itertools import product

from kestra import Kestra

# Configure logging
# logging.basicConfig(
#     level=logging.WARNING,
#     format='%(asctime)s - %(levelname)s - %(message)s',
#     datefmt='%Y-%m-%d %H:%M:%S'
# )
# logger = logging.getLogger(__name__)
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
    taxis = ["yellow", "green"]
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
    print(json.dumps(list(datasets.keys())))
    print(json.dumps(dict(zip(datasets.keys(), [list(datasets[k].keys()) for k in datasets.keys()]))))
    print(json.dumps(datasets))
    Kestra.outputs(
        {
            "taxis": json.dumps(list(datasets.keys())),
            "years": json.dumps(dict(zip(datasets.keys(), [list(datasets[k].keys()) for k in datasets.keys()]))),
            "months": json.dumps(datasets)
        }
    )

