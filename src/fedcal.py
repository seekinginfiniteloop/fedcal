from __future__ import annotations

from datetime import date
from typing import Any, Self

from pandas import DatetimeIndex, Timestamp

from civpay import FedPayDay
from date_attributes import FedBusDay, FedFiscalQuarter, FedFiscalYear, FedHolidays
from dept_status import DepartmentState
from mil import MilitaryPayDay, MilPayPassRange, ProbableMilitaryPassDay
from time_utils import YearMonthDay, _pydate_to_posix, to_datestamp, to_feddateindex


class FedDateStamp(Timestamp):
    """
    A child class for pandas Timestamp that extends functionality for
    federal_calendar. For the record, I hate subclassing, but this was
    the cleanest way to add functionality to pandas Timestamp objects.
    FedTimestamp instances support all functionality of pandas' Timestamp
    objects, but add substantial functionality for federal_calendar.
    (https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.Timestamp.html).
    """

    def __new__(cls, ts_input=None, *args, **kwargs) -> Self:
        if ts_input is None:
            ts_input: Timestamp = Timestamp.now()

        return super().__new__(cls, ts_input, *args, **kwargs)

    @property
    def holiday(self) -> bool:
        """
        Returns True if the timestamp is a federal holiday, False otherwise.
        """
        return FedHolidays.is_holiday(date=self)

    @property
    def business_day(self) -> bool:
        """
        Returns True if the timestamp is a business day, False otherwise.
        """
        return FedBusDay.is_bday(date=self)

    @property
    def civ_payday(self) -> bool:
        """
        Returns True if the timestamp is a civilian payday, False otherwise.
        """
        return FedPayDay.is_fed_payday(self)

    @property
    def mil_payday(self) -> bool:
        pass

    @property
    def fiscal_quarter(self) -> int:
        """
        Returns the fiscal quarter of the timestamp.
        """
        return FedFiscalQuarter.get_fiscal_quarter(date=self)

    @property
    def fy(self) -> int:
        """
        Returns the fiscal year of the timestamp.
        """
        return FedFiscalYear.get_fiscal_year(date=self)

    @property
    def shutdown(self) -> bool:
        """
        Returns True if the timestamp is a shutdown date, False otherwise.
        """
        return is_shutdown()

    @property
    def appropriations_gap(self) -> bool:
        """
        Returns True if the timestamp is an appropriations gap date, False otherwise.
        """
        return is_appropriations_gap()

    @property
    def cr(self) -> bool:
        """
        Returns True if the timestamp is a continuing resolution date, False otherwise.
        """
        return is_continuing_resolution()

    @property
    def year_month_day(self) -> YearMonthDay:
        return YearMonthDay(year=self.year, month=self.month, day=self.day)

    @property
    def timestamp(self) -> int:
        """
        Overrides the pandas Timestamp.timestamp() method. Returns the number of seconds since the Unix epoch (1970-01-01 00:00:00 UTC) as an integer
        normalized to midnight (vice pandas' return of a float).

        :raises TypeError: _description_
        :return: _description_
        :rtype: int
        """
        date_obj = date(year=self.year, month=self.month, day=self.day)
        return _pydate_to_posix(pydate=date_obj)


class FedDateIndex(DatetimeIndex):
    def __new__(cls, data, *args, **kwargs) -> Self:
        instance: Self = super().__new__(cls, data, *args, **kwargs)
        instance = to_datestamp(instance)
        return instance

    @property
    def fy(self) -> int:
        for date in self.datetimeindex:
            return FedFiscalYear.get_fiscal_year(date=date)

    @property
    def fiscal_quarter(self) -> int:
        for date in self.datetimeindex:
            return FedFiscalQuarter.get_fiscal_quarter(date=date)

    @property
    def holidays(self) -> bool:
        for date in self.datetimeindex:
            return FedHolidays.is_holiday(date=date)

    @property
    def likely_Christmas_Eve_holiday(self) -> bool:
        for date in self.datetimeindex:
            return FedHolidays.likely_Christmas_Eve_holiday(date=date)

    @property
    def business_day(self) -> bool:
        """
        Returns True if the datetimeindex is a business day, False otherwise.
        """
        for date in self.datetimeindex:
            return FedBusDay.is_bday(date=date)

    @property
    def shutdown(self) -> bool:
        """
        Returns True if the datetimeindex is a shutdown date, False otherwise.
        """
        return self.datetimeindex.is_shutdown()

    @property
    def appropriations_gap(self) -> bool:
        """
        Returns True if the datetimeindex is an appropriations gap date, False otherwise.
        """
        return self.datetimeindex.is_appropriations_gap()

    @property
    def cr(self) -> bool:
        """
        Returns True if the datetimeindex is a continuing resolution date, False otherwise.
        """
        return self.datetimeindex.is_continuing_resolution()

    def contains(self, date: Timestamp) -> Any:
        """
        Checks if a date is within the range.

        Args:
            date (Timestamp | Any): The date to check.

        Returns:
            Any: True if the date is within the range, False otherwise.
        """
        if date is not isinstance(date, Timestamp):
            date = stamp_date(date=date)
        return self.start <= date <= self.end

    def overlaps(self, other: Timestamp | Any) -> Any:
        """
        Checks if the range overlaps with another range.

        Args:
            other (Timestamp | Any): The other range to check. Accepts Timestamps or any date-like object.

        Returns:
            Any: True if the ranges overlap, False otherwise.
        """
        if other is not isinstance(other, DatetimeIndex):
            other = to_datetimeindex()
        return self.start <= other.end and self.end >= other.start


@to_datestamp.register(cls=FedDateStamp)
def _return_datestamp(date_input: FedDateStamp) -> FedDateStamp:
    """
    We handle stray non-conversions by returning them.
    This function lives here away from its friends in time_utils to avoid
    circular import issues.
    """
    return date_input


@to_feddateindex.register(cls=FedDateIndex)
def _from_feddateindex(input_dates) -> "FedDateIndex":
    """
    We catch and return stray FedDateIndex objects that happen into our net.
    like _return_datestamp, this function lives here to avoid circular imports.
    """
    return input_dates
