from __future__ import annotations

from typing import TYPE_CHECKING, Dict, Generator, Mapping, Union

if TYPE_CHECKING:
    from datetime import date, datetime

    import numpy as np
    import pandas as pd

    from fedcal.constants import AppropsStatus, Dept, OpsStatus, ShutdownFlag
    from fedcal.depts import FedDepartment
    from fedcal.time_utils import YearMonthDay

FedDateStampConvertibleTypes = Union[
    "pd.Timestamp",
    int,
    "np.int64",
    "np.datetime64",
    float,
    "YearMonthDay",
    tuple[int, int, int],
    tuple[str, str, str],
    str,
    "date",
    "datetime",
]

FedDateIndexConvertibleTypes = Union[
    tuple[FedDateStampConvertibleTypes, FedDateStampConvertibleTypes],
    tuple["pd.Timestamp", "pd.Timestamp"],
    "np.ndarray",
    "pd.Series",
    "pd.DatetimeIndex",
    "pd.Index",
]

AppropriationsGapsMapType = Mapping[tuple[int, int], tuple[set["Dept"], "ShutdownFlag"]]

CRMapType = Mapping[tuple[int, int], set["Dept"]]

StatusTupleType = tuple["AppropsStatus", "OpsStatus"]

AssembledBudgetIntervalType = tuple[set["Dept"], StatusTupleType]

DateStampStatusMapType = Mapping["Dept", StatusTupleType]

StatusMapType = Mapping[str, StatusTupleType]

StatusPoolType = Mapping[tuple["Dept", str], "FedDepartment"]

StatusDictType = Dict["Dept", "FedDepartment"]

StatusGeneratorType = Generator[tuple[str, StatusDictType], None, None]

StatusCacheType = Dict[str, StatusDictType]

ExtractedStatusDataGeneratorType = Generator[tuple["pd.Timestamp", "FedDepartment"]]
