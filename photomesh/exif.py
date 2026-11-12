"""Strict shared EXIF GPS decoding; malformed numbers never become zero."""
import math


def rational(value):
    try:
        number = float(value) if not isinstance(value, (tuple, list)) else float(value[0]) / float(value[1])
    except (TypeError, ValueError, ZeroDivisionError, OverflowError, IndexError) as exc:
        raise ValueError("Invalid EXIF rational") from exc
    if not math.isfinite(number):
        raise ValueError("EXIF number must be finite")
    return number


def altitude(gps):
    if 6 not in gps:
        return None
    ref = gps.get(5, 0)
    if isinstance(ref, (bytes, bytearray)):
        if len(ref) != 1:
            return None
        ref = ref[0]
    if ref not in (0, 1):
        return None
    try:
        value = rational(gps[6])
        return value * (-1 if ref == 1 else 1) if value >= 0 else None
    except ValueError:
        return None


def coordinates(gps):
    def dms(values, ref, positive, negative, limit):
        if isinstance(ref, bytes):
            ref = ref.decode("ascii")
        if ref not in (positive, negative) or len(values) != 3:
            raise ValueError("Invalid GPS direction or angle")
        d, m, s = map(rational, values)
        if not (0 <= d <= limit and 0 <= m < 60 and 0 <= s < 60):
            raise ValueError("Invalid GPS angle")
        value = d + m / 60 + s / 3600
        if value > limit:
            raise ValueError("GPS angle outside its domain")
        return -value if ref == negative else value
    try:
        lat = dms(gps[2], gps[1], "N", "S", 90)
        lon = dms(gps[4], gps[3], "E", "W", 180)
    except (KeyError, TypeError, ValueError, UnicodeError):
        return None, None, None
    return lon, lat, altitude(gps)


def photo_metadata(image):
    """Read documented DJI XMP fields without inferring a vertical datum.

    Existing valid EXIF positions win. XMP is a fallback position source only;
    reported receiver deviations remain opt-in, not an accuracy guarantee.
    """
    import xml.etree.ElementTree as ET
    try:
        exif = image.getexif()
        position = coordinates(exif.get_ifd(0x8825) if exif else {})
    except (ValueError, TypeError, OSError, KeyError):
        position = (None, None, None)
    info = getattr(image, 'info', {})
    raw = info.get('xmp') or info.get('XML:com.adobe.xmp') or b''
    if isinstance(raw, str):
        raw = raw.encode('utf-8')
    fields = {}
    allowed = {'RtkFlag', 'RtkStdLon', 'RtkStdLat', 'RtkStdHgt', 'AltitudeType',
               'AbsoluteAltitude', 'RelativeAltitude', 'GpsLatitude', 'GpsLongitude', 'SurveyingMode'}
    if isinstance(raw, bytes) and len(raw) <= 1_000_000 and b'<!DOCTYPE' not in raw.upper() and b'<!ENTITY' not in raw.upper():
        try:
            root = ET.fromstring(raw[raw.index(b'<'):])
            for element in root.iter():
                for key, value in [*element.attrib.items(), (element.tag, element.text)]:
                    if key.startswith('{http://www.dji.com/drone-dji/1.0/}'):
                        name = key.split('}', 1)[1]
                        if name in allowed and value is not None:
                            fields[name] = str(value).strip()
        except (ET.ParseError, ValueError):
            pass
    accuracy = None
    source = 'EXIF GPS' if position[0] is not None else 'unavailable'
    try:
        xmp_position = tuple(rational(fields[key]) for key in ('GpsLongitude', 'GpsLatitude', 'AbsoluteAltitude'))
        if abs(xmp_position[0]) > 180 or abs(xmp_position[1]) > 90:
            raise ValueError('Invalid XMP coordinates')
        if position[0] is None:
            position, source = xmp_position, 'DJI XMP'
        consistent = (abs(position[0] - xmp_position[0]) < 1e-5 and
                      abs(position[1] - xmp_position[1]) < 1e-5 and
                      position[2] is not None and abs(position[2] - xmp_position[2]) < 1.)
    except (KeyError, ValueError, TypeError):
        consistent = False
    try:
        values = [rational(fields[key]) for key in ('RtkStdLon', 'RtkStdLat', 'RtkStdHgt')]
        if consistent and fields.get('RtkFlag') in ('16', '34', '50') and fields.get('SurveyingMode') != '0' and all(.0001 <= value <= 10000 for value in values):
            accuracy = values
    except (KeyError, ValueError):
        pass
    if fields.get('RtkFlag') == '0':
        position, accuracy, source = (None, None, None), None, 'DJI positioning unavailable'
    return dict(lon=position[0], lat=position[1], alt=position[2], gps_accuracy=accuracy,
                gps_metadata=dict(source=source, height_reference='unknown', dji=fields))
