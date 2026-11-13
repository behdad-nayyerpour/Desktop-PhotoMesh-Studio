"""Enable Windows' documented per-process UTF-8 mode on pinned BSD engines.

Only RT_MANIFEST changes. All non-resource PE sections must remain byte-exact.
This is build-time packaging; it never changes Windows' system locale.
"""
import ctypes as c
from ctypes import wintypes as w
import hashlib
from pathlib import Path
import struct
import xml.etree.ElementTree as ET


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def sections(path):
    data=Path(path).read_bytes()
    if data[:2]!=b'MZ': raise ValueError('Not a Windows engine')
    nt=struct.unpack_from('<I',data,60)[0]
    if data[nt:nt+4]!=b'PE\0\0': raise ValueError('Invalid PE header')
    count=struct.unpack_from('<H',data,nt+6)[0]
    optional=nt+24
    if struct.unpack_from('<H',data,optional)[0]!=0x20b: raise ValueError('Expected x64 engine')
    certificate=struct.unpack_from('<II',data,optional+112+4*8)
    if any(certificate): raise ValueError('Refusing to invalidate a signed engine')
    offset=optional+struct.unpack_from('<H',data,nt+20)[0]
    result={}
    for index in range(count):
        header=offset+40*index
        name=data[header:header+8].rstrip(b'\0')
        size,start=struct.unpack_from('<II',data,header+16)
        if start+size>len(data): raise ValueError('Truncated PE section')
        result[name]=hashlib.sha256(data[start:start+size]).hexdigest()
    return result


def patch(path, expected_before):
    path=Path(path).resolve(strict=True)
    if digest(path)!=expected_before: raise ValueError('Engine differs from official reviewed input')
    before=sections(path)
    k=c.WinDLL('kernel32',use_last_error=True)
    k.LoadLibraryExW.argtypes=[w.LPCWSTR,w.HANDLE,w.DWORD];k.LoadLibraryExW.restype=w.HANDLE
    k.FindResourceExW.argtypes=[w.HANDLE,c.c_void_p,c.c_void_p,w.WORD];k.FindResourceExW.restype=w.HANDLE
    k.SizeofResource.argtypes=[w.HANDLE,w.HANDLE];k.SizeofResource.restype=w.DWORD
    k.LoadResource.argtypes=[w.HANDLE,w.HANDLE];k.LoadResource.restype=w.HANDLE
    k.LockResource.argtypes=[w.HANDLE];k.LockResource.restype=c.c_void_p
    k.FreeLibrary.argtypes=[w.HANDLE];k.FreeLibrary.restype=w.BOOL
    handle=k.LoadLibraryExW(str(path),None,2|32)
    if not handle: raise c.WinError(c.get_last_error())
    try:
        resource=k.FindResourceExW(handle,24,1,1033)
        if not resource: raise c.WinError(c.get_last_error())
        pointer=k.LockResource(k.LoadResource(handle,resource))
        if not pointer: raise c.WinError(c.get_last_error())
        original=c.string_at(pointer,k.SizeofResource(handle,resource)).rstrip(b'\0')
    finally:
        k.FreeLibrary(handle)
    tree=ET.fromstring(original)
    ET.register_namespace('','urn:schemas-microsoft-com:asm.v1')
    ET.register_namespace('asmv3','urn:schemas-microsoft-com:asm.v3')
    ET.register_namespace('ws2019','http://schemas.microsoft.com/SMI/2019/WindowsSettings')
    app=ET.SubElement(tree,'{urn:schemas-microsoft-com:asm.v3}application')
    settings=ET.SubElement(app,'{urn:schemas-microsoft-com:asm.v3}windowsSettings')
    ET.SubElement(settings,'{http://schemas.microsoft.com/SMI/2019/WindowsSettings}activeCodePage').text='UTF-8'
    data=ET.tostring(tree,encoding='utf-8',xml_declaration=True)
    k.BeginUpdateResourceW.argtypes=[w.LPCWSTR,w.BOOL];k.BeginUpdateResourceW.restype=w.HANDLE
    k.UpdateResourceW.argtypes=[w.HANDLE,c.c_void_p,c.c_void_p,w.WORD,c.c_void_p,w.DWORD];k.UpdateResourceW.restype=w.BOOL
    k.EndUpdateResourceW.argtypes=[w.HANDLE,w.BOOL];k.EndUpdateResourceW.restype=w.BOOL
    handle=k.BeginUpdateResourceW(str(path),False)
    if not handle: raise c.WinError(c.get_last_error())
    buffer=c.create_string_buffer(data)
    if not k.UpdateResourceW(handle,24,1,1033,buffer,len(data)):
        error=c.get_last_error();k.EndUpdateResourceW(handle,True);raise c.WinError(error)
    if not k.EndUpdateResourceW(handle,False): raise c.WinError(c.get_last_error())
    after=sections(path)
    if set(before)!=set(after) or any(before[name]!=after[name] for name in before if name!=b'.rsrc'):
        raise ValueError('Manifest preparation changed engine code/data sections')
    return dict(before=expected_before,after=digest(path),non_resource_sections_unchanged=True)
