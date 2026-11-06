"""Shared EXIF number decoding; no image decoding or heavyweight imports."""
def rational(v):
    try:
        return float(v)
    except Exception:
        try:
            return v[0] / v[1]
        except Exception:
            return 0.0


def altitude(gps):
    """EXIF altitude reference may be an integer or a one-byte value."""
    if 6 not in gps:
        return None
    reference = gps.get(5, 0)
    if isinstance(reference, (bytes, bytearray)):
        reference = reference[0] if reference else 0
    return rational(gps[6]) * (-1 if reference == 1 else 1)
