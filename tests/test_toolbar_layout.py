"""Approved compact toolbar interactions and conditional processing warning."""
import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QToolButton


def test_two_rows_and_uniform_display_labels(window):
    assert len(window.toolbars) == 2
    assert window.processing_toolbar is window.main_toolbar
    assert window.view_toolbar is window.display_toolbar
    assert window.actions["Preferences..."] in window.main_toolbar.actions()
    for a in window.display_toolbar.actions():
        widget = window.display_toolbar.widgetForAction(a)
        if isinstance(widget, QToolButton):
            assert widget.toolButtonStyle() == Qt.ToolButtonTextUnderIcon
            assert widget.iconSize().width() == 21
            assert widget.text()
    actions = window.display_toolbar.actions()
    positions = [actions.index(window.layer_action(key)) for key in ("ortho", "dem", "cameras")]
    assert positions == sorted(positions)
    assert any(a.isSeparator() for a in actions[positions[1]+1:positions[2]])
    menu = window.show_items_button.menu().actions()
    for key in ("tiled", "camera_labels", "marker_labels", "trackball"):
        assert window.layer_action(key) in menu
    for key in ("ortho", "dem", "cameras", "markers", "shapes", "region", "grid"):
        assert window.layer_action(key) not in menu
    assert window.actions["Perspective/Orthographic"] in menu


def test_lightglue_warning_is_immediate_and_conditional(window, qtbot):
    from photomesh.dialogs import AlignPhotosDialog
    dialog = AlignPhotosDialog(window); qtbot.addWidget(dialog)
    assert dialog.neural_warning.isHidden()
    for method in ("SIFT + LightGlue", "ALIKED + LightGlue"):
        dialog.feature_method.setCurrentText(method)
        assert not dialog.neural_warning.isHidden()
        assert "may take a long time" in dialog.neural_warning.text()
        assert "CPU" in dialog.neural_warning.text()
    dialog.feature_method.setCurrentText("SIFT")
    assert dialog.neural_warning.isHidden()


def test_cube_view_icons_are_distinct_from_cursor_and_each_other(qapp):
    from photomesh.icons import render_image
    images = [render_image("view_" + name, 32) for name in
              ("top", "bottom", "left", "right", "front", "back", "isometric")]
    cursor = render_image("navigation", 32)
    assert all(image != cursor for image in images)
    # The isometric view uses the same cube face cue as Top; its label explains
    # the diagonal viewing direction. Opposite sides must remain distinguishable.
    for first, second in ((0, 1), (2, 3), (4, 5)):
        assert images[first] != images[second]


def test_split_layer_body_toggles_once_and_arrow_only_opens_menu(window, qtbot):
    from PySide6.QtCore import QPoint, QTimer
    from PySide6.QtWidgets import QStyle, QStyleOptionToolButton
    for button in window.mode_buttons:
        action = button.visibility
        original = action.isChecked()
        changes = []
        on_change = changes.append
        action.toggled.connect(on_change)
        try:
            qtbot.mouseClick(button, Qt.LeftButton, pos=QPoint(8, 8))
            assert action.isChecked() != original and button.isChecked() == action.isChecked()
            assert changes == [not original]
            selected = button.current
            qtbot.mouseClick(button, Qt.LeftButton, pos=QPoint(8, 8))
            assert action.isChecked() == original and button.current is selected
            assert changes == [not original, original]
            opened = []
            on_open = lambda values=opened: values.append(True)
            button.menu().aboutToShow.connect(on_open)
            option = QStyleOptionToolButton()
            button.initStyleOption(option)
            arrow = button.style().subControlRect(QStyle.CC_ToolButton, option,
                                                  QStyle.SC_ToolButtonMenu, button)
            assert not arrow.isEmpty()
            QTimer.singleShot(50, button.menu().close)
            qtbot.mouseClick(button, Qt.LeftButton, pos=arrow.center())
            qtbot.waitUntil(lambda: bool(opened))
            assert action.isChecked() == original
            assert changes == [not original, original]
            assert all(a.text() != "Hidden" for a in button.menu().actions())
        finally:
            action.toggled.disconnect(on_change)
            button.menu().close()
            action.setChecked(original)


def test_processing_labels_are_complete_and_approved(window):
    expected = ["Add Photos", "Align Photos", "Build Cloud", "Build Mesh", "Build Texture",
                "Build Tiled Model", "Build DEM", "Build Orthomosaic"]
    ids = ["Add Photos...", "Align Photos...", "Build Point Cloud...", "Build Model...",
           "Build Texture...", "Build Tiled Model...", "Build DEM...", "Build Orthomosaic..."]
    assert [window.actions[name].iconText() for name in ids] == expected


def test_removed_commands_have_no_handlers_or_shortcuts(window):
    from photomesh.mainwindow import SHORTCUTS
    for name in ("Full Screen", "Measure Shape..."):
        assert name not in window.actions
        assert name not in window._handlers()
        assert name not in SHORTCUTS
    assert not hasattr(window, "toggle_full_screen")
    assert not hasattr(window, "measure_shape")


def test_layer_button_initialization_does_not_invoke_commands(window, no_dialogs):
    assert no_dialogs == []
    for button in window.mode_buttons:
        assert button.isChecked() == button.visibility.isChecked()


@pytest.mark.parametrize("theme", ["Dark", "Light"])
@pytest.mark.parametrize("checked", [False, True])
def test_split_captions_have_room_beside_native_arrow(window, qtbot, theme, checked):
    from PySide6.QtWidgets import QApplication, QStyle, QStyleOptionToolButton
    from photomesh.theme import apply_theme
    apply_theme(QApplication.instance(), theme)
    for button in [*window.mode_buttons, window.transparency_button]:
        action = button.defaultAction()
        original = action.isChecked()
        try:
            action.setChecked(checked)
            button.ensurePolished()
            button.resize(button.sizeHint())
            option = QStyleOptionToolButton()
            button.initStyleOption(option)
            body = button.style().subControlRect(QStyle.CC_ToolButton, option,
                                                 QStyle.SC_ToolButton, button)
            arrow = button.style().subControlRect(QStyle.CC_ToolButton, option,
                                                  QStyle.SC_ToolButtonMenu, button)
            assert button.isChecked() == checked
            caption_width = body.width() - body.intersected(arrow).width()
            assert caption_width >= button.fontMetrics().horizontalAdvance(button.text()) + 8
            assert arrow.width() > 0
            assert button.minimumSizeHint().width() >= button.sizeHint().width()
        finally:
            action.setChecked(original)
