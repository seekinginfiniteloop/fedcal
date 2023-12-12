from __future__ import annotations
from typing import TYPE_CHECKING
from enum import Enum, unique
from pandas import DataFrame, Series, Timestamp, Timedelta, date_range

from attrs import define, field

from ._date_attributes import FedBusDay, FedHolidays
from .time_utils import to_datestamp, to_feddateindex

if TYPE_CHECKING:
    from pandas import DatetimeIndex

    from .feddatestamp import FedDateStamp
    from .feddateindex import FedDateIndex


@define(order=True)
class MilitaryPayDay:
    """
    Handles the calculation and verification of military paydays.

    Attributes
    ----------
    date: date used for calculations.

    Methods
    -------
    is_military_payday(date=None) -> bool
        Determines if the given date is a military payday.

    Notes
    -----
    *Private Methods*:
        _calculate_next_payday(date, next_month)
            Calculates the next military payday based on the given date.

        _generate_payday_range(payday)
            Generates a range of dates around a payday for further processing.

        _is_next_bday_in_range(date, payday_range)
            Checks if the next business day falls within the provided range of dates.
    """

    date: "FedDateStamp" = field(converter=to_datestamp)

    def is_military_payday(
        self, date: Timestamp | "FedDateStamp" | None = None
    ) -> bool:
        """
        Determines if the given date is a military payday.

        Parameters
        ----------
        date : date to check, defaults to the date attribute if None.

        Returns
        -------
        Boolean indicating whether the date is a military payday.
        """
        if date is None:
            date: "FedDateStamp" = self.date

        if date.day in (1, 15) and FedBusDay.is_bday(date=date):
            return True

        # Handle dates that are not the 1st or 15th
        if date.day > 15:
            next_payday: Timestamp = self._calculate_next_payday(
                date=date, next_month=True
            )
            payday_range: "DatetimeIndex" = self._generate_payday_range(
                payday=next_payday
            )
        elif date.day < 15:
            next_payday = self._calculate_next_payday(date=date, next_month=False)
            payday_range = self._generate_payday_range(payday=next_payday)

        return self._is_next_bday_in_range(date=date, payday_range=payday_range)

    def _calculate_next_payday(
        self, date: Timestamp | "FedDateStamp", next_month: bool
    ) -> Timestamp:
        """
        Calculates the next military payday based on the given date.

        Parameters
        ----------
        date : date from which to calculate the next payday.
        next_month : boolean indicating whether to calculate for the next month.

        Returns
        -------
        FedDateStamp of the next military payday.
        """
        if next_month:
            if date.month == 12:
                # If it's December, increment year and reset to Jan
                year: int = date.year + 1
                month: int = 1
            else:
                year: int = date.year
                month: int = date.month + 1
            day: int = 1
        else:
            year: int = date.year
            month: int = date.month
            day: int = 15

        return to_datestamp(Timestamp(year=year, month=month, day=day))

    def _generate_payday_range(
        self, payday: Timestamp | "FedDateStamp"
    ) -> "DatetimeIndex":
        """
        Generates a range of dates around a payday for further processing.

        Parameters
        ----------
        payday : date of the payday around which to generate the range.

        Returns
        -------
        DatetimeIndex of dates around the payday.
        """
        return date_range(
            start=payday - Timedelta(days=3), end=payday - Timedelta(days=1)
        )

    def _is_next_bday_in_range(
        self, date: Timestamp | "FedDateStamp", payday_range: "DatetimeIndex"
    ) -> bool:
        """
        Checks if the next business day falls within the provided range of dates.

        Parameters
        ----------
        date : date to check.
        payday_range : range of dates to consider.

        Returns
        -------
        Boolean indicating if the next business day is in the range.
        """
        return next(
            (day == date for day in payday_range[::-1] if FedBusDay.is_bday(date=day)),
            False,
        )


@define(order=True)
class ProbableMilitaryPassDay:
    """
    Assesses the likelihood of a given date being a military pass day.

    Attributes
    ----------
    date : date used for determining pass days.

    Methods
    -------
    is_likely_passday(date=None) -> bool
        Evaluates whether the given date is likely a military pass day.

    Notes
    -----
    While technically military passes extend through non-business days, passes
    falling on non-business days don't meaningfully affect available personnel.
    Since our goal is enabling useful data analysis, we do not account for passes falling on non-business days.

    Military passdays are highly variable. When they are granted can vary
    even within major commands or at a single location based on commanders'
    discretion and mission needs. While we try to guess at what day will be
    most likely to be a passday for the majority of members, the overall goal
    is to roughly capture the loss of person-power for these periods for
    offices or locations relying heavily on military personnel, enabling
    productivity and microeconomic analysis.

        Current rules set the following framework (in _likely_passday):
        - If Christmas Eve is a weekday, Christmas Eve.
        - If Monday holiday, Friday is the likely passday.
        - If Friday is the holiday, Monday is the likely passday.
        - If Tuesday, Monday.
        - If Thursday, Friday.
        - If Wednesday, Thursday.

    TODO: In future versions, I hope to add customizable rules for evaluating
    likely passdays (i.e. a Wednesday holiday's passday will be Tuesday
    instead of Thursday).

    *Private Methods*:
        _get_holidays_in_range(date)
            Retrieves holidays within a specified range around a date.

        _likely_passday(date, holidays_in_offset)
            Determines if the given date is likely a pass day based on surrounding holidays.

    """

    date: "FedDateStamp" = field(converter=to_datestamp)

    def is_likely_passday(self, date: "FedDateStamp" | None = None) -> bool:
        """
        Evaluates whether the given date is likely a military pass day.

        Parameters
        ----------
        date : date to evaluate, defaults to the date attribute if None.

        Returns
        -------
        Boolean indicating whether the date is likely a pass day.
        """
        if date is None:
            date = self.date
        elif not FedBusinessDay.is_bday(date=date):
            return False

        holidays_in_offset: list["FedDateStamp"] | None = self._get_holidays_in_range(
            date=date
        )
        if len(holidays_in_offset) == 0:
            return False
        elif self._likely_passday(date=date, holidays_in_offset=holidays_in_offset):
            return True
        else:
            return False

    @staticmethod
    def _get_holidays_in_range(date: "FedDateStamp") -> list["FedDateStamp"] | None:
        """
        Retrieves holidays within a specified range around a date.

        Parameters
        ----------
        date : date around which to retrieve holidays.

        Returns
        -------
        List of holidays within the specified range.
        """
        offset_range: "DatetimeIndex" = date_range(
            start=date - Timedelta(days=3), end=date + Timedelta(days=3)
        )
        if holidays_in_offset := [
            day for day in offset_range if FedHolidays.is_holiday(date=day)
        ]:
            return holidays_in_offset

    @staticmethod
    def _likely_passday(
        date: "FedDateStamp", holidays_in_offset: list["FedDateStamp"]
    ) -> bool:
        """
        Determines if the given date is likely a pass day based on surrounding holidays.

        Parameters
        ----------
        date : date to evaluate.
        holidays_in_offset : list of holidays within a relevant range.

        Returns
        -------
        Boolean indicating if the date is likely a pass day.

        """
        for holiday in holidays_in_offset:
            if holiday.month == 12 and date.day == 24:
                return True
            if (
                (holiday.dayofweek == 0 and date.dayofweek == 4)
                or (holiday.dayofweek == 3 and date.dayofweek == 4)
                or (holiday.dayofweek == 4 and date.dayofweek == 0)
                or (holiday.dayofweek == 1 and date.dayofweek == 0)
                or (holiday.dayofweek == 2 and date.dayofweek == 3)
            ):
                return True
        return False


@unique
class MilDay(Enum):
    """
    Enum for military payday types.
    """

    PAYDAY = "Military payday"
    LIKELY_PASS = "Likely military passday"
    PAY_AND_PASS = "Military paydays and likely passdays"


@define(order=True)
class MilPayPassRange:
    """
    A class for generating a range of military paydays and pass days.

    Attributes
    ----------
    start : Start date for the range. Defaults to Unix Epoch of 1970-1-1.
    end : End date for the range. Like FedPayDay, defaults to 2040-9-30.
    milday : Type of military day to generate as a MilDay enum object (payday,
        pass day, or both).Default is both (MilDay.PAY_AND_PASS)
    daterange : DatetimeIndex of the start, end range.
    paydays : List of military paydays in daterange.
    passdays : List of military pass days in daterange.

    Methods
    -------
    get_mil_dates(self) -> Tuple[list]
        Retrieves military pay and pass days within the specified range.

    get_milpay_series(self) -> Series
        Returns a Series of military paydays.

    get_milpay_list() -> list
        Returns a list of military paydays.

    get_milpass_series() -> Series
        Returns a Series of probable military pass days.

    get_milpass_list() -> list
        Returns a list of probable military pass days.

    get_mil_dates_dataframe() -> DataFrame
        Returns a DataFrame of military pay and pass days.
    """

    start: "FedDateStamp" = field(
        default=Timestamp(year=1970, month=1, day=1), converter=to_datestamp
    )
    end: "FedDateStamp" = field(
        default=Timestamp(year=2040, month=9, day=30), converter=to_datestamp
    )
    milday: MilDay = field(default=MilDay.PAY_AND_PASS)

    def __attrs_post_init__(self) -> None:
        """
        Finishes initializing the instance, generating daterange and attributes paydays and passdays (see above.)
        """
        self.daterange: "FedDateIndex" = to_feddateindex((self.start, self.end))
        self.paydays, self.passdays = self.get_mil_dates()

    def get_mil_dates(
        self,
    ) -> tuple[list["FedDateStamp" | None], list["FedDateStamp" | None]]:
        """
        Retrieves military pay and pass days within the specified range.
        The range is determined by the start and end dates of the instance.
        Populates the paydays and passdays lists based on the selected MilDay type.

        Returns
        -------
        A tuple containing two lists: (paydays, passdays).
        """
        paydays: list = []
        passdays: list = []
        for day in self.daterange:
            if self.milday in [
                MilDay.PAYDAY,
                MilDay.PAY_AND_PASS,
            ] and MilitaryPayDay.is_military_payday(day):
                paydays.append(day)
            if self.milday in [
                MilDay.LIKELY_PASS,
                MilDay.PAY_AND_PASS,
            ] and ProbableMilitaryPassDay.is_likely_passday(day):
                passdays.append(day)

        return paydays, passdays

    def get_milpay_series(self) -> Series:
        """
        Returns a pandas Series of military paydays.

        Returns
        -------
        A pandas Series where each entry is a military payday within the range.

        Raises
        ------
        AttributeError
            If no military paydays are available.
        """
        if not self.paydays:
            raise AttributeError("No military paydays available.")
        return Series(data=self.paydays, name="milpayday")

    def get_milpay_list(self) -> list:
        """
        Returns a list of military paydays.

        Returns
        -------
        A list containing all military paydays within the specified range.
        """
        return self.get_milpay_series().tolist()

    def get_milpass_series(self) -> Series:
        """
        Returns a pandas Series of probable military pass days.

        Returns
        -------
        A pandas Series where each entry is a probable military pass day
        within the range.

        Raises
        ------
        AttributeError
            If no military pass days are available.
        """
        if not self.passdays:
            raise AttributeError("No military pass days available.")
        return Series(data=self.passdays, name="milpassday")

    def get_milpass_list(self) -> list:
        """
        Returns a list of probable military pass days.

        Returns
        -------
        A list containing all probable military pass days within the specified
        range.
        """
        return self.get_milpass_series().tolist()

    def get_mil_dates_dataframe(self) -> DataFrame:
        """
        Returns a DataFrame of military pay and pass days.

        Returns
        -------
        A pandas DataFrame with two columns: 'PayDays' and 'PassDays', each
        containing the respective dates within the specified range.
        """
        data: dict[str, list["FedDateStamp" | None]] = {
            "PayDays": self.paydays,
            "PassDays": self.passdays,
        }
        return DataFrame(data=data)
