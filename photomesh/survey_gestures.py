"""Shared screen-space line handles; normal drags belong to viewport navigation."""
import numpy as np
from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QColor, QPen


class LineGesture:
    def __init__(self):
        self.press = None
        self.editing = None
        self.line = None
        self.moved = False
        self.last = None

    def start(self, position, line=None):
        self.press = np.asarray(position, float)
        self.last = self.press.copy()
        self.line = None if line is None else np.asarray(line, float).copy()
        self.moved, self.editing = False, None
        if self.line is not None:
            handles = np.vstack([self.line, self.line.mean(0)])
            distances = np.linalg.norm(handles - self.press, axis=1)
            index = int(np.argmin(distances))
            if distances[index] <= 10:
                self.editing = index
        return self.editing is not None

    def move(self, position):
        if self.press is None:
            return None
        delta = np.asarray(position, float) - self.press
        self.moved |= np.linalg.norm(delta) > 4
        if np.array_equal(position, self.last):
            return None
        self.last = np.asarray(position, float)
        if self.editing is None or not self.moved:
            return None
        indices = (0, 1) if self.editing == 2 else (self.editing,)
        return [(i, self.line[i] + delta) for i in indices]

    def finish(self, position):
        self.move(position)
        click = self.press is not None and self.editing is None and not self.moved
        self.press = None; self.editing = None; self.line = None
        return click


def paint_survey_line(painter, line, anchor=None, pointer=None):
    painter.setPen(QPen(QColor(255, 165, 25), 2))
    painter.setBrush(QColor(45, 45, 48))
    if line is not None:
        a, b = [QPointF(*point) for point in line]
        painter.drawLine(a, b)
        for point in (a, b):
            painter.drawEllipse(point, 6, 6)
        mid = (a + b) / 2
        painter.drawRect(QRectF(mid.x()-5, mid.y()-5, 10, 10))
    elif anchor is not None:
        a = QPointF(*anchor)
        painter.drawEllipse(a, 6, 6)
        if pointer is not None:
            painter.drawLine(a, QPointF(*pointer))
