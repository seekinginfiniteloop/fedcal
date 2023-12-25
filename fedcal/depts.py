# fedcal depts.py
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
The depts module houses the `FedDepartment` class, which represents a possible
status of a given federal executive department (i.e. Department of Commerce).
`FedDepartment` objects represent a department's appropriations and operational
statuses, but are not time-bound or intended to be instantiated directly.
Instead, they are generated and pooled in a flyweight structure by
`_dept_status.DepartmentStatus` and queried with that module's
`DepartmentState` class, and served to `FedStamp` and `FedIndex` as
output.

We expose this publicly because users will receive FedDepartment objects
from those queries, and can use `FedDepartment`'s properties to customize
that output.
"""

from typing import TYPE_CHECKING

from attrs import astuple, field, frozen

from fedcal.constants import READABLE_STATUS_MAP

if TYPE_CHECKING:
    from typing import Any, Generator, Tuple

    from ._typing import StatusDictType, StatusTupleType
    from .constants import AppropsStatus, Dept, OpsStatus


@frozen()
class FedDepartment:

    """
    Represents a federal department with a specific funding and operational
    status.

    Attributes
    ----------
    name : The name of the executive department.
    approps_status : The funding status of the department.
    ops_status : The operational status of the department.

    status : A simplified string representation of the department's status.

    Methods
    -------
    dept_tuple()
        Returns a tuple representation of the department's name and statuses.
    dept_dict()
        Returns a dictionary representation of the department's name and
        statuses.

    """

    name: Dept = field()
    approps_status: AppropsStatus = field()
    ops_status: OpsStatus = field()

    def __str__(self) -> str:
        """We override attrs default to provide a meaningful string
        representation

        Returns
        -------
        string representation of instance
        """
        return f"""{self.name.abbrev}:
            {self.approps_status},
            {self.ops_status.value}"""

    def __iter__(self) -> Generator[Dept | AppropsStatus | OpsStatus, Any, None]:
        """
        Implement a simple iter to make FedDepartment iterable.

        Yields
        ------
            Generator of instance attributes
        """
        yield self.name
        yield self.approps_status
        yield self.ops_status

    def __eq__(self, other) -> bool:
        """
        Override eq to ensure we can compare FedDepartment objects
        appropriately.

        Parameters
        ----------
        other
            other object to compare

        Returns
        -------
            True if a FedDepartment object with matching attributes
        """
        return (
            isinstance(other, FedDepartment)
            and self.attrs_to_tuple() == other.attrs_to_tuple()
        )

    def __lt__(self, other) -> bool:
        """
        Override lt to ensure we can compare FedDepartment objects
        appropriately.

        Parameters
        ----------
        other
            other object to compare

        Returns
        -------
            True if a FedDepartment object with matching attributes
        """
        return (
            self.attrs_to_tuple() < other.attrs_to_tuple()
            if isinstance(other, FedDepartment)
            else NotImplemented
        )

    def __gt__(self, other) -> bool:
        """
        Override gt to ensure we can compare FedDepartment objects
        appropriately.

        Parameters
        ----------
        other
            other object to compare

        Returns
        -------
            True if a FedDepartment object with matching attributes
        """
        return (
            self.attrs_to_tuple() > other.attrs_to_tuple()
            if isinstance(other, FedDepartment)
            else NotImplemented
        )

    def __hash__(self) -> int:
        """
        We want to make sure FedDepartment objects are properly hashable.

        Returns
        -------
            hash of a tuple of instance's attributes
        """
        return hash(self.attrs_to_tuple())

    def attrs_to_tuple(
        self,
    ) -> Tuple[Dept, AppropsStatus, OpsStatus]:
        """
        Return a tuple of FedDepartment attributes.
        Returns
        -------
        A tuple of FedDepartment attributes.

        """

        return astuple(inst=self)

    def to_status_tuple(self) -> StatusTupleType:
        """
        Returns a StatusTupleType (Tuple[AppropsStatus, OpsStatus] for the FedDepartment instance

        Returns
        -------
        A StatusTupleType for the instance.

        """
        return self.approps_status, self.ops_status

    @property
    def status(self) -> str:
        """
        Return a simplified string representation of the department's status.

        Returns
        -------
        A human-readable string representation of the department's status.

        """
        return READABLE_STATUS_MAP[self.to_status_tuple()]

    def to_dict(self) -> StatusDictType:
        """
        Return a dictionary of FedDepartment attributes.

        Returns
        -------
        A dictionary of FedDepartment attributes.

        """
        return {self.name: self.to_status_tuple()}
