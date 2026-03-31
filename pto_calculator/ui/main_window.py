from __future__ import annotations

from datetime import date
from pathlib import Path

from PySide6.QtCore import QDate, QSettings, Qt, QSortFilterProxyModel, QModelIndex
from PySide6.QtGui import QAction, QColor, QCloseEvent, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDateEdit,
    QDialog,
    QDoubleSpinBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QStatusBar,
    QTabWidget,
    QTableView,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QAbstractItemView,
)
from PySide6.QtCore import QAbstractTableModel

from ..app_bootstrap import (
    APP_DESKTOP_FILE_NAME,
    APP_NAME,
    APP_ORGANIZATION_NAME,
    app_icon_path,
    ensure_windows_app_user_model_id,
)
from ..holiday_templates import load_holiday_template, save_holiday_template
from ..io_utils import export_projection_to_csv, export_projection_to_excel, load_scenario, save_scenario
from ..models import EntryType, HolidayEntry, ProjectionResult, ProjectionRowType
from ..services import PlannerService, create_default_scenario
from .holiday_selector import HolidaySelectorDialog


def load_app_icon() -> QIcon:
    return QIcon(str(app_icon_path()))


def configure_application(app: QApplication) -> QIcon:
    ensure_windows_app_user_model_id()
    if not app.organizationName():
        app.setOrganizationName(APP_ORGANIZATION_NAME)
    if not app.applicationName():
        app.setApplicationName(APP_NAME)
    if hasattr(app, "setApplicationDisplayName") and not app.applicationDisplayName():
        app.setApplicationDisplayName(APP_NAME)
    if hasattr(app, "setDesktopFileName") and not app.desktopFileName():
        app.setDesktopFileName(APP_DESKTOP_FILE_NAME)
    icon = load_app_icon()
    if not icon.isNull():
        app.setWindowIcon(icon)
    return icon


def main() -> None:
    app = QApplication.instance() or QApplication([])
    configure_application(app)
    app.setStyle("Fusion")

    window = MainWindow()
    window.show()
    app.exec()


class SummaryCard(QFrame):
    def __init__(self, title: str, object_name: str) -> None:
        super().__init__()
        self.setObjectName("summaryCard")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(6)

        title_label = QLabel(title)
        title_label.setObjectName("summaryCardTitle")
        self.value_label = QLabel("0.0000 h")
        self.value_label.setObjectName(object_name)

        layout.addWidget(title_label)
        layout.addWidget(self.value_label)

    def set_value(self, value: str) -> None:
        self.value_label.setText(value)


def default_date_for_year(year: int) -> date:
    today = date.today()
    day = today.day
    while day >= 1:
        try:
            return date(year, today.month, day)
        except ValueError:
            day -= 1
    return date(year, 1, 1)


class NullableDateEdit(QDateEdit):
    def __init__(self, year: int, object_name: str) -> None:
        super().__init__()
        self._year = year
        self.setObjectName(object_name)
        self.setDisplayFormat("yyyy-MM-dd")
        self.setCalendarPopup(True)
        self.setSpecialValueText("Select date")
        self.set_year(year)

    def set_year(self, year: int) -> None:
        self._year = year
        sentinel = QDate(year - 1, 12, 31)
        default_date = default_date_for_year(year)
        self.blockSignals(True)
        self.setDateRange(sentinel, QDate(year, 12, 31))
        self.setDate(QDate(default_date.year, default_date.month, default_date.day))
        self.blockSignals(False)
        self._sync_popup_to_date(QDate(default_date.year, default_date.month, default_date.day))

    def set_date_value(self, value: date | None) -> None:
        self.blockSignals(True)
        if value is None:
            self.clear_date_value()
        else:
            self.setDate(QDate(value.year, value.month, value.day))
            self.blockSignals(False)
            return
        self.blockSignals(False)

    def date_value(self) -> date | None:
        current = self.date()
        if current == self.minimumDate():
            return None
        return current.toPython()

    def set_default_date_value(self) -> None:
        default_date = default_date_for_year(self._year)
        self.blockSignals(True)
        self.setDate(QDate(default_date.year, default_date.month, default_date.day))
        self.blockSignals(False)
        self._sync_popup_to_date(QDate(default_date.year, default_date.month, default_date.day))

    def clear_date_value(self) -> None:
        default_date = default_date_for_year(self._year)
        self.blockSignals(True)
        self.setDate(self.minimumDate())
        self.blockSignals(False)
        self._sync_popup_to_date(QDate(default_date.year, default_date.month, default_date.day))

    def _sync_popup_to_date(self, popup_date: QDate) -> None:
        calendar = self.calendarWidget()
        calendar.setCurrentPage(popup_date.year(), popup_date.month())


class ProjectionTableModel(QAbstractTableModel):
    HEADERS = [
        "Date",
        "Type",
        "Label",
        "Reg Start",
        "Float Start",
        "Reg Change",
        "Float Change",
        "Reg Used",
        "Float Used",
        "Reg End",
        "Float End",
        "Note",
    ]

    TYPE_LABELS = {
        ProjectionRowType.PAYDAY: "Payday",
        ProjectionRowType.FLOAT_AWARD: "Float Award",
        ProjectionRowType.PLANNED_PTO: "Planned PTO",
        ProjectionRowType.YEAR_END: "Year End",
    }

    def __init__(self) -> None:
        super().__init__()
        self._result: ProjectionResult | None = None

    def set_result(self, result: ProjectionResult | None) -> None:
        self.beginResetModel()
        self._result = result
        self.endResetModel()

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid() or self._result is None:
            return 0
        return len(self._result.rows)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self.HEADERS)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            return self.HEADERS[section]
        return section + 1

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid() or self._result is None:
            return None

        row = self._result.rows[index.row()]
        column = index.column()

        if role == Qt.DisplayRole:
            values = [
                row.date.isoformat(),
                self.TYPE_LABELS[row.row_type],
                row.label,
                f"{row.regular_start:.4f}",
                f"{row.float_start:.4f}",
                f"{row.regular_change:.4f}",
                f"{row.float_change:.4f}",
                f"{row.regular_used:.4f}",
                f"{row.float_used:.4f}",
                f"{row.regular_end:.4f}",
                f"{row.float_end:.4f}",
                row.note,
            ]
            return values[column]

        if role == Qt.UserRole:
            values = [
                row.date.toordinal(),
                self.TYPE_LABELS[row.row_type],
                row.label,
                row.regular_start,
                row.float_start,
                row.regular_change,
                row.float_change,
                row.regular_used,
                row.float_used,
                row.regular_end,
                row.float_end,
                row.note,
            ]
            return values[column]

        if role == Qt.TextAlignmentRole and column >= 3:
            return int(Qt.AlignRight | Qt.AlignVCenter)

        if role == Qt.BackgroundRole:
            backgrounds = {
                ProjectionRowType.PAYDAY: QColor("#ecfdf3"),
                ProjectionRowType.FLOAT_AWARD: QColor("#eef7ff"),
                ProjectionRowType.PLANNED_PTO: QColor("#fff8ea"),
                ProjectionRowType.YEAR_END: QColor("#f1eefc"),
            }
            return backgrounds[row.row_type]

        if role == Qt.ForegroundRole and column in {9, 10}:
            if row.row_type == ProjectionRowType.YEAR_END and self._result is not None:
                if self._result.regular_forfeiture > 0 or self._result.float_forfeiture > 0:
                    return QColor("#b42318")

        return None

    def row_at(self, source_row: int):
        if self._result is None:
            return None
        return self._result.rows[source_row]


class ProjectionFilterProxyModel(QSortFilterProxyModel):
    def __init__(self) -> None:
        super().__init__()
        self._type_filter = "All"
        self._text_filter = ""
        self.setSortRole(Qt.UserRole)

    def set_type_filter(self, value: str) -> None:
        self._type_filter = value
        self.invalidateFilter()

    def set_text_filter(self, value: str) -> None:
        self._text_filter = value.strip().lower()
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        model = self.sourceModel()
        if not isinstance(model, ProjectionTableModel):
            return True
        row = model.row_at(source_row)
        if row is None:
            return False

        if self._type_filter != "All":
            label = ProjectionTableModel.TYPE_LABELS[row.row_type]
            if label != self._type_filter:
                return False

        if not self._text_filter:
            return True

        haystack = " ".join(
            [
                row.date.isoformat(),
                ProjectionTableModel.TYPE_LABELS[row.row_type],
                row.label,
                row.note,
            ]
        ).lower()
        return self._text_filter in haystack


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        app = QApplication.instance()
        icon = load_app_icon()
        if app is not None:
            icon = configure_application(app)
        self.settings = QSettings()
        holiday_template = load_holiday_template(self.settings)
        self.service = PlannerService(holiday_template=holiday_template)
        self.projection_model = ProjectionTableModel()
        self.projection_proxy = ProjectionFilterProxyModel()
        self.projection_proxy.setSourceModel(self.projection_model)

        self.setWindowTitle(APP_NAME)
        if not icon.isNull():
            self.setWindowIcon(icon)
        self.resize(1480, 940)
        self.setMinimumSize(1220, 760)
        self._build_ui()
        self._build_menu()
        self._apply_styles()
        self._load_settings()
        self._populate_from_scenario()
        self._clear_projection()

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)

        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(16, 16, 16, 16)
        root_layout.setSpacing(12)

        self.workspace_tabs = QTabWidget()
        self.workspace_tabs.setObjectName("workspaceTabs")
        root_layout.addWidget(self.workspace_tabs)

        self.planner_tab = QWidget()
        planner_layout = QVBoxLayout(self.planner_tab)
        planner_layout.setContentsMargins(0, 0, 0, 0)
        planner_layout.setSpacing(12)

        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setChildrenCollapsible(False)
        planner_layout.addWidget(self.splitter)

        scenario_content = QWidget()
        scenario_content.setObjectName("sidebar")
        scenario_layout = QVBoxLayout(scenario_content)
        scenario_layout.setContentsMargins(0, 0, 0, 0)
        scenario_layout.setSpacing(12)
        scenario_layout.addWidget(self._build_scenario_panel())
        scenario_layout.addStretch(1)

        self.sidebar_scroll = QScrollArea()
        self.sidebar_scroll.setObjectName("sidebarScrollArea")
        self.sidebar_scroll.setWidgetResizable(True)
        self.sidebar_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.sidebar_scroll.setFrameShape(QFrame.NoFrame)
        self.sidebar_scroll.setMinimumWidth(430)
        self.sidebar_scroll.setWidget(scenario_content)

        planner_detail_content = QWidget()
        planner_detail_layout = QVBoxLayout(planner_detail_content)
        planner_detail_layout.setContentsMargins(0, 0, 0, 0)
        planner_detail_layout.setSpacing(12)
        planner_detail_layout.addWidget(self._build_planned_panel())
        planner_detail_layout.addWidget(self._build_holiday_panel())
        planner_detail_layout.addStretch(1)

        self.planner_detail_scroll = QScrollArea()
        self.planner_detail_scroll.setObjectName("plannerDetailScrollArea")
        self.planner_detail_scroll.setWidgetResizable(True)
        self.planner_detail_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.planner_detail_scroll.setFrameShape(QFrame.NoFrame)
        self.planner_detail_scroll.setWidget(planner_detail_content)

        self.splitter.addWidget(self.sidebar_scroll)
        self.splitter.addWidget(self.planner_detail_scroll)
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setSizes([440, 940])

        self.projection_tab = QWidget()
        main_layout = QVBoxLayout(self.projection_tab)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(12)
        main_layout.addWidget(self._build_summary_cards())
        main_layout.addWidget(self._build_projection_panel(), 1)

        self.workspace_tabs.addTab(self.planner_tab, "Planner")
        self.workspace_tabs.addTab(self.projection_tab, "Projection")
        self.workspace_tabs.setCurrentWidget(self.planner_tab)

        self.setStatusBar(QStatusBar())

    def _build_menu(self) -> None:
        self.file_menu = self.menuBar().addMenu("File")

        new_action = QAction("New Scenario", self)
        new_action.triggered.connect(self._new_scenario)
        self.file_menu.addAction(new_action)

        save_action = QAction("Save Scenario…", self)
        save_action.triggered.connect(self._save_scenario)
        self.file_menu.addAction(save_action)

        load_action = QAction("Load Scenario…", self)
        load_action.triggered.connect(self._load_scenario)
        self.file_menu.addAction(load_action)

        self.file_menu.addSeparator()

        export_csv_action = QAction("Export CSV…", self)
        export_csv_action.triggered.connect(self._export_csv)
        self.file_menu.addAction(export_csv_action)

        export_xlsx_action = QAction("Export Excel…", self)
        export_xlsx_action.triggered.connect(self._export_excel)
        self.file_menu.addAction(export_xlsx_action)

        self.file_menu.addSeparator()

        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        self.file_menu.addAction(exit_action)

        self.tools_menu = self.menuBar().addMenu("Tools")

        holiday_selector_action = QAction("Holiday Selector", self)
        holiday_selector_action.setObjectName("holidaySelectorAction")
        holiday_selector_action.triggered.connect(self._open_holiday_selector)
        self.tools_menu.addAction(holiday_selector_action)

    def _build_scenario_panel(self) -> QWidget:
        group = QGroupBox("Scenario")
        layout = QGridLayout(group)
        layout.setHorizontalSpacing(10)
        layout.setVerticalSpacing(8)

        self.scenario_name_edit = QLineEdit()
        self.scenario_name_edit.setObjectName("scenarioNameEdit")
        self.scenario_name_edit.textEdited.connect(self._invalidate_projection)

        self.year_spinbox = QSpinBox()
        self.year_spinbox.setObjectName("yearSpinBox")
        self.year_spinbox.setRange(2000, 2100)
        self.year_spinbox.valueChanged.connect(self._on_year_changed)

        self.regular_balance_spinbox = self._make_double_spinbox("regularBalanceSpinBox", 0.0, 500.0, 0.5)
        self.accrual_spinbox = self._make_double_spinbox("accrualSpinBox", 0.0, 40.0, 0.25)
        self.float_balance_spinbox = self._make_double_spinbox("floatBalanceSpinBox", 0.0, 200.0, 0.5)
        self.regular_cap_spinbox = self._make_double_spinbox("regularCapSpinBox", 0.0, 200.0, 0.5)
        self.float_award_spinbox = self._make_double_spinbox("floatAwardSpinBox", 0.0, 80.0, 0.5)
        self.holiday_hours_spinbox = self._make_double_spinbox("holidayHoursSpinBox", 0.0, 24.0, 0.5)

        self.last_pay_date_edit = NullableDateEdit(self.service.scenario.year, "lastPayDateEdit")
        self.last_pay_date_edit.dateChanged.connect(self._invalidate_projection)

        self.calculate_button = QPushButton("Calculate Projection")
        self.calculate_button.setObjectName("calculateButton")
        self.calculate_button.clicked.connect(self._calculate_projection)

        self.reset_holidays_button = QPushButton("Reset Holiday Defaults")
        self.reset_holidays_button.clicked.connect(self._reset_holidays)

        row = 0
        layout.addWidget(QLabel("Scenario Name"), row, 0)
        layout.addWidget(self.scenario_name_edit, row, 1)
        row += 1
        layout.addWidget(QLabel("PTO Year"), row, 0)
        layout.addWidget(self.year_spinbox, row, 1)
        row += 1
        layout.addWidget(QLabel("Regular Balance (h)"), row, 0)
        layout.addWidget(self.regular_balance_spinbox, row, 1)
        row += 1
        layout.addWidget(QLabel("Accrual / Pay Period"), row, 0)
        layout.addWidget(self.accrual_spinbox, row, 1)
        row += 1
        layout.addWidget(QLabel("Float Balance (h)"), row, 0)
        layout.addWidget(self.float_balance_spinbox, row, 1)
        row += 1
        layout.addWidget(QLabel("Last Pay Date"), row, 0)
        layout.addWidget(self.last_pay_date_edit, row, 1)
        row += 1
        layout.addWidget(QLabel("Year-End PTO Cap"), row, 0)
        layout.addWidget(self.regular_cap_spinbox, row, 1)
        row += 1
        layout.addWidget(QLabel("Float Award / Quarter"), row, 0)
        layout.addWidget(self.float_award_spinbox, row, 1)
        row += 1
        layout.addWidget(QLabel("Default Holiday Hours"), row, 0)
        layout.addWidget(self.holiday_hours_spinbox, row, 1)
        row += 1
        layout.addWidget(self.calculate_button, row, 0, 1, 2)
        row += 1
        layout.addWidget(self.reset_holidays_button, row, 0, 1, 2)

        return group

    def _build_planned_panel(self) -> QWidget:
        group = QGroupBox("Planned PTO")
        layout = QVBoxLayout(group)
        layout.setSpacing(8)

        form = QGridLayout()
        self.planned_date_edit = self._make_date_edit("plannedDateEdit")
        self.planned_hours_spinbox = self._make_double_spinbox("plannedHoursSpinBox", 0.0, 24.0, 0.5)
        self.planned_type_combo = QComboBox()
        self.planned_type_combo.setObjectName("plannedTypeComboBox")
        self.planned_type_combo.addItems([EntryType.REGULAR.value, EntryType.FLOAT.value])
        self.planned_note_edit = QLineEdit()
        self.planned_note_edit.setObjectName("plannedNoteEdit")
        self.planned_note_edit.setPlaceholderText("Optional note")
        self.add_planned_button = QPushButton("Add Entry")
        self.add_planned_button.setObjectName("addPlannedButton")
        self.add_planned_button.clicked.connect(self._add_planned_entry)

        form.addWidget(QLabel("Date"), 0, 0)
        form.addWidget(self.planned_date_edit, 0, 1)
        form.addWidget(QLabel("Hours"), 1, 0)
        form.addWidget(self.planned_hours_spinbox, 1, 1)
        form.addWidget(QLabel("Type"), 2, 0)
        form.addWidget(self.planned_type_combo, 2, 1)
        form.addWidget(QLabel("Note"), 3, 0)
        form.addWidget(self.planned_note_edit, 3, 1)
        form.addWidget(self.add_planned_button, 4, 0, 1, 2)
        layout.addLayout(form)

        range_form = QGridLayout()
        self.range_start_edit = self._make_date_edit("rangeStartEdit")
        self.range_end_edit = self._make_date_edit("rangeEndEdit")
        self.range_start_edit.dateChanged.connect(self._sync_range_end_to_start)
        self.range_hours_spinbox = self._make_double_spinbox("rangeHoursSpinBox", 0.0, 24.0, 0.5)
        self.range_type_combo = QComboBox()
        self.range_type_combo.setObjectName("rangeTypeComboBox")
        self.range_type_combo.addItems([EntryType.REGULAR.value, EntryType.FLOAT.value])
        self.add_range_button = QPushButton("Add Range")
        self.add_range_button.setObjectName("addRangeButton")
        self.add_range_button.clicked.connect(self._add_planned_range)

        range_form.addWidget(QLabel("Range Start"), 0, 0)
        range_form.addWidget(self.range_start_edit, 0, 1)
        range_form.addWidget(QLabel("Range End"), 1, 0)
        range_form.addWidget(self.range_end_edit, 1, 1)
        range_form.addWidget(QLabel("Hours / Day"), 2, 0)
        range_form.addWidget(self.range_hours_spinbox, 2, 1)
        range_form.addWidget(QLabel("Range Type"), 3, 0)
        range_form.addWidget(self.range_type_combo, 3, 1)
        range_form.addWidget(self.add_range_button, 4, 0, 1, 2)
        layout.addLayout(range_form)

        self.planned_table = QTableWidget(0, 5)
        self.planned_table.setObjectName("plannedEntriesTable")
        self.planned_table.setHorizontalHeaderLabels(["Date", "Hours", "Type", "Source", "Note"])
        self.planned_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.planned_table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.planned_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.planned_table.verticalHeader().setVisible(False)
        self.planned_table.horizontalHeader().setStretchLastSection(True)
        self.planned_table.setMinimumHeight(150)
        layout.addWidget(self.planned_table, 1)

        self.remove_planned_button = QPushButton("Remove Selected")
        self.remove_planned_button.setObjectName("removePlannedButton")
        self.remove_planned_button.clicked.connect(self._remove_planned_entries)
        layout.addWidget(self.remove_planned_button)

        return group

    def _build_holiday_panel(self) -> QWidget:
        group = QGroupBox("Holiday Calendar")
        layout = QVBoxLayout(group)
        layout.setSpacing(8)

        form = QGridLayout()
        self.holiday_date_edit = self._make_date_edit("holidayDateEdit")
        self.holiday_name_edit = QLineEdit()
        self.holiday_name_edit.setObjectName("holidayNameEdit")
        self.holiday_hours_editor = self._make_double_spinbox("holidayEditorHoursSpinBox", 0.0, 24.0, 0.5)
        self.add_holiday_button = QPushButton("Add Holiday")
        self.add_holiday_button.setObjectName("addHolidayButton")
        self.add_holiday_button.clicked.connect(self._add_holiday)

        form.addWidget(QLabel("Date"), 0, 0)
        form.addWidget(self.holiday_date_edit, 0, 1)
        form.addWidget(QLabel("Name"), 1, 0)
        form.addWidget(self.holiday_name_edit, 1, 1)
        form.addWidget(QLabel("Hours"), 2, 0)
        form.addWidget(self.holiday_hours_editor, 2, 1)
        form.addWidget(self.add_holiday_button, 3, 0, 1, 2)
        layout.addLayout(form)

        self.holiday_table = QTableWidget(0, 4)
        self.holiday_table.setObjectName("holidaysTable")
        self.holiday_table.setHorizontalHeaderLabels(["Enabled", "Date", "Name", "Hours"])
        self.holiday_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.holiday_table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.holiday_table.verticalHeader().setVisible(False)
        self.holiday_table.horizontalHeader().setStretchLastSection(True)
        self.holiday_table.setMinimumHeight(180)
        layout.addWidget(self.holiday_table, 1)

        actions = QHBoxLayout()
        self.add_remaining_holidays_button = QPushButton("Add Remaining to Planner")
        self.add_remaining_holidays_button.setObjectName("addRemainingHolidaysButton")
        self.add_remaining_holidays_button.clicked.connect(self._add_remaining_holidays)
        self.remove_holiday_button = QPushButton("Remove Selected")
        self.remove_holiday_button.setObjectName("removeHolidayButton")
        self.remove_holiday_button.clicked.connect(self._remove_holidays)
        actions.addWidget(self.add_remaining_holidays_button)
        actions.addWidget(self.remove_holiday_button)
        layout.addLayout(actions)

        return group

    def _build_summary_cards(self) -> QWidget:
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        self.regular_summary_card = SummaryCard("Projected Regular PTO", "regularSummaryValue")
        self.float_summary_card = SummaryCard("Projected Float PTO", "floatSummaryValue")
        self.planned_summary_card = SummaryCard("Planned PTO", "plannedSummaryValue")
        self.forfeiture_summary_card = SummaryCard("Potential Forfeiture", "forfeitureSummaryValue")

        layout.addWidget(self.regular_summary_card)
        layout.addWidget(self.float_summary_card)
        layout.addWidget(self.planned_summary_card)
        layout.addWidget(self.forfeiture_summary_card)
        return container

    def _build_projection_panel(self) -> QWidget:
        group = QGroupBox("Projection")
        layout = QVBoxLayout(group)
        layout.setSpacing(8)

        filters = QHBoxLayout()
        self.filter_text_edit = QLineEdit()
        self.filter_text_edit.setObjectName("projectionFilterEdit")
        self.filter_text_edit.setPlaceholderText("Filter by date, type, label, or note")
        self.filter_text_edit.textChanged.connect(self.projection_proxy.set_text_filter)

        self.filter_type_combo = QComboBox()
        self.filter_type_combo.setObjectName("projectionTypeFilterComboBox")
        self.filter_type_combo.addItems(["All", "Payday", "Float Award", "Planned PTO", "Year End"])
        self.filter_type_combo.currentTextChanged.connect(self.projection_proxy.set_type_filter)

        filters.addWidget(self.filter_text_edit, 1)
        filters.addWidget(self.filter_type_combo)
        layout.addLayout(filters)

        self.projection_table = QTableView()
        self.projection_table.setObjectName("projectionTableView")
        self.projection_table.setModel(self.projection_proxy)
        self.projection_table.setSortingEnabled(True)
        self.projection_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.projection_table.setAlternatingRowColors(False)
        self.projection_table.verticalHeader().setVisible(False)
        self.projection_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.projection_table, 1)

        return group

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow, QWidget {
                background: #f7f6f2;
                color: #1f2937;
                font-family: "Segoe UI", "Avenir Next", sans-serif;
                font-size: 13px;
            }
            QScrollArea, QScrollArea > QWidget > QWidget {
                background: transparent;
            }
            QTabWidget::pane {
                border: none;
                background: transparent;
            }
            QTabBar::tab {
                background: #ece6d8;
                color: #5b4a31;
                border: 1px solid #d9d3c5;
                border-bottom: none;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
                padding: 10px 16px;
                margin-right: 4px;
                font-weight: 600;
            }
            QTabBar::tab:selected {
                background: #fffdf8;
                color: #1f2937;
            }
            QGroupBox {
                background: #fffdf8;
                border: 1px solid #ddd7ca;
                border-radius: 14px;
                margin-top: 10px;
                padding-top: 14px;
                font-weight: 600;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 14px;
                padding: 0 6px;
                color: #5b4a31;
            }
            QLineEdit, QDoubleSpinBox, QSpinBox, QComboBox, QDateEdit {
                background: #ffffff;
                border: 1px solid #d9d3c5;
                border-radius: 10px;
                min-height: 22px;
                padding: 7px 10px;
            }
            QTableView, QTableWidget {
                background: #ffffff;
                border: 1px solid #d9d3c5;
                border-radius: 10px;
                gridline-color: #e8e1d5;
            }
            QPushButton {
                background: #1f6f78;
                color: white;
                border: none;
                border-radius: 10px;
                padding: 9px 12px;
                min-height: 22px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #165660;
            }
            QPushButton:pressed {
                background: #123d44;
            }
            QHeaderView::section {
                background: #ece6d8;
                color: #453622;
                border: none;
                border-right: 1px solid #d9d3c5;
                border-bottom: 1px solid #d9d3c5;
                padding: 8px;
                font-weight: 600;
            }
            QTableWidget::item:selected, QTableView::item:selected {
                background: #cde7ea;
                color: #123d44;
            }
            #summaryCard {
                background: #fffdf8;
                border: 1px solid #ddd7ca;
                border-radius: 18px;
                min-height: 86px;
            }
            #summaryCardTitle {
                color: #6b7280;
                font-size: 12px;
                font-weight: 600;
            }
            #regularSummaryValue, #floatSummaryValue, #plannedSummaryValue, #forfeitureSummaryValue {
                font-size: 22px;
                font-weight: 700;
                color: #0f172a;
            }
            """
        )

    def _load_settings(self) -> None:
        geometry = self.settings.value("main_window_geometry")
        if geometry is not None:
            self.restoreGeometry(geometry)
        splitter_state = self.settings.value("main_splitter")
        if splitter_state is not None:
            self.splitter.restoreState(splitter_state)
        current_tab = self.settings.value("workspace_tab_index")
        if current_tab is not None:
            self.workspace_tabs.setCurrentIndex(int(current_tab))

    def closeEvent(self, event: QCloseEvent) -> None:
        self.settings.setValue("main_window_geometry", self.saveGeometry())
        self.settings.setValue("main_splitter", self.splitter.saveState())
        self.settings.setValue("workspace_tab_index", self.workspace_tabs.currentIndex())
        super().closeEvent(event)

    def _make_double_spinbox(self, object_name: str, minimum: float, maximum: float, step: float) -> QDoubleSpinBox:
        spinbox = QDoubleSpinBox()
        spinbox.setObjectName(object_name)
        spinbox.setRange(minimum, maximum)
        spinbox.setDecimals(4)
        spinbox.setSingleStep(step)
        spinbox.valueChanged.connect(self._invalidate_projection)
        return spinbox

    def _make_date_edit(self, object_name: str) -> QDateEdit:
        edit = QDateEdit()
        edit.setObjectName(object_name)
        edit.setDisplayFormat("yyyy-MM-dd")
        edit.setCalendarPopup(True)
        edit.dateChanged.connect(self._invalidate_projection)
        return edit

    def _populate_from_scenario(self) -> None:
        scenario = self.service.scenario
        self.scenario_name_edit.setText(scenario.name)
        self.year_spinbox.blockSignals(True)
        self.year_spinbox.setValue(scenario.year)
        self.year_spinbox.blockSignals(False)
        self.regular_balance_spinbox.setValue(scenario.regular_balance)
        self.accrual_spinbox.setValue(scenario.accrual_per_period)
        self.float_balance_spinbox.setValue(scenario.float_balance)
        self.regular_cap_spinbox.setValue(scenario.policy.regular_pto_cap)
        self.float_award_spinbox.setValue(scenario.policy.float_award_per_quarter)
        self.holiday_hours_spinbox.setValue(scenario.policy.holiday_hours)
        self.last_pay_date_edit.set_year(scenario.year)
        if scenario.last_pay_date is None:
            self.last_pay_date_edit.set_default_date_value()
        else:
            self.last_pay_date_edit.set_date_value(scenario.last_pay_date)
        self._reset_form_dates(scenario.year)
        self._refresh_planned_table()
        self._refresh_holiday_table()

    def _reset_form_dates(self, year: int) -> None:
        default_date = default_date_for_year(year)
        qdate = QDate(default_date.year, default_date.month, default_date.day)
        for widget in (self.planned_date_edit, self.range_start_edit, self.range_end_edit, self.holiday_date_edit):
            widget.blockSignals(True)
            widget.setDate(qdate)
            widget.blockSignals(False)

    def _sync_range_end_to_start(self, selected_date: QDate) -> None:
        self.range_end_edit.blockSignals(True)
        self.range_end_edit.setDate(selected_date)
        self.range_end_edit.blockSignals(False)

    def _refresh_planned_table(self) -> None:
        self.planned_table.setRowCount(0)
        for planned_entry in self.service.scenario.planned_entries:
            row = self.planned_table.rowCount()
            self.planned_table.insertRow(row)
            self.planned_table.setItem(row, 0, QTableWidgetItem(planned_entry.date.isoformat()))
            self.planned_table.setItem(row, 1, QTableWidgetItem(f"{planned_entry.hours:.4f}"))
            self.planned_table.setItem(row, 2, QTableWidgetItem(planned_entry.entry_type.value))
            self.planned_table.setItem(row, 3, QTableWidgetItem(planned_entry.source.value))
            self.planned_table.setItem(row, 4, QTableWidgetItem(planned_entry.note))

    def _refresh_holiday_table(self) -> None:
        self.holiday_table.setRowCount(0)
        for holiday in self.service.scenario.holidays:
            row = self.holiday_table.rowCount()
            self.holiday_table.insertRow(row)

            enabled_item = QTableWidgetItem()
            enabled_item.setFlags(enabled_item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEditable)
            enabled_item.setCheckState(Qt.Checked if holiday.enabled else Qt.Unchecked)
            self.holiday_table.setItem(row, 0, enabled_item)
            self.holiday_table.setItem(row, 1, QTableWidgetItem(holiday.date.isoformat()))
            self.holiday_table.setItem(row, 2, QTableWidgetItem(holiday.name))
            self.holiday_table.setItem(row, 3, QTableWidgetItem(f"{holiday.hours:.4f}"))

    def _read_holidays_from_table(self) -> list[HolidayEntry]:
        holidays: list[HolidayEntry] = []
        for row in range(self.holiday_table.rowCount()):
            enabled_item = self.holiday_table.item(row, 0)
            date_item = self.holiday_table.item(row, 1)
            name_item = self.holiday_table.item(row, 2)
            hours_item = self.holiday_table.item(row, 3)
            if not date_item or not name_item or not hours_item:
                continue
            holidays.append(
                HolidayEntry(
                    date=self._parse_date(date_item.text(), allow_blank=False),
                    name=name_item.text().strip(),
                    hours=float(hours_item.text()),
                    enabled=enabled_item.checkState() == Qt.Checked if enabled_item else True,
                )
            )
        return sorted(holidays, key=lambda holiday: (holiday.date, holiday.name))

    def _sync_scenario_from_form(self) -> None:
        scenario = self.service.scenario
        scenario.name = self.scenario_name_edit.text().strip() or "Untitled Scenario"
        scenario.year = int(self.year_spinbox.value())
        scenario.regular_balance = float(self.regular_balance_spinbox.value())
        scenario.accrual_per_period = float(self.accrual_spinbox.value())
        scenario.float_balance = float(self.float_balance_spinbox.value())
        scenario.policy.regular_pto_cap = float(self.regular_cap_spinbox.value())
        scenario.policy.float_award_per_quarter = float(self.float_award_spinbox.value())
        scenario.policy.holiday_hours = float(self.holiday_hours_spinbox.value())
        scenario.last_pay_date = self.last_pay_date_edit.date_value()
        scenario.holidays = self._read_holidays_from_table()
        self.service.sort_entries()
        self.service.sort_holidays()

    def _parse_date(self, text: str, allow_blank: bool) -> date | None:
        text = text.strip()
        if not text:
            if allow_blank:
                return None
            raise ValueError("Date is required.")
        parsed = date.fromisoformat(text)
        return parsed

    def _selected_rows(self, table: QTableWidget) -> list[int]:
        return sorted({index.row() for index in table.selectionModel().selectedRows()})

    def _invalidate_projection(self) -> None:
        self.service.projection = None
        self._clear_projection()

    def _clear_projection(self) -> None:
        self.projection_model.set_result(None)
        self.regular_summary_card.set_value("0.0000 h")
        self.float_summary_card.set_value("0.0000 h")
        self.planned_summary_card.set_value("0.0000 h")
        self.forfeiture_summary_card.set_value("0.0000 h")

    def _on_year_changed(self, year: int) -> None:
        self._sync_scenario_from_form()
        self.service.set_year(year)
        self._populate_from_scenario()
        self._clear_projection()
        self.statusBar().showMessage(f"Switched to PTO year {year}. Planned entries were cleared and holidays reset.", 5000)

    def _add_planned_entry(self) -> None:
        try:
            entry_date = self.planned_date_edit.date().toPython()
            self._ensure_year_match(entry_date, "Planned PTO date")
            hours = float(self.planned_hours_spinbox.value())
            if hours <= 0:
                raise ValueError("Hours must be greater than zero.")
            self.service.add_planned_entry(
                when=entry_date,
                hours=hours,
                entry_type=EntryType(self.planned_type_combo.currentText()),
                note=self.planned_note_edit.text().strip(),
            )
        except ValueError as exc:
            self._warn("Planned PTO", str(exc))
            return
        self._refresh_planned_table()
        self._clear_projection()

    def _add_planned_range(self) -> None:
        try:
            start = self.range_start_edit.date().toPython()
            end = self.range_end_edit.date().toPython()
            self._ensure_year_match(start, "Range start")
            self._ensure_year_match(end, "Range end")
            if end < start:
                raise ValueError("Range end must be on or after the start date.")
            hours = float(self.range_hours_spinbox.value())
            if hours <= 0:
                raise ValueError("Hours must be greater than zero.")
            self.service.add_planned_range(
                start=start,
                end=end,
                hours=hours,
                entry_type=EntryType(self.range_type_combo.currentText()),
            )
        except ValueError as exc:
            self._warn("Planned PTO Range", str(exc))
            return
        self._refresh_planned_table()
        self._clear_projection()

    def _remove_planned_entries(self) -> None:
        rows = self._selected_rows(self.planned_table)
        if not rows:
            self._warn("Planned PTO", "Select one or more planned entries to remove.")
            return
        self.service.remove_planned_entries(rows)
        self._refresh_planned_table()
        self._clear_projection()

    def _add_holiday(self) -> None:
        try:
            holiday_date = self.holiday_date_edit.date().toPython()
            self._ensure_year_match(holiday_date, "Holiday date")
            holiday_name = self.holiday_name_edit.text().strip()
            if not holiday_name:
                raise ValueError("Holiday name is required.")
            holiday_hours = float(self.holiday_hours_editor.value())
            if holiday_hours <= 0:
                raise ValueError("Holiday hours must be greater than zero.")
            self.service.add_holiday(HolidayEntry(holiday_date, holiday_name, holiday_hours, True))
        except ValueError as exc:
            self._warn("Holiday Calendar", str(exc))
            return
        self._refresh_holiday_table()
        self._clear_projection()

    def _remove_holidays(self) -> None:
        rows = self._selected_rows(self.holiday_table)
        if not rows:
            self._warn("Holiday Calendar", "Select one or more holidays to remove.")
            return
        self.service.remove_holidays(rows)
        self._refresh_holiday_table()
        self._clear_projection()

    def _reset_holidays(self) -> None:
        self._sync_scenario_from_form()
        self.service.reset_holidays()
        self._refresh_holiday_table()
        self._clear_projection()

    def _open_holiday_selector(self) -> None:
        self._sync_scenario_from_form()
        dialog = HolidaySelectorDialog(self.service.holiday_template, self)
        if dialog.exec() != QDialog.Accepted:
            return
        self._apply_holiday_template(dialog.result_template(), dialog.save_as_default)

    def _apply_holiday_template(self, template, save_as_default: bool) -> None:
        self._sync_scenario_from_form()
        self.service.set_holiday_template(template, apply_to_current=True)
        if save_as_default:
            save_holiday_template(self.settings, template)
            self.statusBar().showMessage("Applied holiday template and saved it as the default.", 5000)
        else:
            self.statusBar().showMessage("Applied holiday template to the current scenario.", 5000)
        self._refresh_holiday_table()
        self._clear_projection()

    def _add_remaining_holidays(self) -> None:
        try:
            self._sync_scenario_from_form()
            added = self.service.add_remaining_holiday_entries()
        except ValueError as exc:
            self._warn("Holiday Planner", str(exc))
            return
        self._refresh_planned_table()
        self._clear_projection()
        self.statusBar().showMessage(f"Added {added} remaining holiday entries to the planner.", 5000)

    def _calculate_projection(self) -> None:
        try:
            self._sync_scenario_from_form()
            if self.service.scenario.last_pay_date is None:
                raise ValueError("Last pay date is required.")
            self._ensure_year_match(self.service.scenario.last_pay_date, "Last pay date")
            result = self.service.calculate_projection()
        except Exception as exc:
            self._warn("Projection", str(exc))
            return

        self.projection_model.set_result(result)
        self.projection_table.sortByColumn(0, Qt.AscendingOrder)
        self.regular_summary_card.set_value(f"{result.final_regular_balance:.4f} h")
        self.float_summary_card.set_value(f"{result.final_float_balance:.4f} h")
        self.planned_summary_card.set_value(f"{result.total_planned_hours:.4f} h")
        self.forfeiture_summary_card.set_value(f"{result.regular_forfeiture + result.float_forfeiture:.4f} h")
        self.workspace_tabs.setCurrentWidget(self.projection_tab)
        self.statusBar().showMessage(f"Calculated {result.pay_period_count} pay periods for {result.year}.", 5000)

    def _ensure_year_match(self, input_date: date, label: str) -> None:
        if input_date.year != self.year_spinbox.value():
            raise ValueError(f"{label} must be inside the selected PTO year.")

    def _new_scenario(self) -> None:
        self.service.replace_scenario(create_default_scenario(holiday_template=self.service.holiday_template))
        self._populate_from_scenario()
        self._clear_projection()
        self.statusBar().showMessage("Started a new scenario.", 5000)

    def _save_scenario(self) -> None:
        try:
            self._sync_scenario_from_form()
        except Exception as exc:
            self._warn("Save Scenario", str(exc))
            return

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save PTO Scenario",
            f"{self.service.scenario.name}.json",
            "JSON Files (*.json)",
        )
        if not path:
            return
        save_scenario(path, self.service.scenario)
        self.statusBar().showMessage(f"Saved scenario to {Path(path).name}.", 5000)

    def _load_scenario(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Load PTO Scenario",
            "",
            "JSON Files (*.json)",
        )
        if not path:
            return
        try:
            scenario = load_scenario(path)
        except Exception as exc:
            self._warn("Load Scenario", str(exc))
            return
        self.service.replace_scenario(scenario)
        self._populate_from_scenario()
        self._clear_projection()
        self.statusBar().showMessage(f"Loaded scenario from {Path(path).name}.", 5000)

    def _export_csv(self) -> None:
        if self.service.projection is None:
            self._warn("Export CSV", "Calculate a projection before exporting.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export CSV", "pto_projection.csv", "CSV Files (*.csv)")
        if not path:
            return
        export_projection_to_csv(path, self.service.projection)
        self.statusBar().showMessage(f"Exported CSV to {Path(path).name}.", 5000)

    def _export_excel(self) -> None:
        if self.service.projection is None:
            self._warn("Export Excel", "Calculate a projection before exporting.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export Excel", "pto_projection.xlsx", "Excel Files (*.xlsx)")
        if not path:
            return
        export_projection_to_excel(path, self.service.projection)
        self.statusBar().showMessage(f"Exported Excel to {Path(path).name}.", 5000)

    def _warn(self, title: str, message: str) -> None:
        QMessageBox.warning(self, title, message)
