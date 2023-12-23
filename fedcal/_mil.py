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

import pandas as pd
import numpy as np
from attrs import define, field


from fedcal import _date_attributes, time_utils


@define(order=True, kw_only=True)
class MilitaryPayDay:

    """
    Handles the calculation and verification of military paydays.

    Attributes
    ----------
    dates: date or dates used for calculations.

    paydays: boolean or boolean Series indicating whether the date or dates
    are military paydays

    Methods
    -------
    get_mil_paydays(dates=None) -> bool | np.ndarray
        Determines if the given date/dates is a military payday.

    Notes
    -----
    *Private Methods*:

        _get_paydays_mask(dates)
            helper method for `get_mil_paydays` that generates a boolean mask
            to use for evaluating the dates for paydays
    """

    dates: pd.Timestamp | pd.DatetimeIndex | pd.Series = field(default=None)
    paydays = field(default=None, init=False)

    def __attrs_post_init__(self) -> None:
        """
        Initializes the instance and sets attributes.
        """
        self.dates = time_utils.ensure_datetimeindex(dates=self.dates)

        self.paydays: pd.Series | bool | None = self.get_mil_paydays(dates=self.dates)

    def get_mil_paydays(self, dates: pd.DatetimeIndex | pd.Series = None) -> pd.Series:
        """
        Determines if the given date is a military payday.

        Parameters
        ----------
        dates : date to check, defaults to the date attribute if None.

        Returns
        -------
        Boolean array of dates reflecting military paydays for the range.
        """

        dates = pd.DatetimeIndex(data=self.dates if dates is None else dates)
        bizday_instance = _date_attributes.FedBusDay()

        first_or_fifteenth_mask: pd.Series = pd.Series(
            data=(dates.day.isin(values=[1, 15])), index=dates, dtype=bool
        )
        business_days_mask = pd.Series(
            dates.isin(bizday_instance.get_business_days(dates=dates)),
            index=dates,
            dtype=bool,
        )

        payday_mask: pd.Series[bool] = first_or_fifteenth_mask & business_days_mask

        non_biz_1st_15th = dates[first_or_fifteenth_mask & ~business_days_mask]
        for non_biz_date in non_biz_1st_15th:
            return self._extracted_from_get_mil_paydays_30(
                non_biz_date, bizday_instance, payday_mask
            )

    # TODO Rename this here and in `get_mil_paydays`
    def _extracted_from_get_mil_paydays_30(self, non_biz_date, bizday_instance, payday_mask):
        prev_days = pd.date_range(start=non_biz_date - pd.Timedelta(days=3), end=non_biz_date - pd.Timedelta(days=1))
        prev_business_days = bizday_instance.get_business_days(dates=prev_days)
        prev_business_day_mask = pd.Series(index=prev_days, data=prev_business_days)

        recent_biz_day = prev_days[prev_business_day_mask].max()
        payday_mask.at[recent_biz_day] = True

        return payday_mask


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
    get_probable_passdays(dates=None) -> np.ndarray
        Leverages boolean masking operations to identify probable
        military passdays across a DatetimeIndex.

    is_likely_passday(date=None) -> bool
        Evaluates whether the given date is likely a military pass day.

    Notes
    -----
    While technically military passes extend through non-business days, passes
    falling on non-business days don't meaningfully affect available personnel.
    Since our goal is enabling useful data analysis, we do not account for
    passes falling on non-business days.

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
        _get_base_masks(dates) -> dict
            a helper method for get_probable_passdays that generates a
            dictionary of boolean masks to use for evaluation.
    """

    dates: pd.DatetimeIndex | pd.Series | pd.Timestamp | None = field(default=None)

    passdays: pd.DatetimeIndex | pd.Series | None = field(default=None, init=False)

    def __attrs_post_init__(self) -> None:
        """
        Complete initialization of the instance and sets attributes

        Raises
        ------
        AttributeError
            if neither date nor dates are provided
        """
        self.dates = time_utils.ensure_datetimeindex(dates=self.dates)
        self.passdays = self.get_probable_passdays(dates=self.dates)

    def get_probable_passdays(
        self, dates: pd.DatetimeIndex | pd.Series
    ) -> pd.Series[bool]:
        """
        Determines the likely passdays for the given dates.

        Parameters
        ----------
        dates : dates for checking against passday masks

        Returns
        -------
        Boolean pd.Series indicating whether the dates in the range are
        probable passdays.

        """
        if dates is None:
            dates = self.dates
        else:
            dates = (
                time_utils.to_datetimeindex(dates)
                if isinstance(dates, pd.Series)
                else dates
            )
        masks: pd.DataFrame = self._get_base_masks(dates=dates)
        fri_mask = dates.isin(
            dates[masks["monday_holidays"]] - pd.DateOffset(days=3)
        ) | dates.isin(dates[masks["thursday_holidays"]] + pd.DateOffset(days=1))

        mon_mask = dates.isin(
            dates[masks["friday_holidays"]] + pd.DateOffset(days=3)
        ) | dates.isin(dates[masks["tuesday_holidays"]] - pd.DateOffset(days=1))
        thurs_mask = dates.isin(
            dates[masks["wednesday_holidays"]] + pd.DateOffset(days=1)
        )

        return (fri_mask | mon_mask | thurs_mask) & masks["eligible_days"]

    @staticmethod
    def _get_base_masks(
        dates: pd.DatetimeIndex,
    ) -> pd.DataFrame:
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

        bizday_instance = _date_attributes.FedBusDay()
        holidays_instance = _date_attributes.FedHolidays()

        # Initialize the DataFrame
        mask_frame = pd.DataFrame(index=dates)

        mask_frame["dates"] = dates.to_series(index=dates)
        mask_frame["holidays"] = dates.isin(values=holidays_instance.holidays)
        mask_frame["holiday_days_of_week"] = dates.dayofweek
        mask_frame["business_days"] = dates.isin(
            values=bizday_instance.get_business_days(dates=dates)
        )

        for day, dow in zip(
            ["monday", "tuesday", "wednesday", "thursday", "friday"], range(5)
        ):
            mask_frame[f"{day}_holidays"] = (
                mask_frame["holiday_days_of_week"] == dow
            ) & mask_frame["holidays"]

        mask_frame["eligible_days"] = (
            mask_frame["business_days"] & ~mask_frame["holidays"]
        )

        return mask_frame
