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

import warnings
from typing import TYPE_CHECKING

import pandas as pd
from attrs import define, field
from pandas.tseries.holiday import USFederalHolidayCalendar
from pandas.tseries.offsets import CustomBusinessDay

from fedcal import constants
from fedcal.time_utils import ensure_datetimeindex

if TYPE_CHECKING:
    from typing import ClassVar, Generator

    from numpy.typing import NDArray
    from pandas import DatetimeIndex, Index, PeriodIndex, Series, Timestamp


@define(order=True, auto_attribs=True)
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
                normalize=True, calendar=hol_instance.holidays
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
            next_business_days = dates + cls.fed_business_days
            return next_business_days == dates

    def get_prior_business_day(
        self, date: Timestamp
    ) -> Generator[Timestamp, None, None]:
        """
        Generates next earliest business day. Primarily for finding
        next-earliest business day before a military payday that doesn't
        fall on a business day.

        Yields
        ------
        next nearest business day prior to the given date
        """
        current_day: Timestamp = date - CustomBusinessDay(
            calendar=self.fed_business_days.calendar
        )
        while current_day < date:
            yield current_day
            current_day += CustomBusinessDay(calendar=self.fed_business_days.calendar)


@define(order=True, auto_attribs=True)
class FedHolidays:

    """
    Class representing federal holidays, including historically proclaimed
    holidays and optionally guessed future Christmas Eve proclamation holidays.

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

    #TODO: Implement as pd.AbstractHolidayCalendar
    """

    proclaimed_holidays: ClassVar[pd.DatetimeIndex] = pd.DatetimeIndex(
        data=(constants.HISTORICAL_HOLIDAYS_BY_PROCLAMATION), name="proclaimed_holidays"
    )

    holidays: ClassVar[pd.DataFrame] = None

    def __attrs_post_init__(self) -> None:
        """
        We initialize holidays if it's not already there.
        """
        if type(self).holidays is None:
            _base_cal = USFederalHolidayCalendar()
            _holidays: DatetimeIndex = _base_cal.holidays()
            type(self).holidays: DatetimeIndex = type(self).proclaimed_holidays.union(
                other=_holidays
            )

    def get_holidays(
        self, dates: Timestamp | DatetimeIndex | Series[bool]
    ) -> NDArray[bool] | bool:
        """
        Check if a given date is a federal holiday.

        Parameters
        ----------
        dates : The dates to check.

        Returns
        -------
        boolean array or bool; True if the date is a federal holiday, False
        otherwise.

        """
        dates = ensure_datetimeindex(dates=dates)
        return dates.isin(values=type(self).holidays)

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
        return christmas_days.weekday.isin(values=[1, 4]) & (
            filtered_dates == christmas_eves
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
