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
from enum import IntEnum, unique
from typing import ClassVar

import numpy as np
import pandas as pd
from attrs import define, field
from numpy.typing import NDArray
from numpy import busdaycalendar, datetime64, int64, int32, ndarray
from pandas import DataFrame, DateOffset, DatetimeIndex, Index, Series, Timestamp,

from fedcal import cal_offsets
from fedcal.time_utils import ensure_datetimeindex, to_datetimeindex, dt2date
from fedcal.enum import DoW, Month
from fedcal.cal_offsets import FedBusinessDay, FedHolidays

from pandas.api.types import is_scalar
from pandas.tseries.offsets import MonthBegin, MonthEnd, CustomBusinessDay
from pandas._libs.tslibs.offsets import (
from datetime import timedelta
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
    """

    _prefix: ClassVar[str] = "CMB"
    _min_day_of_month: int = 7
    n: int = 1
    normalize = True
    day_of_month = 15
    b_day: ClassVar[FedBusinessDay] = FedBusinessDay()


    def __attrs_post_init__(self) -> None:
        if not hasattr(type(self), "calendar"):
            hol = FedHolidays()
            type(self).calendar = np.busdaycalendar(weekmask="1101100", holidays=hol.np_holidays)
        super().__init__(n=self.n, normalize=self.normalize, weekmask=self.weekmask, holidays=self.holidays, calendar=type(self).calendar, offset=self.offset)


    def is_on_offset(self, dt: Timestamp | DatetimeIndex | Series[bool]) -> bool | NDArray[bool]:
        """
        Check if the (scalar) date is on the offset.
        """
        if is_scalar(val=dt):
            return self._check_scalar_on_offset(dt=dt)
        else:
            return self._check_array_on_offset(dtarr=dt)

    def _check_scalar_on_offset(self, dt: Timestamp | NDArray[datetime64] | DatetimeIndex | Series[Timestamp]) -> bool:
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
        if isinstance(dtarr, ndarray) and dtarr.dtype.str.startswith(("datetime64", "int")):
            dtarr = dtarr.astype(dtype="datetime64[ns]")

        dti: DatetimeIndex = ensure_datetimeindex(dates=dtarr).normalize()
        compare_dti: DatetimeIndex = pd.date_range(start=dti.min() - MonthBegin(n=1), end=dti.max() + MonthEnd(n=1), freq=self, normalize=True)
        return dti.isin(values=compare_dti)

    @apply_wraps
    def _apply(self, other: Timestamp) -> Timestamp:
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
class TestPass(CustomBusinessDay):
    _prefix: ClassVar[str] = "CDP"
    n: int = 1
    normalize: str = True
    weekmask: str = "Mon Tue Thu Fri"
    holidays: NDArray[datetime64] | None = None
    calendar: ClassVar[busdaycalendar] = np.busdaycalendar(weekmask="1101100", holidays=FedHolidays().np_holidays)
    offset = timedelta(days=0)

    # mapping of holiday-day-of-the-week to passday-day-of-the-week
    # default is Friday passday for Thursday or Monday holiday, Monday passday
    # for Friday or Tuesday holiday, and Thursday passday for Wednesday holiday
    passday_map: dict[str: str] = {
        "Mon": 'Fri', # holiday day of observance : day of associated passday
        "Tue": 'Mon',
        "Wed": 'Thu',
        "Thu": "Fri",
        "Fri": "Mon",
    }

    _map: dict | None = None

    def __attrs_post_init__(self) -> None:
        super().__init__(
            n=self.n, normalize=self.normalize, weekmask=self.weekmask, holidays=self.holidays, calendar=type(self).calendar, offset= self.offset
        )
        self._map = self._set_map()

    def _set_map(self) -> None:
        self._map = {}
        for k, v in self.passday_map.items() if k in DoW.__members__.keys() and v in DoW.__members__.keys() else None:
            nk = DoW.__members__.get(k)
            nv = DoW.__members__.get(v)
            self._map[nk] = nv



@define(order=True, kw_only=True)
class ProbableMilitaryPassDay:

    """
    Assesses the likelihood of a given date being a military pass day.

    Attributes
    ----------
    dates : date or dates used for determining pass days.
    passdays : dates that are likely to be pass days from the date or dates.

    note: you must pass either a date or dates to the instance.

    Methods
    -------
    get_probable_passdays(dates=None) -> NDArray
        Leverages boolean masking operations to identify probable
        military passdays across a DatetimeIndex.

    Notes
    -----
    While technically military passes extend through non-business days, passes
    falling on non-business days don't meaningfully affect available personnel.
    Since our goal is enabling useful data analysis, we do not account for
    passes falling on non-business days.

        Military passdays are highly variable. When they are granted can vary
        even within major commands or at a single location based on commanders'
        discretion and mission needs. While we try to guess at what day will be
        most likely to be a passday for the majority of members, the overall
        goal is to roughly capture the loss of person-power for these periods
        for offices or locations relying heavily on military personnel,
        enabling productivity and microeconomic analysis.

            Current rules set the following framework (in _likely_passday):
    ]       - If Monday holiday, previous Friday is the likely passday.
            - If Friday is the holiday, following Monday is the likely passday.
            - If Tuesday, Monday.
            - If Thursday, Friday.
            - If Wednesday, Thursday.

        TODO: In future versions, I hope to add customizable rules for
        evaluating likely passdays (i.e. a Wednesday holiday's passday will be
        Tuesday instead of Thursday).

    *Private Methods*:
        _get_base_masks(dates) -> DataFrame
            a helper method for get_probable_passdays that generates a
            DataFrame of boolean masks for identifying passdays.
    """

    dates: DatetimeIndex | Series[Timestamp] | Timestamp | None = field(default=None)

    passdays: NDArray[bool] | None = field(default=None, init=False)

    def __attrs_post_init__(self) -> None:
        """
        Complete initialization of the instance and sets attributes
        """
        self.dates = ensure_datetimeindex(dates=self.dates)
        self.passdays = self.get_probable_passdays(dates=self.dates)

    def get_probable_passdays(
        self, dates: DatetimeIndex | Series[Timestamp]
    ) -> NDArray[bool]:
        """
        Determines the likely passdays for the given dates.

        Parameters
        ----------
        dates : dates for checking against passday masks

        Returns
        -------
        Boolean NDArray indicating whether the dates in the range are
        probable passdays.

        """
        if dates is None:
            dates = self.dates
        else:
            dates = to_datetimeindex(dates) if isinstance(dates, pd.Series) else dates
        masks: DataFrame = self._get_base_masks(dates=dates)
        fri_mask: Series[bool] = dates.isin(
            dates[masks["monday_holidays"]] - pd.DateOffset(days=3)
        ) | dates.isin(dates[masks["thursday_holidays"]] + pd.DateOffset(days=1))

        mon_mask: Series[bool] = dates.isin(
            dates[masks["friday_holidays"]] + pd.DateOffset(days=3)
        ) | dates.isin(dates[masks["tuesday_holidays"]] - pd.DateOffset(days=1))
        thurs_mask: Series[bool] = dates.isin(
            dates[masks["wednesday_holidays"]] + pd.DateOffset(days=1)
        )

        return (fri_mask | mon_mask | thurs_mask) & masks["business_days"]

    @staticmethod
    def _get_base_masks(
        dates: DatetimeIndex,
    ) -> DataFrame:
        """
        Retrieves the base masks for evaluating a DatetimeIndex for possible
        passdays. A helper method to `get_probable_passdays`.


        Parameters
        ----------
        dates : dates to retrieve masks for.

        Returns
        -------
        A dataframe of boolean masks, and date information
        """

        bday = cal_offsets.FedBusinessDay()
        holiday = cal_offsets.FedHolidays()

        mask_frame = pd.DataFrame(index=dates)

        mask_frame["dates"] = dates.to_series(index=dates)
        mask_frame["holidays"] = dates.isin(values=holiday.holidays)
        mask_frame["holiday_days_of_week"] = dates.dayofweek
        mask_frame["business_days"] = bday.get_business_days(dates=dates)

        for day, dow in zip(
            ["monday", "tuesday", "wednesday", "thursday", "friday"], range(5)
        ):
            mask_frame[f"{day}_holidays"] = (
                mask_frame["holiday_days_of_week"] == dow
            ) & mask_frame["holidays"]
        return mask_frame
