# fedcal _mil.py
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
This is a private module. Feel free to use it directly if you like,
but we aim to expose all functionality through `FedIndex` and
`FedStamp` for simplicity.

The _mil module contains classes for calculations related to military
person-power:
- `MilitaryPayDay` calculates and provides military pay days
- `ProbableMilitaryPassday` heuristically calculates probable
military passdays surrounding federal holidays.
"""
from __future__ import annotations

from typing import ClassVar

import numpy as np
import pandas as pd
from attrs import define
from numpy.typing import NDArray
from numpy import busdaycalendar, datetime64, int64, int32, ndarray
from pandas import DatetimeIndex, Series, Timedelta, Timestamp

from fedcal.time_utils import ensure_datetimeindex, dt2date
from fedcal.enum import DoW
from fedcal.cal_offsets import FedBusinessDay, FedHolidays
from fedcal._typing import DT_LIKE

from pandas.api.types import is_scalar
from pandas.tseries.offsets import MonthBegin, MonthEnd, CustomBusinessDay
from datetime import datetime, timedelta
from pandas._libs.tslibs.offsets import (
    apply_wraps,
    SemiMonthOffset,
    shift_month,
)


@define(slots=False, order=False)
class MilitaryPayDay(SemiMonthOffset):
    """
    Custom date offset class based on pandas' SemiMonthOffset for efficient
    date calculations of military paydays based on their rules of falling on
    the 1st or 15th of the month if they are business days, else soonest prior
    business day. We use FedBusinessDay's underlying numpy calendar for
    efficient vector operations on the date shifts.

    Attributes
    ----------
    n: default of 1. An attribute of SemiMonthOffset; not currently implemented for other values.
    normalize: default is true, as this is a calendar we're mostly concerned with dates -- normalizes time values to midnight.
    day_of_month: default is 15. The day of the month to calculate the payday on.As a SemiMonthOffset class, the other date is 1.
    b_day: FedBusinessDay object used for adjusting business day offsets.
    offset: default is 0, and different values not currently implemented.
    """

    _prefix: ClassVar[str] = "CMB"
    _min_day_of_month: int = 7
    n: int = 1
    normalize = True
    day_of_month = 15
    b_day: ClassVar[FedBusinessDay] = FedBusinessDay()
    offset: timedelta | Timedelta = timedelta(days=0)


    def __attrs_post_init__(self) -> None:
        """
        Initializes FedHolidays if not yet initialized; initializes SemiMonthOffset parent class.
        """
        if self.n != 1 or self.offset != timedelta(days=0):
            raise NotImplementedError("These attribute specifications are not supported for MilitaryPayDay, yet.")
        if not hasattr(type(self), "calendar"):
            hol = FedHolidays()
            type(self).calendar = np.busdaycalendar(weekmask="1101100", holidays=hol.np_holidays)
        super().__init__(n=self.n, normalize=self.normalize, day_of_month=self.day_of_month)


    def is_on_offset(self, dt: Timestamp | DatetimeIndex | Series[Timestamp]) -> bool | NDArray[bool]:
        """
        Check if the date(s) is on the offset.

        Parameters
        ----------
        dt : datetime scalar or array to check for being useful.

        Returns
        -------
        bool or array of bool for values on offset.

        """
        if is_scalar(val=dt):
            return self._check_scalar_on_offset(dt=dt)
        else:
            return self._check_array_on_offset(dtarr=dt)

    def _check_scalar_on_offset(self, dt: Timestamp) -> bool:
        """
        Checks scalar if it is on the offset

        Parameters
        ----------
        dt
            datetime scalar for checking

        Returns
        -------
            True if the date is on the offset.
        """
        if self.b_day.is_on_offset(dt=dt) and dt.day in [1, self.day_of_month]:
            return True
        if self.b_day.is_on_offset(dt=dt) and (
            self.day_of_month - 3 < dt.day < self.day_of_month
        ):
            return self.b_day.rollback(dt=dt.replace(day=self.day_of_month)) == dt
        if self.b_day.is_on_offset(dt=dt) and dt.day > 24:
            next_month = dt + pd.Timedelta(months=1)
            return self.b_day.rollback(dt=next_month.replace(day=1)) == dt
        return False

    def _check_array_on_offset(self, dtarr: NDArray[datetime64] | DatetimeIndex | Series[Timestamp]) -> NDArray[bool]:
        """
        Checks an array for values on the offset.

        Parameters
        ----------
        dtarr
            array of datetimes to check

        Returns
        -------
            An NDArray of bool value reflecting days of the week.
        """
        if isinstance(dtarr, ndarray) and dtarr.dtype.str.startswith(("datetime64", "int")):
            dtarr = dtarr.astype(dtype="datetime64[ns]")

        dti: DatetimeIndex = ensure_datetimeindex(dates=dtarr).normalize()
        compare_dti: DatetimeIndex = pd.date_range(start=dti.min() - MonthBegin(n=1), end=dti.max() + MonthEnd(n=1), freq=self, normalize=True)
        return dti.isin(values=compare_dti)

    @apply_wraps
    def _apply(self, other: Timestamp) -> Timestamp:
        """
        Overrides parent's _apply method. Responsible for applying an offset
        to a datetime scalar.

        Parameters
        ----------
        other
            datetime scalar to be offset

        Returns
        -------
            Date adjusted by the offset.
        """
        if self.n > 0:
            target_day: int = self.day_of_month if other.day < self.day_of_month else 1
            other = (
                shift_month(other, self.n) if other.day >= self.day_of_month else other
            )
        else:
            target_day = self.day_of_month if other.day > self.day_of_month else 1

        adjusted_date = other.replace(day=target_day)

        return self.b_day.rollback(dt=adjusted_date)

    def _apply_array(self, dtarr: NDArray[datetime64]) -> NDArray[datetime64]:
        """
        Applies the offset to an array input.

        Parameters
        ----------
        dtarr
            A datetime array for offsetting

        Returns
        -------
            Offset array.
        """
        np_dtstruct: NDArray[datetime64, int32] = dt2date(
            dtarr=dtarr.astype(dtype="datetime64[ns]")
        )
        days = np_dtstruct[..., 3]

        is_target: NDArray[bool] = np.isin(
            element=days, test_elements=[1, self.day_of_month]
        )
        busdays = np.is_busday(
            np_dtstruct[..., 0][is_target], busdaycal=self.b_day.calendar
        )
        non_busdays_idx = np.where(is_target & ~busdays)[0]

        offset_dates: NDArray[datetime64] = np.busday_offset(
            dates=np_dtstruct[..., 0][non_busdays_idx],
            offsets=0,
            roll="backward",
            busdaycal=self.b_day.calendar,
        )
        off_arr: NDArray[datetime64] = dtarr.copy().astype(dtype="datetime64[D]")
        off_arr[non_busdays_idx] = offset_dates

        return off_arr

@define(order=False, slots=False)
class MilitaryPassday(CustomBusinessDay):
    """
    A custom pandas DateOffset class for *probable* military passdays
    business-day-adjacent to federal holidays. With passdays reflected as only
    the affected normal business day vice the entire period if it spans a
    weekend.

    Because passday practices can be very localized, we set a default mapping
    of probable passdays based on holiday day of the week in self.passday_map,
    with default behavior as follows: Mon & Thu holidays have corresponding
    Friday passdays, Friday and Tuesday holidays mapped to Monday passdays, and
    Wednesday to Thursday. You can change these values by passing your own
    dictionary to self.passday_map using three-letter strings for each day in
    title case, e.g. {"Mon": "Fri", "Tue": "Mon", "Wed": "Thu"}. The mapping
    for each value must be to an adjacent business day, and weekends cannot be
    mapped to either value. Perhaps a future version can implement more
    flexibility, please fork and open a pull request.

    Methods
    -------
    is_on_offset : returns True if the date is on the offset, False otherwise.

    nearest_holiday : a handy utility that can find the nearest holiday to any
    date-like object, whether scalar or array. Used in passday calculations,
    but available for broader use because it's spiffy.

    Attributes
    ----------
    n : default to 1. Allowance for other values not currently implemented.
    This would significantly affect offset calculations in a way that is
    probably not desirable for anyone interested in military passdays.

    normalize : default to True. Normalizes dates to midnight, removing time
    data. As this is a calendar focused on dates, that's what we start with.

    weekmask: defaults to M-F. Like n, this attribute is part of
    CustomBusinessDay's core logic. While we'd love to change it, for now you
    cannot pass other values.

    holidays: defaults to None, but there if you want to pass additional
    holidays to consider in calculations.

    calendar: defaults to a numpy busdaycalendar with vectorized U.S. federal
    holidays.

    offset: defaults to timedelta(days=0). Not fully implemented and unlikely
    to be useful for most users, but on the to-do list for eventual
    implementation.

    passday_map: default mappings of holiday day-of-week to
    passday-day-of-week. You may provide custom mappings meeting criteria in
    the _passday_reqs property

    _map : An internal mapping of holiday-day-of-week to passday-day-of-week
    using an enum translated from string input.

    Raises
    ------
    ValueError
        If the passday map is not a valid mapping of holiday-day-of-the-week
        to passday-day-of-the-week. Message describing criteria is both the
        error message and a property, _passday_reqs.
    NotImplementedError
        If the n, normalize, weekmask, or offset attributes are changed.


    Notes
    -----
    *Private Methods*:
        __attrs_post_init__ : initializes the parent CustomBusinessDay class
            and sets the internal mapping of holiday-day-of-week to passdays
        _set_map : sets the internal mapping of holiday-day-of-week to passdays
        _passday_reqs : describes the requirements for a valid passday map.
        _validate_map : validates the internal mapping of holiday-day-of-week
            to passdays
        _apply : Custom implementation of the parent CustomBusinessDay class's
            _apply method, which handles scalar date offsets.
        _apply_array : Custom implementation of the parent CustomBusinessDay's
            _apply_array method, which handles array date offsets.
    """
    _prefix: ClassVar[str] = "CDP"
    n: int = 1
    normalize: str = True
    weekmask: str = "Mon Tue Wed Thu Fri"
    holidays: NDArray[datetime64] | None = None
    calendar: ClassVar[busdaycalendar] = np.busdaycalendar(weekmask="1111100", holidays=FedHolidays().np_holidays)
    offset = timedelta(days=0)

    # mapping of holiday-day-of-the-week to passday-day-of-the-week
    # default is Friday passday for Thursday or Monday holiday, Monday passday
    # for Friday or Tuesday holiday, and Thursday passday for Wednesday holiday
    passday_map: dict[str, str] = {
        "Mon": "Fri",       # [key] holiday day of observance to:
        "Tue": "Mon",       # *value* day of associated passday
        "Wed": "Thu",
        "Thu": "Fri",
        "Fri": "Mon",
    }

    _map: dict | None = None

    def __attrs_post_init__(self) -> None:
        """
        Validates attributes and initializes the parent class.

        Raises
        ------
        NotImplementedError
            If core attributes n, weekmask,or offset are not their default
            values.
        """
        if self.n != 1 or self.weekmask != "Mon Tue Wed Thu Fri" or self.offset != timedelta(days=0):
            raise NotImplementedError("Changing defaults for this attribute is not currently supported.")
        super().__init__(
            n=self.n, normalize=self.normalize, weekmask=self.weekmask, holidays=self.holidays, calendar=type(self).calendar, offset= self.offset
        )
        self._map = self._set_map()
        self._validate_map()

    def _set_map(self) -> None:
        """
        Sets the internal mapping for holidays to passdays.
        """
        self._map: dict[DoW, DoW] = {DoW.__members__.get(k): DoW.__members__.get(v) for k, v in self.passday_map.items()}

    @property
    def _passday_reqs(self) -> str:
        """
        Provides requirements for passday_map to pass validation, used as an
        error message.
        """
        return """Passday map must:
                1) Use 5 unique weekday keys and 5 unique
                values (each consisting of weekdays).
                2) Keys and values must have valid DoW objects (i.e. provided string must be in title case (e.g. 'Tue') and have 3 letters
                3) Keys and values must be within one adjacent businessday
                4) Keys and values cannot be the same.
                5) Keys or values cannot be Saturday or Sunday.
                """

    def _validate_map(self) -> None:
        """
        Validates the passday_map

        Raises
        ------
        ValueError
            If criteria in _passday_reqs are not met.
        """
        if len(set(self._map.keys())) != 5 or len(set(self._map.values())) != 5 or not all(isinstance(v, DoW) for v in self._map.values()) or any(v > 4 for v in self._map.values()):
            raise ValueError(self._passday_reqs)
        for k, v in self._map.items():
            if k == v or (k in [4, 0] and abs(k - v) not in [1, 3]) or abs(k - v) != 1:
                raise ValueError(self._passday_reqs)


    def is_on_offset(self, dt: Timestamp) -> bool:
        """
        Tests if a scalar date is on the offset.

        Returns
        -------
        bool
            True if the date is on the offset, False otherwise.
        """
        return self._apply(other=dt) == dt

    @apply_wraps
    def _apply(self, other:Timestamp) -> Timestamp:
        """
        Custom implementation of the parent CustomBusinessDay class's _apply
        method; applies date offset to a scalar date.

        Parameters
        ----------
        other : Timestamp
            Scalar date to apply offset to.

        Returns
        -------
        Timestamp
            Date with offset applied.

        """
        hol: Timestamp = self.nearest_holiday(other=other)
        hol_dow: int = pd.to_datetime(hol).dayofweek
        pass_dow: DoW = self._map[hol_dow]
        if pass_dow < hol_dow and (hol_dow != 4 and pass_dow != 0):
            return self.rollback(dt=hol) - self.offset
        else:
            return self.rollforward(dt=hol) + self.offset


    def _apply_array(self, dtarr) -> NDArray[datetime64] | None:
        """
        Custom implementation of the parent CustomBusinessDay class's
        _apply_array method; applies date offset to an array of dates.

        Parameters
        ----------
        dtarr : NDArray[datetime64]
            Array of dates to apply offset to.

        Returns
        -------
        NDArray[datetime64]
            Array of dates with offset applied.
        """
        hols: NDArray[datetime64] = self.nearest_holiday(other=dtarr)
        hols_dow: NDArray[int64] = (hols.astype('datetime64[D]').view('int64') - 4) % 7  # Day of week for holidays
        pass_dow = np.array(object=[self._map[DoW(value=dow)] for dow in hols_dow])

        roll_backward = (pass_dow < hols_dow) & ~((hols_dow == 4) & (pass_dow == 0))

        offset_dates: NDArray[datetime64] = hols.copy()
        offset_dates[roll_backward] = np.busday_offset(dates=hols[roll_backward], offsets=self.offset, roll='backward', busdaycal=self.calendar)
        offset_dates[~roll_backward] = np.busday_offset(dates=hols[~roll_backward], offsets=self.offset, roll='forward', busdaycal=self.calendar)

        return offset_dates

    @staticmethod
    def nearest_holiday(other: DT_LIKE, holidays: DT_LIKE | None = None) -> DT_LIKE:
        """
        Finds nearest holiday to date or dates, supports vectorized and scalar input as long as they implement comparison, subtraction, and abs.

        Adapted from Tamas Hegedus on StackOverflow:
        https://stackoverflow.com/questions/32237862/find-the-closest-date-to-a-given-date

        Parameters
        ----------
        other : date or dates to find nearest holiday to.
        holidays : list of dates to find nearest holiday to.

        Returns
        -------
        nearest holiday(s) to date or dates.

        """
        if not isinstance (other, datetime64):
            other = pd.to_datetime(other).dt.normalize().to_numpy() if isinstance (other, Series) else pd.to_datetime(other).normalize().to_numpy()
        holidays = holidays or FedHolidays().np_holidays
        return min(holidays, key = lambda x: abs(x - other))
