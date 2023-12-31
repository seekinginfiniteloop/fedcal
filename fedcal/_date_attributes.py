# fedcal _date_attributes.py
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

The _date_attributes module contains classes for handling general
date attributes of the federal calendar:
- business days (`FedBusDay`)
- holidays (`FedHolidays`)
- fiscal years/quarters (`FedFiscalCal`)
"""
from __future__ import annotations

import warnings
from typing import ClassVar

import numpy as np
import pandas as pd
from attrs import define, field
from numpy.typing import NDArray
from pandas import DatetimeIndex, Index, PeriodIndex, Series, Timestamp
from pandas.tseries.holiday import (
    USFederalHolidayCalendar,
    USMartinLutherKingJr,
    USColumbusDay,
    USLaborDay,
    USPresidentsDay,
    USMemorialDay,
    USThanksgivingDay,
    AbstractHolidayCalendar,
    Holiday,
    nearest_workday,
)
from pandas.tseries.offsets import CustomBusinessDay

from fedcal.time_utils import ensure_datetimeindex


@define(order=True, hash=True, kw_only=True)
class FedBusDay:

    """
    Class representing federal business days, excluding federal holidays.

    Attributes
    ----------
    fed_business_days (class attribute): Business day offset excluding US
    federal holidays and past proclaimed holidays.

    Methods
    -------
    get_business_days(dates) -> bool
        Determine if a given date is a federal business day.

    get_prior_business_day(date) -> Generator[pd.Timestamp, Any, None]
        Generates next prior business day to the date.

    """

    fed_business_days: ClassVar[CustomBusinessDay] | None = None

    def __attrs_post_init__(self) -> None:
        """
        Complete initialization of the instance and sets attributes
        """
        if not type(self).fed_business_days:
            hol_instance = FedHolidays()
            type(self).fed_business_days = CustomBusinessDay(
                normalize=True,
                holidays=hol_instance.holidays,
            )

    @classmethod
    def get_business_days(
        cls, dates: Timestamp | Series | DatetimeIndex
    ) -> NDArray[bool]:
        """
        Method for retrieving business days, adjusted for federal holidays.

        Parameters
        ----------
        dates : either a single pd.Timestamp or a Series of
        Timestamps for offsetting with fed_business_days.

        Returns
        -------
        ndarray of bool
            True if the date is a business day, False if not.
        """
        dates: DatetimeIndex = ensure_datetimeindex(dates=dates)
        with warnings.catch_warnings():
            warnings.simplefilter(action="ignore")
            return dates.isin(values=(dates + cls.fed_business_days))

    def get_prior_business_day(self, date: Timestamp) -> Timestamp:
        """
        Generates next earliest business day. Primarily for finding
        next-earliest business day before a military payday that doesn't
        fall on a business day.

        Returns
        -------
        next nearest business day prior to the given date
        """
        return self.fed_business_days.rollback(dt=date)


# Custom Holiday objects; it bothers me that only half of the rules in
# USFederalHolidayCalendar have their own variable. I know why, but... no.
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

@define(slots=False)
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
            name="1973 Christmas Eve proclamation (Nixon)", year=1973, month=12, day=24
        ),
        Holiday(
            name="1973 New Year's Eve proclamation (Nixon)", year=1973, month=12, day=31
        ),
    ]

    def __attrs_pre_init(self) -> None
        super().__init__(rules=type(self).rules)

    def holidays(self, start: Timestamp = None, end: Timestamp = None, return_name: bool = False) -> DatetimeIndex | Series:
        """
        Implements parent classes's method of the same name. Returns
        DatetimeIndex of holidays for either given dates or cls dates
        (1970-2199). Optional return flag returns a series with holidays
        named.

        Parameters
        ----------
        start : start date for the range, defaults to cls dates if None.
        end : end date for the range, defaults to cls dates if None.
        return_name : whether to return a series with holidays named.
        Defaults to False.

        Returns
        -------
        DatetimeIndex of holidays between the start and end dates, or
        Series of holidays with names of holidays if return_name flag.
        """
        return super().holidays(start=start, end=end, return_name=return_name)

    


    def get_proclamation_holidays(
        self, dates: Timestamp | DatetimeIndex | Series[Timestamp]
    ) -> NDArray[bool]:
        """
        Check if a given date was a holiday proclaimed by executive order.

        Parameters
        ----------
        dates : The dates to check.

        Returns
        -------
        True if the date was a proclaimed holiday, False otherwise.
        """
        proc_holidays =
        dates: DatetimeIndex = ensure_datetimeindex(dates=dates)
        return dates.isin(values=type(self).proclaimed_holidays)

    @staticmethod
    def guess_proclamation_holidays(
        dates: Timestamp | Series[Timestamp] | DatetimeIndex,
    ) -> NDArray[bool]:
        """
        Guess if a future Christmas Eve may be proclaimed a holiday based on
        Christmas Day's weekday.

        Parameters
        ----------
        dates : Dates for which to guess the holidays.

        Returns
        -------
        An ndarray of boolean values indicating whether each date is likely
        a proclaimed holiday. Only evaluates Christmas Eves.

        """
        dates = ensure_datetimeindex(dates=dates)
        christmas_days: DatetimeIndex = pd.to_datetime(
            arg=dates.year.astype(dtype=str) + "-12-25"
        )
        christmas_eves = christmas_days - pd.DateOffset(normalize=True, days=1)
        filtered_dates: DatetimeIndex = dates[dates.year > 2023]
        return (
            None
            if filtered_dates.empty
            else (
                christmas_days.weekday.isin(values=[1, 4])
                & (filtered_dates == christmas_eves)
            )
        )


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
