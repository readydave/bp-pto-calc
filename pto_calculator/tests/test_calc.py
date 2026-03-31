from datetime import date

from pto_calculator.calc import calculate_projection, generate_default_holidays
from pto_calculator.models import EntryType, PlannedEntry, ProjectionRequest, ProjectionRowType, ScenarioPolicy
from pto_calculator.services import PlannerService, create_default_scenario


def make_request(
    *,
    year: int,
    regular_balance: float,
    accrual_per_period: float,
    float_balance: float,
    last_pay_date: date,
    planned_entries: list[PlannedEntry] | None = None,
    policy: ScenarioPolicy | None = None,
):
    return ProjectionRequest(
        year=year,
        regular_balance=regular_balance,
        accrual_per_period=accrual_per_period,
        float_balance=float_balance,
        last_pay_date=last_pay_date,
        planned_entries=planned_entries or [],
        holidays=generate_default_holidays(year),
        policy=policy or ScenarioPolicy(),
    )


def test_projection_supports_selected_year_and_quarter_awards():
    result = calculate_projection(
        make_request(
            year=2026,
            regular_balance=40.0,
            accrual_per_period=4.0,
            float_balance=0.0,
            last_pay_date=date(2026, 3, 13),
        )
    )

    award_dates = [row.date for row in result.rows if row.row_type == ProjectionRowType.FLOAT_AWARD]
    assert award_dates == [date(2026, 4, 1), date(2026, 7, 1), date(2026, 10, 1)]
    assert result.pay_period_count > 0
    assert result.final_float_balance == 36.0


def test_projection_supports_leap_years():
    result = calculate_projection(
        make_request(
            year=2028,
            regular_balance=16.0,
            accrual_per_period=5.0,
            float_balance=4.0,
            last_pay_date=date(2028, 2, 25),
        )
    )

    assert result.rows[-1].date == date(2028, 12, 31)
    assert result.final_regular_balance >= 16.0


def test_post_final_pay_date_entry_affects_year_end_balance():
    result = calculate_projection(
        make_request(
            year=2026,
            regular_balance=40.0,
            accrual_per_period=4.0,
            float_balance=8.0,
            last_pay_date=date(2026, 11, 27),
            planned_entries=[PlannedEntry(date(2026, 12, 30), 8.0, EntryType.REGULAR)],
        )
    )

    planned_row = next(row for row in result.rows if row.row_type == ProjectionRowType.PLANNED_PTO)
    assert planned_row.date == date(2026, 12, 30)
    assert result.rows[-1].date == date(2026, 12, 31)
    assert result.final_regular_balance == 40.0


def test_regular_over_cap_is_forfeited_on_next_payday():
    result = calculate_projection(
        make_request(
            year=2026,
            regular_balance=198.0,
            accrual_per_period=4.0,
            float_balance=8.0,
            last_pay_date=date(2026, 12, 4),
        )
    )

    payday_row = next(row for row in result.rows if row.row_type == ProjectionRowType.PAYDAY)
    assert payday_row.regular_end == 200.0
    assert "Forfeited 2.0000h over 200.0000h max" in payday_row.note
    assert result.final_regular_balance == 200.0
    assert result.regular_forfeiture == 82.0
    assert result.float_forfeiture == 8.0


def test_year_end_cap_only_applies_on_december_31():
    result = calculate_projection(
        make_request(
            year=2026,
            regular_balance=118.0,
            accrual_per_period=4.0,
            float_balance=8.0,
            last_pay_date=date(2026, 12, 4),
        )
    )

    year_end_row = result.rows[-1]
    assert year_end_row.row_type == ProjectionRowType.YEAR_END
    assert year_end_row.note == "Year-end forfeiture 2.0000h over 120.0000h cap"
    assert result.final_regular_balance == 122.0
    assert result.regular_forfeiture == 2.0


def test_year_end_forfeiture_uses_year_end_cap_even_without_next_payday():
    result = calculate_projection(
        make_request(
            year=2026,
            regular_balance=205.0,
            accrual_per_period=0.0,
            float_balance=0.0,
            last_pay_date=date(2026, 12, 31),
        )
    )

    year_end_row = result.rows[-1]
    assert year_end_row.row_type == ProjectionRowType.YEAR_END
    assert year_end_row.note == "Year-end forfeiture 85.0000h over 120.0000h cap"
    assert result.regular_forfeiture == 85.0


def test_observed_holiday_generation_and_remaining_holiday_entries():
    holidays = generate_default_holidays(2026)
    holiday_dates = {holiday.date for holiday in holidays}
    assert date(2026, 7, 3) in holiday_dates

    service = PlannerService(create_default_scenario(2026))
    service.scenario.last_pay_date = date(2026, 7, 1)
    added = service.add_remaining_holiday_entries()
    assert added > 0
    assert any(entry.source.value == "holiday" for entry in service.scenario.planned_entries)
