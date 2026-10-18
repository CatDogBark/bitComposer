"""The player's Qt face: engine.Player behind a QObject the QML window
(qml/Main.qml) binds to, plus the tray icon, single-instance handling and
the offscreen screenshot mode.

Threads: the engine calls back from its decode and generation threads
through `schedule`, which here posts the callable to the Qt main thread.
Everything the window shows is pushed from the main thread as properties.

Screenshot mode (`bitcomposer-player --screenshot out.png --screen
1920x1080 --scale 1.5`) renders the window offscreen as it would open on
that screen, with a few freshly composed songs loaded and nothing played,
so the layout can be checked at sizes and scalings nobody here owns.
"""
import os
import sys
import tempfile
from pathlib import Path

from .. import __version__
from . import update as upd

HERE = Path(__file__).resolve().parent
APP_ID = "CatDogBark.bitComposer"
# Logical pixels a taskbar or panel takes from a screen's height: what the
# screenshot mode subtracts, since an offscreen screen has none.
TASKBAR = 48


def run(music_dir=None, screenshot=None, screen=None, scale=None, panels="", minimized=False, try_update=None) -> int:
    if screenshot:
        # Before Qt loads: no real display, a fixed scale, the software
        # renderer (no GPU in CI), and a config dir of its own so nothing
        # here touches the real player's state.
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        os.environ["QT_QUICK_BACKEND"] = "software"
        os.environ["QT_SCALE_FACTOR"] = str(scale or 1)
        os.environ.pop("QT_SCREEN_SCALE_FACTORS", None)
        os.environ.pop("QT_ENABLE_HIGHDPI_SCALING", None)
        tmp = tempfile.mkdtemp(prefix="bitcomposer-shot-")
        os.environ["XDG_CONFIG_HOME"] = os.environ["APPDATA"] = tmp
        os.environ["BITCOMPOSER_MUSIC_DIR"] = music_dir or os.path.join(tmp, "music")
        music_dir = os.environ["BITCOMPOSER_MUSIC_DIR"]

    from PySide6.QtCore import QUrl
    from PySide6.QtGui import QAction, QDesktopServices, QFontDatabase, QIcon
    from PySide6.QtNetwork import QLocalServer, QLocalSocket
    from PySide6.QtQml import QQmlApplicationEngine
    from PySide6.QtQuick import QQuickWindow  # noqa: F401  (so the root object comes back as one, with grabWindow)
    from PySide6.QtWidgets import QApplication, QFileDialog, QMenu, QMessageBox, QSystemTrayIcon

    from .backend import Backend

    if sys.platform.startswith("win"):
        try:   # the taskbar groups and badges by this, and shows our icon rather than Python's
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
        except Exception:
            pass

    app = QApplication(sys.argv[:1])
    app.setApplicationName("bitComposer")
    app.setOrganizationName("bitComposer")
    app.setApplicationVersion(__version__)
    app.setDesktopFileName("bitcomposer-player")
    icon = QIcon(str(HERE / "icons" / "bitcomposer.svg"))
    app.setWindowIcon(icon)
    for f in sorted((HERE / "fonts").glob("*.ttf")):
        QFontDatabase.addApplicationFont(str(f))

    # The app-menu entry first, before a second launch hands off to the
    # running player and quits: a launch from a terminal while an older
    # player runs must still put the entry (back) in the menu.
    entry_state = ""
    if not screenshot:
        from .desktop import announce_icons, ensure_entry
        try:
            entry_state = ensure_entry()    # first launch of an installed copy: into the app menu
        except OSError as e:
            print(f"bitcomposer-player: could not write the app-menu entry: {e}", file=sys.stderr)
        if entry_state:
            announce_icons()

    # One player at a time: a second launch shows the first one's window.
    # "One" per settings folder, so a run with its own XDG_CONFIG_HOME (a
    # test, a second profile) never hands off to the everyday player.
    server = None
    if not screenshot:
        import zlib
        from .engine import state_file
        user = os.environ.get("USER") or os.environ.get("USERNAME") or "user"
        name = f"bitcomposer-player-{user}-{zlib.crc32(str(state_file().parent).encode()):08x}"
        probe = QLocalSocket()
        probe.connectToServer(name)
        if probe.waitForConnected(300):
            # The desktop's activation token, when it launched us (Wayland:
            # XDG_ACTIVATION_TOKEN), goes along: GNOME brings a window forward
            # only with one, and says "is ready" in a notification otherwise.
            token = os.environ.get("XDG_ACTIVATION_TOKEN", "")
            probe.write(f"show {token}\n".encode())
            probe.flush()
            probe.waitForBytesWritten(300)
            probe.disconnectFromServer()
            return 0
        QLocalServer.removeServer(name)      # a stale socket from a crash
        server = QLocalServer()
        server.listen(name)

    if screenshot:
        _compose_demo(Path(music_dir))

    backend = Backend(music_dir=music_dir, quiet=bool(screenshot))
    if entry_state == "added":
        backend.notify("bitComposer is in your app menu now")

    # The media keys: MPRIS on Linux (the desktop routes the keys, the media
    # applet and the lock screen to it), global hot keys on Windows.
    media_keys = None
    if not screenshot:
        if sys.platform.startswith("linux"):
            from .mpris import Mpris
            m = Mpris(backend)
            if m.start():
                backend.mpris = m
                backend.set_media_keys("through the desktop's media controls (MPRIS)")
        elif sys.platform.startswith("win"):
            try:
                from .mediakeys_win import MediaKeys
                media_keys = MediaKeys(backend, log=backend.notify)
                app.installNativeEventFilter(media_keys)
                app.aboutToQuit.connect(media_keys.release)
                backend.set_media_keys(f"{len(media_keys.ids)} of 4 keys" if media_keys.ids else "taken by another program")
            except Exception as e:
                print(f"bitcomposer-player: media keys unavailable: {e}", file=sys.stderr)
    if screenshot:
        sw, sh = screen
        s = float(scale or 1)
        backend.set_screen(round(sw / s), round(sh / s) - TASKBAR)

    if not screenshot:
        # The window's starting height is the screen's; the primary one
        # until the window says where it is (follow_screen below).
        g = app.primaryScreen().availableGeometry()
        backend.set_screen(g.width(), g.height())
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("backend", backend)
    open_panels = {p.strip() for p in (panels or "").split(",") if p.strip()}
    # Started at login (--minimized): no window. With a tray (if one comes up
    # in time) it sits there; with none (GNOME without the AppIndicator
    # extension) it runs in the background, the media keys and the desktop's
    # media controls reaching it, and opening it from the app menu shows the
    # window (a second launch hands off). A minimized window was tried for
    # the no-tray case: GNOME answers a window that maps minimized with an
    # "is ready" notification, at every login.
    if minimized and not screenshot:
        _wait_for_tray(app)
    engine.setInitialProperties({"startSettings": "settings" in open_panels or "set" in open_panels,
                                 "startMaster": "mix" in open_panels, "still": bool(screenshot),
                                 "startHidden": bool(minimized and not screenshot)})
    engine.load(QUrl.fromLocalFile(str(HERE / "qml" / "Main.qml")))
    if not engine.rootObjects():
        print("bitcomposer-player: the window failed to load (see the QML errors above)", file=sys.stderr)
        return 1
    window = engine.rootObjects()[0]

    if screenshot:
        code = _grab(app, window, backend, screenshot)
        del window, engine         # the window goes before the backend it binds to
        return code

    # Follow the screen the window is on, for the fit-to-screen height.
    watched = set()

    def follow_screen(*_):
        scr = window.screen()
        if scr is None:
            return
        g = scr.availableGeometry()
        backend.set_screen(g.width(), g.height())
        if scr.name() not in watched:
            watched.add(scr.name())
            scr.availableGeometryChanged.connect(follow_screen)
    window.screenChanged.connect(follow_screen)
    follow_screen()

    def show_window(token: str = ""):
        if token:
            os.environ["XDG_ACTIVATION_TOKEN"] = token     # Qt's Wayland activation uses it once
        window.show()
        window.raise_()
        window.requestActivate()
    backend.raiseRequested.connect(show_window)

    if server is not None:
        def on_connection():
            sock = server.nextPendingConnection()
            if sock is not None:
                def got():
                    words = bytes(sock.readAll()).decode(errors="replace").split()
                    show_window(words[1] if len(words) > 1 and words[0] == "show" else "")
                sock.readyRead.connect(got)
                sock.disconnected.connect(sock.deleteLater)
        server.newConnection.connect(on_connection)

    # Tray: closing the window leaves the music playing, as the widget did.
    tray = None
    if QSystemTrayIcon.isSystemTrayAvailable():
        tray = QSystemTrayIcon(icon)
        tray.setToolTip("bitComposer")
        menu = QMenu()
        act_play = QAction("Play / Pause", menu); act_play.triggered.connect(backend.playPause)
        act_next = QAction("Next", menu); act_next.triggered.connect(backend.next)
        act_gen = QAction("Generate new track", menu); act_gen.triggered.connect(lambda: backend.generate(backend.autoFlags()))
        act_show = QAction("Show window", menu); act_show.triggered.connect(show_window)
        act_login = QAction("Start at login", menu)
        act_login.setCheckable(True)
        act_login.setChecked(backend.autostart)
        act_login.setEnabled(backend.autostartSupported)
        act_login.toggled.connect(lambda on: on != backend.autostart and backend.setAutostart(on))
        backend.autostartChanged.connect(lambda: act_login.setChecked(backend.autostart))
        act_quit = QAction("Quit", menu); act_quit.triggered.connect(app.quit)
        for a in (act_show, None, act_play, act_next, act_gen, None, act_login, None, act_quit):
            menu.addSeparator() if a is None else menu.addAction(a)
        tray.setContextMenu(menu)

        def on_tray(reason):
            if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
                if window.isVisible() and window.isActive():
                    window.hide()
                else:
                    show_window()
            elif reason == QSystemTrayIcon.ActivationReason.MiddleClick:
                backend.playPause()
        tray.activated.connect(on_tray)
        backend.titleChanged.connect(lambda t: tray.setToolTip(f"bitComposer\n{t}" if t else "bitComposer"))
        tray.show()
        backend.set_tray(True)
        app.setQuitOnLastWindowClosed(False)

    # Python-side dialogs the QML asks for.
    def choose_folder():
        chosen = QFileDialog.getExistingDirectory(None, "Music folder", str(backend.player.music_dir))
        if chosen:
            backend.player.set_music_dir(Path(chosen))
    backend.folderRequested.connect(choose_folder)
    backend.openFolderRequested.connect(lambda p: QDesktopServices.openUrl(QUrl.fromLocalFile(p)))

    def confirm_update(version):
        ans = QMessageBox.question(None, "bitComposer",
                                   f"Update to {version}?\n\nThe player restarts (or the installer runs) when it is done.")
        if ans == QMessageBox.StandardButton.Yes:
            backend.start_update()
    backend.updateConfirm.connect(confirm_update)
    backend.quitRequested.connect(app.quit)

    if try_update:
        if upd.install_kind() == "frozen":
            backend.offer(upd.local_release(try_update, __version__))
        else:
            backend.notify("--try-update is for the installed Windows build")
    app.aboutToQuit.connect(backend.shutdown)
    # Ctrl+C in a terminal and a SIGTERM quit cleanly (state saved, audio
    # closed). Python only sees a signal when it runs, so a slow timer
    # hands it the thread now and then.
    import signal
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: app.quit())
    from PySide6.QtCore import QTimer
    wake = QTimer()
    wake.timeout.connect(lambda: None)
    wake.start(500)
    backend.start()
    code = app.exec()
    del window, engine             # the window goes before the backend it binds to
    if backend.restart_after_quit:
        upd.restart_self()
    return code


def _wait_for_tray(app, seconds: float = 20.0) -> bool:
    """At login the panel holding the tray may come up after us: wait for
    it a little, so a --minimized start does not open the window just
    because it was early. False if no tray turned up (the window opens
    minimized). GNOME's tray, where there is one, is an extension loaded
    with the shell, which is up before login programs start, so it is
    asked for only briefly there."""
    import time
    from PySide6.QtWidgets import QSystemTrayIcon
    if "GNOME" in os.environ.get("XDG_CURRENT_DESKTOP", "").upper():
        seconds = min(seconds, 3.0)
    end = time.monotonic() + seconds
    while not QSystemTrayIcon.isSystemTrayAvailable():
        if time.monotonic() > end:
            return False
        app.processEvents()
        time.sleep(0.25)
    return True


def _compose_demo(music: Path) -> None:
    """A few songs for the screenshot: seeded, so every run shows the same."""
    from ..cli import build_parser, compose_from_args
    music.mkdir(parents=True, exist_ok=True)
    for i, extra in enumerate((["--sound", "ffvi"], ["--sound", "megamanx"], ["--sound", "mana"], ["--sound", "evermore"])):
        suffix = [] if i % 2 else ["--prefix", "(auto) "]
        args = build_parser().parse_args(extra + ["--seed", str(4100 + i), "-d", str(music)] + suffix)
        compose_from_args(args)


def _grab(app, window, backend, out) -> int:
    from PySide6.QtCore import QTimer
    backend.load_first()
    window.show()

    def shoot():
        try:
            _shoot()
        except Exception as e:
            print(f"screenshot failed: {e!r}", file=sys.stderr)
            app.exit(1)

    def _shoot():
        img = window.grabWindow()
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        ok = img.save(str(out))
        content = window.property("contentH")
        print(f"{out}: window {window.width()}x{window.height()} logical, image {img.width()}x{img.height()} px, "
              f"content {content:.0f}, screen {backend.screen_size()[0]}x{backend.screen_size()[1]} logical, "
              f"{'scrolls' if content > window.height() else 'fits'}"
              + ("" if ok else "  (SAVE FAILED)"))
        app.exit(0 if ok else 1)
    QTimer.singleShot(1500, shoot)
    return app.exec()
