from __future__ import annotations

from copy import deepcopy
from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..holiday_templates import (
    OCCURRENCE_LABELS,
    WEEKDAY_LABELS,
    copy_holiday_template,
    describe_custom_rule,
    federal_holiday_rows,
)
from ..models import CustomHolidayRule, HolidayOccurrence, HolidayRuleType, HolidayTemplate


class CustomHolidayRuleDialog(QDialog):
    def __init__(self, rule: CustomHolidayRule | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("customHolidayRuleDialog")
        self.setWindowTitle("Custom Holiday")
        self.setModal(True)
        self.resize(430, 250)

        layout = QVBoxLayout(self)
        form = QGridLayout()
        form.setHorizontalSpacing(10)
        form.setVerticalSpacing(8)

        self.name_edit = QLineEdit()
        self.name_edit.setObjectName("customHolidayNameEdit")

        self.enabled_checkbox = QCheckBox("Enabled")
        self.enabled_checkbox.setObjectName("customHolidayEnabledCheckBox")
        self.enabled_checkbox.setChecked(True)

        self.hours_spinbox = QDoubleSpinBox()
        self.hours_spinbox.setObjectName("customHolidayHoursSpinBox")
        self.hours_spinbox.setRange(0.5, 24.0)
        self.hours_spinbox.setDecimals(4)
        self.hours_spinbox.setSingleStep(0.5)
        self.hours_spinbox.setValue(8.0)

        self.rule_type_combo = QComboBox()
        self.rule_type_combo.setObjectName("customHolidayRuleTypeComboBox")
        self.rule_type_combo.addItem("Fixed date", HolidayRuleType.FIXED_DATE)
        self.rule_type_combo.addItem("Nth weekday", HolidayRuleType.NTH_WEEKDAY)
        self.rule_type_combo.currentIndexChanged.connect(self._update_rule_inputs)

        self.month_spinbox = QSpinBox()
        self.month_spinbox.setObjectName("customHolidayMonthSpinBox")
        self.month_spinbox.setRange(1, 12)

        self.day_spinbox = QSpinBox()
        self.day_spinbox.setObjectName("customHolidayDaySpinBox")
        self.day_spinbox.setRange(1, 31)

        self.weekday_combo = QComboBox()
        self.weekday_combo.setObjectName("customHolidayWeekdayComboBox")
        for index, label in enumerate(WEEKDAY_LABELS):
            self.weekday_combo.addItem(label, index)

        self.occurrence_combo = QComboBox()
        self.occurrence_combo.setObjectName("customHolidayOccurrenceComboBox")
        for occurrence, label in OCCURRENCE_LABELS.items():
            self.occurrence_combo.addItem(label, occurrence)

        row = 0
        form.addWidget(QLabel("Name"), row, 0)
        form.addWidget(self.name_edit, row, 1)
        row += 1
        form.addWidget(QLabel("Hours"), row, 0)
        form.addWidget(self.hours_spinbox, row, 1)
        row += 1
        form.addWidget(QLabel("Rule Type"), row, 0)
        form.addWidget(self.rule_type_combo, row, 1)
        row += 1
        form.addWidget(QLabel("Month"), row, 0)
        form.addWidget(self.month_spinbox, row, 1)
        row += 1
        form.addWidget(QLabel("Day"), row, 0)
        form.addWidget(self.day_spinbox, row, 1)
        row += 1
        form.addWidget(QLabel("Weekday"), row, 0)
        form.addWidget(self.weekday_combo, row, 1)
        row += 1
        form.addWidget(QLabel("Occurrence"), row, 0)
        form.addWidget(self.occurrence_combo, row, 1)
        row += 1
        form.addWidget(self.enabled_checkbox, row, 1)

        layout.addLayout(form)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setObjectName("customHolidayCancelButton")
        self.cancel_button.clicked.connect(self.reject)
        self.save_button = QPushButton("Save")
        self.save_button.setObjectName("customHolidaySaveButton")
        self.save_button.clicked.connect(self.accept)
        buttons.addWidget(self.cancel_button)
        buttons.addWidget(self.save_button)
        layout.addLayout(buttons)

        self._populate(rule or CustomHolidayRule(name="", month=1, day=1))
        self._update_rule_inputs()

    def _populate(self, rule: CustomHolidayRule) -> None:
        self.name_edit.setText(rule.name)
        self.enabled_checkbox.setChecked(rule.enabled)
        self.hours_spinbox.setValue(rule.hours)
        self.rule_type_combo.setCurrentIndex(self.rule_type_combo.findData(rule.rule_type))
        self.month_spinbox.setValue(rule.month)
        self.day_spinbox.setValue(rule.day)
        self.weekday_combo.setCurrentIndex(self.weekday_combo.findData(rule.weekday))
        self.occurrence_combo.setCurrentIndex(self.occurrence_combo.findData(rule.occurrence))

    def _update_rule_inputs(self) -> None:
        is_fixed_date = self.rule_type_combo.currentData() == HolidayRuleType.FIXED_DATE
        self.day_spinbox.setEnabled(is_fixed_date)
        self.weekday_combo.setEnabled(not is_fixed_date)
        self.occurrence_combo.setEnabled(not is_fixed_date)

    def holiday_rule(self) -> CustomHolidayRule:
        name = self.name_edit.text().strip()
        if not name:
            raise ValueError("Custom holiday name is required.")

        rule_type = self.rule_type_combo.currentData()
        month = int(self.month_spinbox.value())
        day = int(self.day_spinbox.value())
        weekday = int(self.weekday_combo.currentData())
        occurrence = self.occurrence_combo.currentData()
        hours = float(self.hours_spinbox.value())

        if rule_type == HolidayRuleType.FIXED_DATE:
            validation_year = 2024 if month == 2 and day == 29 else 2025
            try:
                date(validation_year, month, day)
            except ValueError as exc:
                raise ValueError("Enter a valid month/day combination for the recurring holiday.") from exc

        return CustomHolidayRule(
            name=name,
            hours=hours,
            enabled=self.enabled_checkbox.isChecked(),
            rule_type=rule_type,
            month=month,
            day=day,
            weekday=weekday,
            occurrence=occurrence,
        )

    def accept(self) -> None:
        try:
            self.holiday_rule()
        except ValueError as exc:
            QMessageBox.warning(self, "Custom Holiday", str(exc))
            return
        super().accept()


class HolidaySelectorDialog(QDialog):
    def __init__(self, template: HolidayTemplate, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("holidaySelectorDialog")
        self.setWindowTitle("Holiday Selector")
        self.setModal(True)
        self.resize(760, 560)

        self.save_as_default = False
        self._result_template = copy_holiday_template(template)
        self.custom_rules = deepcopy(template.custom_rules)

        layout = QVBoxLayout(self)
        intro = QLabel(
            "Choose which U.S. federal holidays are included by default and add your own recurring holidays."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        content = QHBoxLayout()
        content.addWidget(self._build_federal_group(), 1)
        content.addWidget(self._build_custom_group(), 1)
        layout.addLayout(content, 1)

        actions = QHBoxLayout()
        actions.addStretch(1)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setObjectName("cancelHolidayTemplateButton")
        self.cancel_button.clicked.connect(self.reject)
        self.apply_button = QPushButton("Apply")
        self.apply_button.setObjectName("applyHolidayTemplateButton")
        self.apply_button.clicked.connect(lambda: self._finish(save_as_default=False))
        self.apply_save_button = QPushButton("Apply and Save as Default")
        self.apply_save_button.setObjectName("applyAndSaveHolidayTemplateButton")
        self.apply_save_button.clicked.connect(lambda: self._finish(save_as_default=True))
        actions.addWidget(self.cancel_button)
        actions.addWidget(self.apply_button)
        actions.addWidget(self.apply_save_button)
        layout.addLayout(actions)

        self._populate_federal_table(template)
        self._refresh_custom_rules_table()

    def _build_federal_group(self) -> QWidget:
        group = QGroupBox("U.S. Federal Holidays")
        layout = QVBoxLayout(group)
        helper = QLabel("Official OPM-recognized federal holidays under 5 U.S.C. 6103.")
        helper.setWordWrap(True)
        layout.addWidget(helper)

        self.federal_table = QTableWidget(0, 2)
        self.federal_table.setObjectName("federalHolidayTable")
        self.federal_table.setHorizontalHeaderLabels(["Include", "Holiday"])
        self.federal_table.setSelectionMode(QAbstractItemView.NoSelection)
        self.federal_table.verticalHeader().setVisible(False)
        self.federal_table.horizontalHeader().setStretchLastSection(True)
        self.federal_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        layout.addWidget(self.federal_table, 1)
        return group

    def _build_custom_group(self) -> QWidget:
        group = QGroupBox("Custom Recurring Holidays")
        layout = QVBoxLayout(group)
        helper = QLabel("These recurring holidays are generated each year from the saved rule.")
        helper.setWordWrap(True)
        layout.addWidget(helper)

        self.custom_rules_table = QTableWidget(0, 4)
        self.custom_rules_table.setObjectName("customHolidayRulesTable")
        self.custom_rules_table.setHorizontalHeaderLabels(["Enabled", "Name", "Rule", "Hours"])
        self.custom_rules_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.custom_rules_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.custom_rules_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.custom_rules_table.verticalHeader().setVisible(False)
        self.custom_rules_table.horizontalHeader().setStretchLastSection(True)
        self.custom_rules_table.itemDoubleClicked.connect(lambda _: self._edit_custom_rule())
        layout.addWidget(self.custom_rules_table, 1)

        buttons = QHBoxLayout()
        self.add_rule_button = QPushButton("Add")
        self.add_rule_button.setObjectName("addCustomHolidayRuleButton")
        self.add_rule_button.clicked.connect(self._add_custom_rule)
        self.edit_rule_button = QPushButton("Edit Selected")
        self.edit_rule_button.setObjectName("editCustomHolidayRuleButton")
        self.edit_rule_button.clicked.connect(self._edit_custom_rule)
        self.remove_rule_button = QPushButton("Remove Selected")
        self.remove_rule_button.setObjectName("removeCustomHolidayRuleButton")
        self.remove_rule_button.clicked.connect(self._remove_custom_rule)
        buttons.addWidget(self.add_rule_button)
        buttons.addWidget(self.edit_rule_button)
        buttons.addWidget(self.remove_rule_button)
        layout.addLayout(buttons)
        return group

    def _populate_federal_table(self, template: HolidayTemplate) -> None:
        self.federal_table.setRowCount(0)
        for holiday_id, label in federal_holiday_rows():
            row = self.federal_table.rowCount()
            self.federal_table.insertRow(row)
            enabled_item = QTableWidgetItem()
            enabled_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
            enabled_item.setCheckState(Qt.Checked if template.federal_holidays.get(holiday_id, True) else Qt.Unchecked)
            enabled_item.setData(Qt.UserRole, holiday_id)
            name_item = QTableWidgetItem(label)
            name_item.setFlags(Qt.ItemIsEnabled)
            self.federal_table.setItem(row, 0, enabled_item)
            self.federal_table.setItem(row, 1, name_item)

    def _refresh_custom_rules_table(self) -> None:
        self.custom_rules_table.setRowCount(0)
        for rule in self.custom_rules:
            row = self.custom_rules_table.rowCount()
            self.custom_rules_table.insertRow(row)
            enabled_item = QTableWidgetItem()
            enabled_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsUserCheckable)
            enabled_item.setCheckState(Qt.Checked if rule.enabled else Qt.Unchecked)
            name_item = QTableWidgetItem(rule.name)
            name_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            description_item = QTableWidgetItem(describe_custom_rule(rule))
            description_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            hours_item = QTableWidgetItem(f"{rule.hours:.4f}")
            hours_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.custom_rules_table.setItem(row, 0, enabled_item)
            self.custom_rules_table.setItem(row, 1, name_item)
            self.custom_rules_table.setItem(row, 2, description_item)
            self.custom_rules_table.setItem(row, 3, hours_item)

    def _selected_custom_rule_index(self) -> int | None:
        selection = self.custom_rules_table.selectionModel()
        if selection is None or not selection.selectedRows():
            return None
        return selection.selectedRows()[0].row()

    def _add_custom_rule(self) -> None:
        dialog = CustomHolidayRuleDialog(parent=self)
        if dialog.exec() != QDialog.Accepted:
            return
        self.custom_rules.append(dialog.holiday_rule())
        self._refresh_custom_rules_table()

    def _edit_custom_rule(self) -> None:
        selected_row = self._selected_custom_rule_index()
        if selected_row is None:
            QMessageBox.warning(self, "Holiday Selector", "Select a custom holiday rule to edit.")
            return
        dialog = CustomHolidayRuleDialog(self._current_custom_rules()[selected_row], self)
        if dialog.exec() != QDialog.Accepted:
            return
        self.custom_rules[selected_row] = dialog.holiday_rule()
        self._refresh_custom_rules_table()
        self.custom_rules_table.selectRow(selected_row)

    def _remove_custom_rule(self) -> None:
        selected_row = self._selected_custom_rule_index()
        if selected_row is None:
            QMessageBox.warning(self, "Holiday Selector", "Select a custom holiday rule to remove.")
            return
        del self.custom_rules[selected_row]
        self._refresh_custom_rules_table()

    def _current_custom_rules(self) -> list[CustomHolidayRule]:
        rules = deepcopy(self.custom_rules)
        for row, rule in enumerate(rules):
            enabled_item = self.custom_rules_table.item(row, 0)
            rule.enabled = enabled_item.checkState() == Qt.Checked if enabled_item else rule.enabled
        return rules

    def selected_template(self) -> HolidayTemplate:
        federal_holidays = {}
        for row in range(self.federal_table.rowCount()):
            enabled_item = self.federal_table.item(row, 0)
            holiday_id = enabled_item.data(Qt.UserRole)
            federal_holidays[holiday_id] = enabled_item.checkState() == Qt.Checked

        return HolidayTemplate(
            federal_holidays=federal_holidays,
            custom_rules=self._current_custom_rules(),
        )

    def _finish(self, save_as_default: bool) -> None:
        self.save_as_default = save_as_default
        self._result_template = self.selected_template()
        self.accept()

    def result_template(self) -> HolidayTemplate:
        return copy_holiday_template(self._result_template)
