"""Clearly labelled processing, display and camera-view toolbars."""
from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import QToolBar, QLabel, QToolButton, QMenu
from .icons import layer_icon, TOOLBAR_ICON, MODE_ICON
from .toolbuttons import LayerModeButton


def build_toolbar(window):
    bars = []

    def bar(title, name, new_row=False):
        if new_row:
            window.addToolBarBreak()
        tb = QToolBar(title, window)
        tb.setObjectName(name)
        tb.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        tb.setIconSize(QSize(TOOLBAR_ICON, TOOLBAR_ICON))
        window.addToolBar(tb)
        label = QLabel(title + "  ")
        label.setMargin(3)
        tb.addWidget(label)
        bars.append(tb)
        return tb

    def action(tb, name, icon, label=None):
        a = window.actions[name]
        a.setIcon(layer_icon(icon))
        a.setToolTip(name.rstrip("."))
        if label:
            a.setIconText(label)
        tb.addAction(a)
        return a

    files = bar("Project", "toolbar")
    window.main_toolbar = files
    for name, icon in (("New", "file_new"), ("Open...", "file_open"), ("Save", "file_save"),
                       ("Undo", "undo"), ("Redo", "redo")):
        action(files, name, icon)
    action(files, "Preferences...", "preferences", "Settings")
    processing = bar("Processing", "processing_toolbar", True)
    window.processing_toolbar = processing
    for name, icon, label in (
        ("Add Photos...", "add_photos", "Photos"),
        ("Align Photos...", "align", "Align / Tie Points"),
        ("Build Point Cloud...", "cloud", "Point Cloud"),
        ("Build Model...", "mesh", "Mesh"),
        ("Build Texture...", "mode_textured", "Texture"),
        ("Build Tiled Model...", "mesh", "Tiles"),
        ("Build DEM...", "dem", "DEM"),
        ("Build Orthomosaic...", "ortho", "Orthomosaic")):
        action(processing, name, icon, label)

    display = bar("Display", "display_toolbar", True)
    window.display_toolbar = display

    def mode(key, title, entries):
        choices = []
        for name, icon, label in entries:
            a = window.actions[name]
            a.setIcon(layer_icon(icon))
            choices.append((a, label))
        button = LayerModeButton(display, choices, title, window.layer_action(key), MODE_ICON)
        button.setObjectName(key + "_display_button")
        display.addWidget(button)
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

    # Less frequent overlays stay in one labelled menu, not a duplicate row.
    extras = QToolButton(display)
    extras.setText("Layers")
    extras.setIcon(layer_icon("show_items"))
    extras.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
    extras.setPopupMode(QToolButton.InstantPopup)
    menu = QMenu(extras)
    for key in ("tiled", "ortho", "dem", "cameras", "camera_labels", "markers",
                "marker_labels", "shapes", "region", "grid", "trackball"):
        menu.addAction(window.layer_action(key))
    menu.addSeparator()
    menu.addAction(window.actions["Model/Show All"])
    menu.addAction(window.actions["Model/Hide All"])
    extras.setMenu(menu)
    display.addWidget(extras)
    window.show_items_button = extras
    display.addWidget(window._transparency_button(display))

    view = bar("View", "view_toolbar", True)
    window.view_toolbar = view
    for name in ("Top", "Bottom", "Left", "Right", "Front", "Back", "Isometric"):
        action(view, name, "navigation")
    view.addSeparator()
    for name, icon in (("Zoom In", "zoom_in"), ("Zoom Out", "zoom_out"), ("Reset View", "reset_view")):
        action(view, name, icon)
    action(view, "Perspective/Orthographic", "navigation", "Orthographic")
    window.toolbars = bars
    toggle = window.actions["View/Toolbar"]
    toggle.setChecked(True)
    toggle.toggled.connect(lambda on: [tb.setVisible(on) for tb in bars])
