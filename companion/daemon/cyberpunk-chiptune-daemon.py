#!/usr/bin/env python3
"""
Cyberpunk Chiptune Player Daemon
Plays .mod/.xm/.it/.s3m tracker files via libopenmpt, exposes MPRIS2 over D-Bus.
"""

import ctypes
import ctypes.util
import os
import random
import signal
import struct
import sys
import threading
import time
from pathlib import Path

import dbus
import dbus.service
import dbus.mainloop.glib
from gi.repository import GLib

import subprocess as _subprocess

# ─── Configuration ────────────────────────────────────────────────────────────

MUSIC_DIR = os.path.expanduser("~/Music/Chiptune")
SAMPLE_RATE = 48000
CHANNELS = 2
FRAMES_PER_BUFFER = 2048
EXTENSIONS = {".mod", ".xm", ".it", ".s3m", ".mptm"}

# ─── libopenmpt ctypes bindings ───────────────────────────────────────────────

_lib = ctypes.CDLL("libopenmpt.so.0")

# Error handling callback type
_openmpt_log_func = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p)

def _log_silent(user, level, message):
    pass

_silent_log = _openmpt_log_func(_log_silent)

# Module creation
_lib.openmpt_module_create_from_memory2.restype = ctypes.c_void_p
_lib.openmpt_module_create_from_memory2.argtypes = [
    ctypes.c_void_p, ctypes.c_size_t,  # data, size
    _openmpt_log_func, ctypes.c_void_p,  # log callback
    ctypes.c_void_p, ctypes.c_void_p,  # error callback (unused)
    ctypes.c_void_p, ctypes.c_void_p,  # initial ctl
    ctypes.c_void_p,  # error info
]

# Metadata
_lib.openmpt_module_get_metadata.restype = ctypes.c_void_p
_lib.openmpt_module_get_metadata.argtypes = [ctypes.c_void_p, ctypes.c_char_p]

# Duration / position
_lib.openmpt_module_get_duration_seconds.restype = ctypes.c_double
_lib.openmpt_module_get_duration_seconds.argtypes = [ctypes.c_void_p]

_lib.openmpt_module_get_position_seconds.restype = ctypes.c_double
_lib.openmpt_module_get_position_seconds.argtypes = [ctypes.c_void_p]

_lib.openmpt_module_set_position_seconds.restype = ctypes.c_double
_lib.openmpt_module_set_position_seconds.argtypes = [ctypes.c_void_p, ctypes.c_double]

# Channels / patterns info
_lib.openmpt_module_get_num_channels.restype = ctypes.c_int32
_lib.openmpt_module_get_num_channels.argtypes = [ctypes.c_void_p]

_lib.openmpt_module_get_num_patterns.restype = ctypes.c_int32
_lib.openmpt_module_get_num_patterns.argtypes = [ctypes.c_void_p]

# Repeat control
_lib.openmpt_module_set_repeat_count.restype = ctypes.c_int32
_lib.openmpt_module_set_repeat_count.argtypes = [ctypes.c_void_p, ctypes.c_int32]

# Audio rendering
_lib.openmpt_module_read_interleaved_stereo.restype = ctypes.c_size_t
_lib.openmpt_module_read_interleaved_stereo.argtypes = [
    ctypes.c_void_p, ctypes.c_int32, ctypes.c_size_t, ctypes.c_void_p
]

# Cleanup
_lib.openmpt_module_destroy.restype = None
_lib.openmpt_module_destroy.argtypes = [ctypes.c_void_p]

_lib.openmpt_free_string.restype = None
_lib.openmpt_free_string.argtypes = [ctypes.c_void_p]


class OpenMPTModule:
    """Wrapper around a libopenmpt module."""

    def __init__(self, filepath):
        data = Path(filepath).read_bytes()
        buf = ctypes.create_string_buffer(data)
        self._mod = _lib.openmpt_module_create_from_memory2(
            buf, len(data), _silent_log, None, None, None, None, None, None
        )
        if not self._mod:
            raise RuntimeError(f"Failed to load: {filepath}")
        # Don't loop — we'll handle next-track in the player
        _lib.openmpt_module_set_repeat_count(self._mod, 0)
        self.filepath = filepath

    def get_metadata(self, key):
        ptr = _lib.openmpt_module_get_metadata(self._mod, key.encode())
        if ptr:
            result = ctypes.cast(ptr, ctypes.c_char_p).value.decode("utf-8", errors="replace")
            _lib.openmpt_free_string(ptr)
            return result
        return ""

    @property
    def title(self):
        t = self.get_metadata("title")
        if t:
            return t
        # Fall back to filename
        return Path(self.filepath).stem.replace("_", " ")

    @property
    def artist(self):
        return self.get_metadata("artist") or self.get_metadata("tracker")

    @property
    def type_name(self):
        return self.get_metadata("type")

    @property
    def duration(self):
        return _lib.openmpt_module_get_duration_seconds(self._mod)

    @property
    def position(self):
        return _lib.openmpt_module_get_position_seconds(self._mod)

    @property
    def num_channels(self):
        return _lib.openmpt_module_get_num_channels(self._mod)

    @property
    def num_patterns(self):
        return _lib.openmpt_module_get_num_patterns(self._mod)

    def seek(self, seconds):
        _lib.openmpt_module_set_position_seconds(self._mod, ctypes.c_double(seconds))

    def read_stereo(self, frames, buf):
        return _lib.openmpt_module_read_interleaved_stereo(
            self._mod, SAMPLE_RATE, frames, buf
        )

    def destroy(self):
        if self._mod:
            _lib.openmpt_module_destroy(self._mod)
            self._mod = None

    def __del__(self):
        self.destroy()


# ─── Player Engine ────────────────────────────────────────────────────────────

AUTOGEN_PREFIX = "bitcomposer_auto_"
AUTOGEN_MAX = 10


class ChiptunePlayer:
    """Core player: playlist management, audio output, state tracking."""

    def __init__(self):
        self.playlist = []
        self.shuffle_order = []
        self.current_index = -1
        self.shuffle = False
        self.module = None
        self.status = "Stopped"  # "Playing", "Paused", "Stopped"
        self.volume = 1.0

        self._lock = threading.Lock()
        self._pw_proc = None
        self._decode_thread = None
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._pause_event.set()  # Not paused initially
        self._pause_position = 0.0

        # Audio buffer
        self._buf = (ctypes.c_int16 * (FRAMES_PER_BUFFER * CHANNELS))()

        # Auto-generate state
        self.auto_generate = False
        self.auto_generate_settings = ""  # CLI flags string
        self._generating = False

    def scan_music_dir(self):
        """Scan music directory for tracker files."""
        music_path = Path(MUSIC_DIR)
        if not music_path.exists():
            music_path.mkdir(parents=True, exist_ok=True)

        files = sorted([
            str(f) for f in music_path.rglob("*")
            if f.suffix.lower() in EXTENSIONS and f.is_file()
        ])
        self.playlist = files
        self._rebuild_shuffle()
        print(f"[SCAN] Found {len(files)} tracks in {MUSIC_DIR}")

    def _rebuild_shuffle(self):
        self.shuffle_order = list(range(len(self.playlist)))
        random.shuffle(self.shuffle_order)

    def _effective_index(self, idx):
        if self.shuffle and 0 <= idx < len(self.shuffle_order):
            return self.shuffle_order[idx]
        return idx

    def _open_audio(self):
        if self._pw_proc is None or self._pw_proc.poll() is not None:
            if self._pw_proc is not None:
                try:
                    self._pw_proc.stdin.close()
                except Exception:
                    pass
                self._pw_proc = None
            self._pw_proc = _subprocess.Popen(
                [
                    "paplay",
                    "--format=s16le",
                    "--rate=" + str(SAMPLE_RATE),
                    "--channels=" + str(CHANNELS),
                    "--raw",
                    "--stream-name=Cyberpunk Chiptune Player",
                ],
                stdin=_subprocess.PIPE,
                stdout=_subprocess.DEVNULL,
                stderr=_subprocess.DEVNULL,
            )

    def _close_audio(self):
        if self._pw_proc:
            try:
                self._pw_proc.kill()
                self._pw_proc.wait(timeout=0.5)
            except Exception:
                pass
            self._pw_proc = None

    def _decode_loop(self):
        """Background thread: decode PCM from module and pipe to pw-cat."""
        while not self._stop_event.is_set():
            self._pause_event.wait(timeout=0.1)
            if self._stop_event.is_set():
                break
            if not self._pause_event.is_set():
                continue

            with self._lock:
                if self.module is None:
                    break
                frames_read = self.module.read_stereo(FRAMES_PER_BUFFER, self._buf)

            if frames_read == 0:
                # Track ended — advance to next
                GLib.idle_add(self._on_track_ended)
                break

            raw = bytes(self._buf)[:frames_read * CHANNELS * 2]

            # Apply volume
            if self.volume < 1.0:
                samples = struct.unpack(f"<{frames_read * CHANNELS}h", raw)
                raw = struct.pack(
                    f"<{frames_read * CHANNELS}h",
                    *[max(-32768, min(32767, int(s * self.volume))) for s in samples]
                )

            try:
                self._pw_proc.stdin.write(raw)
                self._pw_proc.stdin.flush()
            except (BrokenPipeError, OSError):
                # Only advance track if we weren't told to stop
                if not self._stop_event.is_set():
                    GLib.idle_add(self._on_track_ended)
                break

    def _on_track_ended(self):
        """Called from main loop when a track finishes."""
        if self.auto_generate and not self._generating:
            self._auto_generate_next()
        else:
            self.next()
        return False  # Don't repeat GLib idle callback

    def _auto_generate_next(self):
        """Generate a new track and play it (runs generation in background thread)."""
        self._generating = True
        settings = self.auto_generate_settings
        thread = threading.Thread(target=self._do_generate, args=(settings,), daemon=True)
        thread.start()

    def _do_generate(self, settings):
        """Background thread: run bitcomposer, then schedule playlist update on main loop."""
        import time as _time
        ts = int(_time.time())
        filename = f"{AUTOGEN_PREFIX}{ts}.it"
        outpath = os.path.join(MUSIC_DIR, filename)

        cmd = f"python3 -m bitcomposer.cli {settings} -o {outpath}"
        print(f"[AUTOGEN] Generating: {filename}")
        try:
            result = _subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                print(f"[AUTOGEN] Error: {result.stderr}")
                self._generating = False
                # Fall back to normal next
                GLib.idle_add(self.next)
                return
        except Exception as e:
            print(f"[AUTOGEN] Exception: {e}")
            self._generating = False
            GLib.idle_add(self.next)
            return

        print(f"[AUTOGEN] Generated: {filename}")
        # Prune old autogen files
        self._prune_autogen(outpath)
        # Schedule playlist rescan and play on main thread
        GLib.idle_add(self._autogen_play, outpath)

    def _prune_autogen(self, keep_path):
        """Delete oldest auto-generated files if over the limit."""
        music = Path(MUSIC_DIR)
        autogen_files = sorted(
            [f for f in music.glob(f"{AUTOGEN_PREFIX}*.it") if f.is_file()],
            key=lambda f: f.stat().st_mtime
        )
        # Keep the newest AUTOGEN_MAX (including the one we just made)
        while len(autogen_files) > AUTOGEN_MAX:
            oldest = autogen_files.pop(0)
            if str(oldest) != keep_path:
                print(f"[AUTOGEN] Pruning: {oldest.name}")
                try:
                    oldest.unlink()
                except OSError as e:
                    print(f"[AUTOGEN] Prune error: {e}")

    def _autogen_play(self, filepath):
        """Main thread callback: rescan, find the new file, play it."""
        self.scan_music_dir()
        # Find the new file in playlist
        for i, f in enumerate(self.playlist):
            if f == filepath:
                self.stop_playback()
                if self._load_track(i):
                    self.play()
                break
        self._generating = False
        return False

    def _load_track(self, index):
        """Load a track by playlist index."""
        if not self.playlist:
            return False

        real_idx = self._effective_index(index)
        if real_idx < 0 or real_idx >= len(self.playlist):
            return False

        filepath = self.playlist[real_idx]
        try:
            new_module = OpenMPTModule(filepath)
        except RuntimeError as e:
            print(f"[ERROR] {e}")
            return False

        with self._lock:
            if self.module:
                self.module.destroy()
            self.module = new_module
            self.current_index = index

        print(f"[LOAD] {new_module.title} ({Path(filepath).suffix})")
        return True

    def play(self, index=None):
        """Start playback. If index given, load that track first."""
        self.stop_playback()

        if index is not None:
            if not self._load_track(index):
                return
        elif self.module is None:
            # Load first track
            if not self._load_track(0):
                return

        self._open_audio()
        self._stop_event.clear()
        self._pause_event.set()
        self.status = "Playing"

        self._decode_thread = threading.Thread(target=self._decode_loop, daemon=True)
        self._decode_thread.start()

    def pause(self):
        if self.status == "Playing":
            # Save position, kill audio pipeline for instant silence
            with self._lock:
                self._pause_position = self.module.position if self.module else 0
            self._stop_event.set()
            self._close_audio()
            if self._decode_thread:
                self._decode_thread.join(timeout=0.5)
                self._decode_thread = None
            self.status = "Paused"
        elif self.status == "Paused":
            # Resume from saved position
            if self.module:
                with self._lock:
                    self.module.seek(self._pause_position)
                self._open_audio()
                self._stop_event.clear()
                self._pause_event.set()
                self._decode_thread = threading.Thread(target=self._decode_loop, daemon=True)
                self._decode_thread.start()
            self.status = "Playing"

    def stop_playback(self):
        self._stop_event.set()
        self._pause_event.set()
        self._close_audio()  # Kill paplay first so decode thread's write breaks immediately
        if self._decode_thread:
            self._decode_thread.join(timeout=0.5)
            self._decode_thread = None
        if self.status != "Stopped":
            self.status = "Stopped"

    def next(self):
        if not self.playlist:
            return
        new_index = (self.current_index + 1) % len(self.playlist)
        was_playing = self.status == "Playing"
        self.stop_playback()
        if self._load_track(new_index) and was_playing:
            self.play()

    def previous(self):
        if not self.playlist:
            return
        # If more than 3 seconds in, restart current track
        if self.module and self.module.position > 3.0:
            self.module.seek(0)
            return
        new_index = (self.current_index - 1) % len(self.playlist)
        was_playing = self.status == "Playing"
        self.stop_playback()
        if self._load_track(new_index) and was_playing:
            self.play()

    def set_shuffle(self, enabled):
        self.shuffle = enabled
        if enabled:
            self._rebuild_shuffle()

    def set_volume(self, vol):
        self.volume = max(0.0, min(1.0, vol))

    def seek_to(self, seconds):
        with self._lock:
            if self.module:
                self.module.seek(seconds)

    def get_metadata(self):
        with self._lock:
            if self.module:
                return {
                    "title": self.module.title,
                    "artist": self.module.artist,
                    "type": self.module.type_name,
                    "duration": self.module.duration,
                    "position": self.module.position,
                    "channels": self.module.num_channels,
                    "patterns": self.module.num_patterns,
                    "file": os.path.basename(self.module.filepath),
                }
        return {}

    def get_playlist_info(self):
        return [os.path.basename(f) for f in self.playlist]

    def shutdown(self):
        self.stop_playback()
        with self._lock:
            if self.module:
                self.module.destroy()
                self.module = None


# ─── MPRIS2 D-Bus Service ────────────────────────────────────────────────────

MPRIS_BUS_NAME = "org.mpris.MediaPlayer2.CyberpunkChiptune"
MPRIS_OBJECT_PATH = "/org/mpris/MediaPlayer2"
MPRIS_IFACE = "org.mpris.MediaPlayer2"
MPRIS_PLAYER_IFACE = "org.mpris.MediaPlayer2.Player"
DBUS_PROPS_IFACE = "org.freedesktop.DBus.Properties"


class MPRISService(dbus.service.Object):
    """MPRIS2 D-Bus interface for the chiptune player."""

    def __init__(self, player, bus):
        self.player = player
        self._bus = bus
        bus_name = dbus.service.BusName(MPRIS_BUS_NAME, bus)
        super().__init__(bus_name, MPRIS_OBJECT_PATH)
        self._props_changed_timer = None

    def _emit_props_changed(self):
        """Emit PropertiesChanged signal for player state."""
        props = {
            "PlaybackStatus": self.player.status,
            "Metadata": self._get_metadata_dict(),
            "Shuffle": self.player.shuffle,
            "Volume": self.player.volume,
        }
        self.PropertiesChanged(MPRIS_PLAYER_IFACE, props, [])

    def _get_metadata_dict(self):
        meta = self.player.get_metadata()
        d = dbus.Dictionary({}, signature="sv")
        if meta:
            track_id = f"/org/cyberpunk/chiptune/track/{self.player.current_index}"
            d["mpris:trackid"] = dbus.ObjectPath(track_id)
            d["mpris:length"] = dbus.Int64(int(meta["duration"] * 1_000_000))
            d["xesam:title"] = meta["title"]
            d["xesam:artist"] = dbus.Array([meta["artist"] or "Unknown"], signature="s")
            d["xesam:album"] = meta.get("type", "Chiptune")
            d["cyberpunk:channels"] = dbus.Int32(meta.get("channels", 0))
            d["cyberpunk:patterns"] = dbus.Int32(meta.get("patterns", 0))
            d["cyberpunk:file"] = meta.get("file", "")
            d["cyberpunk:format"] = meta.get("type", "")
        return d

    # ── org.mpris.MediaPlayer2 ──

    @dbus.service.method(MPRIS_IFACE)
    def Raise(self):
        pass

    @dbus.service.method(MPRIS_IFACE)
    def Quit(self):
        self.player.shutdown()
        loop.quit()

    # ── org.mpris.MediaPlayer2.Player ──

    @dbus.service.method(MPRIS_PLAYER_IFACE)
    def Play(self):
        if self.player.status == "Paused":
            self.player.pause()  # Toggle back to playing
        elif self.player.status == "Stopped":
            self.player.play()
        self._emit_props_changed()

    @dbus.service.method(MPRIS_PLAYER_IFACE)
    def Pause(self):
        if self.player.status == "Playing":
            self.player.pause()
            self._emit_props_changed()

    @dbus.service.method(MPRIS_PLAYER_IFACE)
    def PlayPause(self):
        if self.player.status == "Playing":
            self.player.pause()
        elif self.player.status == "Paused":
            self.player.pause()  # Toggle
        else:
            self.player.play()
        self._emit_props_changed()

    @dbus.service.method(MPRIS_PLAYER_IFACE)
    def Stop(self):
        self.player.stop_playback()
        self._emit_props_changed()

    @dbus.service.method(MPRIS_PLAYER_IFACE)
    def Next(self):
        self.player.next()
        self._emit_props_changed()

    @dbus.service.method(MPRIS_PLAYER_IFACE)
    def Previous(self):
        self.player.previous()
        self._emit_props_changed()

    @dbus.service.method(MPRIS_PLAYER_IFACE, in_signature="x")
    def Seek(self, offset_usec):
        offset_sec = offset_usec / 1_000_000
        meta = self.player.get_metadata()
        if meta:
            new_pos = meta["position"] + offset_sec
            self.player.seek_to(max(0, new_pos))

    @dbus.service.method(MPRIS_PLAYER_IFACE, in_signature="ox")
    def SetPosition(self, track_id, position_usec):
        self.player.seek_to(position_usec / 1_000_000)

    # ── Custom methods ──

    @dbus.service.method(MPRIS_BUS_NAME, out_signature="s")
    def GetState(self):
        """Return compact state as a parseable string for the plasmoid."""
        meta = self.player.get_metadata()
        ag = int(self.player.auto_generate)
        if not meta:
            return f"Stopped|0|0|0||||||{int(self.player.shuffle)}|{len(self.player.playlist)}|{self.player.current_index}|{ag}"
        return (
            f"{self.player.status}"
            f"|{meta['position']:.1f}"
            f"|{meta['duration']:.1f}"
            f"|{meta['channels']}"
            f"|{meta['title']}"
            f"|{meta['artist']}"
            f"|{meta['type']}"
            f"|{meta['file']}"
            f"|{meta['patterns']}"
            f"|{int(self.player.shuffle)}"
            f"|{len(self.player.playlist)}"
            f"|{self.player.current_index}"
            f"|{ag}"
        )

    @dbus.service.method(MPRIS_BUS_NAME, out_signature="as")
    def GetPlaylist(self):
        return dbus.Array(self.player.get_playlist_info(), signature="s")

    @dbus.service.method(MPRIS_BUS_NAME, in_signature="i")
    def PlayIndex(self, index):
        self.player.stop_playback()
        if self.player._load_track(index):
            self.player.play()
        self._emit_props_changed()

    @dbus.service.method(MPRIS_BUS_NAME)
    def Rescan(self):
        self.player.scan_music_dir()
        self._emit_props_changed()

    @dbus.service.method(MPRIS_BUS_NAME, in_signature="bs")
    def SetAutoGenerate(self, enabled, settings):
        """Toggle auto-generate mode. settings = CLI flags string."""
        self.player.auto_generate = bool(enabled)
        self.player.auto_generate_settings = str(settings)
        print(f"[AUTOGEN] {'ON' if enabled else 'OFF'} settings: {settings}")
        if enabled and self.player.status != "Playing":
            # Kick off the first generation immediately
            self.player._auto_generate_next()
        self._emit_props_changed()

    # ── Properties ──

    @dbus.service.method(DBUS_PROPS_IFACE, in_signature="ss", out_signature="v")
    def Get(self, interface, prop):
        return self.GetAll(interface).get(prop, "")

    @dbus.service.method(DBUS_PROPS_IFACE, in_signature="s", out_signature="a{sv}")
    def GetAll(self, interface):
        if interface == MPRIS_IFACE:
            return {
                "CanQuit": True,
                "CanRaise": False,
                "HasTrackList": False,
                "Identity": "Cyberpunk Chiptune Player",
                "DesktopEntry": "cyberpunk-chiptune",
                "SupportedUriSchemes": dbus.Array([], signature="s"),
                "SupportedMimeTypes": dbus.Array([], signature="s"),
            }
        elif interface == MPRIS_PLAYER_IFACE:
            return {
                "PlaybackStatus": self.player.status,
                "LoopStatus": "Playlist",
                "Rate": 1.0,
                "Shuffle": self.player.shuffle,
                "Metadata": self._get_metadata_dict(),
                "Volume": self.player.volume,
                "Position": dbus.Int64(
                    int(self.player.get_metadata().get("position", 0) * 1_000_000)
                ),
                "MinimumRate": 1.0,
                "MaximumRate": 1.0,
                "CanGoNext": len(self.player.playlist) > 1,
                "CanGoPrevious": len(self.player.playlist) > 1,
                "CanPlay": len(self.player.playlist) > 0,
                "CanPause": True,
                "CanSeek": True,
                "CanControl": True,
            }
        return {}

    @dbus.service.method(DBUS_PROPS_IFACE, in_signature="ssv")
    def Set(self, interface, prop, value):
        if interface == MPRIS_PLAYER_IFACE:
            if prop == "Shuffle":
                self.player.set_shuffle(bool(value))
                self._emit_props_changed()
            elif prop == "Volume":
                self.player.set_volume(float(value))
                self._emit_props_changed()

    @dbus.service.signal(DBUS_PROPS_IFACE, signature="sa{sv}as")
    def PropertiesChanged(self, interface, changed, invalidated):
        pass


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    global loop

    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    bus = dbus.SessionBus()

    player = ChiptunePlayer()
    player.scan_music_dir()

    mpris = MPRISService(player, bus)

    loop = GLib.MainLoop()

    def shutdown(sig, frame):
        print("\n[SHUTDOWN] Cleaning up...")
        player.shutdown()
        loop.quit()

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    print(f"[READY] Cyberpunk Chiptune Player daemon running")
    print(f"[READY] {len(player.playlist)} tracks loaded from {MUSIC_DIR}")
    print(f"[READY] D-Bus: {MPRIS_BUS_NAME}")

    loop.run()


if __name__ == "__main__":
    main()
