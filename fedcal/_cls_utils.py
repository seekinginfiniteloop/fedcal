from __future__ import annotations

from funcy import decorator
import pandas as pd
from attr import define, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import numpy as np


@define()
class SeriesExporter:
    array: "np.ndarray" | pd.Index | pd.PeriodIndex | pd.Series | None = field()
    datetimeindex: pd.DatetimeIndex | None = field(default=None)

    def array_to_series(self, name: str = None, dtype: Any = None) -> pd.Series:
        if not hasattr(self.array, "__iter__"):
            self.array = [self.array]
        return pd.Series(
            data=self.array, index=self.datetimeindex, name=name, dtype=dtype
        )


@decorator
def to_series(
    call, to_series: bool = False, name: str = None, dtype: Any = None
) -> pd.Series | "np.ndarray" | pd.Index | pd.PeriodIndex:
    result: "np.ndarray" = call()

    def get_datetimeindex() -> pd.DatetimeIndex | None:
        for source in [call._kwargs, call._locals, getattr(call._func, "self", None)]:
            datetimeindex: pd.DatetimeIndex = source.get("datetimeindex") or source.get(
                "dates"
            )
            if isinstance(datetimeindex, pd.DatetimeIndex):
                return datetimeindex
            if isinstance(source, dict):
                for vals in source.values():
                    if isinstance(vals, pd.DatetimeIndex):
                        return vals
            else:
                for attr in vars(source).values():
                    if isinstance(attr, pd.DatetimeIndex):
                        return attr

    if to_series:
        datetimeindex: pd.DatetimeIndex | None = get_datetimeindex()
        exporter = SeriesExporter(array=result, datetimeindex=datetimeindex)
        return exporter.array_to_series(name=name, dtype=dtype)
    return result
