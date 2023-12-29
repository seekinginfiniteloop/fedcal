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
This module replaces multiple modules in the previous back-end that employed
a complex series of interval trees, generators, and objects. Instead, we now
have a simple factory pipeline to reliably pipe our time series department
status data into fedcal using native pandas objects. It processes and returns
our data as a pandas MultiIndex layered by time-based Interval Index at the
top level (level-0), and string representations of and Dept and DeptStatus
objects on the next levels.)
"""

from bisect import bisect_left, bisect_right
from typing import Any, Generator

import pandas as pd
from fedcal import _status_store as store
from fedcal._typing import DTIntervalType, RawIntervalType, RefinedIntervalType
from fedcal.time_utils import to_dt
from pandas import MultiIndex, Timestamp


def filter_intervals(
    raw_intervals: list[RawIntervalType], start_date: Timestamp, end_date: Timestamp
) -> Generator[DTIntervalType, Any, None]:
    """
    Filters input intervals, bisecting dates to efficiently identify the range
    to process.

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
    Generator form of list[DTIntervalType]
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


def process_interval(
    interval_data: RawIntervalType | DTIntervalType,
) -> RefinedIntervalType:
    """
    Processes interval data from filter_intervals into Interval, Dept, and
    DeptStatus.

    Parameters
    ----------
    interval_data
        Raw or datetime-processed intervals

    Returns
    -------
    RefinedIntervalType; our intervals ready to load
    into an index
    """
    s, e, dept, status = interval_data
    return (
        pd.Interval(
            left=s if isinstance(s, Timestamp) else to_dt(t=s),
            right=e if isinstance(e, Timestamp) else to_dt(t=e),
            closed="both",
        ),
        dept.short,
        status.var,
    )


def to_multi_index(interval_list: list[RefinedIntervalType]) -> MultiIndex:
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


def fetch_index(
    intervals: list[RawIntervalType] | None = None,
    dates: tuple[Timestamp] | None = None,
) -> MultiIndex:
    """
    Fetches intervals from _interval_store.

    Parameters
    ----------
    intervals : list[RawIntervalType], optional
        intervals to use, by default None
    dates : Ite, optional
        dates to filter intervals by, by default None

    Returns
    -------
    MultiIndex with intervals, departments, and statuses as levels
    """
    raw_intervals: list[RawIntervalType] = intervals or store.intervals
    if dates:
        start_date, end_date = dates
        filtered_intervals: Generator[DTIntervalType, None] = filter_intervals(
            raw_intervals=raw_intervals,
            start_date=start_date,
            end_date=end_date,
        )
    else:
        filtered_intervals = raw_intervals

    processed_intervals: map[RefinedIntervalType] = map(
        process_interval, filtered_intervals
    )
    return to_multi_index(interval_list=list(processed_intervals))
