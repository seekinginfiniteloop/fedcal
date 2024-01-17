# fedcal status.py
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
Manages the base index for government status data retrieval and delivery,
supplied by _status_factory.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from numpy import int64
from numpy.typing import NDArray
from pandas import DataFrame, Index, MultiIndex

from fedcal.enum import Dept, DeptStatus
from fedcal._typing import DatetimeScalarOrArray
from fedcal._status_factory import fetch_index, dhs_formed
from fedcal.utils import to_dt64

StatusIntervalDtype = pd.IntervalDtype(subtype="datetime64[ns]")

DeptCatDtype = pd.CategoricalDtype(
    categories=Dept.list_by_attr(attr="short"), ordered=False
)

StatusCatDtype = pd.CategoricalDtype(
    categories=DeptStatus.list_by_attr(attr="var").sort(
        key=lambda x: DeptStatus.swap_attr(val=x, rtn_attr="val")
    ),
    ordered=True,
)


def _set_frame(mdx: MultiIndex = None) -> DataFrame:
    """
    Converts status MultiIndex to a categorical DataFrame with IntervalIndex.
    """
    mdx = mdx or fetch_index()
    df: DataFrame = mdx.to_frame(index=False, name=["Interval", "Department", "Status"])
    df["Interval"] = df["Interval"].astype(dtype=StatusIntervalDtype)
    df["Department"] = df["Department"].astype(dtype=DeptCatDtype)
    df["Status"] = df["Status"].astype(dtype=StatusCatDtype)
    return df.set_index(keys=["Interval"])


@dataclass(slots=True, order=True, frozen=True)
class GovStatus:
    """
    _summary_
    """

    name: str = field(default="gov_status")
    mdx: MultiIndex = field(default_factory=fetch_index())
    df: DataFrame = field(default=None, init=False)
    status_cats: Index[str] = field(default=StatusCatDtype.categories)
    status_cat_map: dict[str, str] = field(
        default=DeptStatus.attr_member_map(attr="var")
    )

    dept_cats: Index[str] = field(default=DeptCatDtype.categories)
    dept_cat_map: dict[str, str] = field(default=Dept.attr_member_map(attr="short"))

    def __post_init__(self):
        self.df = _set_frame(mdx=self.mdx)

    def depts(self, dt: DatetimeScalarOrArray = None) -> list[Dept] | NDArray:
        """
        Returns the set of Dept enum objects for the specified date(s) if a
        date is provided, else provides current Dept objects.

        Parameters
        ----------
        dt : datetime-like object for department identification.

        Returns
        -------
        Either a set of Dept enum objects or a Numpy array of Dept enums.
        """
        if dt:
            if pd.api.types.is_scalar(val=dt):
                return (
                    Dept.members().remove(Dept.DHS)
                    if dt < dhs_formed
                    else Dept.members()
                )
            dt = to_dt64(dt=dt, to_int64=True)
            dhs: NDArray[int64] = to_dt64(dt=dhs_formed, to_int64=True)
            return np.where(dt >= dhs, Dept.members(), Dept.members().remove(Dept.DHS))
        return Dept.members()

    @property
    def statuses(self) -> MultiIndex:
        """Alias for mdx and index properties."""
        return self.mdx

    @property
    def dataframe(self) -> DataFrame:
        """
        Returns the status dataframe.
        """
        return self.df

    @property
    def status_categories(self) -> Index[str]:
        """
        Returns the status categories.
        """
        return self.status_cats

    @property
    def dept_categories(self) -> Index[str]:
        """
        Returns the department categories.
        """
        return self.dept_cats


def df_by_dept(self, dept: str) -> DataFrame:
    """
    Returns the status dataframe for the specified department.
    """
    return self.df.loc[self.df["Department"] == dept]


def status_at(self, dt: pd.Timestamp) -> DataFrame:
    """
    Returns the status dataframe for the specified date.
    """
    return self.status.loc[dt]


def status_in_range(self, datetimeindex: pd.DatetimeIndex) -> DataFrame:
    """
    Returns the status dataframe for the specified date range.
    """
    return datetimeindex.isin(values=self.status.get_level_values(level=0))


__all__: list[str] = ["GovStatus"]
