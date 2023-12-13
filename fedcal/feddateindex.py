from __future__ import annotations

from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    KeysView,
    Self,
)
from pandas import DatetimeIndex, DataFrame, MultiIndex, Timestamp, Series

from ._dept_status import DepartmentState
from ._civpay import FedPayDay
from .constants import (
    CR_DATA_CUTOFF_DATE,
    DHS_FORMED,
    EXECUTIVE_DEPARTMENT,
    EXECUTIVE_DEPARTMENTS_SET,
    STATUS_MAP,
    READABLE_STATUS_MAP,
)
from ._date_attributes import FedBusDay, FedFiscalQuarter, FedFiscalYear, FedHolidays
from .feddatestamp import FedDateStamp
from ._mil import MilPayPassRange
from .time_utils import to_datestamp, to_feddateindex

if TYPE_CHECKING:
    from numpy import ndarray
    from ._typing import (
        FedDateStampConvertibleTypes,
        FedDateIndexConvertibleTypes,
        ExtractedStatusDataGeneratorType,
        StatusTupleType,
        StatusGeneratorType,
        StatusCacheType,
    )


class FedDateIndex(DatetimeIndex):
    """
    A specialized DatetimeIndex class for handling dates in a federal context.

    This class extends DatetimeIndex with additional functionality specific
    to federal dates. It includes methods and properties for handling various
    aspects of federal operations, such as paydays, department statuses, and
    fiscal years.

    Attributes
    ----------
    business_days : Series
        Series indicating business days.

    fys : Series
        Series representing fiscal years.

    fiscal_quarters : Series
        Series for fiscal quarters.

    holidays : Series
        Series indicating holidays.

    proclaimed_holidays : ndarray
        Array of boolean values for proclaimed holidays.

    possible_proclamation_holidays : ndarray
        Array of boolean values for possible proclamation holidays.

    probable_mil_passdays : Series
        Series indicating probable military pass days.

    mil_paydays : Series
        Series of military paydays.

    civ_paydays : Series
        Series of civilian paydays.

    departments : DataFrame
        DataFrame of departments.

    departments_bool : DataFrame
        DataFrame indicating department existence per date.

    all_depts_status : DataFrame
        DataFrame with status for all departments.

    all_depts_full_approps : Series
        Series for departments with full appropriations.

    all_depts_cr : Series
        Series for departments under a continuing resolution.

    all_depts_cr_or_full_approps : Series
        Series for departments under full appropriations or a CR.

    all_unfunded : Series
        Series for all unfunded departments.

    gov_cr : Series
        Series indicating any department under a CR.

    gov_shutdown : Series
        Series indicating any department in a shutdown.

    gov_unfunded : Series
        Series for any unfunded department.

    full_op_depts : DataFrame
        DataFrame of fully operational departments.

    full_or_cr_depts : DataFrame
        DataFrame of departments fully funded or under a CR.

    cr_depts : DataFrame
        DataFrame of departments under a CR.

    gapped_depts : DataFrame
        DataFrame of departments in a funding gap.

    shutdown_depts : DataFrame
        DataFrame of departments in a shutdown.

    unfunded_depts : DataFrame
        DataFrame of unfunded departments.

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
        Constructs a status DataFrame based on given criteria.

    status_dataframe_to_multiindex
        Converts a status DataFrame to a multiindex DataFrame.

    status_dataframe_to_all_bool
        Converts a status DataFrame to a boolean DataFrame.

    get_departments_status
        Retrieves the status of specified departments.

    Examples
    --------
    # Example usage
    (TODO: Beef up examples)
    fed_index = FedDateIndex(['2023-01-01', '2023-01-02'])
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
    """

    def __new__(cls, data, *args, **kwargs) -> Self:
        """
        Create a new instance of FedDateIndex.

        Parameters
        ----------
        data : array-like (1-dimensional)
            The array-like input data to create the date index.
        *args : list
            Variable length argument list.
        **kwargs : dict
            Arbitrary keyword arguments.

        Returns
        -------
        FedDateIndex
            A new instance of FedDateIndex.

        Notes
        -----
        This method overrides the `__new__` method of DatetimeIndex to apply
        custom initialization, such as setting the date range and converting
        to a FedDateIndex format.
        """
        instance: Self = super().__new__(cls, data, *args, **kwargs)
        instance = to_feddateindex(instance)
        instance.set_self_date_range()
        return instance

    # Methods for caching and other internal use to the class
    @staticmethod
    def _reverse_human_readable_status(status_str: str) -> "StatusTupleType":
        """
        Convert a human-readable status string to its corresponding status tuple.

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
        This method uses the `READABLE_STATUS_MAP` to reverse map human-readable
        status strings to their internal tuple representations.
        """

        return READABLE_STATUS_MAP.inv[status_str]

    def set_self_date_range(self) -> None:
        """
        Set the start and end date range of the FedDateIndex instance.

        Notes
        -----
        This method updates the `start` and `end` attributes of the instance
        with `FedDateStamp` objects. It defaults to the minimum and maximum of
        the index if `start` or `end` are not explicitly set.
        """
        self.start: FedDateStamp = to_datestamp(self.start or self.min())
        self.end: FedDateStamp = to_datestamp(self.end or self.max())

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
        return MilPayPassRange(start=self.start, end=self.end)

    def _set_mil_cache(self) -> None:
        """
        Initialize or update the military cache for the instance.

        Notes
        -----
        This method sets the `_mil_cache` attribute with a `MilPayPassRange`
        object. If `_mil_cache` is already set, it leaves it unchanged.
        Otherwise, it calls `_get_mil_cache` to generate and set the cache.
        """

        self._mil_cache: MilPayPassRange = self._mil_cache or self._get_mil_cache()

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
        `FedDateIndex`'s primary means of retrieving statuses for Federal
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
        self.states = DepartmentState()
        return DepartmentState.get_state_for_range_generator(
            start=self.start, end=self.end
        )

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
        department_filter: set[EXECUTIVE_DEPARTMENT] | None = None,
    ) -> "ExtractedStatusDataGeneratorType":
        """
        Extract status data based on specified statuses and department filters.
        This is a helper/retriever method for `construct_status_dataframe`. It
        fetches data for specified departments and/or
        Parameters
        ----------
        statuses : set[str] or None, optional
            Set of status strings to filter by. If None, uses all status keys.
            Valid status keys (keys are the keys to `constants.STATUS_MAP`).

        department_filter : set[EXECUTIVE_DEPARTMENT] or None, optional
            Set of departments to filter by. If None, uses all executive
            departments. Inputs are a set of EXECUTIVE_DEPARTMENT enum objects.

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

        statuses: set[str] | KeysView[str] = statuses or STATUS_MAP.keys()
        department_filter = department_filter or EXECUTIVE_DEPARTMENTS_SET

        data_check_statuses: set[str] = {"DEFAULT_STATUS", "CR_STATUS"}

        for date, department_statuses in (
            data_input.items() if isinstance(data_input, dict) else data_input
        ):
            if to_datestamp(date).fedtimestamp < CR_DATA_CUTOFF_DATE and any(
                status in statuses for status in data_check_statuses
            ):
                adjusted_statuses: set["StatusTupleType"] = {
                    STATUS_MAP[key]
                    for key in statuses
                    if key not in data_check_statuses
                } | {STATUS_MAP["CR_DATA_CUTOFF_DEFAULT_STATUS"]}
            else:
                adjusted_statuses: set["StatusTupleType"] = {
                    STATUS_MAP[key] for key in statuses
                }

            for department, fed_department_instance in department_statuses.items():
                status_tuple: StatusTupleType = (
                    fed_department_instance.to_status_tuple()
                )
                if (
                    department in department_filter
                    and status_tuple in adjusted_statuses
                ):
                    yield (to_datestamp(date), fed_department_instance)

    def _check_dept_status(self, statuses: set[str], check_any: bool = False) -> Series:
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
            keys to `constants.STATUS_MAP`.
        check_any : bool, optional
            If True, checks if any department matches the statuses. If False,
            checks if all departments match. Defaults to False.

        Returns
        -------
        Series
            A boolean Pandas Series indicating whether each date matches the
            criteria.

        Notes
        -----
        This method constructs a dataframe from status data and department
        data, then applies the specified logic (any or all) to determine if
        the departments match the given statuses for each date.
        """

        status_df: DataFrame = self.construct_status_dataframe(
            statuses=statuses
        ).set_index(keys="Date")
        dept_df: DataFrame = self.departments.set_index(keys="Date")

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

        comparison_df: DataFrame = status_df["Departments"].apply(func=comparison_func)

        return comparison_df.any(axis=1) if check_any else comparison_df.all(axis=1)

    # utility methods

    def to_fedtimestamp(self) -> Series:
        """
        Convert the dates in the index to POSIX timestamps normalized to midnight.

        Returns
        -------
        Series
            A Pandas Series containing integer POSIX timestamps.

        Notes
        -----
        This method normalizes each date in the index to midnight and then
        converts them to POSIX timestamps (seconds since the Unix epoch).
        """

        return (
            (self.normalize() - Timestamp(ts_input="1970-01-01"))
            .total_seconds()
            .astype(dtype=int)
        )

    def contains_date(self, date: FedDateStamp | FedDateStampConvertibleTypes) -> bool:
        """
        Check if the index contains a specified date.

        Parameters
        ----------
        date : FedDateStamp or FedDateStampConvertibleTypes
        The date to check for in the index.

        Returns
        -------
        bool
        True if the date is in the index, False otherwise.

        Notes
        -----
        This method converts the input date to a `FedDateStamp`, if necessary, and
        then checks if it exists in the index.
        """

        if not isinstance(date, FedDateStamp):
            date = to_datestamp(date=date)
        return date in self

    def contains_index(
        self, other_index: "FedDateIndex" | "FedDateIndexConvertibleTypes"
    ) -> bool:
        """
        Check if the index contains a specified date.

        Parameters
        ----------
        date : FedDateStamp or FedDateStampConvertibleTypes
            The date to check for in the index.

        Returns
        -------
        bool
            True if the date is in the index, False otherwise.

        Notes
        -----
        This method converts the input date to a `FedDateStamp`, if necessary, and then checks if it exists in the index.
        """

        if not isinstance(other_index, FedDateIndex):
            other_index = to_feddateindex(other_index)
        return other_index.isin(values=self).all()

    def overlaps_index(
        self, other_index: "FedDateIndex" | "FedDateIndexConvertibleTypes"
    ) -> bool:
        """
        Check if the index overlaps with another index.

        Parameters
        ----------
        other_index : FedDateIndex or FedDateIndexConvertibleTypes
            The other index to check for overlap.

        Returns
        -------
        bool
            True if any date from the other index is in this index, False otherwise.

        Notes
        -----
        This method converts the input index to a `FedDateIndex`, if
        necessary, and then checks for any overlapping dates using the `isin`
        method.
        """

        if not isinstance(other_index, FedDateIndex):
            other_index = to_feddateindex(other_index)
        return other_index.isin(values=self).any()

    def construct_status_dataframe(
        self,
        statuses: set[str] | None = None,
        department_filter: set[EXECUTIVE_DEPARTMENT] | None = None,
    ) -> DataFrame:
        """
        Primary constructor method for `FedDateIndex`s department status
        properties. Outputs a human readable DataFrame of data for the given
        status and department inputs. For deeper analysis, may be optionally
        converted with the status_dataframe_to_multiindex() and
        status_dataframe_to_all_bool() methods.

        Parameters
        ----------
        statuses : set[str] or None, optional
        Set of status keys to include. If None, includes all statuses.
        Valid keys are keys to `constants.STATUS_MAP`.

        department_filter : set[EXECUTIVE_DEPARTMENT] or None, optional
        Set of departments to include. If None, includes all departments.
        Valid inputs are EXECUTIVE_DEPARTMENT enum objects.

        Returns
        -------
        DataFrame
        A Pandas DataFrame with columns for date, department, and status.

        Notes
        -----
        This method extracts status data based on the given filters and
        constructs a DataFrame from it, with each row representing a
        date-department-status trio.
        """

        extracted_data: "ExtractedStatusDataGeneratorType" = self._extract_status_data(
            statuses=statuses, department_filter=department_filter
        )
        rows: list[Any] = []
        for date, fed_department_instance in extracted_data:
            row: dict[str, Any] = {
                "Date": date,
                "Department": fed_department_instance.name.SHORT,
                "Status": fed_department_instance.status,
            }
            rows.append(row)
        return DataFrame(data=rows)

    def status_dataframe_to_multiindex(self, df: DataFrame) -> DataFrame:
        """
        Convert a status dataframe generated by construct_status_dataframe to
        a multi-indexed dataframe.

        Parameters
        ----------
        df : DataFrame
            The dataframe with status information to convert.

        Returns
        -------
        DataFrame
            A Pandas DataFrame with a multi-index (Date, Department,
            FundingStatus, OperationalStatus).

        Notes
        -----
        This method iterates over the given dataframe and converts each row
        into a tuple representing the multi-index structure, then constructs a
        new DataFrame with these tuples as the index.
        """

        multiindex_data: list[Any] = []
        for _, row in df.iterrows():
            date: FedDateStamp = row["Date"]
            department_short: str = row["Department"]
            human_readable_status: str = row["Status"]

            department_enum: EXECUTIVE_DEPARTMENT = (
                EXECUTIVE_DEPARTMENT.from_short_name(short_name=department_short)
            )
            funding_status, operational_status = self._reverse_human_readable_status(
                status_str=human_readable_status
            )

            multiindex_data.append(
                (date, department_enum, funding_status, operational_status)
            )

        multiindex: MultiIndex = MultiIndex.from_tuples(
            tuples=multiindex_data,
            names=["Date", "Department", "FundingStatus", "OperationalStatus"],
        )
        return DataFrame(index=multiindex).reset_index()

    def status_dataframe_to_all_bool(self, df: DataFrame) -> DataFrame:
        """
        Convert a DataFrame generated by construct_status_dataframe() with
        departments and statuses into a boolean DataFrame.

        This method takes a DataFrame with 'Department' and 'Status' columns
        and transforms it into a DataFrame where each column represents a
        combination of a department and a status, filled with boolean values.

        Parameters
        ----------
        df : DataFrame
            A DataFrame containing 'Date', 'Department', and 'Status' columns.

        Returns
        -------
        DataFrame
            A transformed DataFrame with columns for each department-status
            combination, filled with boolean values indicating the presence
            of each department-status pair.
        """

        unique_departments: "ndarray"[str] = df["Department"].unique()
        unique_statuses: "ndarray"[str] = df["Status"].unique()

        columns: list[str] = [
            f"{dept}-{status}"
            for dept in unique_departments
            for status in unique_statuses
        ]
        bool_df: DataFrame = DataFrame(index=df.index, columns=columns).fillna(
            value=False
        )

        for index, row in df.iterrows():
            date = row["Date"]
            department_short: str = row["Department"]
            human_readable_status: str = row["Status"]

            col_name: str = f"{department_short}-{human_readable_status}"
            bool_df.at[index, col_name] = True

        return bool_df.reset_index(drop=True)

    def get_departments_status(
        self, departments: set[EXECUTIVE_DEPARTMENT]
    ) -> DataFrame:
        """
        Generate a DataFrame of department statuses for a given set of
        departments.

        This method provides a DataFrame detailing the statuses for a specific
        set of departments over the `FedDateIndex`'s date range.

        Parameters
        ----------
        departments : set of EXECUTIVE_DEPARTMENT
            A set of EXECUTIVE_DEPARTMENT enum objects for which to retrieve
            status information.

        Returns
        -------
        DataFrame
            A DataFrame containing status information for the specified
            departments.

        """

        self._set_status_cache()
        return self.construct_status_dataframe(
            statuses={"all"}, department_filter=departments
        )

    # Begin date attribute property methods
    @property
    def business_days(self) -> Series:
        """
        Determine if the dates in the index are Federal business days.

        This property checks each date in the index to see if it is a business
        day, based on federal business day rules.

        Returns
        -------
        Series
            A Pandas Series of boolean values, where True indicates a business day.

        """

        next_business_days = self + FedBusDay.fed_business_days
        return self == next_business_days

    @property
    def fys(self) -> Series:
        """
        Retrieve the fiscal years for each date in the index.

        This property maps each date in the index to its corresponding federal
        fiscal year.

        Returns
        -------
        Series
            A Pandas Series with the fiscal year for each date in the index.

        """

        return FedFiscalYear.get_fiscal_years(datetimeindex=self)

    @property
    def fiscal_quarters(self) -> Series:
        """
        Obtain the fiscal quarters for each date in the index.

        This property identifies the federal fiscal quarter for each date in
        the index.

        Returns
        -------
        Series
            A Pandas Series with the fiscal quarter for each date in the index.

        """
        return FedFiscalQuarter.get_fiscal_quarters(datetimeindex=self)

    @property
    def holidays(self) -> Series:
        """
        Identify federal holidays in the index.

        This property checks each date in the index to determine if it is a
        federal holiday.

        Returns
        -------
        Series
            A Pandas Series of boolean values, where True indicates a federal
            holiday.
        """

        next_holidays: DatetimeIndex = self + FedHolidays.holidays
        return self == next_holidays

    @property
    def proclaimed_holidays(self) -> "ndarray":
        """
        Check for proclaimed federal holidays in the index.

        This property identifies dates in the index that are proclaimed federal
        holidays.

        Returns
        -------
        ndarray
            An ndarray of boolean values, where True indicates a proclaimed
            federal
            holiday.

        """
        return self.isin(values=DatetimeIndex(data=FedHolidays.proclaimed_holidays))

    @property
    def possible_proclamation_holidays(self) -> "ndarray":
        """
        Guesses if the dates in the index are possible *future* proclamation
        federal holidays.

        Returns
        -------
        Pandas Series of boolean values indicating possible proclamation
        holidays.

        Notes
        -----
        See notes to FedDateStamp.possible_proclamation_holiday.

        """
        return FedHolidays.guess_proclamation_holidays(datetimeindex=self)

    @property
    def probable_mil_passdays(self) -> Series:
        """
        Estimate military pass days within the index's date range.

        This property calculates the probable military pass days based on the
        index's date range and internal military cache data. See notes on
        similar properties in FedDateStamp; while this will be mostly
        accurate, specific dates for passes vary between commands and locales.

        Returns
        -------
        Series
            A Pandas Series indicating probable military pass days.

        """

        self._set_mil_cache()
        return self._mil_cache.get_milpass_series()

    # Payday properties
    @property
    def mil_paydays(self) -> Series:
        """
        Identify military payday dates within the index.

        This property uses the index's date range and military cache data to
        determine the dates that are military paydays.

        Returns
        -------
        Series
            A Pandas Series indicating military payday dates.

        """

        self._set_mil_cache()
        return self._mil_cache.get_milpay_series()

    @property
    def civ_paydays(self) -> Series:
        """
        Determine civilian payday dates within the index's date range.

        This property calculates the dates that are civilian paydays based on the index's date range.

        Returns
        -------
        Series
            A Pandas Series indicating civilian payday dates.

        """

        self.set_self_date_range()
        return FedPayDay.get_paydays_as_series(start=self.start, end=self.end)

    @property
    def departments(self) -> DataFrame:
        """
        Create a DataFrame of departments active on each date in the index.

        This property generates a DataFrame where each row corresponds to a
        date in the index, listing the active executive departments on that
        date and adjusting for the formation of DHS.

        Returns
        -------
        DataFrame
            A DataFrame with each date in the index and the active departments
            on that date.
        """

        all_depts: list[str] = ", ".join(
            [dept.SHORT for dept in EXECUTIVE_DEPARTMENTS_SET]
        )
        pre_dhs_depts: list[str] = ", ".join(
            [
                dept.SHORT
                for dept in EXECUTIVE_DEPARTMENTS_SET.difference(
                    EXECUTIVE_DEPARTMENT.DHS
                )
            ]
        )

        dept_df: DataFrame = self.to_frame(name="Departments")
        dept_df["Departments"] = dept_df.index.map(
            mapper=lambda date: all_depts if date >= DHS_FORMED else pre_dhs_depts
        )
        return dept_df

    @property
    def departments_bool(self) -> DataFrame:
        """
        Generates a DataFrame indicating whether each department exists on
        each date in the index.

        This method specifically accounts for the formation of the
        Department of Homeland Security (DHS). Dates prior to DHS's
        formation will have a False value for DHS.

        Returns
        -------
        DataFrame
            A DataFrame with the index as dates and columns as department
            short names. Each cell is True if the department exists on that
            date, except for DHS before its formation date, which is False.
        """

        dept_columns: list[str] = [dept.SHORT for dept in EXECUTIVE_DEPARTMENT]
        df: DataFrame = DataFrame(index=self, columns=dept_columns).fillna(value=True)

        # Adjust for DHS
        dhs_start_date: FedDateStamp | None = to_datestamp(date=DHS_FORMED)
        df.loc[df.index < dhs_start_date, "DHS"] = False

        return df

    @property
    def all_depts_status(self) -> DataFrame:
        """
        Provides a status DataFrame for all departments over the entire date range.

        This method leverages the internal status cache to obtain the status
        information for all departments. It's useful for getting a
        comprehensive overview of the status across all departments for the
        index's range.

        Returns
        -------
        DataFrame
            A DataFrame with status information for all departments across the
            index's date range.
        """

        self._set_status_cache()
        return self.construct_status_dataframe(statuses={"all"})

    @property
    def all_depts_full_approps(self) -> Series:
        """
        Determines if all departments have full appropriations on each date.

        This method checks whether each department is operating under full
        appropriations ('DEFAULT_STATUS') for every date in the index.

        Returns
        -------
        Series
            A Pandas Series where each date is True if all departments have
            full appropriations, otherwise False.

        """

        return self._check_dept_status(statuses={"DEFAULT_STATUS"})

    @property
    def all_depts_cr(self) -> Series:
        """
        Checks if all departments are under a continuing resolution (CR) on each date.

        This method assesses whether each department is operating under a
        continuing resolution ('CR_STATUS') for every date in the index.

        Returns
        -------
        Series
            A Pandas Series where each date is True if all departments are
            under a CR, otherwise False.

        """

        return self._check_dept_status(statuses={"CR_STATUS"})

    @property
    def all_depts_cr_or_full_approps(self) -> Series:
        """
        Determines if all departments have either full appropriations or are
        under a continuing resolution on each date.

        This method is a combination check for 'DEFAULT_STATUS' (full
        appropriations) and 'CR_STATUS' (continuing resolution) for all
        departments on each date.

        Returns
        -------
        Series
            A Series where each date is True if all departments have either full appropriations or are under a CR, otherwise False.
        """

        return self._check_dept_status(statuses={"DEFAULT_STATUS", "CR_STATUS"})

    @property
    def all_unfunded(self) -> Series:
        """
        Assesses if all departments are unfunded on each date.

        This method checks whether each department is either in a gap period
        ('GAP_STATUS') or a shutdown ('SHUTDOWN_STATUS') for every date in the
        index.

        Returns
        -------
        Series
            A Series where each date is True if all departments are unfunded
            (either in a gapped approps status or a shutdown), otherwise False.

        """

        return self._check_dept_status(statuses={"GAP_STATUS", "SHUTDOWN_STATUS"})

    @property
    def gov_cr(self) -> Series:
        """
        Checks if any department is under a continuing resolution (CR) on each date.

        This method evaluates whether *any* department is operating under a CR
        ('CR_STATUS') for each date in the index.

        Returns
        -------
        Series
            A Series where each date is True if *any* department is under a CR,
            otherwise False.

        """

        return self._check_dept_status(statuses={"CR_STATUS"}, check_any=True)

    @property
    def gov_shutdown(self) -> Series:
        """
        Determines if any department is in a shutdown status on each date.

        This method assesses whether *any* department is experiencing a shutdown
        /furlough ('SHUTDOWN_STATUS') for each date in the index.

        Returns
        -------
        Series
            A Series where each date is True if *any* department is in a
            shutdown, otherwise False.
        """

        return self._check_dept_status(statuses={"SHUTDOWN_STATUS"}, check_any=True)

    @property
    def gov_unfunded(self) -> Series:
        """
        Evaluates if any department is unfunded on each date.

        This method checks whether *any* department is either in a gap status
        ('GAP_STATUS') or a shutdown/furlough ('SHUTDOWN_STATUS') on each date
        in the index.

        Returns
        -------
        Series
            A Series indicating if *any* department is unfunded (either in a
            gap status or a shutdown) on each respective date.

        """

        return self._check_dept_status(
            statuses={"SHUTDOWN_STATUS", "GAP_STATUS"}, check_any=True
        )

    @property
    def full_op_depts(self) -> DataFrame:
        """
        Generates a DataFrame detailing departments with full operational
        status on each date in the index.

        This method compiles information about departments operating under full
        appropriations ('DEFAULT_STATUS') over the index's date range. It's
        handy for identifying when each department is fully operational and
        has a full-year appropriation.

        Returns
        -------
        DataFrame
            A DataFrame listing departments with their operational status,
            where the status indicates full appropriations for each date in
            the index.

        """

        return self.construct_status_dataframe(statuses={"DEFAULT_STATUS"})

    @property
    def full_or_cr_depts(self) -> DataFrame:
        """
        Compiles a DataFrame of departments either fully funded or under a
        continuing resolution.

        This method provides a snapshot of departments that are either
        operating with full appropriations ('DEFAULT_STATUS') or under a
        continuing resolution ('CR_STATUS').

        Returns
        -------
        DataFrame
            A DataFrame showing departments with either full appropriations or
            under a CR for each date in the index.

        """

        return self.construct_status_dataframe(statuses={"DEFAULT_STATUS", "CR_STATUS"})

    @property
    def cr_depts(self) -> DataFrame:
        """
        Creates a DataFrame listing departments under a continuing resolution (CR).

        This method focuses on identifying departments that are operating
        under a CR ('CR_STATUS') for each date in the index. It's specifically
        tailored for tracking CR situations across departments.

        Returns
        -------
        DataFrame
            A DataFrame with departments that are under a CR for each date in
        the index.

        """

        return self.construct_status_dataframe(statuses={"CR_STATUS"})

    @property
    def gapped_depts(self) -> DataFrame:
        """
        Generates a DataFrame of departments in a funding gap period.

        This method is used to identify departments experiencing a gap in
        funding ('GAP_STATUS') over the index's date range. It highlights
        periods when departments are without proper appropriations.

        Returns
        -------
        DataFrame
            A DataFrame showing departments in a funding gap for each date in
            the index.

        """

        return self.construct_status_dataframe(statuses={"GAP_STATUS"})

    @property
    def shutdown_depts(self) -> DataFrame:
        """
        Produces a DataFrame of departments affected by a shutdown.

        This method isolates instances where departments are in a shutdown
        ('SHUTDOWN_STATUS'), providing a clear view of which departments are
        impacted and when.

        Returns
        -------
        DataFrame
            A DataFrame detailing departments in a shutdown for each date in
            the index.

        """

        return self.construct_status_dataframe(statuses={"SHUTDOWN_STATUS"})

    @property
    def unfunded_depts(self) -> DataFrame:
        """
        Creates a DataFrame highlighting departments with no current funding.

        This method compiles data on departments either in a gap period
        ('GAP_STATUS') or a shutdown ('SHUTDOWN_STATUS'), useful for
        understanding which departments are unfunded.

        Returns
        -------
        DataFrame
            A DataFrame indicating departments that are unfunded for each date
            in the index.

        """

        return self.construct_status_dataframe(
            statuses={"GAP_STATUS", "SHUTDOWN_STATUS"}
        )


@to_feddateindex.register(cls=FedDateIndex)
def _from_feddateindex(input_dates) -> "FedDateIndex":
    """
    We catch and return stray FedDateIndex objects that happen into our net.
    A lonely refugee from the parent function in .time_utils, here to avoid
    circular import issues until we can implement a more permanent fix.
    """
    return input_dates
