from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog

from pto_calculator.holiday_templates import FEDERAL_HOLIDAY_LABELS, default_holiday_template
from pto_calculator.app_bootstrap import app_icon_path
from pto_calculator.models import (
    CustomHolidayRule,
    FederalHolidayId,
    HolidayEntry,
    HolidayRuleType,
    PtoScenario,
)
from pto_calculator.ui.holiday_selector import HolidaySelectorDialog
from pto_calculator.ui.main_window import MainWindow, default_date_for_year


def _set_last_pay_date(window: MainWindow, value: str) -> None:
    if not value:
        window.last_pay_date_edit.clear_date_value()
        return
    window.last_pay_date_edit.set_date_value(date.fromisoformat(value))


def test_validation_requires_last_pay_date(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    messages = []
    window._warn = lambda title, message: messages.append((title, message))

    window.regular_balance_spinbox.setValue(40.0)
    window.accrual_spinbox.setValue(4.0)
    window.float_balance_spinbox.setValue(8.0)
    _set_last_pay_date(window, "")

    qtbot.mouseClick(window.calculate_button, Qt.LeftButton)

    assert messages
    assert "Last pay date is required." in messages[-1][1]


def test_add_remove_and_range_add_planned_entries(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    window.planned_date_edit.setDate(window.planned_date_edit.date().addDays(10))
    window.planned_hours_spinbox.setValue(8.0)
    qtbot.mouseClick(window.add_planned_button, Qt.LeftButton)

    window.range_start_edit.setDate(window.range_start_edit.date().addDays(20))
    window.range_end_edit.setDate(window.range_start_edit.date().addDays(2))
    window.range_hours_spinbox.setValue(4.0)
    qtbot.mouseClick(window.add_range_button, Qt.LeftButton)

    assert window.planned_table.rowCount() == 4

    window.planned_table.selectRow(0)
    qtbot.mouseClick(window.remove_planned_button, Qt.LeftButton)

    assert window.planned_table.rowCount() == 3


def test_year_switch_resets_holidays_and_projection_state(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    window.planned_date_edit.setDate(window.planned_date_edit.date().addDays(5))
    window.planned_hours_spinbox.setValue(8.0)
    qtbot.mouseClick(window.add_planned_button, Qt.LeftButton)
    assert window.planned_table.rowCount() == 1

    current_year = window.year_spinbox.value()
    window.year_spinbox.setValue(current_year + 1)

    assert window.planned_table.rowCount() == 0
    assert window.holiday_table.rowCount() > 0
    assert window.projection_model.rowCount() == 0


def test_date_pickers_default_to_system_matching_date(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    expected = default_date_for_year(window.year_spinbox.value())

    assert window.last_pay_date_edit.date_value() == expected
    assert window.planned_date_edit.date().toPython() == expected
    assert window.range_start_edit.date().toPython() == expected
    assert window.range_end_edit.date().toPython() == expected
    assert window.holiday_date_edit.date().toPython() == expected


def test_empty_last_pay_date_popup_opens_on_system_matching_date(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    expected = default_date_for_year(window.year_spinbox.value())
    window.last_pay_date_edit.clear_date_value()
    popup_page = (
        window.last_pay_date_edit.calendarWidget().yearShown(),
        window.last_pay_date_edit.calendarWidget().monthShown(),
    )

    assert window.last_pay_date_edit.date_value() is None
    assert popup_page == (expected.year, expected.month)


def test_range_end_date_tracks_range_start_date(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    start_date = window.range_start_edit.date().addDays(12)
    window.range_start_edit.setDate(start_date)

    assert window.range_end_edit.date() == start_date


def test_summary_cards_match_projection_output(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    window.regular_balance_spinbox.setValue(40.0)
    window.accrual_spinbox.setValue(4.0)
    window.float_balance_spinbox.setValue(8.0)
    _set_last_pay_date(window, f"{window.year_spinbox.value()}-03-13")
    qtbot.mouseClick(window.calculate_button, Qt.LeftButton)

    projection = window.service.projection
    assert projection is not None
    assert window.workspace_tabs.currentWidget() == window.projection_tab
    assert window.regular_summary_card.value_label.text() == f"{projection.final_regular_balance:.4f} h"
    assert window.float_summary_card.value_label.text() == f"{projection.final_float_balance:.4f} h"
    assert window.planned_summary_card.value_label.text() == f"{projection.total_planned_hours:.4f} h"


def test_app_icon_asset_exists():
    assert app_icon_path().is_file()


def test_main_window_sets_a_non_null_icon(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    assert not window.windowIcon().isNull()


def test_tools_menu_contains_holiday_selector(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    action_texts = [action.text() for action in window.tools_menu.actions()]

    assert "Holiday Selector" in action_texts


def test_holiday_selector_shows_all_official_federal_holidays(qtbot):
    dialog = HolidaySelectorDialog(default_holiday_template())
    qtbot.addWidget(dialog)

    listed_names = {dialog.federal_table.item(row, 1).text() for row in range(dialog.federal_table.rowCount())}

    assert dialog.federal_table.rowCount() == 11
    assert listed_names == set(FEDERAL_HOLIDAY_LABELS.values())


def test_apply_holiday_template_updates_current_holiday_table(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    template = default_holiday_template()
    template.federal_holidays = {holiday_id: False for holiday_id in template.federal_holidays}
    template.custom_rules = [
        CustomHolidayRule(
            name="Company Picnic",
            hours=6.0,
            rule_type=HolidayRuleType.FIXED_DATE,
            month=8,
            day=14,
        )
    ]

    window._apply_holiday_template(template, save_as_default=False)

    assert window.holiday_table.rowCount() == 1
    assert window.holiday_table.item(0, 1).text() == f"{window.year_spinbox.value()}-08-14"
    assert window.holiday_table.item(0, 2).text() == "Company Picnic"


def test_apply_and_save_holiday_template_persists_across_fresh_window_instance(qtbot):
    first_window = MainWindow()
    qtbot.addWidget(first_window)

    template = default_holiday_template()
    template.federal_holidays[FederalHolidayId.CHRISTMAS_DAY] = False
    template.custom_rules = [
        CustomHolidayRule(
            name="Fiscal Shutdown",
            hours=4.0,
            rule_type=HolidayRuleType.FIXED_DATE,
            month=12,
            day=31,
        )
    ]
    first_window._apply_holiday_template(template, save_as_default=True)

    second_window = MainWindow()
    qtbot.addWidget(second_window)

    holiday_names = {holiday.name for holiday in second_window.service.scenario.holidays}

    assert FEDERAL_HOLIDAY_LABELS[FederalHolidayId.CHRISTMAS_DAY] not in holiday_names
    assert "Fiscal Shutdown" in holiday_names


def test_custom_recurring_entries_can_be_added_edited_and_removed(qtbot, monkeypatch):
    dialog = HolidaySelectorDialog(default_holiday_template())
    qtbot.addWidget(dialog)

    returned_rules = iter(
        [
            CustomHolidayRule(
                name="Summer Friday",
                hours=4.0,
                rule_type=HolidayRuleType.FIXED_DATE,
                month=8,
                day=7,
            ),
            CustomHolidayRule(
                name="Summer Friday Updated",
                hours=6.0,
                rule_type=HolidayRuleType.FIXED_DATE,
                month=8,
                day=14,
            ),
        ]
    )

    class FakeCustomHolidayRuleDialog:
        def __init__(self, rule=None, parent=None):
            self._rule = next(returned_rules)

        def exec(self):
            return QDialog.Accepted

        def holiday_rule(self):
            return self._rule

    monkeypatch.setattr("pto_calculator.ui.holiday_selector.CustomHolidayRuleDialog", FakeCustomHolidayRuleDialog)

    dialog._add_custom_rule()
    assert dialog.custom_rules_table.rowCount() == 1
    assert dialog.custom_rules_table.item(0, 1).text() == "Summer Friday"

    dialog.custom_rules_table.selectRow(0)
    dialog._edit_custom_rule()
    assert dialog.custom_rules_table.item(0, 1).text() == "Summer Friday Updated"
    assert dialog.custom_rules_table.item(0, 3).text() == "6.0000"

    dialog.custom_rules_table.selectRow(0)
    dialog._remove_custom_rule()
    assert dialog.custom_rules_table.rowCount() == 0


def test_loaded_scenario_keeps_concrete_holidays_until_template_is_applied(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    template = default_holiday_template()
    template.federal_holidays = {holiday_id: False for holiday_id in template.federal_holidays}
    template.custom_rules = [
        CustomHolidayRule(
            name="Template Holiday",
            rule_type=HolidayRuleType.FIXED_DATE,
            month=10,
            day=10,
        )
    ]
    window.service.set_holiday_template(template)

    loaded_scenario = PtoScenario(
        name="Loaded",
        year=2026,
        holidays=[HolidayEntry(date(2026, 4, 22), "Loaded Holiday", 8.0, True)],
    )
    window.service.replace_scenario(loaded_scenario)
    window._populate_from_scenario()

    assert window.holiday_table.rowCount() == 1
    assert window.holiday_table.item(0, 2).text() == "Loaded Holiday"

    window._apply_holiday_template(template, save_as_default=False)

    assert window.holiday_table.rowCount() == 1
    assert window.holiday_table.item(0, 2).text() == "Template Holiday"
