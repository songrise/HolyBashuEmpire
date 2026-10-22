"""Windows process identity using handles, without CIM service dependencies."""
from contextlib import contextmanager
import ctypes as C
from ctypes import wintypes as W
import os


@contextmanager
def handle(pid, *, terminate=False):
    if os.name != 'nt':
        raise RuntimeError('EU5 process control currently supports Windows only')
    kernel = C.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.argtypes = [W.DWORD, W.BOOL, W.DWORD]
    kernel.OpenProcess.restype = W.HANDLE
    kernel.CloseHandle.argtypes = [W.HANDLE]
    kernel.CloseHandle.restype = W.BOOL
    value = kernel.OpenProcess(0x1000 | (0x0001 if terminate else 0), False, int(pid))
    if not value:
        error = C.get_last_error()
        if error == 87:  # Process has already exited.
            yield None, kernel
            return
        raise C.WinError(error)
    try:
        yield value, kernel
    finally:
        kernel.CloseHandle(value)


def describe(value, kernel, pid):
    if not value:
        return None
    kernel.GetProcessTimes.argtypes = [W.HANDLE] + [C.POINTER(C.c_ulonglong)] * 4
    kernel.GetProcessTimes.restype = W.BOOL
    times = [C.c_ulonglong() for _ in range(4)]
    if not kernel.GetProcessTimes(value, *[C.byref(t) for t in times]):
        raise C.WinError(C.get_last_error())
    kernel.QueryFullProcessImageNameW.argtypes = [W.HANDLE, W.DWORD, W.LPWSTR, C.POINTER(W.DWORD)]
    kernel.QueryFullProcessImageNameW.restype = W.BOOL
    name = C.create_unicode_buffer(32768); size = W.DWORD(len(name))
    if not kernel.QueryFullProcessImageNameW(value, 0, name, C.byref(size)):
        raise C.WinError(C.get_last_error())
    class UnicodeString(C.Structure):
        _fields_ = [('length', W.USHORT), ('capacity', W.USHORT), ('buffer', W.LPVOID)]
    query = C.WinDLL('ntdll').NtQueryInformationProcess
    query.argtypes = [W.HANDLE, W.ULONG, W.LPVOID, W.ULONG, C.POINTER(W.ULONG)]
    query.restype = W.LONG
    needed = W.ULONG()
    query(value, 60, None, 0, C.byref(needed))
    if not C.sizeof(UnicodeString) <= needed.value <= 1024 * 1024:
        raise RuntimeError('Cannot read process command line safely')
    data = C.create_string_buffer(needed.value)
    if query(value, 60, data, len(data), C.byref(needed)) < 0:
        raise RuntimeError('Process command line query failed')
    text = UnicodeString.from_buffer(data)
    start, end = C.addressof(data), C.addressof(data) + len(data)
    if not text.buffer or text.length % 2 or not start <= text.buffer <= text.buffer + text.length <= end:
        raise RuntimeError('Invalid process command line buffer')
    command = C.wstring_at(text.buffer, text.length // 2)
    return dict(pid=int(pid), created=str(times[0].value), executable=name.value, command_line=command)


def identity(pid):
    with handle(pid) as (value, kernel):
        return describe(value, kernel, pid)


def command_arguments(command):
    """Use Windows quoting rules, including quoted user directories with spaces."""
    if os.name != 'nt':
        import shlex
        return shlex.split(command)
    shell = C.WinDLL('shell32', use_last_error=True)
    parse = shell.CommandLineToArgvW
    parse.argtypes = [W.LPCWSTR, C.POINTER(C.c_int)]
    parse.restype = C.POINTER(W.LPWSTR)
    count = C.c_int()
    values = parse(command, C.byref(count))
    if not values:
        raise C.WinError(C.get_last_error())
    kernel = C.WinDLL('kernel32', use_last_error=True)
    kernel.LocalFree.argtypes = [W.HLOCAL]
    kernel.LocalFree.restype = W.HLOCAL
    try:
        return [values[i] for i in range(count.value)]
    finally:
        kernel.LocalFree(values)


def terminate_matching(expected, run, matches, before_stop):
    # A held handle prevents a PID-reuse race between final identity check and termination.
    with handle(expected['pid'], terminate=True) as (value, kernel):
        if not matches(describe(value, kernel, expected['pid']), expected, run):
            raise RuntimeError('Process identity changed; refusing termination')
        before_stop()
        kernel.TerminateProcess.argtypes = [W.HANDLE, W.UINT]
        kernel.TerminateProcess.restype = W.BOOL
        if not kernel.TerminateProcess(value, 1):
            raise C.WinError(C.get_last_error())
