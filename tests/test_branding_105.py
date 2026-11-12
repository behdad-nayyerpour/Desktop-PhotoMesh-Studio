"""Rename contracts: settings/project compatibility and all icon consumers."""
import json

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from photomesh import APP_NAME, SETTINGS_APPLICATION, SETTINGS_ORGANIZATION


def test_display_rename_keeps_previous_settings_namespace(qapp):
    app = QApplication.instance()
    old = (app.organizationName(), app.applicationName(), app.applicationDisplayName())
    try:
        app.setOrganizationName(SETTINGS_ORGANIZATION)
        app.setApplicationName(SETTINGS_APPLICATION)
        app.setApplicationDisplayName(APP_NAME)
        previous = QSettings(QSettings.defaultFormat(), QSettings.UserScope,
                             "PhotoMesh", "PhotoMesh Studio")
        previous.setValue("ui/rename_contract", "kept")
        assert QSettings().fileName() == previous.fileName()
        assert QSettings().value("ui/rename_contract") == "kept"
        previous.remove("ui/rename_contract")
        assert app.applicationDisplayName() == "Lens2Mesh"
    finally:
        app.setOrganizationName(old[0])
        app.setApplicationName(old[1])
        app.setApplicationDisplayName(old[2])


def test_legacy_project_and_script_about_action_remain_usable(window, tmp_path):
    path = tmp_path / "legacy.pmsx"
    window.project.save(str(path))
    assert json.loads(path.read_text(encoding="utf-8"))["format"] == "photomesh-studio/2"
    action = window.actions["About PhotoMesh Studio..."]
    assert action.text() == "About Lens2Mesh..."
    assert APP_NAME in window.windowTitle()
