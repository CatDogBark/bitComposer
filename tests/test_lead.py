"""The lead by salience (bitcomposer.translate.lead): the tune is the labelled melody where heard, else the most varied heard voice."""
import os
import tempfile
import time
import types
import unittest
import unittest.mock
from multiprocessing.pool import ThreadPool

from bitcomposer.translate import lead, store
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

    def test_the_features_the_rule_reads(self):
        f = lead.features_of([(0.0, 1.0, 60.0, "a"), (1.0, 1.0, 64.0, "a"), (2.0, 1.0, 67.0, "a"), (3.0, 1.0, 72.0, "a")], 8)
        self.assertAlmostEqual(f["pc"], 1.5, places=6); self.assertEqual(f["presence"], 0.5); self.assertEqual(f["median"], 65.5)


class LeadPassTests(unittest.TestCase):
    """The pass over a game (lead.run) with the rendering stood in for: four songs, the first one's render the slowest."""
    LUFS = {"a": {"whole": -10.0, 0: -8.0, 1: -12.0, 3: -3.0},      # the melody heard: the label kept
            "b": {"whole": -10.0, 0: -14.0, 1: -2.0, 3: -3.0}}      # the melody buried: the counter leads
    WAIT = {"a": 0.3, "b": 0.15, "d": 0.0}

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.spc = os.path.join(self.tmp.name, "spc")
        os.makedirs(self.spc)
        for sid in "abd":                                            # song c has no SPC file
            open(os.path.join(self.spc, f"{sid}.spc"), "w").close()
        line = lambda *midis: [(float(i), 1.0, float(m), "k") for i, m in enumerate(midis)]
        self.songs = [types.SimpleNamespace(
            sid=sid, title=f"Song {sid.upper()}", bars=[(0.0, 4.0), (4.0, 8.0)], voice_of={},
            voices=[(0, R.MELODY, None, {}), (1, R.COUNTER, None, {}), (3, R.BASS, None, {})],
            voice_notes={0: (R.MELODY, line(60, 62, 64, 65, 67, 69, 71, 72)), 1: (R.COUNTER, line(72, 71, 69, 67, 65, 64, 62, 60)),
                         3: (R.BASS, line(36, 43, 36, 43, 36, 43, 36, 43)), 9: (R.DRUMS, line(36, 38))}) for sid in "abcd"]

    def render(self, job):
        spc_path, voices, out_dir, keep = job
        sid = voices.sid
        self.assertEqual(voices.voice_notes[9], (R.DRUMS, True))     # what is handed over: each voice's role, and whether it has notes
        self.assertFalse(keep)
        time.sleep(self.WAIT[sid])
        return ("ok", dict(self.LUFS[sid])) if sid in self.LUFS else ("error", "no driver known")

    def run_pass(self, workers):
        db = store.connect(os.path.join(self.tmp.name, f"readings-{workers}.db"))
        self.addCleanup(db.close)
        for s in self.songs:
            db.execute("INSERT INTO songs (id, file, game) VALUES (?,?,?)", (s.sid, f"/elsewhere/{s.sid}.spc", "Test Quest"))
            for v, role, _, _ in s.voices:
                db.execute("INSERT INTO voices (song, voice, role) VALUES (?,?,?)", (s.sid, v, role))
        db.commit()
        said, counted, pools = [], [], []

        class Threads(ThreadPool):                                   # the pool's interface without its processes
            def __init__(self, count):
                pools.append(count)
                super().__init__(count)
        with unittest.mock.patch.object(lead.rhythm, "load", lambda db, game: (self.songs, {})), \
                unittest.mock.patch.object(lead, "_render", self.render), unittest.mock.patch.object(lead, "Pool", Threads):
            result = lead.run(db, "Test Quest", self.spc, say=said.append, progress=lambda done, total: counted.append((done, total)),
                              workers=workers)
        rows = [db.execute(f"SELECT * FROM {table} ORDER BY 1, 2, 3").fetchall() for table in ("features", "voices")]
        return result, said, counted, rows, pools

    def test_the_songs_are_settled_in_order_however_many_render_at_once(self):
        alone, together = self.run_pass(1), self.run_pass(3)
        self.assertEqual(alone[4], [])                               # one at a time: no pool
        self.assertEqual(together[4], [3])                           # three songs to render, three at once
        self.assertEqual(alone[:4], together[:4])                    # the same readings, words and counts either way
        result, said, counted, (features, voices), _ = together
        self.assertEqual(list(result), ["a", "b"])                   # heard, in the songs' order, though b's render came back first
        self.assertEqual([why for _, why, _ in result.values()], ["label kept", "relabel"])
        self.assertEqual(result["b"][2], {1: R.MELODY, 0: R.COUNTER})
        self.assertEqual([line.split(":")[0].strip() for line in said], ["Song A", "Song B", "Song C", "Song D"])
        self.assertIn("no SPC file", said[2]); self.assertIn("not rendered (no driver known)", said[3])
        self.assertEqual(counted, [(0, 4), (1, 4), (2, 4), (3, 4), (4, 4)])   # every song counted, heard or not
        self.assertIn(("b", 0, R.COUNTER, None, None, None), voices); self.assertIn(("b", 1, R.MELODY, None, None, None), voices)
        self.assertIn(("a", 0, R.MELODY, None, None, None), voices)
        self.assertIn(("b", "lead", "now_melody", 1.0), features); self.assertIn(("a", "render", "voice_lufs_3", -3.0), features)
        self.assertEqual(len(features), 3 + 3 + 2)                   # each heard voice's loudness, and b's two lead rows

    def test_a_dry_run_stores_nothing(self):
        db = store.connect(os.path.join(self.tmp.name, "dry.db"))
        self.addCleanup(db.close)
        db.execute("INSERT INTO songs (id, file, game) VALUES ('b', 'b.spc', 'Test Quest')")
        with unittest.mock.patch.object(lead.rhythm, "load", lambda db, game: (self.songs[1:2], {})), \
                unittest.mock.patch.object(lead, "_render", self.render):
            result = lead.run(db, "Test Quest", self.spc, dry_run=True, say=lambda line: None, workers=1)
        self.assertEqual(result["b"][1], "relabel")
        self.assertEqual(db.execute("SELECT count(*) FROM features").fetchone()[0], 0)


if __name__ == "__main__":
    unittest.main()


class LayerShareTests(unittest.TestCase):
    def test_every_share_has_a_class(self):
        from bitcomposer.translate import rhythm
        self.assertEqual([rhythm.layer_share_class(x) for x in (0.0, 0.39, 0.4, 0.79, 0.8, 9.0, 40.0)], ["sparse", "sparse", "half", "half", "full", "full", "full"])
