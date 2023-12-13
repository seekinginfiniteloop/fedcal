from __future__ import annotations

import time
from datetime import date, datetime
from functools import singledispatch, wraps
from typing import TYPE_CHECKING, Any, Tuple

import pandas as pd
import pytz
from attrs import astuple, define, field
from numpy import datetime64, int64, ndarray

from pandas.tseries.frequencies import to_offset

import .feddatestamp as fedstamp
import .feddateindex as fedindex

if TYPE_CHECKING:
    from pytz.tzinfo import DstTzInfo

    from ._typing import FedDateIndexConvertibleTypes, FedDateStampConvertibleTypes
    from .feddateindex import FedDateIndex
    from .feddatestamp import FedDateStamp


def _pydate_to_posix(pydate: date) -> int:
    """
    A simple utility function to convert Python datetime.date objects to POSIX
    timestamps in integer form. This keeps our numbers at reasonable precision.

    Parameters
    ----------
    pydate : A Python date object

    Returns
    -------
    A POSIX timestamp as an integer (whole seconds since the Unix Epoch).

    """
    return int(time.mktime(pydate))


def get_today_in_posix() -> int:
    """
    Returns the current date in POSIX format.

    Returns
    -------
    int
        The current date in POSIX format.

    """
    today: datetime = datetime.now()
    return int(time.mktime(today.timetuple()))


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
    hint than Tuple[int, int, int]? I think so. Could we use Python date
    instead? Also yes.

    Attributes
    ----------
    year : Four digit year as an integer
    month : integer month
    day : integer day

    Methods
    -------
    from_timestamp(date: pd.Timestamp | FedDateStamp) -> YearMonthDay
        Convert a pandas pd.Timestamp or FedDateStamp object into a YearMonthDay
        object.

    to_posix_timestamp(self) -> int
        Converts a YearMonthDay object to a POSIX integer timestamp.

    to_datestamp(self) -> FedDateStamp
        Converts YearMonthDay to FedDateStamp.

    to_pdtimestamp(self) -> pd.Timestamp
        Converts YearMonthDay to pandas pd.Timestamp.

    to_pydate(self) -> date
        Converts YearMonthDay to Python date object (datetime.date)

    timetuple(self) -> Tuple[int, int, int]
        Returns a tuple of YearMonthDay attributes.

    """

    year: int = field(converter=int)
    month: int = field(converter=int)
    day: int = field(converter=int)

    @staticmethod
    def from_timestamp(date: pd.Timestamp | "FedDateStamp") -> "YearMonthDay":
        """
        Convert a pandas pd.Timestamp or FedDateStamp object into a YearMonthDay object.

        Parameters
        ----------
        date : Date to convert

        Returns
        -------
        YearMonthDay object

        """
        return YearMonthDay(year=date.year, month=date.month, day=date.day)

    def to_posix_timestamp(self) -> int:
        """
        Converts a YearMonthDay object to a POSIX integer timestamp.

        Returns
        -------
        A POSIX timestamp as an integer (whole seconds since the Unix Epoch).

        """
        pydate: date = self.to_pydate()
        return _pydate_to_posix(pydate=pydate)

    def to_datestamp(self) -> "FedDateStamp":
        """
        Converts YearMonthDay to FedDateStamp.

        Returns
        -------
        A FedDateStamp object.

        """
        from .feddatestamp import FedDateStamp

        return FedDateStamp(self.to_pdtimestamp())

    def to_pdtimestamp(self) -> pd.Timestamp:
        """
        Converts YearMonthDay to pandas pd.Timestamp.

        Returns
        -------
        A pandas pd.Timestamp object.

        """
        return pd.Timestamp(year=self.year, month=self.month, day=self.day)

    def to_pydate(self) -> date:
        """
        Converts YearMonthDay to Python date.

        Returns
        -------
        A Python date object.

        """

        return date(year=self.year, month=self.month, day=self.day)

    @property
    def timetuple(self) -> Tuple["YearMonthDay"]:
        """
        Returns a tuple of YearMonthDay attributes.

        Returns
        -------
        A tuple of YearMonthDay attributes.

        """
        return astuple(inst=self)


@singledispatch
def to_datestamp(date_input: "FedDateStampConvertibleTypes") -> "FedDateStamp" | None:
    """
    We want to handle diverse date inputs without tripping, because one
    goal of our library is to provide a feature-rich addition that
    seamlessly behaves like and integrates into pandas. This
    singledispatch function allows us to funnel diverse inputs for conversion
    based on type without repeating ourselves.

    Parameters
    ----------
    date_input : Any FedDateStampConvertibleTypes for conversion to a FedDateStamp.

    Returns
    -------
    A FedDateStamp object (if successful), else None

    Raises
    ------
    TypeError
        Raises a type error if it encounters unsupported date types.

    """
    raise TypeError(
        f"Unsupported date format. You provided type: {type(date_input)}. Supported types are FedDateStampConvertibleTypes"
    )


@to_datestamp.register(cls=pd.Timestamp)
def _timestamp_to_datestamp(date_input: pd.Timestamp) -> "FedDateStamp":
    """Conversion for pandas Timestamps"""
    return _stamp_date(timestamp=date_input)


@to_datestamp.register(cls=int)
@to_datestamp.register(cls=int64)
@to_datestamp.register(cls=float)
def _posix_to_datestamp(date_input: int | int64 | float) -> "FedDateStamp":
    """
    Conversion for POSIX timestamps; we assume isolated integers or floats are POSIX time.
    """
    return _stamp_date(timestamp=date.fromtimestamp(date_input))


@to_datestamp.register(cls=str)
def _str_to_datestamp(date_input: str) -> "FedDateStamp":
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
        return _stamp_date(timestamp=date.fromisoformat(date_input))
    except ValueError as e:
        for fmt in ("%m/%d/%Y", "%m-%d-%Y", "%d/%m/%Y", "%d-%m-%Y"):
            try:
                parsed_date = datetime.strptime(date_input, fmt).date()
                return _stamp_date(timestamp=parsed_date)
            except ValueError:
                continue
        raise ValueError(
            f"""Date string '{date_input}' is not in a recognized format. All
            reasonable attempts to parse it failed. Are you trying to use an
            alien date format? Please use an ISO 8601 format"""
        ) from e


@to_datestamp.register(cls=date)
@to_datestamp.register(cls=datetime)
@to_datestamp.register(cls=datetime64)
def _date_to_datestamp(date_input: date | datetime | datetime64) -> "FedDateStamp":
    """Conversions for Python date and datetime objects."""
    return _stamp_date(timestamp=date_input)


@to_datestamp.register(cls=YearMonthDay)
def _yearmonthday_to_datestamp(date_input: YearMonthDay) -> "FedDateStamp":
    """Conversion for YearMonthDay objects."""
    return date_input.to_datestamp()


@to_datestamp.register(cls=tuple)
def _timetuple_to_datestamp(date_input: Tuple) -> "FedDateStamp":
    if len(date_input) != 3:
        raise ValueError(
            "Timetuple input requires a tuple with four-digit year, month, day as integers or integer-convertible strings."
        )

    try:
        year, month, day = (int(item) for item in date_input)
    except ValueError as e:
        raise ValueError(
            "Year, month, and day must be integers or strings that can be converted to integers."
        ) from e

    if not (1970 <= year <= 9999):
        raise ValueError("Year must be a four-digit number, and not before 1970.")

    return YearMonthDay(year=year, month=month, day=day).to_datestamp()


@to_datestamp.register(cls=fedstamp.FedDateStamp)
def _return_datestamp(date_input: "FedDateStamp") -> "FedDateStamp":
    """
    We handle stray non-conversions by returning them.
    """
    return date_input


def check_timestamp(
    func,
):
    """
    Since _stamp_date is designed to normalize Timestamps before
    subclassing them with FedDateStamp, to avoid repeating ourselves with
    conversions to Timestamps in most of our to_datestamp converters, we
    instead wrap/decorate _stamp_date to intercept and convert any
    non-Timestamps to Timestamps once to_datestamp gets them in a format
    pd.Timestamp will accept.

    Parameters
    ----------
    func : Our wrapped function.

    Returns
    -------
    A wrapper around func that converts non-pd.Timestamp input to Timestamps.

    """

    @wraps(wrapped=func)
    def wrapper(arg) -> pd.Timestamp | "FedDateStamp" | Any | None:
        """Our pd.Timestamp handling wrapper."""
        if isinstance(arg, pd.Timestamp):
            return func(arg)
        elif isinstance(arg, FedDateStamp):
            return
        elif arg is None:
            raise ValueError(
                f"""provided argument, {arg} is None; we're not mind readers
                here. Please provide a pd.Timestamp for _stamp_date."""
            )
        else:
            try:
                return func(pd.Timestamp(ts_input=arg))
            except TypeError as e:
                raise TypeError(
                    f"""input {arg} could not be converted to a pd.Timestamp. Our
                    _stamp_date function needs pandas Timestamps or a
                    pd.Timestamp convertible date-like object (e.g. Python date)
                    """
                ) from e

    return wrapper


@check_timestamp
def _stamp_date(timestamp: pd.Timestamp) -> "FedDateStamp":
    """
    If incoming Timestamps have timezone information, we normalize them to
    U.S. Eastern -- because Washington D.C. We then make them FedDateStamps.

    Parameters
    ----------
    timestamp : A pandas pd.Timestamp for conversion (through subclassing) to a
    FedDateStamp.

    Returns
    -------
    A FedDateStamp object.

    """
    from .feddatestamp import FedDateStamp

    if timestamp.tzinfo is None:
        return FedDateStamp(timestamp)
    eastern: "DstTzInfo" = pytz.timezone(zone="US/Eastern")
    return FedDateStamp(timestamp.tz_convert(tz=eastern))


def wrap_tuple(
    func,
):
    """
    To avoid repeating ourselves with date converters that handle two
    arguments for FedDateIndex, we instead wrap the singledispatch
    function so it converts two arguments into a tuple. This way, we can
    elegantly route all tuples to our existing to_datestamp converters.

    wrap_tuple intercepts something like:
        to_feddateindex(date1, date2)

    And forwards it on as:
        to_feddateindex((date1, date2))

    Parameters
    ----------
    func : Our wrapped function.

    Returns
    -------
    A wrapper around func that converts multi-argument dates to a tuple.

    """

    @wraps(wrapped=func)
    def wrapper(*args) -> Tuple | Any | None:
        """Our to-tuple handling wrapper."""
        return func((args[0], args[1])) if len(args) == 2 else func(*args)

    return wrapper


@wrap_tuple
@singledispatch
def to_feddateindex(
    input_dates: "FedDateIndexConvertibleTypes",
) -> "FedDateIndex" | None:
    """
    A singledispatch function for handling date conversions to FedDateIndex.
    Most types are pushed into tuples by wrap_tuple and funneled to our
    to_datetime functions for conversion. We also add support for array_like
    objects, such as pandas pd.Index and pd.Series, and numpy ndarrays. And, of
    course, pd.DatetimeIndex itself.

    Parameters
    ----------
    input_dates : Any FedDateIndexConvertibleTypes (i.e. any
    FedDateStampConvertibleType, FedDateStamp, pd.Timestamp).

    Returns
    -------
    A FedDateIndex object.

    Raises
    ------
    TypeError
        If supplies with an unsupported type.

    """

    raise TypeError(
        "You provided unsupported types. Supported types are FedDateIndexConvertibleTypes"
    )


@to_feddateindex.register(cls=tuple)
def _from_tuple(input_dates) -> "FedDateIndex":
    """
    We reuse to_datestamp to efficiently handle tuples of supported types.
    Even if not provided as a tuple, any two arguments will be funneled into
    a tuple by wrap_tuple.
    """
    start, end = map(to_datestamp, input_dates)
    return _get_feddateindex(start, end)


@to_feddateindex.register(cls=pd.DatetimeIndex)
def _from_datetimeindex(input_dates) -> "FedDateIndex":
    """We subclass and return a pd.DatetimeIndex"""
    from .feddateindex import FedDateIndex

    return FedDateIndex(input_dates)


@to_feddateindex.register(cls=pd.Series)
@to_feddateindex.register(cls=pd.Index)
@to_feddateindex.register(cls=ndarray)
def _from_array_like(input_dates) -> "FedDateIndex":
    """
    We try to convert array-like objects to pd.DatetimeIndex

    Raises
    ------
    ValueError
        If the conversion fails, likely because the array does not contain
        datetimes.

    """
    try:
        datetimeindex = pd.DatetimeIndex(input_dates)
        from .feddateindex import FedDateIndex

        return FedDateIndex(datetimeindex)
    except ValueError as e:
        raise ValueError(
            f"""Failed to convert input to pd.DatetimeIndex. Must contain
            inputs compatible with a pandas pd.DatetimeIndex. You provided: \n
            {input_dates}"""
        ) from e


@to_feddateindex.register(cls=fedindex.FedDateIndex)
def _from_feddateindex(input_dates: "FedDateIndex") -> "FedDateIndex":
    """
    We catch and return stray FedDateIndex objects that happen into our net.
    """
    return input_dates


def _get_feddateindex(
    start: "FedDateStamp" | "FedDateStampConvertibleTypes",
    end: "FedDateStamp" | "FedDateStampConvertibleTypes",
) -> "FedDateIndex":
    """
    Converts a start and end date to a FedDateIndex.

    Parameters
    ----------
    start : The start date.
    end : The end date.

    Returns
    --------
    A FedDateIndex object.

    """
    from .feddateindex import FedDateIndex
    from .feddatestamp import FedDateStamp

    start = start if isinstance(start, FedDateStamp) else to_datestamp(start)
    end = end if isinstance(end, FedDateStamp) else to_datestamp(end)

    daterange: pd.DatetimeIndex = pd.date_range(
        start=start, end=end, freq=to_offset(freq="D"), inclusive="both"
    )
    return FedDateIndex(daterange)
