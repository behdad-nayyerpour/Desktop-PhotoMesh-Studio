"""Bottom-docked survey controls, independent of geometry and navigation."""
import numpy as np
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QDockWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QFormLayout, QLabel, QPushButton, QDoubleSpinBox, QProgressBar)


class SurveyPanel(QDockWidget):
    closed = Signal()

    def __init__(self, parent, section, unit):
        super().__init__('Cross Section', parent)
        self.setObjectName('survey-tools')
        self.setAllowedAreas(Qt.BottomDockWidgetArea)
        self.setFeatures(QDockWidget.DockWidgetClosable)
        title = QWidget(); title_layout = QHBoxLayout(title)
        title_layout.setContentsMargins(6, 2, 6, 2)
        title_layout.addWidget(QLabel(self.windowTitle()), 1)
        close = QPushButton('Close'); close.setObjectName('surveyClose')
        close.setMaximumWidth(70); close.clicked.connect(self.close)
        title_layout.addWidget(close); self.setTitleBarWidget(title)
        self.section, self.unit = True, unit
        self.points, self.next_pick = [None, None], 0
        body = QWidget(); self.setWidget(body)
        layout = QHBoxLayout(body)
        controls = QWidget(); left = QVBoxLayout(controls)
        left.setContentsMargins(0, 0, 0, 0)
        self.hint = QLabel('Click start, then end. Drag an end circle or the centre square to edit. Drag elsewhere to rotate / pan; wheel to zoom.')
        self.hint.setWordWrap(True)
        self.hint.setMinimumHeight(self.fontMetrics().lineSpacing() * 3)
        left.addWidget(self.hint)
        self.status = QLabel('Click the start point.'); self.status.setWordWrap(True)
        self.status.setStyleSheet('font-weight: bold;')
        self.status.setMinimumHeight(self.fontMetrics().lineSpacing() * 2)
        left.addWidget(self.status)
        busy_row = QHBoxLayout()
        self.progress = QProgressBar(); self.progress.setRange(0, 0); self.progress.hide()
        self.cancel = QPushButton('Cancel calculation'); self.cancel.hide()
        self.cancel.clicked.connect(parent._survey_cancel)
        busy_row.addWidget(self.progress, 1); busy_row.addWidget(self.cancel)
        left.addLayout(busy_row)
        form = QFormLayout(); self.coordinates = []
        for index, label in enumerate(('Start', 'End')):
            row = QHBoxLayout(); spins = []
            for _ in range(2):
                box = QDoubleSpinBox(); box.setRange(-1e12, 1e12); box.setDecimals(6)
                box.setKeyboardTracking(False)
                box.valueChanged.connect(lambda _value, i=index: parent._survey_coordinates_changed(i))
                row.addWidget(box); spins.append(box)
            form.addRow(f'{label} X / Y ({unit}):', row)
            self.coordinates.append(spins)
        left.addLayout(form)
        self.result = QLabel('Choose the start and end points.'); self.result.setWordWrap(True)
        self.result.setMinimumHeight(self.fontMetrics().lineSpacing() * 3)
        left.addWidget(self.result)
        if self.section:
            note = QLabel('Profile: sampled highest mesh intersection in the vertical section plane; mesh gaps stay empty.')
            note.setWordWrap(True); left.addWidget(note)
        self.reset = QPushButton('New line / clear'); self.reset.clicked.connect(parent._survey_clear)
        left.addWidget(self.reset); left.addStretch()
        layout.addWidget(controls, 1)
        if self.section:
            import pyqtgraph as pg
            self.plot = pg.PlotWidget(); self.plot.setMinimumWidth(280)
            self.plot.setBackground(self.palette().base().color())
            for axis in ('left', 'bottom'):
                self.plot.getAxis(axis).setTextPen(self.palette().text().color())
                self.plot.getAxis(axis).setPen(self.palette().text().color())
            self.plot.setLabel('bottom', 'Distance along section', units=unit)
            self.plot.setLabel('left', 'Elevation / model Z', units=unit)
            self.curve = self.plot.plot(pen=pg.mkPen('#31b6dd', width=2), connect='finite')
            self.selection = self.plot.plot(pen=None, symbol='o', symbolBrush='#ffb33b', symbolSize=9)
            self.plot.scene().sigMouseClicked.connect(parent._survey_profile_clicked)
            layout.addWidget(self.plot, 2)
        self.setMinimumHeight(320)

    def set_busy(self, busy):
        self.progress.setVisible(busy); self.cancel.setVisible(busy)
        self.reset.setEnabled(not busy)
        for row in self.coordinates:
            for control in row:
                control.setEnabled(not busy)

    def set_point(self, index, point):
        self.points[index] = np.asarray(point, float)
        for spin, value in zip(self.coordinates[index], point):
            spin.blockSignals(True); spin.setValue(float(value)); spin.blockSignals(False)
        self.next_pick = 1 - index

    def closeEvent(self, event):
        self.closed.emit()
        super().closeEvent(event)
