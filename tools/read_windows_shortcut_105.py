"""Read shell-link paths through the explicit Unicode COM interface.

No Resolve, SetPath or Save calls are made while reading installed shortcuts.
The Windows Script Host automation getter can expose lossy ANSI paths.
"""
from contextlib import contextmanager
import ctypes as ct
import json
from pathlib import Path
import sys
import uuid


class GUID(ct.Structure):
    _fields_ = [('bytes', ct.c_ubyte * 16)]

    @classmethod
    def parse(cls, value):
        return cls.from_buffer_copy(uuid.UUID(value).bytes_le)


def call(pointer, index, types, *arguments):
    table = ct.cast(pointer, ct.POINTER(ct.POINTER(ct.c_void_p))).contents
    function = ct.WINFUNCTYPE(ct.c_long, ct.c_void_p, *types)(table[index])
    result = function(pointer, *arguments)
    if result < 0:
        raise OSError(f'COM method {index} failed: 0x{result & 0xffffffff:08x}')
    return result


@contextmanager
def shell_link():
    ole = ct.OleDLL('ole32')
    ole.CoInitializeEx.argtypes = [ct.c_void_p, ct.c_uint32]
    ole.CoCreateInstance.argtypes = [ct.POINTER(GUID), ct.c_void_p, ct.c_uint32,
                                     ct.POINTER(GUID), ct.POINTER(ct.c_void_p)]
    ole.CoUninitialize.argtypes = []
    ole.CoUninitialize.restype = None
    ole.CoInitializeEx(None, 2)
    link, persist = ct.c_void_p(), ct.c_void_p()
    try:
        ole.CoCreateInstance(ct.byref(GUID.parse('00021401-0000-0000-c000-000000000046')),
                             None, 1, ct.byref(GUID.parse('000214f9-0000-0000-c000-000000000046')),
                             ct.byref(link))
        call(link, 0, [ct.POINTER(GUID), ct.POINTER(ct.c_void_p)],
             ct.byref(GUID.parse('0000010b-0000-0000-c000-000000000046')), ct.byref(persist))
        yield link, persist
    finally:
        for pointer in (persist, link):
            if pointer:
                table = ct.cast(pointer, ct.POINTER(ct.POINTER(ct.c_void_p))).contents
                ct.WINFUNCTYPE(ct.c_ulong, ct.c_void_p)(table[2])(pointer)
        ole.CoUninitialize()


def read_shortcut(path):
    with shell_link() as (link, persist):
        call(persist, 5, [ct.c_wchar_p, ct.c_uint32], str(Path(path).resolve()), 0)
        values = {}
        for key, index in [('target', 3), ('working_directory', 8), ('arguments', 10), ('icon', 16)]:
            buffer = ct.create_unicode_buffer(32768)
            types = [ct.POINTER(ct.c_wchar), ct.c_int]
            arguments = [buffer, len(buffer)]
            if key == 'target':
                types += [ct.c_void_p, ct.c_uint32]
                arguments += [None, 4]  # SLGP_RAWPATH; do not resolve/mutate a link.
            elif key == 'icon':
                icon_index = ct.c_int()
                types += [ct.POINTER(ct.c_int)]
                arguments += [ct.byref(icon_index)]
            call(link, index, types, *arguments)
            values[key] = buffer.value
            if key == 'icon':
                values['icon_index'] = icon_index.value
        return values


if __name__ == '__main__':
    print(json.dumps(read_shortcut(sys.argv[1]), ensure_ascii=True))
