from __future__ import annotations

from datetime import date, datetime
from typing import (
    TYPE_CHECKING,
    List,
    Self,
)
from pandas import Timestamp
from ._dept_status import DepartmentState
from ._civpay import FedPayDay
from .constants import (
    CR_DATA_CUTOFF_DATE,
    EXECUTIVE_DEPARTMENT,
    STATUS_MAP,
)
from ._date_attributes import FedBusDay, FedFiscalQuarter, FedFiscalYear, FedHolidays
from ._mil import MilitaryPayDay, ProbableMilitaryPassDay
from .time_utils import YearMonthDay, _pydate_to_posix, to_datestamp

if TYPE_CHECKING:
    from ._dept_status import FedDepartment
    from ._typing import (
        StatusDictType,
        StatusTupleType,
    )


class FedDateStamp(Timestamp):

    """
    A child class of pandas Timestamp, extending functionality for
    fedcal. Supports all functionalities of pandas' Timestamp
    objects, while adding specific features for the fedcal.

    Attributes
    ----------
    No attributes at initialization except those inherited from pandas'
    Timestamp.

    _status_cache : A *private* lazy attribute that caches StatusDictType
    dictionary (Dict[EXECUTIVE_DEPARTMENT, FedDepartment]) from _dept_status.
    DepartmentState for the date for supplying status-related properties.
    Provided by _get_status_cache() and _set_status_cache() private methods.

    year_month_day
        returns the FedDateStamp as a YearMonthDay object.

    fedtimestamp
        Returns the POSIX timestamp normalized to midnight.

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
        Estimates if the date is likely a military pass day. Actual passdays
        vary across commands and locations, but this should return a result
        that's correct in the majority of cases.

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
        EXECUTIVE_DEPARTMENT enum objects.

    all_depts_status
        Retrieves the status of all departments as a dictionary on the date.

    all_depts_full_approps
        Checks if all departments are fully appropriated on the date,
        returning bool.

    all_depts_cr
        Checks if all departments were/are under a continuing resolution on
        the date, returning bool.

    all_depts_cr_or_full_approps
        Checks if all departments were/are either fully appropriated or under
        a continuing resolution on the date, returning bool.

    all_unfunded
        Checks if all departments were/are unfunded on the date (either
        shutdown or otherwise gapped), returning bool.

    cr
        Checks if the date was during a continuing resolution (can include
        near-future dates since we know CR expiration dates at the time they
        are passed), returning bool.

    shutdown
        Checks if the date was/is during a shutdown, returning bool.

    approps_gap
        Checks if the date was/is during an appropriations gap, returning bool.

    funding_gap
        Check if the date was/is during a funding gap (appropriations gap or
        shutdown), returning bool.

    full_op_depts
        Retrieves departments that were fully operational (had a full-year
        appropriation) on the date, returning a dict.

    full_or_cr_depts
        Retrieves departments that were/are either fully operational or under
        a continuing resolution on the date, returning a dict.

    cr_depts
        Retrieves departments that were/are under a continuing resolution on
        the date, returning a dict. Current data are from FY99 to present. As
        discussed above for cr, these can include near future dates.

    gapped_depts
        Retrieves departments that were/are in an appropriations gap on the
        date but not shutdown, returning a dict. Notably, these are isolated
        to the 1970s and early 80s.

    shutdown_depts
        Retrieves departments that were/are shut down on the date. Data
        available from FY75 to present.

    unfunded_depts
        Retrieves departments that were/are unfunded on the date (either
        gapped or shutdown), returning a dict.

    Methods
    -------
    dict_to_dept_set(status_dict)
        Converts a StatusDictType dictionary to a set of EXECUTIVE_DEPARTMENT
        enum objects.

    dict_to_feddept_set(status_dict)
        Converts a StatusDictType dictionary to a set of FedDepartment

    dict_to_dept_list(status_dict)
        Utility method that converts a status dictionary (which most of the
        status-related property methods return) to a sorted list of
        EXECUTIVE_DEPARTMENT enum objects.

    dict_to_feddept_list(status_dict)
        Utility method that converts a status dictionary (which most of the
        status-related property methods return) to a sorted list of
        FedDepartment objects.

    get_departments_by_status(status_key)
        Retrieves departments matching a specific status, primary getter for
        status-related property methods.


    Notes
    -----
    *Private Methods*:
    _get_status_cache()
        Retrieves the status cache.

    _set_status_cache()
        Sets the status cache if not already set.
    """

    def __new__(cls, ts_input=None, *args, **kwargs) -> Self:
        """
        We ensure new instances mirror Timestamp behavior and pass any args/
        kwargs. Like Timestamp, if you don't pass a date, FedDateStamp will
        initialize for today.
        """
        if ts_input is None:
            ts_input: Timestamp = datetime.now()

        return super().__new__(cls, ts_input, *args, **kwargs)

    # static utility methods
    @staticmethod
    def dict_to_dept_set(status_dict: "StatusDictType") -> set["EXECUTIVE_DEPARTMENT"]:
        """
        Convert a status dictionary to a set of executive departments.

        Parameters
        ----------
        status_dict : A dictionary mapping departments to their statuses from
        a dictionary structure (StatusDictType) supplied by most of
        FedDateStamp's status-related property methods.

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
        status_dic
            A dictionary mapping departments to their statuses.

        Returns
        -------
        A sorted list representing FedDepartments.

        """
        return set((status_dict.values()))

    @staticmethod
    def dict_to_dept_list(
        status_dict: "StatusDictType",
    ) -> List["EXECUTIVE_DEPARTMENT"]:
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
        self.state = DepartmentState()
        return DepartmentState.get_state(date=self)

    def _set_status_cache(self) -> None:
        """
        Set the status cache if not already set.
        """
        self.status_cache: "StatusDictType" = (
            self.status_cache or self._get_status_cache()
        )

    # getter methods for retrieving from cache by department and by status

    def get_departments_by_status(self, status_key: str) -> "StatusDictType":
        """
        Retrieve departments matching a specific status. This is the primary
        getter method for FedDateStamp's status-related property methods.

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
        cache: "StatusDictType" | None = self.status_cache

        if self.timestamp() < CR_DATA_CUTOFF_DATE and status_key in {
            "DEFAULT_STATUS",
            "CR_STATUS",
        }:
            status_key = "CR_DATA_CUTOFF_DEFAULT_STATUS"

        target_status: "StatusTupleType" | None = STATUS_MAP.get(status_key)

        if cache is None or target_status is None:
            return {}

        return {
            dept: fed_dept
            for dept, fed_dept in cache.items()
            if fed_dept.to_status_tuple() == target_status
        }

    # utility properties
    @property
    def year_month_day(self) -> YearMonthDay:
        """
        Returns a YearMonthDay object for the date.

        Returns
        -------
        A YearMonthDay object representing the year, month, and day of the
        timestamp.

        """
        return YearMonthDay(year=self.year, month=self.month, day=self.day)

    @property
    def fedtimestamp(self) -> int:
        """
        Built for internal use in fedcal, variation of Timestamp.timestamp()
        method, which remains available. Returns the number of seconds since
        the Unix epoch (1970-01-01 00:00:00 UTC) as an integer normalized to
        midnight (vice pandas' return of a float).

        Returns
        -------
        Integer POSIX timestamp in seconds.

        """
        date_obj: date = date(year=self.year, month=self.month, day=self.day)
        return _pydate_to_posix(pydate=date_obj)

    # business day property
    @property
    def business_day(self) -> bool:
        """
        Checks if the date is a [Federal] business day.

        Returns
        -------
        True if the date is a business day, False otherwise.

        """
        return FedBusDay.is_bday(date=self)

    # holiday properties
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
        return FedHolidays.is_holiday(date=self)

    @property
    def proclamation_holiday(self) -> bool:
        """
        Checks if the date was an out-of-cycle holiday proclaimed by executive
        order. Data available from FY74 to present (no known instances before
        that time).

        Returns
        -------
        True if the timestamp was a proclaimed holiday, False otherwise.

        """
        return FedHolidays.was_proclaimed_holiday(date=self)

    @property
    def possible_proclamation_holiday(self) -> bool:
        """
        If given a future date, guesses if it may be a proclaimed holiday.

        Returns
        -------
        True if the timestamp is a proclaimed holiday, False otherwise.

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
        return FedHolidays.guess_christmas_eve_proclamation_holiday(date=self)

    @property
    def probable_mil_passday(self) -> bool:
        """
        Estimates if the timestamp is likely a military pass day.

        Returns
        -------
        True if the timestamp is likely a military pass day, False otherwise.

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
        return ProbableMilitaryPassDay.is_likely_passday(date=self)

    # payday properties
    @property
    def mil_payday(self) -> bool:
        """
        Checks if the date is a military payday based on DFAS pay schedule.

        Returns
        -------
        True if the timestamp is a military payday, False otherwise.

        """
        return MilitaryPayDay.is_military_payday(date=self)

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
        return FedPayDay.is_fed_payday(date=self)

    # FY/FQ properties
    @property
    def fiscal_quarter(self) -> int:
        """
        Retrieves the fiscal quarter of the date.

        Returns
        -------
        An integer representing the fiscal quarter (1-4).
        """
        return FedFiscalQuarter.get_fiscal_quarter(date=self)

    @property
    def fy(self) -> int:
        """
        Retrieves the fiscal year of the date.

        Returns
        -------
        An integer representing the fiscal year (e.g. 23 for FY23).

        """
        return FedFiscalYear.get_fiscal_year(date=self)

    # department and appropriations related status properties
    @property
    def departments(self) -> set["EXECUTIVE_DEPARTMENT"]:
        """
        Retrieves the set of executive departments active on the date.

        Returns
        -------
        A set of EXECUTIVE_DEPARTMENT enums.

        """
        return DepartmentState.get_executive_departments_set_at_time(date=self)

    @property
    def all_depts_status(self) -> "StatusDictType":
        """
        Retrieves the status of all departments.

        Returns
        -------
        A StatusDictType mapping each department to its status on the date.

        """
        self._set_status_cache()
        return self.status_cache

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
    def all_depts_cr_or_full_approps(self) -> bool:
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
        True if the timestamp is during a continuing resolution, False
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
        True if the timestamp is during a shutdown, False otherwise.

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
    def gov_funding_gap(self) -> bool:
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
    def full_or_cr_depts(self) -> "StatusDictType" | None:
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


@to_datestamp.register(cls=FedDateStamp)
def _return_datestamp(date_input: FedDateStamp) -> FedDateStamp:
    """
    We handle stray non-conversions by returning them.
    This function and its companion in feddateindex.py are lonely refugees
    from the parentf unction in .time_utils, here to avoid circular import
    issues until we can implement a more permanent fix.
    """
    return date_input
