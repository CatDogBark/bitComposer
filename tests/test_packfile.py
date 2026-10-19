"""Pack files: the format, the loader, the CLI. Run with: python3 -m unittest discover -s tests"""
import json
import math
import random
import struct
import unittest
import wave

from support import compose_song, os, samples, tempfile, unittest  # noqa: F401,F811
from bitcomposer import cli  # noqa: E402
from bitcomposer.packs import PACKS, PACK_NAMES  # noqa: E402
from bitcomposer.packs import packfile as pf  # noqa: E402


def write_wav(path, values, rate=22050, width=2, channels=1):
    """values in -1..1, one per frame, written to every channel."""
    with wave.open(str(path), "wb") as w:
        w.setnchannels(channels); w.setsampwidth(width); w.setframerate(rate)
        out = bytearray()
        for v in values:
            for _ in range(channels):
                if width == 1:
                    out += bytes([128 + int(v * 127)])
                else:
                    out += int(v * (2 ** (8 * width - 1) - 1)).to_bytes(width, "little", signed=True)
        w.writeframes(bytes(out))


class PackFiles(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        d = self.dir.name
        write_wav(os.path.join(d, "flute.wav"),
                  [math.sin(2 * math.pi * 441 * i / 22050) * min(1, i / 600) for i in range(22050)])
        r = random.Random(1)
        write_wav(os.path.join(d, "thump.wav"),
                  [0.7 * math.sin(2 * math.pi * 60 * i / 22050) * math.exp(-i / 2500)
                   + r.uniform(-.2, .2) * math.exp(-i / 300) for i in range(8000)])
        self.pack = {"bitcomposer_pack": 1, "name": "testpack", "label": "Test pack", "palette": "snes",
                     "voices": {"lead": ["flute"], "drums": {"kick": "thump"}},
                     "habits": {"tempo": {"slow": 1, "medium": 3}, "echo": 1.0, "echo_feedback": [0.4, 0.5]},
                     "samples": {"flute": {"file": "flute.wav", "hz": 441, "loop": [11025, 22050], "release": "flute"},
                                 "thump": {"file": "thump.wav"}}}

    def save(self, pack=None):
        path = os.path.join(self.dir.name, "pack.json")
        with open(path, "w") as fh:
            json.dump(pack or self.pack, fh)
        return path

    def load(self, pack=None):
        name = pf.load_pack_file(self.save(pack))
        self.addCleanup(pf.unload, name)
        return name

    def test_builtin_packs_read_back_through_the_format(self):
        """Everything a built-in pack says, a pack file can say: each one
        written as pack file data and read back is the same table."""
        for name in PACK_NAMES:
            data = json.loads(json.dumps(pf.to_data(name)))
            parsed, own = pf.parse(data, self.dir.name, source=name)
            expected = dict(PACKS[name]); expected.setdefault("trims", {})
            self.assertEqual(parsed["table"], expected, name)
            self.assertEqual(own, {})

    def test_a_pack_file_with_its_own_voices_composes(self):
        name = self.load()
        self.assertEqual(name, "testpack")
        self.assertNotIn(name, PACK_NAMES)                 # never in SOUND's random draw
        self.assertEqual(PACKS[name]["voices"]["alt_lead"], ["testpack_flute"])   # filled from the lead
        self.assertEqual(PACKS[name]["habits"]["echo_feedback"], (0.4, 0.5))
        self.assertEqual(PACKS[name]["voices"]["drums"]["snare"], "snes_snare")   # the palette's kit fills in
        # the kit voice is percussion though its name says nothing; the flute sustains, with its release
        self.assertTrue(samples.is_percussion("testpack_thump"))
        self.assertFalse(samples.is_struck("testpack_flute"))
        self.assertEqual(samples.PRESET_RELEASE["testpack_flute"], "flute")
        song = compose_song(seed=3, pack=name)
        self.assertEqual(song["info"]["pack"], name)
        self.assertEqual(song["info"]["instruments"]["melody"], "testpack_flute")
        self.assertEqual(song["info"]["instruments"]["kick"], "testpack_thump")
        flute = next(s for s in song["samples"] if s.name == "Testpack Flute")
        # in tune: a 441 Hz recording at 22050 Hz plays middle C at its C5Speed
        self.assertEqual(flute.c5_speed, round(22050 * 2 ** ((60 - (69 + 12 * math.log2(441 / 440))) / 12)))
        self.assertEqual((flute.sus_loop_start, flute.sus_loop_end), (11025, 22050))
        # the same seed is the same song
        self.assertEqual(compose_song(seed=3, pack=name)["message"], song["message"])
        # unloading takes it all back out
        pf.unload(name)
        self.assertNotIn(name, PACKS)
        self.assertNotIn("testpack_flute", samples.INSTRUMENT_PRESETS)
        self.assertFalse(samples.is_percussion("testpack_thump"))

    def test_loading_again_is_free_and_a_changed_file_reloads(self):
        name = self.load()
        before = samples.INSTRUMENT_PRESETS["testpack_flute"]
        self.assertEqual(pf.load_pack_file(self.save()), name)        # rewritten, same bytes: reloaded
        self.pack["habits"]["tempo"] = {"fast": 1}
        self.load()
        self.assertEqual(PACKS[name]["habits"]["tempo"], {"fast": 1})
        self.assertIsNot(samples.INSTRUMENT_PRESETS["testpack_flute"], before)

    def test_the_cli_composes_with_a_pack_file(self):
        path = self.save()
        self.addCleanup(pf.unload, "testpack")
        args = cli.build_parser().parse_args(["--pack-file", path, "--sound", "chip", "-s", "5",
                                              "-o", os.path.join(self.dir.name, "song.it")])
        out, info = cli.compose_from_args(args)
        self.assertTrue(os.path.exists(out))
        self.assertEqual(info["pack"], "testpack")                   # the pack file wins over --sound
        self.assertEqual(info["style"], "snes")

    def test_mistakes_are_named_with_where_they_are(self):
        def broken(change, expect):
            pack = json.loads(json.dumps(self.pack))
            change(pack)
            with self.assertRaises(pf.PackError) as cm:
                pf.load_pack_file(self.save(pack))
            self.assertIn(expect, str(cm.exception))
        broken(lambda p: p.pop("bitcomposer_pack"), "bitcomposer_pack: must be 1")
        broken(lambda p: p.update(name="ffvi"), "name: 'ffvi' is a built-in sound")
        broken(lambda p: p.update(name="Bad Name"), "name: lower-case")
        broken(lambda p: p.update(palette="nes"), "palette: one of")
        broken(lambda p: p["habits"].update(tempo={"medum": 1}), "habits.tempo.medum: not one of slow, medium, fast")
        broken(lambda p: p["habits"].update(tempos={"slow": 1}), "habits.tempos: not a habit")
        broken(lambda p: p["habits"].update(echo=2), "habits.echo: a chance from 0 to 1")
        broken(lambda p: p["voices"].update(lead=["flute", "nosuch"]), "voices.lead[1]: 'nosuch' is neither")
        broken(lambda p: p["voices"].update(drums={"cowbell": "thump"}), "voices.drums.cowbell: not a kit piece")
        broken(lambda p: p["samples"]["flute"].update(loop=[0, 99999]), "samples.flute.loop: start and end inside")
        broken(lambda p: p["samples"]["flute"].update(file="missing.wav"), "samples.flute.file: no such file")
        broken(lambda p: p["samples"]["flute"].pop("hz"), "samples.flute: a tonal voice needs its pitch")
        broken(lambda p: p["samples"]["flute"].pop("loop"), "samples.flute.release: a release fades")
        broken(lambda p: p["samples"].update(snes_brass=p["samples"]["flute"]), "samples.snes_brass: a built-in voice")
        broken(lambda p: p.update(trims={"kick": 99}), "trims.kick: a channel volume")
        broken(lambda p: p.update(extra=1), "extra: not a pack field")

    def test_wav_sample_formats(self):
        """8, 16 and 24-bit, mono and stereo all come out as the same 16-bit voice."""
        values = [math.sin(i / 7) * 0.8 for i in range(200)]
        out = {}
        for width in (1, 2, 3):
            for channels in (1, 2):
                path = os.path.join(self.dir.name, f"w{width}{channels}.wav")
                write_wav(path, values, width=width, channels=channels)
                data, frames, rate = pf.read_wav(pf.Path(path))
                self.assertEqual((frames, rate), (200, 22050))
                out[(width, channels)] = struct.unpack("<200h", data)
        ref = out[(2, 1)]
        for k, v in out.items():
            tolerance = 512 if k[0] == 1 else 2           # 8-bit: steps of 256, written at 127/128 scale
            self.assertLessEqual(max(abs(a - b) for a, b in zip(v, ref)), tolerance, k)


if __name__ == "__main__":
    unittest.main()
