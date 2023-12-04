from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

from attrs import define, field
from pandas import DatetimeIndex, Timedelta, Timestamp, concat
from pandas.tseries.holiday import USFederalHolidayCalendar
from pandas.tseries.offsets import CustomBusinessDay

from constants import HISTORICAL_HOLIDAYS_BY_PROCLAMATION
from time_utils import to_datestamp

if TYPE_CHECKING:
    from fedcal import FedDateStamp


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

    def is_bday(self, date: Timestamp | "FedDateStamp") -> bool:
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
        next_business_day: Timestamp = (
            date - Timedelta(days=1)
        ) + self.fed_business_days
        return next_business_day == date


class GuessChristmasEveHoliday(Enum):
    """
    A simple enum class for setting preferences on FedHolidays. If YES, FedHoliday generates Christmas Eve days likely to be made a holiday under executive order.
    """

    YES = 1
    NO = 2


@define(order=True)
class FedHolidays:
    """
    Class representing federal holidays, including historically proclaimed holidays and optionally guessed Christmas Eve holidays.

    Attributes
    ----------
    proclaimed_holidays : List of holidays proclaimed by executive orders.
    holidays : Combined list of regular and proclaimed federal holidays.
    guess_christmas_eve_holiday : Enum to indicate if we should guess if future Presidents will proclaim a given Christmas Eve a holiday.

    Methods
    -------
    is_holiday(date) -> bool
        Check if a given date is a federal holiday.
    was_proclaimed_holiday(date) -> bool
        Check if a given date was a holiday by proclamation (most were Christmas Eve).
    guess_christmas_eve_proclamation_holiday(date) -> bool
        Guess if Christmas Eve is likely to be a holiday based on Christmas day.
    add_poss_Christmas_Eve_holidays() -> DatetimeIndex
        Add possible Christmas Eve holidays to the holiday list.
    """

    proclaimed_holidays: list[Timestamp] = field(
        default=HISTORICAL_HOLIDAYS_BY_PROCLAMATION
    )
    holidays: DatetimeIndex = field(init=False)

    guess_christmas_eve_holiday: GuessChristmasEveHoliday = field(
        default=GuessChristmasEveHoliday.NO
    )

    def __attrs_post_init__(self) -> None:
        """
        If you decide to roll the dice and guess on Presidential proclamations, then we add these to self.holidays
        """
        self.holidays = concat(
            [proclaimed_holidays, USFederalHolidayCalendar().holidays()]
        ).drop_duplicates()
        if self.guess_christmas_eve_holiday == GuessChristmasEveHoliday.YES:
            self.holidays = self.add_poss_Christmas_Eve_holidays()

    def is_holiday(self, date: Timestamp | "FedDateStamp") -> bool:
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

    def was_proclaimed_holiday(self, date: Timestamp | "FedDateStamp") -> bool:
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
        self, date: Timestamp | "FedDateStamp"
    ) -> bool:
        """
        Guess if Christmas Eve is likely to be a holiday based on Christmas day's weekday.

        Parameters
        ----------
        date : The date to check.

        Returns
        -------
        True if Christmas Eve is likely to be a holiday, False otherwise.
        """

        christmas: Timestamp = Timestamp(year=date.year, month=12, day=25)
        # Check if Christmas is on a Tuesday or Friday
        return christmas.dayofweek in [1, 4] and (date.month == 12 and date.day == 24)

    def add_poss_Christmas_Eve_holidays(self) -> DatetimeIndex:
        christmas_eves: list[Timestamp] = [
            Timestamp(year=holiday.year, month=12, day=24)
            for holiday in self.holidays
            if self.guess_christmas_eve_proclamation_holiday(date=holiday)
            and holiday.year > 2023
        ]
        return self.holidays.union(other=DatetimeIndex(data=christmas_eves))


@define(order=True)
class FedFiscalYear:
    """
    Class representing the federal fiscal year calculations.

    Attributes
    ----------
    date : Reference date for fiscal year calculations.

    Methods
    -------
    get_fiscal_year(date=None)
        Get the fiscal year for a given date.
    is_fiscal_year(year_to_check, date=None)
        Check if a given year matches the fiscal year of a date.
    """

    date: Timestamp = field(converter=to_datestamp)

    def get_fiscal_year(self, date: Timestamp | "FedDateStamp" | None = None) -> int:
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
        return date.year + 1 if date.month >= 10 else date.year

    def is_fiscal_year(
        self, year_to_check: int, date: Timestamp | "FedDateStamp" | None = None
    ) -> bool:
        """
        Check if a given year is the fiscal year of the provided date.

        Parameters
        ----------
        year_to_check : The fiscal year to check.
        date : The date to compare with.

        Returns
        -------
        True if the provided year matches the fiscal year of the date, False otherwise.
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
    get_fiscal_quarter(date=None)
        Get the fiscal quarter for a given date.

    is_fiscal_quarter(quarter_to_check, date=None)
        Check if a given quarter matches the fiscal quarter of a date.
    """

    date: Timestamp = field(converter=to_datestamp)

    def get_fiscal_quarter(self, date: Timestamp | None = None) -> int:
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
        self, quarter_to_check: int, date: Timestamp | None = None
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
