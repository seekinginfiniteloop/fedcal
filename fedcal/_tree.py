# fedcal _tree.py
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
This is a private module that implements intervaltree storage of
appropriations status data from constants.py. Given the eccentricities
of interval trees, we handle querying through a layered approach with
`_dept_status.DepartmentState` handling queries for `FedStamp` and `FedIndex`.

We use interval trees because they're optimal for interval queries.
This module's classes and functions:
- `_get_date_interval` and `_get_overlap_interval` are helpers
for building our trees.
- `CRTreeGrower` and `AppropriationsTreeGrower` build
interval trees for continuing resolutions and approps gaps/shutdowns
respectively.
- `Tree` is the primary tree, which is a union of the trees built
by `CRTreeGrower` and `AppropriationsTreeGrower`. It's a singleton
class -- we only want (and need) to build one. As designed,
`CRTreeGrower` and `AppropriationsTreeGrower` are initialized by `Tree`,
and so are also effectively singletons.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Self, Tuple

from attrs import define, field
from intervaltree import IntervalTree

from fedcal import time_utils
from fedcal.constants import (
    APPROPRIATIONS_GAPS,
    CR_DEPARTMENTS,
    DEPTS_SET,
    STATUS_MAP,
    Dept,
    ShutdownFlag,
)

if TYPE_CHECKING:
    import pandas as pd
    from fedcal._typing import (
        AppropriationsGapsMapType,
        AssembledBudgetIntervalType,
        CRMapType,
        FedStampConvertibleTypes,
    )
    from fedcal.time_utils import YearMonthDay


def _get_date_interval(
    dates: Tuple[int, int]
    | Tuple["FedStampConvertibleTypes", "FedStampConvertibleTypes"]
) -> tuple[int, int]:
    """
    Converts a tuple dates to a tuple of POSIX timestamps for use in our
    IntervalTrees. Primarily accepts Timestamps, but can handle any
    FedStampConvertibleTypes.

    Parameters
    ----------
        dates
            tuple of dates comprised of int (POSIX), or
            FedStampConvertibleTypes representing the start and end of an
            interval.

    Returns
    -------
        A tuple of POSIX timestamps representing the start and end dates.

    """
    start: "pd.Timestamp" | int | "FedStampConvertibleTypes"
    end: "pd.Timestamp" | int | "FedStampConvertibleTypes"
    start, end = dates
    if start is not isinstance(start, int):
        start_timestamp: "pd.Timestamp" = time_utils.to_timestamp(start)
        start = time_utils.pdtimestamp_to_posix_seconds(timestamp=start_timestamp)
    if end is not isinstance(end, int):
        end_timestamp: "pd.Timestamp" = time_utils.to_timestamp(end)
        end: "pd.Timestamp" = time_utils.pdtimestamp_to_posix_seconds(
            timestamp=end_timestamp
        )
    if start == end:
        # we add a day because intervaltree's end intervals are exclusive, and
        # our calendar otherwise uses inclusive dates.
        end = end + 86400
    return start, end


def _get_overlap_interval(
    start: int,
    end: int,
    date_range: Tuple[int, int]
    | Tuple["FedStampConvertibleTypes", "FedStampConvertibleTypes"]
    | None = None,
) -> Tuple[int, int] | None:
    """
    Returns the overlap interval between the given start and end dates and the
    date range.

    Parameters
    ----------
    start : The start date of the interval.
    end : The end date of the interval.
    date_range : Optional date range to check for overlap.

    Returns
    -------
    The overlap interval as a tuple of start and end dates. If there
    is no overlap, returns None.

    """

    if not date_range:
        return start, end
    start_range, end_range = date_range
    start_range: int = (
        (
            time_utils.pdtimestamp_to_posix_seconds(
                timestamp=time_utils.to_timestamp(start_range)
            )
        )
        if start_range is not isinstance(start_range, int)
        else start_range
    )
    end_range: int = (
        (
            time_utils.pdtimestamp_to_posix_seconds(
                timestamp=time_utils.to_timestamp(start_range)
            )
        )
        if end_range is not isinstance(end_range, int)
        else end_range
    )
    if end < start_range or start > end_range:
        return None  # No overlap
    overlap_start: int = max(start, start_range)
    overlap_end: int = min(end, end_range)
    return overlap_start, overlap_end


@define(order=True)
class CRTreeGrower:

    """
    Class responsible for growing a CR (Continuing Resolution) IntervalTree
    enables efficient time-based queries. This class
    generates one of the trees used by Tree.

    Attributes
    ----------
    depts_set_set: A set of Dept enum objects.
    cr_departments : Dictionary mapping intervals (POSIX timestamps) for
        continuing resolutions (FY99-Present) to affected departments.
    tree : The interval tree to grow.

    Methods
    -------
    grow_cr_tree(self, cr_departments, dates) -> IntervalTree
        Grows an interval tree based on the provided CR intervals and affected
        departments (from constants.py).

    Notes
    -----
    *Private Methods*:
    _filter_cr_department_sets(departments) -> set[Dept]
        Filters input sets from constants.py to produce actual set of
        Dept objects for our IntervalTree.

    """

    depts_set_set: set[Dept] = field(default=DEPTS_SET)
    cr_departments: "CRMapType" = field(default=CR_DEPARTMENTS)
    tree: IntervalTree = field(factory=IntervalTree)

    def __attrs_post_init__(self) -> None:
        """
        Initializes the CR tree after the class is instantiated.
        """
        self.tree = self.grow_cr_tree()

    @staticmethod
    def _filter_cr_department_sets(
        departments: set[Dept] | set[None],
    ) -> set[Dept]:
        """
        Filters input sets from constants.py to produce actual set of
        Dept objects for our IntervalTree.

        Parameters
        ----------
        departments : A set of Dept objects, intended for
        internal use from constants.py.

        Returns
        -------
        final set of Dept objects for our IntervalTree

        """
        return DEPTS_SET.difference(departments)

    def grow_cr_tree(
        self,
        cr_departments: "CRMapType" | None = None,
        dates: Tuple["YearMonthDay", "YearMonthDay"] | None = None,
    ) -> IntervalTree:
        """
        Grows an interval tree based on the provided CR intervals and affected
        departments (from constants). Sets of affected departments in
        constants are the difference set, so we need to construct our
        tree accordingly.

        Parameters
        ----------
        cr_departments : A dictionary mapping time intervals to departments.
        dates : Optional dates for restricting dates for the generated
            tree. Otherwise produces tree for FY99 - Present

        Returns
        -------
        The populated interval tree.

        """
        cr_departments = (
            cr_departments if cr_departments is not None else self.cr_departments
        )
        cr_tree: IntervalTree = self.tree if self.tree is not None else IntervalTree()
        date_range: tuple[int, int] | None = (
            _get_date_interval(dates=dates) if dates else None
        )

        for (start, end), departments in cr_departments.items():
            if _get_overlap_interval(start=start, end=end, date_range=date_range):
                generated_departments: set[Dept] = self._filter_cr_department_sets(
                    departments=departments
                )
                data: "AssembledBudgetIntervalType" = (
                    generated_departments,
                    STATUS_MAP["CR_STATUS"],
                )
                cr_tree.addi(begin=start, end=end + 86400, data=data)
        return cr_tree


@define(order=True)
class AppropriationsGapsTreeGrower:
    """
    Class grows an IntervalTree comprised of date ranges and affected
    departments for appropriations gaps since FY75. Includes both shutdowns
    and other gaps in appropriations short of a federal shutdown, shutdowns
    are stored as ShutdownFlag enum objects

    Attributes
    ----------
    tree : The interval tree to grow with appropriations gaps.

    appropriations_gaps : Dictionary mapping intervals to department enum
    objects and shutdown information from constants.py.

    date : Optionally limit the date range of the generated tree, by
    default all dates from FY75 to present are included. Accepts any date-like
    object

    Methods
    -------
    grow_appropriation_gaps_tree(self, appropriations_gaps, dates) ->
    IntervalTree
        Grows an interval tree based on the provided data for appropriations
        gaps (from constants.py).
    """

    tree: IntervalTree = field(factory=IntervalTree)
    appropriations_gaps: "AppropriationsGapsMapType" = field(
        default=APPROPRIATIONS_GAPS
    )
    dates: Any | None = field(default=None)

    def __attrs_post_init__(self) -> None:
        """
        Initializes the appropriations gaps tree after the class is
        instantiated.
        """
        self.tree = self.grow_appropriation_gaps_tree()

    def grow_appropriation_gaps_tree(
        self,
        appropriations_gaps: "AppropriationsGapsMapType" | None = None,
        dates: "FedStampConvertibleTypes" = None,
    ) -> IntervalTree:
        """
        Grows an interval tree based on the provided data for appropriations
        gaps (from constants).

        appropriations_gaps
            A dictionary mapping time intervals to departments and shutdown
            information.

        dates
            Optional dates for restricting the dates of the produced
            tree. By default produces a tree for all dates there are data
            (FY75 - Present). Accepts any
            FedStampConvertibleTypes.

        Returns
        --------
        The populated interval tree with appropriations gaps information.

        """

        appropriations_gaps = (
            appropriations_gaps
            if appropriations_gaps is not None
            else self.appropriations_gaps
        )
        gap_tree: IntervalTree = self.tree if self.tree is not None else IntervalTree()
        date_range: tuple[int, int] | None = (
            _get_date_interval(dates=dates) if dates else None
        )

        for (start, end), (departments, shutdown) in appropriations_gaps.items():
            if _get_overlap_interval(start=start, end=end, date_range=date_range):
                if shutdown == ShutdownFlag.SHUTDOWN:
                    data: "AssembledBudgetIntervalType" = (
                        departments,
                        STATUS_MAP["SHUTDOWN_STATUS"],
                    )
                else:
                    data: "AssembledBudgetIntervalType" = (
                        departments,
                        STATUS_MAP["GAP_STATUS"],
                    )
                gap_tree.addi(begin=start, end=end + 86400, data=data)
        return gap_tree


class Tree:

    """
    Class representing a combined interval tree with CR and appropriations
    gaps data.

    **This class is intended to be immutable**: once an instance is created,
    its data should not be modified.
    Please treat the 'cr_tree' and 'gap_tree' as read-only properties.

    Like gremlins, you shouldn't feed them after midnight.

    The tree **only stores exceptions to normal appropriations**, if a given
    department(s) is not in the tree for a given interval, then the
    department(s) were fully appropriated. However, current continuing
    resolution data is only implemented since FY99; if a query is for a period
    before FY99, and the department(s) are not in the tree, then the
    departments(s) may have been fully funded OR under a continuing resolution.

    Tree is a background class not intended for frontline use. Instead,
    most users should use DepartmentState to retrieve department status, as
    this class adds logic for data missing in Tree.

    Attributes
    ----------
    _instance : The singleton instance of the class.

    cr_tree : The continuing resolution tree.

    gap_tree : The appropriations gaps tree.

    tree : The union of the CR and gap trees.

    _initialized : A boolean flag indicating if the instance has been
    initialized. We use this flag to ensure the instance is only
    initialized once.

    Example
    -------
    Initializing Tree:
        Tree()

    Notes
    -----
    *Private methods*:
    _initialize_cr_tree() -> IntervalTree
        Initializes the CR tree.
    _initialize_gap_tree() -> IntervalTree
        Initializes the gap tree.

    """

    _instance = None

    def __new__(cls) -> Self | "Tree":
        """
        We override __new__ to ensure only one Tree is created and make
        creation intuitive.
        """
        if cls._instance is None:
            cls._instance: Self = super(Tree, cls).__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """
        We initialize the instance if one has not already been initialized.
        We also initialize the feeder trees, CRTreeGrower and
        AppropriationsGapsTreeGrower, if not already initialized.
        We then union them together to form our tree, which enables efficient
        time-based queries in O(n * log n).

        Raises
        ------
        AttributeError
            If the instance has already been initialized.

        Notes
        -----
        See class attributes for a description of attributes initialized here.

        This is a singleton class, so we ensure that only one instance is
        created. We also initialize the feeder trees, CRTreeGrower and
        AppropriationsGapsTreeGrower, if not already initialized.
        We then union them together to form our tree, which enables
        efficient time-based queries in O(n * log n).

        See intervaltree documentation for usage examples:
        https://github.com/chaimleib/intervaltree
        """
        if not hasattr(self, "_initialized"):
            self.cr_tree: IntervalTree = self._initialize_cr_tree()
            self.gap_tree: IntervalTree = self._initialize_gap_tree()
            self.tree: IntervalTree = self.cr_tree.union(other=self.gap_tree)

            self._initialized = True

    def _initialize_cr_tree(self) -> IntervalTree:
        """
        We initialize the CR tree if it has not already been initialized.

        Returns
        -------
        CRTreeGrower.tree : The CR tree.

        """
        crtree = CRTreeGrower()
        return crtree.tree

    def _initialize_gap_tree(self) -> IntervalTree:
        """
        We initialize the appropriations gaps tree if it has not already been
        initialized.

        Returns
        -------
        AppropriationsGapsTreeGrower.tree : The appropriations gaps tree.

        """
        gaptree = AppropriationsGapsTreeGrower()
        return gaptree.tree
