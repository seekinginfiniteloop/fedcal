from __future__ import annotations

from typing import TYPE_CHECKING, Dict, Mapping, Tuple, Union

if TYPE_CHECKING:
    from datetime import date, datetime

    from constants import (
        EXECUTIVE_DEPARTMENT,
        FUNDING_STATUS,
        OPERATIONAL_STATUS,
        SHUTDOWN_FLAG,
    )
    from dept_status import FedDepartment
    from fedcal import FedDateStamp
    from numpy import datetime64, int64, ndarray
    from pandas import DatetimeIndex, Index, Series, Timestamp
    from time_utils import YearMonthDay

FedDateStampConvertibleTypes = Union[
    "Timestamp",
    int,
    "int64",
    "datetime64",
    float,
    "YearMonthDay",
    Tuple[int, int, int],
    Tuple[str, str, str],
    str,
    "date",
    "datetime",
]

FedDateIndexConvertibleTypes = Union[
    Tuple[FedDateStampConvertibleTypes, FedDateStampConvertibleTypes],
    Tuple["FedDateStamp", "FedDateStamp"],
    "ndarray",
    "Series",
    "DatetimeIndex",
    "Index",
]

AppropriationsGapsMapType = Mapping[
    tuple[int, int], Tuple[set["EXECUTIVE_DEPARTMENT"], "SHUTDOWN_FLAG"]
]

CRMapType = Mapping[Tuple[int, int], set["EXECUTIVE_DEPARTMENT"]]

AssembledBudgetIntervalType = Tuple[
    set["EXECUTIVE_DEPARTMENT"], Tuple["FUNDING_STATUS", "OPERATIONAL_STATUS"]
]

StatusMapType = Mapping[str, Tuple["FUNDING_STATUS", "OPERATIONAL_STATUS"]]

StatusPoolType = Mapping[Tuple["EXECUTIVE_DEPARTMENT", str], "FedDepartment"]

StatusDictType = Dict["EXECUTIVE_DEPARTMENT", "FedDepartment"]
