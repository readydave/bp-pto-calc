from datetime import date

from PySide6.QtCore import QSettings

from pto_calculator.holiday_templates import (
    FEDERAL_HOLIDAY_LABELS,
    default_holiday_template,
    generate_holidays_from_template,
    load_holiday_template,
    save_holiday_template,
)
from pto_calculator.models import (
    CustomHolidayRule,
    FederalHolidayId,
    HolidayOccurrence,
    HolidayRuleType,
)
from pto_calculator.services import PlannerService


def test_default_holiday_template_generates_expected_federal_dates():
    template = default_holiday_template()

    holidays_2025 = {holiday.name: holiday.date for holiday in generate_holidays_from_template(2025, template, 8.0)}
    holidays_2026 = {holiday.name: holiday.date for holiday in generate_holidays_from_template(2026, template, 8.0)}
    holidays_2028 = {holiday.name: holiday.date for holiday in generate_holidays_from_template(2028, template, 8.0)}

    assert holidays_2025["New Year's Day"] == date(2025, 1, 1)
    assert holidays_2025["Thanksgiving Day"] == date(2025, 11, 27)
    assert holidays_2026["Birthday of Martin Luther King, Jr."] == date(2026, 1, 19)
    assert holidays_2026["Independence Day"] == date(2026, 7, 3)
    assert "New Year's Day" not in holidays_2028
    assert holidays_2028["Washington's Birthday"] == date(2028, 2, 21)


def test_disabled_built_in_holidays_are_omitted():
    template = default_holiday_template()
    template.federal_holidays[FederalHolidayId.CHRISTMAS_DAY] = False

    holiday_names = {holiday.name for holiday in generate_holidays_from_template(2026, template, 8.0)}

    assert FEDERAL_HOLIDAY_LABELS[FederalHolidayId.CHRISTMAS_DAY] not in holiday_names


def test_fixed_date_custom_rules_allow_leap_day_and_skip_non_leap_years():
    template = default_holiday_template()
    template.federal_holidays = {holiday_id: False for holiday_id in template.federal_holidays}
    template.custom_rules = [
        CustomHolidayRule(
            name="Leap Day",
            hours=6.0,
            rule_type=HolidayRuleType.FIXED_DATE,
            month=2,
            day=29,
        )
    ]

    holidays_2028 = generate_holidays_from_template(2028, template, 8.0)
    holidays_2026 = generate_holidays_from_template(2026, template, 8.0)

    assert [(holiday.name, holiday.date, holiday.hours) for holiday in holidays_2028] == [
        ("Leap Day", date(2028, 2, 29), 6.0)
    ]
    assert holidays_2026 == []


def test_nth_weekday_custom_rules_support_last_occurrence():
    template = default_holiday_template()
    template.federal_holidays = {holiday_id: False for holiday_id in template.federal_holidays}
    template.custom_rules = [
        CustomHolidayRule(
            name="Summer Friday",
            rule_type=HolidayRuleType.NTH_WEEKDAY,
            month=8,
            weekday=4,
            occurrence=HolidayOccurrence.LAST,
        )
    ]

    holidays = generate_holidays_from_template(2026, template, 8.0)

    assert [(holiday.name, holiday.date) for holiday in holidays] == [("Summer Friday", date(2026, 8, 28))]


def test_holiday_template_round_trips_through_qsettings():
    settings = QSettings()
    template = default_holiday_template()
    template.federal_holidays[FederalHolidayId.COLUMBUS_DAY] = False
    template.custom_rules = [
        CustomHolidayRule(
            name="Company Shutdown",
            hours=4.0,
            rule_type=HolidayRuleType.FIXED_DATE,
            month=12,
            day=31,
        )
    ]

    save_holiday_template(settings, template)
    loaded = load_holiday_template(settings)

    assert loaded.federal_holidays[FederalHolidayId.COLUMBUS_DAY] is False
    assert loaded.custom_rules[0].name == "Company Shutdown"
    assert loaded.custom_rules[0].hours == 4.0


def test_service_year_reset_regenerates_holidays_from_template():
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

    service = PlannerService(holiday_template=template)
    service.set_year(2026)

    holiday_names = {holiday.name for holiday in service.scenario.holidays}
    custom_holiday = next(holiday for holiday in service.scenario.holidays if holiday.name == "Fiscal Shutdown")

    assert FEDERAL_HOLIDAY_LABELS[FederalHolidayId.CHRISTMAS_DAY] not in holiday_names
    assert custom_holiday.date == date(2026, 12, 31)
    assert custom_holiday.hours == 4.0
