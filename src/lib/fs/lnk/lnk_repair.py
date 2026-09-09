# file: src/lib/fs/lnk/lnk_repair.py

from pathlib import Path

import ctypes
from ctypes import wintypes


ole32 = ctypes.OleDLL("ole32.dll")


IID_IShellLinkW = "{000214F9-0000-0000-C000-000000000046}"
CLSID_ShellLink = "{00021401-0000-0000-C000-000000000046}"
IID_IPersistFile = "{0000010B-0000-0000-C000-000000000046}"


class GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", wintypes.DWORD),
        ("Data2", wintypes.WORD),
        ("Data3", wintypes.WORD),
        ("Data4", ctypes.c_ubyte * 8),
    ]


def guid_from_string(guid_string):
    guid = GUID()

    ctypes.windll.ole32.CLSIDFromString(
        ctypes.c_wchar_p(guid_string),
        ctypes.byref(guid)
    )

    return guid


def query_interface(obj, iid):
    vtable = ctypes.cast(
        obj,
        ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))
    ).contents

    QueryInterface = ctypes.WINFUNCTYPE(
        ctypes.c_long,
        ctypes.c_void_p,
        ctypes.POINTER(GUID),
        ctypes.POINTER(ctypes.c_void_p),
    )(vtable[0])

    result = ctypes.c_void_p()

    hr = QueryInterface(
        obj,
        ctypes.byref(iid),
        ctypes.byref(result)
    )

    if hr != 0:
        raise RuntimeError(f"QueryInterface failed: {hr}")

    return result


def call_method(obj, index, restype, *argtypes):
    vtable = ctypes.cast(
        obj,
        ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))
    ).contents

    return ctypes.WINFUNCTYPE(
        restype,
        ctypes.c_void_p,
        *argtypes
    )(vtable[index])


def get_path(obj):
    buffer = ctypes.create_unicode_buffer(1024)

    GetPath = call_method(
        obj,
        3,
        ctypes.c_long,
        ctypes.c_wchar_p,
        ctypes.c_int,
        ctypes.c_void_p,
        ctypes.c_uint,
    )

    hr = GetPath(
        obj,
        buffer,
        1024,
        None,
        0
    )

    if hr != 0:
        return None

    return buffer.value


def set_path(obj, path):
    SetPath = call_method(
        obj,
        20,
        ctypes.c_long,
        ctypes.c_wchar_p
    )

    hr = SetPath(
        obj,
        str(path)
    )

    if hr != 0:
        raise RuntimeError(f"SetPath failed: {hr}")


def save_link(obj):
    Save = call_method(
        obj,
        6,
        ctypes.c_long,
        ctypes.c_wchar_p,
        ctypes.c_int
    )

    hr = Save(
        obj,
        None,
        True
    )

    if hr != 0:
        raise RuntimeError(f"Save failed: {hr}")

def repair_lnk(lnk_path: Path) -> Path | None:

    ole32.CoInitialize(None)

    try:
        print("Loading:", lnk_path)

        shell_link = ctypes.c_void_p()

        clsid = guid_from_string(CLSID_ShellLink)
        iid = guid_from_string(IID_IShellLinkW)

        hr = ole32.CoCreateInstance(
            ctypes.byref(clsid),
            None,
            1,
            ctypes.byref(iid),
            ctypes.byref(shell_link)
        )

        if hr != 0:
            raise RuntimeError(f"CoCreateInstance failed: {hr}")

        print("Created IShellLink")

        persist_file = query_interface(
            shell_link,
            guid_from_string(IID_IPersistFile)
        )

        print("Got IPersistFile")

        Load = call_method(
            persist_file,
            5,
            ctypes.c_long,
            ctypes.c_wchar_p,
            ctypes.c_uint
        )

        hr = Load(
            persist_file,
            str(lnk_path),
            0
        )

        if hr != 0:
            raise RuntimeError(f"Load failed: {hr}")

        print("Loaded shortcut")

        Resolve = call_method(
            shell_link,
            19,
            ctypes.c_long,
            ctypes.c_void_p,
            ctypes.c_uint
        )

        hr = Resolve(
            shell_link,
            None,
            0
        )

        print("Resolve result:", hr)

        resolved = get_path(shell_link)

        print("Resolved path:", resolved)

        if not resolved:
            return None

        set_path(shell_link, resolved)
        save_link(persist_file)

        print("Shortcut repaired and saved")

        return Path(resolved)
    

    finally:
        ole32.CoUninitialize()


