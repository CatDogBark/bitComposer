#!/usr/bin/env python3
"""
Cyberpunk Chiptune Player Daemon
Plays .mod/.xm/.it/.s3m tracker files via libopenmpt, exposes MPRIS2 over D-Bus.
"""

import ctypes
import json
import math
import os
import random
import shlex
import signal
import struct
import threading
from pathlib import Path

import dbus
import dbus.service
import dbus.mainloop.glib
from gi.repository import GLib, Gio

import subprocess as _subprocess

# ─── Configuration ────────────────────────────────────────────────────────────

MUSIC_DIR = os.path.expanduser("~/Music/Chiptune")
STATE_FILE = os.path.expanduser("~/.config/cyberpunk-chiptune/state.json")
SAMPLE_RATE = 48000

# Volume is a linear gain. 1.0 is unity; anything above it is boost, soft-
# limited so peaks round off instead of clipping. Generated modules peak
# around -6 to -9 dBFS, which is why the player sounded quiet next to
# everything else, so the ceiling leaves room to bring them up to level.
VOLUME_MAX = 3.0
_LIMIT_KNEE = 20000.0   # soft limiting starts here (of 32767)
_LIMIT_SPAN = 32767.0 - _LIMIT_KNEE
CHANNELS = 2
FRAMES_PER_BUFFER = 2048
# Audio queued ahead of the speakers. Without a request PipeWire handed paplay
# a 2.0 s buffer, so seeks and gain changes were heard two seconds late. The
# decoder fills 43 ms per buffer, so 150 ms is comfortable with headroom for
# a brief stall (autogen kicking off, say) without a dropout.
OUTPUT_LATENCY_MS = 150
EXTENSIONS = {".mod", ".xm", ".it", ".s3m", ".mptm"}

# ─── libopenmpt ctypes bindings ───────────────────────────────────────────────

_lib = ctypes.CDLL("libopenmpt.so.0")

# Error handling callback type
_openmpt_log_func = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p)

def _log_silent(user, level, message):
    pass

_silent_log = _openmpt_log_func(_log_silent)

# Module creation — through the extended API, which also hands us the
# "interactive" interface (live per-channel volume, used by the mixer).
_VP = ctypes.c_void_p
_lib.openmpt_module_ext_create_from_memory.restype = _VP
_lib.openmpt_module_ext_create_from_memory.argtypes = [
    _VP, ctypes.c_size_t,              # data, size
    _openmpt_log_func, _VP,            # log callback
    _VP, _VP,                          # error callback (unused)
    _VP, _VP,                          # error, error_message
    _VP,                               # initial ctls
]
_lib.openmpt_module_ext_get_module.restype = _VP
_lib.openmpt_module_ext_get_module.argtypes = [_VP]
_lib.openmpt_module_ext_get_interface.restype = ctypes.c_int
_lib.openmpt_module_ext_get_interface.argtypes = [_VP, ctypes.c_char_p, _VP, ctypes.c_size_t]
_lib.openmpt_module_ext_destroy.restype = None
_lib.openmpt_module_ext_destroy.argtypes = [_VP]


class _Interactive(ctypes.Structure):
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

_lib.openmpt_free_string.restype = None
_lib.openmpt_free_string.argtypes = [ctypes.c_void_p]


class OpenMPTModule:
    """Wrapper around a libopenmpt module."""

    def __init__(self, filepath):
        data = Path(filepath).read_bytes()
        buf = ctypes.create_string_buffer(data)
        self._ext = _lib.openmpt_module_ext_create_from_memory(
            buf, len(data), _silent_log, None, None, None, None, None, None
        )
        if not self._ext:
            self._mod = None
            raise RuntimeError(f"Failed to load: {filepath}")
        self._mod = _lib.openmpt_module_ext_get_module(self._ext)
        self._iface = _Interactive()
        if not _lib.openmpt_module_ext_get_interface(
                self._ext, b"interactive", ctypes.byref(self._iface), ctypes.sizeof(self._iface)):
            self._iface = None
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
        """IT has no artist field. Our own files carry a "bitcomposer <version>"
        line in the song message, so credit them; otherwise fall back to the
        tracker name libopenmpt reports."""
        artist = self.get_metadata("artist")
        if artist:
            return artist
        if "bitcomposer" in self.get_metadata("message").lower():
            return "bitComposer"
        return self.get_metadata("tracker")

    @property
    def type_name(self):
        return self.get_metadata("type")

    @property
    def message(self):
        return self.get_metadata("message")

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

    def channel_volume(self, ch):
        """Channel volume as the file's 0-64 value (libopenmpt reports it as a fraction)."""
        if not self._iface:
            return 64
        return int(round(self._iface.get_channel_volume(self._ext, ch) * 64))

    def set_channel_volume(self, ch, vol):
        """Set a channel's volume (0-64) on the playing module, immediately."""
        if not self._iface or not (0 <= ch < self.num_channels):
            return False
        return self._iface.set_channel_volume(self._ext, ch, max(0, min(64, vol)) / 64.0) == 1

    def destroy(self):
        if getattr(self, "_ext", None):
            _lib.openmpt_module_ext_destroy(self._ext)
            self._ext = None
            self._mod = None

    def __del__(self):
        self.destroy()


# ─── Gain ─────────────────────────────────────────────────────────────────────

def _soft_limit(y: float) -> int:
    """Round off a sample above the knee instead of clipping it."""
    a = abs(y)
    if a <= _LIMIT_KNEE:
        return int(y)
    lim = _LIMIT_KNEE + _LIMIT_SPAN * math.tanh((a - _LIMIT_KNEE) / _LIMIT_SPAN)
    return int(lim) if y > 0 else -int(lim)


def _apply_gain(raw: bytes, n: int, gain: float) -> bytes:
    """Scale n int16 samples by gain. Only touches the limiter when a buffer
    actually exceeds the knee, so unity-ish gains stay cheap."""
    samples = struct.unpack(f"<{n}h", raw)
    scaled = [s * gain for s in samples]
    if gain > 1.0 and max(map(abs, scaled)) > _LIMIT_KNEE:
        out = [_soft_limit(y) for y in scaled]
    else:
        out = [max(-32768, min(32767, int(y))) for y in scaled]
    return struct.pack(f"<{n}h", *out)


def _load_state() -> dict:
    try:
        with open(STATE_FILE) as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def _save_state(state: dict):
    try:
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
        tmp = STATE_FILE + ".tmp"
        with open(tmp, "w") as fh:
            json.dump(state, fh)
        os.replace(tmp, STATE_FILE)
    except OSError as e:
        print(f"[STATE] Could not save: {e}")


# ─── Player Engine ────────────────────────────────────────────────────────────

# Auto-generated tracks are "<Title> (auto).it"; the suffix is what marks them
# for pruning and what KeepTrack strips. Files from before titles existed were
# "bitcomposer_auto_<timestamp>.it" and are still recognised.
AUTOGEN_SUFFIX = " (auto)"
AUTOGEN_LEGACY_PREFIX = "bitcomposer_auto_"
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

        # Volume and shuffle survive restarts; a quiet player that resets to
        # unity on every login is the complaint that added the gain control.
        saved = _load_state()
        try:
            self.volume = max(0.0, min(VOLUME_MAX, float(saved.get("volume", 1.0))))
        except (TypeError, ValueError):
            pass
        self.shuffle = bool(saved.get("shuffle", False))
        self._title_cache = {}   # path -> (mtime, title)
        # Live mixer values for the loaded track, channel -> 0-64. libopenmpt
        # resets channel state on every seek (and resume is a seek), so these
        # are re-applied after each one instead of silently reverting.
        self._live_mix = {}

        self._lock = threading.Lock()
        self._pw_proc = None
        self._decode_thread = None
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._pause_event.set()  # Not paused initially
        self._pause_position = 0.0

        # Audio buffer
        self._buf = (ctypes.c_int16 * (FRAMES_PER_BUFFER * CHANNELS))()

        # Auto-generate state. The flag and its flags string are restored from
        # the state file so "radio mode" survives a reboot; nothing starts
        # playing until asked, generation only triggers when a track ends.
        self.auto_generate = bool(saved.get("auto_generate", False))
        self.auto_generate_settings = str(saved.get("auto_generate_settings", ""))
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
        # Keep pointing at the track that is loaded. Files appearing or
        # disappearing before it in sort order used to shift current_index
        # onto a different file, so the widget highlighted the wrong row and
        # Next skipped or repeated a track.
        if self.module is not None and self.module.filepath in files:
            self.current_index = files.index(self.module.filepath)
        elif self.current_index >= len(files):
            self.current_index = -1
        self._prune_autogen()
        print(f"[SCAN] Found {len(files)} tracks in {MUSIC_DIR}")

    def _rebuild_shuffle(self):
        self.shuffle_order = list(range(len(self.playlist)))
        random.shuffle(self.shuffle_order)

    def _step_index(self, direction):
        """Playlist index of the next (+1) or previous (-1) track.

        current_index is always a real playlist position — the same numbering
        GetPlaylist, PlayIndex and the widget use. Shuffle only changes how
        we step from one to the next: along a shuffled ring of positions
        rather than in list order. Previously the index was a position in the
        shuffled ring, so with shuffle on PlayIndex(n) from the widget played
        a different track from the one clicked and the highlight was wrong.
        """
        n = len(self.playlist)
        if n == 0:
            return -1
        if not self.shuffle:
            return (self.current_index + direction) % n
        if len(self.shuffle_order) != n:
            self._rebuild_shuffle()
        try:
            pos = self.shuffle_order.index(self.current_index)
        except ValueError:
            pos = -1 if direction > 0 else 0
        return self.shuffle_order[(pos + direction) % n]

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
                    f"--latency-msec={OUTPUT_LATENCY_MS}",
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
        """Background thread: decode PCM from module and pipe to paplay."""
        # libopenmpt applies a position change lazily, on the read that
        # follows it, and that resets channel state — so a mix re-applied
        # right after seek() is undone by the first buffer. Re-apply after
        # each of the first few reads instead; it costs microseconds.
        reapply_left = 3
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
                if reapply_left:
                    self._reapply_mix()
                    reapply_left -= 1

            if frames_read == 0:
                # Track ended — advance to next
                GLib.idle_add(self._on_track_ended)
                break

            raw = bytes(self._buf)[:frames_read * CHANNELS * 2]

            # Apply volume
            if self.volume != 1.0:
                raw = _apply_gain(raw, frames_read * CHANNELS, self.volume)

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
        # argv, not a shell string: settings arrive over D-Bus from any client,
        # and the music dir can contain spaces.
        try:
            flags = shlex.split(settings)
        except ValueError as e:
            print(f"[AUTOGEN] Bad settings {settings!r}: {e}")
            flags = []
        # The CLI names the file after the song's title; we only add the
        # (auto) suffix and read the chosen path back from its output.
        cmd = ["python3", "-m", "bitcomposer.cli", *flags,
               "-d", MUSIC_DIR, "--suffix", AUTOGEN_SUFFIX]
        print("[AUTOGEN] Generating...")
        try:
            result = _subprocess.run(cmd, capture_output=True, text=True, timeout=30)
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

        outpath = ""
        for line in result.stdout.splitlines():
            if line.startswith("Generated: "):
                outpath = line[len("Generated: "):].strip()
        if not outpath or not os.path.exists(outpath):
            print(f"[AUTOGEN] Could not find output in: {result.stdout!r}")
            self._generating = False
            GLib.idle_add(self.next)
            return

        print(f"[AUTOGEN] Generated: {os.path.basename(outpath)}")
        # Schedule playlist rescan (which prunes) and play on main thread
        GLib.idle_add(self._autogen_play, outpath)

    def _prune_autogen(self):
        """Delete the oldest auto-generated files beyond AUTOGEN_MAX.

        Runs on every rescan, so this is the single place autogen output is
        pruned; bitcomposer-generate.sh used to prune independently with the
        same cap. The track currently loaded is never removed.
        """
        music = Path(MUSIC_DIR)
        autogen_files = sorted(
            [f for f in music.rglob("*") if f.is_file()
             and f.suffix.lower() in EXTENSIONS and self.is_autogen(str(f))],
            key=lambda f: f.stat().st_mtime
        )
        playing = self.module.filepath if self.module else None
        removed = False
        while len(autogen_files) > AUTOGEN_MAX:
            oldest = autogen_files.pop(0)
            if str(oldest) == playing:
                continue
            print(f"[AUTOGEN] Pruning: {oldest.name}")
            try:
                oldest.unlink()
                removed = True
            except OSError as e:
                print(f"[AUTOGEN] Prune error: {e}")
        if removed:
            self.playlist = [f for f in self.playlist if Path(f).exists()]
            self._rebuild_shuffle()
            if self.module is not None and self.module.filepath in self.playlist:
                self.current_index = self.playlist.index(self.module.filepath)

    def _autogen_play(self, filepath):
        """Main thread callback: rescan, find the new file, play it.

        If auto-generate was switched off while the track was being made,
        keep the file but do not start it — the user just said stop."""
        self.scan_music_dir()
        if self.auto_generate:
            for i, f in enumerate(self.playlist):
                if f == filepath:
                    self.stop_playback()
                    if self._load_track(i):
                        self.play()
                    break
        else:
            print(f"[AUTOGEN] Switched off mid-generation; {os.path.basename(filepath)} kept, not played")
        self._generating = False
        return False

    def _load_track(self, index):
        """Load a track by playlist index."""
        if not self.playlist:
            return False

        if index < 0 or index >= len(self.playlist):
            return False

        filepath = self.playlist[index]
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
            self._live_mix = {}   # a new track starts from its own header mix

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
                    self._reapply_mix()
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
        new_index = self._step_index(+1)
        was_playing = self.status == "Playing"
        self.stop_playback()
        if self._load_track(new_index) and was_playing:
            self.play()

    def previous(self):
        if not self.playlist:
            return
        # If more than 3 seconds in, restart current track
        if self.module and self.module.position > 3.0:
            self.seek_to(0)
            return
        new_index = self._step_index(-1)
        was_playing = self.status == "Playing"
        self.stop_playback()
        if self._load_track(new_index) and was_playing:
            self.play()

    def _persist(self):
        _save_state({
            "volume": round(self.volume, 3),
            "shuffle": self.shuffle,
            "auto_generate": self.auto_generate,
            "auto_generate_settings": self.auto_generate_settings,
        })

    def track_title(self, path):
        """Module title for a playlist entry, cached by mtime. Falls back to the
        filename when the module has none or cannot be opened."""
        try:
            mtime = os.stat(path).st_mtime
        except OSError:
            return Path(path).stem
        hit = self._title_cache.get(path)
        if hit and hit[0] == mtime:
            return hit[1]
        try:
            mod = OpenMPTModule(path)
            title = mod.title
            mod.destroy()
        except RuntimeError:
            title = Path(path).stem
        self._title_cache[path] = (mtime, title)
        return title

    def is_autogen(self, path):
        stem = Path(path).stem
        return stem.endswith(AUTOGEN_SUFFIX) or stem.startswith(AUTOGEN_LEGACY_PREFIX)

    def keep_track(self, index):
        """Rename an auto-generated track so pruning leaves it alone.
        Returns the new basename, or "" if nothing was done."""
        if not (0 <= index < len(self.playlist)):
            return ""
        path = self.playlist[index]
        if not self.is_autogen(path):
            return os.path.basename(path)
        stem, ext = os.path.splitext(os.path.basename(path))
        if stem.endswith(AUTOGEN_SUFFIX):
            stem = stem[:-len(AUTOGEN_SUFFIX)]
        elif stem.startswith(AUTOGEN_LEGACY_PREFIX):
            stem = "bitcomposer_" + stem[len(AUTOGEN_LEGACY_PREFIX):]
        new_path = os.path.join(os.path.dirname(path), stem + ext)
        n = 2
        while os.path.exists(new_path):
            new_path = os.path.join(os.path.dirname(path), f"{stem} {n}{ext}")
            n += 1
        try:
            os.rename(path, new_path)
        except OSError as e:
            print(f"[KEEP] {e}")
            return ""
        self.playlist[index] = new_path
        if path in self._title_cache:
            self._title_cache[new_path] = self._title_cache.pop(path)
        with self._lock:
            if self.module and self.module.filepath == path:
                self.module.filepath = new_path
        print(f"[KEEP] {os.path.basename(path)} -> {os.path.basename(new_path)}")
        return os.path.basename(new_path)

    def set_shuffle(self, enabled):
        self.shuffle = enabled
        if enabled:
            self._rebuild_shuffle()
        self._persist()

    def set_volume(self, vol):
        self.volume = max(0.0, min(VOLUME_MAX, vol))
        self._persist()

    def _halt_decoder(self):
        """Stop the decode thread and drop the audio pipe, discarding whatever
        was queued. Used by pause and seek so the change is heard at once."""
        self._stop_event.set()
        self._close_audio()
        if self._decode_thread:
            self._decode_thread.join(timeout=0.5)
            self._decode_thread = None

    def _start_decoder(self):
        self._open_audio()
        self._stop_event.clear()
        self._pause_event.set()
        self._decode_thread = threading.Thread(target=self._decode_loop, daemon=True)
        self._decode_thread.start()

    def _reapply_mix(self):
        """Restore the live mixer after a seek (call with the lock held)."""
        if self.module:
            for ch, vol in self._live_mix.items():
                self.module.set_channel_volume(ch, vol)

    def set_channel_volume(self, ch, vol):
        with self._lock:
            if not self.module:
                return False
            ok = self.module.set_channel_volume(ch, vol)
            if ok:
                self._live_mix[ch] = vol
            return ok

    def seek_to(self, seconds):
        # Seeking only moved the module's read position; the audio already
        # queued in the pipe still played out first. Flush it like pause does.
        was_playing = self.status == "Playing"
        if was_playing:
            self._halt_decoder()
        with self._lock:
            if self.module:
                self.module.seek(max(0.0, seconds))
                self._reapply_mix()
        if was_playing:
            self._start_decoder()

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
                    "message": self.module.message,
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
        """Return compact state as a parseable string for the plasmoid.

        16 pipe-delimited fields; see docs/INSTALL.md. Free-text fields have
        the delimiter stripped so a module titled "A|B" cannot shift them.
        Field 15 is the module's song message minus its title line, joined
        with " / "; field 16 is the music directory.
        """
        meta = self.player.get_metadata()
        ag = int(self.player.auto_generate)
        vol = f"{self.player.volume:.2f}"
        clean = lambda v: str(v).replace("|", "/").replace("\n", " ")
        if not meta:
            return (f"Stopped|0|0|0||||||{int(self.player.shuffle)}"
                    f"|{len(self.player.playlist)}|{self.player.current_index}|{ag}|{vol}"
                    f"||{clean(MUSIC_DIR)}")
        lines = [ln.strip() for ln in (meta.get("message") or "").splitlines() if ln.strip()]
        if lines and lines[0] == meta["title"]:
            lines = lines[1:]
        blurb = "  /  ".join(clean(ln) for ln in lines[:3])
        return (
            f"{self.player.status}"
            f"|{meta['position']:.1f}"
            f"|{meta['duration']:.1f}"
            f"|{meta['channels']}"
            f"|{clean(meta['title'])}"
            f"|{clean(meta['artist'])}"
            f"|{clean(meta['type'])}"
            f"|{clean(meta['file'])}"
            f"|{meta['patterns']}"
            f"|{int(self.player.shuffle)}"
            f"|{len(self.player.playlist)}"
            f"|{self.player.current_index}"
            f"|{ag}"
            f"|{vol}"
            f"|{blurb}"
            f"|{clean(MUSIC_DIR)}"
        )

    @dbus.service.method(MPRIS_BUS_NAME, out_signature="as")
    def GetPlaylist(self):
        return dbus.Array(self.player.get_playlist_info(), signature="s")

    @dbus.service.method(MPRIS_BUS_NAME, out_signature="as")
    def GetPlaylistInfo(self):
        """One "filename|title|auto" line per track, in GetPlaylist order.
        auto is 1 for bitcomposer_auto_* files, which Rescan may prune."""
        out = []
        for path in self.player.playlist:
            title = self.player.track_title(path).replace("|", "/")
            out.append(f"{os.path.basename(path)}|{title}|{int(self.player.is_autogen(path))}")
        return dbus.Array(out, signature="s")

    @dbus.service.method(MPRIS_BUS_NAME, in_signature="i", out_signature="s")
    def KeepTrack(self, index):
        """Rename an auto-generated track out of the prune set. Returns the new filename."""
        name = self.player.keep_track(int(index))
        self._emit_props_changed()
        return name

    @dbus.service.method(MPRIS_BUS_NAME, in_signature="ii", out_signature="b")
    def SetChannelVolume(self, channel, volume):
        """Live mixer: set one channel's volume (0-64) on the playing module.
        Takes effect on the next buffer; nothing is restarted. Persist it
        with bitcomposer-master.sh, which writes the file header."""
        return bool(self.player.set_channel_volume(int(channel), int(volume)))

    @dbus.service.method(MPRIS_BUS_NAME, out_signature="ai")
    def GetChannelVolumes(self):
        """Current channel volumes (0-64) of the loaded module."""
        with self.player._lock:
            if not self.player.module:
                return dbus.Array([], signature="i")
            n = self.player.module.num_channels
            return dbus.Array([self.player.module.channel_volume(c) for c in range(n)], signature="i")

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
        """Toggle auto-generate mode. settings = CLI flags string.

        Only a real off->on switch while stopped kicks off a generation. The
        widget re-sends this call with the current flags on every settings
        change, and it used to start a fresh track each time — so with the
        player stopped, every chip click began playing something.
        """
        was_on = self.player.auto_generate
        self.player.auto_generate = self._as_bool(enabled)
        self.player.auto_generate_settings = str(settings)
        self.player._persist()
        if self.player.auto_generate != was_on:
            print(f"[AUTOGEN] {'ON' if self.player.auto_generate else 'OFF'} settings: {settings}")
        if (self.player.auto_generate and not was_on
                and self.player.status != "Playing" and not self.player._generating):
            # Nothing is playing, so start the radio now.
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

    @staticmethod
    def _as_bool(value):
        """Coerce a D-Bus variant to bool.

        qdbus6 (which the widget uses) sends "false" as a *string* variant,
        and bool("false") is True — so Shuffle could be switched on but
        never off from the widget.
        """
        if isinstance(value, str):
            return value.strip().lower() in ("1", "true", "yes", "on")
        return bool(value)

    @dbus.service.method(DBUS_PROPS_IFACE, in_signature="ssv")
    def Set(self, interface, prop, value):
        if interface == MPRIS_PLAYER_IFACE:
            if prop == "Shuffle":
                self.player.set_shuffle(self._as_bool(value))
                self._emit_props_changed()
            elif prop == "Volume":
                try:
                    self.player.set_volume(float(value))
                except (TypeError, ValueError):
                    return
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

    # Watch the music dir so files dropped in (or removed) show up without an
    # explicit Rescan. Changes are debounced: a copy of several files, or a
    # file still being written, triggers one rescan a second after it settles.
    pending = {"id": 0}

    def _rescan_later():
        pending["id"] = 0
        player.scan_music_dir()
        mpris._emit_props_changed()
        return False

    def _on_dir_change(monitor, f, other, event):
        if event in (Gio.FileMonitorEvent.CHANGES_DONE_HINT,
                     Gio.FileMonitorEvent.DELETED,
                     Gio.FileMonitorEvent.MOVED_IN,
                     Gio.FileMonitorEvent.MOVED_OUT,
                     Gio.FileMonitorEvent.RENAMED):
            if pending["id"]:
                GLib.source_remove(pending["id"])
            pending["id"] = GLib.timeout_add(1000, _rescan_later)

    try:
        gdir = Gio.File.new_for_path(MUSIC_DIR)
        monitor = gdir.monitor_directory(Gio.FileMonitorFlags.WATCH_MOVES, None)
        monitor.connect("changed", _on_dir_change)
        print(f"[READY] Watching {MUSIC_DIR} for changes")
    except GLib.Error as e:
        monitor = None
        print(f"[WARN] No file monitor ({e}); use Rescan")

    loop = GLib.MainLoop()

    def shutdown(sig, frame):
        print("\n[SHUTDOWN] Cleaning up...")
        player.shutdown()
        loop.quit()

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    print("[READY] Cyberpunk Chiptune Player daemon running")
    print(f"[READY] {len(player.playlist)} tracks loaded from {MUSIC_DIR}")
    print(f"[READY] D-Bus: {MPRIS_BUS_NAME}")

    loop.run()


if __name__ == "__main__":
    main()
