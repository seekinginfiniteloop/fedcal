# fedcal time_utils.py
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
time_utils.py provides a number of helper converter functions for handling
time conversions in fedcal. We expose it publicly because they're probably
generally useful for other things.

It includes:
- `get_today_in_posix_day` and `pdtimestamp_to_posix_day` for
handling POSIX-day integer second retrieval for today and from pandas
Timestamp objects respectively.

- `YearMonthDay` a class for handling date conversions from year, month, day.
It's there because I wanted something cleaner than datetime. I like it. It's
gonna stay.

- `to_timestamp` and `to_datetimeindex` are singledispatch converter functions
for converting a wide range of possible time inputs to `pd.Timestamp` and
`pd.DatetimeIndex` respectively. As they can look complex for the uninitiated
let's dive in deeper:

- `to_timestamp` routes input based on type (that's what a singledispatch is)
to helper converters, most of which prep input for conversion to `pd.
Timestamp`. Those converters then route output through a wrapper,
`check_timestamp`, which centralizes conversions to `pd.Timestamp` so
we're not repeating ourselves in each of the converters. `check_timestamp`
wraps `_normalize_timestamp`, which normalizes timezone-aware `pd.Timestamps`
to U.S. Eastern (because Washington D.C.).

- `to_datetimeindex` is similar to `to_timestamp`, but is itself wrapped
by `wrap_tuple`, which intercepts two argument formatted input (i.e.
start-date, end_date) and outputs it as a single argument tuple (i.e.
(start_date, end_date)). Most input is then processed through `to_timestamp`
with the tuple's two dates routed separately. That keeps us from repeating
ourselves. `to_datetimeindex` does add functionality for conversions from
array-like objects (i.e. numpy arrays) to `pd.DatetimeIndex` objects.
After conversion, tupled start/end dates are passed through
`_get_datetimeindex_for_range` and all input is finally passed
through `_normalize_datetimeindex` to normalize timezone aware
input to U.S. Eastern, as with `to_timestamp`.
"""

from __future__ import annotations

import datetime
from functools import singledispatch, wraps
from typing import TYPE_CHECKING, Any

import numpy as np
import pandas as pd
from attrs import astuple, define, field
from pandas.tseries.frequencies import to_offset

if TYPE_CHECKING:
    from ._typing import FedIndexConvertibleTypes, FedStampConvertibleTypes


def get_today_in_posix_day() -> int:
    """
    Returns the current date in POSIX-day format.

    Returns
    -------
    int
        The current date in POSIX-day format.

    """
    today: float = pd.Timestamp(datetime.date.today()).timestamp()
    return int(today // 86400)


def pdtimestamp_to_posix_day(timestamp: pd.Timestamp) -> int:
    """
    Converts a pandas Timestamp object to a POSIX-day integer timestamp.

    Parameters
    ----------
    timestamp : pandas Timestamp object

    Returns
    -------
    int
        POSIX-day timestamp in days.

    """
    return int(timestamp.timestamp() // 86400)


@define(order=True)
class YearMonthDay:

    """
    A class to handle conversion of year,month,day integer input to other date
    types needed by the calendar.

    Do we *need* YearMonthDay? No, but it does provide clear typing and ensure
    smooth functioning for the most common form of programmatic date input
    (i.e. year, month, day). We need it in the same sense that an
    average person needs a remote controlled drone... they don't, but it beats
    climbing on a roof. Doesn't YearMonthDay look so much nicer in a type
    hint than tuple[int, int, int]? I think so. Could we use Python date
    instead? Also yes.

    Attributes
    ----------
    year : Four digit year as an integer
    month : integer month
    day : integer day

    Methods
    -------
    from_timestamp(date: pd.Timestamp) -> YearMonthDay
        Convert a pandas pd.Timestamp object into a YearMonthDay
        object.

    to_posix_timestamp(self) -> int
        Converts a YearMonthDay object to a POSIX-day integer timestamp.

    to_pdtimestamp(self) -> pd.Timestamp
        Converts YearMonthDay to pandas pd.Timestamp.

    to_pydate(self) -> date
        Converts YearMonthDay to Python date object (datetime.date)

    timetuple(self) -> tuple[int, int, int]
        Returns a tuple of YearMonthDay attributes.

    """

    year: int = field(converter=int)
    month: int = field(converter=int)
    day: int = field(converter=int)

    @staticmethod
    def from_timestamp(date: pd.Timestamp) -> "YearMonthDay":
        """
        Convert a pandas pd.Timestamp object into a
        YearMonthDay object.

        Parameters
        ----------
        date : Date to convert

        Returns
        -------
        YearMonthDay object

        """
        return YearMonthDay(year=date.year, month=date.month, day=date.day)

    def to_timestamp(self) -> int:
        """
        Converts a YearMonthDay object to a POSIX-day integer timestamp.

        Returns
        -------
        A POSIX timestamp as an integer (seconds since the Unix Epoch).
        """
        return int(self.to_pdtimestamp().timestamp())

    def to_timestamp_day(self) -> int:
        """
        Converts a YearMonthDay object to a POSIX-day integer timestamp.

        Returns
        -------
        A POSIX-day timestamp as an integer (whole days since the Unix Epoch).

        """
        return pdtimestamp_to_posix_day(timestamp=self.to_pdtimestamp())

    def to_pdtimestamp(self) -> pd.Timestamp:
        """
        Converts YearMonthDay to pandas pd.Timestamp.

        Returns
        -------
        A pandas pd.Timestamp object.

        """
        return pd.Timestamp(year=self.year, month=self.month, day=self.day)

    def to_pydate(self) -> datetime.date:
        """
        Converts YearMonthDay to Python datetime.date.

        Returns
        -------
        A Python datetime.date object.

        """

        return datetime.date(year=self.year, month=self.month, day=self.day)

    @property
    def timetuple(self) -> tuple["YearMonthDay"]:
        """
        Returns a tuple of YearMonthDay attributes.

        Returns
        -------
        A tuple of YearMonthDay attributes.

        """
        return astuple(inst=self)


@singledispatch
def to_timestamp(date_input: "FedStampConvertibleTypes") -> pd.Timestamp | None:
    """
    We want to handle diverse date inputs without tripping, because one
    goal of our library is to provide a feature-rich addition that
    seamlessly behaves like and integrates into pandas. This
    singledispatch function allows us to funnel diverse inputs for conversion
    based on type without repeating ourselves.

    We roll our own here because pd.to_datetime has multiple outputs depending
    on input type, and we want to consistently get Timestamps and normalize
    them.

    Parameters
    ----------
    date_input : Any FedStampConvertibleTypes for conversion to a time zone
    normalized Timestamp.

    Returns
    -------
    A pd.Timestamp object (if successful), else None

    Raises
    ------
    TypeError
        Raises a type error if it encounters unsupported date types.

    """
    raise TypeError(
        f"""Unsupported date format. You provided type: {type(date_input)}.
        Supported types are FedStampConvertibleTypes"""
    )


@to_timestamp.register(cls=pd.Timestamp)
def _timestamp_to_timestamp(date_input: pd.Timestamp) -> pd.Timestamp:
    """Conversion for pandas Timestamps"""
    return _normalize_timestamp(date_input)


@to_timestamp.register(cls=int)
@to_timestamp.register(cls=np.int64)
@to_timestamp.register(cls=float)
def _posix_to_timestamp(date_input: int | np.int64 | float) -> pd.Timestamp:
    """
    Conversion for POSIX timestamps; we assume isolated integers or floats are POSIX time.
    """
    if date_input < 100000:
        return _normalize_timestamp(
            datetime.datetime.fromtimestamp((int(date_input) * 86400))
        )
    return _normalize_timestamp(datetime.date.fromtimestamp(date_input))


@to_timestamp.register(cls=str)
def _str_to_timestamp(date_input: str) -> pd.Timestamp:
    """
    Conversion for string dates.
    Tries ISO-formatted strings first, then falls back to American formats.
    Assumes Python 3.11 functionality for handling multiple ISO formats.
    If ISO format fails, we try American date formats -- this being an
    American calendar -- and then European date formats.

    Raises
    ------
    ValueError
        raises a ValueError if it cannot parse a provided string.

    """
    try:
        return _normalize_timestamp(datetime.date.fromisoformat(date_input))
    except ValueError as e:
        for fmt in ("%m/%d/%Y", "%m-%d-%Y", "%d/%m/%Y", "%d-%m-%Y"):
            try:
                parsed_date = datetime.datetime.strptime(date_input, fmt).date()
                return _normalize_timestamp(parsed_date)
            except ValueError:
                continue
        raise ValueError(
            f"""Date string '{date_input}' is not in a recognized format. All
            reasonable attempts to parse it failed. Are you trying to use an
            alien date format? Please use an ISO 8601 format"""
        ) from e


@to_timestamp.register(cls=datetime.date)
@to_timestamp.register(cls=datetime.datetime)
@to_timestamp.register(cls=np.datetime64)
def _date_to_timestamp(
    date_input: datetime.date | datetime.datetime | np.datetime64,
) -> pd.Timestamp:
    """Conversions for Python date and datetime objects."""
    return _normalize_timestamp(date_input)


@to_timestamp.register(cls=YearMonthDay)
def _yearmonthday_to_timestamp(date_input: YearMonthDay) -> pd.Timestamp:
    """Conversion for YearMonthDay objects."""
    return _normalize_timestamp(date_input.to_pdtimestamp())


@to_timestamp.register(cls=tuple)
def _timetuple_to_timestamp(date_input: tuple) -> pd.Timestamp:
    if len(date_input) != 3:
        raise ValueError(
            """Timetuple input requires a tuple with four-digit year, month,
            day as integers or integer-convertible strings."""
        )
    try:
        year, month, day = (int(item) for item in date_input)
    except ValueError as e:
        raise ValueError(
            """Year, month, and day must be integers or strings that can be
            converted to integers."""
        ) from e

    if not 1970 <= year <= 9999:
        raise ValueError("Year must be a four-digit number, and not before 1970.")

    return _normalize_timestamp(
        YearMonthDay(year=year, month=month, day=day).to_pdtimestamp()
    )


def check_timestamp(
    func,
):
    """
    Since _normalize_timestamp is designed to normalize Timestamps, to avoid
    repeating ourselves with conversions to Timestamps in most of our
    to_timestamp converters, we instead wrap/decorate _normalize_timestamp to
    intercept and convert any non-Timestamps to Timestamps once to_timestamp
    gets them in a format pd.Timestamp will accept.

    Parameters
    ----------
    func : Our wrapped function.

    Returns
    -------
    A wrapper around func that converts non-pd.Timestamp input to Timestamps.

    """

    @wraps(wrapped=func)
    def wrapper(arg) -> pd.Timestamp | Any | None:
        """Our pd.Timestamp handling wrapper."""
        if isinstance(arg, pd.Timestamp):
            return func(arg)

        if arg is None:
            raise ValueError(
                f"""provided argument, {arg} is None; we're not mind readers
                here. Please provide a pd.Timestamp for _normalize_timestamp."""
            )
        try:
            return func(pd.Timestamp(ts_input=arg))
        except TypeError as e:
            raise TypeError(
                f"""input {arg} could not be converted to a pd.Timestamp.
                    Our _normalize_timestamp function needs pandas Timestamps
                    or a pd.Timestamp convertible date-like object (e.g. Python
                    date)
                    """
            ) from e

    return wrapper


@check_timestamp
def _normalize_timestamp(timestamp: pd.Timestamp = None) -> pd.Timestamp:
    """
    If incoming Timestamps have timezone information, we normalize them to
    timezone naive UTC for consistency and because we're concerned with
    date-level precision here.

    Parameters
    ----------
    timestamp : A pandas pd.Timestamp for normalization

    Returns
    -------
    Normalized Timestamp

    """
    if timestamp.tzinfo:
        timestamp = timestamp.tz_convert(tz="UTC").normalize()
    return timestamp.normalize()


def wrap_tuple(
    func,
):
    """
    To avoid repeating ourselves with date converters that handle two
    arguments for FedIndex, we instead wrap the singledispatch
    function so it converts two arguments into a tuple. This way, we can
    elegantly route all tuples to our existing to_timestamp converters.

    wrap_tuple intercepts something like:
        to_datetimeindex(date1, date2)

    And forwards it on as:
        to_datetimeindex((date1, date2))

    Parameters
    ----------
    func : Our wrapped function.

    Returns
    -------
    A wrapper around func that converts multi-argument dates to a tuple.

    """

    @wraps(wrapped=func)
    def wrapper(*args) -> tuple | Any | None:
        """Our to-tuple handling wrapper."""
        if count := len(args) in {1, 2}:
            return func(args[0]) if count == 1 else func((args[0], args[1]))
        raise ValueError(f"We need 1 or 2 arguments... not {count}")

    return wrapper


@wrap_tuple
@singledispatch
def to_datetimeindex(
    *input_dates: "FedIndexConvertibleTypes",
) -> pd.DatetimeIndex | None:
    """
    A singledispatch function for handling date conversions to DatetimeIndex.
    Most types are pushed into tuples by wrap_tuple and funneled to our
    to_datetime functions for conversion. We also add support for array_like
    objects, such as pandas pd.Index and pd.Series, and numpy ndarrays. And, of
    course, pd.DatetimeIndex itself.

    Like Timestamp, we do this to ensure they're normalized and to add finer
    control.

    Parameters
    ----------
    input_dates : Any FedIndexConvertibleTypes (i.e. any
    FedStampConvertibleType, pd.Timestamp).

    Returns
    -------
    A DatetimeIndex.

    Raises
    ------
    TypeError
        If supplies with an unsupported type.

    """

    raise TypeError(
        "You provided unsupported types. Supported types are FedIndexConvertibleTypes"
    )


@to_datetimeindex.register(cls=tuple)
def _from_tuple(input_dates) -> pd.DatetimeIndex:
    """
    We reuse `to_timestamp` to efficiently handle tuples of supported types.
    Even if not provided as a tuple, any two arguments will be funneled into
    a tuple by wrap_tuple.
    """
    start, end = map(to_timestamp, input_dates)
    return _get_datetimeindex_from_range(start=start, end=end)


@to_datetimeindex.register(cls=pd.DatetimeIndex)
def _from_datetimeindex(input_dates) -> pd.DatetimeIndex:
    """We catch and release DatetimeIndexes"""
    return _normalize_datetimeindex(datetimeindex=input_dates)


@to_datetimeindex.register(cls=pd.Series)
@to_datetimeindex.register(cls=pd.Index)
@to_datetimeindex.register(cls=np.ndarray)
def _from_array_like(input_dates) -> pd.DatetimeIndex:
    """
    We try to convert array-like objects to pd.DatetimeIndex

    Raises
    ------
    ValueError
        If the conversion fails, likely because the array does not contain
        datetimes.

    """
    try:
        datetimeindex = pd.DatetimeIndex(data=input_dates)
        return _normalize_datetimeindex(datetimeindex=datetimeindex)

    except ValueError as e:
        raise ValueError(
            f"""Failed to convert input to pd.DatetimeIndex. Must contain
            inputs compatible with a pandas pd.DatetimeIndex. You provided: \n
            {input_dates}"""
        ) from e


def _get_datetimeindex_from_range(
    start: pd.Timestamp | "FedStampConvertibleTypes",
    end: pd.Timestamp | "FedStampConvertibleTypes",
) -> pd.DatetimeIndex:
    """
    Converts a start and end date to datetimeindex.

    Parameters
    ----------
    start : The start date.
    end : The end date.

    Returns
    --------
    A datetimeindex.

    """
    start = start if isinstance(start, pd.Timestamp) else to_timestamp(start)
    end = end if isinstance(end, pd.Timestamp) else to_timestamp(end)

    datetimeindex: pd.DatetimeIndex = pd.date_range(
        start=start, end=end, freq=to_offset(freq="D"), inclusive="both"
    )
    return _normalize_datetimeindex(datetimeindex=datetimeindex)


def _normalize_datetimeindex(datetimeindex: pd.DatetimeIndex) -> pd.DatetimeIndex:
    """
    Normalizes a datetimeindex to UTC and makes it timezone naive
    because we're not concerned with that kind of precision here,
    and it keeps output consistent.

    Parameters
    ----------
    datetimeindex : A pandas DatetimeIndex for normalization

    Returns
    -------
    A normalized DatetimeIndex

    """
    if datetimeindex.tz:
        return datetimeindex.tz_convert(tz="UTC").normalize()
    return datetimeindex.normalize()
