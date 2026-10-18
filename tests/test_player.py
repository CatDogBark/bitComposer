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
