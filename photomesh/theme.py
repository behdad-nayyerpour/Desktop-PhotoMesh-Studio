"""Dark Fusion theme (original styling)."""
from PySide6.QtGui import QPalette, QColor
from PySide6.QtWidgets import QApplication


def apply_dark_theme(app: QApplication) -> None:
    if app.style().objectName().lower() != "fusion":
        app.setStyle("Fusion")
    p = QPalette()
    base, window, text = QColor(43, 43, 43), QColor(53, 53, 55), QColor(220, 220, 220)
    p.setColor(QPalette.Window, window)
    p.setColor(QPalette.WindowText, text)
    p.setColor(QPalette.Base, base)
    p.setColor(QPalette.AlternateBase, QColor(48, 48, 50))
    p.setColor(QPalette.ToolTipBase, QColor(30, 30, 30))
    p.setColor(QPalette.ToolTipText, text)
    p.setColor(QPalette.Text, text)
    p.setColor(QPalette.Button, window)
    p.setColor(QPalette.ButtonText, text)
    p.setColor(QPalette.BrightText, QColor(255, 80, 80))
    p.setColor(QPalette.Highlight, QColor(52, 120, 198))
    p.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
    p.setColor(QPalette.Link, QColor(90, 160, 240))
    for role in (QPalette.Text, QPalette.WindowText, QPalette.ButtonText):
        p.setColor(QPalette.Disabled, role, QColor(120, 120, 120))
    app.setPalette(p)
    app.setStyleSheet("""
        QDockWidget::title { background: #3a3a3d; padding: 4px; }
        QDockWidget { titlebar-close-icon: none; }
        QToolBar { background: #3a3a3d; border: none; spacing: 2px; }
        QToolButton { padding: 3px 5px; }
        QToolButton:checked { background: #2f5f94; border-radius: 3px; }
        QTabBar::tab { background: #3a3a3d; padding: 5px 14px; border: 1px solid #2a2a2a; }
        QTabBar::tab:selected { background: #2b2b2b; border-bottom-color: #3478c6; }
        QMenu::separator { height: 1px; background: #555; margin: 4px 8px; }
        QStatusBar { background: #3a3a3d; }
        QHeaderView::section { background: #3a3a3d; padding: 3px; border: 1px solid #2a2a2a; }
    """)


def apply_theme(app, name=None):
    """Apply a persisted palette and refresh custom viewports immediately."""
    from PySide6.QtCore import QSettings
    from PySide6.QtGui import QPalette
    name = name or QSettings().value("ui/theme", "Dark", str)
    if name == "Light":
        if app.style().objectName().lower() != "fusion":
            app.setStyle("Fusion")
        app.setStyleSheet("")
        app.setPalette(app.style().standardPalette())
    else:
        apply_dark_theme(app)
    light = name == "Light"
    for widget in app.allWidgets():
        if hasattr(widget, "apply_theme"):
            widget.apply_theme(light)
        widget.update()


def viewport_color():
    from PySide6.QtCore import QSettings
    return QColor(228, 230, 234) if QSettings().value("ui/theme", "Dark") == "Light" else QColor(74, 74, 80)
