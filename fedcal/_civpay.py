from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd
from attrs import define, field

import .constants
import .time_utils

if TYPE_CHECKING:
    from .feddateindex import FedDateIndex
    from .feddatestamp import FedDateStamp


@define(order=True)
class FedPayDay:

    """
    Represents federal paydays, providing functionalities to generate, check,
    and retrieve paydays within a specified range.

    Attributes
    ----------
    reference_date : default reference date for calculating paydays.
    end_date : date till which paydays are calculated.

    Methods
    -------
    generate_paydays(end_date)
        Generates federal paydays between the reference date and the specified
        end date.

    is_fed_payday(date=None)
        Checks if a given date is a federal payday.

    get_paydays_as_index(start=None, end=None)
        Returns a FedDateIndex of paydays between the start and end dates.

    get_paydays_as_list(start=None, end=None)
        Returns a list of federal paydays between the start and end dates.

    get_paydays_as_series(start=None, end=None)
        Returns a pandas pd.Series of federal paydays between the start and end
        dates.

    """

    reference_date: pd.Timestamp | "FedDateStamp" = field(
        default=constants.FEDPAYDAY_REFERENCE_DATE, converter=time_utils.to_datestamp
    )
    end_date: pd.Timestamp | "FedDateStamp" = field(
        default=pd.Timestamp(year=2040, month=9, day=30), converter=time_utils.to_datestamp
    )

    def __attrs_post_init__(self) -> None:
        self.paydays: pd.DatetimeIndex = self.generate_paydays()

    def generate_paydays(self, end_date: pd.Timestamp | "FedDateStamp") -> None:
        """
        Generates federal paydays between the reference date and the specified
        end date.

        Parameters
        ----------
        end_date : date until which paydays are to be generated.

        Returns
        -------
        pd.DatetimeIndex of generated paydays.

        """
        if end_date > self.reference_date:
            return pd.date_range(start=self.reference_date, end=end_date, freq="2W-FRI")
        else:
            raise ValueError("federal_calendar only supports dates after 1970-1-1.")

    def is_fed_payday(self, date: pd.Timestamp | "FedDateStamp" | None = None) -> bool:
        """
        Checks if a given date is a federal payday.

        Parameters
        ----------
        date : date to check, defaults to end_date if None.

        Returns
        -------
        Boolean indicating whether the date is a federal payday.

        """
        if date is None:
            date = self.end_date
        if (not self.paydays) or (self.paydays.ceil(freq="D") < date):
            self.paydays = self.generate_paydays(date=date)
        return date in self.paydays

    def get_paydays_as_index(
        self,
        start: pd.Timestamp | "FedDateStamp" | None = None,
        end: pd.Timestamp | "FedDateStamp" | None = None,
    ) -> FedDateIndex:
        """
        Returns a FedDateIndex of paydays between the start and end dates.

        Parameters
        ----------
        start : start date for the range, defaults to reference_date if None.
        end : end date for the range, defaults to end_date if None.

        Returns
        -------
        FedDateIndex of paydays within the specified range.

        """
        if end and ((self.paydays.ceil(freq="D") < end) or (not self.paydays)):
            self.paydays = self.generate_paydays(date=end)
        return FedDateIndex(
            self.paydays[
                (self.paydays >= start or self.reference_date)
                & (self.paydays <= end or self.end_date)
            ]
        )

    def get_paydays_as_list(
        self,
        start: pd.Timestamp | "FedDateStamp" | None = None,
        end: pd.Timestamp | "FedDateStamp" | None = None,
    ) -> list[pd.Timestamp]:
        """
        Returns a list of federal paydays between the start and end dates.

        Parameters
        ----------
        start : start date for the range, defaults to reference_date if None.
        end : end date for the range, defaults to end_date if None.

        Returns
        -------
        List of paydays within the specified range.

        """
        return self.get_paydays_as_index(
            start=start or self.reference_date, end=end or self.end_date
        ).tolist()

    def get_paydays_as_series(
        self,
        start: pd.Timestamp | "FedDateStamp" | None = None,
        end: pd.Timestamp | "FedDateStamp" | None = None,
    ) -> pd.Series:
        """
        Returns a list of federal paydays between the start and end dates.

        Parameters
        ----------
        start : start date for the range, defaults to reference_date if None.
        end : end date for the range, defaults to end_date if None.

        Returns
        -------
        List of paydays within the specified range.

        """
        return self.get_paydays_as_index(
            start=start or self.reference_date, end=end or self.end_date
        ).to_series(name="FedPayDay")
