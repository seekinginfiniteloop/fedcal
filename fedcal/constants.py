# fedcal constants.py
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
----TODO: update me please---
"""
from __future__ import annotations

from enum import Enum, unique
from functools import total_ordering
from typing import Any, Generator, Literal

import pandas as pd
from pandas import Timestamp


@unique
@total_ordering
class Dept(Enum):
    """
    Dept enums represent federal departments and are used throughout fedcal to
    represent departments

    Attributes
    ----------
    self.abbrev

    Methods
    -------

    from_shortname : converts shortform string of the enum object back to
        an enum object

    from_longname : converts longform string of the enum object back to
        an enum object

    from_abbrev : converts abbreviated string of the enum object back to
        an enum object

    """

    def __init__(self, abbreviation: str, full_name: str, short_name: str) -> None:
        """
        Initializes an instance of Dept, an enum for storing
        constants of federal executive branch departments.

        Args:
            abbreviation (str): The mixed case abbreviation of the department.
            full_name (str): The full name of the department in mixed case.
            short_name (str): The shortened name of the department in mix case.
        """
        self.abbrev: str = abbreviation  # mixed case abbreviation
        self.full: str = full_name  # full name in mixed case
        self.short: str = short_name  # shortened name in mixed case

    def __iter__(self) -> Generator[str, Any, None]:
        """
        Iterates through the enum object's attributes.
        Returns a generator that yields the enum object's attributes.

        Yields
        ------
            str: The enum object's attributes.

        Example
        -------
        ```python
        for attr in Dept.DHS:
            print(attr)

        > DHS
        > Department of Homeland Security
        > Homeland Security
        ```
        """
        yield self.abbrev
        yield self.full
        yield self.short

    def __str__(self) -> str:
        """
        Customized string representation of enum

        Returns
        -------
        Returns object's full name with abbreviation in parens
        (e.g. "Department of State (DoS)")
        """
        return f"{type(self).__name__}: {self.full} ({self.abbrev})"

    def __eq__(self, other: Any) -> bool:
        """
        Customized equality comparison for enum

        Returns
        -------
        Returns True if other is a Dept enum and its abbrev matches self.abbrev
        """
        return (
            (self.abbrev, self.full, self.short)
            == (other.abbrev, other.full, other.short)
            if isinstance(other, Dept)
            else False
        )

    def __lt__(self, other: Any) -> bool:
        """
        Customized less than comparison for enum

        Returns
        -------
        Returns True if other is a Dept enum and its abbrev is less than
        self.abbrev
        """
        return (
            (self.abbrev, self.full, self.short)
            < (other.abbrev, other.full, other.short)
            if isinstance(other, Dept)
            else False
        )

    def __hash__(self) -> int:
        """
        Customized hash function for enum

        Returns
        -------
        Returns hash of tuple of attributes.
        """
        return hash((self.abbrev, self.full, self.short))

    DHS = ("DHS", "Department of Homeland Security", "Homeland Security")
    DOC = ("DoC", "Department of Commerce", "Commerce")
    DOD = ("DoD", "Department of Defense", "Defense")
    DOE = ("DoE", "Department of Energy", "Energy")
    DOI = ("DoI", "Department of the Interior", "Interior")
    DOJ = ("DoJ", "Department of Justice", "Justice")
    DOL = ("DoL", "Department of Labor", "Labor")
    DOS = ("DoS", "Department of State", "State")
    DOT = ("DoT", "Department of Transportation", "Transportation")
    ED = ("ED", "Department of Education", "Education")
    HHS = (
        "HHS",
        "Department of Health and Human Services",
        "Health and Human Services",
    )
    HUD = (
        "HUD",
        "Department of Housing and Urban Development",
        "Housing and Urban Development",
    )
    IA = ("IA", "Independent Agencies", "Independent Agencies")
    PRES = ("PRES", "Executive Office of the President", "Office of the President")
    USDA = ("USDA", "Department of Agriculture", "Agriculture")
    USDT = ("USDT", "Department of the Treasury", "Treasury")
    VA = ("VA", "Department of Veterans Affairs", "Veterans Affairs")

    @classmethod
    def reverse_lookup(cls, value: str) -> Dept | None:
        """
        Reverse lookup for Dept enum object from value.

        Parameters
        ----------
        value
            value to lookup

        Returns
        -------
            Dept object if found, None otherwise.

        """
        return next(
            (
                dept
                for dept in cls
                if isinstance(value, str)
                and (dept.abbrev == value or dept.full == value or dept.short == value)
            ),
            None,
        )

    @classmethod
    def swap_attr(
        cls, val: int | str, rtn_attr: Literal["val", "var", "approps", "ops", "simple"]
    ) -> int | str:
        """
        Receives the attribute value of a status enum object and returns the
        desired property of that object. Short hand for reverse
        lookup-to-attribute.

        Parameters
        ----------
        val
            Dept object value to lookup
        rtn_attr:
            attribute to return for the object

        Returns
        -------
            attribute if found, None otherwise.
        """
        return cls.reverse_lookup(value=val).__getattribute__(rtn_attr)


HISTORICAL_HOLIDAYS_BY_PROCLAMATION: list[Timestamp] = [
    pd.Timestamp(year=2020, month=12, day=24),
    pd.Timestamp(year=2019, month=12, day=24),
    pd.Timestamp(year=2018, month=12, day=24),
    pd.Timestamp(year=2015, month=12, day=24),
    pd.Timestamp(year=2014, month=12, day=26),
    pd.Timestamp(year=2012, month=12, day=24),
    pd.Timestamp(year=2007, month=12, day=24),
    pd.Timestamp(year=2001, month=12, day=24),
    pd.Timestamp(year=1979, month=12, day=24),
    pd.Timestamp(year=1973, month=12, day=31),
    pd.Timestamp(year=1973, month=12, day=24),
]

"""
HISTORICAL_PROCLAMATION_HOLIDAYS:
A list of Timestamps for historical days where the President proclaimed an
out-of-cycle holiday, usually for Christmas Eve.
Source: FederalTimes
"""

FEDPAYDAY_REFERENCE_DATE = pd.Timestamp(year=1969, month=12, day=19)
"""
FEDPAYDAY_REFERENCE_DATE:
Our reference date for Federal civilian payday calculations. I believe it's
possible to calculate using gregorian calendar patterns without using a known
payday for reference, but that approach adds complexity without meaningful
gain. We use the payday before the first payday of the unix epoch to keep
calculations straightforward (such that the first calculated payday is the
first payday of the epoch).
"""

DEPTS_SET: set[Dept] = {
    Dept.DHS,
    Dept.DOC,
    Dept.DOD,
    Dept.DOE,
    Dept.DOI,
    Dept.DOJ,
    Dept.DOL,
    Dept.DOS,
    Dept.DOT,
    Dept.ED,
    Dept.HHS,
    Dept.HUD,
    Dept.IA,
    Dept.PRES,
    Dept.USDA,
    Dept.USDT,
    Dept.VA,
}

"""
DEPTS_SET: A set of top-level executive departments as enum
objects. Data currently omit judiciary and legislative budgets (federal courts
and Congress).
"""

DHS_FORMED: int = pd.Timestamp(year=2003, month=11, day=25)


@unique
@total_ordering
class DeptStatus(Enum):
    def __init__(
        self,
        value: int,
        variable_string: str,
        appropriations_status: str,
        operational_status: str,
        simple_status: str,
    ) -> None:
        self.val: int = value
        self.var: str = variable_string
        self.approps: str = appropriations_status
        self.ops: str = operational_status
        self.simple: str = simple_status

    def __iter__(self) -> Generator[int, str, Any, None]:
        """
        Iterates through the enum object's attributes.
        Returns a generator that yields the enum object's attributes.

        Yields
        ------
            int | str: The enum object's attributes.
        """
        yield self.val
        yield self.var
        yield self.approps
        yield self.ops
        yield self.simple

    def __str__(self) -> str:
        """
        Customized string representation of enum

        Returns
        -------
        Returns simple status string with object name
        """
        return f"{type(self).__name__}: {self.simple}"

    def __hash__(self) -> int:
        """
        Customized hash function for enum

        Returns
        -------
        Returns hash of value.
        """
        return hash((self.val, self.var, self.approps, self.ops, self.simple))

    def __eq__(self, other: Any) -> bool:
        """
        Customized equality comparison for enum

        Returns
        -------
        Returns True if other is a DeptStatus enum and its value matches self.
        """
        return self.val == other.val if isinstance(other, DeptStatus) else False

    def __lt__(self, other: Any) -> bool:
        """
        Customized less than comparison for enum

        Returns
        -------
        Returns True if other DeptStatus enum has a lower integer value
        """
        return self.val < other.val if isinstance(other, DeptStatus) else False

    FA = (4, "full_approps", "full appropriations", "open", "appropriated")
    ND = (
        3,
        "approps_cr_or_full",
        "appropriated but unknown if full_year or cr",
        "open, unknown capacity",
        "cr or full",
    )
    CR = (2, "cont_res", "continuing resolution", "open with limitations", "cr")
    GAP = (
        1,
        "approps_gap",
        "no appropriations",
        "minimally open",
        "appropriations gap",
    )
    SD = (0, "shutdown", "no appropriations and shutdown", "shutdown", "shutdown")
    FUT = (
        -1,
        "future_unknown",
        "future status unknown",
        "future status unknown",
        "future",
    )

    @classmethod
    def reverse_lookup(cls, value: int | str) -> DeptStatus | None:
        """
        Reverse lookup for status enum object from value.

        Parameters
        ----------
        value
            value to lookup

        Returns
        -------
            DeptStatus object if found, None otherwise.

        """
        return next(
            (
                dept
                for dept in cls
                if (isinstance(value, int) and dept.val == value)
                or (
                    isinstance(value, str)
                    and (
                        dept.var == value
                        or dept.approps == value
                        or dept.ops == value
                        or dept.simple == value
                    )
                )
            ),
            None,
        )

    @classmethod
    def swap_attr(
        cls, val: int | str, rtn_attr: Literal["val", "var", "approps", "ops", "simple"]
    ) -> int | str:
        """
        Receives the attribute value of a status enum object and returns the
        desired property of that object. Short hand for reverse
        lookup-to-attribute.

        Parameters
        ----------
        val
            DeptStatus object value to lookup
        rtn_attr:
            attribute to return for the object

        Returns
        -------
            attribute if found, None otherwise.
        """
        return cls.reverse_lookup(value=val).__getattribute__(rtn_attr)
