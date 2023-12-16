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

from __future__ import annotations

from typing import TYPE_CHECKING, Tuple

from attrs import field, frozen, astuple

if TYPE_CHECKING:
    from .constants import (
        Dept,
        AppropsStatus,
        OpsStatus,
        READABLE_STATUS_MAP,
    )
    from ._typing import StatusDictType, StatusTupleType


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

    status : A simplified string representation of the department's status.

    Methods
    -------
    dept_tuple()
        Returns a tuple representation of the department's name and statuses.
    dept_dict()
        Returns a dictionary representation of the department's name and
        statuses.

    """

    name: "Dept" = field()
    funding_status: "AppropsStatus" = field()
    operational_status: "OpsStatus" = field()

    def __str__(self) -> str:
        """We override attrs default to provide a meaningful string representation"""
        return f"{self.name.abbrev}: funding: {self.funding_status}, operational: {self.operational_status}"

    def attributes_to_tuple(
        self,
    ) -> Tuple["Dept", "AppropsStatus", "OpsStatus"]:
        """
        Return a tuple of FedDepartment attributes.
        Returns
        -------
        A tuple of FedDepartment attributes.

        """

        return astuple(inst=self)

    def to_status_tuple(self) -> "StatusTupleType":
        """
        Returns a StatusTupleType (Tuple[AppropsStatus, OpsStatus] for the FedDepartment instance

        Returns
        -------
        A StatusTupleType for the instance.

        """
        return self.funding_status, self.operational_status

    @property
    def status(self) -> str:
        """
        Return a simplified string representation of the department's status.

        Returns
        -------
        A human-readable string representation of the department's status.

        """
        return READABLE_STATUS_MAP[self.to_status_tuple()]

    def to_dict(self) -> "StatusDictType":
        """
        Return a dictionary of FedDepartment attributes.

        Returns
        -------
        A dictionary of FedDepartment attributes.

        """
        return {self.name: self.to_status_tuple()}
