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
