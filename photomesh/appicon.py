"""Lens2Mesh icon from user-approved L2M drone/terrain artwork.
The internal ICO filename remains stable for existing shortcuts."""
from __future__ import annotations

import os
import struct
import sys

ICO_SIZES = (16, 20, 24, 32, 40, 48, 64, 128, 256)
APP_USER_MODEL_ID = "PhotoMesh.PhotoMeshStudio"
ICO_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources", "photomesh.ico")


def draw(p, n):
    """Draw the approved artwork, shared by splash, window and ICO output."""
    from PySide6.QtCore import QRectF
    from PySide6.QtGui import QImage, QPainter
    artwork = QImage(os.path.join(os.path.dirname(ICO_PATH), "lens2mesh.png"))
    if artwork.isNull():
        raise RuntimeError("Lens2Mesh icon resource is missing or unreadable")
    p.save()
    try:
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        p.drawImage(QRectF(0, 0, n, n), artwork)
    finally:
        p.restore()


def image(n):
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QImage, QPainter
    img = QImage(n, n, QImage.Format_ARGB32_Premultiplied); img.fill(Qt.transparent)
    p = QPainter(img)
    try:
        draw(p, n)
    finally:
        p.end()
    return img


_ICON = None


def app_icon():
    """QIcon with pre-sized entries from the approved high-resolution master."""
    global _ICON
    if _ICON is None:
        from PySide6.QtGui import QIcon, QPixmap
        ic = QIcon()
        for s in ICO_SIZES:
            ic.addPixmap(QPixmap.fromImage(image(s)))
        _ICON = ic
    return _ICON


def png_bytes(n):
    from PySide6.QtCore import QBuffer, QByteArray, QIODevice
    ba = QByteArray(); buf = QBuffer(ba); buf.open(QIODevice.WriteOnly)
    image(n).save(buf, "PNG"); buf.close()
    return bytes(ba.data())


def ico_bytes(sizes=ICO_SIZES):
    """Multi-size Windows .ico with PNG entries (Vista+)."""
    imgs = [(s, png_bytes(s)) for s in sizes]
    out = struct.pack("<HHH", 0, 1, len(imgs))
    off = 6 + 16 * len(imgs)
    data = b""
    for s, b in imgs:
        out += struct.pack("<BBBBHHII", s % 256, s % 256, 0, 0, 1, 32, len(b), off + len(data))
        data += b
    return out + data


def write_ico(path=ICO_PATH):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(ico_bytes())
    return path


def set_app_user_model_id(app_id=APP_USER_MODEL_ID):
    """Windows: own taskbar group + our icon instead of python.exe's. Returns True if set."""
    if sys.platform != "win32":
        return False
    try:
        import ctypes
        return ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(str(app_id)) == 0
    except Exception:  # noqa: BLE001
        return False


def install(app, window=None):
    """Window/taskbar icon on the application (all windows/dialogs) and the main window."""
    ic = app_icon()
    app.setWindowIcon(ic)
    if window is not None:
        window.setWindowIcon(ic)
    return ic
