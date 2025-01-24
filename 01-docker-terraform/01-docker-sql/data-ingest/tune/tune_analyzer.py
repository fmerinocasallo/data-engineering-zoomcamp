#!/usr/bin/env python
# coding: utf-8
from os import PathLike
from pathlib import Path

import click
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

plt.rcParams['backend'] = 'TkAgg'


def plot(data: pd.DataFrame, fname: str | bytes | PathLike) -> None:
    """
    Plot PostgreSQL ingestion performance stats.

    Args:
        data: PostgreSQL ingestion performance stats.
        fname: Filename containing plotted figure.
    """
    fig, axs = plt.subplots(nrows=data["method"].nunique(), ncols=2, figsize=(24, 8), layout="constrained")
    for i, method in enumerate(data["method"].unique()):
        if i == (data["method"].nunique()-1):
            legend = "auto"
        else:
            legend = False

        sns.barplot(
            x="chunk_size_dw",
            y="tex",
            hue="chunk_size_sql",
            data=data[data["method"] == method],
            ax=axs[i][0],
            legend=legend,
        )

        sns.barplot(
            x="chunk_size_dw",
            y="mem",
            hue="chunk_size_sql",
            data=data[data["method"] == method],
            ax=axs[i][1],
            legend=legend,
        )

        if i == (data["method"].nunique()-1):
            sns.move_legend(
                axs[i][0],
                bbox_to_anchor=(0.5, -0.75),
                loc='lower center',
                ncol=data["chunk_size_sql"].nunique(),
            )

            sns.move_legend(
                axs[i][1],
                bbox_to_anchor=(0.5, -0.75),
                loc='lower center',
                ncol=data["chunk_size_sql"].nunique(),
            )
        else:
            pass

        axs[i][0].set_title(f"SQL insertion clause used: {method}")
        axs[i][1].set_title(f"SQL insertion clause used: {method}")

    plt.savefig(fname.with_suffix(".png"))


@click.command()
@click.option(
    '--fname',
    type=click.Path(resolve_path=True, path_type=Path),
    required=True,
    help='Filename (PARQUET format) storing performance stats of data-manager.',
)
def main(fname):
    """
    Plot PostgreSQL ingestion performance stats.

    Args:
        fname: Filename (PARQUET format) storing PostgreSQL ingestion performance stats.
    """
    df = pd.read_parquet(fname)
    plot(df, fname)


if __name__ == "__main__":
    main()
