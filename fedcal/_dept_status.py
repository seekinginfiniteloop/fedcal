from __future__ import annotations

from itertools import product
from typing import TYPE_CHECKING

from attrs import define, field
from intervaltree import IntervalTree

from fedcal import constants, time_utils
from fedcal.depts import FedDepartment

# we import Tree from fedcal._tree inside DepartmentState to keep it offline
# until needed

if TYPE_CHECKING:
    import pandas as pd
    from fedcal._typing import (
        FedStampConvertibleTypes,
        StatusDictType,
        StatusGeneratorType,
        StatusMapType,
        StatusPoolType,
        StatusTupleType,
    )
    from fedcal.constants import Dept


@define(order=True)
class DepartmentStatus:

    """
    Manages the statuses of various departments, using a flyweight pattern
    for efficiency.

    Attributes
    ----------
    departments : Dict[Dept, FedDepartment]
        A dictionary mapping each executive department to its current
        FedDepartment instance.
    status_map : StatusMapType
        Maps status keys to corresponding tuples of funding and operational
        statuses, from constants.py STATUS_MAP.
    _status_pool : StatusPoolType
        *class attribute*: A pool of FedDepartment instances for reuse,
        ensuring only one instance per status combination.

    Methods
    -------
    get_status_pool()
        Retrieves the singleton status pool.
    set_department_status(department, status_key)
        Sets the status of a given department based on a status key.
    get_department_status(department)
        Retrieves the current status of a given department.

    """

    status_map: "StatusMapType" = field(default=constants.STATUS_MAP)
    _status_pool: "StatusPoolType" | None = None

    def __attrs_post_init__(self) -> None:
        self._status_pool: StatusPoolType = self.get_status_pool()

    @classmethod
    def get_status_pool(cls) -> StatusPoolType:
        """
        A singleton flyweight method. Retrieves the singleton status pool,
        initializing it if needed. This framework ensures our status pool
        only stores a department's possible status once

        Attributes
        ----------
        status_pool : The singleton status pool containing FedDepartment
        instances for each status combination.
        """
        if cls._status_pool is None:
            cls._status_pool = cls._initialize_status_pool()
        return cls._status_pool

    @classmethod
    def _initialize_status_pool(cls) -> StatusPoolType:
        """
        Initializes the status pool class attribute with FedDepartment
        instances.

        This private method populates the _status_pool class attribute with
        FedDepartment instances, each corresponding to a unique combination of
        executive department and status key.

        The method is called internally and ensures that the status pool is
        populated correctly, adhering to the flyweight pattern for efficient
        memory usage.
        """

        _status_pool: "StatusPoolType" = {
            (dept, status_key): FedDepartment(
                name=dept,
                funding_status=cls.status_map[status_key][0],
                operational_status=cls.status_map[status_key][1],
            )
            for dept, status_key in product(constants.DEPTS_SET, cls.status_map.keys())
            if dept != constants.Dept.DHS
            and status_key == "CR_DATA_CUTOFF_DEFAULT_STATUS"
        }
        return _status_pool


@define(order=True)
class DepartmentState:

    """
    Represents the state of departments at different times, based on an
    interval tree structure.

    Attributes
    ----------
    tree : An interval tree representing changes in department statuses over
        time.
    status_pool : DepartmentStatus instance implementing a flyweight pattern
        for storing possible department statuses.
    max_default_date : Cutoff date for future status data, set as the greater
        of the maximum interval in tree or today.

    Methods
    -------
    get_state(date)
        Retrieves the status of all departments for a specific date, returning
        a dictionary of statuses.
    get_state_for_range_generator(start_date, end_date)
        Returns a generator of statuses for a given date range.

    Notes
    -----
    *Private Methods*:
    _initialize_tree() :
    _process_interval(interval, last_known_status, start_posix, end_posix)
        Processes a given interval, updating department statuses as needed.
        Helper function for get_state_for_range_generator().

    """

    tree: IntervalTree = field(init=False)
    status_pool: "StatusPoolType" = field(init=False)
    max_default_date: int = field(init=False)

    def __attrs_post_init__(self) -> None:
        """
        Initializes the DepartmentState instance, setting up the interval tree
        and status pool.

        This method is automatically called after the object is initialized.
        It sets up the interval tree that tracks changes in department
        statuses over time and initializes the status pool for efficient
        status management.
        """
        self.tree: IntervalTree = self._initialize_tree()
        statuses = DepartmentStatus()
        self.status_pool: "StatusPoolType" = statuses._status_pool

        self.max_default_date: int = self._set_max_default()

    def _initialize_tree(self) -> IntervalTree:
        """
        Initializes and returns an IntervalTree instance.

        This method creates an IntervalTree, either by reusing an existing
        tree if available or by generating a new one. This tree is used to
        store intervals representing periods of status changes for departments.

        Returns
        -------
        An interval tree representing department status changes over time.

        """
        from fedcal import _tree  # we wait to load _tree until needed for speed

        interval_tree: IntervalTree = _tree.Tree()
        return interval_tree.tree.copy()

    @staticmethod
    def get_executive_departments_set_at_time(
        date: "pd.Timestamp" | int,
    ) -> set["Dept"]:
        if not isinstance(date, int):
            date = time_utils.pdtimestamp_to_posix_seconds(
                timestamp=time_utils.to_timestamp(date)
            )
        if date >= constants.DHS_FORMED:
            return constants.DEPTS_SET
        else:
            return constants.DEPTS_SET.difference({constants.Dept.DHS})

    def _get_tree_ceiling(self) -> int:
        """
        Get the rightmost date of the tree.

        Returns
        -------
        The rightmost date of the tree (the latest date in the tree).

        """
        return self.tree.end() if self.tree else 0

    def _set_max_default(self) -> int:
        """
        Set the maximum default date.

        Returns
        -------
        The maximum default date, any date after will be handled with
        FUTURE_STATUS.

        """
        tree_ceiling: int = self.tree.end() if self.tree else 0
        today: int = time_utils.get_today_in_posix()
        return max(tree_ceiling, today)

    def get_state(
        self, date: "pd.Timestamp" | "FedStampConvertibleTypes"
    ) -> "StatusDictType":
        """
        Retrieves the status of all departments for a specific date.

        This method checks the interval tree for any intervals that include
        the specified date and determines the status of each department at
        that point in time.

        We also handle special cases like the formation of DHS and the
        current data cutoff for continuing resolutions (FY99)

        Parameters
        ----------
        date : The specific date for which the department statuses are to be
        retrieved.

        Returns
        -------
        A dictionary mapping each department to its status on the specified
        date.

        """
        posix_date: int = time_utils.pdtimestamp_to_posix_seconds(
            timestamp=time_utils.to_timestamp(date)
        )

        executive_department_set: set[
            "Dept"
        ] = self.get_executive_departments_set_at_time(date=date)

        status_dict: "StatusDictType" = {
            dept: self.status_pool[
                (
                    dept,
                    "CR_DATA_CUTOFF_DEFAULT_STATUS"
                    if posix_date < constants.CR_DATA_CUTOFF_DATE
                    else "FUTURE_STATUS"
                    if posix_date > self.max_default_date
                    else "DEFAULT_STATUS",
                )
            ]
            for dept in executive_department_set
        }
        for interval in self.tree.at(p=posix_date):
            for department in interval.data[0]:
                status_key = interval.data[1]
                status_dict[department] = self.status_pool[(department, status_key)]

        return status_dict

    def get_state_for_range_generator(
        self,
        start: "pd.Timestamp",
        end: "pd.Timestamp",
    ) -> "StatusGeneratorType":
        """
        Yields a generator of statuses for a given date range.

        This method iterates through the interval tree for the specified date
        range and determines the status of each department at each point in
        time. We also handle special cases like the formation of DHS and the
        current data cutoff for continuing resolutions (FY99)

        Parameters
        ----------
            start : The start date of the range.
            end : The end date of the range.

        Yields
        ------
        A generator of statuses for the date range.

        Notes
        -----
        TODO: I believe this process could be greatly sped up
        by generating a multiindex from tuples, using the POSIX
        start/end and info in constants.py vice the tree. General
        idea is to build a crazy complex index from tuples and
        then flatten it out into a dataframe. This would be
        more efficient than iterating through the tree.
        Another related thought is to try to reduce everything
        to number associations and slap it into a numpy array
        for pandas to translate.

        """
        start_posix: int = time_utils.pdtimestamp_to_posix_seconds(
            timestamp=time_utils.to_timestamp(start)
        )
        end_posix: int = time_utils.pdtimestamp_to_posix_seconds(
            time_utils.to_timestamp(end)
        )

        for interval in self.tree[start_posix:end_posix]:
            for key_date in {interval.begin, interval.end, start_posix, end_posix}:
                department_set: set[
                    "Dept"
                ] = self.get_executive_departments_set_at_time(date=key_date)
                if start_posix <= key_date <= end_posix:
                    default_status_key: str = self._determine_default_status_key(
                        posix_date=key_date
                    )
                    last_known_status: "StatusDictType" = {
                        dept: self.status_pool[(dept, default_status_key)]
                        for dept in department_set
                    }

                    for inner_interval in self.tree.at(p=key_date):
                        for department in inner_interval.data[0]:
                            status_key: "StatusTupleType" = inner_interval.data[1]
                            last_known_status[department] = self.status_pool[
                                (department, status_key)
                            ]
                    yield (str(key_date), last_known_status)

    def _determine_default_status_key(self, posix_date: int) -> str:
        """
        Simple private helper function to determine default department status
        based on date, setting "CR_DATA_CUTOFF_DEFAULT_STATUS" if before the
        CR data cutoff date, and FUTURE_STATUS if after the max_default_date.

        Parameters
        ----------
        posix_date
            date of the point of interest in POSIX time.

        Returns
        -------
        Returns the default key for STATUS_MAP based on the date.

        """
        if posix_date < constants.CR_DATA_CUTOFF_DATE:
            return "CR_DATA_CUTOFF_DEFAULT_STATUS"
        elif posix_date > self.max_default_date:
            return "FUTURE_STATUS"
        else:
            return "DEFAULT_STATUS"
