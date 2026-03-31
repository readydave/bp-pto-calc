from datetime import date

import openpyxl

from pto_calculator.calc import calculate_projection, generate_default_holidays
from pto_calculator.io_utils import export_projection_to_csv, export_projection_to_excel, load_scenario, save_scenario
from pto_calculator.models import EntrySource, EntryType, PlannedEntry, ProjectionRequest, PtoScenario, ScenarioPolicy


def build_scenario() -> PtoScenario:
    policy = ScenarioPolicy(regular_pto_cap=120.0, float_award_per_quarter=12.0, holiday_hours=8.0)
    return PtoScenario(
        name="Regression Scenario",
        year=2026,
        regular_balance=40.0,
        accrual_per_period=4.0,
        float_balance=8.0,
        last_pay_date=date(2026, 3, 13),
        policy=policy,
        planned_entries=[
            PlannedEntry(
                date=date(2026, 4, 14),
                hours=8.0,
                entry_type=EntryType.REGULAR,
                note="Spring trip",
                source=EntrySource.MANUAL,
            )
        ],
        holidays=generate_default_holidays(2026, policy.holiday_hours),
    )


def test_save_and_load_versioned_scenario(tmp_path):
    scenario = build_scenario()
    path = tmp_path / "scenario.json"

    save_scenario(path, scenario)
    loaded = load_scenario(path)

    assert loaded.name == scenario.name
    assert loaded.year == 2026
    assert loaded.last_pay_date == date(2026, 3, 13)
    assert loaded.planned_entries[0].note == "Spring trip"
    assert len(loaded.holidays) == len(scenario.holidays)


def test_loads_legacy_scenario_format(tmp_path):
    legacy_payload = {
        "regular_balance": "32",
        "accrual": "4",
        "float_balance": "12",
        "last_pay_date": "2026-03-13",
        "planned_pto": [["2026-04-04", 8, "Regular"]],
    }
    path = tmp_path / "legacy.json"
    path.write_text(__import__("json").dumps(legacy_payload), encoding="utf-8")

    scenario = load_scenario(path)

    assert scenario.year == 2026
    assert scenario.planned_entries[0].entry_type == EntryType.REGULAR
    assert scenario.holidays


def test_csv_and_excel_exports_include_projection_rows(tmp_path):
    scenario = build_scenario()
    result = calculate_projection(
        ProjectionRequest(
            year=scenario.year,
            regular_balance=scenario.regular_balance,
            accrual_per_period=scenario.accrual_per_period,
            float_balance=scenario.float_balance,
            last_pay_date=scenario.last_pay_date,
            planned_entries=scenario.planned_entries,
            holidays=scenario.holidays,
            policy=scenario.policy,
        )
    )

    csv_path = tmp_path / "projection.csv"
    xlsx_path = tmp_path / "projection.xlsx"
    export_projection_to_csv(csv_path, result)
    export_projection_to_excel(xlsx_path, result)

    csv_text = csv_path.read_text(encoding="utf-8")
    assert "Spring trip" in csv_text
    assert "Year End" in csv_text
    assert ".0000" in csv_text

    workbook = openpyxl.load_workbook(xlsx_path)
    sheet = workbook.active
    assert sheet.max_row > 2
    assert sheet["A2"].value is not None
    assert sheet["C2"].value is not None
    assert sheet["D2"].number_format == "0.0000"
