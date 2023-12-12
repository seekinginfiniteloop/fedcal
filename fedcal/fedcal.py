from __future__ import annotations

from datetime import date, datetime
from typing import (
    TYPE_CHECKING,
    Any,
    KeysView,
    List,
    Self,
)
from pandas import DatetimeIndex, DataFrame, MultiIndex, Timestamp, Index

from ._dept_status import DepartmentState
from .civpay import FedPayDay
from .constants import (
    CR_DATA_CUTOFF_DATE,
    DHS_FORMED,
    EXECUTIVE_DEPARTMENT,
    EXECUTIVE_DEPARTMENTS_SET,
    STATUS_MAP,
    READABLE_STATUS_MAP
    EXECUTIVE_DEPARTMENT
)
from .date_attributes import FedBusDay, FedFiscalQuarter, FedFiscalYear, FedHolidays
from .depts import FedDepartment
from .mil import MilitaryPayDay, MilPayPassRange, ProbableMilitaryPassDay
from .time_utils import YearMonthDay, _pydate_to_posix, to_datestamp, to_feddateindex

if TYPE_CHECKING:
    from pandas import Series
    from numpy import ndarray
    from ._dept_status import FedDepartment
    from ._typing import (
        FedDateStampConvertibleTypes,
        ExtractedStatusDataGeneratorType,
        StatusDictType,
        StatusTupleType,
        StatusGeneratorType,
        StatusCacheType,
    )


class FedDateStamp(Timestamp):
    """
    A child class of pandas Timestamp, extending functionality for
    fedcal. Supports all functionalities of pandas' Timestamp
    objects, while adding specific features for the fedcal.

    Attributes
    ----------
    No attributes at initialization except those inherited from pandas'
    Timestamp.

    self._status_cache : A *private* lazy attribute that caches StatusDictType
    dictionary (Dict[EXECUTIVE_DEPARTMENT, FedDepartment]) from _dept_status.
    DepartmentState for the date for supplying status-related properties.
    Provided by _get_status_cache() and _set_status_cache() private methods.

    Methods
    -------
    dict_to_dept_set(status_dict)
        Converts a StatusDictType dictionary to a set of EXECUTIVE_DEPARTMENT
        enum objects.

    dict_to_dept_list(status_dict)
        Utility method that converts a status dictionary (which most of the
        status-related property methods return) to a sorted list of
        EXECUTIVE_DEPARTMENT enum objects.

    dict_to_feddept_list(status_dict)
        Utility method that converts a status dictionary (which most of the
        status-related property methods return) to a sorted list of
        FedDepartment objects.

    get_departments_by_status(status_key)
        Retrieves departments matching a specific status, primary getter for
        status-related property methods.

    year_month_day
        returns the FedDateStamp as a YearMonthDay object.

    fedtimestamp
        Returns the POSIX timestamp normalized to midnight.

    business_day
        Checks if the date is a business day.

    holiday
        Checks if the date is a federal holiday.

    proclamation_holiday
        Checks if the date was a proclaimed holiday (i.e. a one-off holiday proclaimed by executive order).

    possible_proclamation_holiday
        Guesses (I take no further ownership of the result) if the date is likely to be a proclaimed holiday.

    probable_military_passday
        Estimates if the date is likely a military pass day. Actual passdays
        vary across commands and locations, but this should return a result
        that's correct in the majority of cases.

    mil_payday
        Checks if the date is a military payday.

    civ_payday
        Checks if the date is a civilian payday.

    fiscal_quarter
        Retrieves the [Federal] fiscal quarter of the timestamp.

    fy
        Retrieves the [Federal] fiscal year of the timestamp.

    departments
        Retrieves the set of executive departments active on the date, as
        EXECUTIVE_DEPARTMENT enum objects.

    all_depts_status
        Retrieves the status of all departments as a dictionary on the date.

    all_depts_full_approps
        Checks if all departments are fully appropriated on the date,
        returning bool.

    all_depts_cr
        Checks if all departments were/are under a continuing resolution on
        the date, returning bool.

    all_depts_cr_or_full_approps
        Checks if all departments were/are either fully appropriated or under
        a continuing resolution on the date, returning bool.

    all_unfunded
        Checks if all departments were/are unfunded on the date (either
        shutdown or otherwise gapped), returning bool.

    cr
        Checks if the date was during a continuing resolution (can include
        near-future dates since we know CR expiration dates at the time they
        are passed), returning bool.

    shutdown
        Checks if the date was/is during a shutdown, returning bool.

    approps_gap
        Checks if the date was/is during an appropriations gap, returning bool.

    funding_gap
        Check if the date was/is during a funding gap (appropriations gap or shutdown), returning bool.

    full_op_depts
        Retrieves departments that were fully operational (had a full-year
        appropriation) on the date, returning a dict.

    full_or_cr_depts
        Retrieves departments that were/are either fully operational or under
        a continuing resolution on the date, returning a dict.

    cr_depts
        Retrieves departments that were/are under a continuing resolution on
        the date, returning a dict. Current data are from FY99 to present. As
        discussed above for cr, these can include near future dates.

    gapped_depts
        Retrieves departments that were/are in an appropriations gap on the
        date but not shutdown, returning a dict. Notably, these are isolated
        to the 1970s and early 80s.

    shutdown_depts
        Retrieves departments that were/are shut down on the date. Data
        available from FY75 to present.

    unfunded_depts
        Retrieves departments that were/are unfunded on the date (either
        gapped or shutdown), returning a dict.

    Notes
    -----
    *Private Methods*:
    _get_status_cache()
        Retrieves the status cache.

    _set_status_cache()
        Sets the status cache if not already set.
    """

    def __new__(cls, ts_input=None, *args, **kwargs) -> Self:
        """
        We ensure new instances mirror Timestamp behavior and pass any args/
        kwargs. Like Timestamp, if you don't pass a date, FedDateStamp will
        initialize for today.
        """
        if ts_input is None:
            ts_input: Timestamp = datetime.now()

        return super().__new__(cls, ts_input, *args, **kwargs)

    # static utility methods
    @staticmethod
    def dict_to_dept_set(status_dict: "StatusDictType") -> set["EXECUTIVE_DEPARTMENT"]:
        """
        Convert a status dictionary to a set of executive departments.

        Parameters
        ----------
        status_dict : A dictionary mapping departments to their statuses from
        a dictionary structure (StatusDictType) supplied by most of
        FedDateStamp's status-related property methods.

        Returns
        -------
        A set representing the departments.
        """
        return set(status_dict.keys())

    @staticmethod
    def dict_to_dept_set(status_dict: "StatusDictType") -> set["FedDepartment"]:
        """
        Convert a status dictionary to a sorted list of executive departments.

        Parameters
        ----------
        status_dict
            A dictionary mapping departments to their statuses.

        Returns
        -------
        A sorted list representing the departments.
        """
        return set(status_dict.values())

    @staticmethod
    def dict_to_dept_list(
        status_dict: "StatusDictType",
    ) -> List["EXECUTIVE_DEPARTMENT"]:
        """
        Convert a status dictionary to a sorted list of executive departments.

        Parameters
        ----------
        status_dict
            A dictionary mapping departments to their statuses.

        Returns
        -------
        A sorted list representing the departments.
        """
        return sorted(list(status_dict.keys()))

    @staticmethod
    def dict_to_feddept_list(status_dict: "StatusDictType") -> list["FedDepartment"]:
        """
        Convert a status dictionary to a sorted list of FedDepartment objects.

        Parameters
        ----------
        status_dict
            A dictionary mapping departments to their FedDepartment objects.

        Returns
        -------
        A sorted list of FedDepartment objects.
        """
        return sorted(list(status_dict.values()))

    # caching methods
    def _get_status_cache(self) -> "StatusDictType":
        """
        Retrieve the current status cache.

        Returns
        -------
        The current status cache, mapping departments to their statuses.
        """
        self.state = DepartmentState()
        return DepartmentState.get_state(date=self)

    def _set_status_cache(self) -> None:
        """
        Set the status cache if not already set.
        """
        self.status_cache: "StatusDictType" = (
            self.status_cache or self._get_status_cache()
        )

    # getter methods for retrieving from cache by department and by status

    def get_departments_by_status(self, status_key: str) -> "StatusDictType":
        """
        Retrieve departments matching a specific status. This is the primary
        getter method for FedDateStamp's status-related property methods.

        Parameters
        ----------
        status_key
            The key representing the status to filter departments by.

        Returns
        -------
        A dictionary of departments and their status, filtered by the
        specified status key.
        """
        self._set_status_cache()
        cache: "StatusDictType" | None = self.status_cache

        if self.timestamp() < CR_DATA_CUTOFF_DATE and status_key in {
            "DEFAULT_STATUS",
            "CR_STATUS",
        }:
            status_key = "CR_DATA_CUTOFF_DEFAULT_STATUS"

        target_status: "StatusTupleType" | None = STATUS_MAP.get(
            status_key)

        if cache is None or target_status is None:
            return {}

        return {
            dept: fed_dept
            for dept, fed_dept in cache.items()
            if fed_dept.to_status_tuple() == target_status
        }

    # utility properties
    @property
    def year_month_day(self) -> YearMonthDay:
        """
        Returns a YearMonthDay object for the date.

        Returns
        -------
        A YearMonthDay object representing the year, month, and day of the
        timestamp.
        """
        return YearMonthDay(year=self.year, month=self.month, day=self.day)

    @property
    def fedtimestamp(self) -> int:
        """
        Built for internal use in fedcal, variation of Timestamp.timestamp()
        method, which remains available. Returns the number of seconds since
        the Unix epoch (1970-01-01 00:00:00 UTC) as an integer normalized to
        midnight (vice pandas' return of a float).

        Returns
        -------
        Integer POSIX timestamp in seconds.
        """
        date_obj: date = date(year=self.year, month=self.month, day=self.day)
        return _pydate_to_posix(pydate=date_obj)

    # business day property
    @property
    def business_day(self) -> bool:
        """
        Checks if the date is a [Federal] business day.

        Returns
        -------
        True if the date is a business day, False otherwise.
        """
        return FedBusDay.is_bday(date=self)

    # holiday properties
    @property
    def holiday(self) -> bool:
        """
        Checks if the date is a federal holiday.

        Returns
        -------
        True if the date is a federal holiday, False otherwise.

        Notes
        -----
        This property is built on pandas' USFederalHolidayCalendar, but
        supplemented with historical holidays proclaimed by the President
        from FY74 to present (no known examples before that year).
        """
        return FedHolidays.is_holiday(date=self)

    @property
    def proclamation_holiday(self) -> bool:
        """
        Checks if the date was an out-of-cycle holiday proclaimed by executive
        order. Data available from FY74 to present (no known instances before
        that time).

        Returns
        -------
        True if the timestamp was a proclaimed holiday, False otherwise.
        """
        return FedHolidays.was_proclaimed_holiday(date=self)

    @property
    def possible_proclamation_holiday(self) -> bool:
        """
        If given a future date, guesses if it may be a proclaimed holiday.

        Returns
        -------
        True if the timestamp is a proclaimed holiday, False otherwise.

        Notes
        -----
        This method is probably very inaccurate, and uses a simple heuristic
        method based on the day of week Christmas and Christmas Eve fall
        (nearly all President-proclaimed holidays were for Christmas Eve).
        A quick analysis of historical trends suggests that these proclamations
        are highly variable and most closely correlated with the President or
        recency of the President issuing them than the date. For example,
        Presidents' Obama and Trump are responsible for 55% of of
        proclamations, and 73% occurred after the year 2000.
        """
        return FedHolidays.guess_christmas_eve_proclamation_holiday(date=self)

    @property
    def probable_mil_passday(self) -> bool:
        """
        Estimates if the timestamp is likely a military pass day.

        Returns
        -------
        True if the timestamp is likely a military pass day, False otherwise.

        Notes
        -----
        Future versions of this method will add customization options for the
        heuristic used to determine these dates. Military passdays associated
        with holidays are highly variable across commands and locations based
        on a range of factors. However, the majority fall into a reasonably
        predictable pattern. Results from this method should be accurate for
        the majority of cases, and otherwise provide an approximation
        for predictable gaps in military person-power.
        """
        return ProbableMilitaryPassDay.is_likely_passday(date=self)

    # payday properties
    @property
    def mil_payday(self) -> bool:
        """
        Checks if the date is a military payday based on DFAS pay schedule.

        Returns
        -------
        True if the timestamp is a military payday, False otherwise.
        """
        return MilitaryPayDay.is_military_payday(date=self)

    @property
    def civ_payday(self) -> bool:
        """
        Checks if the date is a civilian payday.

        Returns
        -------
        True if the date is a civilian payday, False otherwise.

        Notes
        -----
        Method is based on the Federal biweekly pay schedule, which applies to
        *nearly* all, but **not all**, Federal employee.
        """
        return FedPayDay.is_fed_payday(date=self)

    # FY/FQ properties
    @property
    def fiscal_quarter(self) -> int:
        """
        Retrieves the fiscal quarter of the date.

        Returns
        -------
        An integer representing the fiscal quarter (1-4).
        """
        return FedFiscalQuarter.get_fiscal_quarter(date=self)

    @property
    def fy(self) -> int:
        """
        Retrieves the fiscal year of the date.

        Returns
        -------
        An integer representing the fiscal year (e.g. 23 for FY23).
        """
        return FedFiscalYear.get_fiscal_year(date=self)

    # department and appropriations related status properties
    @property
    def departments(self) -> set["EXECUTIVE_DEPARTMENT"]:
        """
        Retrieves the set of executive departments active on the date.

        Returns
        -------
        A set of EXECUTIVE_DEPARTMENT enums.
        """
        return DepartmentState.get_executive_departments_set_at_time(date=self)

    @property
    def all_depts_status(self) -> "StatusDictType":
        """
        Retrieves the status of all departments.

        Returns
        -------
        A StatusDictType mapping each department to its status on the date.
        """
        self._set_status_cache()
        return self.status_cache

    @property
    def all_depts_full_approps(self) -> bool:
        """
        Checks if all departments were/are fully appropriated on the date.

        Returns
        -------
        True if all departments are fully appropriated, False otherwise.
        """
        self._set_status_cache()
        return self.dict_to_dept_set(status_dict=self.full_op_depts) == self.departments

    @property
    def all_depts_cr(self) -> bool:
        """
        Checks if all departments are/were under a continuing resolution on the date.

        Returns
        -------
        True if all departments are under a continuing resolution, False otherwise.
        """
        self._set_status_cache()
        return (
            self.dict_to_dept_set(
                status_dict=self.get_departments_by_status(status_key="CR_STATUS")
            )
            == self.departments
        )

    @property
    def all_depts_cr_or_full_approps(self) -> bool:
        """
        Checks if all departments were/are either fully appropriated or under a continuing resolution on the date.

        Returns
        -------
        True if all departments are either fully appropriated or under a continuing resolution, False otherwise.
        """
        self._set_status_cache()
        return (
            self.dict_to_dept_set(status_dict=self.full_or_cr_depts) == self.departments
        )

    @property
    def all_unfunded(self) -> bool:
        """
        Checks if all departments were/are unfunded (appropriations gap or shutdown) on the date.

        Returns
        -------
        True if all departments are unfunded, False otherwise.
        """
        self._set_status_cache()
        return (
            self.dict_to_dept_set(status_dict=self.unfunded_depts) == self.departments
        )

    @property
    def cr(self) -> bool:
        """
        Returns True if the timestamp is a continuing resolution date, False
        otherwise.
        """
        self._set_status_cache()
        return bool(self.cr_depts)

    @property
    def shutdown(self) -> bool:
        """
        Checks if *any* departments were/are shutdown on the date.

        Returns
        -------
        True if the timestamp is during a shutdown, False otherwise.
        """
        self._set_status_cache()
        return bool(self.shutdown_depts)

    @property
    def approps_gap(self) -> bool:
        """
        Checks if the date was/is during an appropriations gap for *any*
        departments.

        Returns
        -------
        True if the date is during an appropriations gap, False otherwise.
        """
        self._set_status_cache()
        return bool(self.gapped_depts)

    @property
    def funding_gap(self) -> bool:
        """
        Checks if any departments were/are either subject to a gap in
        appropriations or shutdown on the date.

        Returns
        -------
        True if the date is during a funding gap.
        """
        self._set_status_cache()
        return bool(self.gapped_depts | self.shutdown_depts)

    @property
    def full_op_depts(self) -> "StatusDictType" | None:
        """
        Retrieves departments that were/are fully operational (i.e. had
        full-year appropriations) on the date.

        Returns
        -------
        A StatusDictType dictionary representing departments that are fully
        operational.
        """
        self._set_status_cache()
        return self.get_departments_by_status(status_key="DEFAULT_STATUS")

    @property
    def full_or_cr_depts(self) -> "StatusDictType" | None:
        """
        Retrieves departments that were/are either fully operational or under
        a continuing resolution on the date.

        Returns
        -------
        A StatusDictType dictionary representing departments that are either
        fully operational or under a continuing resolution.
        """
        return self.get_departments_by_status(
            status_key="DEFAULT_STATUS"
        ) | self.get_departments_by_status(status_key="CR_STATUS")

    @property
    def cr_depts(self) -> "StatusDictType" | None:
        """
        Retrieves departments that were/are under a continuing resolution on
        the date.

        Returns
        -------
        A StatusDictType dictionary representing departments that are under a
        continuing resolution.
        """
        return self.get_departments_by_status(status_key="CR_STATUS")

    @property
    def gapped_depts(self) -> "StatusDictType" | None:
        """
        Retrieves departments that were/are under an appropriations gap on the
        date (but not shutdown).

        Returns
        -------
        A StatusDictType dictionary representing departments that are in an
        appropriations gap.
        """
        return self.get_departments_by_status(status_key="GAP_STATUS")

    @property
    def shutdown_depts(self) -> "StatusDictType" | None:
        """
        Retrieves departments that were/are shut down for the date.

        Returns
        -------
        A StatusDictType dictionary representing departments that are shut
        down.
        """
        return self.get_departments_by_status(status_key="SHUTDOWN_STATUS")

    @property
    def unfunded_depts(self) -> "StatusDictType" | None:
        """
        Retrieves departments that were/are unfunded for the date
        (either under an appropriations gap or fully shutdown).

        Returns
        -------
        A StatusDictType dictionary representing departments that are unfunded.
        """
        return self.get_departments_by_status(
            status_key="SHUTDOWN_STATUS"
        ) | self.get_departments_by_status(status_key="GAP_STATUS")

class FedDateIndex(DatetimeIndex):
    def __new__(cls, data, *args, **kwargs) -> Self:
        instance: Self = super().__new__(cls, data, *args, **kwargs)
        instance = to_feddateindex(instance)
        instance.set_self_date_range()
        return instance

    @staticmethod
    def _reverse_human_readable_status(status_str: str) -> "StatusTupleType":
        return READABLE_STATUS_MAP.inv[status_str]

    def set_self_date_range(self) -> None:
        self.start: FedDateStamp = to_datestamp(self.start or self.min())
        self.end: FedDateStamp = to_datestamp(self.end or self.max())

    def _get_mil_cache(self) -> None:
        self.set_self_date_range()
        return MilPayPassRange(start=self.start, end=self.end)

    def _set_mil_cache(self) -> None:
        self._mil_cache: MilPayPassRange = self._mil_cache or self._get_mil_cache()

    def _set_status_gen(self) -> None:
        """
        Set the status generator if not already set.
        """
        self._status_gen: "StatusGeneratorType" = (
            self._status_gen or self._get_status_gen()
        )

    def _get_status_gen(self) -> "StatusGeneratorType":
        """
        Retrieve the status generator from DepartmentState.

        Returns
        -------
        The status generator for the range, mapping departments to their statuses.
        """
        self.set_self_date_range()
        self.states = DepartmentState()
        return DepartmentState.get_state_for_range_generator(
            start=self.start, end=self.end
        )

    def _set_status_cache(self) -> None:
        self._set_status_gen()
        self._status_cache: "StatusCacheType" = (
            self._status_cache or self._generate_status_cache()
        )

    def _generate_status_cache(self) -> "StatusCacheType":
        gen: "StatusGeneratorType" = self._status_gen or self._set_status_gen()
        return dict(gen)

    def to_fedtimestamp(self) -> "Series":
        """
        Convert the dates in the index to POSIX timestamps normalized to midnight.

        Returns
        -------
        Pandas Series of integer POSIX timestamps.
        """

        return (
            (self.normalize() - Timestamp(ts_input="1970-01-01"))
            .total_seconds()
            .astype(dtype=int)
        )

    def _extract_status_data(self, statuses: set[str] | None = None, department_filter: set[EXECUTIVE_DEPARTMENT] | None = None) -> "ExtractedStatusDataGeneratorType":
        self._set_status_gen()
        data_input: "StatusCacheType" | "StatusGeneratorType" = self._status_cache or self._status_gen

        statuses: set[str] | KeysView[str] = statuses or STATUS_MAP.keys()
        department_filter = department_filter or EXECUTIVE_DEPARTMENTS_SET

        data_check_statuses: set[str] = {"DEFAULT_STATUS", "CR_STATUS"}

        for date, department_statuses in (data_input.items() if isinstance(data_input, dict) else data_input):

            if to_datestamp(date).fedtimestamp < CR_DATA_CUTOFF_DATE and any(status in statuses for status in data_check_statuses):
            adjusted_statuses: set["StatusTupleType"] = {STATUS_MAP[key] for key in statuses if key not in data_check_statuses} | {STATUS_MAP["CR_DATA_CUTOFF_DEFAULT_STATUS"]}
            else:
                adjusted_statuses: set["StatusTupleType"] = {STATUS_MAP[key] for key in statuses}

            for department, fed_department_instance in department_statuses.items():
                status_tuple: StatusTupleType = fed_department_instance.to_status_tuple()
                if department in department_filter and status_tuple in adjusted_statuses:
                    yield (to_datestamp(date), fed_department_instance)


    def construct_status_dataframe(self, statuses: set[str] | None = None, department_filter: set[EXECUTIVE_DEPARTMENT] | None = None) -> DataFrame:
        extracted_data: "ExtractedStatusDataGeneratorType" = self._extract_status_data(statuses=statuses, department_filter=department_filter)
        rows: list[Any] = []
        for date, fed_department_instance in extracted_data:
            row: dict[str, Any] = {
                "Date": date,
                "Department": fed_department_instance.name.SHORT,
                "Status": fed_department_instance.status
            }
            rows.append(row)
        return DataFrame(data=rows)

    def status_df_to_multiindex(self, df: DataFrame) -> DataFrame:
        multiindex_data: list[Any] = []
        for _, row in df.iterrows():
            date: FedDateStamp = row['Date']
            department_short: str = row['Department']
            human_readable_status: str = row['Status']

            department_enum: EXECUTIVE_DEPARTMENT = EXECUTIVE_DEPARTMENT.from_short_name(short_name=department_short)
            funding_status, operational_status = self._reverse_human_readable_status(status_str=human_readable_status)

            multiindex_data.append((date, department_enum, funding_status, operational_status))

        multiindex: MultiIndex = MultiIndex.from_tuples(tuples=multiindex_data, names=["Date", "Department", "FundingStatus", "OperationalStatus"])
        return DataFrame(index=multiindex).reset_index()

    def status_df_to_all_bool(self, df: DataFrame) -> DataFrame:

        unique_departments: "ndarray"[str] = df['Department'].unique()
        unique_statuses: "ndarray"[str] = df['Status'].unique()

        columns: list[str] = [f"{dept}-{status}" for dept in unique_departments for status in unique_statuses]
        bool_df: DataFrame = DataFrame(index=df.index, columns=columns).fillna(value=False)

        for index, row in df.iterrows():
            date = row['Date']
            department_short: str = row['Department']
            human_readable_status: str = row['Status']

            col_name: str = f"{department_short}-{human_readable_status}"
            bool_df.at[index, col_name] = True

        return bool_df.reset_index(drop=True)

    @property
    def business_days(self) -> "Series":
        next_business_days  = self + FedBusDay.fed_business_days
        return self == next_business_days

    @property
    def holidays(self) -> Series:
        next_holidays: DatetimeIndex = self + FedHolidays.holidays
        return self == next_holidays

    @property
    def proclaimed_holidays(self) -> "ndarray":
        """
        Check if the dates in the index are proclaimed federal
        holidays.

        Returns
        -------
        Pandas Series of boolean values indicating proclaimed holidays.
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
    def probable_mil_passdays(self) -> "Series":
        self._set_mil_cache()
        return self._mil_cache.get_milpass_series()

    @property
    def mil_paydays(self) -> "Series":
        self._set_mil_cache()
        return self._mil_cache.get_milpay_series()

    @property
    def civ_paydays(self) -> "Series":
        self.set_self_date_range()
        return FedPayDay.get_paydays_as_series(start=self.start, end=self.end)

    @property
    def fys(self) -> "Series":
        return FedFiscalYear.get_fiscal_years(datetimeindex=self)

    @property
    def fiscal_quarters(self) -> "Series":
        return FedFiscalQuarter.get_fiscal_quarters(datetimeindex=self)

    @property
    def departments(self) -> DataFrame:
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
        dept_columns: list[str] = [dept.SHORT for dept in EXECUTIVE_DEPARTMENT]
        df: DataFrame = DataFrame(index=self, columns=dept_columns).fillna(value=True)

        # Adjust for DHS
        dhs_start_date: FedDateStamp | None = to_datestamp(date=DHS_FORMED)
        df.loc[df.index < dhs_start_date, "DHS"] = False

        return df

    @property
    def all_depts_status(self) -> DataFrame:
        self._set_status_cache()
        data_for_df: dict = {}
        for date, dept_statuses in self._status_cache.items():
            for dept, fed_dept in dept_statuses.items():
                if dept not in data_for_df:
                    data_for_df[dept] = {}
                data_for_df[dept][date] = str(object=fed_dept)

        df = DataFrame(data=data_for_df)
        df.index = (
            df.index if df.index.dtype == "datetime64[ns]" else to_datestamp(df.index)
        )
        return df

    @property
    def all_depts_full_approps(self) -> "Series"[bool]:
        return self.construct_status_dataframe(statuses={"DEFAULT_STATUS"})["Departments"] == self.departments


    @property
    def all_depts_cr(self) -> "Series"[bool] | None:


    @property
    def all_depts_cr_or_full_approps(self) -> "Series"[bool] | None:


    @property
    def all_unfunded(self) -> "Series"[bool] | None:


    @property
    def cr(self) -> DataFrame | None:


    @property
    def shutdown(self) -> DataFrame:


    @property
    def approps_gap(self) -> bool:


    @property
    def funding_gap(self) -> bool:

    @property
    def full_op_depts(self) -> "StatusDictType" | None:


    @property
    def full_or_cr_depts(self) -> "StatusDictType" | None:

    @property
    def cr_depts(self) -> "StatusDictType" | None:

    @property


    @property
    def shutdown_depts(self) -> "StatusDictType" | None:


    @property
    def unfunded_depts(self) -> "StatusDictType" | None:



    def contains(self, date: Timestamp) -> Any:
        """
        Checks if a date is within the range.

        Args:
            date (Timestamp | Any): The date to check.

        Returns:
            Any: True if the date is within the range, False otherwise.
        """
        if date is not isinstance(date, Timestamp):
            date = to_datestamp(date=date)
        return self.start <= date <= self.end

    def overlaps(
        self, other: "Timestamp" | FedDateStamp | "FedDateStampConvertibleTypes"
    ) -> Any:
        """
        Checks if the range overlaps with another range.

        Args:
            other (Timestamp | Any): The other range to check. Accepts Timestamps or any date-like object.

        Returns:
            Any: True if the ranges overlap, False otherwise.
        """
        if other is not isinstance(other, DatetimeIndex):
            other = to_datetimeindex()
        return self.start <= other.end and self.end >= other.start


@to_datestamp.register(cls=FedDateStamp)
def _return_datestamp(date_input: FedDateStamp) -> FedDateStamp:
    """
    We handle stray non-conversions by returning them.
    This function and its companion below are lonely refugees from the parent
    function in .time_utils, here to avoid circular import issues until we can
    implement a more permanent fix.
    """
    return date_input


@to_feddateindex.register(cls=FedDateIndex)
def _from_feddateindex(input_dates) -> "FedDateIndex":
    """
    We catch and return stray FedDateIndex objects that happen into our net.
    like _return_datestamp, this function lives here to avoid circular imports.
    """
    return input_dates
