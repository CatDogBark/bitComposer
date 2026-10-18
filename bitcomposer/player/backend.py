"""The QObject the player window binds to: engine.Player's state as Qt
properties, its actions as slots. app.py owns the window, tray and dialogs;
this owns nothing visual.
"""
import json
import os
import sys
import threading
from pathlib import Path

from PySide6.QtCore import Property, QObject, QTimer, Qt, Signal, Slot

from .. import __version__
from .engine import Player, VOLUME_MAX, AUTOGEN_MAX, state_file
from . import autostart as startup   # the module; `autostart` below is the Qt property
from . import update as upd


class _Dispatcher(QObject):
    """Runs callables on the thread it lives on (the main one): the engine's
    `schedule`, safe to call from the decode and generation threads."""
    call = Signal(object)

    def __init__(self):
        super().__init__()
        self.call.connect(self._run, Qt.QueuedConnection)

    @Slot(object)
    def _run(self, fn):
        fn()


def _short(path: Path) -> str:
    home = str(Path.home())
    s = str(path)
    return "~" + s[len(home):] if s.startswith(home) else s


class Backend(QObject):
    stateChanged = Signal()
    positionChanged = Signal()
    playlistChanged = Signal()
    channelVolumesChanged = Signal()
    screenChanged = Signal()
    noticeChanged = Signal()
    updateChanged = Signal()
    trayChanged = Signal()
    titleChanged = Signal(str)
    # Asks for app.py: dialogs and quitting live there.
    folderRequested = Signal()
    openFolderRequested = Signal(str)
    updateConfirm = Signal(str)
    quitRequested = Signal()
    raiseRequested = Signal()
    autostartChanged = Signal()
    mediaKeysChanged = Signal()

    def __init__(self, music_dir=None, quiet=False, output_kind=None):
        super().__init__()
        self._dispatch = _Dispatcher()
        self.quiet = quiet
        self.player = Player(music_dir=music_dir, schedule=self._dispatch.call.emit, output_kind=output_kind)
        self.player.on_change = self._changed
        self.player.on_log = self._log
        self._state = {}
        self._position = 0.0
        self._playlist = []
        self._playlist_sig = None
        self._channel_volumes = []
        self._file = None
        self._screen = [0, 0]
        self._notice = ""
        self._release = None
        self._updating = False
        self._tray = False
        self._dirty = False
        self.restart_after_quit = False
        self.mpris = None                 # app.py starts one on Linux
        self._media_keys = ""
        self._tick = QTimer(self)
        self._tick.setInterval(250)
        self._tick.timeout.connect(self._update_position)
        self.player.scan()
        self._refresh()

    # ── engine → window ──
    def _changed(self):
        # The engine reports every step of an action (stop, load, start);
        # one refresh per turn of the event loop is plenty.
        if not self._dirty:
            self._dirty = True
            QTimer.singleShot(0, self._refresh)

    def _log(self, msg: str):
        if not self.quiet:
            print(msg, file=sys.stderr)
        text = msg.split("] ", 1)[1] if msg.startswith("[") and "] " in msg else msg
        if threading.current_thread() is threading.main_thread():
            self._set_notice(text)        # in order with what the caller says next
        else:
            self._dispatch.call.emit(lambda: self._set_notice(text))

    def _set_notice(self, text: str):
        self._notice = text
        self.noticeChanged.emit()

    def _refresh(self):
        self._dirty = False
        p = self.player
        m = p.metadata()
        st = {
            "status": p.status, "shuffle": p.shuffle, "autoGenerate": p.auto_generate,
            "volume": p.volume, "currentIndex": p.current_index, "generating": p._generating,
            "musicDir": str(p.music_dir), "shortDir": _short(p.music_dir),
        }
        if m:
            st.update({
                "title": m["title"], "artist": m["artist"], "format": m["type"], "file": m["file"],
                "channels": m["channels"], "patterns": m["patterns"], "duration": m["duration"],
                # The widget's line: key and tempo, sound and form, the voices.
                "message": "  /  ".join(m["blurb"].split("  /  ")[:3]) if m["blurb"] else "",
                "voices": m["voices"], "drew": m["drew"], "layout": m["layout"], "autogen": m["autogen"],
            })
        old_title = self._state.get("title", "")
        self._state = st
        self.stateChanged.emit()
        if st.get("title", "") != old_title:
            self.titleChanged.emit(st.get("title", ""))

        sig = tuple(p.playlist)
        if sig != self._playlist_sig:
            self._playlist_sig = sig
            self._playlist = [{"file": f, "title": p.track_title(f), "auto": p.is_autogen(f)} for f in p.playlist]
            self.playlistChanged.emit()

        f = m.get("file") if m else None
        if f != self._file:
            self._file = f
            self._channel_volumes = p.channel_volumes()
            self.channelVolumesChanged.emit()
        self._update_position()
        if p.status == "Playing":
            self._tick.start()
        else:
            self._tick.stop()
        if self.mpris:
            self.mpris.update()

    def _update_position(self):
        pos = self.player.position()
        if abs(pos - self._position) > 0.01:
            self._position = pos
            self.positionChanged.emit()

    # ── properties ──
    def _get_state(self): return self._state
    state = Property("QVariantMap", _get_state, notify=stateChanged)

    def _get_position(self): return self._position
    position = Property(float, _get_position, notify=positionChanged)

    def _get_playlist(self): return self._playlist
    playlist = Property("QVariantList", _get_playlist, notify=playlistChanged)

    def _get_channel_volumes(self): return self._channel_volumes
    channelVolumes = Property("QVariantList", _get_channel_volumes, notify=channelVolumesChanged)

    def _get_screen(self): return self._screen
    screenAvail = Property("QVariantList", _get_screen, notify=screenChanged)

    def _get_notice(self): return self._notice
    notice = Property(str, _get_notice, notify=noticeChanged)

    def _get_update_version(self): return self._release["version"] if self._release else ""
    updateVersion = Property(str, _get_update_version, notify=updateChanged)

    def _get_updating(self): return self._updating
    updating = Property(bool, _get_updating, notify=updateChanged)

    def _get_tray(self): return self._tray
    trayAvailable = Property(bool, _get_tray, notify=trayChanged)

    def _get_autostart(self): return startup.is_enabled()
    autostart = Property(bool, _get_autostart, notify=autostartChanged)

    def _get_autostart_supported(self): return startup.supported()
    autostartSupported = Property(bool, _get_autostart_supported, constant=True)

    def _get_check_updates(self): return self.player.check_updates
    checkUpdates = Property(bool, _get_check_updates, notify=updateChanged)

    def _get_media_keys(self): return self._media_keys
    mediaKeys = Property(str, _get_media_keys, notify=mediaKeysChanged)

    def set_media_keys(self, text: str):
        self._media_keys = text
        self.mediaKeysChanged.emit()

    def _get_version(self): return __version__
    version = Property(str, _get_version, constant=True)

    def _get_max_gain(self): return VOLUME_MAX
    maxGain = Property(float, _get_max_gain, constant=True)

    def _get_autogen_max(self): return AUTOGEN_MAX
    autogenMax = Property(int, _get_autogen_max, constant=True)

    # ── for app.py ──
    def set_screen(self, w: int, h: int):
        if [w, h] != self._screen:
            self._screen = [w, h]
            self.screenChanged.emit()

    def screen_size(self):
        return self._screen

    def notify(self, text: str):
        """A line for the window's footer."""
        self._set_notice(text)

    def on_main(self, fn):
        """Run fn on the main thread (from the MPRIS thread, say)."""
        self._dispatch.call.emit(fn)

    def current_path(self) -> str:
        m = self.player.module
        return m.filepath if m is not None else ""

    def set_tray(self, on: bool):
        self._tray = on
        self.trayChanged.emit()

    def load_first(self):
        """Screenshot mode: a track loaded, nothing playing."""
        if self.player.playlist:
            self.player._load(0)
        self._refresh()

    def start(self):
        """After the window is up: the update check, off the main thread,
        unless it is turned off (SET > PLAYER > UPDATES)."""
        if not self.player.check_updates:
            return

        def check():
            rel = upd.newer_release(__version__)
            if rel:
                self._dispatch.call.emit(lambda: self._offer(rel))
        threading.Thread(target=check, daemon=True).start()

    def offer(self, rel):
        """Show UPDATE for this release (the check's, or --try-update's)."""
        self._offer(rel)

    def _offer(self, rel):
        self._release = rel
        self.updateChanged.emit()
        self._set_notice(f"version {rel['version']} is out")

    def start_update(self):
        rel = self._release
        if not rel or self._updating:
            return
        self._updating = True
        self.updateChanged.emit()

        def work():
            quit_now = upd.apply_update(rel, self._log, restart=None)
            self._dispatch.call.emit(lambda: self._update_done(quit_now))
        threading.Thread(target=work, daemon=True).start()

    def _update_done(self, quit_now: bool):
        self._updating = False
        self.updateChanged.emit()
        if quit_now:
            self.restart_after_quit = upd.install_kind() == "pipx"
            self.quitRequested.emit()

    def shutdown(self):
        self._tick.stop()
        if self.mpris:
            self.mpris.stop()
        self.player.shutdown()
        self.player.persist()

    def autoFlags(self) -> str:
        return self.player.auto_generate_settings

    # ── window → engine ──
    @Slot()
    def playPause(self): self.player.play_pause()

    @Slot()
    def stop(self): self.player.stop()

    @Slot()
    def next(self): self.player.next()

    @Slot()
    def previous(self): self.player.previous()

    @Slot()
    def toggleShuffle(self):
        self.player.set_shuffle(not self.player.shuffle)
        self._refresh()

    @Slot(float)
    def setVolume(self, gain):
        self.player.set_volume(gain)
        self._refresh()

    @Slot(int)
    def playIndex(self, idx): self.player.play(idx)

    @Slot(float)
    def seek(self, seconds):
        self.player.seek(seconds)
        self._update_position()
        if self.mpris:
            self.mpris.seeked(self.player.position())

    @Slot(str)
    def generate(self, flags):
        if self.player._generating:
            return
        self._set_notice("composing…")

        def done(path):
            if path:
                self._set_notice(f"composed {Path(path).name}")
            else:
                self._set_notice(self.player.last_error or "generation failed")
        self.player.generate(flags, play=True, on_done=done)
        self._refresh()

    @Slot(bool, str)
    def setAutoGenerate(self, enabled, flags):
        p = self.player
        was_on = p.auto_generate
        p.set_auto_generate(enabled, flags)
        # A real off→on switch with nothing playing starts the radio now
        # (the daemon's rule: settings changes alone never start a track).
        if enabled and not was_on and p.status != "Playing" and not p._generating:
            self._set_notice("composing…")
            p.generate(flags, play=True)
        self._refresh()

    @Slot(str)
    def setAutoFlags(self, flags):
        """Settings changed in the window: they are what AUTO composes next."""
        if flags != self.player.auto_generate_settings:
            self.player.set_auto_generate(self.player.auto_generate, flags)

    @Slot(int, int)
    def setChannelVolume(self, ch, vol): self.player.set_channel_volume(ch, vol)

    @Slot(result=bool)
    def applyMix(self):
        ok = self.player.apply_mix_to_file()
        self._set_notice("mix written into the file" if ok else "could not write the mix")
        if ok:
            self._channel_volumes = self.player.channel_volumes()
        return ok

    @Slot(int)
    def keep(self, idx):
        new = self.player.keep_track(idx)
        self._set_notice(f"kept as {new}" if new else "nothing to keep")

    @Slot()
    def rescan(self): self.player.scan()

    @Slot()
    def openFolder(self):
        self.player.music_dir.mkdir(parents=True, exist_ok=True)
        self.openFolderRequested.emit(str(self.player.music_dir))

    @Slot()
    def chooseFolder(self): self.folderRequested.emit()

    @Slot()
    def applyUpdate(self):
        if self._release and not self._updating:
            self.updateConfirm.emit(self._release["version"])

    @Slot(bool)
    def setCheckUpdates(self, on):
        self.player.check_updates = bool(on)
        self.player.persist()
        if not on and self._release and not self._updating:
            self._release = None              # no UPDATE offer from a check the user turned off
        self._set_notice("checks GitHub for a newer version at start" if on else "never checks for updates")
        self.updateChanged.emit()

    @Slot(bool)
    def setAutostart(self, on):
        err = startup.set_enabled(on)
        self._set_notice(err or ("starts at login, in the tray" if on else "no longer starts at login"))
        self.autostartChanged.emit()

    @Slot()
    def hiddenToTray(self):
        if not getattr(self, "_told_tray", False):
            self._told_tray = True
            self._set_notice("still playing in the tray; quit from its menu")

    # The window's own settings (compose choices, preset, tab, zoom), as the
    # QML hands them over: JSON beside the engine's player.json.
    @Slot(result=str)
    def loadUi(self):
        try:
            return (state_file().parent / "window.json").read_text()
        except OSError:
            return ""

    @Slot(str)
    def saveUi(self, text):
        try:
            p = state_file().parent / "window.json"
            p.parent.mkdir(parents=True, exist_ok=True)
            tmp = p.with_suffix(".tmp")
            tmp.write_text(text)
            os.replace(tmp, p)
        except OSError:
            pass
