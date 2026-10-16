"""The file: determinism, IT header and samples, tempo fields, CLI naming. Run with: python3 -m unittest discover -s tests"""
import unittest

from support import (_gen, _read, analyze, compose_song, composer, it_format, names, os, pattern, struct, sys, tempfile, unittest)  # noqa: F401



class Determinism(unittest.TestCase):
    def test_same_seed_same_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, _ = _gen(tmp, 11)
            data_a = _read(a)
            b, _ = _gen(tmp, 11)
            self.assertEqual(data_a, _read(b))

    def test_different_seeds_differ(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, _ = _gen(tmp, 1)
            b, _ = _gen(tmp, 2)
            self.assertNotEqual(_read(a), _read(b))


class FileFormat(unittest.TestCase):
    def test_title_and_message(self):
        with tempfile.TemporaryDirectory() as tmp:
            path, info = _gen(tmp, 3)
            m = analyze.IT(path)
            self.assertEqual(m.name, info["title"])
            self.assertLessEqual(len(info["title"]), names.MAX_TITLE)
            self.assertTrue(m.special & 1, "message flag not set")
            msg_len, msg_off = struct.unpack("<HI", m.raw[0x36:0x3C])
            msg = m.raw[msg_off:msg_off + msg_len].decode("ascii").split("\r")
            self.assertEqual(msg[0], info["title"])
            self.assertIn(f"{info['tempo']} BPM", msg[1])
            self.assertIn(info["style"], msg[2])
            self.assertTrue(any(ln.startswith("seed 3") for ln in msg), msg)
            if info["echo"]:
                self.assertTrue(any(ln.startswith("echo: ") for ln in msg), msg)
            self.assertEqual(msg[-1], "layout: " + ",".join(pattern.CHANNEL_ROLES))
            # titles differ between seeds and depend only on the seed
            _, info_b = _gen(tmp, 4)
            self.assertNotEqual(info["title"], info_b["title"])
            self.assertEqual(compose_song(seed=3)["name"], info["title"])

    def test_header_and_channel_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            path, info = _gen(tmp, 3)
            m = analyze.IT(path)
            self.assertEqual(m.name, info["title"])
            self.assertEqual(m.patnum, info["num_patterns"])
            self.assertEqual(len(m.played()), info["num_orders"])
            # 14 channels enabled, the rest flagged disabled (bit 7 of the pan byte).
            pans = m.raw[0x40:0x80]
            self.assertTrue(all(p < 128 for p in pans[:pattern.NUM_CHANNELS]))
            self.assertTrue(all(p & 128 for p in pans[pattern.NUM_CHANNELS:]))
            self.assertEqual(len(composer.CHANNEL_VOLUMES), pattern.NUM_CHANNELS)

    def test_sample_headers_consistent(self):
        song = compose_song(seed=4, style_pref="snes")
        for s in song["samples"]:
            self.assertEqual(len(s.data), 2 * s.length, s.name)
            self.assertLessEqual(s.loop_end, s.length, s.name)
            self.assertLessEqual(s.loop_start, s.loop_end, s.name)
            self.assertGreater(s.c5_speed, 8000)

    def test_no_orphan_patterns(self):
        """Every pattern in the file is reachable from the order list."""
        for seed in (1, 2, 3):
            song = compose_song(seed=seed)
            self.assertEqual(set(song["orders"]), set(range(len(song["patterns"]))))


class Tempo(unittest.TestCase):
    def test_bpm_roundtrip(self):
        for bpm in (80, 100, 125, 150, 180):
            for speed in (4, 5, 6):
                t = it_format.bpm_to_it_tempo(bpm, speed)
                back = it_format.it_tempo_to_bpm(t, speed)
                self.assertAlmostEqual(back, bpm, delta=bpm * 0.03)

    def test_audible_tempo_in_range(self):
        with tempfile.TemporaryDirectory() as tmp:
            for seed in range(1, 9):
                path, info = _gen(tmp, seed)
                r = analyze.analyze(path)
                self.assertTrue(75 <= r["bpm"] <= 185, (seed, r["bpm"]))
                self.assertAlmostEqual(r["bpm"], info["tempo"], delta=1.0)


class CliNaming(unittest.TestCase):
    def test_title_names_with_suffix_and_collisions(self):
        from bitcomposer import cli
        with tempfile.TemporaryDirectory() as tmp:
            import contextlib, io
            argv = sys.argv
            try:
                for extra in ([], ["--suffix", " (auto)"], []):
                    sys.argv = ["bitcomposer", "-s", "3", "-d", tmp, *extra]
                    with contextlib.redirect_stdout(io.StringIO()):
                        cli.main()
            finally:
                sys.argv = argv
            title = compose_song(seed=3)["name"]
            names = sorted(os.listdir(tmp))
            self.assertEqual(names, sorted([f"{title}.it", f"{title} (auto).it", f"{title} 2.it"]))


if __name__ == "__main__":
    unittest.main()


class SongMessage(unittest.TestCase):
    """The machine-readable lines players read: voices by role, what the song drew."""

    def test_message_names_every_voice_and_the_draws(self):
        song = compose_song(seed=5, style_pref="snes", pack="megamanx")
        lines = {ln.split(":", 1)[0]: ln.split(":", 1)[1].strip() for ln in song["message"].splitlines() if ":" in ln}
        voices = dict(item.split("=", 1) for item in lines["voices"].split(","))
        for role in ("melody", "harmony", "bass", "arp", "kick", "snare", "hihat", "tom", "crash", "open_hihat"):
            self.assertEqual(voices[role], song["info"]["instruments"][role], role)
        drew = dict(item.split("=", 1) for item in lines["drew"].split(","))
        self.assertEqual(drew["sound"], "megamanx")
        self.assertEqual(drew["form"], song["info"]["song_form"])
        self.assertEqual(drew["harmony"], song["info"]["harmony_mode"])
        self.assertIn("tempo", drew)
        self.assertEqual(lines["layout"].split(","), list(pattern.CHANNEL_ROLES))

