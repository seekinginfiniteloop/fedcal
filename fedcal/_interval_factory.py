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
    start, end, dept, status = interval_data
    return Interval(left=start, right=end, closed="both"), dept, status


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


def fetch_index(intervals=None, dates=None) -> MultiIndex:
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
    if not dates:
        return to_multi_index(interval_list=store.intervals)
    dates = map(to_dt, dates)

    raw_intervals: IntervalConstantStoreType = intervals or store.intervals
    filtered_intervals = (
        filter_intervals(
            raw_intervals=raw_intervals,
            start_date=min(dates),
            end_date=max(dates),
        )
        if dates
        else raw_intervals
    )
    processed_intervals = map(process_interval, filtered_intervals)

    return to_multi_index(interval_list=list(processed_intervals))
