"""Two compact toolbar rows; shared actions keep menus and Workspace in sync."""
from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import QToolBar, QToolButton, QMenu
from .icons import layer_icon, TOOLBAR_ICON
from .toolbuttons import LayerModeButton


def build_toolbar(window):
    def row(title, name, style):
        tb = QToolBar(title, window)
        tb.setObjectName(name)
        tb.setToolButtonStyle(style)
        tb.setIconSize(QSize(TOOLBAR_ICON, TOOLBAR_ICON))
        tb.setStyleSheet("QToolBar{spacing:0px;padding:1px;} QToolButton{padding:2px 3px;margin:0px;}")
        window.addToolBar(tb)
        return tb

    def action(tb, name, icon, label=None):
        a = window.actions[name]
        a.setIcon(layer_icon(icon))
        a.setToolTip(name.rstrip("."))
        a.setIconText(label or name.rstrip("."))
        tb.addAction(a)
        return a

    top = row("Project and processing", "toolbar", Qt.ToolButtonTextBesideIcon)
    window.main_toolbar = window.processing_toolbar = top
    for name, icon in (("New", "file_new"), ("Open...", "file_open"), ("Save", "file_save")):
        action(top, name, icon)
    top.addSeparator()
    action(top, "Undo", "undo"); action(top, "Redo", "redo")
    top.addSeparator()
    for name, icon, label in (
        ("Add Photos...", "add_photos", "Add Photos"),
        ("Align Photos...", "align", "Align Photos"),
        ("Build Point Cloud...", "cloud", "Build Cloud"),
        ("Build Model...", "mesh", "Build Mesh"),
        ("Build Texture...", "mode_textured", "Build Texture"),
        ("Build Tiled Model...", "tiled", "Build Tiled Model"),
        ("Build DEM...", "dem", "Build DEM"),
        ("Build Orthomosaic...", "ortho", "Build Orthomosaic")):
        action(top, name, icon, label)
    top.addSeparator()
    action(top, "Preferences...", "preferences", "Settings")

    window.addToolBarBreak()
    bottom = row("Display and views", "display_toolbar", Qt.ToolButtonTextUnderIcon)
    bottom.setStyleSheet("QToolBar{spacing:0px;padding:1px;} QToolButton{padding:2px 1px;margin:0px;}")
    window.display_toolbar = window.view_toolbar = bottom

    def mode(key, title, entries):
        choices = []
        for name, icon, label in entries:
            a = window.actions[name]
            a.setIcon(layer_icon(icon))
            choices.append((a, label))
        button = LayerModeButton(bottom, choices, title, window.layer_action(key), TOOLBAR_ICON)
        button.setObjectName(key + "_display_button")
        bottom.addWidget(button)
        return button

    window.tie_mode_button = mode("tie", "Tie Points", [
        ("Tie Points - Colors", "tie", "Colors")])
    window.cloud_mode_button = mode("cloud", "Cloud", [
        ("Point Cloud - Colors", "cloud_colors", "Colors"),
        ("Point Cloud - Solid", "cloud_solid", "Solid")])
    window.model_mode_button = mode("mesh", "Mesh", [
        ("Model - Shaded", "mode_shaded", "Shaded"),
        ("Model - Solid", "mode_solid", "Solid"),
        ("Model - Textured", "mode_textured", "Textured"),
        ("Model - Wireframe", "mode_wireframe", "Wireframe")])
    window.mode_buttons = [window.tie_mode_button, window.cloud_mode_button, window.model_mode_button]

    def layer(key, label):
        a = window.layer_action(key)
        a.setIconText(label)
        bottom.addAction(a)

    layer("ortho", "Ortho"); layer("dem", "DEM")
    bottom.addSeparator()
    for key, label in (("cameras", "Cameras"), ("markers", "Markers"), ("shapes", "Shapes"),
                       ("region", "Region"), ("grid", "Grid")):
        layer(key, label)
    window.transparency_action = window.actions["Transparent View"]
    window.transparency_action.setIconText("Transparency")
    transparency = window._transparency_button(bottom)
    transparency.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
    transparency.setIconSize(QSize(TOOLBAR_ICON, TOOLBAR_ICON))
    bottom.addWidget(transparency)

    extras = QToolButton(bottom)
    extras.setText("Layers"); extras.setIcon(layer_icon("layers"))
    extras.setIconSize(QSize(TOOLBAR_ICON, TOOLBAR_ICON))
    extras.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
    extras.setPopupMode(QToolButton.InstantPopup)
    extras.setToolTip("Additional layers, labels and view options")
    menu = QMenu(extras)
    for key in ("tiled", "camera_labels", "marker_labels", "trackball"):
        menu.addAction(window.layer_action(key))
    tiled_modes = menu.addMenu("Tiled model display")
    for name in ("Textured", "Solid", "Wireframe", "Elevation"):
        tiled_modes.addAction(window.actions["Tiled Model - " + name])
    menu.addSeparator()
    menu.addAction(window.actions["Perspective/Orthographic"])
    menu.addSeparator()
    menu.addAction(window.actions["Show All"])
    menu.addAction(window.actions["Hide All"])
    extras.setMenu(menu)
    bottom.addWidget(extras)
    window.show_items_button = extras

    bottom.addSeparator()
    for name in ("Top", "Bottom", "Left", "Right", "Front", "Back", "Isometric"):
        action(bottom, name, "view_" + name.lower(), "Iso" if name == "Isometric" else name)
    bottom.addSeparator()
    for name, icon, label in (("Zoom In", "zoom_in", "Zoom In"),
                              ("Zoom Out", "zoom_out", "Zoom Out"),
                              ("Reset View", "fit_view", "Fit")):
        action(bottom, name, icon, label)
    window.toolbars = [top, bottom]
    toggle = window.actions["Toolbar"]
    toggle.setChecked(True)
    toggle.toggled.connect(lambda on: [tb.setVisible(on) for tb in window.toolbars])
