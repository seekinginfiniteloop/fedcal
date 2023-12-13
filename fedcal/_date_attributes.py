from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

import pandas as pd
from attrs import define, field
from pandas.tseries.holiday import USFederalHolidayCalendar
from pandas.tseries.offsets import CustomBusinessDay

import .constants
import .time_utils

if TYPE_CHECKING:
    from numpy import ndarray
    from pandas import Index, Series

    from .feddatestamp import FedDateStamp


@define(order=True)
class FedBusDay:

    """
    Class representing federal business days, excluding federal holidays.

    Attributes
    ----------
    fed_business_days : Business day offset excluding US federal holidays.

    Methods
    -------
    is_bday(date) -> bool
        Determine if a given date is a federal business day.

    """

    fed_business_days: CustomBusinessDay = field(
        factory=lambda: CustomBusinessDay(calendar=FedHolidays.holidays)
    )

    def is_bday(self, date: pd.Timestamp | "FedDateStamp") -> bool:
        """
        Class representing federal business days, excluding federal holidays.

        Attributes
        ----------
        fed_business_days : CustomBusinessDay
            Business day offset excluding US federal holidays.

        Methods
        -------
        is_bday(date)
            Determine if a given date is a federal business day.

        """
        next_business_day: pd.Timestamp = (
            date - pd.Timedelta(days=1)
        ) + self.fed_business_days
        return next_business_day == date


class GuessChristmasEveHoliday(Enum):

    """
    A simple enum class for setting preferences on FedHolidays. If YES,
    FedHoliday generates Christmas Eve days that *may*  be made a holiday
    under executive order.

    Why not just a simple bool? Because I want you understand what you are
    asking for here. This will make you read the comments, or at least type
    out "GuessChristmasEveHoliday.YES" in your code.
    """

    YES = 1
    NO = 2


@define(order=True)
class FedHolidays:

    """
    Class representing federal holidays, including historically proclaimed
    holidays and optionally guessed Christmas Eve holidays.

    Attributes
    ----------
    proclaimed_holidays : List of holidays proclaimed by executive orders.
    holidays : Combined list of regular and proclaimed federal holidays.
    guess_christmas_eve_holiday : Enum to indicate if we should guess if
    future Presidents will proclaim a given Christmas Eve a holiday.

    Methods
    -------
    is_holiday(date) -> bool
        Check if a given date is a federal holiday.
    was_proclaimed_holiday(date) -> bool
        Check if a given date was a holiday by proclamation (most were
        Christmas Eve).
    guess_christmas_eve_proclamation_holiday(date) -> bool
        Guess if Christmas Eve is likely to be a holiday based on Christmas
        day.
    guess_proclamation_holidays(pd.DatetimeIndex) -> Series
        Guess if any Christmas Eves in a pd.DatetimeIndex may be a holiday based
        on Christmas day
    add_poss_christmas_eve_holidays() -> pd.DatetimeIndex
        Add possible Christmas Eve holidays to the holiday list.

    """

    proclaimed_holidays: list[pd.Timestamp] = field(
        default=constants.HISTORICAL_HOLIDAYS_BY_PROCLAMATION
    )
    holidays: pd.DatetimeIndex = field(init=False)

    guess_christmas_eve_holiday: GuessChristmasEveHoliday = field(
        default=GuessChristmasEveHoliday.NO
    )

    def __attrs_post_init__(self) -> None:
        """
        If you decide to roll the dice and guess on Presidential proclamations, then we add these to self.holidays
        """
        self.holidays = pd.concat(
            [self.proclaimed_holidays, USFederalHolidayCalendar().holidays()]
        ).drop_duplicates()
        if self.guess_christmas_eve_holiday == GuessChristmasEveHoliday.YES:
            self.holidays = self.add_poss_christmas_eve_holidays()

    def is_holiday(self, date: pd.Timestamp | "FedDateStamp") -> bool:
        """
        Check if a given date is a federal holiday.

        Parameters
        ----------
        date : The date to check.

        Returns
        -------
        True if the date is a federal holiday, False otherwise.

        """
        return date in self.holidays

    def was_proclaimed_holiday(self, date: pd.Timestamp | "FedDateStamp") -> bool:
        """
        Check if a given date was a holiday proclaimed by executive order.

        Parameters
        ----------
        date : The date to check.

        Returns
        -------
        True if the date was a proclaimed holiday, False otherwise.

        """
        return date in self.proclaimed_holidays

    def guess_christmas_eve_proclamation_holiday(
        self, date: pd.Timestamp | "FedDateStamp"
    ) -> bool:
        """
        Guess if Christmas Eve is likely to be a holiday based on Christmas
        day's weekday.

        Parameters
        ----------
        date : The date to check.

        Returns
        -------
        True if Christmas Eve is likely to be a holiday, False otherwise.

        """

        christmas: pd.Timestamp = pd.Timestamp(year=date.year, month=12, day=25)
        # Check if Christmas is on a Tuesday or Friday
        return christmas.dayofweek in [1, 4] and (date.month == 12 and date.day == 24)

    @staticmethod
    def guess_proclamation_holidays(datetimeindex: pd.DatetimeIndex) -> "ndarray":
        """
        Guess if Christmas Eve may be proclaimed a holiday based on Christmas
        Day's weekday.

        Parameters
        ----------
        datetimeindex : pd.DatetimeIndex
            A Pandas DatetimeIndex for which to guess the holidays.

        Returns
        -------
        Pandas Series of boolean values indicating whether each date is likely
        a proclaimed holiday.

        """
        christmas_series: pd.DatetimeIndex = pd.to_datetime(
            arg=datetimeindex.year.astype(dtype=str) + "-12-25"
        )

        filtered_index: pd.DatetimeIndex = datetimeindex[datetimeindex.year > 2023]

        christmas_weekday: "Index" = christmas_series.dayofweek

        return christmas_weekday.isin(values=[1, 4]) & (
            (filtered_index.month == 12) & (filtered_index.day == 24)
        )

    def add_poss_christmas_eve_holidays(self) -> pd.DatetimeIndex:
        """
        Add possible Christmas Eve holidays using the
        guess_proclamation_holidays method.

        Returns
        -------
        A DatetimeIndex including the original holidays and any guessed
        Christmas Eve holidays.

        """
        christmas_eves: pd.DatetimeIndex = self.holidays[
            self.guess_proclamation_holidays(datetimeindex=self.holidays)
        ]

        return self.holidays.union(other=christmas_eves)


@define(order=True)
class FedFiscalYear:
    """
    Class representing the federal fiscal year calculations.

    Attributes
    ----------
    date : Reference date for fiscal year calculations.

    Methods
    -------
    get_fiscal_years(datetimeindex)
        get fiscal years for an input datetimeindex
    get_fiscal_year(date=None)
        Get the fiscal year for a given date.
    is_fiscal_year(year_to_check, date=None)
        Check if a given year matches the fiscal year of a date.

    """

    date: pd.Timestamp = field(converter=time_utils.to_datestamp)

    @staticmethod
    def get_fiscal_years(datetimeindex: pd.DatetimeIndex) -> "Series":
        """
        Calculate the fiscal year for each date in datetimeindex.

        Parameters
        ----------
        datetimeindex = A pandas DatetimeIndex for processing.

        Returns
        -------
        Pandas Series of integers representing the fiscal year for each date.

        """
        year_offset: int = (datetimeindex.month >= 10).astype(dtype=int)
        return datetimeindex.year + year_offset

    def get_fiscal_year(self, date: pd.Timestamp | "FedDateStamp" | None = None) -> int:
        """
        Calculate the fiscal year for a given date.

        Parameters
        ----------
        date : The date for which to calculate the fiscal year.

        Returns
        -------
        The fiscal year.

        """
        if date is None:
            date = self.date
        offset: int = int(date.month >= 10)
        return date.year + offset

    def is_fiscal_year(
        self, year_to_check: int, date: pd.Timestamp | "FedDateStamp" | None = None
    ) -> bool:
        """
        Check if a given year is the fiscal year of the provided date.

        Parameters
        ----------
        year_to_check : The fiscal year to check.
        date : The date to compare with.

        Returns
        -------
        True if the provided year matches the fiscal year of the date, False
        otherwise.

        """
        if date is None:
            date = self.date
        return self.get_fiscal_year(date=date) == year_to_check


@define(order=True)
class FedFiscalQuarter:

    """
    Class representing federal fiscal quarter calculations.

    Attributes
    ----------
    date : Reference date for fiscal quarter calculations.

    Methods
    -------
    get_fiscal_quarters(datetimeindex)
        Get the fiscal quarters for each date in datetimeindex.

    get_fiscal_quarter(date=None)
        Get the fiscal quarter for a given date.

    is_fiscal_quarter(quarter_to_check, date=None)
        Check if a given quarter matches the fiscal quarter of a date.

    """

    date: pd.Timestamp = field(converter=time_utils.to_datestamp)

    @staticmethod
    def get_fiscal_quarters(datetimeindex: pd.DatetimeIndex) -> "Series":
        """
        Calculate the fiscal quarter for each date in datetimeindex.

        Parameters
        ----------
        datetimeindex = A pandas DatetimeIndex for processing.

        Returns
        -------
        Pandas Series of integers representing the fiscal quarter for each
        date.

        """
        adjusted_month: Series = (datetimeindex.month + 2) % 12 + 1
        return ((adjusted_month - 1) // 3) + 1

    def get_fiscal_quarter(self, date: pd.Timestamp | None = None) -> int:
        """
        Check if a given quarter is the fiscal quarter of the provided date.

        Parameters
        ----------
        quarter_to_check : The fiscal quarter to check.
        date : The date to compare with.

        Returns
        -------
        True if the provided quarter matches the fiscal quarter of the
            date, False otherwise.

        """

        if date is None:
            date = self.date
        adjusted_month: int = (date.month + 2) % 12 + 1
        return ((adjusted_month - 1) // 3) + 1

    def is_fiscal_quarter(
        self, quarter_to_check: int, date: pd.Timestamp | None = None
    ) -> bool:
        """
        Check if a given quarter is the fiscal quarter of the provided date.

        Parameters
        ----------
        quarter_to_check : The fiscal quarter to check.
        date : The date to compare with.

        Returns
        -------
        True if the provided quarter matches the fiscal quarter of the
            date, False otherwise.

        """
        if date is None:
            date = self.date
        return self.get_fiscal_quarter(date=date) == quarter_to_check
