"""libopenmpt through ctypes: the player's module loader, with the
interactive interface for the live mixer.

The library is found per platform: libopenmpt.so.0 on Linux (apt
libopenmpt0), libopenmpt.dll next to this file or next to the executable on
Windows (the release build bundles it), libopenmpt.dylib on macOS.
"""
import ctypes
import os
import sys
from pathlib import Path

SAMPLE_RATE = 48000


def _find_library():
    if sys.platform.startswith("win"):
        here = Path(__file__).resolve().parent
        exe = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
        for base in (here, exe, exe / "player", Path.cwd()):
            dll = base / "libopenmpt.dll"
            if dll.exists():
                return str(dll)
        return "libopenmpt.dll"
    if sys.platform == "darwin":
        return "libopenmpt.dylib"
    return "libopenmpt.so.0"


class LibraryMissing(RuntimeError):
    pass


_lib = None


def lib():
    """The loaded library, or LibraryMissing with the install hint."""
    global _lib
    if _lib is None:
        name = _find_library()
        try:
            _lib = ctypes.CDLL(name)
        except OSError as e:
            if sys.platform.startswith("win"):
                hint = "libopenmpt.dll is missing: it ships with the release zip and installer"
            elif sys.platform == "darwin":
                hint = "install libopenmpt: brew install libopenmpt"
            else:
                hint = "install libopenmpt: apt install libopenmpt0 (Debian/Ubuntu) or dnf install libopenmpt"
            raise LibraryMissing(f"{hint} ({e})") from e
        _bind(_lib)
    return _lib


_VP = ctypes.c_void_p
_LOG_FUNC = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p)


def _log_silent(user, level, message):
    pass


_silent_log = _LOG_FUNC(_log_silent)


class Interactive(ctypes.Structure):
    """openmpt_module_ext_interface_interactive, field order as in libopenmpt_ext.h."""
    _fields_ = [
        ("set_current_speed", ctypes.CFUNCTYPE(ctypes.c_int, _VP, ctypes.c_int32)),
        ("set_current_tempo", ctypes.CFUNCTYPE(ctypes.c_int, _VP, ctypes.c_int32)),
        ("set_tempo_factor", ctypes.CFUNCTYPE(ctypes.c_int, _VP, ctypes.c_double)),
        ("get_tempo_factor", ctypes.CFUNCTYPE(ctypes.c_double, _VP)),
        ("set_pitch_factor", ctypes.CFUNCTYPE(ctypes.c_int, _VP, ctypes.c_double)),
        ("get_pitch_factor", ctypes.CFUNCTYPE(ctypes.c_double, _VP)),
        ("set_global_volume", ctypes.CFUNCTYPE(ctypes.c_int, _VP, ctypes.c_double)),
        ("get_global_volume", ctypes.CFUNCTYPE(ctypes.c_double, _VP)),
        ("set_channel_volume", ctypes.CFUNCTYPE(ctypes.c_int, _VP, ctypes.c_int32, ctypes.c_double)),
        ("get_channel_volume", ctypes.CFUNCTYPE(ctypes.c_double, _VP, ctypes.c_int32)),
        ("set_channel_mute_status", ctypes.CFUNCTYPE(ctypes.c_int, _VP, ctypes.c_int32, ctypes.c_int)),
        ("get_channel_mute_status", ctypes.CFUNCTYPE(ctypes.c_int, _VP, ctypes.c_int32)),
        ("set_instrument_mute_status", ctypes.CFUNCTYPE(ctypes.c_int, _VP, ctypes.c_int32, ctypes.c_int)),
        ("get_instrument_mute_status", ctypes.CFUNCTYPE(ctypes.c_int, _VP, ctypes.c_int32)),
        ("play_note", ctypes.CFUNCTYPE(ctypes.c_int32, _VP, ctypes.c_int32, ctypes.c_int32, ctypes.c_double, ctypes.c_double)),
        ("stop_note", ctypes.CFUNCTYPE(ctypes.c_int, _VP, ctypes.c_int32)),
    ]


def _bind(L):
    L.openmpt_module_ext_create_from_memory.restype = _VP
    L.openmpt_module_ext_create_from_memory.argtypes = [_VP, ctypes.c_size_t, _LOG_FUNC, _VP, _VP, _VP, _VP, _VP, _VP]
    L.openmpt_module_ext_get_module.restype = _VP
    L.openmpt_module_ext_get_module.argtypes = [_VP]
    L.openmpt_module_ext_get_interface.restype = ctypes.c_int
    L.openmpt_module_ext_get_interface.argtypes = [_VP, ctypes.c_char_p, _VP, ctypes.c_size_t]
    L.openmpt_module_ext_destroy.restype = None
    L.openmpt_module_ext_destroy.argtypes = [_VP]
    L.openmpt_module_get_metadata.restype = _VP
    L.openmpt_module_get_metadata.argtypes = [_VP, ctypes.c_char_p]
    L.openmpt_module_get_duration_seconds.restype = ctypes.c_double
    L.openmpt_module_get_duration_seconds.argtypes = [_VP]
    L.openmpt_module_get_position_seconds.restype = ctypes.c_double
    L.openmpt_module_get_position_seconds.argtypes = [_VP]
    L.openmpt_module_set_position_seconds.restype = ctypes.c_double
    L.openmpt_module_set_position_seconds.argtypes = [_VP, ctypes.c_double]
    L.openmpt_module_get_num_channels.restype = ctypes.c_int32
    L.openmpt_module_get_num_channels.argtypes = [_VP]
    L.openmpt_module_get_num_patterns.restype = ctypes.c_int32
    L.openmpt_module_get_num_patterns.argtypes = [_VP]
    L.openmpt_module_set_repeat_count.restype = ctypes.c_int32
    L.openmpt_module_set_repeat_count.argtypes = [_VP, ctypes.c_int32]
    L.openmpt_module_read_interleaved_stereo.restype = ctypes.c_size_t
    L.openmpt_module_read_interleaved_stereo.argtypes = [_VP, ctypes.c_int32, ctypes.c_size_t, _VP]
    L.openmpt_free_string.restype = None
    L.openmpt_free_string.argtypes = [_VP]


class Module:
    """One loaded module, with live per-channel volume."""

    def __init__(self, filepath: str):
        L = lib()
        data = Path(filepath).read_bytes()
        self._buf = ctypes.create_string_buffer(data)
        self._ext = L.openmpt_module_ext_create_from_memory(self._buf, len(data), _silent_log, None, None, None, None, None, None)
        if not self._ext:
            self._mod = None
            raise RuntimeError(f"not a module libopenmpt can read: {filepath}")
        self._mod = L.openmpt_module_ext_get_module(self._ext)
        self._iface = Interactive()
        if not L.openmpt_module_ext_get_interface(self._ext, b"interactive", ctypes.byref(self._iface), ctypes.sizeof(self._iface)):
            self._iface = None
        L.openmpt_module_set_repeat_count(self._mod, 0)
        self.filepath = filepath

    def get_metadata(self, key: str) -> str:
        L = lib()
        ptr = L.openmpt_module_get_metadata(self._mod, key.encode())
        if ptr:
            out = ctypes.cast(ptr, ctypes.c_char_p).value.decode("utf-8", errors="replace")
            L.openmpt_free_string(ptr)
            return out
        return ""

    @property
    def title(self) -> str:
        return self.get_metadata("title") or Path(self.filepath).stem.replace("_", " ")

    @property
    def artist(self) -> str:
        artist = self.get_metadata("artist")
        if artist:
            return artist
        if "bitcomposer" in self.get_metadata("message").lower():
            return "bitComposer"
        return self.get_metadata("tracker")

    @property
    def type_name(self) -> str:
        return self.get_metadata("type")

    @property
    def message(self) -> str:
        return self.get_metadata("message")

    @property
    def duration(self) -> float:
        return lib().openmpt_module_get_duration_seconds(self._mod)

    @property
    def position(self) -> float:
        return lib().openmpt_module_get_position_seconds(self._mod)

    @property
    def num_channels(self) -> int:
        return lib().openmpt_module_get_num_channels(self._mod)

    @property
    def num_patterns(self) -> int:
        return lib().openmpt_module_get_num_patterns(self._mod)

    def seek(self, seconds: float) -> None:
        lib().openmpt_module_set_position_seconds(self._mod, ctypes.c_double(max(0.0, seconds)))

    def read_stereo(self, frames: int, buf, rate: int = SAMPLE_RATE) -> int:
        return lib().openmpt_module_read_interleaved_stereo(self._mod, rate, frames, buf)

    def channel_volume(self, ch: int) -> int:
        """The channel's volume as the file's 0-64 value."""
        if not self._iface:
            return 64
        return int(round(self._iface.get_channel_volume(self._ext, ch) * 64))

    def set_channel_volume(self, ch: int, vol: int) -> bool:
        if not self._iface or not (0 <= ch < self.num_channels):
            return False
        return self._iface.set_channel_volume(self._ext, ch, max(0, min(64, vol)) / 64.0) == 1

    def destroy(self) -> None:
        if getattr(self, "_ext", None):
            lib().openmpt_module_ext_destroy(self._ext)
            self._ext = None
            self._mod = None

    def __del__(self):
        try:
            self.destroy()
        except Exception:
            pass
