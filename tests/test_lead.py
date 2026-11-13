"""The lead by salience (bitcomposer.translate.lead): the tune is the labelled melody where heard, else the most varied heard voice."""
import unittest

from bitcomposer.translate import lead
from bitcomposer.translate import roles as R


class LeadTests(unittest.TestCase):
    def voices(self, mel_lufs, ctr_lufs, acc_lufs=-20.0):
        return {0: {"role": R.MELODY, "lufs": mel_lufs, "pc": 2.8, "presence": 0.6, "median": 70},
                1: {"role": R.COUNTER, "lufs": ctr_lufs, "pc": 2.6, "presence": 0.7, "median": 74},
                2: {"role": R.ACCOMP, "lufs": acc_lufs, "pc": 1.2, "presence": 0.9, "median": 62},
                3: {"role": R.BASS, "lufs": -3.0, "pc": 2.2, "presence": 0.9, "median": 40}}

    def test_a_heard_melody_keeps_the_lead(self):
        self.assertEqual(lead.lead_of(self.voices(-8.0, -2.0)), (0, "label kept"))          # 6 dB under the loudest: heard
        self.assertEqual(lead.relabel_plan(self.voices(-8.0, -2.0), 0), {})

    def test_a_buried_melody_gives_the_lead_to_the_most_varied_heard_voice(self):
        v = self.voices(-14.0, -2.0)
        self.assertEqual(lead.lead_of(v), (1, "relabel"))                                   # 11 dB under the bass (-3): the counter leads
        self.assertEqual(lead.relabel_plan(v, 1), {1: R.MELODY, 0: R.COUNTER})              # the old melody is the counter-line
        v2 = self.voices(-14.0, -2.0); v2[4] = {"role": R.COUNTER, "lufs": -12.0, "pc": 2.5, "presence": 0.5, "median": 66}
        self.assertEqual(lead.relabel_plan(v2, 1), {1: R.MELODY, 0: R.ACCOMP})             # a counter remains: the old melody accompanies

    def test_the_bass_never_leads_and_a_pad_is_passed_over(self):
        v = self.voices(-14.0, -14.0, acc_lufs=-1.0)                                        # only the pad (pc 1.2) and the bass are heard
        self.assertEqual(lead.lead_of(v), (2, "relabel"))                                   # the pad, over the bass: heard voices short of variety still beat nothing
        v = self.voices(-14.0, -14.0, acc_lufs=-14.0)
        self.assertEqual(lead.lead_of(v)[1], "nothing heard")                               # nothing but the bass within the window: the label stands
        self.assertEqual(lead.lead_of({3: v[3]}), (None, "no melody"))

    def test_whether_the_pass_has_run_on_a_games_readings(self):
        """The tables' source keeps what `passed` says: a game read again has no voice heard and no tune moved, and its
        tables count the reader's label (rounds 102 to 151 were counted so, the pass not run after the re-read)."""
        import sqlite3
        db = sqlite3.connect(":memory:")
        db.execute("CREATE TABLE songs (id INTEGER PRIMARY KEY, game TEXT)")
        db.execute("CREATE TABLE features (song INTEGER, source TEXT, name TEXT, value REAL)")
        db.executemany("INSERT INTO songs VALUES (?, ?)", [(1, "a"), (2, "a"), (3, "a"), (4, "b")])
        self.assertEqual(lead.passed(db, "a"), {"heard": 0, "relabelled": 0})
        db.executemany("INSERT INTO features VALUES (?, ?, ?, ?)",
                       [(1, "render", "voice_lufs_0", -20.0), (1, "render", "voice_lufs_3", -31.0), (2, "render", "voice_lufs_1", -18.0),
                        (2, "lead", "was_melody", 1.0), (2, "lead", "now_melody", 4.0), (3, "echo", "delay", 5.0),
                        (4, "render", "voice_lufs_0", -9.0), (4, "lead", "now_melody", 2.0)])
        self.assertEqual(lead.passed(db, "a"), {"heard": 2, "relabelled": 1})                # a song counts once, whatever its voices
        self.assertEqual(lead.passed(db, "b"), {"heard": 1, "relabelled": 1})
        self.assertEqual(lead.passed(db), {"heard": 3, "relabelled": 2})                     # every game's: the library's

    def test_the_features_the_rule_reads(self):
        f = lead.features_of([(0.0, 1.0, 60.0, "a"), (1.0, 1.0, 64.0, "a"), (2.0, 1.0, 67.0, "a"), (3.0, 1.0, 72.0, "a")], 8)
        self.assertAlmostEqual(f["pc"], 1.5, places=6); self.assertEqual(f["presence"], 0.5); self.assertEqual(f["median"], 65.5)


if __name__ == "__main__":
    unittest.main()


class LayerShareTests(unittest.TestCase):
    def test_every_share_has_a_class(self):
        from bitcomposer.translate import rhythm
        self.assertEqual([rhythm.layer_share_class(x) for x in (0.0, 0.39, 0.4, 0.79, 0.8, 9.0, 40.0)], ["sparse", "sparse", "half", "half", "full", "full", "full"])
