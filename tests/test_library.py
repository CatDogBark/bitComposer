"""The packs on this machine (the player's PACKS panel): add, move, rename,
export, delete, import. Run with: python3 -m unittest discover -s tests"""
import json
import math
import os
import random
import sys
import tempfile
import threading
import zipfile
from pathlib import Path

from support import unittest  # noqa: F401
from bitcomposer.packs import library, packfile  # noqa: E402
from test_packfile import write_wav  # noqa: E402


def make_pack(folder: Path) -> dict:
    """A small pack in `folder`: three pitched samples (lead and bass), two
    drums, and why they are where they are. Returns its pack file's data."""
    tone = [math.sin(2 * math.pi * 441 * i / 22050) * min(1, i / 600) for i in range(11025)]
    for v in ("flute", "oboe", "horn"):
        write_wav(folder / f"{v}.wav", tone)
    r = random.Random(2)
    for v in ("thump", "tick"):
        write_wav(folder / f"{v}.wav", [r.uniform(-.5, .5) * math.exp(-i / 400) for i in range(4000)])
    pitched = {"hz": 441, "loop": [5000, 11025], "release": "lead"}
    data = {"bitcomposer_pack": 1, "name": "test_quest", "label": "Test Quest", "palette": "snes",
            "voices": {"lead": ["flute"] * 4 + ["oboe"] * 2, "bass_heavy": ["horn"], "bass_medium": ["horn"],
                       "bass_light": ["horn"], "drums": {"kick": "thump", "snare": "tick"}},
            "samples": {"flute": {"file": "flute.wav", **pitched}, "oboe": {"file": "oboe.wav", **pitched},
                        "horn": {"file": "horn.wav", **pitched},
                        "thump": {"file": "thump.wav", "percussion": True},
                        "tick": {"file": "tick.wav", "percussion": True}}}
    (folder / "pack.json").write_text(json.dumps(data))
    (folder / library.WHY).write_text(json.dumps({"songs": 9, "why": {"flute": [["melody", 7, 900]]}}))
    return data


class Library(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        old = os.environ.get("BITCOMPOSER_DATA_DIR")
        os.environ["BITCOMPOSER_DATA_DIR"] = os.path.join(self.dir.name, "data")
        self.addCleanup(lambda: os.environ.__setitem__("BITCOMPOSER_DATA_DIR", old) if old is not None
                        else os.environ.pop("BITCOMPOSER_DATA_DIR", None))
        self.src = Path(self.dir.name) / "made"
        self.src.mkdir()
        self.data = make_pack(self.src)
        self.addCleanup(packfile.unload, "test_quest")

    def test_a_pack_added_from_its_folder_is_listed_part_by_part(self):
        self.assertEqual(library.add(self.src), "test_quest")
        [p] = library.listing()
        self.assertEqual(p["parts"], {"lead": ["flute", "oboe"], "bass": ["horn"]})
        self.assertEqual(p["kit"], {"kick": "thump", "snare": "tick"})
        self.assertEqual((p["songs"], p["samples"], p["out"]), (9, 5, []))
        self.assertEqual(p["why"]["flute"], [["melody", 7, 900]])
        self.assertEqual(packfile.load_pack_file(p["path"]), "test_quest")

    def test_moving_a_sample_keeps_how_often_it_is_drawn(self):
        library.add(self.src)
        library.move("test_quest", "flute", "bass")                   # to all three bass pools, four times each
        voices = json.loads(library.pack_file("test_quest").read_text())["voices"]
        self.assertEqual(voices["lead"], ["oboe"] * 2)
        self.assertEqual(voices["bass_light"], ["horn", "flute", "flute", "flute", "flute"])
        library.move("test_quest", "thump", "snare")                  # a kit piece holds one drum: tick goes out
        [p] = library.listing()
        self.assertEqual((p["kit"], p["out"]), ({"snare": "thump"}, ["tick"]))
        library.move("test_quest", "oboe", "out")
        self.assertNotIn("lead", library.listing()[0]["parts"])
        with self.assertRaises(packfile.PackError):
            library.move("test_quest", "horn", "kick")               # a pitched sample is no drum
        with self.assertRaises(packfile.PackError):
            library.move("test_quest", "tick", "arp")                # nor a drum an arp

    def test_an_exported_pack_comes_back_as_it_went(self):
        library.add(self.src)
        library.move("test_quest", "oboe", "harmony")
        before = library.listing()
        zipped = library.export("test_quest", Path(self.dir.name) / "out")
        self.assertEqual(zipped.suffix, ".zip")
        self.assertEqual(sorted(zipfile.ZipFile(zipped).namelist()),
                         sorted(["pack.json", library.WHY, "flute.wav", "oboe.wav", "horn.wav", "thump.wav", "tick.wav"]))
        library.delete("test_quest")
        self.assertEqual(library.listing(), [])
        self.assertEqual(library.add(zipped), "test_quest")
        self.assertEqual(library.listing(), before)
        with self.assertRaises(library.Exists):
            library.add(zipped)
        self.assertEqual(library.add(zipped, replace=True), "test_quest")

    def test_a_zip_reaching_out_of_its_folder_is_refused(self):
        bad = Path(self.dir.name) / "bad.zip"
        with zipfile.ZipFile(bad, "w") as z:
            z.writestr("pack.json", json.dumps(self.data))
            z.writestr("../flute.wav", b"RIFF")
        with self.assertRaises(packfile.PackError):
            library.add(bad)
        self.assertFalse((Path(self.dir.name) / "data" / "flute.wav").exists())

    def test_a_renamed_pack_moves_its_folder(self):
        library.add(self.src)
        library.rename("test_quest", "quest_two")
        self.addCleanup(packfile.unload, "quest_two")
        self.assertEqual([p["name"] for p in library.listing()], ["quest_two"])
        self.assertEqual(json.loads(library.pack_file("quest_two").read_text())["name"], "quest_two")
        with self.assertRaises(packfile.PackError):
            library.rename("quest_two", "ffvi")                      # a built-in sound's name

    def test_a_preview_is_a_module_of_the_voice(self):
        library.add(self.src)
        for voice, part in (("flute", "lead"), ("oboe", "harmony"), ("horn", "bass"), ("thump", "kick")):
            path = library.preview("test_quest", voice, part, Path(self.dir.name) / f"{voice}.it")
            raw = path.read_bytes()
            self.assertEqual(raw[:4], b"IMPM")
            self.assertEqual(int.from_bytes(raw[0x24:0x26], "little"), 1)   # one sample

    def test_an_import_made_anew_replaces_the_pack(self):
        # the import's own process stood in for: it reports two songs and writes the pack
        library.add(self.src)
        library.move("test_quest", "oboe", "out")
        src, done, finished = self.src, [], threading.Event()

        class Fake(library.Import):
            def command(self):
                return [sys.executable, "-c", "import shutil, sys; print('progress 1 2'); print('progress 2 2'); "
                        f"shutil.copytree({str(src)!r}, sys.argv[1])", str(self.stage)]
        job = Fake(self.src, "test_quest", on_progress=lambda d, t: done.append((d, t)),
                   on_done=lambda name, error: (done.append((name, error)), finished.set()))
        original = library.can_import
        library.can_import = lambda: True                              # no emulator needed: nothing is emulated
        self.addCleanup(setattr, library, "can_import", original)
        job.start()
        self.assertTrue(finished.wait(20))
        self.assertEqual(done, [(1, 2), (2, 2), ("test_quest", None)])
        self.assertEqual(library.listing()[0]["parts"]["lead"], ["flute", "oboe"])   # fresh: the move is gone
        self.assertFalse(any(p.name.startswith(".") for p in library.packs_dir().iterdir()))


if __name__ == "__main__":
    unittest.main()
