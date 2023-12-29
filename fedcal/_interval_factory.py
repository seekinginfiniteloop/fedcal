# fedcal _interval_factory.py
#
# Copyright (c) 2023 Adam Poulemanos. All rights reserved.
#
# fedcal is open source software subject to the terms of the
# MIT license, found in the
# [GitHub source directory](https://github.com/psuedomagi/fedcal)
# in the LICENSE.md file.
#
# It may be freely distributed, reused, modified, and distributed under the
# terms of that license, but must be accompanied by the license and the
# accompanying copyright notice.

    """
    TODO: update
    """

from bisect import bisect_left, bisect_right
from typing import Any, Generator, Iterable, Tuple

import pandas as pd
from fedcal import _interval_store as store
from fedcal._typing import IntervalConstantStoreType
from fedcal.constants import Dept, DeptStatus
from pandas import Interval, MultiIndex, Timestamp


def to_dt(t: str, fmt: str | None = None) -> Timestamp:
    """
    Short and quick string to datetime conversion for loading intervals.

    Parameters
    ----------
    t : str
        The string to convert.
    fmt : str, optional, defaults to
    Returns
    -------
    Timestamp
    """
    t_fmt = fmt or "%Y-%m-%d %H:%M:%S"
    return pd.to_datetime(arg=t, format=t_fmt)


def filter_intervals(
    raw_intervals: IntervalConstantStoreType, start_date: Timestamp, end_date: Timestamp
) -> Generator[Tuple[Iterable[Timestamp], Dept, DeptStatus], Any, None]:
    """
    Filters input intervals, bisecting dates go

    Parameters
    ----------
    raw_intervals
        intervals to process
    start_date
        desired start date of interval range
    end_date
        desired end date of interval range

    Yields
    ------
        Generator form of IntervalConstantStoreType if start and end were
        converted to Timestamp
    """

    start: int = bisect_left(
        a=raw_intervals,
        x=start_date,
        key=lambda t: to_dt(t=t[0]),
    )
    end: int = bisect_right(
        a=raw_intervals,
        x=end_date,
        key=lambda t: to_dt(t=t[0]),
    )
    for i in raw_intervals[start:end]:
        yield map(to_dt, i[1:]), i[2], i[3]


def process_interval(interval_data) -> Tuple[Interval[Timestamp], Dept, DeptStatus]:
    """
    Processes interval data from filter_intervals into Interval, Dept, and
    DeptStatus.

    Parameters
    ----------
    interval_data
        IntervalConstantStoreType from filter_intervals

    Returns
    -------
    Tuple[Interval[Timestamp], Dept, DeptStatus]; our intervals ready to load i
    nto an index
    """
    s, e, dept, status = interval_data
    return Interval(left=s if isinstance(s, Timestamp) else to_dt(t=s), right=e if isinstance(e, Timestamp) else to_dt(t=e), closed="both"), dept, status


def to_multi_index(interval_list) -> MultiIndex:
    """
    Converts our intervals to a MultiIndex.

    Parameters
    ----------
    interval_list
        list of tuples from process_interval

    Returns
    -------
    pd.MultiIndex with intervals, departments, and statuses as levels
    """
    intervals, depts, statuses = zip(*interval_list)
    return pd.MultiIndex.from_arrays(
        arrays=[intervals, depts, statuses], names=["Interval", "Department", "Status"]
    )


def fetch_index(intervals: IntervalConstantStoreType | None = None, dates: Timestamp | None = None) -> MultiIndex:
    """
    Fetches intervals from _interval_store.

    Parameters
    ----------
    intervals : IntervalConstantStoreType, optional
        intervals to use, by default None
    dates : Iterable[str], optional
        dates to filter intervals by, by default None

    Returns
    -------
    MultiIndex with intervals, departments, and statuses as levels
    """
    raw_intervals = intervals or store.intervals
    if dates:
        start_date, end_date = min(dates), max(dates)
        filtered_intervals: Generator[Tuple[Iterable[Timestamp], Dept, DeptStatus], Any, None] = filter_intervals(
            raw_intervals=raw_intervals,
            start_date=start_date,
            end_date=end_date,
        )
    processed_intervals = map(process_interval, filtered_intervals or raw_intervals)
        return to_multi_index(interval_list=list(processed_intervals))
