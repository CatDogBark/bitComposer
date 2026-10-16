"""Theory: scales, chords, arp colour, rhythm templates. Run with: python3 -m unittest discover -s tests"""
import unittest

from support import (it_format, melody, random, theory, unittest)  # noqa: F401



class Theory(unittest.TestCase):
    def test_progression_degrees_fit_their_scale(self):
        for scale, progs in theory.PROGRESSIONS.items():
            n = len(theory.SCALES[scale])
            for prog in progs:
                for entry in prog:
                    degree, ctype, shift = theory.unpack_chord(entry)
                    self.assertLess(degree, n, (scale, entry))
                    self.assertIn(ctype, theory.CHORD_INTERVALS)
                    self.assertIn(shift, (-1, 0, 1))

    def test_borrowed_chords_shift_root(self):
        scale = theory.build_scale(48, "major", octaves=2)
        self.assertEqual(theory.chord_root_for(48, scale, (6, "major", -1)), 48 + 10)
        self.assertEqual(theory.chord_root_for(48, scale, (4, "major")), 48 + 7)

    def test_secondary_chord_is_valid_entry(self):
        random.seed(5)
        for scale, progs in theory.PROGRESSIONS.items():
            n = len(theory.SCALES[scale])
            for prog in progs:
                for a, b in zip(prog, prog[1:] + prog[:1]):
                    degree, ctype, _ = theory.unpack_chord(theory.secondary_chord(scale, a, b))
                    self.assertLess(degree, n)
                    self.assertIn(ctype, theory.CHORD_INTERVALS)

    def test_arp_colour_tones_come_from_the_scale(self):
        from bitcomposer import arp
        for scale_name, root in (("major", 60), ("mixolydian", 62), ("phrygian", 64),
                                 ("natural_minor", 57), ("minor_pentatonic", 60)):
            scale = theory.build_scale(root, scale_name, octaves=3)
            chord = theory.build_chord(root, "minor" if "minor" in scale_name or scale_name == "phrygian" else "major")
            pcs = {n % 12 for n in scale}
            for off in arp.colour_tones(chord, scale):
                self.assertIn((root + off) % 12, pcs, (scale_name, off))
        # a coloured arp only ever plays scale tones
        random.seed(2)
        scale = theory.build_scale(60, "major", octaves=4)
        notes = arp.generate_arp([(0, 64, [60, 64, 67])], "classic_up", 1.0,
                                 scale_notes=scale, colour=True)
        self.assertTrue(notes)
        self.assertTrue(all(n % 12 in {x % 12 for x in scale} for _, n, _ in notes))
        self.assertTrue(any(n % 12 in (71, 74) for _, n, _ in notes) or
                        any(n % 12 in (11, 2) for _, n, _ in notes), "no 7th/9th appeared")

    def test_arpeggio_param(self):
        # C major voiced from E: offsets to G (3) and C (8).
        self.assertEqual(it_format.arpeggio_param(64, [60, 64, 67]), 0x38)

    def test_rhythm_templates_include_odd_offsets(self):
        self.assertTrue(any(o % 2 for t in melody.RHYTHM_TEMPLATES for o in t))


if __name__ == "__main__":
    unittest.main()
