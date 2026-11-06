"""Native split buttons: primary click toggles a layer, arrow selects its style."""
from __future__ import annotations

from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import QToolButton, QMenu, QStyle, QStyleOptionToolButton
from shiboken6 import isValid


class LayerModeButton(QToolButton):
    """Share the visibility QAction with menus and Workspace; retain mode while off."""

    def __init__(self, parent, entries, title, visibility, icon_size=26):
        super().__init__(parent)
        self.visibility = visibility
        self.title = title
        self._labels = dict(entries)
        self.current = entries[0][0]
        self.setDefaultAction(visibility)
        self.setPopupMode(QToolButton.MenuButtonPopup)
        self.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.setIconSize(QSize(icon_size, icon_size))
        self.setAutoRaise(True)
        self.setStyleSheet("QToolButton{padding:2px 1px;margin:0px;}")
        menu = QMenu(self)
        for action, _label in entries:
            action.setCheckable(True)
            menu.addAction(action)
            action.triggered.connect(lambda _=False, selected=action: self.set_current(selected))
        self.setMenu(menu)
        visibility.changed.connect(self._sync_visibility)
        self._sync_visibility()

    def sizeHint(self):
        hint = super().sizeHint()
        option = QStyleOptionToolButton()
        self.initStyleOption(option)
        arrow = self.style().pixelMetric(QStyle.PM_MenuButtonIndicator, option, self)
        # The menu indicator occupies part of the native label rectangle.
        # Reserve it in addition to the complete caption and breathing room.
        caption = self.fontMetrics().horizontalAdvance(getattr(self, "title", self.text()))
        hint.setWidth(max(hint.width(), caption + max(arrow, 12) + 16))
        return hint

    def minimumSizeHint(self):
        return self.sizeHint()

    def set_current(self, action):
        if action not in self._labels:
            return
        self.current = action
        self._sync_visibility()

    def labels(self):
        return list(self._labels.values())

    def actionEvent(self, event):
        super().actionEvent(event)
        if getattr(self, "current", None) is not None:
            self._sync_visibility()

    def _sync_visibility(self):
        if not isValid(self) or not isValid(self.visibility) or not isValid(self.current):
            return
        self.setText(self.title)
        self.setIcon(self.current.icon())
        state = "On" if self.visibility.isChecked() else "Off"
        self.setToolTip(f"{self.title}: {state}, {self._labels[self.current]}. "
                        "Click to show/hide; arrow selects a display style.")
        for action in self._labels:
            if not isValid(action):
                continue
            previous = action.blockSignals(True)
            action.setChecked(action is self.current)
            action.blockSignals(previous)
