from __future__ import annotations

from typing import TYPE_CHECKING, Any, Self, Tuple

from attrs import define, field, frozen
from intervaltree import IntervalTree

from _typing import (
    AppropriationsGapsMapType,
    AssembledBudgetIntervalType,
    CRMapType,
    FedDateStampConvertibleTypes,
)
from constants import (
    APPROPRIATIONS_GAPS,
    CR_DEPARTMENTS,
    EXECUTIVE_DEPARTMENT,
    EXECUTIVE_DEPARTMENTS_SET,
    STATUS_MAP,
)
from time_utils import YearMonthDay, to_datestamp

if TYPE_CHECKING:
    from fedcal import FedDateStamp


def _get_date_interval(
    dates: Tuple[int, int]
    | Tuple["FedDateStamp", "FedDateStamp"]
    | Tuple[FedDateStampConvertibleTypes, FedDateStampConvertibleTypes]
) -> tuple[int, int]:
    """
    Converts a tuple dates to a tuple of POSIX timestamps for use in our
    IntervalTrees. Primarily accepts FedDateStamp objects, but

    Parameters
    ----------
        dates
            tuple of dates comprised of int (POSIX), FedDateStamp, or
            FedDateStampConvertibleTypes representing the start and end of an
            interval.

    Returns
    -------
        A tuple of POSIX timestamps representing the start and end dates.
    """
    start: "FedDateStamp" | int | FedDateStampConvertibleTypes
    end: "FedDateStamp" | int | FedDateStampConvertibleTypes
    start, end = dates
    if start is not isinstance(start, int):
        start_datestamp: "FedDateStamp" = to_datestamp(start)
        start = start_datestamp.timestamp()
    if end is not isinstance(end, int):
        end_datestamp: "FedDateStamp" = to_datestamp(end)
        end: "FedDateStamp" = end_datestamp.timestamp()
    if start == end:
        # we add a day because intervaltree's end intervals are exclusive, and our calendar otherwise uses inclusive dates.
        end = end + 86400
    return start, end


def _get_overlap_interval(
    start: int,
    end: int,
    date_range: Tuple[int, int]
    | Tuple["FedDateStamp", "FedDateStamp"]
    | Tuple[FedDateStampConvertibleTypes, FedDateStampConvertibleTypes]
    | None = None,
) -> Tuple[int, int] | None:
    """
    Returns the overlap interval between the given start and end dates and the date range.

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
        (to_datestamp(start_range).timestamp())
        if start_range is not isinstance(start_range, int)
        else start_range
    )
    end_range: int = (
        (to_datestamp(end_range).timestamp())
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
    executive_departments_set: A set of EXECUTIVE_DEPARTMENT enum objects.
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
    _filter_cr_department_sets(departments) -> set[EXECUTIVE_DEPARTMENT]
        Filters input sets from constants.py to produce actual set of EXECUTIVE_DEPARTMENT objects for our IntervalTree.
    """

    executive_departments_set: set[EXECUTIVE_DEPARTMENT] = field(
        default=EXECUTIVE_DEPARTMENTS_SET, factory=set
    )
    cr_departments: CRMapType = field(default=CR_DEPARTMENTS, factory=dict)
    tree: IntervalTree = field(default=None, factory=IntervalTree)

    def __attrs_post_init__(self) -> None:
        """
        Initializes the CR tree after the class is instantiated.
        """
        self.tree = self.grow_cr_tree()

    @staticmethod
    def _filter_cr_department_sets(
        departments: set[EXECUTIVE_DEPARTMENT] | set[None],
    ) -> set[EXECUTIVE_DEPARTMENT]:
        """
        Filters input sets from constants.py to produce actual set of EXECUTIVE_DEPARTMENT objects for our IntervalTree.

        Parameters
        ----------
        departments : A set of EXECUTIVE_DEPARTMENT objects, intended for internal use from constants.py.

        Returns
        -------
        final set of EXECUTIVE_DEPARTMENT objects for our IntervalTree
        """
        return EXECUTIVE_DEPARTMENTS_SET.difference(departments)

    def grow_cr_tree(
        self,
        cr_departments: CRMapType | None = None,
        dates: Tuple[YearMonthDay, YearMonthDay] | None = None,
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
            if overlap := _get_overlap_interval(
                start=start, end=end, date_range=date_range
            ):
                generated_departments: set[
                    EXECUTIVE_DEPARTMENT
                ] = self._filter_cr_department_sets(departments=departments)
                data: AssembledBudgetIntervalType = (
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
    are stored as SHUTDOWN_FLAG enum objects

    Attributes
    ----------
    tree : The interval tree to grow with appropriations gaps.

    appropriations_gaps : Dictionary mapping intervals to department enum
    objects and shutdown information from constants.py.

    date : Optionally limit the date range of the generated tree, by
    default all dates from FY75 to present are included. Accepts any date-like object

    Methods
    -------
    grow_appropriation_gaps_tree(self, appropriations_gaps, dates) -> IntervalTree
        Grows an interval tree based on the provided data for appropriations
        gaps (from constants.py).
    """

    tree: IntervalTree = field(default=None, factory=IntervalTree)
    appropriations_gaps: AppropriationsGapsMapType = field(
        default=APPROPRIATIONS_GAPS, factory=dict
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
        appropriations_gaps: AppropriationsGapsMapType | None = None,
        dates: "FedDateStamp" | FedDateStampConvertibleTypes = None,
    ) -> IntervalTree:
        """
        Grows an interval tree based on the provided data for appropriations
        gaps (from constants).

        appropriations_gaps
            A dictionary mapping time intervals to departments and shutdown information.

        dates
            Optional dates for restricting the dates of the produced
            tree. By default produces a tree for all dates there are data (FY75 - Present). Accepts any FedDateStamp or FedDateStampConvertibleTypes.

        Returns
        --------
        The populated interval tree with appropriations gaps information.
        """

        appropriations_gaps = (
            appropriations_gaps
            if appropriations_gaps is not None
            else self.appropriations_gaps
        )
        tree: IntervalTree = self.tree if self.tree is not None else IntervalTree()
        date_range: tuple[int, int] | None = (
            _get_date_interval(dates=dates) if dates else None
        )

        for (start, end), (departments, shutdown) in appropriations_gaps.items():
            if overlap := _get_overlap_interval(
                start=start, end=end, date_range=date_range
            ):
                if shutdown == SHUTDOWN_FLAG.SHUTDOWN:
                    data: AssembledBudgetIntervalType = (
                        departments,
                        STATUS_MAP["SHUTDOWN_STATUS"],
                    )
                else:
                    data: AssembledBudgetIntervalType = (
                        departments,
                        STATUS_MAP["GAP_STATUS"],
                    )
                tree.addi(begin=start, end=end + 86400, data=data)


@frozen()
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

    def __new__(cls, *args, **kwargs) -> Self | "Tree":
        """
        We override __new__ to ensure only one Tree is created and make
        creation intuitive.
        """
        if cls._instance is None:
            cls._instance: Self = super(Tree, cls).__new__(cls=cls, *args, **kwargs)
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
        if hasattr(CRTreeGrower, "tree"):
            return CRTreeGrower.tree
        else:
            return CRTreeGrower().tree

    def _initialize_gap_tree(self) -> IntervalTree:
        """
        We initialize the appropriations gaps tree if it has not already been
        initialized.

        Returns
        -------
        AppropriationsGapsTreeGrower.tree : The appropriations gaps tree.
        """
        if hasattr(AppropriationsGapsTreeGrower, "tree"):
            return AppropriationsGapsTreeGrower.tree
        else:
            return AppropriationsGapsTreeGrower().tree
