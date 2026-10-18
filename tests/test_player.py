"""The player engine, headless: a null audio output paces the decode thread,
so transport, the live mixer, KEEP and in-process generation run as they do
in the window, without a device."""
import os
import queue
import tempfile
import time
import unittest

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
        self.assertTrue(done[0].endswith(" (auto).it"))
        self.assertEqual(p.status, "Playing")
        self.assertEqual(os.path.basename(p.module.filepath), os.path.basename(done[0]))

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
        self.assertTrue(b.state["file"].endswith(" (auto).it"))
        self.assertIn("composed", b.notice)
        # the window's own settings round-trip
        b.saveUi('{"settTempo": "fast"}')
        self.assertEqual(b.loadUi(), '{"settTempo": "fast"}')

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
