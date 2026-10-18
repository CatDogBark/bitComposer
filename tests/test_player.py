"""The player engine, headless: a null audio output paces the decode thread,
so transport, the live mixer, KEEP and in-process generation run as they do
in the window, without a device."""
import os
import queue
import sys
import tempfile
import time
import unittest
import unittest.mock

try:
    from .support import compose_and_save
except ImportError:          # discover -s tests imports the modules top-level
    from support import compose_and_save
from bitcomposer.player import engine
from bitcomposer.player.openmpt import LibraryMissing, lib


def _have_openmpt():
    try:
        lib()
        return True
    except LibraryMissing:
        return False


@unittest.skipUnless(_have_openmpt(), "libopenmpt is not installed")
class EngineHeadless(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.music = os.path.join(self.tmp.name, "music")
        os.makedirs(self.music)
        os.environ["XDG_CONFIG_HOME"] = os.path.join(self.tmp.name, "cfg")
        compose_and_save(os.path.join(self.music, "Kept.it"), seed=3, sound="chip")
        compose_and_save(os.path.join(self.music, "Fresh (auto).it"), seed=4, sound="chip")
        self.q = queue.Queue()
        self.p = engine.Player(music_dir=self.music, schedule=self.q.put, output_kind="null")
        self.p.on_log = lambda *_: None

    def tearDown(self):
        self.p.shutdown()
        self.tmp.cleanup()

    def pump(self, seconds):
        end = time.time() + seconds
        while time.time() < end:
            try:
                self.q.get(timeout=0.05)()
            except queue.Empty:
                pass

    def test_transport_mixer_keep_and_generate(self):
        p = self.p
        p.scan()
        self.assertEqual([p.is_autogen(t) for t in p.playlist], [True, False])
        p.play(1)
        self.pump(0.8)
        m = p.metadata()
        self.assertEqual(p.status, "Playing")
        self.assertEqual(m["channels"], 19)
        self.assertEqual(m["layout"][:2], ["melody", "harmony"])
        self.assertGreater(p.position(), 0.3)
        # pause holds the position, resume moves on from it
        p.pause(); self.pump(0.2)
        held = p.position()
        self.assertEqual(p.status, "Paused")
        p.pause(); self.pump(0.6)
        self.assertGreater(p.position(), held)
        # the live mixer survives a seek and APPLY writes it into the file
        self.assertTrue(p.set_channel_volume(1, 5))
        p.seek(20.0); self.pump(0.3)
        self.assertEqual(p.channel_volumes()[1], 5)
        self.assertTrue(p.apply_mix_to_file())
        with open(p.playlist[1], "rb") as fh:
            fh.seek(0x80)
            self.assertEqual(fh.read(2)[1], 5)
        # KEEP strips the suffix
        self.assertEqual(p.keep_track(0), "Fresh.it")
        self.assertFalse(p.is_autogen(p.playlist[0]))
        # generation in-process lands in the folder as an (auto) track and plays
        done = []
        p.generate("--sound chip -s 9", play=True, on_done=done.append)
        self.pump(60)
        self.assertEqual(len(done), 1)
        self.assertTrue(os.path.basename(done[0]).startswith("(auto) "))   # the mark in front
        self.assertEqual(p.status, "Playing")
        self.assertEqual(os.path.basename(p.module.filepath), os.path.basename(done[0]))
        # KEEP takes the mark off the front
        new = p.playlist.index(done[0])
        self.assertEqual(p.keep_track(new), os.path.basename(done[0])[len("(auto) "):])
        self.assertFalse(p.is_autogen(p.playlist[new]))

    def test_newest_first_and_a_remix_stays_put(self):
        p = self.p
        p.scan()
        names = [os.path.basename(f) for f in p.playlist]
        self.assertEqual(names, ["Fresh (auto).it", "Kept.it"])     # composed second, listed first
        older = os.path.join(self.music, "Kept.it")
        os.utime(older, (time.time() + 60, time.time() + 60))        # touched later: now the newest
        p.scan()
        self.assertEqual(os.path.basename(p.playlist[0]), "Kept.it")
        before = os.stat(older).st_mtime_ns
        engine.write_channel_volumes(older, [5] * 19)                # APPLY TO TRACK
        self.assertEqual(os.stat(older).st_mtime_ns, before)

    def test_message_parsing_and_header_write(self):
        info = engine.parse_message("Title\r\nC major - 120 BPM\r\nvoices: melody=a,harmony=b\r\ndrew: sound=chip,form=aaba\r\nlayout: melody,harmony,echo.melody\r\n")
        self.assertEqual(info["layout"], ["melody", "harmony", "echo.melody"])
        self.assertEqual(info["voices"]["harmony"], "b")
        self.assertEqual(info["drew"]["form"], "aaba")
        self.assertEqual(info["lines"], ["Title", "C major - 120 BPM"])
        path = os.path.join(self.music, "Kept.it")
        engine.write_channel_volumes(path, [1, 2, 3])
        with open(path, "rb") as fh:
            fh.seek(0x80)
            self.assertEqual(fh.read(3), bytes([1, 2, 3]))


class UpdateCheck(unittest.TestCase):
    def test_versions_and_release_choice(self):
        import json
        from bitcomposer.player import update as u
        self.assertLess(u.parse_version("1.0.0rc2"), u.parse_version("1.0.0"))
        self.assertLess(u.parse_version("1.0.0rc1"), u.parse_version("1.0.0rc2"))
        self.assertLess(u.parse_version("1.0.0"), u.parse_version("1.0.1"))
        self.assertEqual(u.parse_version("garbage"), ())
        rels = [{"tag_name": "v1.0.0rc3", "prerelease": True, "html_url": "p",
                 "assets": [{"name": "bitComposer-setup.exe", "browser_download_url": "u"}]},
                {"tag_name": "v0.9.1", "prerelease": False, "html_url": "q", "assets": []}]
        fetch = lambda url: json.dumps(rels).encode()
        # a candidate player sees the next candidate; a release player does not
        self.assertEqual(u.newer_release("1.0.0rc2", fetch)["version"], "1.0.0rc3")
        self.assertEqual(u.newer_release("1.0.0rc2", fetch)["installer"], "u")
        self.assertIsNone(u.newer_release("0.9.1", fetch))
        rels.append({"tag_name": "v1.0.0", "prerelease": False, "html_url": "r", "assets": []})
        self.assertEqual(u.newer_release("0.9.1", fetch)["version"], "1.0.0")
        self.assertEqual(u.newer_release("1.0.0rc2", fetch)["version"], "1.0.0")
        self.assertIsNone(u.newer_release("1.0.0", fetch))
        # a dead network is no update, not an error
        self.assertIsNone(u.newer_release("1.0.0", lambda url: (_ for _ in ()).throw(OSError("offline"))))
        self.assertIn(u.install_kind(), ("frozen", "pipx", "other"))

    def test_pipx_is_told_by_its_metadata_file(self):
        """pipx's venv python links to the system one, so the interpreter's
        path says nothing; the venv's pipx_metadata.json does."""
        from unittest import mock
        from bitcomposer.player import update as u
        with tempfile.TemporaryDirectory() as venv:
            with mock.patch.object(sys, "prefix", venv):
                self.assertEqual(u.install_kind(), "other")
                open(os.path.join(venv, "pipx_metadata.json"), "w").close()
                self.assertEqual(u.install_kind(), "pipx")

    def test_pipx_update_streams_its_output(self):
        """The update screen gets pipx's lines as they come, cleaned of its
        debug prefixes, and a failure says so instead of vanishing."""
        from unittest import mock
        from bitcomposer.player import update as u
        with tempfile.TemporaryDirectory() as t:
            def fake_pipx(code):
                f = os.path.join(t, f"pipx{code}")
                with open(f, "w") as fh:
                    fh.write("#!/bin/sh\necho 'pipx >(install_package:247): Installing bitcomposer from spec x'\n"
                             "echo 'installing bitcomposer...'\necho 'done! \u2728'\nexit %d\n" % code)
                os.chmod(f, 0o755)
                return [f]
            rel = {"version": "9.9.9", "tag": "v9.9.9", "page": "p"}
            for code, expect in ((0, True), (1, False)):
                lines = []
                with mock.patch.object(u, "install_kind", lambda: "pipx"), \
                        mock.patch.object(u, "pipx_command", lambda c=code: fake_pipx(c)):
                    self.assertEqual(u.apply_update(rel, lambda text, prog: lines.append(text)), expect)
                self.assertEqual(lines[0], "$ pipx install --force bitcomposer==9.9.9")
                self.assertIn("Installing bitcomposer from spec x", lines)          # the prefix gone
                self.assertIn("done!", lines)                                       # the pictograph gone
                self.assertTrue(lines[-1].startswith("updated to" if expect else "pipx exited with 1"))

    def test_pipx_update_asks_again_past_a_stale_index(self):
        """pip's saved copy of PyPI's version list can predate the release
        the player saw on GitHub: the update asks once more without pip's
        cache, and says PyPI is behind when it still has no such version."""
        from unittest import mock
        from bitcomposer.player import update as u
        with tempfile.TemporaryDirectory() as t:
            def fake_pipx(listed_without_cache):
                f = os.path.join(t, f"pipx-{listed_without_cache}")
                with open(f, "w") as fh:
                    fh.write("#!/bin/sh\n"
                             f"if [ -n \"$PIP_NO_CACHE_DIR\" ] && [ {int(listed_without_cache)} = 1 ]; then echo 'done!'; exit 0; fi\n"
                             "echo '    ERROR: Could not find a version that satisfies the requirement bitcomposer==9.9.9 (from versions: 9.9.8)'\n"
                             "echo '    ERROR: No matching distribution found for bitcomposer==9.9.9'\nexit 1\n")
                os.chmod(f, 0o755)
                return [f]
            rel = {"version": "9.9.9", "tag": "v9.9.9", "page": "p"}
            for listed, expect in ((True, True), (False, False)):
                lines = []
                with mock.patch.object(u, "install_kind", lambda: "pipx"), \
                        mock.patch.object(u, "pipx_command", lambda l=listed: fake_pipx(l)):
                    self.assertEqual(u.apply_update(rel, lambda text, prog: lines.append(text)), expect)
                self.assertIn("$ PIP_NO_CACHE_DIR=1 pipx install --force bitcomposer==9.9.9", lines)
                if expect:
                    self.assertTrue(lines[-1].startswith("updated to 9.9.9"))
                else:
                    self.assertTrue(any(l.startswith("PyPI does not list 9.9.9 yet") for l in lines))
                    self.assertTrue(lines[-1].startswith("pipx exited with 1"))
            # any other failure is not retried
            lines = []
            with mock.patch.object(u, "install_kind", lambda: "pipx"), \
                    mock.patch.object(u, "pipx_command", lambda: ["false"]):
                self.assertFalse(u.apply_update(rel, lambda text, prog: lines.append(text)))
            self.assertFalse(any("PIP_NO_CACHE_DIR" in l for l in lines))

    def test_try_update_offers_a_local_installer(self):
        """--try-update: the UPDATE button for a setup.exe on this machine,
        so the update path runs without a published release."""
        from bitcomposer.player import update as u
        with tempfile.TemporaryDirectory() as t:
            setup = os.path.join(t, "bitComposer-setup.exe")
            with open(setup, "wb") as fh:
                fh.write(b"MZ")
            rel = u.local_release(setup, "1.0.0rc2")
            self.assertEqual(rel["version"], "1.0.0rc2 (test)")
            import urllib.request
            got = os.path.join(t, "copy.exe")
            urllib.request.urlretrieve(rel["installer"], got)          # what apply_update does with it
            with open(got, "rb") as fh:
                self.assertEqual(fh.read(), b"MZ")
            # a wheel says its own version, and pipx installs it by path
            wheel = os.path.join(t, "bitcomposer-1.0.0rc5-py3-none-any.whl")
            rel = u.local_release(wheel, "1.0.0rc4")
            self.assertEqual(rel["version"], "1.0.0rc5 (test)")
            self.assertEqual(rel["spec"], wheel)

    def test_restart_leaves_the_one_time_options_behind(self):
        """After an update the new player starts on the same command, less a
        test release (offered again otherwise) and a hidden start."""
        from unittest import mock
        from bitcomposer.player import update as u
        argv = ["/x/bitcomposer-player", "--minimized", "--try-update", "a.whl",
                "--try-update=b.whl", "--music-dir", "/m"]
        with mock.patch.object(sys, "argv", argv), mock.patch.object(os, "execv") as execv:
            u.restart_self()
        self.assertEqual(execv.call_args[0][1][-2:], ["--music-dir", "/m"])
        self.assertFalse([a for a in execv.call_args[0][1] if "update" in a or a == "--minimized"])


def _have_qt():
    try:
        import PySide6.QtQuick  # noqa: F401
        return True
    except ImportError:
        return False


@unittest.skipUnless(_have_openmpt() and _have_qt(), "needs libopenmpt and PySide6")
class WindowHeadless(unittest.TestCase):
    """The Qt face offscreen: the bridge the QML binds to, driven the way
    the window drives it, and the window itself loading without a QML
    error and fitting the screen it is told about."""

    @classmethod
    def setUpClass(cls):
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        os.environ["QT_QUICK_BACKEND"] = "software"
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.music = os.path.join(self.tmp.name, "music")
        os.makedirs(self.music)
        os.environ["XDG_CONFIG_HOME"] = os.path.join(self.tmp.name, "cfg")
        compose_and_save(os.path.join(self.music, "Kept.it"), seed=3, sound="chip")
        compose_and_save(os.path.join(self.music, "Fresh (auto).it"), seed=4, sound="chip")
        from bitcomposer.player.backend import Backend
        self.b = Backend(music_dir=self.music, quiet=True, output_kind="null")

    def tearDown(self):
        self.b.shutdown()
        self.tmp.cleanup()

    def pump(self, seconds, until=None):
        end = time.time() + seconds
        while time.time() < end:
            self.app.processEvents()
            if until and until():
                return True
            time.sleep(0.02)
        return bool(until and until())

    def test_bridge(self):
        b = self.b
        self.assertEqual([t["auto"] for t in b.playlist], [True, False])
        self.assertEqual(b.state["currentIndex"], -1)
        b.playIndex(1)
        self.assertTrue(self.pump(2, lambda: b.position > 0.3))
        st = b.state
        self.assertEqual(st["status"], "Playing")
        self.assertEqual(st["currentIndex"], 1)
        self.assertEqual(st["layout"][0], "melody")
        self.assertIn("BPM", st["message"])
        self.assertEqual(len(b.channelVolumes), 19)
        b.setChannelVolume(1, 7)
        self.assertTrue(b.applyMix())
        self.assertEqual(b.channelVolumes[1], 7)
        b.keep(0)
        self.pump(0.2)
        self.assertEqual([t["auto"] for t in b.playlist], [False, False])
        # turning AUTO on while playing composes nothing yet
        b.setAutoGenerate(True, "--sound chip")
        self.pump(0.2)
        self.assertFalse(b.state["generating"])
        self.assertTrue(b.state["autoGenerate"])
        # GENERATE composes in the background and plays the new track
        b.generate("--sound chip -s 9")
        self.pump(0.1)
        self.assertTrue(b.state["generating"])
        self.assertTrue(self.pump(60, lambda: not b.state["generating"]))
        self.assertEqual(len(b.playlist), 3)
        self.assertEqual(b.state["status"], "Playing")
        self.assertTrue(b.state["file"].startswith("(auto) "))
        self.assertIn("composed", b.notice)
        # the window's own settings round-trip
        b.saveUi('{"settTempo": "fast"}')
        self.assertEqual(b.loadUi(), '{"settTempo": "fast"}')
        # the update check can be turned off, and stays off
        import json
        from bitcomposer.player.engine import state_file
        self.assertTrue(b.checkUpdates)
        b.setCheckUpdates(False)
        self.assertFalse(b.checkUpdates)
        with open(state_file()) as fh:
            self.assertFalse(json.load(fh)["check_updates"])

    def test_window_loads_and_fits(self):
        from pathlib import Path
        from PySide6.QtCore import QUrl
        from PySide6.QtQml import QQmlApplicationEngine
        from PySide6.QtQuick import QQuickWindow  # noqa: F401
        import bitcomposer.player as pkg
        warnings = []
        eng = QQmlApplicationEngine()
        eng.warnings.connect(lambda ws: warnings.extend(w.toString() for w in ws))
        self.b.set_screen(1280, 672)       # 1920x1080 at 150%, less a taskbar
        eng.rootContext().setContextProperty("backend", self.b)
        eng.setInitialProperties({"startSettings": True, "startMaster": True, "still": True})
        eng.load(QUrl.fromLocalFile(str(Path(pkg.__file__).parent / "qml" / "Main.qml")))
        self.assertTrue(eng.rootObjects(), warnings)
        win = eng.rootObjects()[0]
        self.b.playIndex(0)
        win.show()
        self.pump(1.0)
        self.assertEqual(warnings, [])
        # both panels open: taller than the screen, so the window stops at
        # the screen and the column scrolls inside it
        self.assertGreater(win.property("contentH"), 672)
        self.assertLessEqual(win.height(), 672)
        self.assertLessEqual(win.width(), 1280)
        win.close()
        del eng

    def test_minimized_start_stays_in_the_tray(self):
        """--minimized (start at login): no window until asked for; shown
        later, it sizes itself as a normal start does."""
        from pathlib import Path
        from PySide6.QtCore import QUrl
        from PySide6.QtQml import QQmlApplicationEngine
        from PySide6.QtQuick import QQuickWindow  # noqa: F401
        import bitcomposer.player as pkg
        warnings = []
        eng = QQmlApplicationEngine()
        eng.warnings.connect(lambda ws: warnings.extend(w.toString() for w in ws))
        self.b.set_screen(1920, 1152)
        eng.rootContext().setContextProperty("backend", self.b)
        eng.setInitialProperties({"still": True, "startHidden": True})
        eng.load(QUrl.fromLocalFile(str(Path(pkg.__file__).parent / "qml" / "Main.qml")))
        win = eng.rootObjects()[0]
        self.pump(0.8)
        self.assertFalse(win.isVisible())
        self.assertFalse(win.property("_sized"))
        win.show()
        self.assertTrue(self.pump(3, lambda: win.property("_sized")))
        self.pump(0.3)
        self.assertLess(win.height(), 1152 - 64)          # shrunk to the content, as a normal start
        self.assertEqual(warnings, [])
        win.close()
        del eng

    def test_update_screen(self):
        """UPDATE opens the update screen asking first; UPDATE NOW runs it and
        its lines reach the screen's log; a failure ends on CLOSE, and the
        player is unchanged."""
        from pathlib import Path
        from unittest import mock
        from PySide6.QtCore import QObject, QUrl
        from PySide6.QtQml import QQmlApplicationEngine
        from PySide6.QtQuick import QQuickWindow  # noqa: F401
        import bitcomposer.player as pkg
        from bitcomposer.player import update as u
        warnings = []
        eng = QQmlApplicationEngine()
        eng.warnings.connect(lambda ws: warnings.extend(w.toString() for w in ws))
        self.b.set_screen(1920, 1152)
        eng.rootContext().setContextProperty("backend", self.b)
        eng.setInitialProperties({"still": True})
        eng.load(QUrl.fromLocalFile(str(Path(pkg.__file__).parent / "qml" / "Main.qml")))
        win = eng.rootObjects()[0]
        win.show()
        self.pump(0.5)
        panel = win.findChild(QObject, "updatePanel")
        self.assertFalse(panel.property("visible"))
        self.b.offer({"version": "9.9.9", "tag": "v9.9.9", "page": "p", "installer": None})
        self.b.applyUpdate()
        self.pump(0.3)
        self.assertEqual(self.b.updateState, "confirm")
        self.assertTrue(panel.property("visible"))

        def fake(rel, report, restart=None):
            report("$ pipx install --force bitcomposer==9.9.9", None)
            report("installing bitcomposer...", None)
            report("pipx exited with 1; the player is unchanged", None)
            return False
        with mock.patch.object(u, "apply_update", fake):
            self.b.confirmUpdate()
            self.assertTrue(self.pump(3, lambda: self.b.updateState == "failed"))
        self.pump(0.3)
        self.assertEqual(len(self.b.updateLog), 3)
        self.assertEqual(win.findChild(QObject, "updateLog").property("count"), 3)
        self.b.closeUpdate()
        self.pump(0.2)
        self.assertFalse(panel.property("visible"))
        self.assertEqual(warnings, [])
        win.close()
        del eng

    def test_panels_open_inside_the_window(self):
        """SET and MIX opened after start leave the window's size alone (it
        grew before, off the bottom of a Wayland screen, and flashed) and
        scroll the opened panel into view."""
        from pathlib import Path
        from PySide6.QtCore import QObject, QUrl
        from PySide6.QtQml import QQmlApplicationEngine
        from PySide6.QtQuick import QQuickWindow  # noqa: F401
        import bitcomposer.player as pkg
        warnings = []
        eng = QQmlApplicationEngine()
        eng.warnings.connect(lambda ws: warnings.extend(w.toString() for w in ws))
        self.b.set_screen(1920, 1152)
        eng.rootContext().setContextProperty("backend", self.b)
        eng.setInitialProperties({"still": True})
        eng.load(QUrl.fromLocalFile(str(Path(pkg.__file__).parent / "qml" / "Main.qml")))
        win = eng.rootObjects()[0]
        self.b.playIndex(0)
        win.show()
        self.assertTrue(self.pump(3, lambda: win.property("_sized")))
        self.pump(0.5)
        size = (win.width(), win.height())
        self.assertLess(win.height(), 1152 - 64)          # panels closed: the content, not the screen
        scroll = win.findChild(QObject, "scroll")
        win.setProperty("showSettings", True)
        self.pump(0.5)
        win.setProperty("showMaster", True)
        self.pump(0.6)
        self.assertEqual((win.width(), win.height()), size)
        self.assertGreater(win.property("contentH"), win.height())
        self.assertGreater(scroll.property("contentY"), 0)  # MIX scrolled into view
        self.assertEqual(warnings, [])
        win.close()
        del eng


class DesktopEntry(unittest.TestCase):
    """The Linux app-menu entry: the first launch of an installed player
    adds it, a moved program is repaired, a removed entry stays removed."""

    def setUp(self):
        from unittest import mock
        self.tmp = tempfile.TemporaryDirectory()
        t = self.tmp.name
        self.bin = os.path.join(t, "bin")
        os.makedirs(self.bin)
        self.exe = os.path.join(self.bin, "bitcomposer-player")
        open(self.exe, "w").close()
        os.chmod(self.exe, 0o755)
        self.patches = [
            mock.patch.dict(os.environ, {"XDG_DATA_HOME": os.path.join(t, "data"), "XDG_CONFIG_HOME": os.path.join(t, "cfg"),
                                         "PATH": self.bin}),
            mock.patch.object(sys, "argv", [self.exe]),
            mock.patch.object(sys, "platform", "linux"),
        ]
        for p in self.patches:
            p.start()
        os.environ.pop("FLATPAK_ID", None)
        from bitcomposer.player import desktop
        self.d = desktop
        self.entry, self.icon = desktop._paths()

    def tearDown(self):
        for p in reversed(self.patches):
            p.stop()
        self.tmp.cleanup()

    def read(self):
        with open(self.entry) as fh:
            return fh.read()

    def test_first_launch_repair_and_removal(self):
        d = self.d
        self.assertEqual(d.ensure_entry(), "added")
        text = self.read()
        self.assertIn(f"Exec={self.exe}\n", text)
        self.assertIn("Icon=bitcomposer\n", text)
        self.assertIn("StartupWMClass=bitcomposer-player\n", text)
        self.assertTrue(os.path.exists(self.icon))
        self.assertEqual(d.ensure_entry(), "")              # nothing to do the second time
        with open(self.icon, "w") as fh:                     # an older version's icon
            fh.write("<svg/>")
        self.assertEqual(d.ensure_entry(), "icon")
        self.assertEqual(d.ensure_entry(), "")
        # the program moved (a reinstall elsewhere): the entry follows it
        moved = os.path.join(self.tmp.name, "other bin", "bitcomposer-player")
        os.makedirs(os.path.dirname(moved))
        os.rename(self.exe, moved)
        with unittest.mock.patch.object(sys, "argv", [moved]), unittest.mock.patch.dict(os.environ, {"PATH": os.path.dirname(moved)}):
            self.assertEqual(d.ensure_entry(), "repaired")
            self.assertIn(f'Exec="{moved}"\n', self.read())
            self.assertEqual(d.ensure_entry(), "")          # quoted path with a space reads back
        # removed by the user: stays removed until asked for
        self.assertEqual(len(d.remove_entry()), 2)
        self.assertEqual(d.ensure_entry(), "")
        self.assertFalse(os.path.exists(self.entry))

    def test_start_at_login(self):
        from bitcomposer.player import autostart
        self.assertTrue(autostart.supported())
        self.assertFalse(autostart.is_enabled())
        self.assertEqual(autostart.set_enabled(True), "")
        f = os.path.join(os.environ["XDG_CONFIG_HOME"], "autostart", "bitcomposer-player.desktop")
        with open(f) as fh:
            text = fh.read()
        self.assertIn(f"Exec={self.exe} --minimized\n", text)   # in the tray, not the window
        self.assertTrue(autostart.is_enabled())
        self.assertEqual(autostart.set_enabled(False), "")
        self.assertFalse(os.path.exists(f))
        with unittest.mock.patch.object(sys, "argv", ["-m"]):    # a checkout run cannot be started at login
            self.assertFalse(autostart.supported())
            self.assertNotEqual(autostart.set_enabled(True), "")

    def test_site_icon_is_the_app_icon(self):
        """docs/ is all GitHub Pages serves, so the site keeps a copy of the tile."""
        from pathlib import Path
        root = Path(__file__).resolve().parents[1]
        self.assertEqual((root / "docs/images/bitcomposer.svg").read_bytes(),
                         (root / "bitcomposer/player/icons/bitcomposer.svg").read_bytes())

    def test_leaves_alone(self):
        d = self.d
        os.makedirs(os.path.dirname(self.entry))
        with open(self.entry, "w") as fh:                    # someone's own entry, no mark
            fh.write("[Desktop Entry]\nExec=/gone/bitcomposer-player\n")
        self.assertEqual(d.ensure_entry(), "")
        self.assertEqual(self.read(), "[Desktop Entry]\nExec=/gone/bitcomposer-player\n")
        os.remove(self.entry)
        with unittest.mock.patch.dict(os.environ, {"FLATPAK_ID": "io.github.CatDogBark.bitComposer"}):
            self.assertEqual(d.ensure_entry(), "")           # a Flatpak ships its own
        with unittest.mock.patch.object(sys, "argv", ["-m"]):
            self.assertEqual(d.ensure_entry(), "")           # python -m from a checkout: a menu cannot start that
        self.assertFalse(os.path.exists(self.entry))


def _have_bus_tools():
    import shutil
    try:
        import jeepney  # noqa: F401
    except ImportError:
        return False
    return shutil.which("dbus-daemon") is not None and sys.platform.startswith("linux")


@unittest.skipUnless(_have_openmpt() and _have_qt() and _have_bus_tools(), "needs libopenmpt, PySide6, jeepney and dbus-daemon")
class MprisOnAPrivateBus(unittest.TestCase):
    """The player as an MPRIS service, driven over a bus of its own the way
    the media keys, the Plasma applet and playerctl drive it."""

    @classmethod
    def setUpClass(cls):
        import subprocess
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])
        cls.daemon = subprocess.Popen(["dbus-daemon", "--session", "--nofork", "--print-address=1"],
                                      stdout=subprocess.PIPE, text=True)
        cls.address = cls.daemon.stdout.readline().strip()

    @classmethod
    def tearDownClass(cls):
        cls.daemon.terminate()
        cls.daemon.wait(5)

    def setUp(self):
        from jeepney.io.blocking import open_dbus_connection
        from bitcomposer.player.backend import Backend
        from bitcomposer.player.mpris import Mpris
        self.tmp = tempfile.TemporaryDirectory()
        self.music = os.path.join(self.tmp.name, "music")
        os.makedirs(self.music)
        os.environ["XDG_CONFIG_HOME"] = os.path.join(self.tmp.name, "cfg")
        compose_and_save(os.path.join(self.music, "One.it"), seed=3, sound="chip")
        compose_and_save(os.path.join(self.music, "Two.it"), seed=4, sound="chip")
        self.b = Backend(music_dir=self.music, quiet=True, output_kind="null")
        self.m = Mpris(self.b, bus=self.address)
        self.assertTrue(self.m.start())
        self.b.mpris = self.m
        self.client = open_dbus_connection(bus=self.address)

    def tearDown(self):
        self.client.close()
        self.b.shutdown()
        self.tmp.cleanup()

    def pump(self, seconds, until=None):
        end = time.time() + seconds
        while time.time() < end:
            self.app.processEvents()
            if until and until():
                return True
            time.sleep(0.02)
        return bool(until and until())

    def call(self, iface, member, sig=None, body=()):
        from jeepney import DBusAddress, new_method_call
        from bitcomposer.player import mpris
        addr = DBusAddress(mpris.PATH, bus_name=mpris.BUS_NAME, interface=iface)
        reply = self.client.send_and_get_reply(new_method_call(addr, member, sig, body), timeout=3)
        return reply.body

    def prop(self, name, iface="org.mpris.MediaPlayer2.Player"):
        (variant,) = self.call("org.freedesktop.DBus.Properties", "Get", "ss", (iface, name))
        return variant

    def test_media_keys_and_what_the_desktop_reads(self):
        from jeepney import MatchRule, message_bus
        from bitcomposer.player import mpris
        self.assertEqual(self.prop("Identity", mpris.ROOT), ("s", "bitComposer"))
        self.assertEqual(self.prop("DesktopEntry", mpris.ROOT), ("s", "bitcomposer-player"))
        self.assertIn("org.mpris.MediaPlayer2.Player", self.call("org.freedesktop.DBus.Introspectable", "Introspect")[0])
        self.assertEqual(self.prop("PlaybackStatus"), ("s", "Stopped"))
        changes = MatchRule(type="signal", interface="org.freedesktop.DBus.Properties", member="PropertiesChanged")
        seeks = MatchRule(type="signal", interface=mpris.PLAYER, member="Seeked")
        self.client.send_and_get_reply(message_bus.AddMatch(changes), timeout=3)
        self.client.send_and_get_reply(message_bus.AddMatch(seeks), timeout=3)
        with self.client.filter(changes) as changed, self.client.filter(seeks) as seeked:
            self.call(mpris.PLAYER, "PlayPause")                          # the play/pause key
            self.assertTrue(self.pump(3, lambda: self.b.state.get("status") == "Playing"))
            sig = self.client.recv_until_filtered(changed, timeout=3)
            self.assertEqual(sig.header.fields[8], "sa{sv}as")          # 8: the signature field
            iface, props, invalidated = sig.body
            self.assertEqual((iface, invalidated), (mpris.PLAYER, []))
            self.assertEqual(props["PlaybackStatus"], ("s", "Playing"))
            meta = props["Metadata"][1]
            self.assertEqual(meta["mpris:trackid"][0], "o")
            self.assertEqual(meta["mpris:length"][0], "x")
            self.assertGreater(meta["mpris:length"][1], 10_000_000)
            self.assertEqual(meta["xesam:artist"][0], "as")
            self.pump(0.6)
            sig_pos, us = self.prop("Position")
            self.assertEqual(sig_pos, "x")
            self.assertGreater(us, 200_000)
            # SetPosition with the current track's id, then the Seeked signal
            tid = self.prop("Metadata")[1]["mpris:trackid"][1]
            self.call(mpris.PLAYER, "SetPosition", "ox", (tid, 30_000_000))
            self.assertTrue(self.pump(3, lambda: self.b.player.position() >= 29.5))   # the seek runs on this (the main) thread
            got = self.client.recv_until_filtered(seeked, timeout=3)
            self.assertAlmostEqual(got.body[0] / 1e6, 30.0, delta=0.5)
            # volume from the desktop's slider, next from the key, pause
            self.call("org.freedesktop.DBus.Properties", "Set", "ssv", (mpris.PLAYER, "Volume", ("d", 0.5)))
            self.assertTrue(self.pump(2, lambda: abs(self.b.state.get("volume", 1) - 0.5) < 1e-6))
            first = self.b.state["file"]
            self.call(mpris.PLAYER, "Next")
            self.assertTrue(self.pump(3, lambda: self.b.state.get("file") != first))
            self.call(mpris.PLAYER, "Pause")
            self.assertTrue(self.pump(3, lambda: self.b.state.get("status") == "Paused"))
            self.call(mpris.PLAYER, "Pause")                              # Pause is not a toggle
            self.pump(0.3)
            self.assertEqual(self.b.state.get("status"), "Paused")
        raised = []
        self.b.raiseRequested.connect(lambda: raised.append(1))
        self.call(mpris.ROOT, "Raise")
        self.assertTrue(self.pump(2, lambda: raised))


def _player_script():
    import shutil
    here = os.path.join(os.path.dirname(sys.executable), "bitcomposer-player")
    return here if os.path.exists(here) else shutil.which("bitcomposer-player")


@unittest.skipUnless(_have_openmpt() and _have_qt() and sys.platform.startswith("linux") and _player_script(),
                     "needs libopenmpt, PySide6 and an installed bitcomposer-player")
class SecondLaunch(unittest.TestCase):
    """A launch while a player already runs hands off to it and quits, but
    puts the app-menu entry back first (a terminal launch beside an older
    player left the menu empty)."""

    def test_entry_written_before_the_hand_off(self):
        import subprocess
        with tempfile.TemporaryDirectory() as t:
            env = dict(os.environ, QT_QPA_PLATFORM="offscreen", XDG_CONFIG_HOME=os.path.join(t, "cfg"),
                       XDG_DATA_HOME=os.path.join(t, "data"), BITCOMPOSER_MUSIC_DIR=os.path.join(t, "music"))
            entry = os.path.join(t, "data", "applications", "bitcomposer-player.desktop")
            flag = os.path.join(t, "cfg", "bitcomposer", "desktop-entry")
            first = subprocess.Popen([_player_script()], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            try:
                end = time.time() + 20
                while time.time() < end and not os.path.exists(entry):
                    time.sleep(0.2)
                self.assertTrue(os.path.exists(entry))
                time.sleep(1.0)                                  # the first player is listening by now
                os.remove(entry)
                os.remove(flag)
                second = subprocess.run([_player_script()], env=env, timeout=20, capture_output=True)
                self.assertEqual(second.returncode, 0)
                self.assertTrue(os.path.exists(entry))
                self.assertIsNone(first.poll())                  # handed off, the first one still runs
            finally:
                first.terminate()
                first.wait(10)
