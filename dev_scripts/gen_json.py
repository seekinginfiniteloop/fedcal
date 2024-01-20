# dev script gen_json.py for fedcal
#
# Copyright (c) 2023-2024 Adam Poulemanos. All rights reserved.
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
Generates the JSON used to feed status data for fedcal. This is easier to
maintain. Uses a functional factory to avoid stateful problems in generation.
"""
from __future__ import annotations

import json

from enum import Enum, unique
from typing import Any, Literal, Union

import pandas as pd
from matplotlib.transforms import interval_contains_open
from pandas import Interval, Timestamp


@unique
class Dept(Enum):
    """
    Dept enums represent federal departments and are used throughout fedcal to
    represent departments

    Attributes
    ----------
    abbrev
    full
    short

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

    def __iter__(self):
        yield self.value


depts_set: set[Dept] = {
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
depts_set: A set of top-level executive departments as enum
objects. Data currently omit judiciary and legislative budgets (federal courts
and Congress).
"""

dhs_formed: Timestamp = pd.to_datetime(arg="2002-11-25", format="ISO8601")


@unique
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
    SDN = (0, "shutdown", "no appropriations and shutdown", "shutdown", "shutdown")
    FUT = (
        -1,
        "future_unknown",
        "future status unknown",
        "future status unknown",
        "future",
    )


class ShutdownFlag(Enum):
    """ShutdownFlag: An enum object denoting whether an appropriations gap
    caused a shutdown."""

    def __str__(
        self,
    ) -> str:
        return (
            f"{type(self).__name__}: shutdown"
            if self.value == 1
            else f"{type(self).__name__}: not shutdown"
        )

    NO_SHUTDOWN = 0
    SHUTDOWN = 1


# Note: For APPROPRIATIONS_GAPS and CR_DEPARTMENTS we don't base the intervals
# on bill timelines, but instead times when the departments were/are impacted,
# so if the same set of departments experienced a CR for a given period, even
# if under multiple bills with different expiration dates, it's the same group
# for our purposes. We're concerned with status here, not legislative nuance.

APPROPRIATIONS_GAPS = {
    ("1976-10-01", "1976-10-10"): (
        depts_set.difference(
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
    ("1977-10-01", "1977-10-12"): (
        depts_set.difference(
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
    ("1977-11-10", "1977-11-29"): (
        depts_set.difference(
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
    ("1978-10-01", "1978-10-17"): (
        depts_set.difference(
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
    ("1979-10-01", "1979-10-11"): (
        depts_set.difference({Dept.DHS}),
        ShutdownFlag.NO_SHUTDOWN,
    ),
    ("1981-11-21", "1981-11-21"): (
        depts_set.difference({Dept.DHS}),
        ShutdownFlag.SHUTDOWN,
    ),
    ("1982-12-18", "1982-12-20"): (
        depts_set.difference({Dept.DHS}),
        ShutdownFlag.NO_SHUTDOWN,
    ),
    ("1983-11-11", "1983-11-13"): (
        depts_set.difference({Dept.DHS}),
        ShutdownFlag.NO_SHUTDOWN,
    ),
    ("1984-10-04", "1984-10-15"): (
        depts_set.difference(
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
    ("1986-10-17", "1986-10-17"): (
        depts_set.difference({Dept.DHS}),
        ShutdownFlag.SHUTDOWN,
    ),
    ("1987-12-19", "1987-12-19"): (
        depts_set.difference({Dept.DHS}),
        ShutdownFlag.NO_SHUTDOWN,
    ),
    ("1990-10-06", "1990-10-08"): (
        depts_set.difference({Dept.DHS}),
        ShutdownFlag.NO_SHUTDOWN,
    ),
    ("1995-11-14", "1995-11-18"): (
        depts_set.difference({Dept.USDA, Dept.DOE, Dept.DHS}),
        ShutdownFlag.SHUTDOWN,
    ),
    ("1995-12-16", "1996-01-05"): (
        depts_set.difference({Dept.USDA, Dept.USDT, Dept.DHS, Dept.DOE, Dept.DOD}),
        ShutdownFlag.SHUTDOWN,
    ),
    ("2013-10-01", "2013-10-16"): (depts_set, ShutdownFlag.SHUTDOWN),
    ("2018-01-21", "2018-01-21"): (depts_set, ShutdownFlag.SHUTDOWN),
    ("2018-12-22", "2019-02-09"): (
        depts_set.difference(
            {Dept.DOL, Dept.HHS, Dept.ED, Dept.VA, Dept.DOE, Dept.DOD}
        ),
        ShutdownFlag.SHUTDOWN,
    ),
}
# ("1980-05-01", "1980-05-01"): ({"Federal Trade Commission"}, ShutdownFlag.
# SHUTDOWN), for now, we omit FTC since it is not a Department-level entity;
# agency-level data is on the to-do list
"""
APPROPRIATIONS_GAPS:

A mapping of federal appropriations gaps. Each key is a tuple of ISO 8601
formatted strings for start and end dates. Values for each key are a set of
Dept objects representing *affected* departments, and an enum flag indicating
whether the event was a shutdown or an approps gap without a shutdown.

Two 2020 appropriations gaps are not included because they lasted less
than a day and had no substantial impact on government operations.
"""


cr_data_cutoff: Timestamp = pd.to_datetime(arg="1998-10-01", format="ISO8601")

"""
cr_data_cutoff: POSIX-day date of the beginning of the data cutoff period.
Current cutoff is 1 October 1998, CR data is not currently in fedcal for
any time before this.
"""

CR_DEPARTMENTS = {
    ("1998-10-01", "1998-10-07"): set(),
    ("1998-10-08", "1998-10-17"): {Dept.DOE},
    ("1998-10-18", "1998-10-21"): {Dept.DOE, Dept.DOD},
    ("1999-10-01", "1999-10-09"): {Dept.USDT, Dept.DOE},
    ("1999-10-10", "1999-10-20"): {Dept.USDT, Dept.DOE, Dept.DOT},
    ("1999-10-21", "1999-10-21"): {Dept.HUD, Dept.DOT, Dept.USDT, Dept.VA, Dept.DOE},
    ("1999-10-23", "1999-10-25"): {
        Dept.USDA,
        Dept.HUD,
        Dept.DOT,
        Dept.USDT,
        Dept.VA,
        Dept.DOE,
    },
    ("1999-10-26", "1999-11-29"): {
        Dept.DOD,
        Dept.USDA,
        Dept.HUD,
        Dept.DOT,
        Dept.USDT,
        Dept.VA,
        Dept.DOE,
    },
    ("2000-10-01", "2000-10-11"): {Dept.DOD},
    ("2000-10-12", "2000-10-23"): {Dept.DOE, Dept.DOI, Dept.DOD, Dept.DOT},
    ("2000-10-24", "2000-10-27"): {
        Dept.DOD,
        Dept.HUD,
        Dept.DOT,
        Dept.VA,
        Dept.DOE,
        Dept.DOI,
    },
    ("2000-10-28", "2000-11-06"): {
        Dept.DOD,
        Dept.USDA,
        Dept.HUD,
        Dept.DOT,
        Dept.VA,
        Dept.DOE,
        Dept.DOI,
    },
    ("2000-11-07", "2000-12-21"): {
        Dept.DOD,
        Dept.DOE,
        Dept.USDA,
        Dept.HUD,
        Dept.DOT,
        Dept.VA,
        Dept.DOS,
        Dept.DOI,
    },
    ("2001-10-01", "2001-11-05"): set(),
    ("2001-11-06", "2001-11-12"): {Dept.DOI},
    ("2001-11-13", "2001-11-26"): {Dept.USDT, Dept.DOI, Dept.DOE},
    ("2001-11-27", "2001-11-27"): {Dept.HUD, Dept.USDT, Dept.VA, Dept.DOE, Dept.DOI},
    ("2001-11-29", "2001-12-18"): {
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
    ("2001-12-19", "2002-01-10"): {
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
    ("2002-10-01", "2002-10-22"): set(),
    ("2002-10-23", "2002-11-24"): {Dept.DOD},
    ("2002-11-25", "2003-02-20"): {Dept.DOD},
    ("2003-10-01", "2003-11-10"): {Dept.DHS, Dept.DOD},
    ("2003-11-11", "2003-12-01"): {Dept.DHS, Dept.DOI, Dept.DOD},
    ("2003-12-02", "2004-01-23"): {Dept.DHS, Dept.DOE, Dept.DOI, Dept.DOD},
    ("2004-10-01", "2004-10-18"): {Dept.DOD},
    ("2004-10-19", "2004-12-08"): {Dept.DHS, Dept.DOD},
    ("2005-10-01", "2005-10-18"): {Dept.DOI},
    ("2005-10-19", "2005-11-10"): {Dept.DHS, Dept.DOI},
    ("2005-11-11", "2005-11-14"): {Dept.DHS, Dept.DOI, Dept.USDA},
    ("2005-11-15", "2005-11-19"): {Dept.DHS, Dept.DOS, Dept.DOI, Dept.USDA},
    ("2005-11-20", "2005-11-22"): {Dept.DOE, Dept.USDA, Dept.DHS, Dept.DOS, Dept.DOI},
    ("2005-11-23", "2005-11-30"): {
        Dept.DOE,
        Dept.DOC,
        Dept.USDA,
        Dept.DHS,
        Dept.DOS,
        Dept.DOJ,
        Dept.DOI,
    },
    ("2005-12-01", "2005-12-30"): {
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
    ("2006-10-01", "2006-10-04"): {Dept.DOD},
    ("2006-10-05", "2007-09-30"): {Dept.DHS, Dept.DOD},
    ("2007-10-01", "2007-11-13"): set(),
    ("2007-11-14", "2007-12-26"): {Dept.DOD},
    ("2008-10-01", "2009-03-11"): {Dept.DHS, Dept.DOD, Dept.VA},
    ("2009-10-01", "2009-10-21"): set(),
    ("2009-10-22", "2009-10-28"): {Dept.USDA},
    ("2009-10-29", "2009-10-29"): {Dept.DHS, Dept.DOE, Dept.USDA},
    ("2009-10-31", "2009-12-18"): {Dept.DHS, Dept.DOE, Dept.DOI, Dept.USDA},
    ("2009-12-19", "2009-12-19"): {
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
    ("2010-10-01", "2011-04-15"): set(),
    ("2010-10-01", "2011-11-18"): set(),
    ("2011-11-19", "2011-12-23"): {Dept.USDA, Dept.DOC, Dept.HUD, Dept.DOT, Dept.DOJ},
    ("2012-10-01", "2013-03-26"): set(),
    ("2013-03-27", "2013-09-30"): {
        Dept.DOD,
        Dept.DOC,
        Dept.USDA,
        Dept.DHS,
        Dept.VA,
        Dept.DOJ,
    },
    ("2013-10-17", "2014-01-17"): set(),
    ("2014-10-01", "2014-12-16"): set(),
    ("2014-12-17", "2015-03-04"): {
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
    ("2015-10-01", "2015-12-18"): set(),
    ("2016-10-01", "2017-05-05"): {Dept.VA},
    ("2017-10-01", "2018-01-20"): set(),
    ("2018-01-22", "2018-03-23"): set(),
    ("2018-10-01", "2018-12-21"): {
        Dept.DOL,
        Dept.DOD,
        Dept.ED,
        Dept.VA,
        Dept.HHS,
        Dept.DOE,
    },
    ("2019-02-10", "2019-02-15"): {
        Dept.DOL,
        Dept.DOD,
        Dept.ED,
        Dept.VA,
        Dept.HHS,
        Dept.DOE,
    },
    ("2019-10-01", "2019-12-20"): set(),
    ("2020-10-01", "2020-12-27"): set(),
    ("2021-10-01", "2022-03-15"): set(),
    ("2022-10-01", "2022-12-29"): set(),
    ("2023-10-01", "2024-03-01"): set(),
}
# VA, Ag, Energy, DOT, and HUD expire on the 1st; all others on the 8th, but
# we'll update when and if a divide in status happens
"""
CR_DEPARTMENTS: A mapping of arguments that craft the continuing resolution
calendar. Current data begin with FY99. Each key is a tuple of ISO8601
formatted strings for the start and end of the time interval. **Intervals
represent periods where there were no changes in affected agencies.**

**Each value is a set of UNAFFECTED departments as Dept enum
objects, which will be subtracted from the set of executive departments for
the period. Consequently, an empty set indicates all executive departments
were affected.**

"""
epoch_start: Timestamp = pd.to_datetime(arg="1970-01-01", format="ISO8601")

StatusIntervalType = tuple[Interval, Dept, DeptStatus]
StatusJSONType = list[
    dict[dict[Literal["interval"], Literal["start"], Literal["end"]], str],
    dict[Literal["dept"], str],
    dict[Literal["status"], str],
]


def create_interval(
    start_date: Timestamp, end_date: Timestamp, dept: Dept, status: DeptStatus
) -> StatusIntervalType:
    """
    Create an interval with the specified start date, end date, department,
    and status.

    Parameters
    ----------
        start_date: The start date of the interval.
        end_date: The end date of the interval.
        dept: The department enum associated with the interval.
        status: The DeptStatus enum of the interval.

    Returns
    -------
        The created interval as a tuple containing the interval, department,
        and status.
    """
    return pd.Interval(left=start_date, right=end_date, closed="left"), dept, status


def process_data_entry(
    key: tuple[str, str],
    value: set[Dept] | tuple[set[Dept] | None, ShutdownFlag],
    approps_gap_flag: bool,
    depts_set: set[Dept],
) -> tuple[set[Dept] | None, set[Dept] | None, Timestamp, Timestamp, DeptStatus]:
    """
    Process a data entry and return the affected departments, unaffected
    departments, start date, end date, and status.

    Parameters
    ----------
        key: A tuple representing the start date and end date of the entry.
        value: A set of Dept enum objects representing unaffected departments
            (CR_DEPARTMENTS) or a tuple representing a set of affected
            departments and shutdown flag enum (APPROPRIATIONS_GAPS).
            approps_gap_flag: A boolean the input are for appropriations gaps
            (handling for a tuple with a set and shutdown flag vice just a set
            as values)
        depts_set: set of all Dept enum objects

    Returns
    -------
        A tuple containing the affected departments, unaffected departments,
        start date, end date, and status.
    """
    start_date: Timestamp = pd.to_datetime(arg=key[0], format="ISO8601")
    end_date: Timestamp = pd.to_datetime(arg=key[1], format="ISO8601") + pd.Timedelta(
        days=1
    )
    status_mapping = {
        (False, None): DeptStatus.CR,
        (True, ShutdownFlag.SHUTDOWN): DeptStatus.SDN,
        (True, ShutdownFlag.NO_SHUTDOWN): DeptStatus.GAP,
    }
    status: DeptStatus = status_mapping[
        (approps_gap_flag, value[1])
        if value and approps_gap_flag
        else (approps_gap_flag, None)
    ]

    affected_depts = (
        value[0]
        if (value and approps_gap_flag)
        else depts_set.difference(value)
        if value
        else depts_set
    )
    unaffected_depts: set[Dept] = depts_set.difference(affected_depts)
    return affected_depts, unaffected_depts, start_date, end_date, status


def gen_interval_data(
    data: set[Dept] | None, approps_gap_flag: bool, depts_set: set[Dept] = depts_set
) -> list[StatusIntervalType]:
    intervals = []
    for key, value in data.items():
        depts_set = (
            depts_set.difference(Dept.DHS)
            if pd.to_datetime(key[1]) < dhs_formed
            else depts_set
        )
        (
            affected_depts,
            unaffected_depts,
            start_date,
            end_date,
            status,
        ) = process_data_entry(
            key=key, value=value, approps_gap_flag=approps_gap_flag, depts_set=depts_set
        )
        intervals += [
            create_interval(
                start_date=start_date, end_date=end_date, dept=dept, status=status
            )
            for dept in affected_depts
        ]
        intervals += [
            create_interval(
                start_date=start_date,
                end_date=end_date,
                dept=dept,
                status=DeptStatus.ND if end_date < cr_data_cutoff else DeptStatus.FA,
            )
            for dept in unaffected_depts
        ]
    return intervals


def insert_gap_intervals(dept, intervals) -> list[StatusIntervalType]:
    """
    Identifies gaps between our CR and appropriations gaps data on a
    department-by-department basis, and creates intervals for these gaps.
    Status is either FA (full_appropriations) or ND (CR or
    full_appropriations) if before cr_data_cutoff
    since they are by definition not under a gap/shutdown or CR.

    Parameters
    ----------
        dept: The department to insert gap intervals for.
        intervals: The intervals to process.

    Returns
    -------
        A list of gap intervals for the specified department.
    """
    start_date: Timestamp = epoch_start if dept != Dept.DHS else dhs_formed
    periods_sorted = sorted(
        (item for item in intervals if item[1] == dept), key=lambda x: x[0].left
    )
    temp = []
    if start_date < periods_sorted[0][0].left:
        temp.append(
            create_interval(
                start_date=start_date,
                end_date=periods_sorted[0][0].left,
                dept=dept,
                status=DeptStatus.ND if dept != Dept.DHS else DeptStatus.FA,
            )
        )
    for i, period in enumerate(iterable=periods_sorted[:-1]):
        next_period_start = periods_sorted[i + 1][0].left
        gap_end = next_period_start
        gap_start = period[0].right
        if gap_start < gap_end:
            status = (
                DeptStatus.ND if period[0].right < cr_data_cutoff else DeptStatus.FA
            )
            temp.append(
                create_interval(
                    start_date=gap_start, end_date=gap_end, dept=dept, status=status
                )
            )
    return temp


def clean_interval(interval: StatusIntervalType) -> StatusIntervalType | None:
    inv: Interval[Timestamp] = interval[0]
    department: Dept = interval[1]
    status: DeptStatus = interval[2]
    match (inv.right, department, status):
        case (inv.right, _, DeptStatus.FA) if inv.right < cr_data_cutoff:
            return inv, department, DeptStatus.ND
        case (inv.right, Dept.DHS, _) if inv.right < dhs_formed:
            return None
    return interval


def interval_to_dict(interval: Interval) -> dict[str, str]:
    """
    Convert an interval to a dictionary for writing to JSON.

    Parameters
    ----------
        interval: The interval to convert.

    Returns
    -------
        A dictionary with "start" and "end" keys representing the left and right attributes of the interval, respectively.
    """
    return {"start": interval.left.isoformat(), "end": interval.right.isoformat()}


def serialize_intervals(
    intervals: StatusIntervalType,
) -> StatusJSONType:
    """
    Serialize the intervals into a JSON-compatible format.

    Parameters
    ----------
        intervals: The intervals to serialize.

    Returns
    -------
        A list of dictionaries representing the serialized intervals.
    """
    return [
        {
            "interval": interval_to_dict(interval=interval),
            "dept": dept.name,
            "status": status.name,
        }
        for interval, dept, status in intervals
    ]


def write_to_json(data: StatusJSONType, filename: str) -> None:
    """
    Write the data to a JSON file.

    Parameters
    ----------
        data: The data to write.
        filename: The name of the file to write to.
    """
    with open(file=filename, mode="w") as file:
        json.dump(obj=data, fp=file, indent=4)


def main() -> None:
    """
    The main function that generates, cleans, and serializes intervals.
    """
    intervals: list[StatusIntervalType] = gen_interval_data(
        data=CR_DEPARTMENTS, approps_gap_flag=False
    )

    intervals += gen_interval_data(data=APPROPRIATIONS_GAPS, approps_gap_flag=True)

    for dept in depts_set:
        intervals += insert_gap_intervals(dept=dept, intervals=intervals)

    cleaned_intervals: list[StatusIntervalType | None] = [
        clean_interval(interval=interval)
        for interval in intervals
        if clean_interval(interval=interval)
    ]

    unique_intervals = set(cleaned_intervals)
    sorted_intervals: list[StatusIntervalType | None] = sorted(
        list(unique_intervals),
        key=lambda x: (x[0].left, x[0].right, str(x[1]), str(x[2])),
    )

    serialized_intervals: StatusJSONType = serialize_intervals(
        intervals=sorted_intervals
    )
    write_to_json(
        data=serialized_intervals,
        filename="status_intervals.json",
    )


if __name__ == "__main__":
    main()
