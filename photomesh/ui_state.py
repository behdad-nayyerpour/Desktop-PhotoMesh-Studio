"""Versioned window layout; no project data or photo paths are rewritten."""
from PySide6.QtCore import QSettings

KEY = "ui/layout_v104"


def restore_window_state(window):
    settings = QSettings()
    geometry = settings.value(KEY + "/geometry")
    state = settings.value(KEY + "/state")
    if geometry is not None:
        window.restoreGeometry(geometry)
    if state is not None:
        window.restoreState(state, 104)
    splitter = settings.value(KEY + "/project_splitter")
    if splitter is not None:
        window.workspace_splitter.restoreState(splitter)
    window.plan_view.setCurrentWidget(window.photo_view if
        settings.value(KEY + "/plan_content", "ortho", str) == "photo" else window.ortho_view)
    window.tabs.setCurrentIndex(1 if settings.value(KEY + "/active_tab", 0, int) == 1 else 0)
    mode = settings.value(KEY + "/mesh_mode", "shaded", str)
    if mode in ("shaded", "solid", "textured", "wireframe"):
        window.model_view.set_mesh_mode(mode)
        window._sync_mode_button("Model - " + mode.capitalize())
    solid = settings.value(KEY + "/cloud_solid", False, bool)
    window.model_view.set_solid("cloud", solid)
    window._sync_mode_button("Point Cloud - " + ("Solid" if solid else "Colors"))
    mode = settings.value(KEY + "/tiled_mode", "textured", str)
    if mode in ("textured", "solid", "wireframe", "elevation"):
        window.model_view.set_tiled_mode(mode)
    window.actions["Perspective/Orthographic"].setChecked(settings.value(KEY + "/orthographic", False, bool))
    # Toolbar visibility is restored by Qt; synchronize the shared menu action.
    toolbar_action = window.actions["Toolbar"]
    toolbar_action.blockSignals(True)
    toolbar_action.setChecked(any(not toolbar.isHidden() for toolbar in window.toolbars))
    toolbar_action.blockSignals(False)
    for name, dock in window.docks.items():
        action = window.actions[name]
        action.blockSignals(True)
        action.setChecked(not dock.isHidden())
        action.blockSignals(False)
    # A removed monitor must not strand the main window outside every screen.
    screens = window.screen().virtualSiblings() if window.screen() else []
    if screens and not any(screen.availableGeometry().intersects(window.frameGeometry()) for screen in screens):
        window.move(screens[0].availableGeometry().topLeft())


def save_window_state(window):
    settings = QSettings()
    settings.setValue(KEY + "/geometry", window.saveGeometry())
    settings.setValue(KEY + "/state", window.saveState(104))
    settings.setValue(KEY + "/project_splitter", window.workspace_splitter.saveState())
    settings.setValue(KEY + "/active_tab", window.tabs.currentIndex())
    settings.setValue(KEY + "/plan_content", "photo" if window.plan_view.currentWidget() is window.photo_view else "ortho")
    settings.setValue(KEY + "/mesh_mode", window.model_view.mesh_mode)
    settings.setValue(KEY + "/cloud_solid", window.model_view.solid.get("cloud", False))
    settings.setValue(KEY + "/tiled_mode", window.model_view.tiled_mode)
    settings.setValue(KEY + "/orthographic", window.model_view.ortho)
    settings.sync()
