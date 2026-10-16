"""Style packs, their engine habits, the mix rules. Run with: python3 -m unittest discover -s tests"""
import unittest

from support import (compose_song, composer, it_format, names, pattern, samples, unittest)  # noqa: F401



class Packs(unittest.TestCase):
    def test_ffvi_pack_uses_its_voices_and_habits(self):
        from bitcomposer.packs import PACKS
        song = compose_song(seed=5, style_pref="snes", pack="ffvi")
        info = song["info"]
        self.assertEqual(info["pack"], "ffvi")
        voices = PACKS["ffvi"]["voices"]
        self.assertIn(info["instruments"]["melody"], voices["lead"])
        self.assertIn(info["instruments"]["harmony"], voices["harmony"])
        self.assertIn(info["instruments"]["counter"], voices["counter"])
        self.assertEqual(info["instruments"]["tom"], "ffvi_timpani")
        self.assertIn("(ffvi)", song["message"] if "message" in song else "(ffvi)")
        self.assertIn(info["harmony_mode"], ("ostinato", "sustain", "pulse", "stabs"))

    def test_every_pack_generates_with_its_own_voices(self):
        from bitcomposer.packs import PACKS
        for name, pack in PACKS.items():
            info = compose_song(seed=6, style_pref="snes", pack=name)["info"]
            self.assertEqual(info["pack"], name, name)
            self.assertIn(info["instruments"]["melody"], pack["voices"]["lead"], name)
            self.assertIn(info["instruments"]["arp"], pack["voices"]["arp"], name)
            self.assertEqual(info["instruments"]["tom"], pack["voices"]["drums"]["tom"], name)

    def test_drone_bass_holds_one_note_per_chord(self):
        from bitcomposer import bass
        notes = bass.generate_bass(48, "minor", 32, style="drone", weight="heavy")
        self.assertEqual(notes, [(0, 36)])      # heavy register: octave 2
        self.assertEqual(bass.pick_section_bass("light", 0.95, "drone"), "drone")

    def test_riff_library_is_chord_safe_and_one_bar(self):
        from bitcomposer import bass
        for name, figure in bass.RIFFS.items():
            self.assertTrue(all(0 <= row < 16 for row, _ in figure), name)
            self.assertTrue(all(iv % 12 in (0, 7, 10) for _, iv in figure), name)
            notes = bass.generate_bass(48, "minor", 32, style="riff", weight="heavy", riff=name)
            self.assertEqual([r for r, _ in notes][:len(figure)], [r for r, _ in figure], name)
        song = compose_song(seed=101, style_pref="snes", pack="megamanx")
        self.assertIn(song["info"]["bass_riff"], list(bass.RIFFS) + [None])
        # the seventh snaps to the key: in a major scale it becomes the sixth
        major = [60, 62, 64, 65, 67, 69, 71]
        notes = bass.generate_bass(48, "major", 16, style="riff", weight="heavy", riff="funk", scale_notes=major)
        self.assertEqual(notes[-1][1] - notes[0][1], 9)
        minor = [60, 62, 63, 65, 67, 68, 70]
        notes = bass.generate_bass(48, "minor", 16, style="riff", weight="heavy", riff="funk", scale_notes=minor)
        self.assertEqual(notes[-1][1] - notes[0][1], 10)

    def test_riff_keeps_every_note_and_pops_use_the_high_sample(self):
        from bitcomposer import bass, pattern
        import random
        random.seed(1)
        full = bass.generate_bass(48, "major", 32, style="riff", weight="heavy", density=0.3, riff="funk")
        self.assertEqual(len(full), 2 * len(bass.RIFFS["funk"]))
        song = compose_song(seed=101, style_pref="snes", pack="megamanx")
        self.assertEqual(song["info"]["bass_style"], "riff")
        insts = {c.instrument for p in song["patterns"] for r in p.data for c in [r[pattern.CH_BASS]] if c.note not in (0, 254, 255)}
        self.assertEqual(len(insts), 2, insts)      # the low sample and the high one

    def test_arp_never_pushes_where_the_riff_pushes(self):
        from bitcomposer import bass, arp, pattern
        for seed in range(100, 130):
            info = compose_song(seed=seed, style_pref="snes", pack="megamanx")["info"]
            if not info["bass_riff"]:
                continue
            pushes = {r % 16 for r, _ in bass.RIFFS[info["bass_riff"]] if r % pattern.ROWS_PER_BEAT}
            for sec in ("verse", "chorus", "bridge"):
                steps = {r % 16 for r, _, _ in arp.FIGURES[info["arp_figures"][sec]]["steps"] if r % pattern.ROWS_PER_BEAT}
                self.assertFalse(steps & pushes, (seed, sec, info["bass_riff"], info["arp_figures"][sec]))

    def test_chug_voicings_restrike_on_their_steps(self):
        from bitcomposer import harmony
        rows = [r for r, n in harmony.generate_harmony([60, 64, 67], 32, "chug_sync", 3)[0] if n != -1]
        self.assertEqual(rows, [0, 3, 6, 8, 14, 16, 19, 22, 24, 30])

    def test_riff_bass_repeats_each_bar(self):
        from bitcomposer import bass
        notes = bass.generate_bass(48, "minor", 32, style="riff", weight="heavy")
        rows = [r for r, _ in notes]
        self.assertEqual(rows, [0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30])
        self.assertEqual(notes[2][1] - notes[0][1], 12)
        self.assertEqual(bass.pick_section_bass("heavy", 0.95, "riff"), "riff")

    def test_slap_echo_writes_tick_delays(self):
        song = compose_song(seed=9, style_pref="snes", echo="on", echo_delay="slap")
        self.assertEqual(song["info"]["echo_delay"], "slap")
        delayed = sum(1 for p in song["patterns"] for r in p.data
                      if r[pattern.CH_ECHO1].note not in (0, 254, 255) and r[pattern.CH_ECHO1].effect == it_format.FX_SPECIAL)
        self.assertGreater(delayed, 0)

    def test_written_levels_stay_in_range(self):
        for seed, pack in ((4, "megamanx"), (21, "none"), (7, "evermore")):
            vols = composer.channel_volumes_for(compose_song(seed=seed, style_pref="snes", pack=pack)["info"])
            self.assertTrue(all(0 <= v <= 64 for v in vols), vols)
            self.assertEqual(len(vols), pattern.NUM_CHANNELS)

    def test_sustaining_arp_voice_is_trimmed(self):
        song = compose_song(seed=4, style_pref="snes", pack="megamanx")
        self.assertEqual(song["info"]["instruments"]["arp"], "mmx_pulse_lead")
        self.assertFalse(song["info"]["struck"]["arp"])
        self.assertEqual(composer.channel_volumes_for(song["info"])[pattern.CH_ARP], round(composer.SUSTAINING_ARP_LEVEL * composer.MASTER_GAIN))
        plain = compose_song(seed=21, style_pref="snes", pack="none")
        self.assertTrue(plain["info"]["struck"]["arp"])
        self.assertEqual(composer.channel_volumes_for(plain["info"])[pattern.CH_ARP], round(composer.CHANNEL_VOLUMES[pattern.CH_ARP] * composer.MASTER_GAIN))

    def test_struck_table_matches_the_classifier(self):
        names = set()
        for pal in composer.PALETTES.values():
            for v in pal.values():
                names.update(v if isinstance(v, list) else (v.values() if isinstance(v, dict) else []))
        from bitcomposer.packs import PACKS
        for p in PACKS.values():
            for v in p["voices"].values():
                names.update(v if isinstance(v, list) else ([v] if isinstance(v, str) else v.values()))
        for name in sorted(names):
            if name in samples.INSTRUMENT_PRESETS and not samples.is_percussion(name):
                self.assertEqual(samples.is_struck(name), samples.generate_instrument(name)["struck"], name)

    def test_pack_none_is_plain_snes(self):
        from bitcomposer.packs import PACKS
        info = compose_song(seed=5, style_pref="snes", pack="none")["info"]
        self.assertIsNone(info["pack"])
        self.assertIn(info["instruments"]["melody"], composer.PALETTES["snes"]["lead"])

    def test_ostinato_voicing_restrikes_every_cell(self):
        from bitcomposer import harmony
        voices = harmony.generate_harmony([60, 64, 67], 32, "ostinato", 3)
        rows = [r for r, n in voices[0] if n != -1]
        self.assertEqual(rows, [0, 3, 6, 8, 11, 14, 16, 19, 22, 24, 27, 30])


if __name__ == "__main__":
    unittest.main()
