# fedcal _typing.py
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
This module provides internal type definitions for fedcal to keep the code
clean but well-typed.
"""
from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, Iterable, TypeVar, Union

from numpy import datetime64, int64
from numpy.typing import NDArray
from pandas import DatetimeIndex, Index, Interval, PeriodIndex, Series, Timestamp

if TYPE_CHECKING:
    from fedcal.time_utils import YearMonthDay
    from fedcal.enum import Dept, DeptStatus


EnumType = TypeVar("EnumType", bound="EnumBase")

FedStampConvertibleTypes = Union[
    Timestamp,
    int,
    int64,
    datetime64,
    float,
    "YearMonthDay",
    tuple[int, int, int],
    tuple[str, str, str],
    str,
    datetime.date,
    datetime.datetime,
]

FedIndexConvertibleTypes = Union[
    tuple[FedStampConvertibleTypes, FedStampConvertibleTypes],
    tuple[Timestamp, Timestamp],
    NDArray,
    Series,
    DatetimeIndex,
    Index,
    PeriodIndex,
]

RefinedIntervalType = tuple[Interval, "Dept", "DeptStatus"]

DT_LIKE = TypeVar('datetime-like')
