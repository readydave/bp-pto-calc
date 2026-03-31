from __future__ import annotations

import json
from copy import deepcopy
from datetime import date, timedelta

from PySide6.QtCore import QSettings

from .models import (
    CustomHolidayRule,
    FederalHolidayId,
    HolidayEntry,
    HolidayOccurrence,
    HolidayRuleType,
    HolidayTemplate,
)

TEMPLATE_VERSION = 1
TEMPLATE_VERSION_KEY = "holiday_selector/template_version"
TEMPLATE_JSON_KEY = "holiday_selector/template_json"

FEDERAL_HOLIDAY_ORDER = [
    FederalHolidayId.NEW_YEARS_DAY,
    FederalHolidayId.MARTIN_LUTHER_KING_JR_DAY,
    FederalHolidayId.WASHINGTONS_BIRTHDAY,
    FederalHolidayId.MEMORIAL_DAY,
    FederalHolidayId.JUNETEENTH,
    FederalHolidayId.INDEPENDENCE_DAY,
    FederalHolidayId.LABOR_DAY,
    FederalHolidayId.COLUMBUS_DAY,
    FederalHolidayId.VETERANS_DAY,
    FederalHolidayId.THANKSGIVING_DAY,
    FederalHolidayId.CHRISTMAS_DAY,
]

FEDERAL_HOLIDAY_LABELS: dict[FederalHolidayId, str] = {
    FederalHolidayId.NEW_YEARS_DAY: "New Year's Day",
    FederalHolidayId.MARTIN_LUTHER_KING_JR_DAY: "Birthday of Martin Luther King, Jr.",
    FederalHolidayId.WASHINGTONS_BIRTHDAY: "Washington's Birthday",
    FederalHolidayId.MEMORIAL_DAY: "Memorial Day",
    FederalHolidayId.JUNETEENTH: "Juneteenth National Independence Day",
    FederalHolidayId.INDEPENDENCE_DAY: "Independence Day",
    FederalHolidayId.LABOR_DAY: "Labor Day",
    FederalHolidayId.COLUMBUS_DAY: "Columbus Day",
    FederalHolidayId.VETERANS_DAY: "Veterans Day",
    FederalHolidayId.THANKSGIVING_DAY: "Thanksgiving Day",
    FederalHolidayId.CHRISTMAS_DAY: "Christmas Day",
}

WEEKDAY_LABELS = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]

OCCURRENCE_LABELS: dict[HolidayOccurrence, str] = {
    HolidayOccurrence.FIRST: "1st",
    HolidayOccurrence.SECOND: "2nd",
    HolidayOccurrence.THIRD: "3rd",
    HolidayOccurrence.FOURTH: "4th",
    HolidayOccurrence.LAST: "Last",
}


def default_holiday_template() -> HolidayTemplate:
    return HolidayTemplate(
        federal_holidays={holiday_id: True for holiday_id in FEDERAL_HOLIDAY_ORDER},
        custom_rules=[],
    )


def copy_holiday_template(template: HolidayTemplate) -> HolidayTemplate:
    return HolidayTemplate(
        federal_holidays=dict(template.federal_holidays),
        custom_rules=deepcopy(template.custom_rules),
    )


def generate_holidays_from_template(year: int, template: HolidayTemplate, default_hours: float) -> list[HolidayEntry]:
    holidays: list[HolidayEntry] = []

    for holiday_id in FEDERAL_HOLIDAY_ORDER:
        if not template.federal_holidays.get(holiday_id, True):
            continue
        holiday_date = _generate_federal_holiday_date(year, holiday_id)
        if holiday_date is not None:
            holidays.append(HolidayEntry(holiday_date, FEDERAL_HOLIDAY_LABELS[holiday_id], default_hours, True))

    for rule in template.custom_rules:
        if not rule.enabled:
            continue
        holiday_date = _generate_custom_rule_date(year, rule)
        if holiday_date is None:
            continue
        holidays.append(HolidayEntry(holiday_date, rule.name, rule.hours, True))

    return sorted(holidays, key=lambda holiday: (holiday.date, holiday.name))


def load_holiday_template(settings: QSettings) -> HolidayTemplate:
    version = settings.value(TEMPLATE_VERSION_KEY)
    raw_template = settings.value(TEMPLATE_JSON_KEY)
    if not raw_template:
        return default_holiday_template()

    try:
        payload = json.loads(str(raw_template))
        payload_version = int(payload.get("template_version", version or TEMPLATE_VERSION))
        if payload_version != TEMPLATE_VERSION:
            return default_holiday_template()
        return holiday_template_from_payload(payload)
    except Exception:
        return default_holiday_template()


def save_holiday_template(settings: QSettings, template: HolidayTemplate) -> None:
    payload = holiday_template_to_payload(template)
    settings.setValue(TEMPLATE_VERSION_KEY, TEMPLATE_VERSION)
    settings.setValue(TEMPLATE_JSON_KEY, json.dumps(payload))
    settings.sync()


def holiday_template_to_payload(template: HolidayTemplate) -> dict:
    return {
        "template_version": TEMPLATE_VERSION,
        "federal_holidays": {
            holiday_id.value: bool(template.federal_holidays.get(holiday_id, True))
            for holiday_id in FEDERAL_HOLIDAY_ORDER
        },
        "custom_rules": [
            {
                "name": rule.name,
                "hours": rule.hours,
                "enabled": rule.enabled,
                "rule_type": rule.rule_type.value,
                "month": rule.month,
                "day": rule.day,
                "weekday": rule.weekday,
                "occurrence": rule.occurrence.value,
            }
            for rule in template.custom_rules
        ],
    }


def holiday_template_from_payload(payload: dict) -> HolidayTemplate:
    template = default_holiday_template()
    federal_payload = payload.get("federal_holidays", {})
    for holiday_id in FEDERAL_HOLIDAY_ORDER:
        if holiday_id.value in federal_payload:
            template.federal_holidays[holiday_id] = bool(federal_payload[holiday_id.value])

    custom_rules: list[CustomHolidayRule] = []
    for rule in payload.get("custom_rules", []):
        custom_rules.append(
            CustomHolidayRule(
                name=str(rule.get("name", "")).strip(),
                hours=float(rule.get("hours", 8.0)),
                enabled=bool(rule.get("enabled", True)),
                rule_type=HolidayRuleType(rule.get("rule_type", HolidayRuleType.FIXED_DATE.value)),
                month=int(rule.get("month", 1)),
                day=int(rule.get("day", 1)),
                weekday=int(rule.get("weekday", 0)),
                occurrence=HolidayOccurrence(rule.get("occurrence", HolidayOccurrence.FIRST.value)),
            )
        )
    template.custom_rules = custom_rules
    return template


def federal_holiday_rows() -> list[tuple[FederalHolidayId, str]]:
    return [(holiday_id, FEDERAL_HOLIDAY_LABELS[holiday_id]) for holiday_id in FEDERAL_HOLIDAY_ORDER]


def describe_custom_rule(rule: CustomHolidayRule) -> str:
    if rule.rule_type == HolidayRuleType.FIXED_DATE:
        return f"Every year on {rule.month:02d}-{rule.day:02d}"
    weekday_name = WEEKDAY_LABELS[rule.weekday]
    occurrence_label = OCCURRENCE_LABELS[rule.occurrence]
    return f"{occurrence_label} {weekday_name} of month {rule.month:02d}"


def _generate_federal_holiday_date(year: int, holiday_id: FederalHolidayId) -> date | None:
    if holiday_id == FederalHolidayId.NEW_YEARS_DAY:
        return _observed_or_none(date(year, 1, 1), year)
    if holiday_id == FederalHolidayId.MARTIN_LUTHER_KING_JR_DAY:
        return _nth_weekday(year, 1, 0, 3)
    if holiday_id == FederalHolidayId.WASHINGTONS_BIRTHDAY:
        return _nth_weekday(year, 2, 0, 3)
    if holiday_id == FederalHolidayId.MEMORIAL_DAY:
        return _last_weekday(year, 5, 0)
    if holiday_id == FederalHolidayId.JUNETEENTH:
        return _observed_or_none(date(year, 6, 19), year)
    if holiday_id == FederalHolidayId.INDEPENDENCE_DAY:
        return _observed_or_none(date(year, 7, 4), year)
    if holiday_id == FederalHolidayId.LABOR_DAY:
        return _nth_weekday(year, 9, 0, 1)
    if holiday_id == FederalHolidayId.COLUMBUS_DAY:
        return _nth_weekday(year, 10, 0, 2)
    if holiday_id == FederalHolidayId.VETERANS_DAY:
        return _observed_or_none(date(year, 11, 11), year)
    if holiday_id == FederalHolidayId.THANKSGIVING_DAY:
        return _nth_weekday(year, 11, 3, 4)
    if holiday_id == FederalHolidayId.CHRISTMAS_DAY:
        return _observed_or_none(date(year, 12, 25), year)
    return None


def _generate_custom_rule_date(year: int, rule: CustomHolidayRule) -> date | None:
    if rule.rule_type == HolidayRuleType.FIXED_DATE:
        try:
            return date(year, rule.month, rule.day)
        except ValueError:
            return None
    if rule.occurrence == HolidayOccurrence.LAST:
        return _last_weekday(year, rule.month, rule.weekday)
    return _nth_weekday(year, rule.month, rule.weekday, int(rule.occurrence.value))


def _observed_or_none(actual: date, year: int) -> date | None:
    observed = actual
    if actual.weekday() == 5:
        observed = actual - timedelta(days=1)
    elif actual.weekday() == 6:
        observed = actual + timedelta(days=1)
    if observed.year != year:
        return None
    return observed


def _nth_weekday(year: int, month: int, weekday: int, occurrence: int) -> date:
    current = date(year, month, 1)
    count = 0
    while True:
        if current.weekday() == weekday:
            count += 1
            if count == occurrence:
                return current
        current += timedelta(days=1)


def _last_weekday(year: int, month: int, weekday: int) -> date:
    if month == 12:
        current = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        current = date(year, month + 1, 1) - timedelta(days=1)
    while current.weekday() != weekday:
        current -= timedelta(days=1)
    return current
