from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, KeysView

import pandas as pd
from fedcal import _civpay, _date_attributes, _dept_status, _mil, constants, time_utils
from fedcal._meta import MagicDelegator

if TYPE_CHECKING:
    import numpy as np
    from fedcal._typing import (
        ExtractedStatusDataGeneratorType,
        FedIndexConvertibleTypes,
        FedStampConvertibleTypes,
        StatusCacheType,
        StatusGeneratorType,
        StatusTupleType,
    )
    from fedcal.constants import AppropsStatus, Dept, OpsStatus


class FedIndex(
    metaclass=MagicDelegator,
    delegate_to="datetimeindex",
    delegate_class=pd.DatetimeIndex,
):

    """
    `FedIndex` extends pd.DatetimeIndex with additional
    functionality specific to federal dates. Like `FedStamp`, it uses
    a metaclass, `MagicDelegator`, combined with attribute delegation to its
    datetimeindex attribute to mirror pandas' `DatetimeIndex` functionality
    while adding significant additional capabilities for federal analysis.It
    includes methods and properties for handling various aspects of federal
    operations, such as paydays, department statuses, and fiscal years.

    Attributes
    ----------
    business_days : pd.Series
        pd.Series indicating business days.

    fys : pd.Series
        pd.Series representing fiscal years.

    fiscal_quarters : pd.Series
        pd.Series for fiscal quarters.

    holidays : pd.Series
        pd.Series indicating holidays.

    proclaimed_holidays : np.ndarray
        Array of boolean values for proclaimed holidays.

    possible_proclamation_holidays : np.ndarray
        Array of boolean values for possible proclamation holidays.

    probable_mil_passdays : pd.Series
        pd.Series indicating probable military pass days.

    mil_paydays : pd.Series
        pd.Series of military paydays.

    civ_paydays : pd.Series
        pd.Series of civilian paydays.

    departments : pd.DataFrame
        pd.DataFrame of departments.

    departments_bool : pd.DataFrame
        pd.DataFrame indicating department existence per date.

    all_depts_status : pd.DataFrame
        pd.DataFrame with status for all departments.

    all_depts_full_approps : pd.Series
        pd.Series for departments with full appropriations.

    all_depts_cr : pd.Series
        pd.Series for departments under a continuing resolution.

    all_depts_cr_or_full_approps : pd.Series
        pd.Series for departments under full appropriations or a CR.

    all_unfunded : pd.Series
        pd.Series for all unfunded departments.

    gov_cr : pd.Series
        pd.Series indicating any department under a CR.

    gov_shutdown : pd.Series
        pd.Series indicating any department in a shutdown.

    gov_unfunded : pd.Series
        pd.Series for any unfunded department.

    full_op_depts : pd.DataFrame
        pd.DataFrame of fully operational departments.

    full_or_cr_depts : pd.DataFrame
        pd.DataFrame of departments fully funded or under a CR.

    cr_depts : pd.DataFrame
        pd.DataFrame of departments under a CR.

    gapped_depts : pd.DataFrame
        pd.DataFrame of departments in a funding gap.

    shutdown_depts : pd.DataFrame
        pd.DataFrame of departments in a shutdown.

    unfunded_depts : pd.DataFrame
        pd.DataFrame of unfunded departments.

    Methods
    -------
    to_fedtimestamp
        Converts dates to POSIX timestamps.

    contains_date
        Checks if a date is in the index.

    contains_index
        Checks if another index is contained within this one.

    overlaps_index
        Checks for any overlap with another index.

    construct_status_dataframe
        Constructs a status pd.DataFrame based on given criteria.

    status_dataframe_to_multiindex
        Converts a status pd.DataFrame to a multiindex pd.DataFrame.

    status_dataframe_to_all_bool
        Converts a status pd.DataFrame to a boolean pd.DataFrame.

    get_departments_status
        Retrieves the status of specified departments.

    Examples
    --------
    # Example usage
    (TODO: Beef up examples)
    fed_index = FedIndex(['2023-01-01', '2023-01-02'])
    print(fed_index.business_days)
    print(fed_index.full_op_depts)

    Notes
    -------
    *Private Methods*:
        _reverse_human_readable_status : Converts human-readable status to
        internal representation.
        set_self_date_range : Sets the start and end date of the index.
        _get_mil_cache : Retrieves military cache data.
        _set_mil_cache : Sets the military cache.
        _set_status_gen : Sets the status generator.
        _get_status_gen : Gets the status generator.
        _set_status_cache : Sets the status cache.
        _generate_status_cache : Generates the status cache.
        _extract_status_data : Extracts status data based on filters.
        _check_dept_status : Checks department status against criteria.

    TODO
    ----
    Implement custom __setattr__, __setstate_cython__, __setstate__,
    __init_subclass__, __hash__, __getstate__, __dir__, (__slots__?)
    """

    def __init__(
        self,
        datetimeindex: pd.DatetimeIndex | None = None,
        dates: FedIndexConvertibleTypes | None = None,
    ) -> None:
        if isinstance(datetimeindex, pd.DatetimeIndex):
            self.datetimeindex: pd.DatetimeIndex = datetimeindex
        elif datetimeindex or dates:
            self.datetimeindex = self._convert_input(
                time_input=datetimeindex
            ) or self._convert_input(time_input=dates)
        else:
            self.datetimeindex: pd.DatetimeIndex = self._set_default_index()
        self.start: pd.Timestamp
        self.end: pd.Timestamp
        self.start, self.end = self.set_self_date_range()

        # define caches; only created if accessed
        self._mil_cache = None
        self._status_gen = None
        self._status_cache = None
        self._holidays = None

    def __getattr__(self, name: str) -> Any:
        if name in self.__class__.__dict__:
            return self.__class__.__dict__[name].__get__(self, self.__class__)

        if hasattr(self.pdtimestamp, name):
            return getattr(self.pdtimestamp, name)
        else:
            raise AttributeError(
                f"'{type(self).__name__}' object has no attribute '{name}'"
            )

    def __getattribute__(self, name: str) -> Any:
        return object.__getattribute__(self, name)

    # Methods for caching and other internal use to the class
    @staticmethod
    def _convert_input(time_input: FedIndexConvertibleTypes) -> pd.DatetimeIndex:
        return time_utils.to_datetimeindex(time_input)

    @staticmethod
    def _set_default_index() -> pd.DatetimeIndex:
        default_range: tuple["YearMonthDay", "YearMonthDay"] = (
            time_utils.YearMonthDay(year=1998, month=10, day=1),
            time_utils.YearMonthDay(year=2045, month=9, day=30),
        )
        return time_utils.to_datetimeindex(default_range)

    @staticmethod
    def _reverse_human_readable_status(status_str: str) -> "StatusTupleType":
        """
        Convert a human-readable status string to its corresponding status
        tuple.

        Parameters
        ----------
        status_str : str
            The status string to be converted.

        Returns
        -------
        StatusTupleType
            The corresponding tuple representation of the status.

        Notes
        -----
        This method uses the `READABLE_STATUS_MAP` to reverse map
        human-readable status strings to their internal tuple representations.
        """
        return constants.READABLE_STATUS_MAP.inv[status_str]

    def set_self_date_range(self) -> tuple[pd.Timestamp, pd.Timestamp]:
        """
        Set the start and end date range of the FedIndex instance.

        Notes
        -----
        This method sets the `start` and `end` attributes of the instance It
        defaults to the minimum and maximum of the index if `start` or `end`
        are not explicitly set.
        """
        return self.datetimeindex.min(), self.datetimeindex.max()

    def _get_mil_cache(self) -> None:
        """
        Retrieve the military pay pass range for the current date range.

        Returns
        -------
        None
        This method does not return a value but sets an internal cache.

        Notes
        -----
        The method updates the start and end date range of the instance and
        then retrieves the MilPayPassRange object corresponding to this
        updated range.
        """

        self.set_self_date_range()
        return _mil.MilPayPassRange(start=self.start, end=self.end)

    def _set_mil_cache(self) -> None:
        """
        Initialize or update the military cache for the instance.

        Notes
        -----
        This method sets the `_mil_cache` attribute with a `MilPayPassRange`
        object. If `_mil_cache` is already set, it leaves it unchanged.
        Otherwise, it calls `_get_mil_cache` to generate and set the cache.
        """
        self._mil_cache: _mil.MilPayPassRange = self._mil_cache or self._get_mil_cache()

    def _set_status_gen(self) -> None:
        """
        Initialize the department status generator for the instance.

        Notes
        -----
        This method sets the `_status_gen` attribute with a
        `StatusGeneratorType` object. If `_status_gen` is already set, it does
        nothing. Otherwise, it uses `_get_status_gen` to generate and set the
        status generator.
        """
        self._status_gen: "StatusGeneratorType" = (
            self._status_gen or self._get_status_gen()
        )

    def _get_status_gen(self) -> "StatusGeneratorType":
        """
        Retrieve the status generator for the current date range. This is
        `FedIndex`'s primary means of retrieving statuses for Federal
        departments.

        Returns
        -------
        StatusGeneratorType
            A generator that maps departments to their statuses over the
            specified date range.

        Notes
        -----
        The method sets the date range of the instance and initializes the
        `states` attribute with a `DepartmentState` object. It then retrieves
        the status generator from `DepartmentState`
        get_state_for_range_generator` for the specified start and end dates.
        """

        self.set_self_date_range()
        states = _dept_status.DepartmentState()
        return states.get_state_for_range_generator(start=self.start, end=self.end)

    def _set_status_cache(self) -> None:
        """
        Initialize or update the status cache for the instance.

        Notes
        -----
        This method ensures the status generator is set using
        `_set_status_gen` and
        then sets or updates the `_status_cache` attribute. If `_status_cache`
        is not already set, it uses `_generate_status_cache` to create and set
        the cache.
        """

        self._set_status_gen()
        self._status_cache: "StatusCacheType" = (
            self._status_cache or self._generate_status_cache()
        )

    def _generate_status_cache(self) -> "StatusCacheType":
        """
        Generate a status cache based on the current status generator.

        Returns
        -------
        StatusCacheType
            A dictionary representing the status cache.

        Notes
        -----
        The method first ensures the status generator is set, either by using an
        existing one or initializing it. It then creates a dictionary from the
        status generator to serve as the status cache.
        """
        gen: "StatusGeneratorType" = self._status_gen or self._set_status_gen()
        return dict(gen)

    def _extract_status_data(
        self,
        statuses: set[str] | None = None,
        department_filter: set["Dept"] | None = None,
    ) -> "ExtractedStatusDataGeneratorType":
        """
        Extract status data based on specified statuses and department filters.
        This is a helper/retriever method for `construct_status_dataframe`. It
        fetches data for specified departments and/or
        Parameters
        ----------
        statuses : set[str] or None, optional
            Set of status strings to filter by. If None, uses all status keys.
            Valid status keys (keys are the keys to `STATUS_MAP`).

        department_filter : set[Dept] or None, optional
            Set of departments to filter by. If None, uses all executive
            departments. Inputs are a set of Dept enum objects.

        Yields
        ------
        ExtractedStatusDataGeneratorType
            A generator yielding tuples of date and department instance for
            each matching status and department.

        Notes
        -----
        This method sets the status generator and then iterates over the
        status data, adjusting for certain conditions like date cutoffs. It
        yields only the data that matches the specified statuses and
        departments.
        """

        self._set_status_gen()
        data_input: "StatusCacheType" | "StatusGeneratorType" = (
            self._status_cache or self._status_gen
        )

        statuses: set[str] | KeysView[str] = statuses or constants.keys()
        department_filter = department_filter or constants.DEPTS_SET

        data_check_statuses: set[str] = {"DEFAULT_STATUS", "CR_STATUS"}

        for date, department_statuses in (
            data_input.items() if isinstance(data_input, dict) else data_input
        ):
            if time_utils.pdtimestamp_to_posix_seconds(
                timestamp=time_utils.to_timestamp(date)
            ) < constants.CR_DATA_CUTOFF_DATE and any(
                status in statuses for status in data_check_statuses
            ):
                adjusted_statuses: set["StatusTupleType"] = {
                    constants.STATUS_MAP[key]
                    for key in statuses
                    if key not in data_check_statuses
                } | {constants.STATUS_MAP["CR_DATA_CUTOFF_DEFAULT_STATUS"]}
            else:
                adjusted_statuses: set["StatusTupleType"] = {
                    constants.STATUS_MAP[key] for key in statuses
                }

            for department, fed_department_instance in department_statuses.items():
                status_tuple: StatusTupleType = (
                    fed_department_instance.to_status_tuple()
                )
                if (
                    department in department_filter
                    and status_tuple in adjusted_statuses
                ):
                    yield (time_utils.to_timestamp(date), fed_department_instance)

    def _check_dept_status(
        self, statuses: set[str], check_any: bool = False
    ) -> pd.Series:
        """
        Check department statuses against specified statuses and aggregation
        logic. By default, checks if passed statuses apply to all departments
        on a given date. If check_any = True is passed, it will instead check
        if any department was in that status for the date (see gov_[status]
        methods).

        Parameters
        ----------
        statuses : set[str]
            Set of status strings to check departments against. Valid keys are
            keys to `STATUS_MAP`.
        check_any : bool, optional
            If True, checks if any department matches the statuses. If False,
            checks if all departments match. Defaults to False.

        Returns
        -------
        pd.Series
            A boolean Pandas pd.Series indicating whether each date matches the
            criteria.

        Notes
        -----
        This method constructs a dataframe from status data and department
        data, then applies the specified logic (any or all) to determine if
        the departments match the given statuses for each date.
        """

        status_df: pd.DataFrame = self.construct_status_dataframe(
            statuses=statuses
        ).set_index(keys="Date")
        dept_df: pd.DataFrame = self.departments.set_index(keys="Date")

        dept_df["Departments"] = dept_df["Departments"].apply(
            func=lambda x: set(x.split(", "))
        )

        if check_any:
            comparison_func: Callable = lambda depts: dept_df["Departments"].apply(
                func=lambda d: bool(d & depts)
            )
        else:
            comparison_func: Callable = lambda depts: dept_df["Departments"].apply(
                func=lambda d: d == depts
            )

        comparison_df: pd.DataFrame = status_df["Departments"].apply(
            func=comparison_func
        )

        return comparison_df.any(axis=1) if check_any else comparison_df.all(axis=1)

    # utility methods

    def to_fedtimestamp(self) -> pd.Series:
        """
        Convert the dates in the index to POSIX timestamps normalized to midnight.

        Returns
        -------
        pd.Series
            A Pandas pd.Series containing integer POSIX timestamps.

        Notes
        -----
        This method normalizes each date in the index to midnight and then
        converts them to POSIX timestamps (seconds since the Unix epoch).
        """

        return (
            self.datetimeindex.to_series()
            .apply(func=lambda x: time_utils.pdtimestamp_to_posix_seconds(timestamp=x))
            .astype(dtype=int)
        )

    def contains_date(self, date: "FedStampConvertibleTypes") -> bool:
        """
        Check if the index contains a specified date.

        Parameters
        ----------
        date : FedStampConvertibleTypes
        The date to check for in the index.

        Returns
        -------
        bool
        True if the date is in the index, False otherwise.

        Notes
        -----
        This method converts the input date to a `FedStamp`, if necessary,
        and then checks if it exists in the index.
        """
        date: pd.Timestamp = time_utils.to_timestamp(date)
        return date in self.datetimeindex

    def contains_index(self, other_index: "FedIndexConvertibleTypes") -> bool:
        """
        Check if the index contains a specified date.

        Parameters
        ----------
        date : FedIndexConvertibleTypes
            The date to check for in the index.

        Returns
        -------
        bool
            True if the date is in the index, False otherwise.

        Notes
        -----
        This method converts the input date to a `pd.Timestamp`, if necessary,
        and then checks if it exists in the index.
        """

        other_index = time_utils.to_datetimeindex(other_index)
        return other_index.isin(values=self.datetimeindex).all()

    def overlaps_index(self, other_index: "FedIndexConvertibleTypes") -> bool:
        """
        Check if the index overlaps with another index.

        Parameters
        ----------
        other_index : FedIndexConvertibleTypes
            The other index to check for overlap.

        Returns
        -------
        bool
            True if any date from the other index is in this index, False
            otherwise.

        Notes
        -----
        This method converts the input index, if
        necessary, and then checks for any overlapping dates using the `isin`
        method.
        """

        other_index = time_utils.to_datetimeindex(other_index)
        return other_index.isin(values=self.datetimeindex.any())

    def construct_status_dataframe(
        self,
        statuses: set[str] | None = None,
        department_filter: set["Dept"] | None = None,
    ) -> pd.DataFrame:
        """
        Primary constructor method for `FedIndex`s department status
        properties. Outputs a human readable pd.DataFrame of data for the given
        status and department inputs. For deeper analysis, may be optionally
        converted with the status_dataframe_to_multiindex() and
        status_dataframe_to_all_bool() methods.

        Parameters
        ----------
        statuses : set[str] or None, optional
        Set of status keys to include. If None, includes all statuses.
        Valid keys are keys to `STATUS_MAP`.

        department_filter : set[Dept] or None, optional
        Set of departments to include. If None, includes all departments.
        Valid inputs are Dept enum objects.

        Returns
        -------
        pd.DataFrame
        A Pandas pd.DataFrame with columns for date, department, and status.

        Notes
        -----
        This method extracts status data based on the given filters and
        constructs a pd.DataFrame from it, with each row representing a
        date-department-status trio.
        """

        extracted_data: "ExtractedStatusDataGeneratorType" = self._extract_status_data(
            statuses=statuses, department_filter=department_filter
        )
        rows: list[Any] = []
        for date, fed_department_instance in extracted_data:
            row: dict[str, Any] = {
                "Date": date,
                "Department": fed_department_instance.name.short,
                "Status": fed_department_instance.status,
            }
            rows.append(row)
        return pd.DataFrame(data=rows)

    def status_dataframe_to_multiindex(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Convert a status dataframe generated by construct_status_dataframe to
        a multi-indexed dataframe.

        Parameters
        ----------
        df : pd.DataFrame
            The dataframe with status information to convert.

        Returns
        -------
        pd.DataFrame
            A Pandas pd.DataFrame with a multi-index (Date, Department,
            FundingStatus, OperationalStatus).

        Notes
        -----
        This method iterates over the given dataframe and converts each row
        into a tuple representing the multi-index structure, then constructs a
        new pd.DataFrame with these tuples as the index.
        """
        multiindex_data: list[Any] = []
        for _, row in df.iterrows():
            date: pd.Timestamp = row["Date"]
            department_short: str = row["Department"]
            human_readable_status: str = row["Status"]

            department_enum: "Dept" = constants.Dept.from_short_name(
                short_name=department_short
            )
            funding_status: "AppropsStatus"
            operational_status: "OpsStatus"
            funding_status, operational_status = self._reverse_human_readable_status(
                status_str=human_readable_status
            )

            multiindex_data.append(
                (date, department_enum, funding_status, operational_status)
            )

        multiindex: pd.MultiIndex = pd.MultiIndex.from_tuples(
            tuples=multiindex_data,
            names=["Date", "Department", "FundingStatus", "OperationalStatus"],
        )
        return pd.DataFrame(index=multiindex).reset_index()

    def status_dataframe_to_all_bool(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Convert a pd.DataFrame generated by construct_status_dataframe() with
        departments and statuses into a boolean pd.DataFrame.

        This method takes a pd.DataFrame with 'Department' and 'Status' columns
        and transforms it into a pd.DataFrame where each column represents a
        combination of a department and a status, filled with boolean values.

        Parameters
        ----------
        df : pd.DataFrame
            A pd.DataFrame containing 'Date', 'Department', and 'Status'
            columns.

        Returns
        -------
        pd.DataFrame
            A transformed pd.DataFrame with columns for each department-status
            combination, filled with boolean values indicating the presence
            of each department-status pair.
        """

        unique_departments: "np.ndarray"[str] = df["Department"].unique()
        unique_statuses: "np.ndarray"[str] = df["Status"].unique()

        columns: list[str] = [
            f"{dept}-{status}"
            for dept in unique_departments
            for status in unique_statuses
        ]
        bool_df: pd.DataFrame = pd.DataFrame(index=df.index, columns=columns).fillna(
            value=False
        )

        for index, row in df.iterrows():
            date: pd.Timestamp = row["Date"]
            department_short: str = row["Department"]
            human_readable_status: str = row["Status"]

            col_name: str = f"{department_short}-{human_readable_status}"
            bool_df.at[index, col_name] = True

        return bool_df.reset_index(drop=True)

    def get_departments_status(self, departments: set["Dept"]) -> pd.DataFrame:
        """
        Generate a pd.DataFrame of department statuses for a given set of
        departments.

        This method provides a pd.DataFrame detailing the statuses for a
        specific set of departments over the `FedIndex`'s date range.

        Parameters
        ----------
        departments : set of Dept
            A set of Dept enum objects for which to retrieve
            status information.

        Returns
        -------
        pd.DataFrame
            A pd.DataFrame containing status information for the specified
            departments.

        """

        self._set_status_cache()
        return self.construct_status_dataframe(
            statuses={"all"}, department_filter=departments
        )

    # Begin date attribute property methods
    @property
    def business_days(self) -> pd.Series:
        """
        Determine if the dates in the index are Federal business days.

        This property checks each date in the index to see if it is a business
        day, based on federal business day rules.

        Returns
        -------
        pd.Series
            A Pandas pd.Series of boolean values, where True indicates a business day.

        """
        bizdays = _date_attributes.FedBusDay()
        next_business_days = self.datetimeindex + bizdays.fed_business_days
        return self == next_business_days

    @property
    def fys(self) -> pd.Series:
        """
        Retrieve the fiscal years for each date in the index.

        This property maps each date in the index to its corresponding federal
        fiscal year.

        Returns
        -------
        pd.Series
            A Pandas pd.Series with the fiscal year for each date in the index.

        """
        fyears = _date_attributes.FedFiscalYear()
        return fyears.get_fiscal_years(datetimeindex=self.datetimeindex)

    @property
    def fiscal_quarters(self) -> pd.Series:
        """
        Obtain the fiscal quarters for each date in the index.

        This property identifies the federal fiscal quarter for each date in
        the index.

        Returns
        -------
        pd.Series
            A Pandas pd.Series with the fiscal quarter for each date in the
            index.

        """
        fqs = _date_attributes.FedFiscalQuarter()
        return fqs.get_fiscal_quarters(datetimeindex=self.datetimeindex)

    def _set_holidays(self) -> None:
        self._holidays = self._holidays or _date_attributes.FedHolidays()

    @property
    def holidays(self) -> pd.Series:
        """
        Identify federal holidays in the index.

        This property checks each date in the index to determine if it is a
        federal holiday.

        Returns
        -------
        pd.Series
            A Pandas pd.Series of boolean values, where True indicates a
            federal holiday.
        """
        self._set_holidays()
        next_holidays: pd.DatetimeIndex = self.datetimeindex + self._holidays
        return self.datetimeindex == next_holidays

    @property
    def proclaimed_holidays(self) -> "np.ndarray":
        """
        Check for proclaimed federal holidays in the index.

        This property identifies dates in the index that are proclaimed federal
        holidays.

        Returns
        -------
        np.ndarray
            An np.ndarray of boolean values, where True indicates a proclaimed
            federal
            holiday.

        """
        self._set_holidays()
        return self.datetimeindex.isin(
            values=pd.DatetimeIndex(data=self._holidays.proclaimed_holidays)
        )

    @property
    def possible_proclamation_holidays(self) -> "np.ndarray":
        """
        Guesses if the dates in the index are possible *future* proclamation
        federal holidays.

        Returns
        -------
        Pandas pd.Series of boolean values indicating possible proclamation
        holidays.

        Notes
        -----
        See notes to FedStamp.possible_proclamation_holiday.

        """
        self._set_holidays()
        return self._holidays.guess_proclamation_holidays(
            datetimeindex=self.datetimeindex
        )

    @property
    def probable_mil_passdays(self) -> pd.Series:
        """
        Estimate military pass days within the index's date range.

        This property calculates the probable military pass days based on the
        index's date range and internal military cache data. See notes on
        similar properties in FedStamp; while this will be mostly
        accurate, specific dates for passes vary between commands and locales.

        Returns
        -------
        pd.Series
            A Pandas pd.Series indicating probable military pass days.

        """

        self._set_mil_cache()
        return self._mil_cache.get_milpass_series()

    # Payday properties
    @property
    def mil_paydays(self) -> pd.Series:
        """
        Identify military payday dates within the index.

        This property uses the index's date range and military cache data to
        determine the dates that are military paydays.

        Returns
        -------
        pd.Series
            A Pandas pd.Series indicating military payday dates.

        """

        self._set_mil_cache()
        return self._mil_cache.get_milpay_series()

    @property
    def civ_paydays(self) -> pd.Series:
        """
        Determine civilian payday dates within the index's date range.

        This property calculates the dates that are civilian paydays based on the index's date range.

        Returns
        -------
        pd.Series
            A Pandas pd.Series indicating civilian payday dates.

        """

        self.set_self_date_range()
        pays = _civpay.FedPayDay()
        return pays.get_paydays_as_series(start=self.start, end=self.end)

    @property
    def departments(self) -> pd.DataFrame:
        """
        Create a pd.DataFrame of departments active on each date in the index.

        This property generates a pd.DataFrame where each row corresponds to a
        date in the index, listing the active executive departments on that
        date and adjusting for the formation of DHS.

        Returns
        -------
        pd.DataFrame
            A pd.DataFrame with each date in the index and the active
            departments
            on that date.
        """
        all_depts: list[str] = ", ".join([dept.short for dept in constants.DEPTS_SET])
        pre_dhs_depts: list[str] = ", ".join(
            [dept.short for dept in constants.DEPTS_SET.difference(constants.Dept.DHS)]
        )

        dept_df: pd.DataFrame = self.datetimeindex.to_frame(name="Departments")
        dept_df["Departments"] = dept_df.index.map(
            mapper=lambda date: all_depts
            if date >= constants.DHS_FORMED
            else pre_dhs_depts
        )
        return dept_df

    @property
    def departments_bool(self) -> pd.DataFrame:
        """
        Generates a pd.DataFrame indicating whether each department exists on
        each date in the index.

        This method specifically accounts for the formation of the
        Department of Homeland Security (DHS). Dates prior to DHS's
        formation will have a False value for DHS.

        Returns
        -------
        pd.DataFrame
            A pd.DataFrame with the index as dates and columns as department
            short names. Each cell is True if the department exists on that
            date, except for DHS before its formation date, which is False.
        """

        dept_columns: list[str] = [dept.short for dept in constants.Dept]
        df: pd.DataFrame = pd.DataFrame(
            index=self.datetimeindex, columns=dept_columns
        ).fillna(value=True)

        # Adjust for DHS
        dhs_start_date: pd.Timestamp | None = time_utils.to_timestamp(
            date=constants.DHS_FORMED
        )
        df.loc[df.index < dhs_start_date, "DHS"] = False

        return df

    @property
    def all_depts_status(self) -> pd.DataFrame:
        """
        Provides a status pd.DataFrame for all departments over the entire
        date range.

        This method leverages the internal status cache to obtain the status
        information for all departments. It's useful for getting a
        comprehensive overview of the status across all departments for the
        index's range.

        Returns
        -------
        pd.DataFrame
            A pd.DataFrame with status information for all departments across
            the index's date range.
        """

        self._set_status_cache()
        return self.construct_status_dataframe(statuses={"all"})

    @property
    def all_depts_full_approps(self) -> pd.Series:
        """
        Determines if all departments have full appropriations on each date.

        This method checks whether each department is operating under full
        appropriations ('DEFAULT_STATUS') for every date in the index.

        Returns
        -------
        pd.Series
            A Pandas pd.Series where each date is True if all departments have
            full appropriations, otherwise False.

        """

        return self._check_dept_status(statuses={"DEFAULT_STATUS"})

    @property
    def all_depts_cr(self) -> pd.Series:
        """
        Checks if all departments are under a continuing resolution (CR) on
        each date.

        This method assesses whether each department is operating under a
        continuing resolution ('CR_STATUS') for every date in the index.

        Returns
        -------
        pd.Series
            A Pandas pd.Series where each date is True if all departments are
            under a CR, otherwise False.

        """

        return self._check_dept_status(statuses={"CR_STATUS"})

    @property
    def all_depts_cr_or_full_approps(self) -> pd.Series:
        """
        Determines if all departments have either full appropriations or are
        under a continuing resolution on each date.

        This method is a combination check for 'DEFAULT_STATUS' (full
        appropriations) and 'CR_STATUS' (continuing resolution) for all
        departments on each date.

        Returns
        -------
        pd.Series
            A pd.Series where each date is True if all departments have either
            full appropriations or are under a CR, otherwise False.
        """

        return self._check_dept_status(statuses={"DEFAULT_STATUS", "CR_STATUS"})

    @property
    def all_unfunded(self) -> pd.Series:
        """
        Assesses if all departments are unfunded on each date.

        This method checks whether each department is either in a gap period
        ('GAP_STATUS') or a shutdown ('SHUTDOWN_STATUS') for every date in the
        index.

        Returns
        -------
        pd.Series
            A pd.Series where each date is True if all departments are unfunded
            (either in a gapped approps status or a shutdown), otherwise False.

        """

        return self._check_dept_status(statuses={"GAP_STATUS", "SHUTDOWN_STATUS"})

    @property
    def gov_cr(self) -> pd.Series:
        """
        Checks if any department is under a continuing resolution (CR) on each
        date.

        This method evaluates whether *any* department is operating under a CR
        ('CR_STATUS') for each date in the index.

        Returns
        -------
        pd.Series
            A pd.Series where each date is True if *any* department is under a CR,
            otherwise False.

        """

        return self._check_dept_status(statuses={"CR_STATUS"}, check_any=True)

    @property
    def gov_shutdown(self) -> pd.Series:
        """
        Determines if any department is in a shutdown status on each date.

        This method assesses whether *any* department is experiencing a
        shutdown /furlough ('SHUTDOWN_STATUS') for each date in the index.

        Returns
        -------
        pd.Series
            A pd.Series where each date is True if *any* department is in a
            shutdown, otherwise False.
        """

        return self._check_dept_status(statuses={"SHUTDOWN_STATUS"}, check_any=True)

    @property
    def gov_unfunded(self) -> pd.Series:
        """
        Evaluates if any department is unfunded on each date.

        This method checks whether *any* department is either in a gap status
        ('GAP_STATUS') or a shutdown/furlough ('SHUTDOWN_STATUS') on each date
        in the index.

        Returns
        -------
        pd.Series
            A pd.Series indicating if *any* department is unfunded (either in a
            gap status or a shutdown) on each respective date.

        """

        return self._check_dept_status(
            statuses={"SHUTDOWN_STATUS", "GAP_STATUS"}, check_any=True
        )

    @property
    def full_op_depts(self) -> pd.DataFrame:
        """
        Generates a pd.DataFrame detailing departments with full operational
        status on each date in the index.

        This method compiles information about departments operating under full
        appropriations ('DEFAULT_STATUS') over the index's date range. It's
        handy for identifying when each department is fully operational and
        has a full-year appropriation.

        Returns
        -------
        pd.DataFrame
            A pd.DataFrame listing departments with their operational status,
            where the status indicates full appropriations for each date in
            the index.

        """

        return self.construct_status_dataframe(statuses={"DEFAULT_STATUS"})

    @property
    def full_or_cr_depts(self) -> pd.DataFrame:
        """
        Compiles a pd.DataFrame of departments either fully funded or under a
        continuing resolution.

        This method provides a snapshot of departments that are either
        operating with full appropriations ('DEFAULT_STATUS') or under a
        continuing resolution ('CR_STATUS').

        Returns
        -------
        pd.DataFrame
            A pd.DataFrame showing departments with either full appropriations
            or under a CR for each date in the index.

        """

        return self.construct_status_dataframe(statuses={"DEFAULT_STATUS", "CR_STATUS"})

    @property
    def cr_depts(self) -> pd.DataFrame:
        """
        Creates a pd.DataFrame listing departments under a continuing
        resolution (CR).

        This method focuses on identifying departments that are operating
        under a CR ('CR_STATUS') for each date in the index. It's specifically
        tailored for tracking CR situations across departments.

        Returns
        -------
        pd.DataFrame
            A pd.DataFrame with departments that are under a CR for each date
            in the index.

        """

        return self.construct_status_dataframe(statuses={"CR_STATUS"})

    @property
    def gapped_depts(self) -> pd.DataFrame:
        """
        Generates a pd.DataFrame of departments in a funding gap period.

        This method is used to identify departments experiencing a gap in
        funding ('GAP_STATUS') over the index's date range. It highlights
        periods when departments are without proper appropriations.

        Returns
        -------
        pd.DataFrame
            A pd.DataFrame showing departments in a funding gap for each date
            in the index.

        """
        return self.construct_status_dataframe(statuses={"GAP_STATUS"})

    @property
    def shutdown_depts(self) -> pd.DataFrame:
        """
        Produces a pd.DataFrame of departments affected by a shutdown.

        This method isolates instances where departments are in a shutdown
        ('SHUTDOWN_STATUS'), providing a clear view of which departments are
        impacted and when.

        Returns
        -------
        pd.DataFrame
            A pd.DataFrame detailing departments in a shutdown for each date in
            the index.

        """
        return self.construct_status_dataframe(statuses={"SHUTDOWN_STATUS"})

    @property
    def unfunded_depts(self) -> pd.DataFrame:
        """
        Creates a pd.DataFrame highlighting departments with no current
        funding.

        This method compiles data on departments either in a gap period
        ('GAP_STATUS') or a shutdown ('SHUTDOWN_STATUS'), useful for
        understanding which departments are unfunded.

        Returns
        -------
        pd.DataFrame
            A pd.DataFrame indicating departments that are unfunded for each
            date in the index.

        """

        return self.construct_status_dataframe(
            statuses={"GAP_STATUS", "SHUTDOWN_STATUS"}
        )


def to_fedindex(date_range: FedIndexConvertibleTypes = None) -> FedIndex:
    """
    Converts a date range to a `FedIndex`.

    Parameters
    ----------
    date_range
        A date range to convert to a `FedIndex`. The date range can be any
        `FedIndexConvertibleTypes`:
            tuple[FedStampConvertibleTypes, FedStampConvertibleTypes],
            tuple[pd.Timestamp, pd.Timestamp],
            "np.np.ndarray",
            "pd.Series",
            "pd.DatetimeIndex",
            "pd.Index",
        ]

    Returns
    -------
    FedIndex
        A `FedIndex` object representing the date range.

    Examples
    --------
    ```python
    to_fedindex((("2017-10-1"), "2025-9-30"))
    to_fedindex(pd.date_range(start="2017-10-1", end="2025-9-30"))
    to_fedindex(np.arange("2017-10-1", "2025-9-30", dtype="datetime64[D]"))
    to_fedindex(pd.Series(pd.date_range(start="2017-10-1", end="2025-9-30")))
    to_fedindex(pd.Index(pd.date_range(start="2017-10-1", end="2025-9-30")))
    to_fedindex(((datetime.datetime(2000,1,1)),datetime.datetime(2010,5,30)))
    ```
    """
    date_range = time_utils.to_datetimeindex(date_range)
    return FedIndex(datetimeindex=date_range)
