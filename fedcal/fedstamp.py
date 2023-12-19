# fedcal fedstamp.py
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
fedstamp is one of fedcal's two main APIs, home to `FedStamp` a proxy
for pandas' `pd.Timestamp` with additional functionality for fedcal
data, with the goal of seamlessly building on `pd.Timestamp` and
integrating fedcal data into pandas analyses.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

import pandas as pd
from fedcal import _civpay, _date_attributes, _dept_status, _mil, constants, time_utils
from fedcal._meta import MagicDelegator

if TYPE_CHECKING:
    from fedcal._typing import (
        FedStampConvertibleTypes,
        StatusDictType,
        StatusTupleType,
    )
    from fedcal.constants import Dept
    from fedcal.depts import FedDepartment
    from fedcal.time_utils import YearMonthDay


class FedStamp(
    metaclass=MagicDelegator, delegate_to="pdtimestamp", delegate_class=pd.Timestamp
):

    """
        `FedStamp` extends `pd.Timestamp` for fedcal functionality.
        Supports all functionalities of pandas' pd.Timestamp
        objects, while adding specific features for the fedcal.

        Attributes
        ----------
        pdtimestamp : the `pd.Timestamp` object that forms the backbone of the
        instance. If a pdtimestamp is not provided at instantiations, the
        instance will default to the current date (datetime.now()). Note: we
        use pdtimestamp as an attribute name to avoid overwriting Timestamp.
        timestamp().

        _status_cache : A *private* lazy attribute that caches StatusDictType
        dictionary (Dict[Dept, FedDepartment]) from _dept_status.
        DepartmentState for the date for supplying status-related properties.
        Provided by _get_status_cache() and _set_status_cache() private
        methods.

        _holidays: A *private* lazy attribute that caches our FedHolidays
    instance once called.

        year_month_day
            returns the FedStamp as a YearMonthDay object.

        posix_day
            Returns the POSIX-day timestamp normalized to midnight.

        business_day
            Checks if the date is a business day.

        holiday
            Checks if the date is a federal holiday.

        proclamation_holiday
            Checks if the date was a proclaimed holiday (i.e. a one-off holiday
            proclaimed by executive order).

        possible_proclamation_holiday
            Guesses (I take no further ownership of the result) if the date is
            likely to be a proclaimed holiday.

        probable_military_passday
            Estimates if the date is likely a military pass day. Actual
            passdays vary across commands and locations, but this should
            return a result that's correct in the majority of cases.

        mil_payday
            Checks if the date is a military payday.

        civ_payday
            Checks if the date is a civilian payday.

        fiscal_quarter
            Retrieves the [Federal] fiscal quarter of the timestamp.

        fy
            Retrieves the [Federal] fiscal year of the timestamp.

        departments
            Retrieves the set of executive departments active on the date, as
            Dept enum objects.

        all_depts_status
            Retrieves the status of all departments as a dictionary on the
            date.

        all_depts_full_approps
            Checks if all departments are fully appropriated on the date,
            returning bool.

        all_depts_cr
            Checks if all departments were/are under a continuing resolution on
            the date, returning bool.

        all_depts_funded
            Checks if all departments were/are either fully appropriated or
            under a continuing resolution on the date, returning bool.

        all_unfunded
            Checks if all departments were/are unfunded on the date (either
            shutdown or otherwise gapped), returning bool.

        cr
            Checks if the date was during a continuing resolution (can include
            near-future dates since we know CR expiration dates at the time
            they are passed), returning bool.

        shutdown
            Checks if the date was/is during a shutdown, returning bool.

        approps_gap
            Checks if the date was/is during an appropriations gap, returning
            bool.

        funding_gap
            Check if the date was/is during a funding gap (appropriations gap
            or shutdown), returning bool.

        full_op_depts
            Retrieves departments that were fully operational (had a full-year
            appropriation) on the date, returning a dict.

        funded_depts
            Retrieves departments that were/are either fully operational or
            under a continuing resolution on the date, returning a dict.

        cr_depts
            Retrieves departments that were/are under a continuing resolution
            on the date, returning a dict. Current data are from FY99 to
            present. As discussed above for cr, these can include near future
            dates.

        gapped_depts
            Retrieves departments that were/are in an appropriations gap on the
            date but not shutdown, returning a dict. Notably, these are
            isolated to the 1970s and early 80s.

        shutdown_depts
            Retrieves departments that were/are shut down on the date. Data
            available from FY75 to present.

        unfunded_depts
            Retrieves departments that were/are unfunded on the date (either
            gapped or shutdown), returning a dict.

        Methods
        -------
        dict_to_dept_set(status_dict)
            Converts a StatusDictType dictionary to a set of Dept
            enum objects.

        dict_to_feddept_set(status_dict)
            Converts a StatusDictType dictionary to a set of FedDepartment

        dict_to_dept_list(status_dict)
            Utility method that converts a status dictionary (which most of the
            status-related property methods return) to a sorted list of
            Dept enum objects.

        dict_to_feddept_list(status_dict)
            Utility method that converts a status dictionary (which most of the
            status-related property methods return) to a sorted list of
            FedDepartment objects.

        get_departments_by_status(status_key)
            Retrieves departments matching a specific status, primary getter
            for status-related property methods.


        Notes
        -----
        *Private Methods*:
        _get_status_cache()
            Retrieves the status cache.

        _set_status_cache()
            Sets the status cache if not already set.

        _set_holidays()
            sets the _holidays attribute for the holiday, proclamation_holiday
            and possible_proclamation_holiday properties.


        TODO
        ----
        Implement custom __setattr__, __setstate_cython__, __setstate__,
        __delattr__, __init_subclass__, __hash__, __getstate__, __dir__,
        __reduce__, __reduce_ex__, reduce_cython__, (__slots__?)
    """

    def __init__(self, pdtimestamp: pd.Timestamp | None = None) -> None:
        """
        Initializes instance and sets pdtimestamp to today if no pdtimestamp
        provided at instantiation.

        Parameters
        ----------
        pdtimestamp
            pd.Timestamp object to set as the pdtimestamp. If not provided, the
            instance will default to the current date (datetime.now()).
            All core functionality of the class is built from this attribute.
        """
        if isinstance(pdtimestamp, pd.Timestamp):
            self.pdtimestamp = pdtimestamp
        elif pdtimestamp is not None:
            self.pdtimestamp = time_utils.to_timestamp(pdtimestamp)
        else:
            pd.Timestamp(ts_input=datetime.now())

        self._status_cache: "StatusDictType" | None = None
        self._holidays = None

    def __getattr__(self, name: str) -> Any:
        """
        Delegates attribute access to the pdtimestamp attribute. This lets
        FedStamp objects use any methods/attributes of Timestamp.

        Parameters
        ----------
        name : The name of the attribute to retrieve.

        Returns
        -------
        The value of the attribute.

        """

        if name in self.__class__.__dict__:
            return self.__class__.__dict__[name].__get__(self, self.__class__)

        if hasattr(self.pdtimestamp, name):
            return getattr(self.pdtimestamp, name)
        raise AttributeError(
            f"'{type(self).__name__}' object has no attribute '{name}'"
        )

    def __getattribute__(self, name: str) -> Any:
        """
        We set __getattribute__ manually to ensure it overrides
        any delegation to pd.Timestamp from our metaclass.
        (It shouldn't, I know, but I swear it was.)

        Parameters
        ----------
        name
            name of attribute

        Returns
        -------
            attribute if found.
        """
        return object.__getattribute__(self, name)

    # static utility methods
    @staticmethod
    def dict_to_dept_set(status_dict: "StatusDictType") -> set["Dept"]:
        """
        Convert a status dictionary to a set of executive departments.

        Parameters
        ----------
        status_dict : A dictionary mapping departments to their statuses from
        a dictionary structure (StatusDictType) supplied by most of
        FedStamp's status-related property methods.

        Returns
        -------
        A set representing the departments.

        """
        return set(status_dict.keys())

    @staticmethod
    def dict_to_feddept_set(status_dict: "StatusDictType") -> set["FedDepartment"]:
        """
        Convert a status dictionary to a set of FedDepartment objects.

        Parameters
        ----------
        status_dict
            A dictionary mapping departments to their statuses.

        Returns
        -------
        A sorted list representing FedDepartments.

        """
        return set((status_dict.values()))

    @staticmethod
    def dict_to_dept_list(
        status_dict: "StatusDictType",
    ) -> list["Dept"]:
        """
        Convert a status dictionary to a sorted list of executive departments.

        Parameters
        ----------
        status_dict
            A dictionary mapping departments to their statuses.

        Returns
        -------
        A sorted list representing the departments.

        """
        return sorted(list(status_dict.keys()))

    @staticmethod
    def dict_to_feddept_list(status_dict: "StatusDictType") -> list["FedDepartment"]:
        """
        Convert a status dictionary to a sorted list of FedDepartment objects.

        Parameters
        ----------
        status_dict
            A dictionary mapping departments to their FedDepartment objects.

        Returns
        -------
        A sorted list of FedDepartment objects.

        """
        return sorted(list(status_dict.values()))

    # caching methods
    def _get_status_cache(self) -> "StatusDictType":
        """
        Retrieve the current status cache.

        Returns
        -------
        The current status cache, mapping departments to their statuses.

        """
        if not _dept_status.DepartmentState.tree:
            _dept_status.DepartmentState()
            _dept_status.DepartmentState.get_state_tree()
        return _dept_status.DepartmentState.get_state(date=self.pdtimestamp)

    def _set_status_cache(self) -> None:
        """
        Set the status cache if not already set.
        """
        self._status_cache: "StatusDictType" = (
            self._status_cache or self._get_status_cache()
        )

    # getter methods for retrieving from cache by department and by status

    def get_departments_by_status(self, status_key: str) -> "StatusDictType":
        """
        Retrieve departments matching a specific status. This is the primary
        getter method for FedStamp's status-related property methods.

        Parameters
        ----------
        status_key
            The key representing the status to filter departments by.

        Returns
        -------
        A dictionary of departments and their status, filtered by the
        specified status key.

        """
        self._set_status_cache()
        cache: "StatusDictType" | None = self._status_cache

        if self.posix_day < constants.CR_DATA_CUTOFF_DATE and status_key in {
            "DEFAULT_STATUS",
            "CR_STATUS",
        }:
            status_key = "CR_DATA_CUTOFF_DEFAULT_STATUS"

        target_status: "StatusTupleType" | None = constants.STATUS_MAP.get(status_key)

        if cache is None or target_status is None:
            return {}

        return {
            dept: fed_dept
            for dept, fed_dept in cache.items()
            if fed_dept.to_status_tuple() == target_status
        }

    def get_feddepts_status(
        self, departments: list[Dept] | set[Dept]
    ) -> set[FedDepartment]:
        """
        Retrieve the status for a list of departments.

        Parameters
        ----------
        departments
            A list of departments to retrieve status for.

        Returns
        -------
        A set of FedDepartment objects representing the status of the
        specified departments.

        """
        self._set_status_cache()
        cache: "StatusDictType" | None = self._status_cache
        return {cache.get(dept) for dept in departments}

    # utility properties
    @property
    def year_month_day(self) -> "YearMonthDay":
        """
        Returns a YearMonthDay object for the date.

        Returns
        -------
        A YearMonthDay object representing the year, month, and day of the
        pdtimestamp.

        """
        return time_utils.YearMonthDay(
            year=self.pdtimestamp.year,
            month=self.pdtimestamp.month,
            day=self.pdtimestamp.day,
        )

    @property
    def posix_day(self) -> int:
        """
        Built for internal use in fedcal, variation of pd.Timestamp.timestamp()
        method, which remains available. Returns the number of days since
        the Unix epoch (1970-01-01 00:00:00 UTC) as an integer normalized to
        midnight (vice pandas' return of a float).

        Returns
        -------
        Integer POSIX-day timestamp in seconds.

        """
        return time_utils.pdtimestamp_to_posix_day(timestamp=self.pdtimestamp)

    # business day property
    @property
    def business_day(self) -> bool:
        """
        Checks if the date is a [Federal] business day.

        Returns
        -------
        True if the date is a business day, False otherwise.

        """
        busday = _date_attributes.FedBusDay()
        return busday.get_business_days(dates=self.pdtimestamp)

    # holiday properties
    def _set_holidays(self) -> None:
        """
        Sets the holidays attribute.
        """
        self._holidays = _date_attributes.FedHolidays()

    @property
    def holiday(self) -> bool:
        """
        Checks if the date is a federal holiday.

        Returns
        -------
        True if the date is a federal holiday, False otherwise.

        Notes
        -----
        This property is built on pandas' USFederalHolidayCalendar, but
        supplemented with historical holidays proclaimed by the President
        from FY74 to present (no known examples before that year).

        """
        holidays = self._holidays or self._set_holidays()

        return holidays.is_holiday(date=self.pdtimestamp)

    @property
    def proclamation_holiday(self) -> bool:
        """
        Checks if the date was an out-of-cycle holiday proclaimed by executive
        order. Data available from FY74 to present (no known instances before
        that time).

        Returns
        -------
        True if the pdtimestamp was a proclaimed holiday, False otherwise.

        """
        holidays = self._holidays or self._set_holidays()
        return holidays.was_proclaimed_holiday(date=self.pdtimestamp)

    @property
    def possible_proclamation_holiday(self) -> bool:
        """
        If given a future date, guesses if it may be a proclaimed holiday.

        Returns
        -------
        True if the pdtimestamp is a proclaimed holiday, False otherwise.

        Notes
        -----
        This method is probably very inaccurate, and uses a simple heuristic
        method based on the day of week Christmas and Christmas Eve fall
        (nearly all President-proclaimed holidays were for Christmas Eve).
        A quick analysis of historical trends suggests that these proclamations
        are highly variable and most closely correlated with the President or
        recency of the President issuing them than the date. For example,
        Presidents' Obama and Trump are responsible for 55% of of
        proclamations, and 73% occurred after the year 2000.

        """
        holidays = self._holidays or self._set_holidays()
        return holidays.guess_christmas_eve_proclamation_holiday(date=self.pdtimestamp)

    @property
    def probable_mil_passday(self) -> bool:
        """
        Estimates if the pdtimestamp is likely a military pass day.

        Returns
        -------
        True if the pdtimestamp is likely a military pass day, False otherwise.

        Notes
        -----
        Future versions of this method will add customization options for the
        heuristic used to determine these dates. Military passdays associated
        with holidays are highly variable across commands and locations based
        on a range of factors. However, the majority fall into a reasonably
        predictable pattern. Results from this method should be accurate for
        the majority of cases, and otherwise provide an approximation
        for predictable gaps in military person-power.

        """
        passday = _mil.ProbableMilitaryPassDay(date=self.pdtimestamp)
        return passday.is_likely_passday(date=self.pdtimestamp)

    # payday properties
    @property
    def mil_payday(self) -> bool:
        """
        Checks if the date is a military payday based on DFAS pay schedule.

        Returns
        -------
        True if the pdtimestamp is a military payday, False otherwise.

        """
        milpay = _mil.MilitaryPayDay(date=self.pdtimestamp)
        return milpay.is_military_payday(date=self.pdtimestamp)

    @property
    def civ_payday(self) -> bool:
        """
        Checks if the date is a civilian payday.

        Returns
        -------
        True if the date is a civilian payday, False otherwise.

        Notes
        -----
        Method is based on the Federal biweekly pay schedule, which applies to
        *nearly* all, but **not all**, Federal employee.

        """
        payday = _civpay.FedPayDay(end_date=self.pdtimestamp + pd.Timedelta(days=1))
        return payday.is_fed_payday(date=self.pdtimestamp)

    # FY/FQ properties
    @property
    def fiscal_quarter(self) -> int:
        """
        Retrieves the fiscal quarter of the date.

        Returns
        -------
        An integer representing the fiscal quarter (1-4).
        """
        fqs = _date_attributes.FedFiscalQuarter(date=self.pdtimestamp)
        return fqs.get_fiscal_quarter(date=self.pdtimestamp)

    @property
    def fy(self) -> int:
        """
        Retrieves the fiscal year of the date.

        Returns
        -------
        An integer representing the fiscal year (e.g. 23 for FY23).

        """
        fys = _date_attributes.FedFiscalYear(date=self.pdtimestamp)
        return fys.get_fiscal_year(date=self.pdtimestamp)

    # department and appropriations related status properties
    @property
    def departments(self) -> set["Dept"]:
        """
        Retrieves the set of executive departments active on the date.

        Returns
        -------
        A set of Dept enums.

        """
        return _dept_status.DepartmentState.get_depts_set_at_time(date=self.pdtimestamp)

    @property
    def all_depts_status(self) -> "StatusDictType":
        """
        Retrieves the status of all departments.

        Returns
        -------
        A StatusDictType mapping each department to its status on the date.

        """
        self._set_status_cache()
        return self._status_cache

    @property
    def all_depts_full_approps(self) -> bool:
        """
        Checks if all departments were/are fully appropriated on the date.

        Returns
        -------
        True if all departments are fully appropriated, False otherwise.

        """
        self._set_status_cache()
        return self.dict_to_dept_set(status_dict=self.full_op_depts) == self.departments

    @property
    def all_depts_cr(self) -> bool:
        """
        Checks if all departments are/were under a continuing resolution on
        the date.

        Returns
        -------
        True if all departments are under a continuing resolution, False
        otherwise.
        """
        self._set_status_cache()
        return (
            self.dict_to_dept_set(
                status_dict=self.get_departments_by_status(status_key="CR_STATUS")
            )
            == self.departments
        )

    @property
    def all_depts_funded(self) -> bool:
        """
        Checks if all departments were/are either fully appropriated or under
        a continuing resolution on the date.

        Returns
        -------
        True if all departments are either fully appropriated or under a
        continuing resolution, False otherwise.
        """
        self._set_status_cache()
        return (
            self.dict_to_dept_set(status_dict=self.full_or_cr_depts) == self.departments
        )

    @property
    def all_unfunded(self) -> bool:
        """
        Checks if all departments were/are unfunded (appropriations gap or
        shutdown) on the date.

        Returns
        -------
        True if all departments are unfunded, False otherwise.

        """
        self._set_status_cache()
        return (
            self.dict_to_dept_set(status_dict=self.unfunded_depts) == self.departments
        )

    @property
    def gov_cr(self) -> bool:
        """
        Checks if *any* departments were/are under a continuing resolution on
        the date.

        Returns
        -------
        True if the pdtimestamp is during a continuing resolution, False
        otherwise.


        """
        self._set_status_cache()
        return bool(self.cr_depts)

    @property
    def gov_shutdown(self) -> bool:
        """
        Checks if *any* departments were/are shutdown on the date.

        Returns
        -------
        True if the pdtimestamp is during a shutdown, False otherwise.

        """
        self._set_status_cache()
        return bool(self.shutdown_depts)

    @property
    def gov_approps_gap(self) -> bool:
        """
        Checks if the date was/is during an appropriations gap for *any*
        departments.

        Returns
        -------
        True if the date is during an appropriations gap, False otherwise.

        """
        self._set_status_cache()
        return bool(self.gapped_depts)

    @property
    def gov_unfunded(self) -> bool:
        """
        Checks if any departments were/are either subject to a gap in
        appropriations or shutdown on the date.

        Returns
        -------
        True if the date is during a funding gap.

        """
        self._set_status_cache()
        return bool(self.gapped_depts | self.shutdown_depts)

    @property
    def full_op_depts(self) -> "StatusDictType" | None:
        """
        Retrieves departments that were/are fully operational (i.e. had
        full-year appropriations) on the date.

        Returns
        -------
        A StatusDictType dictionary representing departments that are fully
        operational.

        """
        self._set_status_cache()
        return self.get_departments_by_status(status_key="DEFAULT_STATUS")

    @property
    def funded_depts(self) -> "StatusDictType" | None:
        """
        Retrieves departments that were/are either fully operational or under
        a continuing resolution on the date.

        Returns
        -------
        A StatusDictType dictionary representing departments that are either
        fully operational or under a continuing resolution.

        """
        return self.get_departments_by_status(
            status_key="DEFAULT_STATUS"
        ) | self.get_departments_by_status(status_key="CR_STATUS")

    @property
    def cr_depts(self) -> "StatusDictType" | None:
        """
        Retrieves departments that were/are under a continuing resolution on
        the date.

        Returns
        -------
        A StatusDictType dictionary representing departments that are under a
        continuing resolution.

        """
        return self.get_departments_by_status(status_key="CR_STATUS")

    @property
    def gapped_depts(self) -> "StatusDictType" | None:
        """
        Retrieves departments that were/are under an appropriations gap on the
        date (but not shutdown).

        Returns
        -------
        A StatusDictType dictionary representing departments that are in an
        appropriations gap.

        """
        return self.get_departments_by_status(status_key="GAP_STATUS")

    @property
    def shutdown_depts(self) -> "StatusDictType" | None:
        """
        Retrieves departments that were/are shut down for the date.

        Returns
        -------
        A StatusDictType dictionary representing departments that are shut
        down.

        """
        return self.get_departments_by_status(status_key="SHUTDOWN_STATUS")

    @property
    def unfunded_depts(self) -> "StatusDictType" | None:
        """
        Retrieves departments that were/are unfunded for the date
        (either under an appropriations gap or fully shutdown).

        Returns
        -------
        A StatusDictType dictionary representing departments that are unfunded.

        """
        return self.get_departments_by_status(
            status_key="SHUTDOWN_STATUS"
        ) | self.get_departments_by_status(status_key="GAP_STATUS")


def to_fedstamp(*date: "FedStampConvertibleTypes") -> FedStamp:
    """
    Converts a date to a FedStamp object.

    Parameters
    ----------
    date : FedStampConvertibleTypes
        The date to convert.

    Returns
    -------
    FedStamp
        The FedStamp object representing the date.

    """
    if count := len(date):
        if count in {1, 3}:
            date = tuple(date) if count == 3 else date
            return FedStamp(pdtimestamp=time_utils.to_timestamp(date))
    raise ValueError(
        f"invalid number of arguments: {count}. to_fedstamp() requires either 1 argument, or 3 integers as YYYY, M, D"
    )
