from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum


SCHEMA_VERSION = 2


class EntryType(StrEnum):
    REGULAR = "Regular"
    FLOAT = "Float"


class EntrySource(StrEnum):
    MANUAL = "manual"
    RANGE = "range"
    HOLIDAY = "holiday"


class FederalHolidayId(StrEnum):
    NEW_YEARS_DAY = "new_years_day"
    MARTIN_LUTHER_KING_JR_DAY = "martin_luther_king_jr_day"
    WASHINGTONS_BIRTHDAY = "washingtons_birthday"
    MEMORIAL_DAY = "memorial_day"
    JUNETEENTH = "juneteenth"
    INDEPENDENCE_DAY = "independence_day"
    LABOR_DAY = "labor_day"
    COLUMBUS_DAY = "columbus_day"
    VETERANS_DAY = "veterans_day"
    THANKSGIVING_DAY = "thanksgiving_day"
    CHRISTMAS_DAY = "christmas_day"


class HolidayRuleType(StrEnum):
    FIXED_DATE = "fixed_date"
    NTH_WEEKDAY = "nth_weekday"


class HolidayOccurrence(StrEnum):
    FIRST = "1"
    SECOND = "2"
    THIRD = "3"
    FOURTH = "4"
    LAST = "last"


class ProjectionRowType(StrEnum):
    PAYDAY = "payday"
    FLOAT_AWARD = "float_award"
    PLANNED_PTO = "planned_pto"
    YEAR_END = "year_end"


@dataclass(slots=True)
class ScenarioPolicy:
    regular_pto_cap: float = 120.0
    float_award_per_quarter: float = 12.0
    holiday_hours: float = 8.0


@dataclass(slots=True)
class HolidayEntry:
    date: date
    name: str
    hours: float = 8.0
    enabled: bool = True


@dataclass(slots=True)
class CustomHolidayRule:
    name: str
    hours: float = 8.0
    enabled: bool = True
    rule_type: HolidayRuleType = HolidayRuleType.FIXED_DATE
    month: int = 1
    day: int = 1
    weekday: int = 0
    occurrence: HolidayOccurrence = HolidayOccurrence.FIRST


@dataclass(slots=True)
class HolidayTemplate:
    federal_holidays: dict[FederalHolidayId, bool] = field(default_factory=dict)
    custom_rules: list[CustomHolidayRule] = field(default_factory=list)


@dataclass(slots=True)
class PlannedEntry:
    date: date
    hours: float
    entry_type: EntryType
    note: str = ""
    source: EntrySource = EntrySource.MANUAL


@dataclass(slots=True)
class ProjectionRow:
    row_type: ProjectionRowType
    date: date
    label: str
    regular_start: float
    float_start: float
    regular_change: float
    float_change: float
    regular_used: float
    float_used: float
    regular_end: float
    float_end: float
    note: str = ""


@dataclass(slots=True)
class ProjectionRequest:
    year: int
    regular_balance: float
    accrual_per_period: float
    float_balance: float
    last_pay_date: date
    planned_entries: list[PlannedEntry] = field(default_factory=list)
    holidays: list[HolidayEntry] = field(default_factory=list)
    policy: ScenarioPolicy = field(default_factory=ScenarioPolicy)


@dataclass(slots=True)
class ProjectionResult:
    year: int
    rows: list[ProjectionRow]
    pay_period_count: int
    total_planned_regular: float
    total_planned_float: float
    final_regular_balance: float
    final_float_balance: float
    regular_forfeiture: float
    float_forfeiture: float

    @property
    def total_planned_hours(self) -> float:
        return self.total_planned_regular + self.total_planned_float


@dataclass(slots=True)
class PtoScenario:
    name: str = "Untitled Scenario"
    year: int = 2026
    regular_balance: float = 0.0
    accrual_per_period: float = 0.0
    float_balance: float = 0.0
    last_pay_date: date | None = None
    policy: ScenarioPolicy = field(default_factory=ScenarioPolicy)
    planned_entries: list[PlannedEntry] = field(default_factory=list)
    holidays: list[HolidayEntry] = field(default_factory=list)
