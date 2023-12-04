from __future__ import annotations

from itertools import product
from typing import TYPE_CHECKING, Any, Dict, Generator, Tuple

from attrs import astuple, define, field
from intervaltree import IntervalTree


from _tree import Tree, _get_overlap_interval
from _typing import (
    FedDateStampConvertibleTypes,
    StatusDictType,
    StatusMapType,
    StatusPoolType,
)
from constants import (
    CR_DATA_CUTOFF_DATE,
    DEPT,
    DHS_FORMED,
    EXECUTIVE_DEPARTMENT,
    EXECUTIVE_DEPARTMENTS_SET,
    FUNDING_STATUS,
    OPERATIONAL_STATUS,
    STATUS_MAP,
)
from time_utils import get_today_in_posix, to_datestamp

if TYPE_CHECKING:
    from fedcal import FedDateStamp


@frozen(order=True)
class FedDepartment:
    """
    Represents a federal department with a specific funding and operational
    status.

    Attributes
    ----------
    name : The name of the executive department.
    funding_status : The funding status of the department.
    operational_status : The operational status of the department.

    Methods
    -------
    dept_tuple()
        Returns a tuple representation of the department's name and statuses.
    dept_dict()
        Returns a dictionary representation of the department's name and
        statuses.
    """

    name: EXECUTIVE_DEPARTMENT = field()
    funding_status: FUNDING_STATUS = field()
    operational_status: OPERATIONAL_STATUS = field()

    def dept_tuple(
        self,
    ) -> Tuple[EXECUTIVE_DEPARTMENT, FUNDING_STATUS, OPERATIONAL_STATUS]:
        """
        Return a tuple of FedDepartment attributes.
        Returns
        -------
        A tuple of FedDepartment attributes.

        """
        return astuple(inst=self)

    def dept_dict(self) -> StatusDictType:
        """
        Return a dictionary of FedDepartment attributes.

        Returns
        -------
        A dictionary of FedDepartment attributes.
        """
        return {self.name: self.dept_tuple}


@define(order=True)
class DepartmentStatus:
    """
    Manages the statuses of various departments, using a flyweight pattern
    for efficiency.

    Attributes
    ----------
    departments : Dict[EXECUTIVE_DEPARTMENT, FedDepartment]
        A dictionary mapping each executive department to its current
        FedDepartment instance.
    status_map : StatusMapType
        Maps status keys to corresponding tuples of funding and operational
        statuses, from constants.py STATUS_MAP.
    _status_pool : StatusPoolType
        A pool of FedDepartment instances for reuse, ensuring only one
        instance per status combination.

    Methods
    -------
    get_status_pool()
        Retrieves the singleton status pool.
    set_department_status(department, status_key)
        Sets the status of a given department based on a status key.
    get_department_status(department)
        Retrieves the current status of a given department.
    """

    departments: Dict[EXECUTIVE_DEPARTMENT, FedDepartment] = field(factory=dict)
    status_map: StatusMapType = field(default=STATUS_MAP, factory=dict)
    _status_pool: StatusPoolType | None = None

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
    def _initialize_status_pool(cls) -> None:
        """
        Initializes the status pool with FedDepartment instances.

        This private method populates the _status_pool class attribute with
        FedDepartment instances, each corresponding to a unique combination of
        executive department and status key.

        The method is called internally and ensures that the status pool is
        populated correctly, adhering to the flyweight pattern for efficient
        memory usage.
        """
        cls._status_pool: StatusPoolType = {
            (dept, status_key): FedDepartment(
                name=dept,
                funding_status=cls.status_map[status_key][0],
                operational_status=cls.status_map[status_key][1],
            )
            for dept, status_key in product(
                EXECUTIVE_DEPARTMENTS_SET, cls.status_map.keys()
            )
            if dept != DEPT.DHS and status_key == "CR_DATA_CUTOFF_DEFAULT_STATUS"
        }

    def get_department_status(self, department: EXECUTIVE_DEPARTMENT) -> FedDepartment:
        """
        Retrieves the current status of the specified department.

        If the department's status has been set previously, this method
        returns the corresponding FedDepartment instance from the departments
        dictionary. If the status has not been set, None is returned.

        Parameters
        ----------
        department : The executive department whose status is to be retrieved.

        Returns
        -------
        The FedDepartment instance representing the department's current
        status, or None if the status has not been set.
        """
        return self.departments.get(department)


@define(order=True)
class DepartmentState:
    """
    Represents the state of departments at different times, based on an interval tree structure.

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
        self.status_pool: StatusPoolType = DepartmentStatus.get_status_pool()

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
        return Tree.tree if hasattr(Tree, "tree") else Tree().tree

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
        today: int = get_today_in_posix()
        return max(tree_ceiling, today)

    def get_state(
        self, date: "FedDateStamp" | FedDateStampConvertibleTypes
    ) -> StatusDictType:
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
        posix_date: int = to_datestamp(date).timestamp()

        executive_department_set: set[EXECUTIVE_DEPARTMENT] = (
            EXECUTIVE_DEPARTMENTS_SET
            if posix_date >= DHS_FORMED
            else EXECUTIVE_DEPARTMENTS_SET.difference(DEPT.DHS)
        )

        status_dict: StatusDictType = {
            dept: self.status_pool[
                (
                    dept,
                    "CR_DATA_CUTOFF_DEFAULT_STATUS"
                    if posix_date < CR_DATA_CUTOFF_DATE
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

    def _process_interval(
        self, interval, last_known_status, start_posix, end_posix
    ) -> Generator[tuple[str, StatusDictType], Any, None]:
        """
        Processes a given interval, updating the status of departments.

        For each interval that overlaps with the specified date range, this
        method updates
        the status of departments affected by the interval. It yields the
        updated statuses
        for each key date within the interval.

        Parameters
        ----------
        interval : The interval to process.
        last_known_status : The last known status of departments before
        processing the interval.
        start_posix : The POSIX timestamp representing the start of the date
        range.
        end_posix : The POSIX timestamp representing the end of the date range.

        Yields
        ------
        A tuple containing the key date (as a string) and the updated status
        of departments.
        """
        if overlap := _get_overlap_interval(
            start=interval.begin,
            end=interval.end,
            date_range=(start_posix, end_posix),
        ):
            for key_date in [overlap[0], overlap[1]]:
                updated_status: StatusDictType = last_known_status.copy()
                for department in interval.data[0]:
                    if department != DEPT.DHS or key_date >= DHS_FORMED:
                        status_key: Tuple[
                            FUNDING_STATUS, OPERATIONAL_STATUS
                        ] = interval.data[1]
                        updated_status[department] = self.status_pool[
                            (department, status_key)
                        ]
                yield (str(key_date), updated_status)
                last_known_status: StatusDictType = updated_status

    def get_state_for_range_generator(
        self, start_date: "FedDateStamp", end_date: "FedDateStamp"
    ) -> Generator[Tuple[str, StatusDictType], None, None]:
        """
        Generates the status of all departments over a specified date range.

        This generator method iterates over each interval in the interval tree
        that overlaps with the specified date range. It yields the status of
        departments for each key date within the range, efficiently handling
        large date ranges through lazy evaluation.

        Parameters
        ----------
        start_date : The start date of the range for which department statuses
            are needed.
        end_date : The end date of the range for which department statuses
            are needed.

        Yields
        ------
        Tuple[str, StatusDictType]
            A tuple containing the key date (as a string) and the status of departments on that date.
        """
        start_posix: int = to_datestamp(start_date).timestamp()
        end_posix: int = to_datestamp(end_date).timestamp()
        default_status_key: str = (
            "CR_DATA_CUTOFF_DEFAULT_STATUS"
            if start_posix < CR_DATA_CUTOFF_DATE
            else "FUTURE_STATUS"
            if end_posix > self.max_default_date
            else "DEFAULT_STATUS"
        )
        last_known_status: StatusDictType = {
            dept: self.status_pool[(dept, default_status_key)]
            for dept in EXECUTIVE_DEPARTMENTS_SET
        }

        for interval in self.tree:
            yield from self._process_interval(
                interval=interval,
                last_known_status=last_known_status,
                start_posix=start_posix,
                end_posix=end_posix,
            )
