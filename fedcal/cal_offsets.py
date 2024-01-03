# fedcal cal_offsets.py
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
Provides calendar-related attributes either for direct use or integration
with FedStamp and FedIndex, namely: federal holidays, business days, and
fiscal years/quarters.

The cal_offsets module contains classes for handling general
calendar offsets of the federal calendar:
- business days (`FedBusinessDay`)
- holidays (`FedHolidays`)
- fiscal years/quarters (`FedFiscalCal`)
"""
from __future__ import annotations

import warnings
from datetime import timedelta
from typing import ClassVar

import numpy as np
import pandas as pd
from attrs import define, field
from fedcal.time_utils import ensure_datetimeindex, get_today
from numpy.typing import NDArray
from pandas import DatetimeIndex, Index, PeriodIndex, Series, Timedelta, Timestamp
from pandas.tseries.holiday import (
    AbstractHolidayCalendar,
    Holiday,
    USColumbusDay,
    USLaborDay,
    USMartinLutherKingJr,
    USMemorialDay,
    USPresidentsDay,
    USThanksgivingDay,
    nearest_workday,
)
from pandas.tseries.offsets import CustomBusinessDay

# Custom Holiday objects; it bothers me that only half of the rules in
# USFederalHolidayCalendar have their own variable. I know it's because of
# their offsets, but... I just had to.

NewYearsDay = Holiday(name="New Year's Day", month=1, day=1, observance=nearest_workday)
MartinLutherKingJr: Holiday = USMartinLutherKingJr
PresidentsDay: Holiday = USPresidentsDay
MemorialDay: Holiday = USMemorialDay
Juneteenth = Holiday(
    name="Juneteenth National Independence Day",
    month=6,
    day=19,
    start_date=pd.Timestamp(year=2021, month=6, day=18),
    observance=nearest_workday,
)
IndependenceDay = Holiday(
    name="Independence Day", month=7, day=4, observance=nearest_workday
)
LaborDay: Holiday = USLaborDay
ColumbusDay: Holiday = USColumbusDay
VeteransDay = Holiday(name="Veterans Day", month=11, day=11, observance=nearest_workday)
ThanksgivingDay: Holiday = USThanksgivingDay
ChristmasDay = Holiday(
    name="Christmas Day", month=12, day=25, observance=nearest_workday
)


@define(order=False, slots=False)
class FedHolidays(AbstractHolidayCalendar):

    """
    Custom implementation based on pandas' USFederalHolidayCalendar and using
    pandas' AbstractHolidayCalendar base/meta calendar.

    Customized to add additional functionality and supply proclaimed holidays.

    US Federal Government Holiday Calendar based on rules specified by:
    https://www.opm.gov/policy-data-oversight/pay-leave/federal-holidays/

    Attributes
    ----------
    proclaimed_holidays : Series of holidays proclaimed by executive orders.
    holidays : Combined Series of regular and proclaimed federal
    holidays.

    np_holidays : vectorized holidays in a numpy array for faster operations

    Methods
    -------
    get_holidays(date) -> Series[bool]
        Check if a given date is a federal holiday.
    get_proclamation_holidays(date) -> Series[bool]
        Check if a given date was a holiday by proclamation (most were
        Christmas Eve).
    guess_proclamation_holidays(dates) -> Series[bool]
        Guess if any future Christmas Eves in a pd.DatetimeIndex may be a
        holiday based on Christmas day
    """

    _prefix: ClassVar[str] = "FH"

    name: ClassVar[str] = "USFederalHolidays"

    rules: ClassVar[list[Holiday]] = [
        NewYearsDay,
        MartinLutherKingJr,
        PresidentsDay,
        MemorialDay,
        Juneteenth,
        IndependenceDay,
        LaborDay,
        ColumbusDay,
        VeteransDay,
        ThanksgivingDay,
        ChristmasDay,
        # now for proclamation holidays:
        Holiday(
            name="2020 Christmas Eve proclamation (Trump)", year=2020, month=12, day=24
        ),
        Holiday(
            name="2019 Christmas Eve proclamation (Trump)", year=2019, month=12, day=24
        ),
        Holiday(
            name="2018 Christmas Eve by proclamation (Trump)",
            year=2018,
            month=12,
            day=24,
        ),
        Holiday(
            name="2015 Christmas Eve proclamation (Obama)", year=2015, month=12, day=24
        ),
        Holiday(
            name="2014 Christmas Eve proclamation (Obama)", year=2014, month=12, day=26
        ),
        Holiday(
            name="2012 Christmas Eve proclamation (Obama)", year=2012, month=12, day=24
        ),
        Holiday(
            name="2007 Christmas Eve proclamation (GW Bush)",
            year=2007,
            month=12,
            day=24,
        ),
        Holiday(
            name="2001 Christmas Eve proclamation (GW Bush)",
            year=2001,
            month=12,
            day=24,
        ),
        Holiday(
            name="1979 Christmas Eve proclamation (Carter)", year=1979, month=12, day=24
        ),
        Holiday(
            name="1973 New Year's Eve proclamation (Nixon)", year=1973, month=12, day=31
        ),
        Holiday(
            name="1973 Christmas Eve proclamation (Nixon)", year=1973, month=12, day=24
        ),
    ]

    proclaimed_holidays: ClassVar[list[Holiday]] = [
        rule for rule in type(self).rules if rule.year
    ]
    scheduled_holidays: ClassVar[list[Holiday]] = [
        rule for rule in type(self).rules if not rule.year
    ]

    np_holidays: ClassVar[NDArray] = None

    def __attrs_post_init__(self) -> None:
        """
        Make sure Abstract Holiday calendar and our attributes are running
        properly.
        """
        super().__init__(name=type(self).name, rules=type(self).rules)
        if not hasattr(type(self), "np_holidays") or not hasattr:(type(self), "np_cal"):
                type(self).np_holidays = self.holidays().to_numpy()




    def holidays(
        self,
        start: Timestamp = None,
        end: Timestamp = None,
        return_name: bool = False,
        with_proclamation: bool = True,
    ) -> DatetimeIndex | Series[str]:
        """
        Implements parent classes's method of the same name. Returns
        DatetimeIndex of holidays for either given dates or class dates
        (1970-2199). Optional return flag returns a series with holidays
        named.

        Parameters
        ----------
        start : start date for the range, defaults to class dates if None.
        end : end date for the range, defaults to class dates if None.
        return_name : whether to return a series with holidays named.
        Defaults to False.
        with_proclamation : whether to include historical proclamation
        holidays (i.e. one-off Christmas Eves), defaults to True.

        Returns
        -------
        DatetimeIndex of holidays between the start and end dates, or
        Series of holidays with names of holidays if return_name flag
        and dates as the index.
        """
        if with_proclamation:
            return super().holidays(start=start, end=end, return_name=return_name)
        else:
            return AbstractHolidayCalendar(
                rules=type(self).scheduled_holidays
            ).holidays(start=start, end=end, return_name=return_name)

    def proclamation_holidays(
        self, start: Timestamp = None, end: Timestamp = None, return_name: bool = False
    ) -> DatetimeIndex | Series[str]:
        """
        Retrieve dates for proclamation holidays only. If dates provided,
        returns only within date range. If return_name flag given, returns a
        series with holidays named, otherwise a DatetimeIndex with only dates.

        Parameters
        ----------
        start : start date for the range, defaults to class dates if None.
        end : end date for the range, defaults to class dates if None.
        return_name : whether to return a series with holidays named.
        Defaults to False.

        Returns
        -------
        DatetimeIndex of holidays between the start and end dates, or
        Series of holidays with names of holidays if return_name flag
        and dates as the index.
        """
        only_proc_hols_instance: AbstractHolidayCalendar = AbstractHolidayCalendar(
            name="USFederalProclamationHolidays", rules=type(self).proclaimed_holidays
        )
        return only_proc_hols_instance.holidays(
            "weeks",
        )

    def _calculate_historical_probabilities(self) -> pd.Series[float]:
        """
        Handles the heavier work of calculating the probabilities
        for estimate_future_proclamation_holidays.

        Returns
        -------
            series of floats giving rough probabilities a future
            Christmas Eve may be a proclamation holiday based on
            its day of the week compared to historical trends.
        """
        _hist_xmas: DatetimeIndex = ChristmasDay.dates(
            start_date="1970-01-01", end_date=get_today()
        )
        _hist_xmas_hol_dow: Series[
            int
        ] = _hist_xmas.to_series().dt.day_of_week.value_counts()

        _hist_p_hols: Series[
            Timestamp
        ] = self.proclamation_holidays().to_series() + pd.DateOffset(days=1)
        _hist_adj_xmas_dow: Series[int] = _hist_p_hols[
            _hist_p_hols.index.isin(_hist_xmas)
        ].dt.day_of_week.value_counts()

        return _hist_adj_xmas_dow / _hist_xmas_hol_dow

    def estimate_future_proclamation_holidays(
        self,
        future_dates: Timestamp | Series[Timestamp] | DatetimeIndex,
    ) -> Series[float]:
        """
        Roughly estimate if a future Christmas Eve may be proclaimed a holiday
        based on Christmas Day's weekday. Of the 10 such proclamations to
        date, 6 (60%) fell on a Tuesday, 2 on a Friday, and 1 each on
        Wednesday and Thursday. The associated proclamation holiday for the
        Thursday actually fell on the 26th... we omit the 26th here because 1
        is not a pattern... The same goes for Nixon's surprise New Year's Eve.

        Parameters
        ----------
        future_dates : Dates for which to guess the holidays.

        Returns
        -------
        A Series of dates with float probabilities they could be declared a
        proclamation holiday based on their day of week and whether they're a
        Christmas Eve.

        """

        dates: DatetimeIndex = ensure_datetimeindex(dates=future_dates)
        max_past: Timestamp = get_today()
        if dates.max() <= max_past:
            raise ValueError(
                f"No dates in provided index are in the future, latest date was: {dates.max()}"
            )

        historical_probabilities: Series[
            float
        ] = self._calculate_historical_probabilities()

        eval_dates: DatetimeIndex = dates[
            (dates.month == 12)
            & (dates.day == 24)
            & (dates.dayofweek < 5)
            & (dates > max_past)
        ]
        if eval_dates.empty:
            return pd.Series(data=np.zeros(shape=len(dates), dtype=bool), index=dates)

        eval_probabilities = eval_dates.dayofweek.map(
            mapper=historical_probabilities
        ).fillna(value=0)
        return pd.Series(
            data=eval_probabilities.reindex(dates, fill_value=0), index=dates
        )


@define(order=False, slots=False)
class FedBusinessDay(CustomBusinessDay):

    """
    Class representing federal business days, adjusted for federal holidays.
    As a CustomBusinessDay object, it may be directly applied to a pandas
    timeseries with simple addition/subtraction (see examples below):

    Attributes
    ----------
    self : CustomBusinessDay child class (the most important thing here)
    You probably won't need to touch any of these defaults and can happily
    call it as FedHolidays()

    n : defaults to 1, number of days represented by the offset. Probably
    never need to change.

    weekmask : defaults to "Mon Tue Wed Thu Fri", and business day in most
    situations, but here if you need to pass a custom weekmask. Note:
    if you pass a custom weekmask, you must also pass a custom calendar.
    This can just be (np.busdaycalendar(weekmask=your_week_mask, holidays=FedHolidays().np_holidays))

    normalize : True -- normalized offset. Note, it will not pass equality
        tests with non-normalized offsets.

    calendar : We default to a numpy busdaycalendar with vectorized holidays.

    Methods
    -------
    *inherits methods from CustomBusinessDay and BusinessDay, such as:

    is_on_offset(dt: Timestamp) -> bool
        Checks if a given date is on a federal business day.

    rollback(dt: Timestamp) -> Timestamp
        rolls the date back to the previous business day if not a business day

    rollforward(dt: Timestamp) -> Timestamp
        rolls the date forward to the next business day if not a business day

    Examples
    --------
    ```python
    # Create a DatetimeIndex of only business days:
    >>> import pandas as pd
    >>> import fedcal as fc
    >>> fbd = fc.FedBusinessDay()
    >>> bdays = pd.date_range(start="2021-01-01", end="2022-01-10", freq=fbd)

    # Shift the result to the next business day (next day on the offset) --
    # for Timestamp or across a DatetimeIndex/Timestamp Series
    >>> ts = pd.to_datetime('2024-1-1') # New Years' Day, a Monday
    >>> fbd.is_on_offset(ts)
    False
    >>> next_business_day = ts + fbd   # subtract for the prior business day
    2024-1-2 00:00:00

    # Add 5 business days for processing (or subtract, or whatever):
    >>> five_bdays = your_datetimeindex + fc.FedBusinessDay(offset=pd.Timedelta(days=5))
    ```
    """

    _prefix: ClassVar[str] = "F"

    n: int = 1  # default from CBD and you shouldn't need to change it
    weekmask: str = "Mon Tue Wed Thu Fri"  # default from CBD
    normalize: bool = True

    # We use numpy arrays for peppiness
    calendar: ClassVar[
        [np.busdaycalendar | AbstractHolidayCalendar]
    ] = np.busdaycalendar(weekmask="1111100", holidays=FedHolidays().np_holidays)

    # we're using the numpy calendar with holidays instead
    holidays: list[Timestamp | np.datetime64] | None = None
    offset: timedelta | Timedelta = timedelta(days=0)

    def __attrs_post_init(self) -> None:
        """We make sure CBD is initiated how we want."""
        super().__init__(
            n=self.n,
            normalize=self.normalize,
            weekmask=self.weekmask,
            holidays=self.holidays,
            calendar=self.calendar,
            offset=self.offset,
        )

    def get_business_days(
        self, dates: Timestamp | Series[Timestamp] | DatetimeIndex, as_bool: bool = False
    ) -> DatetimeIndex | Series[bool] | None:
        """
        Retrieve a Datetimeindex of business days. If as_bool flag is True,
        returns a boolean array of the same length as the input dates.

        Parameters
        ----------
        dates : either a single pd.Timestamp, a Series of
        Timestamps, or DatetimeIndex for offsetting with fed_business_days.
        as_bool : whether to return a boolean array. Defaults to False.

        Returns
        -------
        DatetimeIndex of business days. If as_bool flag is True, returns a
        boolean array reflecting business days in the range.

        """
        dates: DatetimeIndex = ensure_datetimeindex(dates=dates)

        with warnings.catch_warnings():
            warnings.simplefilter(action="ignore")
            if as_bool:
                return dates.isin(values=(dates + self))
            else:
                dates + self

    def get_prior_business_day(self, date: Timestamp) -> Timestamp:
        """
        Generates next earliest business day. Primarily for finding
        next-earliest business day before a military payday that doesn't
        fall on a business day.

        Returns
        -------
        next nearest business day prior to the given date
        """
        return self.rollback(dt=date)


@define(order=True)
class FedFiscalCal:
    """
    Class representing the federal fiscal year calculations.

    Attributes
    ----------
    dates : Reference dates for fiscal year calculations.

    fys_fqs : PeriodIndex of fiscal years and quarters in 'YYYYQ#' format.

    fys : Index of fiscal years as integers

    fqs : Index of fiscal quarters as integers

    fq_start : start day of fiscal quarters

    fq_end : end day of fiscal quarters

    fy_start : start day of fiscal years

    fy_end : end day of fiscal years

    Notes
    -----
    *Private Methods*:
    - _get_cal(dates)
        gets a tuple of the class attributes, fys_fqs, fys, and fqs. Used for
        setting instance attrs.
    - _get_fq_start_end()
        gets a tuple of the class attributes, fq_start, and fq_end. Used for
        setting instance attrs.
    - _get_fy_start_end()
        gets a tuple of the class attributes, fy_start, and fy_end. Used for
        setting instance attrs.
    """

    dates: DatetimeIndex | Series[Timestamp] | Timestamp | None = field(default=None)

    fys_fqs: PeriodIndex | None = field(default=None, init=False)

    fys: Index[int] | None = field(default=None, init=False)

    fqs: Index[int] | None = field(default=None, init=False)

    fq_start: PeriodIndex | None = field(default=None, init=False)

    fq_end: PeriodIndex | None = field(default=None, init=False)

    fy_start: PeriodIndex | None = field(default=None, init=False)

    fy_end: PeriodIndex | None = field(default=None, init=False)

    def __attrs_post_init__(self) -> None:
        """
        Complete initialization of the instance and sets attributes
        """
        self.dates = ensure_datetimeindex(dates=self.dates)
        self.fys_fqs, self.fys, self.fqs = self._get_cal()
        self.fq_start, self.fq_end = self._get_fq_start_end()
        self.fy_start, self.fy_end = self._get_fy_start_end()

    def _get_cal(
        self,
        dates: DatetimeIndex | pd.Series[Timestamp] | Timestamp | None = None,
    ) -> tuple[PeriodIndex, Series[int], Series[int]]:
        """
        Calculate the fiscal year for each date in datetimeindex.

        Parameters
        ----------
        dates = dates for processing, else uses self.dates

        Returns
        -------
        A tuple of the class attributes, fys_fqs, fys, and fqs.
        """
        dates = ensure_datetimeindex(dates=dates) if dates else self.dates

        fy_fq_idx: PeriodIndex = dates.to_period(freq="Q-SEP")

        fys: Index[int] = fy_fq_idx.qyear
        fqs: Index[int] = fy_fq_idx.quarter
        return fy_fq_idx, fys, fqs

    def _get_fq_start_end(self) -> tuple[PeriodIndex, PeriodIndex]:
        """
        Calculate the start and end dates of each fiscal quarter.

        Returns
        -------
        A tuple of the class attributes, fq_start, and fq_end as PeriodIndexes.
        """
        return self.fys_fqs.asfreq(freq="D", how="S"), self.fys_fqs.asfreq(
            freq="D", how="E"
        )

    def _get_fy_start_end(self) -> tuple[PeriodIndex, PeriodIndex]:
        """
        Calculate the start and end dates of each fiscal year.

        Returns
        -------
        A tuple of two PeriodIndexes: fy_start and fy_end.
        """
        fy_start: DatetimeIndex = self.fys_fqs[self.fys_fqs.quarter == 1].asfreq(
            "D", how="start"
        )
        fy_end: DatetimeIndex = self.fys_fqs[self.fys_fqs.quarter == 4].asfreq(
            "D", how="end"
        )

        return fy_start, fy_end
