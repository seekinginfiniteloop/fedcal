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
from typing import TYPE_CHECKING

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
    def from_abbreviation(cls, abbreviation: str) -> Dept:
        """
        Converts an abbreviation of a department to an enum object.
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
        >>> Dept.from_abbreviation("DoI")
        Dept.DOI
        """
        for dept in cls:
            if dept.abbrev == abbreviation:
                return dept
        raise ValueError(f"Department with abbreviation {abbreviation} not found")


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


@unique
class AppropsStatus(Enum):
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
class OpsStatus(Enum):
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
objects. Data currently omit judiciary and legislative budgets (federal courts and Congress).
"""

DHS_FORMED: int = 1038200400
"""DHS_FORMED: POSIX date of DHS formation (2003-11-25)"""


STATUS_MAP: "StatusMapType" = {
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


class ShutdownFlag(Enum):
    """ShutdownFlag: An enum object denoting whether an appropriations gap
    caused a shutdown."""

    NO_SHUTDOWN = 0
    SHUTDOWN = 1


APPROPRIATIONS_GAPS: "AppropriationsGapsMapType" = {
    (212990400, 213768000): ({Dept.HHS, Dept.DOL, Dept.ED}, ShutdownFlag.NO_SHUTDOWN),
    (244526400, 245476800): ({Dept.HHS, Dept.DOL, Dept.ED}, ShutdownFlag.NO_SHUTDOWN),
    (247986000, 249627600): ({Dept.HHS, Dept.DOL, Dept.ED}, ShutdownFlag.NO_SHUTDOWN),
    (276062400, 277444800): (
        {Dept.HHS, Dept.DOL, Dept.DOD, Dept.ED},
        ShutdownFlag.NO_SHUTDOWN,
    ),
    (307598400, 308462400): (
        DEPTS_SET.difference({Dept.DHS}),
        ShutdownFlag.NO_SHUTDOWN,
    ),
    (375166800, 375166800): (
        DEPTS_SET.difference({Dept.DHS}),
        ShutdownFlag.SHUTDOWN,
    ),
    (409035600, 409208400): (
        DEPTS_SET.difference({Dept.DHS}),
        ShutdownFlag.NO_SHUTDOWN,
    ),
    (437374800, 437547600): (
        DEPTS_SET.difference({Dept.DHS}),
        ShutdownFlag.NO_SHUTDOWN,
    ),
    (465710400, 466660800): (
        {Dept.DOJ, Dept.DOS, Dept.HUD, Dept.IA},
        ShutdownFlag.SHUTDOWN,
    ),
    (529905600, 529905600): (
        DEPTS_SET.difference({Dept.DHS}),
        ShutdownFlag.SHUTDOWN,
    ),
    (566888400, 566888400): (
        DEPTS_SET.difference({Dept.DHS}),
        ShutdownFlag.NO_SHUTDOWN,
    ),
    (655185600, 655358400): (
        DEPTS_SET.difference({Dept.DHS}),
        ShutdownFlag.NO_SHUTDOWN,
    ),
    (816325200, 816670800): (
        DEPTS_SET.difference({Dept.DHS, Dept.DOE, Dept.USDA}),
        ShutdownFlag.SHUTDOWN,
    ),
    (819090000, 820818000): (
        DEPTS_SET.difference({Dept.DHS, Dept.DOE, Dept.USDA, Dept.DOD, Dept.USDT}),
        ShutdownFlag.SHUTDOWN,
    ),
    (1380600000, 1381896000): (
        DEPTS_SET,
        ShutdownFlag.SHUTDOWN,
    ),
    (1516510800, 1516510800): (
        DEPTS_SET,
        ShutdownFlag.SHUTDOWN,
    ),
    (1545454800, 1549688400): (
        DEPTS_SET.difference(
            {
                Dept.DOD,
                Dept.DOL,
                Dept.HHS,
                Dept.ED,
                Dept.VA,
                Dept.DOE,
            }
        ),
        ShutdownFlag.SHUTDOWN,
    ),
}
# (326001600, 326001600): ({"Federal Trade Commission"}, ShutdownFlag.
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


CR_DATA_CUTOFF_DATE: int = 883630800

"""
CR_DATA_CUTOFF_DATE: POSIX date of the beginning of the data cutoff period.
Current cutoff is 1 October 1998, CR data is not currently in fedcal for
any time before this.
"""

CR_DEPARTMENTS: "CRMapType" = {
    (907214400, 907732800): set(),
    (907819200, 908596800): {Dept.DOE},
    (908683200, 908942400): {Dept.DOD, Dept.DOE},
    (938750400, 939441600): {Dept.USDT, Dept.DOE},
    (939528000, 940392000): {Dept.USDT, Dept.DOE, Dept.DOT},
    (940478400, 940478400): {
        Dept.VA,
        Dept.HUD,
        Dept.USDT,
        Dept.DOE,
        Dept.DOT,
    },
    (940651200, 940824000): {
        Dept.USDT,
        Dept.DOE,
        Dept.HUD,
        Dept.VA,
        Dept.DOT,
        Dept.USDA,
    },
    (940910400, 943851600): {
        Dept.USDT,
        Dept.DOE,
        Dept.DOD,
        Dept.HUD,
        Dept.VA,
        Dept.DOT,
        Dept.USDA,
    },
    (970372800, 971236800): {Dept.DOD},
    (971323200, 972273600): {Dept.DOD, Dept.DOT, Dept.DOE, Dept.DOI},
    (972360000, 972619200): {
        Dept.DOD,
        Dept.DOE,
        Dept.DOI,
        Dept.HUD,
        Dept.VA,
        Dept.DOT,
    },
    (972705600, 973486800): {
        Dept.DOD,
        Dept.DOE,
        Dept.DOI,
        Dept.HUD,
        Dept.VA,
        Dept.DOT,
        Dept.USDA,
    },
    (973573200, 977374800): {
        Dept.DOD,
        Dept.DOE,
        Dept.DOI,
        Dept.DOS,
        Dept.HUD,
        Dept.VA,
        Dept.DOT,
        Dept.USDA,
    },
    (1001908800, 1004936400): set(),
    (1005022800, 1005541200): {Dept.DOI},
    (1005627600, 1006750800): {Dept.USDT, Dept.DOI, Dept.DOE},
    (1006837200, 1006837200): {
        Dept.VA,
        Dept.USDT,
        Dept.HUD,
        Dept.DOI,
        Dept.DOE,
    },
    (1007010000, 1008651600): {
        Dept.DOC,
        Dept.DOJ,
        Dept.DOI,
        Dept.USDT,
        Dept.DOS,
        Dept.HUD,
        Dept.VA,
        Dept.USDA,
        Dept.DOE,
    },
    (1008738000, 1010638800): {
        Dept.DOC,
        Dept.DOJ,
        Dept.DOT,
        Dept.DOI,
        Dept.USDT,
        Dept.DOS,
        Dept.HUD,
        Dept.VA,
        Dept.USDA,
        Dept.DOE,
    },
    (1033444800, 1035259200): set(),
    (1035345600, 1038200400): {Dept.DOD},
    (1035345600, 1045717200): {Dept.DOD},
    (1038200400, 1045717200): {Dept.DOD},
    (1064980800, 1068440400): {Dept.DHS, Dept.DOD},
    (1068526800, 1070254800): {Dept.DHS, Dept.DOI, Dept.DOD},
    (1070341200, 1074834000): {Dept.DHS, Dept.DOI, Dept.DOD, Dept.DOE},
    (1096603200, 1098072000): {Dept.DOD},
    (1098158400, 1102482000): {Dept.DHS, Dept.DOD},
    (1128139200, 1129608000): {Dept.DOI},
    (1129694400, 1131598800): {Dept.DHS, Dept.DOI},
    (1131685200, 1131944400): {Dept.DHS, Dept.DOI, Dept.USDA},
    (1132030800, 1132376400): {Dept.DHS, Dept.DOI, Dept.DOS, Dept.USDA},
    (1132462800, 1132635600): {
        Dept.DHS,
        Dept.DOS,
        Dept.DOI,
        Dept.USDA,
        Dept.DOE,
    },
    (1132722000, 1133326800): {
        Dept.DHS,
        Dept.DOS,
        Dept.DOC,
        Dept.DOJ,
        Dept.DOI,
        Dept.USDA,
        Dept.DOE,
    },
    (1133413200, 1135918800): {
        Dept.DHS,
        Dept.DOC,
        Dept.DOT,
        Dept.DOI,
        Dept.USDT,
        Dept.VA,
        Dept.DOS,
        Dept.HUD,
        Dept.DOJ,
        Dept.USDA,
        Dept.DOE,
    },
    (1159675200, 1159934400): {Dept.DOD},
    (1160020800, 1191124800): {Dept.DHS, Dept.DOD},
    (1191211200, 1194930000): set(),
    (1195016400, 1198645200): {Dept.DOD},
    (1222833600, 1236744000): {Dept.VA, Dept.DHS, Dept.DOD},
    (1254369600, 1256097600): set(),
    (1256184000, 1256702400): {Dept.USDA},
    (1256788800, 1256788800): {Dept.DHS, Dept.USDA, Dept.DOE},
    (1256961600, 1261112400): {
        Dept.DOI,
        Dept.DHS,
        Dept.USDA,
        Dept.DOE,
    },
    (1261198800, 1261198800): {
        Dept.DOL,
        Dept.DHS,
        Dept.DOC,
        Dept.DOJ,
        Dept.IA,
        Dept.DOT,
        Dept.PRES,
        Dept.USDT,
        Dept.VA,
        Dept.DOS,
        Dept.ED,
        Dept.HUD,
        Dept.DOI,
        Dept.USDA,
        Dept.DOE,
    },
    (1285905600, 1302840000): set(),
    (1285905600, 1321592400): set(),
    (1321678800, 1324616400): {
        Dept.DOC,
        Dept.HUD,
        Dept.DOJ,
        Dept.DOT,
        Dept.USDA,
    },
    (1349064000, 1364270400): set(),
    (1364356800, 1380513600): {
        Dept.VA,
        Dept.DOD,
        Dept.DHS,
        Dept.DOC,
        Dept.DOJ,
        Dept.USDA,
    },
    (1381982400, 1389934800): set(),
    (1412136000, 1418706000): set(),
    (1418792400, 1425445200): {
        Dept.DOL,
        Dept.DOD,
        Dept.DOC,
        Dept.DOT,
        Dept.PRES,
        Dept.USDT,
        Dept.VA,
        Dept.DOI,
        Dept.DOS,
        Dept.ED,
        Dept.USDA,
        Dept.HUD,
        Dept.DOJ,
        Dept.IA,
        Dept.DOE,
    },
    (1443672000, 1450414800): set(),
    (1475294400, 1493956800): {Dept.VA},
    (1506830400, 1516424400): set(),
    (1516597200, 1521777600): set(),
    (1538366400, 1545368400): {
        Dept.VA,
        Dept.DOL,
        Dept.DOD,
        Dept.ED,
        Dept.HHS,
        Dept.DOE,
    },
    (1549774800, 1550206800): {
        Dept.VA,
        Dept.DOL,
        Dept.DOD,
        Dept.ED,
        Dept.HHS,
        Dept.DOE,
    },
    (1569902400, 1576818000): set(),
    (1601524800, 1609045200): set(),
    (1633060800, 1647316800): set(),
    (1664596800, 1672290000): set(),
    (1696132800, 1705640400): set(),
}

"""
CR_DEPARTMENTS: A mapping of arguments that craft the continuing resolution
calendar. Current data begin with FY99. Each key is a tuple of unix
timestamps for the start and end of the time interval. **Intervals represent
periods where there were no changes in affected agencies.**

**Each value is a set of UNAFFECTED departments as Dept enum
objects, which will be subtracted from the set of executive departments for
the period. Consequently, an empty set indicates all executive departments
were affected.**

This format allows optimal input into our interval tree, which we use for
time-series queries.
"""
