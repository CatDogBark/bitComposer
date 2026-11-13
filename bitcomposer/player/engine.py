"""The player engine: a folder of modules, playback through libopenmpt, the
live mixer, auto-generate with prune and KEEP, and the state that survives
a restart. No toolkit and no D-Bus in here: the window (window.py) and the
tray are faces over it.

Lifted from the Plasma widget's D-Bus daemon (2026-10-18; the widget and
the daemon were removed in 1.0.0rc3, the player doing what they did).
Differences from that daemon: generation runs in-process (compose_and_save
in a thread) rather than through the bitcomposer command, since the player
ships with the generator; events reach the face through a scheduler it
provides (a queued Qt signal in the window) instead of GLib directly.
"""
import ctypes
import json
import math
import os
import random
import shlex
import struct
import sys
import threading
import time
from pathlib import Path

from . import level as leveling
from .openmpt import Module, SAMPLE_RATE, LibraryMissing
from .audio import make_output, OutputUnavailable, CHANNELS, LATENCY_MS

EXTENSIONS = {".mod", ".xm", ".it", ".s3m", ".mptm"}
FRAMES_PER_BUFFER = 2048
VOLUME_MAX = 3.0
MEASURE_JOIN = 2.0                 # seconds a shutdown waits for the song being measured in the background
_LIMIT_KNEE = 20000.0
_LIMIT_SPAN = 32767.0 - _LIMIT_KNEE

# Auto-generated tracks are "(auto) <Title>.it": the mark in front, so a file
# browser sorts them together. It marks them for pruning and KEEP strips it.
# Earlier ones were "<Title> (auto).it" and, before that,
# "bitcomposer_auto_<time>.it"; both still count, so they rotate out.
AUTOGEN_PREFIX = "(auto) "
AUTOGEN_LEGACY_SUFFIX = " (auto)"
AUTOGEN_LEGACY_PREFIX = "bitcomposer_auto_"
AUTOGEN_MAX = 10

LEGACY_LAYOUT = ["melody", "harmony", "harmony", "harmony", "bass", "arp",
                 "kick", "snare", "hihat", "tom", "crash", "openhat", "echo.melody", "echo.melody"]


def default_music_dir() -> Path:
    env = os.environ.get("BITCOMPOSER_MUSIC_DIR")
    if env:
        return Path(env).expanduser()
    music = _xdg_music_dir() or Path.home() / "Music"
    return (music if music.is_dir() else Path.home()) / "bitComposer"


def _xdg_music_dir() -> Path | None:
    """The desktop's own Music folder (XDG user dirs: GNOME, Plasma and the
    rest keep it in user-dirs.dirs, translated or moved as the user set it)."""
    if not sys.platform.startswith("linux"):
        return None
    conf = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config") / "user-dirs.dirs"
    try:
        for line in conf.read_text().splitlines():
            if line.startswith("XDG_MUSIC_DIR="):
                value = line.split("=", 1)[1].strip().strip('"').replace("$HOME", str(Path.home()))
                path = Path(value)
                return path if path != Path.home() else None      # unset means $HOME: no Music folder
    except OSError:
        pass
    return None


def state_file() -> Path:
    if sys.platform.startswith("win"):
        base = Path(os.environ.get("APPDATA", Path.home()))
        return base / "bitComposer" / "player.json"
    base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "bitcomposer" / "player.json"


def levels_file() -> Path:
    """The levels measured so far (level.Levels), beside the settings."""
    return state_file().with_name("levels.json")


def _soft_limit(y: float) -> int:
    a = abs(y)
    if a <= _LIMIT_KNEE:
        return int(y)
    lim = _LIMIT_KNEE + _LIMIT_SPAN * math.tanh((a - _LIMIT_KNEE) / _LIMIT_SPAN)
    return int(lim) if y > 0 else -int(lim)


def _apply_gain(raw: bytes, n: int, gain: float) -> bytes:
    samples = struct.unpack(f"<{n}h", raw)
    scaled = [s * gain for s in samples]
    if gain > 1.0 and max(map(abs, scaled)) > _LIMIT_KNEE:
        out = [_soft_limit(y) for y in scaled]
    else:
        out = [max(-32768, min(32767, int(y))) for y in scaled]
    return struct.pack(f"<{n}h", *out)


def parse_message(message: str) -> dict:
    """The machine-readable lines bitcomposer writes into the song message:
    layout (every channel's role), voices (role=name), drew (what the song
    drew), echo. Older files without a layout line get the 14-channel one."""
    out = {"layout": None, "voices": {}, "drew": {}, "echo": "", "lines": []}
    for line in message.replace("\r", "\n").split("\n"):
        line = line.strip()
        if not line:
            continue
        if line.startswith("layout:"):
            out["layout"] = [p.strip() for p in line[7:].split(",") if p.strip()]
        elif line.startswith("voices:"):
            out["voices"] = dict(p.split("=", 1) for p in line[7:].split(",") if "=" in p)
        elif line.startswith("drew:"):
            out["drew"] = dict(p.split("=", 1) for p in line[5:].split(",") if "=" in p)
        elif line.startswith("echo:"):
            out["echo"] = line[5:].strip()
        else:
            out["lines"].append(line)
    return out


def write_channel_volumes(path: str, volumes: list[int]) -> None:
    """Patch an .it file's channel volumes (header bytes 0x80+ch) in place.
    The file keeps its modification time: the playlist is newest first by
    it, and a remix is not a new song."""
    vals = bytes(max(0, min(64, int(v))) for v in volumes[:64])
    st = os.stat(path)
    with open(path, "r+b") as f:
        if f.read(4) != b"IMPM":
            raise ValueError("not an IT module")
        f.seek(0x80)
        f.write(vals)
    os.utime(path, ns=(st.st_atime_ns, st.st_mtime_ns))


class Player:
    """Playlist, transport, mixer, auto-generate. Thread-safe where the
    decode thread meets the face; the face calls everything else from its
    own thread and gives `schedule` so the engine can call back into it."""

    def __init__(self, music_dir: Path | None = None, schedule=None, output_kind: str | None = None):
        self.music_dir = Path(music_dir or default_music_dir())
        self.schedule = schedule or (lambda fn: fn())
        self.output_kind = output_kind
        self.playlist: list[str] = []
        self.shuffle_order: list[int] = []
        self.current_index = -1
        self.shuffle = False
        self.module: Module | None = None
        self.status = "Stopped"
        self.volume = 1.0
        self.width = 1.0               # the stereo width heard: 1.0 the pans as written, less pulled toward centre (WIDTH)
        self.level_on = True           # every song played at one common level (LEVEL; level.py)
        self._level_gain = 1.0         # the loaded song's trim to that level, a gain beside the volume
        self._level_db = None          # and the level it was measured at (None: not measured, or silent)
        self._levels_lock = threading.Lock()
        self._measure_thread = None
        self._measure_stop = threading.Event()
        self.auto_generate = False
        self.auto_generate_settings = ""
        self._generating = False
        self._title_cache: dict[str, tuple[float, str]] = {}
        self._live_mix: dict[int, int] = {}
        self._lock = threading.Lock()
        self._out = None
        self._decode_thread = None
        self._stop_event = threading.Event()
        self._pause_position = 0.0
        self._buf = (ctypes.c_int16 * (FRAMES_PER_BUFFER * CHANNELS))()
        self.on_change = None          # face callback: anything the face shows changed
        self._preview_stop = threading.Event()
        self._preview_resume = False   # a song paused for a preview, to go on after it
        self.on_log = print
        self.last_error = ""
        saved = self._load_state()
        try:
            self.volume = max(0.0, min(VOLUME_MAX, float(saved.get("volume", 1.0))))
        except (TypeError, ValueError):
            pass
        try:
            self.width = max(0.0, min(1.0, float(saved.get("width", 1.0))))
        except (TypeError, ValueError):
            pass
        self.level_on = bool(saved.get("level", True))
        self._levels = leveling.Levels(levels_file())
        self.shuffle = bool(saved.get("shuffle", False))
        self.auto_generate = bool(saved.get("auto_generate", False))
        self.auto_generate_settings = str(saved.get("auto_generate_settings", ""))
        # The one thing the player sends over the network on its own: asking
        # GitHub's releases list for a newer version at start. Off = never.
        self.check_updates = bool(saved.get("check_updates", True))
        # Release candidates offered to a release player too (a tester's
        # choice, off by default); a candidate player always sees them.
        self.prereleases = bool(saved.get("prereleases", False))
        if saved.get("music_dir") and music_dir is None and not os.environ.get("BITCOMPOSER_MUSIC_DIR"):
            self.music_dir = Path(saved["music_dir"])

    # ── state ──
    def _load_state(self) -> dict:
        try:
            with open(state_file()) as fh:
                return json.load(fh)
        except (OSError, ValueError):
            return {}

    def persist(self) -> None:
        try:
            p = state_file()
            p.parent.mkdir(parents=True, exist_ok=True)
            tmp = str(p) + ".tmp"
            with open(tmp, "w") as fh:
                json.dump({"volume": round(self.volume, 3), "width": round(self.width, 3), "level": self.level_on,
                           "shuffle": self.shuffle,
                           "auto_generate": self.auto_generate,
                           "auto_generate_settings": self.auto_generate_settings,
                           "check_updates": self.check_updates,
                           "prereleases": self.prereleases,
                           "music_dir": str(self.music_dir)}, fh)
            os.replace(tmp, p)
        except OSError as e:
            self.on_log(f"[STATE] could not save: {e}")

    def _changed(self) -> None:
        if self.on_change:
            self.schedule(self.on_change)

    # ── playlist ──
    def scan(self) -> None:
        self.music_dir.mkdir(parents=True, exist_ok=True)
        # Newest first, so a song just composed is at the top (by name, a new
        # song landed wherever its title fell, mid-list once the prune ran).
        found = [f for f in self.music_dir.rglob("*") if f.suffix.lower() in EXTENSIONS and f.is_file()]
        found.sort(key=lambda f: (-f.stat().st_mtime, str(f)))
        files = [str(f) for f in found]
        self.playlist = files
        self._rebuild_shuffle()
        if self.module is not None and self.module.filepath in files:
            self.current_index = files.index(self.module.filepath)
        elif self.current_index >= len(files):
            self.current_index = -1
        self._prune_autogen()
        self._measure_ahead()
        self._changed()

    def set_music_dir(self, path: Path) -> None:
        self.stop()
        self._halt_measuring()
        with self._lock:
            if self.module:
                self.module.destroy()
                self.module = None
        self.current_index = -1
        self.music_dir = Path(path)
        self.persist()
        self.scan()

    def _rebuild_shuffle(self) -> None:
        self.shuffle_order = list(range(len(self.playlist)))
        random.shuffle(self.shuffle_order)

    def _step_index(self, direction: int) -> int:
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

    def track_title(self, path: str) -> str:
        try:
            mtime = os.stat(path).st_mtime
        except OSError:
            return Path(path).stem
        hit = self._title_cache.get(path)
        if hit and hit[0] == mtime:
            return hit[1]
        try:
            mod = Module(path)
            title = mod.title
            mod.destroy()
        except (RuntimeError, LibraryMissing):
            title = Path(path).stem
        self._title_cache[path] = (mtime, title)
        return title

    def is_autogen(self, path: str) -> bool:
        stem = Path(path).stem
        return (stem.startswith(AUTOGEN_PREFIX) or stem.endswith(AUTOGEN_LEGACY_SUFFIX)
                or stem.startswith(AUTOGEN_LEGACY_PREFIX))

    def keep_track(self, index: int) -> str:
        if not (0 <= index < len(self.playlist)):
            return ""
        path = self.playlist[index]
        if not self.is_autogen(path):
            return os.path.basename(path)
        stem, ext = os.path.splitext(os.path.basename(path))
        if stem.startswith(AUTOGEN_PREFIX):
            stem = stem[len(AUTOGEN_PREFIX):]
        elif stem.endswith(AUTOGEN_LEGACY_SUFFIX):
            stem = stem[:-len(AUTOGEN_LEGACY_SUFFIX)]
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
            self.on_log(f"[KEEP] {e}")
            return ""
        self.playlist[index] = new_path
        if path in self._title_cache:
            self._title_cache[new_path] = self._title_cache.pop(path)
        with self._levels_lock:
            self._levels.moved(path, new_path)
        with self._lock:
            if self.module and self.module.filepath == path:
                self.module.filepath = new_path
        self._changed()
        return os.path.basename(new_path)

    def _prune_autogen(self) -> None:
        files = sorted((f for f in self.music_dir.rglob("*") if f.is_file() and f.suffix.lower() in EXTENSIONS
                        and self.is_autogen(str(f))), key=lambda f: f.stat().st_mtime)
        playing = self.module.filepath if self.module else None
        removed = False
        while len(files) > AUTOGEN_MAX:
            oldest = files.pop(0)
            if str(oldest) == playing:
                continue
            try:
                oldest.unlink()
                removed = True
                self.on_log(f"[AUTOGEN] pruned {oldest.name}")
            except OSError as e:
                self.on_log(f"[AUTOGEN] prune error: {e}")
        if removed:
            self.playlist = [f for f in self.playlist if Path(f).exists()]
            self._rebuild_shuffle()
            if self.module is not None and self.module.filepath in self.playlist:
                self.current_index = self.playlist.index(self.module.filepath)

    # ── transport ──
    def _load(self, index: int) -> bool:
        if not (0 <= index < len(self.playlist)):
            return False
        path = self.playlist[index]
        try:
            new = Module(path)
        except (RuntimeError, LibraryMissing) as e:
            self.last_error = str(e)
            self.on_log(f"[ERROR] {e}")
            return False
        new.set_stereo_separation(round(self.width * 100))   # the width the listener set, on every module loaded
        level = self.level_of(path) if self.level_on else None
        with self._lock:
            if self.module:
                self.module.destroy()
            self.module = new
            self.current_index = index
            self._live_mix = {}
            self._level_db = level
            self._level_gain = leveling.gain_for(level) if self.level_on else 1.0
        self._changed()
        return True

    def _open_output(self) -> bool:
        try:
            self._out = make_output(SAMPLE_RATE, self.output_kind)
            self._out.open()
            return True
        except OutputUnavailable as e:
            self.last_error = str(e)
            self.on_log(f"[AUDIO] {e}")
            self._out = None
            return False

    def _close_output(self) -> None:
        if self._out:
            self._out.close()
            self._out = None

    def _start_decoder(self) -> None:
        if not self._open_output():
            self.status = "Stopped"
            self._changed()
            return
        self._stop_event.clear()
        self.status = "Playing"
        self._decode_thread = threading.Thread(target=self._decode_loop, daemon=True)
        self._decode_thread.start()
        self._changed()

    def _halt_decoder(self) -> None:
        self._stop_event.set()
        self._close_output()
        if self._decode_thread:
            self._decode_thread.join(timeout=0.5)
            self._decode_thread = None

    def _decode_loop(self) -> None:
        reapply_left = 3
        while not self._stop_event.is_set():
            with self._lock:
                if self.module is None:
                    break
                frames = self.module.read_stereo(FRAMES_PER_BUFFER, self._buf)
                if reapply_left:
                    self._reapply_mix()
                    reapply_left -= 1
            if frames == 0:
                self.schedule(self._on_track_ended)
                break
            raw = bytes(self._buf)[:frames * CHANNELS * 2]
            gain = self.volume * self._level_gain            # the listener's GAIN over the song's trim to the common level
            if gain != 1.0:
                raw = _apply_gain(raw, frames * CHANNELS, gain)
            if not self._out.write(raw):
                if not self._stop_event.is_set():
                    self.schedule(self._on_track_ended)
                break

    def _on_track_ended(self) -> None:
        if self._stop_event.is_set():
            return
        if self.auto_generate and not self._generating:
            self._auto_generate_next()
        else:
            self.next()

    def play(self, index: int | None = None) -> None:
        self.stop()
        if index is not None:
            if not self._load(index):
                return
        elif self.module is None:
            if not self._load(0):
                return
        self._start_decoder()

    def pause(self) -> None:
        if self.status == "Playing":
            with self._lock:
                self._pause_position = self.module.position if self.module else 0.0
            self._halt_decoder()
            self.status = "Paused"
            self._changed()
        elif self.status == "Paused" and self.module:
            with self._lock:
                self.module.seek(self._pause_position)
                self._reapply_mix()
            self._start_decoder()

    def play_pause(self) -> None:
        if self.status == "Playing":
            self.pause()
        elif self.status == "Paused":
            self.pause()
        else:
            self.play()

    def stop(self) -> None:
        self._halt_decoder()
        if self.status != "Stopped":
            self.status = "Stopped"
            self._changed()

    def next(self) -> None:
        if not self.playlist:
            return
        idx = self._step_index(+1)
        was_playing = self.status == "Playing"
        self.stop()
        if self._load(idx) and was_playing:
            self.play()

    def previous(self) -> None:
        if not self.playlist:
            return
        if self.module and self.module.position > 3.0:
            self.seek(0)
            return
        idx = self._step_index(-1)
        was_playing = self.status == "Playing"
        self.stop()
        if self._load(idx) and was_playing:
            self.play()

    def seek(self, seconds: float) -> None:
        was_playing = self.status == "Playing"
        if was_playing:
            self._halt_decoder()
        with self._lock:
            if self.module:
                self.module.seek(max(0.0, seconds))
                self._reapply_mix()
        if was_playing:
            self._start_decoder()
        elif self.status == "Paused":
            self._pause_position = max(0.0, seconds)

    def set_shuffle(self, enabled: bool) -> None:
        self.shuffle = bool(enabled)
        if enabled:
            self._rebuild_shuffle()
        self.persist()

    def set_width(self, width: float) -> None:
        """The stereo width heard at playback, 0 (mono) to 1 (each voice where the song puts it): libopenmpt's stereo
        separation on the playing module and on every module loaded after, saved with the settings. A written song's
        voices sit where its token's game song put them (round 84), by amplitude alone as the SNES pans, which was made
        for a television's speakers; on headphones a lead at 0.25 held all song sits far to one side. The vocabulary keeps
        saying where the game put each voice; this is how the player presents it (HEADPHONES: 0.6)."""
        self.width = max(0.0, min(1.0, float(width)))
        with self._lock:
            if self.module:
                self.module.set_stereo_separation(round(self.width * 100))
        self._changed()

    def set_volume(self, vol: float) -> None:
        self.volume = max(0.0, min(VOLUME_MAX, float(vol)))
        self.persist()

    # ── the common level ──
    def level_of(self, path: str) -> float | None:
        """The song's level in dBFS (level.measure), measured once a file and kept. The measuring is done outside the
        lock, so the song playing, a song just composed and the folder's other songs can be measured side by side."""
        with self._levels_lock:
            known, level = self._levels.cached(path)
        if known:
            return level
        level = leveling.measure(path)
        with self._levels_lock:
            self._levels.put(path, level)
        return level

    def set_level(self, on: bool) -> None:
        """LEVEL: every song played at one common level, or each as it was written. The trim is a gain at playback
        beside the volume, on the playing song at once and on every song loaded after; no file is changed."""
        self.level_on = bool(on)
        path = self.module.filepath if self.module else None
        level = self.level_of(path) if self.level_on and path else None
        with self._lock:
            self._level_db = level
            self._level_gain = leveling.gain_for(level) if self.level_on else 1.0
        self.persist()
        if self.level_on:
            self._measure_ahead()
        self._changed()

    def level_trim(self) -> float | None:
        """The loaded song's trim in dB (under zero: turned down), or None where the level is off or it has none."""
        if not self.level_on or self._level_db is None or self.module is None:
            return None
        return 20.0 * math.log10(self._level_gain)

    def _measure_ahead(self) -> None:
        """The folder's songs not measured yet, measured in the background so that the first play of each does not
        wait for it. One pass at a time; a song it has not reached is measured when it loads."""
        if not self.level_on or (self._measure_thread and self._measure_thread.is_alive()):
            return
        with self._levels_lock:
            todo = [f for f in self.playlist if not self._levels.cached(f)[0]]
        if not todo:
            return
        self._measure_stop.clear()
        self._measure_thread = threading.Thread(target=self._measure_folder, args=(todo, self._measure_stop), daemon=True)
        self._measure_thread.start()

    def _measure_folder(self, paths: list[str], stop: threading.Event) -> None:
        for path in paths:
            if stop.is_set():
                return                         # stopped: whoever stopped it saves, and nothing is written after a shutdown
            self.level_of(path)
        if not stop.is_set():
            with self._levels_lock:
                self._levels.save()

    def _halt_measuring(self) -> None:
        self._measure_stop.set()
        if self._measure_thread:
            self._measure_thread.join(timeout=MEASURE_JOIN)   # a measure still running is left to end; it saves nothing
            self._measure_thread = None
        with self._levels_lock:
            self._levels.save()

    # ── mixer ──
    def _reapply_mix(self) -> None:
        if self.module:
            for ch, vol in self._live_mix.items():
                self.module.set_channel_volume(ch, vol)

    def set_channel_volume(self, ch: int, vol: int) -> bool:
        with self._lock:
            if not self.module:
                return False
            ok = self.module.set_channel_volume(ch, vol)
            if ok:
                self._live_mix[ch] = vol
            return ok

    def channel_volumes(self) -> list[int]:
        with self._lock:
            if not self.module:
                return []
            return [self.module.channel_volume(ch) for ch in range(self.module.num_channels)]

    def levels(self) -> list[float]:
        """Each channel's level in the audio just rendered (about 0 to 1), for
        the window's meters; empty when nothing is playing."""
        with self._lock:
            if not self.module or self.status != "Playing":
                return []
            return [self.module.channel_vu(ch) for ch in range(self.module.num_channels)]

    def apply_mix_to_file(self) -> bool:
        """Write the live mix into the loaded file's header so it survives a reload."""
        with self._lock:
            if not self.module:
                return False
            vols = [self.module.channel_volume(ch) for ch in range(self.module.num_channels)]
            path = self.module.filepath
        try:
            write_channel_volumes(path, vols)
            with self._levels_lock:
                self._levels.forget(path)      # the file keeps its time and its size: a new mix is a new level
            return True
        except (OSError, ValueError) as e:
            self.on_log(f"[MIX] {e}")
            return False

    # ── what is loaded ──
    def metadata(self) -> dict:
        with self._lock:
            if not self.module:
                return {}
            msg = self.module.message
            info = parse_message(msg)
            n = self.module.num_channels
            layout = info["layout"]
            if layout is None:
                layout = LEGACY_LAYOUT[:n] if n == 14 and "bitcomposer" in msg.lower() else [f"ch{i + 1}" for i in range(n)]
            return {"title": self.module.title, "artist": self.module.artist, "type": self.module.type_name,
                    "duration": self.module.duration, "position": self.module.position,
                    "channels": n, "patterns": self.module.num_patterns,
                    "file": os.path.basename(self.module.filepath), "layout": layout,
                    "voices": info["voices"], "drew": info["drew"], "echo": info["echo"],
                    "blurb": "  /  ".join(info["lines"][1:]), "autogen": self.is_autogen(self.module.filepath)}

    def position(self) -> float:
        with self._lock:
            if not self.module:
                return 0.0
            return self._pause_position if self.status == "Paused" else self.module.position

    # ── generation ──
    def generate(self, flags: str = "", play: bool = True, on_done=None) -> None:
        """Compose one song into the music dir (in a thread) and play it."""
        if self._generating:
            return
        self._generating = True
        threading.Thread(target=self._do_generate, args=(flags, play, on_done), daemon=True).start()

    def _auto_generate_next(self) -> None:
        self.generate(self.auto_generate_settings, play=True)

    def _do_generate(self, flags: str, play: bool, on_done) -> None:
        from ..cli import build_parser, compose_from_args   # the CLI's option parsing, in-process
        try:
            args = build_parser().parse_args(shlex.split(flags) + ["-d", str(self.music_dir), "--prefix", AUTOGEN_PREFIX])
            path, _info = compose_from_args(args)
        except SystemExit:
            path = None
            self.last_error = f"bad settings: {flags!r}"
        except Exception as e:                      # keep the player alive on any failure
            path = None
            self.last_error = f"generation failed: {e}"
        if path is None:
            self.on_log(f"[AUTOGEN] {self.last_error}")
        elif self.level_on:
            self.level_of(str(path))           # measured here, in the composing thread, so the song plays without a wait
        self.schedule(lambda: self._generated(path, play, on_done))

    def _generated(self, path, play: bool, on_done) -> None:
        self._generating = False
        if path:
            self.on_log(f"[AUTOGEN] {os.path.basename(path)}")
        self.scan()
        if path and play and (self.auto_generate or on_done is not None):
            for i, f in enumerate(self.playlist):
                if f == str(path):
                    self.stop()
                    if self._load(i):
                        self.play()
                    break
        if on_done:
            on_done(path)
        self._changed()

    def preview(self, path: str) -> None:
        """Play a short module (a pack voice's phrase: packs.library.preview)
        on an output of its own. A song playing pauses for it and goes on
        after; a new preview cuts the one before."""
        self._preview_stop.set()
        resume = self.status == "Playing" or self._preview_resume
        if self.status == "Playing":
            self.pause()
        self._preview_resume = resume
        stop = self._preview_stop = threading.Event()
        threading.Thread(target=self._play_preview, args=(path, stop), daemon=True).start()

    def _play_preview(self, path: str, stop: threading.Event) -> None:
        try:
            module = Module(path)
            module.set_stereo_separation(round(self.width * 100))
        except Exception as e:                      # a preview never takes the player down
            self.on_log(f"[PACKS] cannot play the preview: {e}")
            return
        out = None
        try:
            out = make_output(SAMPLE_RATE, self.output_kind)
            out.open()
            buf = (ctypes.c_int16 * (FRAMES_PER_BUFFER * CHANNELS))()
            while not stop.is_set():
                frames = module.read_stereo(FRAMES_PER_BUFFER, buf)
                if not frames:
                    break
                raw = bytes(buf)[:frames * CHANNELS * 2]
                if self.volume != 1.0:
                    raw = _apply_gain(raw, frames * CHANNELS, self.volume)
                if not out.write(raw):
                    break
            if not stop.is_set():
                time.sleep(LATENCY_MS / 1000 + 0.05)      # what the device still holds
        except OutputUnavailable as e:
            self.on_log(f"[AUDIO] {e}")
        finally:
            if out:
                out.close()
            module.destroy()
        if not stop.is_set() and self._preview_resume:
            self._preview_resume = False
            self.schedule(lambda: self.status == "Paused" and self.pause())   # pause() on a paused song plays it

    def set_auto_generate(self, enabled: bool, flags: str | None = None) -> None:
        self.auto_generate = bool(enabled)
        if flags is not None:
            self.auto_generate_settings = flags
        self.persist()

    def shutdown(self) -> None:
        self.stop()
        self._halt_measuring()
        with self._lock:
            if self.module:
                self.module.destroy()
                self.module = None
