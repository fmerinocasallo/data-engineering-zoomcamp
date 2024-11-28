#!/usr/bin/env python
# coding: utf-8
from os import PathLike
from pathlib import Path
import re

import click
import pandas as pd


def convert_time(eta: str) -> float:
    """
    Convert time values in various units ([hours:minutes:]seconds) to seconds.

    Args:
        eta: Elapsed real (wall clock) time used by the process, in [hours:minutes:]seconds.

    Returns:
        Elapsed real (wall clock) time used by the process, in seconds.

    Raises:
        ValueError: If unable to parse `eta`.
    """
    match = re.search(r"(\d+:\d+:\d+\.\d+|\d+:\d+\.\d+|\d+\.\d+)", eta)
    if match:
        eta = match.group(1)
        # Convert the elapsed time string to a float, handling different formats
        if ":" in eta:
            if len(eta.split(":")) == 3:  # Hours, minutes, seconds
                hours, minutes, seconds = eta.split(":")
                tex = int(hours) * 3600 + int(minutes) * 60 + float(seconds)
            else:  # Minutes, seconds
                minutes, seconds = eta.split(":")
                tex = int(minutes) * 60 + float(seconds)
        else:  # Seconds only
            tex = float(eta)
    else:
        raise ValueError("Unable to parse `eta`: {eta}.")

    return tex


def convert_mem(mem_amount: float, mem_units: str) -> float:
    """
    Convert memory values in various units (GB, MB, and KB) to KB.

    Args:
        mem_amount: Maximum resident set size of the process during its lifetime.
        mem_units: Memory size units (e.g., "KB", "MB", "GB").

    Returns:
        Maximum resident set size of the process during its lifetime, in Kilobytes.

    Raises:
        ValueError: If unable to parse `eta`.
    """
    if mem_units == "KB":
        pass
    elif mem_units == "MB":
        mem_amount *= 1024
    elif mem_units == "GB":
        mem_amount *= 1024**2
    else:
        raise ValueError(f"[FATAL] mem_units is invalid ({mem_units}).")

    return mem_amount


def parse(fname: str | bytes | PathLike) -> pd.DataFrame:
    """
    Parse PostgreSQL ingestion performance stats.

    Args:
        fname: local path where PostgreSQL ingestion performance stats are stored (TXT format).

    Returns:
        Parsed PostgreSQL ingestion performance stats.
    """
    with open(fname, 'r') as f:
        content = f.readlines()

    data = []
    pattern = pattern = r"chunk_size_dw=(\d+) - chunk_size_sql=(\d+) - method=([A-Za-z]+)"
    chunk_size_dw, chunk_size_sql, method, tex, mem = 0, 0, "", 0., 0.
    for line in content:
        if line.startswith("chunk_size_dw"):
            chunk_size_dw, chunk_size_sql, method = re.match(pattern, line.rstrip()).groups()
        elif line.startswith("Took"):
            data_i = line.rstrip().split(" ")

            tex = convert_time(data_i[1])
            mem = convert_mem(float(data_i[3]), data_i[4])

            data.append([chunk_size_dw, chunk_size_sql, method, tex, mem])
        else:
            pass

    return pd.DataFrame(data=data, columns=["chunk_size_dw", "chunk_size_sql", "method", "tex", "mem"])


@click.command()
@click.option(
    '--fname',
    type=click.Path(resolve_path=True, path_type=Path),
    required=True,
    help='Filename (TXT format) storing performance stats of data-manager.',
)
def main(fname):
    """
    Parse PostgreSQL ingestion performance stats.

    Args:
        fname: local path where PostgreSQL ingestion performance stats are stored (TXT format).
    """
    parse(fname).to_parquet(fname.with_suffix(".parquet"))


if __name__ == "__main__":
    main()
