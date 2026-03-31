import os

import pytest
from PySide6.QtCore import QCoreApplication, QSettings

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(autouse=True)
def isolated_qsettings(tmp_path):
    QCoreApplication.setOrganizationName("PtoPlannerTests")
    QCoreApplication.setApplicationName("PTO Planner Tests")
    QSettings.setDefaultFormat(QSettings.IniFormat)
    QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, str(tmp_path))

    settings = QSettings()
    settings.clear()
    settings.sync()

    yield

    settings = QSettings()
    settings.clear()
    settings.sync()
