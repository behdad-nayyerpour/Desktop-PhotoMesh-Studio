"""Stable commands across menus, toolbars, scripts and workspace controls."""
from PySide6.QtGui import QKeySequence
from photomesh.mainwindow import SHORTCUTS
from photomesh.menus import LEGACY_ACTION_GROUPS


def _leaves(menu):
    for action in menu.actions():
        if action.menu():
            yield from _leaves(action.menu())
        elif not action.isSeparator():
            yield action


def test_commands_are_shared_not_recreated(window):
    leaves = [a for menu in window.menus.values() for a in _leaves(menu)]
    assert len(leaves) == len({id(a) for a in leaves})
    assert {a.objectName()[8:] for a in leaves} == {
        name for name, a in window.actions.items() if a.objectName() == "command:" + name
    }
    for group, names in LEGACY_ACTION_GROUPS.items():
        for name in names:
            assert window.actions[group + "/" + name] is window.actions[name]
    assert window.actions["Process/Align Photos..."] is window.actions["Workflow/Align Photos..."]
    assert window.actions["Export/Export Mesh Contours..."] is window.actions["File/Export Mesh Contours..."]
    assert window.actions["Photo/Show Shapes"] is window.actions["Display/Show Shapes"]
    assert window.unhandled_actions == []


def test_moved_processing_action_invokes_handler_once(window, monkeypatch):
    calls = []
    monkeypatch.setattr(window, "align_photos", lambda: calls.append("align"))
    # Bound handlers must be collected while constructing the window.
    from photomesh.mainwindow import MainWindow
    monkeypatch.setattr(MainWindow, "align_photos", lambda self: calls.append("align"))
    other = MainWindow()
    try:
        other.actions["Process/Align Photos..."].trigger()
        assert calls == ["align"]
        assert other.actions["Align Photos..."] in other.processing_toolbar.actions()
    finally:
        other.project.modified = False
        other.close()


def test_shortcuts_survive_menu_moves(window):
    for name, shortcut in SHORTCUTS.items():
        assert window.actions[name].shortcut() == QKeySequence(shortcut), name
    assert window.actions["Transparent View"].shortcut().toString() == "Ctrl+Shift+T"


def test_dock_actions_stay_synchronized(window, qtbot):
    for name, dock in window.docks.items():
        action = window.actions["Display/" + name]
        original = not dock.isHidden()
        action.setChecked(not original)
        qtbot.waitUntil(lambda: dock.isHidden() == original)
        assert action.isChecked() == (not dock.isHidden())
        dock.setVisible(original)
        qtbot.waitUntil(lambda: action.isChecked() == original)


def test_single_shape_action_updates_all_entry_points(window):
    action = window.layer_action("shapes")
    original = action.isChecked()
    try:
        action.setChecked(not original)
        assert window.workspace.vis["shapes"] == (not original)
        assert window.model_view.show["shapes"] == (not original)
        assert window.actions["Ortho/Show Shapes"].isChecked() == (not original)
        assert action in window.display_toolbar.actions()
    finally:
        action.setChecked(original)


def test_photo_commands_require_their_input(window, image_dir, no_dialogs):
    assert not window.actions["Rotate Left"].isEnabled()
    assert not window.actions["Open Next Photo"].isEnabled()
    window.add_photos(sorted(str(p) for p in image_dir.iterdir()))
    assert window.actions["Open Next Photo"].isEnabled()
    assert not window.actions["Rotate Left"].isEnabled()
    window.open_photo(0)
    assert window.actions["Rotate Left"].isEnabled()
    assert window.actions["Rotate Right"].isEnabled()
    before = window.photo_view.view.transform()
    window.actions["Edit/Rotate Right"].trigger()
    assert window.photo_view.view.transform() != before
    window.new_project()
    assert not window.actions["Rotate Left"].isEnabled()
    assert not window.actions["Open Next Photo"].isEnabled()
