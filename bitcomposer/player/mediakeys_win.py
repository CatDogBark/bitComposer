"""The media keys on Windows: play/pause, next, previous and stop as global
hot keys (RegisterHotKey), so they reach the player in the tray or behind
other windows. Linux has MPRIS for this (mpris.py).

The keys come in as WM_HOTKEY thread messages, which Qt's event loop hands
to a native event filter. A key another program has already registered
(some players do) is left to it, and the log says which.
"""
import ctypes
from ctypes import wintypes

from PySide6.QtCore import QAbstractNativeEventFilter

WM_HOTKEY = 0x0312
MOD_NOREPEAT = 0x4000
KEYS = {                     # hot key id: (virtual key, backend slot)
    0xB17: (0xB3, "playPause"),
    0xB18: (0xB0, "next"),
    0xB19: (0xB1, "previous"),
    0xB1A: (0xB2, "stop"),
}


class MediaKeys(QAbstractNativeEventFilter):
    def __init__(self, backend, log=print):
        super().__init__()
        self.b = backend
        self.ids = []
        user32 = ctypes.windll.user32
        for hid, (vk, slot) in KEYS.items():
            if user32.RegisterHotKey(None, hid, MOD_NOREPEAT, vk):
                self.ids.append(hid)
            else:
                log(f"[KEYS] {slot}: taken by another program")

    def nativeEventFilter(self, event_type, message):
        if bytes(event_type) in (b"windows_dispatcher_MSG", b"windows_generic_MSG"):
            msg = wintypes.MSG.from_address(int(message))
            if msg.message == WM_HOTKEY and msg.wParam in self.ids:
                getattr(self.b, KEYS[msg.wParam][1])()
                return True, 0
        return False, 0

    def release(self):
        for hid in self.ids:
            ctypes.windll.user32.UnregisterHotKey(None, hid)
        self.ids = []
