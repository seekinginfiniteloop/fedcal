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


def _npmask_to_series_mask(
    dates: pd.DatetimeIndex, mask: np.ndarray[bool] | bool
) -> pd.Series[bool]:
    """
    Converts a boolean numpy array to a boolean pandas series.
    Utility for cutting repetition. Pandas throws a deprecation
    warning when trying to directly mask a pandas object
    with an np.ndarray, so we cast them to Series for consistency.

    Parameters
    ----------
    dates : DatetimeIndex to use for the boolean series.
    mask : numpy boolean array.

    Returns
    -------
    Boolean pandas series.
    """
    return pd.Series(data=mask, index=dates, dtype=bool)


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
        _timestamp = False
        if isinstance(self.dates, pd.Series):
            self.dates = time_utils.to_datetimeindex(self.dates)
        if isinstance(self.dates, pd.Timestamp):
            self.dates = pd.DatetimeIndex([self.dates])
            _timestamp = True

        self.paydays: pd.Series | bool | None = (
            self.get_mil_paydays(dates=self.dates).iloc[0]
            if _timestamp
            else self.get_mil_paydays(dates=self.dates)
        )

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

        if dates is None:
            dates = (
                self.dates
                if isinstance(self.dates, (pd.DatetimeIndex, pd.Series))
                else None
            )
        dates = pd.DatetimeIndex(dates) if isinstance(dates, pd.Series) else dates

        bizday_instance = _date_attributes.FedBusDay()

        first_or_fifteenth_mask: pd.Series[bool] = _npmask_to_series_mask(
            dates=dates, mask=dates.day.isin([1, 15])
        )

        business_days_mask: pd.Series[bool] = _npmask_to_series_mask(
            dates=dates, mask=bizday_instance.get_business_days(dates=dates)
        )

        payday_mask: pd.Series[bool] = _npmask_to_series_mask(dates=dates, mask=False)
        payday_mask[first_or_fifteenth_mask & business_days_mask] = True

        non_biz_1st_15th_indices = np.where(
            dates.day.isin([1, 15]) & ~business_days_mask
        )[0]

        # Check up to 3 days before each non-business 1st or 15th
        for idx in non_biz_1st_15th_indices:
            for shift in range(1, 4):
                shifted_idx = idx - shift
                if shifted_idx >= 0 and business_days_mask.iloc[shifted_idx]:
                    payday_mask.iloc[shifted_idx] = True
                    break

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
            a helper method for get_probable_passdays that generates a dictionary of boolean masks to use for evaluation.
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
        _timestamp = False
        if isinstance(self.dates, pd.Series):
            self.dates = time_utils.to_datetimeindex(self.dates)
        if isinstance(self.dates, pd.Timestamp):
            self.dates = pd.DatetimeIndex([self.dates])
            _timestamp = True

        self.passdays: pd.Series | bool = (
            self.get_probable_passdays(dates=self.dates).iloc[0]
            if _timestamp
            else self.get_probable_passdays(dates=self.dates)
        )

    def get_probable_passdays(self, dates: pd.DatetimeIndex | pd.Series) -> pd.Series:
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
        dates = (
            time_utils.to_datetimeindex(dates)
            if isinstance(dates, pd.Series)
            else dates
        )
        date_series = pd.Series(data=dates, index=dates)

        mask_dict: dict[str, pd.Series[bool] | pd.Index[int]] = self._get_base_masks(
            dates=dates
        )
        passdays_mask: pd.Series[bool] = _npmask_to_series_mask(dates=dates, mask=False)

        monday_holidays = dates[mask_dict["hol_day_idx"] == 0]
        monday_offset = monday_holidays - pd.Timedelta(value=3, unit='days')
        passdays_mask.loc[monday_offset] = True


        tuesday_holidays = dates[mask_dict["hol_day_idx"] == 1]
        tuesday_offset = tuesday_holidays - pd.Timedelta(value=1, unit='days')
        passdays_mask.loc[tuesday_offset] = True

        wednesday_holidays = dates[mask_dict["hol_day_idx"] == 2]
        wednesday_offset = wednesday_holidays + pd.Timedelta(value=1, unit='days')
        passdays_mask.loc[wednesday_offset] = True

        thursday_holidays = dates[mask_dict["hol_day_idx"] == 3]
        thursday_offset = thursday_holidays + pd.Timedelta(value=1, unit='days')
        passdays_mask.loc[thursday_offset] = True
        friday_holidays = dates[mask_dict["hol_day_idx"] == 4]
        friday_offset = friday_holidays + pd.Timedelta(value=3, unit='days')
        passdays_mask.loc[friday_offset] = True

        passdays_mask |= mask_dict["christmas_eve"] & mask_dict["eligible_days"]
        return dates[passdays_mask]

    @staticmethod
    def _get_base_masks(
        dates: pd.DatetimeIndex,
    ) -> dict[str, pd.Series[bool] | pd.Index[int]]:
        """
        Retrieves the base masks for evaluating a DatetimeIndex for possible passdays. A helper method to `get_probable_passdays`.

        Parameters
        ----------
        dates : dates to retrieve masks for.

        Returns
        -------
        Dictionary of boolean masks.
            - holidays : boolean array indicating whether the date is a holiday.
            - businessdays : boolean array indicating whether the date is a business day.
            - christmas_eve : boolean array indicating whether the date is Christmas Eve.
            - hol_day_idx : integer array indicating the day of the week of the holiday.
            - dates_day_idx : integer array indicating the day of the week of the date.
            - eligible_days : boolean array indicating whether the date is a weekday.
            - friday_holidays : boolean array indicating whether the date is a Friday holiday.
            - monday_holidays : boolean array indicating whether the date is a Monday holiday.
            - thursday_holidays : boolean array indicating whether the date is a Thursday holiday.
        """
        bizday_instance = _date_attributes.FedBusDay()
        holidays_instance = _date_attributes.FedHolidays()
        date_series = pd.Series(data=dates, index=dates)
        holidays_mask: pd.Series[bool] = date_series.isin(
            values=holidays_instance.holidays
        )

        business_days_mask: pd.Series[bool] = date_series.isin(
            values=bizday_instance.get_business_days(dates=dates)
        )

        christmas_eve_mask: pd.Series = pd.Series(
            data=(dates.month == 12) & (dates.day == 24), index=dates, dtype=bool
        )

        holiday_days_of_week: pd.Index[int] = dates[holidays_mask].dayofweek
        print(holiday_days_of_week)
        friday_holidays_mask: pd.Series[bool] = _npmask_to_series_mask(
            dates=dates, mask=np.where(holiday_days_of_week == 4, True, False)
        )
        monday_holidays_mask: pd.Series[bool] = _npmask_to_series_mask(
            dates=dates, mask=np.where(holiday_days_of_week == 0, True, False)
        )
        wednesday_holidays_mask: pd.Series[bool] = _npmask_to_series_mask(
            dates=dates, mask=np.where(holiday_days_of_week == 2, True, False)
        )

        dates_weekdays: pd.Index = dates.dayofweek

        eligible_days_mask: pd.Series[bool] = (
            _npmask_to_series_mask(
                dates=dates, mask=(business_days_mask & dates_weekdays <= 4)
            ),
        )

        return {
            "holidays": holidays_mask,
            "businessdays": business_days_mask,
            "christmas_eve": christmas_eve_mask,
            "hol_day_idx": holiday_days_of_week,
            "dates_day_idx": dates_weekdays,
            "eligible_days": eligible_days_mask,
            "friday_holidays": friday_holidays_mask,
            "monday_holidays": monday_holidays_mask,
            "wednesday_holidays": wednesday_holidays_mask,
        }
