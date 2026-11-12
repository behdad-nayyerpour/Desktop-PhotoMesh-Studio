"""Render the actual installed splash at supported display scales, offline."""
import os
from pathlib import Path
import sys

sys.path.insert(0, os.environ['PYTHONPATH'])
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont, QFontDatabase
from photomesh import splash, appicon

assert Path(splash.__file__).resolve().is_relative_to(Path(os.environ['PYTHONPATH']).resolve())
assert 'Desktop Photogrammetry App' in Path(splash.__file__).read_text(encoding='utf-8')
app = QApplication([])
for font in ('segoeui.ttf', 'segoeuib.ttf'):
    QFontDatabase.addApplicationFont(str(Path(os.environ['WINDIR']) / 'Fonts' / font))
app.setFont(QFont('Segoe UI', 9))
for dpr in (1, 1.25, 1.5, 2):
    pm = splash._pixmap(dpr)
    assert pm.width() == int(splash.W * dpr)
    assert pm.height() == int(splash.H * dpr)
    assert pm.save(f'verified-download/splash-{dpr}.png')
for size in appicon.ICO_SIZES:
    image = appicon.image(size)
    assert not image.isNull() and image.size().width() == size
assert not appicon.app_icon().isNull()
print('Installed splash and shared window/ICO renderers passed at all sizes')
