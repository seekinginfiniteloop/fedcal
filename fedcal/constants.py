# constants.py
from __future__ import annotations

from enum import Enum, unique
from typing import TYPE_CHECKING

from bidict import bidict
from pandas import Timestamp

if TYPE_CHECKING:
    from ._typing import (
        AppropriationsGapsMapType,
        CRMapType,
        StatusMapType,
        StatusTupleType,
    )

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


@unique
class EXECUTIVE_DEPARTMENT(Enum):
    def __init__(self, abbreviation: str, full_name: str, short_name: str) -> None:
        """
        Initializes an instance of EXECUTIVE_DEPARTMENT, an enum for storing
        constants of federal executive branch departments.

        Args:
            abbreviation (str): The mixed case abbreviation of the department.
            full_name (str): The full name of the department in mixed case.
            short_name (str): The shortened name of the department in mix case.
        """
        self.ABBREV: str = abbreviation  # mixed case abbreviation
        self.FULL: str = full_name  # full name in mixed case
        self.SHORT: str = short_name  # shortened name in mixed case

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
    def from_short_name(cls, short_name: str) -> EXECUTIVE_DEPARTMENT:
        for dept in cls:
            if dept.SHORT == short_name:
                return dept
        raise ValueError(f"Department with short name {short_name} not found")

    @classmethod
    def from_long_name(cls, long_name: str) -> EXECUTIVE_DEPARTMENT:
        for dept in cls:
            if dept.FULL == long_name:
                return dept
        raise ValueError(f"Department with long name {long_name} not found")

    @classmethod
    def from_abbreviation(cls, abbreviation: str) -> EXECUTIVE_DEPARTMENT:
        for dept in cls:
            if dept.ABBREV == abbreviation:
                return dept
        raise ValueError(f"Department with abbreviation {abbreviation} not found")


DEPT = EXECUTIVE_DEPARTMENT
"""We shorten EXECUTIVE_DEPARTMENT for brevity."""


HISTORICAL_HOLIDAYS_BY_PROCLAMATION: list[Timestamp] = [
    Timestamp(year=2020, month=12, day=24),
    Timestamp(year=2019, month=12, day=24),
    Timestamp(year=2018, month=12, day=24),
    Timestamp(year=2015, month=12, day=24),
    Timestamp(year=2014, month=12, day=26),
    Timestamp(year=2012, month=12, day=24),
    Timestamp(year=2007, month=12, day=24),
    Timestamp(year=2001, month=12, day=24),
    Timestamp(year=1979, month=12, day=24),
    Timestamp(year=1973, month=12, day=31),
    Timestamp(year=1973, month=12, day=24),
]

"""
HISTORICAL_PROCLAMATION_HOLIDAYS:
A list of Timestamps for historical days where the President proclaimed an
out-of-cycle holiday, usually for Christmas Eve.
Source: FederalTimes
"""

FEDPAYDAY_REFERENCE_DATE = Timestamp(year=1969, month=12, day=19)
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
class FUNDING_STATUS(Enum):
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
class OPERATIONAL_STATUS(Enum):
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


EXECUTIVE_DEPARTMENTS_SET: set[EXECUTIVE_DEPARTMENT] = {
    DEPT.DHS,
    DEPT.DOC,
    DEPT.DOD,
    DEPT.DOE,
    DEPT.DOI,
    DEPT.DOJ,
    DEPT.DOL,
    DEPT.DOS,
    DEPT.DOT,
    DEPT.ED,
    DEPT.HHS,
    DEPT.HUD,
    DEPT.IA,
    DEPT.PRES,
    DEPT.USDA,
    DEPT.USDT,
    DEPT.VA,
}

"""
EXECUTIVE_DEPARTMENTS_SET: A set of top-level executive departments as enum
objects. Data currently omit judiciary and legislative budgets (federal courts and Congress).
"""

DHS_FORMED: int = 1038200400
"""DHS_FORMED: POSIX date of DHS formation (2003-11-25)"""


STATUS_MAP: "StatusMapType" = {
    "DEFAULT_STATUS": (FUNDING_STATUS.FULLY_APPROPRIATED, OPERATIONAL_STATUS.OPEN),
    "CR_STATUS": (
        FUNDING_STATUS.TEMPORARILY_APPROPRIATED,
        OPERATIONAL_STATUS.OPEN_WITH_LIMITATIONS,
    ),
    "CR_DATA_CUTOFF_DEFAULT_STATUS": (
        FUNDING_STATUS.FULLY_OR_TEMPORARILY_APPROPRIATED,
        OPERATIONAL_STATUS.OPEN_OR_OPEN_WITH_LIMITATIONS,
    ),
    "GAP_STATUS": (FUNDING_STATUS.NO_APPROPRIATIONS, OPERATIONAL_STATUS.MINIMALLY_OPEN),
    "SHUTDOWN_STATUS": (FUNDING_STATUS.NO_APPROPRIATIONS, OPERATIONAL_STATUS.SHUTDOWN),
    "FUTURE_STATUS": (FUNDING_STATUS.FUTURE, OPERATIONAL_STATUS.FUTURE),
}

"""
STATUS_MAP: We map possible FUNDING_STATUS, OPERATIONAL_STATUS combinations to string descriptions so we can simplify manipulations _dept_status.py.
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
FedDateIndex behavior of outputing human-readable status.
"""

READABLE_STATUS_MAP: bidict["StatusTupleType", str] = bidict(
    (value for value in STATUS_MAP.values()), (item for item in READABLE_STATUSES)
)

"""
READABLE_STATUS_MAP: A bidict mapping human-readable statuses to their enum
status tuples (FUNDING_STATUS, OPERATIONAL_STATUS). We use this for
FedDepartments' .status property and for converting FedDateIndex
human-readable statuses to more detailed output for power users.
"""


class SHUTDOWN_FLAG(Enum):
    """SHUTDOWN_FLAG: An enum object denoting whether an appropriations gap
    caused a shutdown."""

    NO_SHUTDOWN = 0
    SHUTDOWN = 1


APPROPRIATIONS_GAPS: "AppropriationsGapsMapType" = {
    (212990400, 213768000): ({DEPT.HHS, DEPT.DOL, DEPT.ED}, SHUTDOWN_FLAG.NO_SHUTDOWN),
    (244526400, 245476800): ({DEPT.HHS, DEPT.DOL, DEPT.ED}, SHUTDOWN_FLAG.NO_SHUTDOWN),
    (247986000, 249627600): ({DEPT.HHS, DEPT.DOL, DEPT.ED}, SHUTDOWN_FLAG.NO_SHUTDOWN),
    (276062400, 277444800): (
        {DEPT.HHS, DEPT.DOL, DEPT.DOD, DEPT.ED},
        SHUTDOWN_FLAG.NO_SHUTDOWN,
    ),
    (307598400, 308462400): (
        EXECUTIVE_DEPARTMENTS_SET.difference({DEPT.DHS}),
        SHUTDOWN_FLAG.NO_SHUTDOWN,
    ),
    (375166800, 375166800): (
        EXECUTIVE_DEPARTMENTS_SET.difference({DEPT.DHS}),
        SHUTDOWN_FLAG.SHUTDOWN,
    ),
    (409035600, 409208400): (
        EXECUTIVE_DEPARTMENTS_SET.difference({DEPT.DHS}),
        SHUTDOWN_FLAG.NO_SHUTDOWN,
    ),
    (437374800, 437547600): (
        EXECUTIVE_DEPARTMENTS_SET.difference({DEPT.DHS}),
        SHUTDOWN_FLAG.NO_SHUTDOWN,
    ),
    (465710400, 466660800): (
        {DEPT.DOJ, DEPT.DOS, DEPT.HUD, DEPT.IA},
        SHUTDOWN_FLAG.SHUTDOWN,
    ),
    (529905600, 529905600): (
        EXECUTIVE_DEPARTMENTS_SET.difference({DEPT.DHS}),
        SHUTDOWN_FLAG.SHUTDOWN,
    ),
    (566888400, 566888400): (
        EXECUTIVE_DEPARTMENTS_SET.difference({DEPT.DHS}),
        SHUTDOWN_FLAG.NO_SHUTDOWN,
    ),
    (655185600, 655358400): (
        EXECUTIVE_DEPARTMENTS_SET.difference({DEPT.DHS}),
        SHUTDOWN_FLAG.NO_SHUTDOWN,
    ),
    (816325200, 816670800): (
        EXECUTIVE_DEPARTMENTS_SET.difference({DEPT.DHS, DEPT.DOE, DEPT.USDA}),
        SHUTDOWN_FLAG.SHUTDOWN,
    ),
    (819090000, 820818000): (
        EXECUTIVE_DEPARTMENTS_SET.difference(
            {DEPT.DHS, DEPT.DOE, DEPT.USDA, DEPT.DOD, DEPT.USDT}
        ),
        SHUTDOWN_FLAG.SHUTDOWN,
    ),
    (1380600000, 1381896000): (
        EXECUTIVE_DEPARTMENTS_SET,
        SHUTDOWN_FLAG.SHUTDOWN,
    ),
    (1516510800, 1516510800): (
        EXECUTIVE_DEPARTMENTS_SET,
        SHUTDOWN_FLAG.SHUTDOWN,
    ),
    (1545454800, 1549688400): (
        EXECUTIVE_DEPARTMENTS_SET.difference(
            {
                DEPT.DOD,
                DEPT.DOL,
                DEPT.HHS,
                DEPT.ED,
                DEPT.VA,
                DEPT.DOE,
            }
        ),
        SHUTDOWN_FLAG.SHUTDOWN,
    ),
}
# (326001600, 326001600): ({"Federal Trade Commission"}, SHUTDOWN_FLAG.
# SHUTDOWN), for now, we omit FTC since it is not a Department-level entity;
# agency-level data is on the to-do list
"""
APPROPRIATIONS_GAPS:
A mapping of federal appropriations gaps. Each key is a tuple of the for
(integer start date in unix timestamp), (integer end date in unix timestamp)
({set of affected agencies}, Tuple of FUNDING_STATUS, OPERATIONAL_STATUS enum
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
    (907819200, 908596800): {DEPT.DOE},
    (908683200, 908942400): {DEPT.DOD, DEPT.DOE},
    (938750400, 939441600): {DEPT.USDT, DEPT.DOE},
    (939528000, 940392000): {DEPT.USDT, DEPT.DOE, DEPT.DOT},
    (940478400, 940478400): {
        DEPT.VA,
        DEPT.HUD,
        DEPT.USDT,
        DEPT.DOE,
        DEPT.DOT,
    },
    (940651200, 940824000): {
        DEPT.USDT,
        DEPT.DOE,
        DEPT.HUD,
        DEPT.VA,
        DEPT.DOT,
        DEPT.USDA,
    },
    (940910400, 943851600): {
        DEPT.USDT,
        DEPT.DOE,
        DEPT.DOD,
        DEPT.HUD,
        DEPT.VA,
        DEPT.DOT,
        DEPT.USDA,
    },
    (970372800, 971236800): {DEPT.DOD},
    (971323200, 972273600): {DEPT.DOD, DEPT.DOT, DEPT.DOE, DEPT.DOI},
    (972360000, 972619200): {
        DEPT.DOD,
        DEPT.DOE,
        DEPT.DOI,
        DEPT.HUD,
        DEPT.VA,
        DEPT.DOT,
    },
    (972705600, 973486800): {
        DEPT.DOD,
        DEPT.DOE,
        DEPT.DOI,
        DEPT.HUD,
        DEPT.VA,
        DEPT.DOT,
        DEPT.USDA,
    },
    (973573200, 977374800): {
        DEPT.DOD,
        DEPT.DOE,
        DEPT.DOI,
        DEPT.DOS,
        DEPT.HUD,
        DEPT.VA,
        DEPT.DOT,
        DEPT.USDA,
    },
    (1001908800, 1004936400): set(),
    (1005022800, 1005541200): {DEPT.DOI},
    (1005627600, 1006750800): {DEPT.USDT, DEPT.DOI, DEPT.DOE},
    (1006837200, 1006837200): {
        DEPT.VA,
        DEPT.USDT,
        DEPT.HUD,
        DEPT.DOI,
        DEPT.DOE,
    },
    (1007010000, 1008651600): {
        DEPT.DOC,
        DEPT.DOJ,
        DEPT.DOI,
        DEPT.USDT,
        DEPT.DOS,
        DEPT.HUD,
        DEPT.VA,
        DEPT.USDA,
        DEPT.DOE,
    },
    (1008738000, 1010638800): {
        DEPT.DOC,
        DEPT.DOJ,
        DEPT.DOT,
        DEPT.DOI,
        DEPT.USDT,
        DEPT.DOS,
        DEPT.HUD,
        DEPT.VA,
        DEPT.USDA,
        DEPT.DOE,
    },
    (1033444800, 1035259200): set(),
    (1035345600, 1038200400): {DEPT.DOD},
    (1035345600, 1045717200): {DEPT.DOD},
    (1038200400, 1045717200): {DEPT.DOD},
    (1064980800, 1068440400): {DEPT.DHS, DEPT.DOD},
    (1068526800, 1070254800): {DEPT.DHS, DEPT.DOI, DEPT.DOD},
    (1070341200, 1074834000): {DEPT.DHS, DEPT.DOI, DEPT.DOD, DEPT.DOE},
    (1096603200, 1098072000): {DEPT.DOD},
    (1098158400, 1102482000): {DEPT.DHS, DEPT.DOD},
    (1128139200, 1129608000): {DEPT.DOI},
    (1129694400, 1131598800): {DEPT.DHS, DEPT.DOI},
    (1131685200, 1131944400): {DEPT.DHS, DEPT.DOI, DEPT.USDA},
    (1132030800, 1132376400): {DEPT.DHS, DEPT.DOI, DEPT.DOS, DEPT.USDA},
    (1132462800, 1132635600): {
        DEPT.DHS,
        DEPT.DOS,
        DEPT.DOI,
        DEPT.USDA,
        DEPT.DOE,
    },
    (1132722000, 1133326800): {
        DEPT.DHS,
        DEPT.DOS,
        DEPT.DOC,
        DEPT.DOJ,
        DEPT.DOI,
        DEPT.USDA,
        DEPT.DOE,
    },
    (1133413200, 1135918800): {
        DEPT.DHS,
        DEPT.DOC,
        DEPT.DOT,
        DEPT.DOI,
        DEPT.USDT,
        DEPT.VA,
        DEPT.DOS,
        DEPT.HUD,
        DEPT.DOJ,
        DEPT.USDA,
        DEPT.DOE,
    },
    (1159675200, 1159934400): {DEPT.DOD},
    (1160020800, 1191124800): {DEPT.DHS, DEPT.DOD},
    (1191211200, 1194930000): set(),
    (1195016400, 1198645200): {DEPT.DOD},
    (1222833600, 1236744000): {DEPT.VA, DEPT.DHS, DEPT.DOD},
    (1254369600, 1256097600): set(),
    (1256184000, 1256702400): {DEPT.USDA},
    (1256788800, 1256788800): {DEPT.DHS, DEPT.USDA, DEPT.DOE},
    (1256961600, 1261112400): {
        DEPT.DOI,
        DEPT.DHS,
        DEPT.USDA,
        DEPT.DOE,
    },
    (1261198800, 1261198800): {
        DEPT.DOL,
        DEPT.DHS,
        DEPT.DOC,
        DEPT.DOJ,
        DEPT.IA,
        DEPT.DOT,
        DEPT.PRES,
        DEPT.USDT,
        DEPT.VA,
        DEPT.DOS,
        DEPT.ED,
        DEPT.HUD,
        DEPT.DOI,
        DEPT.USDA,
        DEPT.DOE,
    },
    (1285905600, 1302840000): set(),
    (1285905600, 1321592400): set(),
    (1321678800, 1324616400): {
        DEPT.DOC,
        DEPT.HUD,
        DEPT.DOJ,
        DEPT.DOT,
        DEPT.USDA,
    },
    (1349064000, 1364270400): set(),
    (1364356800, 1380513600): {
        DEPT.VA,
        DEPT.DOD,
        DEPT.DHS,
        DEPT.DOC,
        DEPT.DOJ,
        DEPT.USDA,
    },
    (1381982400, 1389934800): set(),
    (1412136000, 1418706000): set(),
    (1418792400, 1425445200): {
        DEPT.DOL,
        DEPT.DOD,
        DEPT.DOC,
        DEPT.DOT,
        DEPT.PRES,
        DEPT.USDT,
        DEPT.VA,
        DEPT.DOI,
        DEPT.DOS,
        DEPT.ED,
        DEPT.USDA,
        DEPT.HUD,
        DEPT.DOJ,
        DEPT.IA,
        DEPT.DOE,
    },
    (1443672000, 1450414800): set(),
    (1475294400, 1493956800): {DEPT.VA},
    (1506830400, 1516424400): set(),
    (1516597200, 1521777600): set(),
    (1538366400, 1545368400): {
        DEPT.VA,
        DEPT.DOL,
        DEPT.DOD,
        DEPT.ED,
        DEPT.HHS,
        DEPT.DOE,
    },
    (1549774800, 1550206800): {
        DEPT.VA,
        DEPT.DOL,
        DEPT.DOD,
        DEPT.ED,
        DEPT.HHS,
        DEPT.DOE,
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

**Each value is a set of UNAFFECTED departments as EXECUTIVE_DEPARTMENT enum
objects, which will be subtracted from the set of executive departments for
the period. Consequently, an empty set indicates all executive departments
were affected.**

This format allows optimal input into our interval tree, which we use for
time-series queries.
"""
