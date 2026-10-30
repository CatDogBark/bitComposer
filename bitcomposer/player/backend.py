"""The QObject the player window binds to: engine.Player's state as Qt
properties, its actions as slots. app.py owns the window, tray and dialogs;
this owns nothing visual.
"""
import json
import os
import shlex
import shutil
import sys
import tempfile
import threading
from pathlib import Path

from PySide6.QtCore import Property, QObject, QTimer, Qt, Signal, Slot

from .. import __version__
from ..packs import library
from ..packs.packfile import PackError
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
    openUrlRequested = Signal(str)
    quitRequested = Signal()
    raiseRequested = Signal()
    autostartChanged = Signal()
    mediaKeysChanged = Signal()
    packsChanged = Signal()
    packImportRequested = Signal()
    packAddRequested = Signal()
    packExportRequested = Signal(str)

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
        # The update screen: "" (closed), "confirm", "running", "failed", "done".
        self._upd_state = ""
        self._upd_log = []
        self._upd_progress = -1.0           # 0..1, or -1 while it cannot be known
        # What the update screen is doing: "" (an update to a newer release)
        # or "emulator" (PACKS' GET THE EMULATOR: this version again, with
        # the import extra), and the release-like record it runs.
        self._purpose = ""
        self._emu_release = None
        self._tray = False
        self._dirty = False
        self.restart_after_quit = False
        self.mpris = None                 # app.py starts one on Linux
        self._media_keys = ""
        self._tick = QTimer(self)
        self._tick.setInterval(250)
        self._tick.timeout.connect(self._update_position)
        # PACKS: the packs on this machine, an import while one runs, an ADD
        # waiting for "replace?", and where voice previews are written.
        self._packs = []
        self._import = None
        self._import_state = {"busy": False, "done": 0, "total": 0, "name": "", "error": ""}
        self._pending_add = ""
        self._pending_name = ""
        self._previews = None
        self._can_import = None
        self._load_packs()
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

    def _get_upd_state(self): return self._upd_state
    updateState = Property(str, _get_upd_state, notify=updateChanged)

    def _get_upd_log(self): return self._upd_log
    updateLog = Property("QVariantList", _get_upd_log, notify=updateChanged)

    def _get_upd_progress(self): return self._upd_progress
    updateProgress = Property(float, _get_upd_progress, notify=updateChanged)

    def _get_upd_kind(self): return upd.install_kind()
    updateKind = Property(str, _get_upd_kind, constant=True)

    def _get_purpose(self): return self._purpose
    updatePurpose = Property(str, _get_purpose, notify=updateChanged)

    def _get_tray(self): return self._tray
    trayAvailable = Property(bool, _get_tray, notify=trayChanged)

    def _get_autostart(self): return startup.is_enabled()
    autostart = Property(bool, _get_autostart, notify=autostartChanged)

    def _get_autostart_supported(self): return startup.supported()
    autostartSupported = Property(bool, _get_autostart_supported, constant=True)

    def _get_check_updates(self): return self.player.check_updates
    checkUpdates = Property(bool, _get_check_updates, notify=updateChanged)

    def _get_prereleases(self): return self.player.prereleases
    prereleases = Property(bool, _get_prereleases, notify=updateChanged)

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

    def _get_packs(self): return self._packs
    packs = Property("QVariantList", _get_packs, notify=packsChanged)

    def _get_import_state(self): return dict(self._import_state, pendingAdd=self._pending_name)
    importState = Property("QVariantMap", _get_import_state, notify=packsChanged)

    def _get_can_import(self):
        if self._can_import is None:
            self._can_import = library.can_import()
        return self._can_import
    canImport = Property(bool, _get_can_import, constant=True)

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

        prereleases = self.player.prereleases

        def check():
            rel = upd.newer_release(__version__, prereleases=prereleases)
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
        rel = self._emu_release if self._purpose == "emulator" else self._release
        if not rel or self._updating:
            return
        self._updating = True
        self._upd_state = "running"
        self._upd_log = []
        self._upd_progress = -1.0
        self.updateChanged.emit()

        def report(text, progress):            # from the update thread
            self._dispatch.call.emit(lambda: self._update_line(text, progress))

        def work():
            try:
                quit_now = upd.apply_update(rel, report, restart=None)
            except Exception as e:               # never leave the screen spinning
                report(f"update failed: {e}", None)
                quit_now = False
            self._dispatch.call.emit(lambda: self._update_done(quit_now))
        threading.Thread(target=work, daemon=True).start()

    def _update_line(self, text: str, progress):
        if not self.quiet:
            print(f"[UPDATE] {text}", file=sys.stderr)
        self._upd_log = (self._upd_log + [text])[-400:]
        if progress is not None:
            self._upd_progress = float(progress)
        self.updateChanged.emit()

    def _update_done(self, quit_now: bool):
        self._updating = False
        self._upd_state = "done" if quit_now else "failed"
        if not quit_now and self._purpose == "emulator":
            self._upd_log = self._upd_log + [
                "the emulator was not installed. Where PyPI has no build of it for this machine, pip tries to "
                "compile it and needs Rust; it can be built from source instead (CONTRIBUTING.md)"]
        self.updateChanged.emit()
        if quit_now:
            self.restart_after_quit = upd.install_kind() == "pipx"
            QTimer.singleShot(1500, self.quitRequested.emit)   # long enough to read "restarting"

    def shutdown(self):
        self._tick.stop()
        if self._import:
            self._import.cancel()
        if self._previews:
            shutil.rmtree(self._previews, ignore_errors=True)
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
        """UPDATE in the header: the update screen, asking first."""
        if self._release and not self._updating:
            self._purpose = ""
            self._upd_state = "confirm"
            self._upd_log = []
            self._upd_progress = -1.0
            self.updateChanged.emit()

    @Slot()
    def confirmUpdate(self):
        if self._upd_state == "confirm":
            self.start_update()

    @Slot()
    def closeUpdate(self):
        if not self._updating:
            self._upd_state = ""
            self._purpose = ""
            self.updateChanged.emit()

    @Slot()
    def openReleasePage(self):
        rel = self._emu_release if self._purpose == "emulator" else self._release
        if rel:
            self.openUrlRequested.emit(rel["page"])

    @Slot()
    def getEmulator(self):
        """PACKS: add the SNES emulator to this pipx install, through the
        update screen: pipx install --force bitcomposer[import] at this very
        version, then a restart. Asked for, never added by an update: where
        no wheel matches, pip would fail the whole update trying to build it."""
        if self._updating or upd.install_kind() != "pipx":
            return
        self._purpose = "emulator"
        self._emu_release = {"version": __version__, "tag": "emulator", "page": upd.BUILD_HELP,
                             "spec": upd.update_spec(__version__, emulator=True)}
        self._upd_state = "confirm"
        self._upd_log = []
        self._upd_progress = -1.0
        self.updateChanged.emit()

    @Slot(bool)
    def setPrereleases(self, on):
        """SET > PLAYER > CANDIDATES: release candidates offered too. Turned
        on, the check runs again now; turned off, a candidate offered to a
        release player is withdrawn (on a candidate, they are its line)."""
        self.player.prereleases = bool(on)
        self.player.persist()
        if on:
            self._set_notice("offers release candidates too")
            self.start()
        else:
            self._set_notice("offers releases only")
            if self._release and not self._updating and upd.is_prerelease(self._release["version"]) \
                    and not upd.is_prerelease(__version__):
                self._release = None
        self.updateChanged.emit()

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

    # ── PACKS ──
    def _load_packs(self):
        try:
            self._packs = library.listing()
        except OSError as e:
            self._packs = []
            self._set_notice(f"cannot read the packs folder: {e}")
        self.packsChanged.emit()

    def _pack_action(self, fn, done: str = ""):
        """Run a library change, report it, and show the packs as they are now."""
        try:
            fn()
        except (PackError, OSError) as e:
            self._set_notice(str(e))
        else:
            if done:
                self._set_notice(done)
        self._load_packs()

    @Slot()
    def importGame(self):
        if self._import is None:
            self.packImportRequested.emit()

    def import_from(self, source: str):
        """Read a game's SPC files into a pack: a folder of them or a zip (from app.py's dialog)."""
        def progress(done, total):
            self._dispatch.call.emit(lambda: self._import_progress(done, total))

        def finished(name, error):
            self._dispatch.call.emit(lambda: self._import_done(name, error))
        try:
            job = library.Import(source, on_progress=progress, on_done=finished)
            job.start()
        except (PackError, OSError) as e:
            self._set_notice(str(e))
            return
        self._import = job
        self._import_state = {"busy": True, "done": 0, "total": 0, "name": job.name, "error": ""}
        self._set_notice(f"importing {Path(source).name}…")
        self.packsChanged.emit()

    def _import_progress(self, done, total):
        self._import_state = dict(self._import_state, done=done, total=total)
        self.packsChanged.emit()

    def _import_done(self, name, error):
        job, self._import = self._import, None
        self._import_state = {"busy": False, "done": 0, "total": 0, "name": "", "error": error or ""}
        if name:
            self._set_notice(f"imported {name}: {job.done} songs read")
        else:
            self._set_notice(f"import stopped: {error}")
        self._load_packs()

    @Slot()
    def cancelImport(self):
        if self._import:
            self._import.cancel()

    @Slot()
    def addPack(self): self.packAddRequested.emit()

    def add_path(self, path: str):
        """ADD from app.py's dialog: an exported pack (.zip) or a pack file.
        A pack of that name here already waits for confirmReplace."""
        try:
            name = library.add(path)
        except library.Exists as e:
            self._pending_add, self._pending_name = path, e.name
            self.packsChanged.emit()
            return
        except (PackError, OSError) as e:
            self._set_notice(str(e))
            return
        self._set_notice(f"added {name}")
        self._load_packs()

    @Slot(bool)
    def confirmReplace(self, yes):
        path, self._pending_add, self._pending_name = self._pending_add, "", ""
        if yes and path:
            self._pack_action(lambda: library.add(path, replace=True), "replaced")
        else:
            self.packsChanged.emit()

    @Slot(str)
    def exportPack(self, name): self.packExportRequested.emit(name)

    def export_to(self, name: str, dest: str):
        self._pack_action(lambda: self._set_notice(f"exported to {_short(library.export(name, dest))}"))

    @Slot(str)
    def deletePack(self, name):
        self._pack_action(lambda: library.delete(name), f"deleted {name}")

    @Slot(str, str)
    def renamePack(self, name, new):
        self._pack_action(lambda: library.rename(name, new.strip().lower()), f"renamed to {new.strip().lower()}")

    @Slot(str, str, str)
    def movePack(self, name, voice, to):
        self._pack_action(lambda: library.move(name, voice, to))

    @Slot(str, str, str)
    def previewVoice(self, name, voice, part):
        """Hear one of a pack's voices: a short phrase in its part's register."""
        try:
            if not self._previews:
                self._previews = tempfile.mkdtemp(prefix="bitcomposer-preview-")
            path = library.preview(name, voice, part, Path(self._previews) / "preview.it")
        except (PackError, OSError, ValueError) as e:
            self._set_notice(f"cannot preview {voice}: {e}")
            return
        self.player.preview(str(path))

    @Slot(str, result=str)
    def packFlags(self, name):
        """What SOUND adds to the settings for one of these packs."""
        return " --pack-file " + shlex.quote(str(library.pack_file(name)))

    @Slot(result=str)
    def vocabularies(self):
        """The vocabularies on this machine for the window's STYLE row beside Classic: JSON [{name, label, songs, ready,
        kind}]; the row offers the ready ones (a fitted vocabulary needs vocabularies.MIN_SONGS songs)."""
        from ..vocabularies import listing
        try:
            return json.dumps(listing())
        except OSError:
            return "[]"

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
