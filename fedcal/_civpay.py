# fedcal _civpay.py
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
fedcal's _civpay module is not intended for public use, though it certainly
could be. We want to keep the interface simple, so we expose all functionality
through `FedIndex` and `FedStamp`.

`FedPayDay` calculates and provides federal civilian biweekly paydays
and outputs them in a variety of formats.
"""

from __future__ import annotations

import pandas as pd
from attrs import define, field

from fedcal import constants, time_utils


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

    is_fed_payday(date=None)
        Checks if a given date is a federal payday.

    get_paydays_as_index(start=None, end=None)
        Returns a DatetimeIndex of paydays between the start and end dates.

    get_paydays_as_list(start=None, end=None)
        Returns a list of federal paydays between the start and end dates.

    get_paydays_as_series(start=None, end=None)
        Returns a pandas pd.Series of federal paydays between the start and end
        dates.

    Notes
    -----
    *Private method*:
        _generate_paydays(end_date)
            Generates federal paydays between the reference date and the
            specified end date.

    """

    reference_date: pd.Timestamp = field(
        default=constants.FEDPAYDAY_REFERENCE_DATE,
        converter=time_utils.to_timestamp,
    )
    end_date: pd.Timestamp = field(
        default=pd.Timestamp(year=2040, month=9, day=30),
        converter=time_utils.to_timestamp,
    )

    paydays: pd.DatetimeIndex = field(init=False)

    def __attrs_post_init__(self) -> None:
        self.paydays: pd.DatetimeIndex = self._generate_paydays()

    def _generate_paydays(
        self, end_date: pd.Timestamp | None = None
    ) -> pd.DatetimeIndex:
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
        end_date: pd.Timestamp = end_date or self.end_date
        if end_date > self.reference_date:
            return pd.date_range(start=self.reference_date, end=end_date, freq="2W-FRI")
        raise ValueError("fedcal only supports dates after 1970-1-1.")

    def is_fed_payday(self, date: pd.Timestamp | None = None) -> bool:
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

        return date in self.paydays

    def get_paydays_as_index(
        self,
        start: pd.Timestamp | None = None,
        end: pd.Timestamp | None = None,
    ) -> pd.DatetimeIndex:
        """
        Returns a DatetimeIndex of paydays between the start and end dates.

        Parameters
        ----------
        start : start date for the range, defaults to reference_date if None.
        end : end date for the range, defaults to end_date if None.

        Returns
        -------
        DatetimeIndex of paydays within the specified range.

        """
        if end and ((self.paydays.ceil(freq="D") < end) or (not self.paydays)):
            self.paydays = self._generate_paydays(end_date=end)
        return self.paydays[
            (self.paydays >= start or self.reference_date)
            & (self.paydays <= end or self.end_date)
        ]

    def get_paydays_as_list(
        self,
        start: pd.Timestamp | None = None,
        end: pd.Timestamp | None = None,
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
        start: pd.Timestamp | None = None,
        end: pd.Timestamp | None = None,
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
