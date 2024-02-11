import datetime

import click
import numpy as np
import pandas as pd


@click.command()
@click.option("-d", "--n_days", default=10, show_default=True, help='Number of days.')
def rd_series(n_days: int = 10) -> pd.Series:
    today = datetime.date.today()
    data = np.random.randint(10, size=n_days, dtype=int)
    dates = pd.date_range(today, periods=n_days)

    return pd.Series(data=data, index=dates)


if __name__ == "__main__":
    ts = rd_series(standalone_mode=False)
    print(f"ts: {ts}")
