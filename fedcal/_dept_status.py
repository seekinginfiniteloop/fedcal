# fedcal _dept_status.py
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

The _dept_status module contains classes for processing
federal department appropriations and associated operating
statuses over time, which is drawn from constants.py
and stored in an interval tree (_tree module). Classes:
- `DepartmentStatus` creates a 'status pool' of
FedDepartment instances of all possible combinations
for reuse, using a flyweight pattern.
- `DepartmentState` queries and retrieves points and ranges
of interval data from `_tree.Tree()`
"""
from __future__ import annotations

from itertools import product
from typing import ClassVar

from attrs import define
from intervaltree import IntervalTree
from pandas import Timestamp

from fedcal import time_utils
from fedcal._tree import Tree
from fedcal._typing import (
    StatusDictType,
    StatusGeneratorType,
    StatusMapType,
    StatusPoolType,
    StatusTupleType,
)
from fedcal.constants import (
    CR_DATA_CUTOFF_DATE,
    DEPTS_SET,
    DHS_FORMED,
    STATUS_MAP,
    Dept,
)
from fedcal.depts import FedDepartment


@define(order=True, auto_attribs=True)
class DepartmentStatus:

    """
    Manages the statuses of various departments, using a flyweight pattern
    for efficiency.

    Attributes
    ----------
    status_map (class attr): StatusMapType
        Maps status keys to corresponding tuples of funding and operational
        statuses, from constants.py STATUS_MAP.
    status_pool (class attr): StatusPoolType
        *class attribute*: A pool of FedDepartment instances for reuse,
        ensuring only one instance per status combination.

    Methods
    -------
    get_status_pool()
        Retrieves the singleton status pool.

    Notes
    -----
    *Private Methods*:
    - _initialize_status_pool()
        Class method that creates the status_pool class attribute.
    """

    status_map: ClassVar[StatusMapType] = STATUS_MAP
    status_pool: ClassVar[StatusPoolType] = None

    def __attrs_post_init(self) -> None:
        """
        Initializes status_pool if not initialized.
        """
        if not type(self).status_pool:
            type(self).status_pool = type(self)._initialize_status_pool()

    @classmethod
    def _initialize_status_pool(cls) -> StatusPoolType:
        """
        Initializes the status pool class attribute with FedDepartment
        instances.

        This private method populates the status_pool class attribute with
        FedDepartment instances, each corresponding to a unique combination of
        executive department and status key.

        The method is called internally and ensures that the status pool is
        populated correctly, adhering to the flyweight pattern for efficient
        memory usage.
        """

        status_pool: "StatusPoolType" = {
            (dept, status_key): FedDepartment(
                name=dept,
                approps_status=cls.status_map[status_key][0],
                ops_status=cls.status_map[status_key][1],
            )
            for dept, status_key in product(DEPTS_SET, cls.status_map.keys())
        }
        # we delete DHS for this status since it was created after the cutoff
        del status_pool[Dept.DHS, "CR_DATA_CUTOFF_DEFAULT_STATUS"]
        return status_pool

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
        if cls.status_pool is None:
            cls.status_pool: StatusPoolType = cls._initialize_status_pool()
        return cls.status_pool


@define(order=True, auto_attribs=True)
class DepartmentState:

    """
    Represents the state of departments at different times, based on an
    interval tree structure.

    Attributes
    ----------
    tree : An interval tree representing changes in department statuses over
        time.
    max_default_date : Cutoff date for future status data, set as the greater
        of the maximum interval in tree or today.

    Methods
    -------
    initialize_tree()
        Initializes the singleton interval tree.
    get_state(date)
        Retrieves the status of all departments for a specific date, returning
        a dictionary of statuses.
    get_state_for_range_generator(start_date, end_date)
        Returns a generator of statuses for a given date range.
    get_depts_set_at_time(date)
        Returns a set of department enums for all departments at a given date.
    get_state_tree
        Retrieves the singleton interval tree

    Notes
    -----
    Currently the framework assumes a default status of fully funded if during
    a present timeframe and no other status is known. However, this needs
    adjustment because if a Department has received a full-year appropriation,
    we should return fully funded until the end of the FY, but currently it
    will only return that way until the end of the tree or today, whichever is
    later.

    *Private Methods*:
    _set_max_default
        Sets the max_default date for determining what cutoff switches to
        FUTURE_STATUS
    _determine_default_status_key
        Determines the default status key for a given date.
    """

    tree: ClassVar[IntervalTree] | None = None
    max_default_date: ClassVar[int] | None = None

    def __attrs_post_init(self) -> None:
        if not type(self.tree):
            type(self).initialize_tree()

    @classmethod
    def _set_max_default(cls) -> None:
        """
        Set the maximum default date. Sets to the latter of either today or
        the end of the interval tree (because CRs have an expiration date,
        we can have statuses into the future.)

        Returns
        -------
        The maximum default date, any date after will be handled with
        FUTURE_STATUS.

        """
        if not cls.tree:
            cls.initialize_tree()
        tree_ceiling: int = cls.tree.end() if cls.tree else 0
        today: int = time_utils.get_today_in_posix_day()
        cls.max_default_date = max(tree_ceiling, today)

    @classmethod
    def initialize_tree(cls) -> None:
        """
        Initializes and returns an IntervalTree instance.

        This method creates an IntervalTree, either by reusing an existing
        tree if available or by generating a new one. This tree is used to
        store intervals representing periods of status changes for departments.

        Returns
        -------
        An IntervalTree instance representing the state of departments over
        time.

        Notes
        -----
        This method is called internally and ensures that the tree is
        initialized correctly, adhering to the flyweight pattern for efficient
        memory usage.

        """

        _tree_instance = Tree()
        if not _tree_instance.tree:
            _tree_instance.initialize_tree()
        cls.tree: IntervalTree = _tree_instance.tree.copy()

    @classmethod
    def get_state_tree(cls) -> IntervalTree:
        """
        Retrieves the singleton tree.

        Returns
        -------
        The singleton tree.

        """
        if not cls.tree:
            cls.initialize_tree()
            cls._set_max_default()
        return cls.tree

    @staticmethod
    def get_depts_set_at_time(
        date: Timestamp | int,
    ) -> set[Dept]:
        """
        Retrieves set of Depts enum objects based on time input; a helper
        method  for handling DHS's creation.

        Returns
        -------
            The set of Depts objects.
        """
        if not isinstance(date, int):
            date = time_utils.pdtimestamp_to_posix_day(timestamp=date)
        return DEPTS_SET if date >= DHS_FORMED else DEPTS_SET.difference({Dept.DHS})

    @classmethod
    def _determine_default_status_key(cls, posix_date: int) -> str:
        """
        Simple private helper function to determine default department status
        based on date, setting "CR_DATA_CUTOFF_DEFAULT_STATUS" if before the
        CR data cutoff date, and FUTURE_STATUS if after the max_default_date.

        Parameters
        ----------
        posix_date
            date of the point of interest in POSIX-day time.

        Returns
        -------
        Returns the default key for STATUS_MAP based on the date.

        """
        if posix_date < CR_DATA_CUTOFF_DATE:
            return "CR_DATA_CUTOFF_DEFAULT_STATUS"
        if posix_date > cls.max_default_date:
            return "FUTURE_STATUS"
        return "DEFAULT_STATUS"

    @classmethod
    def get_state(cls, date: Timestamp) -> StatusDictType:
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
        status_pool: StatusPoolType = DepartmentStatus.get_status_pool()
        tree: IntervalTree = cls.tree if cls.tree is not None else cls.get_state_tree()
        status_map: "StatusMapType" = STATUS_MAP

        posix_date: int = time_utils.pdtimestamp_to_posix_day(timestamp=date)
        depts_set: set[Dept] = cls.get_depts_set_at_time(date=date)
        default_status_key: str = cls._determine_default_status_key(
            posix_date=posix_date
        )
        status_dict: "StatusDictType" = {}

        if data := tree.at(p=posix_date):
            for interval in data:
                status_key: str = status_map.inverse[interval.data[1]]
                for dept in interval.data[0]:
                    status_dict[dept] = status_pool[(dept, status_key)]

        elif not data:
            for dept in depts_set:
                status_dict[dept] = status_pool[(dept, default_status_key)]

        if diff_set := depts_set.difference(set(status_dict.keys())):
            for dept in diff_set:
                status_dict[dept] = status_pool[(dept, default_status_key)]
        return status_dict

    @classmethod
    def get_state_for_range_generator(
        cls,
        start: Timestamp,
        end: Timestamp,
    ) -> StatusGeneratorType:
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
        status_pool: "StatusPoolType" = DepartmentStatus.get_status_pool()
        tree: IntervalTree = cls.get_state_tree()
        start_posix: int = time_utils.pdtimestamp_to_posix_day(timestamp=start)
        end_posix: int = time_utils.pdtimestamp_to_posix_day(timestamp=end)

        for interval in tree[start_posix:end_posix]:
            for key_date in {interval.begin, interval.end, start_posix, end_posix}:
                department_set: set[Dept] = cls.get_depts_set_at_time(date=key_date)
                if start_posix <= key_date <= end_posix:
                    default_status_key: str = cls._determine_default_status_key(
                        posix_date=key_date
                    )
                    last_known_status: "StatusDictType" = {
                        dept: status_pool[(dept, default_status_key)]
                        for dept in department_set
                    }

                    for inner_interval in tree.at(p=key_date):
                        for department in inner_interval.data[0]:
                            status_key: "StatusTupleType" = inner_interval.data[1]
                            last_known_status[department] = status_pool[
                                (department, status_key)
                            ]
                    yield (
                        time_utils.to_timestamp(key_date).strftime(format="%Y-%m-%d"),
                        last_known_status,
                    )
