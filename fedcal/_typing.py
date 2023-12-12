from __future__ import annotations

from typing import TYPE_CHECKING, Dict, Generator, Mapping, Tuple, Union

if TYPE_CHECKING:
    from datetime import date, datetime

    from numpy import datetime64, int64, ndarray
    from pandas import DatetimeIndex, Index, Series, Timestamp

    from .constants import (
        EXECUTIVE_DEPARTMENT,
        FUNDING_STATUS,
        OPERATIONAL_STATUS,
        SHUTDOWN_FLAG,
    )
    from .depts import FedDepartment
    from .feddatestamp import FedDateStamp
    from .time_utils import YearMonthDay

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

StatusTupleType = Tuple["FUNDING_STATUS", "OPERATIONAL_STATUS"]

AssembledBudgetIntervalType = Tuple[set["EXECUTIVE_DEPARTMENT"], StatusTupleType]

DateStampStatusMapType = Mapping["EXECUTIVE_DEPARTMENT", StatusTupleType]

StatusMapType = Mapping[str, StatusTupleType]

StatusPoolType = Mapping[Tuple["EXECUTIVE_DEPARTMENT", str], "FedDepartment"]

StatusDictType = Dict["EXECUTIVE_DEPARTMENT", "FedDepartment"]

StatusGeneratorType = Generator[Tuple[str, StatusDictType], None, None]

StatusCacheType = Dict[str, StatusDictType]

ExtractedStatusDataGeneratorType = Generator[Tuple["FedDateStamp", "FedDepartment"]]
