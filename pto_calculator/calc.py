from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from .holiday_templates import default_holiday_template, generate_holidays_from_template
from .models import (
    EntryType,
    HolidayEntry,
    PlannedEntry,
    ProjectionRequest,
    ProjectionResult,
    ProjectionRow,
    ProjectionRowType,
)

PAY_PERIOD_DELTA = timedelta(days=14)
MAX_REGULAR_PTO_HOURS = 200.0


def calculate_projection(request: ProjectionRequest) -> ProjectionResult:
    _validate_request(request)

    year_end = date(request.year, 12, 31)
    events = _build_events(request, year_end)
    effective_year_end_cap = request.policy.regular_pto_cap

    running_regular = request.regular_balance
    running_float = request.float_balance
    pay_period_count = 0
    total_planned_regular = 0.0
    total_planned_float = 0.0
    total_regular_forfeiture = 0.0
    rows: list[ProjectionRow] = []

    for event in events:
        start_regular = running_regular
        start_float = running_float
        regular_change = 0.0
        float_change = 0.0
        regular_used = 0.0
        float_used = 0.0
        label = event.label
        note = ""

        if event.kind == ProjectionRowType.PAYDAY:
            regular_change = request.accrual_per_period
            running_regular += regular_change
            pay_period_count += 1
            if running_regular > MAX_REGULAR_PTO_HOURS:
                forfeited = running_regular - MAX_REGULAR_PTO_HOURS
                running_regular = MAX_REGULAR_PTO_HOURS
                regular_change -= forfeited
                total_regular_forfeiture += forfeited
                note = f"Forfeited {forfeited:.4f}h over {MAX_REGULAR_PTO_HOURS:.4f}h max"
        elif event.kind == ProjectionRowType.FLOAT_AWARD:
            float_change = request.policy.float_award_per_quarter
            running_float += float_change
        elif event.kind == ProjectionRowType.PLANNED_PTO:
            planned_entry = event.planned_entry
            assert planned_entry is not None
            notes: list[str] = []
            if planned_entry.note:
                notes.append(planned_entry.note)
            if planned_entry.entry_type == EntryType.REGULAR:
                regular_used = min(planned_entry.hours, running_regular)
                running_regular -= regular_used
                total_planned_regular += regular_used
                if regular_used < planned_entry.hours:
                    notes.append(f"Requested {planned_entry.hours:.4f}h")
            else:
                float_used = min(planned_entry.hours, running_float)
                running_float -= float_used
                total_planned_float += float_used
                if float_used < planned_entry.hours:
                    notes.append(f"Requested {planned_entry.hours:.4f}h")
            note = "; ".join(notes)
        elif event.kind == ProjectionRowType.YEAR_END:
            year_end_forfeiture = max(0.0, running_regular - effective_year_end_cap)
            if year_end_forfeiture > 0:
                note = f"Year-end forfeiture {year_end_forfeiture:.4f}h over {effective_year_end_cap:.4f}h cap"

        rows.append(
            ProjectionRow(
                row_type=event.kind,
                date=event.when,
                label=label,
                regular_start=start_regular,
                float_start=start_float,
                regular_change=regular_change,
                float_change=float_change,
                regular_used=regular_used,
                float_used=float_used,
                regular_end=running_regular,
                float_end=running_float,
                note=note,
            )
        )

    regular_forfeiture = total_regular_forfeiture + max(0.0, running_regular - effective_year_end_cap)
    float_forfeiture = max(0.0, running_float)

    return ProjectionResult(
        year=request.year,
        rows=rows,
        pay_period_count=pay_period_count,
        total_planned_regular=total_planned_regular,
        total_planned_float=total_planned_float,
        final_regular_balance=running_regular,
        final_float_balance=running_float,
        regular_forfeiture=regular_forfeiture,
        float_forfeiture=float_forfeiture,
    )


def generate_default_holidays(year: int, default_hours: float = 8.0) -> list[HolidayEntry]:
    return generate_holidays_from_template(year, default_holiday_template(), default_hours)


def _validate_request(request: ProjectionRequest) -> None:
    if request.year < 2000:
        raise ValueError("Projection year must be 2000 or later.")
    if request.regular_balance < 0 or request.float_balance < 0 or request.accrual_per_period < 0:
        raise ValueError("Balances and accrual values must be non-negative.")
    if request.last_pay_date.year != request.year:
        raise ValueError("Last pay date must be inside the selected PTO year.")
    for planned_entry in request.planned_entries:
        if planned_entry.date.year != request.year:
            raise ValueError("Planned PTO dates must match the selected PTO year.")
        if planned_entry.hours <= 0:
            raise ValueError("Planned PTO hours must be greater than zero.")
    for holiday in request.holidays:
        if holiday.date.year != request.year:
            raise ValueError("Holiday dates must match the selected PTO year.")
        if holiday.hours <= 0:
            raise ValueError("Holiday hours must be greater than zero.")


@dataclass(slots=True)
class _Event:
    kind: ProjectionRowType
    when: date
    priority: int
    order: int
    label: str
    planned_entry: PlannedEntry | None = None


def _build_events(request: ProjectionRequest, year_end: date) -> list[_Event]:
    events: list[_Event] = []
    order = 0
    next_pay_date = request.last_pay_date + PAY_PERIOD_DELTA
    while next_pay_date <= year_end:
        events.append(
            _Event(
                kind=ProjectionRowType.PAYDAY,
                when=next_pay_date,
                priority=10,
                order=order,
                label="Pay period accrual",
            )
        )
        order += 1
        next_pay_date += PAY_PERIOD_DELTA

    for month in (1, 4, 7, 10):
        quarter_date = date(request.year, month, 1)
        if request.last_pay_date < quarter_date <= year_end:
            events.append(
                _Event(
                    kind=ProjectionRowType.FLOAT_AWARD,
                    when=quarter_date,
                    priority=20,
                    order=order,
                    label="Quarterly float award",
                )
            )
            order += 1

    for planned_entry in request.planned_entries:
        if request.last_pay_date < planned_entry.date <= year_end:
            events.append(
                _Event(
                    kind=ProjectionRowType.PLANNED_PTO,
                    when=planned_entry.date,
                    priority=30,
                    order=order,
                    label=f"{planned_entry.entry_type.value} PTO",
                    planned_entry=planned_entry,
                )
            )
            order += 1

    events.append(
        _Event(
            kind=ProjectionRowType.YEAR_END,
            when=year_end,
            priority=99,
            order=order,
            label="Year-end snapshot",
        )
    )
    return sorted(events, key=lambda event: (event.when, event.priority, event.order))
