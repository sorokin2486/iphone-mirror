"""Windows Job Object: дочерние процессы умирают вместе с приложением (даже при падении)."""
from __future__ import annotations

import ctypes
import logging
import sys
from ctypes import wintypes

log = logging.getLogger(__name__)

JOB_OBJECT_EXTENDED_LIMIT_INFORMATION = 9
JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x2000
PROCESS_SET_QUOTA = 0x0100
PROCESS_TERMINATE = 0x0001


class _IoCounters(ctypes.Structure):
    _fields_ = [(n, ctypes.c_ulonglong) for n in (
        "ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
        "ReadTransferCount", "WriteTransferCount", "OtherTransferCount")]


class _BasicLimits(ctypes.Structure):
    _fields_ = [
        ("PerProcessUserTimeLimit", ctypes.c_int64),
        ("PerJobUserTimeLimit", ctypes.c_int64),
        ("LimitFlags", wintypes.DWORD),
        ("MinimumWorkingSetSize", ctypes.c_size_t),
        ("MaximumWorkingSetSize", ctypes.c_size_t),
        ("ActiveProcessLimit", wintypes.DWORD),
        ("Affinity", ctypes.c_size_t),
        ("PriorityClass", wintypes.DWORD),
        ("SchedulingClass", wintypes.DWORD),
    ]


class _ExtendedLimits(ctypes.Structure):
    _fields_ = [
        ("BasicLimitInformation", _BasicLimits),
        ("IoInfo", _IoCounters),
        ("ProcessMemoryLimit", ctypes.c_size_t),
        ("JobMemoryLimit", ctypes.c_size_t),
        ("PeakProcessMemoryUsed", ctypes.c_size_t),
        ("PeakJobMemoryUsed", ctypes.c_size_t),
    ]


class KillOnCloseJob:
    """Пока объект жив (и жив наш процесс), job открыт; закрылся — дети убиты."""

    def __init__(self) -> None:
        self._handle = None
        if sys.platform != "win32":
            return
        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        k32.CreateJobObjectW.restype = wintypes.HANDLE
        k32.OpenProcess.restype = wintypes.HANDLE
        self._k32 = k32
        handle = k32.CreateJobObjectW(None, None)
        if not handle:
            log.warning("CreateJobObject не удался: %s", ctypes.get_last_error())
            return
        info = _ExtendedLimits()
        info.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        ok = k32.SetInformationJobObject(wintypes.HANDLE(handle), JOB_OBJECT_EXTENDED_LIMIT_INFORMATION,
                                         ctypes.byref(info), ctypes.sizeof(info))
        if not ok:
            log.warning("SetInformationJobObject не удался: %s", ctypes.get_last_error())
            k32.CloseHandle(wintypes.HANDLE(handle))
            return
        self._handle = handle

    def assign(self, pid: int) -> bool:
        if not self._handle or pid <= 0:
            return False
        proc = self._k32.OpenProcess(PROCESS_SET_QUOTA | PROCESS_TERMINATE, False, pid)
        if not proc:
            log.warning("OpenProcess(%s) не удался: %s", pid, ctypes.get_last_error())
            return False
        try:
            ok = bool(self._k32.AssignProcessToJobObject(wintypes.HANDLE(self._handle), wintypes.HANDLE(proc)))
            if not ok:
                log.warning("AssignProcessToJobObject не удался: %s", ctypes.get_last_error())
            return ok
        finally:
            self._k32.CloseHandle(wintypes.HANDLE(proc))
