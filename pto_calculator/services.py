from __future__ import annotations

from datetime import date, timedelta

from .calc import calculate_projection
from .holiday_templates import copy_holiday_template, default_holiday_template, generate_holidays_from_template
from .models import (
    EntrySource,
    EntryType,
    HolidayEntry,
    HolidayTemplate,
    PlannedEntry,
    ProjectionResult,
    ProjectionRequest,
    PtoScenario,
)


class PlannerService:
    def __init__(self, scenario: PtoScenario | None = None, holiday_template: HolidayTemplate | None = None) -> None:
        self.holiday_template = copy_holiday_template(holiday_template or default_holiday_template())
        self.scenario = scenario or create_default_scenario(holiday_template=self.holiday_template)
        if not self.scenario.holidays:
            self.scenario.holidays = generate_holidays_from_template(
                self.scenario.year,
                self.holiday_template,
                self.scenario.policy.holiday_hours,
            )
            self.sort_holidays()
        self.projection: ProjectionResult | None = None

    def replace_scenario(self, scenario: PtoScenario) -> None:
        self.scenario = scenario
        if not self.scenario.holidays:
            self.scenario.holidays = generate_holidays_from_template(
                self.scenario.year,
                self.holiday_template,
                self.scenario.policy.holiday_hours,
            )
        self.sort_entries()
        self.sort_holidays()
        self.projection = None

    def set_year(self, year: int) -> None:
        self.scenario.year = year
        self.scenario.last_pay_date = None
        self.scenario.planned_entries.clear()
        self.scenario.holidays = generate_holidays_from_template(
            year,
            self.holiday_template,
            self.scenario.policy.holiday_hours,
        )
        self.sort_holidays()
        self.projection = None

    def reset_holidays(self) -> None:
        self.scenario.holidays = generate_holidays_from_template(
            self.scenario.year,
            self.holiday_template,
            self.scenario.policy.holiday_hours,
        )
        self.sort_holidays()
        self.projection = None

    def set_holiday_template(self, template: HolidayTemplate, apply_to_current: bool = False) -> None:
        self.holiday_template = copy_holiday_template(template)
        if apply_to_current:
            self.reset_holidays()

    def add_planned_entry(
        self,
        when: date,
        hours: float,
        entry_type: EntryType,
        note: str = "",
        source: EntrySource = EntrySource.MANUAL,
    ) -> PlannedEntry:
        planned_entry = PlannedEntry(
            date=when,
            hours=hours,
            entry_type=entry_type,
            note=note,
            source=source,
        )
        self.scenario.planned_entries.append(planned_entry)
        self.sort_entries()
        self.projection = None
        return planned_entry

    def add_planned_range(
        self,
        start: date,
        end: date,
        hours: float,
        entry_type: EntryType,
        note: str = "",
    ) -> int:
        current = start
        added = 0
        existing_keys = {(entry.date, entry.entry_type, entry.note) for entry in self.scenario.planned_entries}
        while current <= end:
            key = (current, entry_type, note)
            if key not in existing_keys:
                self.scenario.planned_entries.append(
                    PlannedEntry(
                        date=current,
                        hours=hours,
                        entry_type=entry_type,
                        note=note,
                        source=EntrySource.RANGE,
                    )
                )
                added += 1
            current += timedelta(days=1)
        self.sort_entries()
        self.projection = None
        return added

    def remove_planned_entries(self, indices: list[int]) -> None:
        for index in sorted(indices, reverse=True):
            del self.scenario.planned_entries[index]
        self.projection = None

    def add_holiday(self, holiday: HolidayEntry) -> None:
        self.scenario.holidays.append(holiday)
        self.sort_holidays()
        self.projection = None

    def remove_holidays(self, indices: list[int]) -> None:
        for index in sorted(indices, reverse=True):
            del self.scenario.holidays[index]
        self.projection = None

    def add_remaining_holiday_entries(self) -> int:
        if self.scenario.last_pay_date is None:
            raise ValueError("Last pay date is required before adding holiday entries.")
        existing_dates = {entry.date for entry in self.scenario.planned_entries}
        added = 0
        for holiday in sorted(self.scenario.holidays, key=lambda item: item.date):
            if holiday.enabled and holiday.date >= self.scenario.last_pay_date and holiday.date not in existing_dates:
                self.scenario.planned_entries.append(
                    PlannedEntry(
                        date=holiday.date,
                        hours=holiday.hours,
                        entry_type=EntryType.FLOAT,
                        note=holiday.name,
                        source=EntrySource.HOLIDAY,
                    )
                )
                added += 1
        self.sort_entries()
        self.projection = None
        return added

    def calculate_projection(self) -> ProjectionResult:
        if self.scenario.last_pay_date is None:
            raise ValueError("Last pay date is required.")
        request = ProjectionRequest(
            year=self.scenario.year,
            regular_balance=self.scenario.regular_balance,
            accrual_per_period=self.scenario.accrual_per_period,
            float_balance=self.scenario.float_balance,
            last_pay_date=self.scenario.last_pay_date,
            planned_entries=list(self.scenario.planned_entries),
            holidays=list(self.scenario.holidays),
            policy=self.scenario.policy,
        )
        self.projection = calculate_projection(request)
        return self.projection

    def sort_entries(self) -> None:
        self.scenario.planned_entries.sort(key=lambda entry: (entry.date, entry.entry_type.value, entry.note, entry.source.value))

    def sort_holidays(self) -> None:
        self.scenario.holidays.sort(key=lambda holiday: (holiday.date, holiday.name))


def create_default_scenario(year: int | None = None, holiday_template: HolidayTemplate | None = None) -> PtoScenario:
    selected_year = year or date.today().year
    scenario = PtoScenario(year=selected_year)
    scenario.holidays = generate_holidays_from_template(
        selected_year,
        holiday_template or default_holiday_template(),
        scenario.policy.holiday_hours,
    )
    return scenario
