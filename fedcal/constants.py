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
The constants data here primarily concern historical appropriations data to
enable queries of executive department funding and operations statuses over
time. Shifts in appropriations status can have profound impacts on the
effectiveness of federal departments, and so these data enable analyses of the
impacts on not just federal services, but national and local economies.

Budget data were primarily accumulated from from Congressional Research
Service: https://crsreports.congress.gov/AppropriationsStatusTable and
cross-referenced with Wikipedia, and the Government Accountability Office
The data are entirely within the public domain. I was unable to find a
publicly available dataset with this information precompiled; so I made one.
"""

from __future__ import annotations

from enum import Enum, unique
from typing import TYPE_CHECKING, Any, Generator, Literal

import pandas as pd
from bidict import frozenbidict

if TYPE_CHECKING:
    from ._typing import (
        AppropriationsGapsMapType,
        CRMapType,
        StatusMapType,
        StatusTupleType,
    )


@unique
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
        return f"{self.__class__.__name__}: {self.full} ({self.abbrev})"

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

    def __gt__(self, other: Any) -> bool:
        """
        Customized greater than comparison for enum

        Returns
        -------
        Returns True if other is a Dept enum and its abbrev is greater than
        self.abbrev
        """
        return (
            (self.abbrev, self.full, self.short)
            > (other.abbrev, other.full, other.short)
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
    def from_short_name(cls, short_name: str) -> Dept:
        """
        Converts a short name of a department to an enum object.
        Raises a ValueError if the department is not found.

        Parameters
        ----------
            short_name (str): The short name of the department.

        Returns
        -------
            Dept: The enum object representing the department.

        Raises
        ------
            ValueError: If the department is not found.

        Example
        -------
            >>> from fedcal.constants import Dept
            >>> Dept.from_short_name("Homeland Security")
            Dept.DHS

        """
        for dept in cls:
            if dept.short == short_name:
                return dept
        raise ValueError(f"Department with short name {short_name} not found")

    @classmethod
    def from_long_name(cls, long_name: str) -> Dept:
        """
            Converts a long name of a department to an enum object.
            Raises a ValueError if the department is not found.

            Returns
            -------
                Dept: The enum object representing the department.

            Raises
            ------
            ValueError : if the department is not found.

            Example
            -------
        >>> from fedcal.constants import Dept
        >>> Dept.from_long_name("Department of the Interior")
            Dept.DOI
        """
        for dept in cls:
            if dept.full == long_name:
                return dept
        raise ValueError(f"Department with long name {long_name} not found")

    @classmethod
    def from_abbrev(cls, abbrev: str) -> Dept:
        """
        Converts an abbrev of a department to an enum object.
        Raises a ValueError if the department is not found.

        Returns
        -------
            Dept: The enum object representing the department.

        Raises
        ------
        ValueError : if the department is not found.

        Example
        -------
        >>> from fedcal.constants import Dept
        >>> Dept.from_abbrev("DoI")
        Dept.DOI
        """
        for dept in cls:
            if dept.abbrev == abbrev:
                return dept
        raise ValueError(f"Department with abbrev {abbrev} not found")


HISTORICAL_HOLIDAYS_BY_PROCLAMATION: list[pd.Timestamp] = [
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


class EnumDunderBase:
    """
    A base class for defining dunder methods for most of fedcal's
    enumerations.
    """

    def __iter__(self) -> Literal:
        """
        Custom iter method for enums

        Returns
        -------
            enum object's value
        """
        return self.value

    def __str__(self) -> str:
        """
        Custom string representation of enum object

        Returns
        -------
            str: a string in the form :ClassName: value"
        """
        return f"{self.__class__.__name__}: {self.value}"

    def __eq__(self, other) -> bool:
        """
        custom eq representation of enum object

        Parameters
        ----------
        other
            other object for comparison

        Returns
        -------
            bool -- True if isinstance of same class and has same value
        """
        return isinstance(other, self.__class__) and self.value == other.value

    def __hash__(self) -> int:
        """
        custom hash representation of enum object

        Returns
        -------
            int -- hash of enum object's value
        """
        return hash(self.value)

    def __lt__(self, other) -> bool:
        """
        custom lt representation of enum object

        Parameters
        ----------
        other
            other object for comparison

        Returns
        -------
            bool -- True if isinstance of same class and has same value
        """
        return isinstance(other, self.__class__) and self.value < other.value

    def __gt__(self, other) -> bool:
        """
        custom gt representation of enum object

        Parameters
        ----------
        other
            other object for comparison

        Returns
        -------
            bool -- True if isinstance of same class and has same value
        """
        return isinstance(other, self.__class__) and self.value > other.value


@unique
class AppropsStatus(EnumDunderBase, Enum):
    """
    An enum class for setting appropriations status for executive departments
    - Fully Appropriated denotes departments operating under a full-year
    appropriations.
    - Temporarily Appropriated denotes departments operating
    under a continuing resolution.
    - Fully or Temporarily Appropriated is used for departments prior to FY99
    with appropriations of some kind, but for which data is not yet included
    in the library.
    No Appropriations denotes departments with no appropriations -- either in
    a gapped or shutdown status. Gap/shutdown data are complete to FY75.
    - Future indicates an unknown future status.
    """

    FULLY_APPROPRIATED = "Fully Appropriated"
    TEMPORARILY_APPROPRIATED = "Temporarily Appropriated"
    FULLY_OR_TEMPORARILY_APPROPRIATED = (
        "Data Incomplete: Fully or Temporarily Appropriated"
    )
    NO_APPROPRIATIONS = "No Appropriations"
    FUTURE = "Future Unknown"


@unique
class OpsStatus(EnumDunderBase, Enum):
    """
    An enum class for setting operating status for executive departments.
    - Open denotes departments operating under a full-year appropriation.
    - Open With Limitations denotes departments operating under a continuing
    resolution.
    - Open or Open With Limitations is used for departments prior to FY99 with
    appropriations of some kind, but for which data is not yet included in the
    library.
    - Minimally Open denotes departments with no appropriations -- in a gapped
    status but not shutdown.
    - Shutdown denotes departments with no appropriations and shutdown.
    Gap/shutdown data are complete to FY75.
    - Future indicates an unknown future status.
    """

    OPEN = "Open"
    OPEN_WITH_LIMITATIONS = "Open With Limitations"
    OPEN_OR_OPEN_WITH_LIMITATIONS = "Data Incomplete: Open or Open with Limitations"
    MINIMALLY_OPEN = "Minimally Open"
    SHUTDOWN = "Shutdown"
    FUTURE = "Future Unknown"


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

DHS_FORMED: int = 12016
"""DHS_FORMED: POSIX-day date of DHS formation (2003-11-25)"""


STATUS_MAP: "StatusMapType" = frozenbidict(
    {
        "DEFAULT_STATUS": (AppropsStatus.FULLY_APPROPRIATED, OpsStatus.OPEN),
        "CR_STATUS": (
            AppropsStatus.TEMPORARILY_APPROPRIATED,
            OpsStatus.OPEN_WITH_LIMITATIONS,
        ),
        "CR_DATA_CUTOFF_DEFAULT_STATUS": (
            AppropsStatus.FULLY_OR_TEMPORARILY_APPROPRIATED,
            OpsStatus.OPEN_OR_OPEN_WITH_LIMITATIONS,
        ),
        "GAP_STATUS": (AppropsStatus.NO_APPROPRIATIONS, OpsStatus.MINIMALLY_OPEN),
        "SHUTDOWN_STATUS": (AppropsStatus.NO_APPROPRIATIONS, OpsStatus.SHUTDOWN),
        "FUTURE_STATUS": (AppropsStatus.FUTURE, OpsStatus.FUTURE),
    }
)

"""
STATUS_MAP: We map possible AppropsStatus, OpsStatus combinations to string
descriptions so we can simplify manipulations _dept_status.py.
"""
READABLE_STATUSES: list[str] = [
    "open, full year approps",
    "open with limits, continuing resolution",
    "unknown open, either CR or full approps",
    "minimally open, no approps",
    "closed, shutdown",
    "future unknown",
]

"""
READABLE_STATUSES: Simplified human-readable statuses for the default
FedIndex behavior of outputing human-readable status.
"""

READABLE_STATUS_MAP: frozenbidict["StatusTupleType", str] = frozenbidict(
    zip(STATUS_MAP.values(), iter(READABLE_STATUSES))
)

"""
READABLE_STATUS_MAP: An immutable bidict mapping human-readable statuses to
their enum status tuples (AppropsStatus, OpsStatus). We use this for
FedDepartments' .status property and for converting FedIndex
human-readable statuses to more detailed output for power users.
"""


class ShutdownFlag(EnumDunderBase, Enum):
    """ShutdownFlag: An enum object denoting whether an appropriations gap
    caused a shutdown."""

    def __str__(
        self,
    ) -> str:
        return (
            f"{self.__class__.__name__}: shutdown"
            if self.value == 1
            else f"{self.__class__.__name__}: not shutdown"
        )

    NO_SHUTDOWN = 0
    SHUTDOWN = 1


APPROPRIATIONS_GAPS: "AppropriationsGapsMapType" = {
    (2465, 2474): (
        DEPTS_SET.difference(
            {
                Dept.DOI,
                Dept.DOE,
                Dept.DHS,
                Dept.DOJ,
                Dept.DOC,
                Dept.DOT,
                Dept.USDA,
                Dept.USDT,
                Dept.VA,
                Dept.HUD,
                Dept.DOD,
                Dept.PRES,
                Dept.IA,
                Dept.DOS,
            }
        ),
        ShutdownFlag.NO_SHUTDOWN,
    ),
    (2830, 2841): (
        DEPTS_SET.difference(
            {
                Dept.DOI,
                Dept.DOE,
                Dept.DHS,
                Dept.DOJ,
                Dept.DOC,
                Dept.DOT,
                Dept.USDA,
                Dept.USDT,
                Dept.VA,
                Dept.HUD,
                Dept.DOD,
                Dept.PRES,
                Dept.IA,
                Dept.DOS,
            }
        ),
        ShutdownFlag.NO_SHUTDOWN,
    ),
    (2870, 2889): (
        DEPTS_SET.difference(
            {
                Dept.DOI,
                Dept.DOE,
                Dept.DHS,
                Dept.DOJ,
                Dept.DOC,
                Dept.DOT,
                Dept.USDA,
                Dept.USDT,
                Dept.VA,
                Dept.HUD,
                Dept.DOD,
                Dept.PRES,
                Dept.IA,
                Dept.DOS,
            }
        ),
        ShutdownFlag.NO_SHUTDOWN,
    ),
    (3195, 3211): (
        DEPTS_SET.difference(
            {
                Dept.DOI,
                Dept.DOT,
                Dept.USDA,
                Dept.USDT,
                Dept.VA,
                Dept.DOE,
                Dept.HUD,
                Dept.DHS,
                Dept.PRES,
                Dept.IA,
                Dept.DOJ,
                Dept.DOS,
                Dept.DOC,
            }
        ),
        ShutdownFlag.NO_SHUTDOWN,
    ),
    (3560, 3570): (DEPTS_SET.difference({Dept.DHS}), ShutdownFlag.NO_SHUTDOWN),
    (4342, 4342): (DEPTS_SET.difference({Dept.DHS}), ShutdownFlag.SHUTDOWN),
    (4734, 4736): (DEPTS_SET.difference({Dept.DHS}), ShutdownFlag.NO_SHUTDOWN),
    (5062, 5064): (DEPTS_SET.difference({Dept.DHS}), ShutdownFlag.NO_SHUTDOWN),
    (5390, 5401): (
        DEPTS_SET.difference(
            {
                Dept.DOI,
                Dept.DOL,
                Dept.DOD,
                Dept.HHS,
                Dept.DOT,
                Dept.USDA,
                Dept.USDT,
                Dept.ED,
                Dept.VA,
                Dept.DOE,
                Dept.PRES,
                Dept.DHS,
                Dept.DOC,
            }
        ),
        ShutdownFlag.SHUTDOWN,
    ),
    (6133, 6133): (DEPTS_SET.difference({Dept.DHS}), ShutdownFlag.SHUTDOWN),
    (6561, 6561): (DEPTS_SET.difference({Dept.DHS}), ShutdownFlag.NO_SHUTDOWN),
    (7583, 7585): (DEPTS_SET.difference({Dept.DHS}), ShutdownFlag.NO_SHUTDOWN),
    (9448, 9452): (
        DEPTS_SET.difference({Dept.USDA, Dept.DOE, Dept.DHS}),
        ShutdownFlag.SHUTDOWN,
    ),
    (9480, 9500): (
        DEPTS_SET.difference({Dept.USDA, Dept.USDT, Dept.DHS, Dept.DOE, Dept.DOD}),
        ShutdownFlag.SHUTDOWN,
    ),
    (15979, 15994): (DEPTS_SET, ShutdownFlag.SHUTDOWN),
    (17552, 17552): (DEPTS_SET, ShutdownFlag.SHUTDOWN),
    (17887, 17936): (
        DEPTS_SET.difference(
            {Dept.DOL, Dept.HHS, Dept.ED, Dept.VA, Dept.DOE, Dept.DOD}
        ),
        ShutdownFlag.SHUTDOWN,
    ),
}
# (3773, 3773): ({"Federal Trade Commission"}, ShutdownFlag.
# SHUTDOWN), for now, we omit FTC since it is not a Department-level entity;
# agency-level data is on the to-do list
"""
APPROPRIATIONS_GAPS:
A mapping of federal appropriations gaps. Each key is a tuple of the for
(integer start date in unix timestamp), (integer end date in unix timestamp)
({set of affected agencies}, Tuple of AppropsStatus, OpsStatus enum
objects)

Two 2020 appropriations gaps are not included because they lasted less than a
day and had no substantial impact on government operations.
"""


CR_DATA_CUTOFF_DATE: int = 10227

"""
CR_DATA_CUTOFF_DATE: POSIX-day date of the beginning of the data cutoff period.
Current cutoff is 1 October 1998, CR data is not currently in fedcal for
any time before this.
"""

CR_DEPARTMENTS: "CRMapType" = {
    (10500, 10506): set(),
    (10507, 10516): {Dept.DOE},
    (10517, 10520): {Dept.DOE, Dept.DOD},
    (10865, 10873): {Dept.USDT, Dept.DOE},
    (10874, 10884): {Dept.USDT, Dept.DOE, Dept.DOT},
    (10885, 10885): {Dept.HUD, Dept.DOT, Dept.USDT, Dept.VA, Dept.DOE},
    (10887, 10889): {Dept.USDA, Dept.HUD, Dept.DOT, Dept.USDT, Dept.VA, Dept.DOE},
    (10890, 10924): {
        Dept.DOD,
        Dept.USDA,
        Dept.HUD,
        Dept.DOT,
        Dept.USDT,
        Dept.VA,
        Dept.DOE,
    },
    (11231, 11241): {Dept.DOD},
    (11242, 11253): {Dept.DOE, Dept.DOI, Dept.DOD, Dept.DOT},
    (11254, 11257): {Dept.DOD, Dept.HUD, Dept.DOT, Dept.VA, Dept.DOE, Dept.DOI},
    (11258, 11267): {
        Dept.DOD,
        Dept.USDA,
        Dept.HUD,
        Dept.DOT,
        Dept.VA,
        Dept.DOE,
        Dept.DOI,
    },
    (11268, 11312): {
        Dept.DOD,
        Dept.DOE,
        Dept.USDA,
        Dept.HUD,
        Dept.DOT,
        Dept.VA,
        Dept.DOS,
        Dept.DOI,
    },
    (11596, 11631): set(),
    (11632, 11638): {Dept.DOI},
    (11639, 11652): {Dept.USDT, Dept.DOI, Dept.DOE},
    (11653, 11653): {Dept.HUD, Dept.USDT, Dept.VA, Dept.DOE, Dept.DOI},
    (11655, 11674): {
        Dept.DOE,
        Dept.DOC,
        Dept.USDA,
        Dept.HUD,
        Dept.USDT,
        Dept.VA,
        Dept.DOS,
        Dept.DOJ,
        Dept.DOI,
    },
    (11675, 11697): {
        Dept.DOE,
        Dept.DOC,
        Dept.USDA,
        Dept.HUD,
        Dept.DOT,
        Dept.USDT,
        Dept.VA,
        Dept.DOS,
        Dept.DOJ,
        Dept.DOI,
    },
    (11961, 11982): set(),
    (11983, 12016): {Dept.DOD},
    (11983, 12103): {Dept.DOD},
    (12016, 12103): {Dept.DOD},
    (12326, 12366): {Dept.DHS, Dept.DOD},
    (12367, 12387): {Dept.DHS, Dept.DOI, Dept.DOD},
    (12388, 12440): {Dept.DHS, Dept.DOE, Dept.DOI, Dept.DOD},
    (12692, 12709): {Dept.DOD},
    (12710, 12760): {Dept.DHS, Dept.DOD},
    (13057, 13074): {Dept.DOI},
    (13075, 13097): {Dept.DHS, Dept.DOI},
    (13098, 13101): {Dept.DHS, Dept.DOI, Dept.USDA},
    (13102, 13106): {Dept.DHS, Dept.DOS, Dept.DOI, Dept.USDA},
    (13107, 13109): {Dept.DOE, Dept.USDA, Dept.DHS, Dept.DOS, Dept.DOI},
    (13110, 13117): {
        Dept.DOE,
        Dept.DOC,
        Dept.USDA,
        Dept.DHS,
        Dept.DOS,
        Dept.DOJ,
        Dept.DOI,
    },
    (13118, 13147): {
        Dept.DOE,
        Dept.DOC,
        Dept.USDA,
        Dept.HUD,
        Dept.DOT,
        Dept.DHS,
        Dept.USDT,
        Dept.VA,
        Dept.DOS,
        Dept.DOJ,
        Dept.DOI,
    },
    (13422, 13425): {Dept.DOD},
    (13426, 13786): {Dept.DHS, Dept.DOD},
    (13787, 13830): set(),
    (13831, 13873): {Dept.DOD},
    (14153, 14314): {Dept.DHS, Dept.DOD, Dept.VA},
    (14518, 14538): set(),
    (14539, 14545): {Dept.USDA},
    (14546, 14546): {Dept.DHS, Dept.DOE, Dept.USDA},
    (14548, 14596): {Dept.DHS, Dept.DOE, Dept.DOI, Dept.USDA},
    (14597, 14597): {
        Dept.DOL,
        Dept.DOE,
        Dept.DOC,
        Dept.USDA,
        Dept.IA,
        Dept.HUD,
        Dept.ED,
        Dept.DOT,
        Dept.DHS,
        Dept.USDT,
        Dept.PRES,
        Dept.VA,
        Dept.DOS,
        Dept.DOJ,
        Dept.DOI,
    },
    (14883, 15079): set(),
    (14883, 15296): set(),
    (15297, 15331): {Dept.USDA, Dept.DOC, Dept.HUD, Dept.DOT, Dept.DOJ},
    (15614, 15790): set(),
    (15791, 15978): {Dept.DOD, Dept.DOC, Dept.USDA, Dept.DHS, Dept.VA, Dept.DOJ},
    (15995, 16087): set(),
    (16344, 16420): set(),
    (16421, 16498): {
        Dept.DOL,
        Dept.DOD,
        Dept.DOE,
        Dept.DOC,
        Dept.USDA,
        Dept.HUD,
        Dept.IA,
        Dept.ED,
        Dept.DOT,
        Dept.USDT,
        Dept.PRES,
        Dept.VA,
        Dept.DOS,
        Dept.DOJ,
        Dept.DOI,
    },
    (16709, 16787): set(),
    (17075, 17291): {Dept.VA},
    (17440, 17551): set(),
    (17553, 17613): set(),
    (17805, 17886): {Dept.DOL, Dept.DOD, Dept.ED, Dept.VA, Dept.HHS, Dept.DOE},
    (17937, 17942): {Dept.DOL, Dept.DOD, Dept.ED, Dept.VA, Dept.HHS, Dept.DOE},
    (18170, 18250): set(),
    (18536, 18623): set(),
    (18901, 19066): set(),
    (19266, 19355): set(),
    (19631, 19741): set(),
}
"""
CR_DEPARTMENTS: A mapping of arguments that craft the continuing resolution
calendar. Current data begin with FY99. Each key is a tuple of unix
timestamp for the start and end of the time interval. **Intervals represent
periods where there were no changes in affected agencies.**

**Each value is a set of UNAFFECTED departments as Dept enum
objects, which will be subtracted from the set of executive departments for
the period. Consequently, an empty set indicates all executive departments
were affected.**

This format allows optimal input into our interval tree, which we use for
time-series queries.
"""
