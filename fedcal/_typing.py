from __future__ import annotations

from typing import TYPE_CHECKING, Dict, Generator, Mapping, Tuple, Union

if TYPE_CHECKING:
    from datetime import date, datetime

    import pandas as pd
    from numpy import datetime64, int64, ndarray

    from .constants import (
        Dept,
        AppropsStatus,
        OpsStatus,
        ShutdownFlag,
    )
    from .depts import FedDepartment
    from .feddatestamp import FedDateStamp
    from .time_utils import YearMonthDay

FedDateStampConvertibleTypes = Union[
    "pd.Timestamp",
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
    "pd.Series",
    "pd.DatetimeIndex",
    "pd.Index",
]

AppropriationsGapsMapType = Mapping[tuple[int, int], Tuple[set["Dept"], "ShutdownFlag"]]

CRMapType = Mapping[Tuple[int, int], set["Dept"]]

StatusTupleType = Tuple["AppropsStatus", "OpsStatus"]

AssembledBudgetIntervalType = Tuple[set["Dept"], StatusTupleType]

DateStampStatusMapType = Mapping["Dept", StatusTupleType]

StatusMapType = Mapping[str, StatusTupleType]

StatusPoolType = Mapping[Tuple["Dept", str], "FedDepartment"]

StatusDictType = Dict["Dept", "FedDepartment"]

StatusGeneratorType = Generator[Tuple[str, StatusDictType], None, None]

StatusCacheType = Dict[str, StatusDictType]

ExtractedStatusDataGeneratorType = Generator[Tuple["FedDateStamp", "FedDepartment"]]
