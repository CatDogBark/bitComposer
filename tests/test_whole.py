import os
import math
import random
import tempfile
import unittest
from fractions import Fraction

from bitcomposer.translate import harmony, pack, rhythm, tables, vocab, whole, writer
from bitcomposer.translate import roles as R


class ChordNamesTests(unittest.TestCase):
    def test_a_numeral_goes_back_to_its_chord(self):
        for mode in ("major", "minor"):
            for tonic in (0, 3, 7, 10):
                for root in range(12):
                    for shape in harmony.SHAPES:
                        name = vocab.numeral(root, tonic, mode, shape)
                        self.assertEqual(whole.chord_of(name, tonic, mode), (root, shape), (name, tonic, mode))
        self.assertIsNone(whole.chord_of(rhythm.NO_CHORD, 0, "major"))
        self.assertIsNone(whole.chord_of("start", 0, "major"))


class PlanTests(unittest.TestCase):
    def test_a_plan_with_no_tables_is_consistent(self):
        p = whole.plan({}, seed=3, game="test")
        self.assertEqual(p.parts[0][0], 0)
        for i, (bar, n, of, label) in enumerate(p.parts):
            if i:
                self.assertEqual(bar, p.parts[i - 1][0] + p.parts[i - 1][1])
            if of is not None:
                self.assertLess(of, i)
                self.assertEqual(n, p.parts[of][1])
                self.assertEqual(label, p.parts[of][3])
        self.assertEqual(len(p.chords), p.bars)
        self.assertTrue(all(c is not None for c in p.chords))
        self.assertEqual(sorted(p.plays), sorted(p.band))
        self.assertTrue(all(len(v) == p.bars for v in p.plays.values()))
        self.assertLessEqual(sum(p.voices.values()), whole.VOICES)
        self.assertTrue(any("assumed" in line for line in p.log))

    def test_the_form_follows_the_tables(self):
        songs = ("s", "t")                                   # two songs: a plan's draw passes over a level one song alone stands behind
        units = [tables.Unit(sid, "g", "3", {"part": "form"}) for sid in songs] + [tables.Unit(sid, "g", "long", {"part": "form"}) for sid in songs]
        sizes = tables.Table(("part",), "sizes", votes=tables.SHARES).fit(units[:2])
        habits = tables.Table(("part",), "length habits", votes=tables.SHARES).fit(units[2:])
        form = tables.Table(("part", "meter", "index"), "form", votes=tables.SHARES).fit([
            tables.Unit(sid, "g", kind, {"part": "form", "meter": 4, "index": i})
            for sid in songs for i, kind in ((1, "new"), (2, "new"), (3, "back"))])
        lengths = tables.Table(("part", "meter", "habit"), "lengths", votes=tables.SHARES).fit([
            tables.Unit(sid, "g", "8", {"part": "form", "meter": 4, "habit": "long"}) for sid in songs])
        log = []
        parts = whole.plan_form({"sizes": sizes, "length_habits": habits, "form": form, "lengths": lengths}, random.Random(1), log)
        self.assertEqual([p[3] for p in parts], ["A", "B", "A"])
        self.assertEqual([p[1] for p in parts], [8, 8, 8])
        self.assertEqual(parts[2][2], 0)
        self.assertEqual(whole.loop_bar_of(parts), 0)                   # A comes back: no intro
        self.assertEqual(whole.loop_bar_of([(0, 4, None, "A"), (4, 8, None, "B"), (12, 8, 1, "B")]), 4)   # A never returns: the loop after it

    def test_the_chords_and_textures_of_a_repeated_part_are_kept(self):
        units = [tables.Unit("s", "g", o, {"part": R.HARMONY, "mode": "major", "previous": p})
                 for o, p in (("I", rhythm.START), ("IV", "I"), ("V", "IV"), ("I", "V"))]
        chords = tables.Cache.fit(units, ("part", "mode", "previous"), name="chords", votes=tables.SHARES)
        parts = [(0, 4, None, "A"), (4, 4, None, "B"), (8, 4, 0, "A")]
        names, chords_ = whole.plan_chords({"chords": chords}, parts, 0, 0, "major", random.Random(2), [])
        self.assertEqual(names[:4], names[8:])
        self.assertEqual(chords_[0], (0, ""))
        tunits = [tables.Unit("s", "g", o, {"part": rhythm.ARRANGEMENT, "habit": "-", "form": f, "index": i, "previous": p})
                  for o, f, i, p in (("no drums melody", "first", 1, rhythm.START), ("all", "middle", 2, "no drums melody"), ("no harmony", "last", 3, "all"))]
        texture = tables.Table(("part", "habit", "form", "previous"), "part textures", votes=tables.SHARES).fit(tunits)
        textures, plays = whole.plan_texture({"part_textures": texture}, parts, ["bass", "drums", "melody"], random.Random(2), [])
        self.assertEqual(textures[:4], textures[8:])
        self.assertEqual(len(set(textures[:4])), 1)                   # a texture a part
        self.assertEqual(textures[0], "bass")                         # the first part: no drums, no melody
        self.assertEqual(textures[4], "bass drums melody")
        self.assertEqual(sorted(plays), ["bass", "drums", "melody"])
        t = tables.Table(("part",), "x", votes=tables.SHARES, discount=0.75).fit([tables.Unit(str(i), "g", f"o{i}", {"part": "p"}) for i in range(6)])
        self.assertTrue(all(t.draw(("p",), random.Random(i), floored=False).startswith("o") for i in range(40)))


class WholeSongTests(unittest.TestCase):
    def test_a_whole_song_from_a_generated_songs_tables_is_written_rendered_and_read_back(self):
        from bitcomposer.composer import compose_song
        from bitcomposer.packs import PACKS
        from bitcomposer.spc import convert
        from bitcomposer.translate import harness, packtables
        song = compose_song(seed=5, pack="ffvi")
        ctx = harness.load_generated(song, "seed 5", "test", seconds=40.0)
        self.assertIsNotNone(ctx)
        models = packtables.read(packtables.build(ctx.db, "test"))
        for name in ("rhythm", "bass", "chords", "texture", "balance", "keys", "tempos", "registers", "form", "lengths", "sizes"):
            self.assertIn(name, models)
        out = whole.compose(models, PACKS["ffvi"], set(), "ffvi", seed=1, game="test", max_bars=32)
        p, written = out["plan"], out["written"]
        self.assertTrue(p.band)
        if "pair_recall" in models and "melody" in written:                # round 40: the tune's urn at the pair logs its draws
            self.assertTrue(any(line.startswith("pairs (pair_recall)") for line in written["melody"].log), written["melody"].log)
        self.assertLessEqual(p.bars, 32)
        for role in p.band:
            self.assertIn(role, written, role)
            if any(p.plays[role]):
                self.assertTrue(written[role].notes, role)
        score = out["score"]
        self.assertGreater(len(score.notes), 0)
        self.assertEqual(score.voices, sum(p.voices[r] for r in out["first"]))
        self.assertTrue(all(0 <= n.voice < score.voices for n in score.notes))
        self.assertTrue(all(n.end is not None and n.end >= n.start for n in score.notes))
        self.assertGreater(score.seconds, p.bars * 4 * 60.0 / p.bpm)          # the loop once more
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "whole.it")
            convert.render(score, path)
            self.assertGreater(os.path.getsize(path), 1000)
        back = out["read"]
        self.assertIsNotNone(back)
        self.assertEqual(len(back.bars), p.bars)
        self.assertEqual(sorted(back.notes), sorted(r for r in p.band if r in written and written[r].notes))
        m = out["measures"]
        self.assertEqual(m["bars"], p.bars)
        if R.MELODY in back.notes:
            self.assertIn("tune", m)
            self.assertLessEqual(m["tune"]["chord_tones"], 1.0)

    def test_a_voice_beside_a_line_follows_the_tokens_stretches(self):
        """Round 90: a voice beside a line whose token entry says what it does beside which part, stretch by stretch
        ("dm-12x4>o": the tune an octave under for four bars from the song's first, then its own), is written so after
        every line is in place: in the doubling bars its notes are the melody's line again at the interval, in the scale;
        in its own bars the notes its layer word gave it (here apart +8). Kefka's three "counter" channels double its tune
        in octaves and thirds for whole stretches; read whole, they were written as a three-voice block of their own at the
        song's loudest level over a one-voice tune (Song Check 72's The Sleeping Observatory)."""
        from bitcomposer.composer import compose_song
        from bitcomposer.translate import harness, packtables
        song = compose_song(seed=5, pack="ffvi")
        ctx = harness.load_generated(song, "seed 5", "test", seconds=40.0)
        models = packtables.read(packtables.build(ctx.db, "test"))
        p = whole.plan(models, 3, "g", max_bars=16)
        self.assertIn(R.MELODY, p.band)
        role = "accompaniment"
        if role not in p.band:
            p.band.append(role); p.weights[role] = "half"
        for r in (role, R.MELODY):
            p.plays[r] = [True] * p.bars
        p.textures = [t + " " + role for t in p.textures]
        p.registers[role] = (56, 64); p.bounds[role] = (56, 64); p.sounds[role] = 0.8
        p.habits[role] = p.habits.get(role) or "medium mixed"
        p.extras[role] = {**(p.extras.get(role) or {}), "richness": "full", "motion": "block", "layers": ["apart +8 like"], "layer": "apart +8 like"}
        p.voices[role] = 2
        p.bounds[f"{role}:1"] = whole.voice_bounds(p, role, "apart +8 like", (44, 92))
        p.layer_ranges[role] = [(44, 92)]                   # where the token song plays the voice's sample: the double folds into it (round 95)
        p.layer_relations[role] = ["dm-12x4>o"]
        written = whole.write(p, whole.song_of(p), models, 3)
        tune = {round(n[0], 3): n[2] for n in written[R.MELODY].notes if n[3] == 0}
        voice = [n for n in written[role].notes if n[3] == 1]
        early = [n for n in voice if n[0] < 16 - 1e-6]
        late = [n for n in voice if n[0] >= 16 - 1e-6]
        self.assertTrue(early and late, written[role].log)
        doubled = [n for n in early if round(n[0], 3) in tune and abs(tune[round(n[0], 3)] - 12 - n[2]) <= 1]
        self.assertGreaterEqual(len(doubled), 0.8 * len(early), (early[:8], written[role].log))
        self.assertTrue(any("voice 2 double the melody's line at -12 in bars 1-4" in l for l in written[role].log), written[role].log)
        self.assertTrue(all(60 <= n[2] <= 76 for n in late), sorted({n[2] for n in late}))      # its own bars: the apart voice in its span

    def test_an_apart_voice_is_written_at_its_offset_and_a_pedal_line_shares_its_note(self):
        """Round 70: an apart voice of an upper part is written in its own span, the line's span at the layer word's
        offset within the range the game plays its sample over (render.voice_bounds, plan.bounds["role:v"]), so it
        sounds at its offset from the line when both sound (round 69 had measured Whole 166's "apart +8" voices at a
        median 0 semitones from the line: every apart voice folded into one `:second` bound, the line's own band). And
        a pedal line (a one-pitch register, as a game plays a drum sample as a rhythmic chord part) shares its note
        with the voices beside it, so they can take their interval from it (Whole 167's apart voice had written 0 notes)."""
        import statistics
        from bitcomposer.composer import compose_song
        from bitcomposer.translate import harness, packtables
        song = compose_song(seed=5, pack="ffvi")
        ctx = harness.load_generated(song, "seed 5", "test", seconds=40.0)
        models = packtables.read(packtables.build(ctx.db, "test"))
        p = whole.plan(models, 3, "g", max_bars=16)
        p.bounds["accompaniment"] = (56, 64)
        self.assertEqual(whole.voice_bounds(p, "accompaniment", "apart +8 like", (44, 92)), (64, 72))
        self.assertEqual(whole.voice_bounds(p, "accompaniment", "apart -8 sparser", (44, 92)), (48, 56))
        self.assertEqual(whole.voice_bounds(p, "accompaniment", "alternating", (44, 92)), (56, 64))
        self.assertEqual(whole.voice_bounds(p, "accompaniment", "apart +8 like", None), (64, 72))       # nothing known of the sample
        self.assertEqual(whole.voice_bounds(p, "accompaniment", "apart +8 like", (40, 60)), (52, 60))   # wholly above its range: its top edge
        self.assertEqual(whole.voice_bounds(p, "accompaniment", "apart -12 like", (60, 80)), (60, 68))  # wholly under: its bottom edge
        p.bounds.pop("accompaniment")
        role = "accompaniment"
        if role not in p.band:
            p.band.append(role); p.weights[role] = "half"; p.plays[role] = [True] * p.bars
            for k, t in enumerate(p.textures):
                p.textures[k] = t + " " + role
        p.registers[role] = (56, 64); p.bounds[role] = (56, 64); p.sounds[role] = 0.8
        p.habits[role] = p.habits.get(role) or "medium mixed"
        p.extras[role] = {**(p.extras.get(role) or {}), "richness": "full", "motion": "block", "layers": ["apart +8 like"], "layer": "apart +8 like"}
        p.voices[role] = 2
        p.bounds[f"{role}:1"] = whole.voice_bounds(p, role, "apart +8 like", (44, 92))
        p.layer_relations.pop(role, None)                   # the generated song's own token says its chord voices run parallel to their line
        written = whole.write(p, whole.song_of(p), models, 3)   # (round 90), and the writer would follow it over the apart word under test
        notes = written[role].notes
        line = [n for n in notes if n[3] == 0]
        voice = [n for n in notes if n[3] == 1]
        self.assertTrue(line and voice, written[role].log)
        offsets = []                                        # the voice's pitch less the line's, a twelfth of a beat at a time where both sound
        step = 1 / 12
        for k in range(int(p.bars * 4 / step)):
            t = k * step
            a = [n[2] for n in line if n[0] - 1e-6 <= t < n[1] - 1e-6]
            b = [n[2] for n in voice if n[0] - 1e-6 <= t < n[1] - 1e-6]
            if a and b:
                offsets.append(min(b) - min(a))
        self.assertTrue(offsets)
        self.assertAlmostEqual(statistics.median(offsets), 8, delta=2, msg=(offsets[:40], written[role].log))
        self.assertTrue(all(62 <= n[2] <= 74 for n in voice), sorted({n[2] for n in voice}))     # its span, but for the clash rule's step aside
        # a pedal line shares its note with the voice beside it: the voice writes
        p.registers[role] = (56, 56); p.bounds[role] = (56, 56)
        written = whole.write(p, whole.song_of(p), models, 3)
        line = [n for n in written[role].notes if n[3] == 0]
        voice = [n for n in written[role].notes if n[3] == 1]
        self.assertTrue(line and all(n[2] == 56.0 for n in line))
        self.assertTrue(voice, written[role].log)


class ChordFigureTests(unittest.TestCase):
    """Round 96: the chord parts' tone figures and degrees, the counter's chord-tone share, a figure mark the chord lacks,
    and a relation stretch's own edge bars."""

    def _chord_song(self, bars: int = 4, shape: str = ""):
        from bitcomposer.translate import vocab
        spans = [(4.0 * k, 4.0 * k + 4.0) for k in range(bars)]
        return rhythm.Song("t", 4, 12, spans, [vocab.Span(0.0, 4.0 * bars, 0, shape, 1.0)], notes={}, sid="s", game="g", tonic=0, mode="major")

    def test_a_chord_parts_line_leaves_the_chord_where_its_tone_figure_says(self):
        """The tone_figures word counts each bar of a chord part's line as its onsets' tone classes against the chord sounding
        (c a chord tone, x off it), by the part, the onset count and the line's pattern; the tone_degrees word the degree an
        off-chord note sits at over the root, by the part and the chord's shape. The upper writer draws both under the line's
        bar and plays the x onsets at the drawn degree, nearest the voicing tone each replaces; without the words the line
        holds the voicing's tones alone, as it had (FFVI's accompaniment line leaves the chord on a quarter of its notes, the
        written one on 0.07, and those from marks the chord lacked)."""
        import importlib
        from fractions import Fraction
        from bitcomposer.translate import tables, writer
        upper_mod = importlib.import_module("bitcomposer.translate.writer.upper")
        s = self._chord_song()
        s.notes["accompaniment"] = [(4.0 * k + i, 0.9, m, "a") for k in range(4) for i, m in enumerate((60.0, 64.0, 67.0, 69.0))]   # C E G A: the A off the chord
        s.voice_notes = {3: ("accompaniment", s.notes["accompaniment"])}
        units = rhythm.tone_figure_units([s])
        self.assertEqual([u.outcome for u in units], ["c c c x"] * 4)
        self.assertEqual(units[0].values, {"part": "accompaniment", "tier": "some", "onsets": "4", "line": "0 1 2 3"})   # a quarter of its onsets off: "some"
        self.assertEqual([(u.outcome, u.values) for u in rhythm.tone_tier_units([s])], [("some", {"part": "accompaniment"})])
        self.assertEqual([rhythm.tone_tier_of(x) for x in (0.0, 0.09, 0.1, 0.29, 0.3, 1.0)], ["rare", "rare", "some", "some", "many", "many"])
        degrees = rhythm.tone_degree_units([s])
        self.assertEqual([(u.outcome, u.values) for u in degrees], [("9", {"part": "accompaniment", "shape": "major", "previous": rhythm.START})] * 4)
        s.notes["accompaniment"][3] = (3.0, 0.9, 71.0, "a")                                   # the first bar C E G B: the B is a second off-chord onset after none
        s.notes["accompaniment"][2] = (2.0, 0.9, 69.0, "a")                                   # ... no: C E A B, the A then the B, chained
        self.assertEqual([(u.outcome, u.values["previous"]) for u in rhythm.tone_degree_units([s])][:2], [("9", rhythm.START), ("11", "9")])
        self.assertEqual(rhythm.tone_figure_units([s])[0].outcome, "c c x x")
        s.notes["accompaniment"][2], s.notes["accompaniment"][3] = (2.0, 0.9, 67.0, "a"), (3.0, 0.9, 69.0, "a")
        self.assertEqual(rhythm.tone_classes([(Fraction(0), [(0.0, 1.0, 60.0, "a")]), (Fraction(1), [(1.0, 1.0, 70.0, "a")])], 0.0, s.chords), ["c", "x"])
        self.assertIsNone(rhythm.tone_classes([(Fraction(0), [(0.0, 1.0, 60.0, "a")])], 40.0, s.chords))   # no chord there
        self.assertEqual(upper_mod.off_tone(67, 0, 9), 69)                                    # the A over G, nearer than the A under it
        self.assertEqual(upper_mod.off_tone(60, 0, 9), 57)                                    # under C
        self.assertEqual(upper_mod.off_tone(64, 0, 2), 62)                                    # a tie goes under
        # the writer: a voicing table that says R 3 5, a tone figure that says the fourth onset leaves the chord, the degree a sixth
        mk = lambda name, outcome, **vals: [tables.Unit(f"s{i}", "g", outcome, vals) for i in range(6)]   # noqa: E731
        voicings = tables.Cache.fit(mk("voicings", "R 3 5", part="accompaniment", shape="major", habit="full"), ("part", "shape", "habit"), name="voicings", votes=tables.SHARES)
        figures = tables.Table(("part", "tier", "onsets", "line"), "tone_figures", votes=tables.SHARES).fit(
            mk("tone_figures", "c c c x", part="accompaniment", tier="some", onsets="4", line="0 1 2 3") + mk("tone_figures", "c c x x", part="accompaniment", tier="many", onsets="4", line="0 1 2 3"))
        degrees = tables.Table(("part", "shape", "previous"), "tone_degrees", votes=tables.SHARES).fit(
            mk("tone_degrees", "9", part="accompaniment", shape="major", previous=rhythm.START) + mk("tone_degrees", "2", part="accompaniment", shape="major", previous="9"))

        def line(models, tier="some"):
            song = self._chord_song()
            shared, log = {}, []
            notes, figs, vcs = writer.upper(song, "accompaniment", [0], {0: (60, 84)}, models, random.Random(1), "dense", "full", 0.5,
                                            key=(0, "major"), plays=[True] * 4, figures=["0 1 2 3"] * 4, shared=shared, tone_index=0, log=log, tone_tier=tier)
            return [int(m) % 12 for a, b, m, v in notes], shared, log
        pcs, shared, log = line({"voicings": voicings, "tone_figures": figures, "tone_degrees": degrees})
        self.assertEqual(len(pcs), 16)
        self.assertTrue(all(pc in (0, 4, 7) for i, pc in enumerate(pcs) if i % 4 != 3), pcs)   # the first three onsets on the chord
        self.assertTrue(all(pc == 9 for i, pc in enumerate(pcs) if i % 4 == 3), pcs)          # the fourth a sixth over the root
        self.assertEqual(int(shared[("line", (1, Fraction(3)))]) % 12, 9)                     # the voices beside it see the note played
        self.assertTrue(any(l.startswith("off the chord by the tone figure (round 96, the song's tier some): 4 of 16 line onsets, in 4 bars") for l in log), log)
        pcs, _, log = line({"voicings": voicings, "tone_figures": figures, "tone_degrees": degrees}, tier="many")   # the heavier tier: two onsets a bar, the second chained
        self.assertTrue(all(pc in (0, 4, 7) for i, pc in enumerate(pcs) if i % 4 < 2), pcs)
        self.assertTrue(all(pcs[i] == 9 and pcs[i + 1] == 2 for i in range(2, 16, 4)), pcs)   # a sixth, then a ninth after it
        self.assertTrue(any("tier many): 8 of 16 line onsets" in l for l in log), log)
        pcs, _, log = line({"voicings": voicings})
        self.assertTrue(all(pc in (0, 4, 7) for pc in pcs), pcs)                              # without the words: the voicing's tones alone
        self.assertEqual(log, [])
        pcs, _, log = line({"voicings": voicings, "tone_figures": figures})                    # the figure without a degree word: the tones kept, and said
        self.assertTrue(all(pc in (0, 4, 7) for pc in pcs), pcs)
        self.assertTrue(any("no tone_degrees word" in l for l in log), log)
        # the pack keeps both tables
        from bitcomposer.translate import packtables
        self.assertEqual(packtables.KEPT["tone_figures"][3], ("part", "tier", "onsets", "line"))
        self.assertEqual(packtables.KEPT["tone_degrees"][3], ("part", "shape", "previous"))
        self.assertEqual(packtables.KEPT["tone_tiers"][3], ("part",))
        # the plan draws the part's tier once a song, on its own stream
        tiers = tables.Table(("part",), "tone_tiers", votes=tables.SHARES).fit(mk("tone_tiers", "many", part="accompaniment"))
        token = "melody=main:64-84:0.9:1:0.7:::slead accompaniment=half:60-72:0.8:1:0.6:::sstr bass=half:36-44:0.9:1:1.0:::sbass top=0.30 tempo=medium"
        bal = {"balance": tables.Table(("part",), "balance", votes=tables.SHARES).fit(mk("balance", token, part=rhythm.ARRANGEMENT))}
        self.assertEqual(whole.plan({**bal, "tone_tiers": tiers}, 7, "g").extras["accompaniment"]["tone_tier"], "many")
        self.assertIsNone(whole.plan(bal, 7, "g").extras["accompaniment"]["tone_tier"])

    def test_a_figure_mark_the_chord_lacks_plays_the_chords_nearest_tone(self):
        """A bass figure's or a voicing's mark names a chord tone; where the chord has none (a 7 over a triad, a 3 over a bare
        fifth, an s over a plain triad) the writer had played the tone meant, a note off the chord (81 % of the written
        bass's 7 marks, 41 % of its 3 marks); it plays the chord's own tone nearest the one meant, the lower at a tie."""
        from bitcomposer.translate import writer
        major = {0, 2, 4, 5, 7, 9, 11}
        self.assertEqual(writer.tone(0, "", "7", major), 0)                                   # a seventh over a major triad: the root
        self.assertEqual(writer.tone(0, "7", "7", major), 10)                                  # where the chord has one: itself
        self.assertEqual(writer.tone(0, "maj7", "7", major), 11)
        self.assertEqual(writer.tone(0, "5", "3", major), 7)                                   # a third over a bare fifth: the fifth
        self.assertEqual(writer.tone(0, "sus2", "3", major), 2)                                # over a sus2: the second
        self.assertEqual(writer.tone(0, "m", "s", major), 3)                                   # a sus over a minor triad: the third (a tie with the fifth goes under)
        self.assertEqual(writer.tone(0, "", "s", major), 4)
        self.assertEqual(writer.tone(0, "sus4", "s", major), 5)
        self.assertEqual(writer.tone(0, "dim", "5", major), 6)                                 # the chord's own fifth as before
        self.assertEqual(writer.tone(2, "", "+", major), 4)                                    # a passing tone as before
        self.assertEqual(writer.stack(["R", "3", "5", "7"], 0, "", major, 48, None), [48, 52, 55, 60])   # the 7 of a triad voicing: the root an octave up

    def test_the_counter_holds_its_chord_tone_share(self):
        """The chord_tones word counts the counter-line's strong-beat chord-tone share as the tune's (FFVI's counter about
        a half; the written one, its notes the voice words' intervals with no chord word, 0.37); the plan draws the counter's
        own share on an own stream and the counter writer holds it: on a beat, while the line is not over the share, the
        interval entries landing on the chord take the share of the mass."""
        from bitcomposer.translate import tables, writer
        s = self._chord_song(8)
        s.notes["melody"] = [(4.0 * k + i, 0.9, 67.0, "m") for k in range(8) for i in range(4)]            # G on every beat
        s.notes["counter"] = [(4.0 * k + i, 0.9, m, "c") for k in range(8) for i, m in enumerate((64.0, 65.0, 64.0, 65.0))]   # E F E F: half on the chord
        units = {u.values["part"]: u.outcome for u in rhythm.chord_tone_habit_units([s])}
        self.assertEqual(units, {"melody": "1.0", "counter": "0.5"})
        self.assertEqual(rhythm.CHORD_TONE_PARTS, ("melody", "counter"))
        # the writer: a table that says "a step under the tune" (F under G, off the chord) as often as "a third under" (E, on it)
        iv_t = tables.Table(("part", "kind", "line", "previous"), "voice_intervals", votes=tables.SHARES).fit(
            [tables.Unit(f"s{i}{o}", "g", o, {"part": "counter", "kind": "other", "line": "scale", "previous": p}) for i in range(10) for o in ("-1", "-2") for p in (rhythm.START, "-1", "-2")])
        mv_t = tables.Table(("part", "kind", "place"), "voice_moves", votes=tables.SHARES).fit(
            [tables.Unit(f"s{i}", "g", o, {"part": "counter", "kind": "other", "place": pl}) for i in range(10) for o, pl in (("0", "with"), ("-1", "with"), ("1", "with"), ("1", "alone"))])
        vals = tables.Table(("part", "value", "habit"), "values", votes=tables.SHARES).fit([tables.Unit(f"s{i}", "g", "held", {"part": "counter", "value": "1", "habit": "held"}) for i in range(3)])
        models = {"voice_intervals": iv_t, "voice_moves": mv_t, "values": vals}
        tune = [(4.0 * k + i, 4.0 * k + i + 0.9, 67.0, 0) for k in range(8) for i in range(4)]
        tune_figs, masks = ["0 1 2 3"] * 8, ["1 1 1 1"] * 8

        def share(rate):
            song = self._chord_song(8)
            notes, figures, log = writer.counter(song, tune, tune_figs, masks, (48, 96), models, random.Random(3), "other",
                                                 key=(0, "major"), articulation="held", register=(60, 84), chord_rate=rate)
            on = [int(m) % 12 in (0, 4, 7) for a, b, m in notes]
            return sum(on) / len(on), log
        free, log_free = share(None)
        self.assertTrue(0.2 <= free <= 0.8, free)                                              # without the word: the table's halves
        self.assertFalse(any("chord tones on the beat" in l for l in log_free))
        held, log_held = share(1.0)
        self.assertGreaterEqual(held, 0.9, held)                                               # held to everything: the third under, on the chord
        self.assertTrue(any(l.startswith("chord tones on the beat: ") and "the song's rate 1.00" in l for l in log_held), log_held)
        # the plan: the counter's own draw on its own stream, the melody's as before
        mk = lambda name, outcome, **vals: [tables.Unit(f"s{i}", "g", outcome, vals) for i in range(3)]   # noqa: E731
        ct = tables.Table(("part",), "chord_tones", votes=tables.SHARES).fit(mk("chord_tones", "0.5", part="melody") + mk("chord_tones", "0.8", part="counter"))
        token = "melody=main:64-84:0.9:1:0.7:::slead counter=half:55-67:0.8:1:0.5:::sstr bass=half:36-44:0.9:1:1.0:::sbass top=0.30 tempo=medium"
        bal = {"balance": tables.Table(("part",), "balance", votes=tables.SHARES).fit(mk("balance", token, part=rhythm.ARRANGEMENT))}
        p = whole.plan({**bal, "chord_tones": ct}, 7, "g")
        self.assertEqual((p.extras["melody"]["chord_tones"], p.extras["counter"]["chord_tones"]), (0.5, 0.8))

    def test_a_relation_stretchs_own_edge_bars_are_a_stretch_of_their_own(self):
        """The reader read a relation over a whole sample run: Umaro's accompaniment voice parallels the tune two octaves up for
        five bars and then plays a run of its own on the same sample, and the whole run read as the parallel (round 95). An
        edge run of two bars or more whose bars follow nothing, carrying eight notes or more, is a stretch of its own."""
        s = self._chord_song(8)
        tune = [(4.0 * k + i, 0.9, m, "m") for k in range(8) for i, m in enumerate((67.0, 69.0, 71.0, 72.0))]
        own = lambda k: [(4.0 * k + i, 0.9, m, "v") for i, m in enumerate((68.0, 72.0, 76.0, 80.0))]   # noqa: E731  a second, a third, a fourth and a sixth over the tune: no one interval
        voice = [(t, 0.9, m + 4.0, "v") for t, _, m, _ in tune if t < 24] + own(6) + own(7)
        s.notes["melody"], s.notes["accompaniment"] = tune, voice
        s.voice_notes = {1: ("melody", tune), 2: ("accompaniment", voice)}
        self.assertEqual(rhythm.relation_words(s).get(2), "pm+4x6>o")                        # parallel a third up for six bars, then its own
        s.voice_notes[2] = ("accompaniment", [(t, 0.9, m + 4.0, "v") for t, _, m, _ in tune])  # parallel throughout: one stretch, whole
        self.assertEqual(rhythm.relation_words(s).get(2), "pm+4")
        s.voice_notes[2] = ("accompaniment", [(t, 0.9, m + 4.0, "v") for t, _, m, _ in tune if t < 28] + own(7))
        self.assertEqual(rhythm.relation_words(s).get(2), "pm+4")                            # one own bar at the end: too short to split
        self.assertEqual(rhythm.RELATION_EDGE_BARS, 2)


class ParallelIntervalTests(unittest.TestCase):
    """Round 97: a parallel voice's interval to its line drawn by the chord."""

    def _song(self, bars: int = 8):
        from bitcomposer.translate import vocab
        spans = [(4.0 * k, 4.0 * k + 4.0) for k in range(bars)]
        return rhythm.Song("t", 4, 12, spans, [vocab.Span(0.0, 4.0 * bars, 0, "", 1.0)], notes={}, sid="s", game="g", tonic=0, mode="major")

    def test_a_parallel_voice_lands_where_the_games_do(self):
        """The parallel_intervals word counts, at each shared onset of a parallel stretch, the voice's semitones from the
        line by the stretch's nominal interval, the line note's tone class against the chord, the part and the interval
        before; the writer draws a parallel stretch's (and a layer doubling's) notes by it, so a third over the chord's
        fifth becomes a fourth, as FFVI's do (its parallels sit on a chord tone 0.62 of the time, the line again in the
        scale 0.42); without the word, or at an octave, the line again as before. A chord part's parallel voice holds the
        part's clashes share."""
        from bitcomposer.translate import tables
        major = {0, 2, 4, 5, 7, 9, 11}
        s = self._song()
        tune = [(4.0 * k + i, 0.9, m, "m") for k in range(8) for i, m in enumerate((60.0, 64.0, 67.0, 64.0))]      # C E G E over C major
        above = {60.0: 64.0, 64.0: 67.0, 67.0: 72.0}                                                                # the chord tone above each: +4, +3, +5
        voice = [(t, 0.9, above[m], "v") for t, _, m, _ in tune]
        s.notes["melody"], s.notes["accompaniment"] = tune, voice
        s.voice_notes = {1: ("melody", tune), 2: ("accompaniment", voice)}
        self.assertEqual(rhythm.relation_words(s).get(2), "pm+3")                             # read as a parallel third (the commonest semitones)
        units = rhythm.parallel_interval_units([s])
        self.assertEqual(len(units), 32)
        self.assertEqual([u.outcome for u in units[:4]], ["third", "fifth", "root", "fifth"])   # where the voice lands against the chord
        self.assertEqual(units[0].values, {"interval": "2", "tone": "root", "part": "accompaniment", "previous": rhythm.START})
        self.assertEqual((units[1].values["tone"], units[1].values["previous"], units[2].values["tone"]), ("third", "third", "fifth"))
        s.notes["accompaniment"][0] = (0.0, 0.9, 61.0, "v")                                    # a C# over the C: off the chord, its semitones
        self.assertEqual(rhythm.parallel_interval_units([s])[0].outcome, "-2")                 # round 109: two under the nominal placing (C + 3), not one over the C
        s.notes["accompaniment"][0] = (0.0, 0.9, 64.0, "v")
        self.assertEqual(rhythm.PARALLEL_SEMITONES, 24)
        from bitcomposer.translate import packtables
        self.assertEqual(packtables.KEPT["parallel_intervals"][3], ("interval", "tone", "part", "previous"))
        # the writer: a table of these units; the line C E G E again a third up lands on E G C G, every note on the chord
        t = tables.Table(("interval", "tone", "part", "previous"), "parallel_intervals", votes=tables.SHARES).fit(units)
        line = [(4.0 * k + i, 4.0 * k + i + 0.9, m, 0) for k in range(8) for i, m in enumerate((60.0, 64.0, 67.0, 64.0))]
        song = self._song()
        drawn = whole.parallel(line, 3, major, 1, song, "accompaniment", {"parallel_intervals": t}, random.Random(1))
        self.assertEqual([int(m) for a, b, m, v in drawn[:4]], [64, 67, 72, 67])                # E G C G, each the chord tone nearest a third up
        self.assertTrue(all(int(m) % 12 in (0, 4, 7) for a, b, m, v in drawn), drawn)
        self.assertTrue(all(v == 1 for a, b, m, v in drawn))
        minor = self._song()                                                                    # the same word over C minor: the fifth over Eb is +4
        minor.chords = [vocab.Span(0.0, 32.0, 0, "m", 1.0)]
        drawn_m = whole.parallel([(0.0, 0.9, 63.0, 0), (1.0, 1.9, 60.0, 0)], 3, major, 1, minor, "accompaniment", {"parallel_intervals": t}, random.Random(1))
        self.assertEqual([int(m) for a, b, m, v in drawn_m], [67, 63])                          # Eb to G (+4), C to Eb (+3): the chord's own tones
        scaled = whole.diatonic(line, 3, major, 1)
        self.assertEqual([int(m) % 12 for a, b, m, v in scaled[:4]], [4, 7, 11, 7])            # the scale's third over G is B, off the chord
        self.assertEqual(whole.parallel(line, 3, major, 1, song, "accompaniment", {}, random.Random(1)), scaled)   # without the word
        self.assertEqual(whole.parallel(line, 12, major, 1, song, "accompaniment", {"parallel_intervals": t}, random.Random(1)), whole.diatonic(line, 12, major, 1))   # an octave: exact
        self.assertEqual(whole.parallel(line, 3, major, 1, None, "accompaniment", {"parallel_intervals": t}, random.Random(1)), scaled)   # no song: the scale
        log = []
        whole.parallel(line, 3, major, 1, song, "accompaniment", {"parallel_intervals": t}, random.Random(1), None, log)
        self.assertTrue(any(l.startswith("voice 2 parallel at +3 by the parallel_intervals word (round 97): 32 notes") for l in log), log)
        # a stretch: the relation word's parallel bars by the word, its own bars its own
        melody = whole.Part("melody", line, [])
        own = [(4.0 * k + 0.5, 4.0 * k + 1.0, 50.0, 1) for k in range(8)]
        log = []
        notes = whole.stretched_notes(1, own, whole.stretch_spans(whole.relation_stretches("pm+3x4>o"), 8), {"melody": melody}, major, 4, log,
                                      song=song, role="accompaniment", models={"parallel_intervals": t}, rng=random.Random(2))
        self.assertEqual([int(m) % 12 for a, b, m, v in notes if a < 16], [4, 7, 0, 7] * 4)   # the parallel bars by the word
        self.assertEqual([m for a, b, m, v in notes if a >= 16], [50.0] * 4)                   # its own bars
        self.assertTrue(any("parallel_intervals" in l for l in log), log)
        # a chord part's parallel voice over a bass holding F (a semitone from E): a share of none sends the E to the table's other entry
        both = tables.Table(("interval", "tone", "part", "previous"), "parallel_intervals", votes=tables.SHARES).fit(
            [tables.Unit(f"s{i}", "g", o, {"interval": "2", "tone": "root", "part": "accompaniment", "previous": p}) for i in range(10) for o in ("third", "fifth") for p in (rhythm.START, "third", "fifth")])
        roots = [(4.0 * k + i, 4.0 * k + i + 0.9, 60.0, 0) for k in range(8) for i in range(4)]
        song.notes["bass"] = [(4.0 * k, 4.0, 65.0, "bass") for k in range(8)]
        free = whole.parallel(roots, 3, major, 1, song, "accompaniment", {"parallel_intervals": both}, random.Random(3), None)
        held = whole.parallel(roots, 3, major, 1, song, "accompaniment", {"parallel_intervals": both}, random.Random(3), {"strong": 0.0, "weak": 0.0})
        e_free, e_held = sum(int(m) % 12 == 4 for a, b, m, v in free), sum(int(m) % 12 == 4 for a, b, m, v in held)
        self.assertGreater(e_free, 8)                                                          # the table's halves: E often
        self.assertLess(e_held, e_free / 2)                                                    # held to none: the first may clash, then G unless four draws say E
        self.assertLessEqual(e_held, 5)
        self.assertTrue(all(int(m) % 12 in (4, 7) for a, b, m, v in held))


class SmallWordTests(unittest.TestCase):
    """Round 98: the form's part the loop returns to, and the tune's note lengths as its song's own."""

    def _song(self, bars: int = 8):
        from bitcomposer.translate import vocab
        spans = [(4.0 * k, 4.0 * k + 4.0) for k in range(bars)]
        return rhythm.Song("t", 4, 12, spans, [vocab.Span(0.0, 4.0 * bars, 0, "", 1.0)], notes={}, sid="s", game="g", tonic=0, mode="major")

    def test_the_loop_returns_to_the_games_part(self):
        """The loop_parts word counts which part of the form a song's loop returns to, by whether the form opens with an
        intro it never comes back to; the plan draws it in place of the rule (after the intro, else the first bar), which
        FFVI breaks in 21 of 61 loops, returning to the intro itself in 15 of 53."""
        from bitcomposer.translate import tables
        s = self._song()
        s.parts = [(0, 4, None, "A"), (4, 8, None, "B"), (12, 8, 1, "B")]                        # an intro, then B twice
        s.loop_bar = 4
        self.assertEqual([(u.outcome, u.values) for u in rhythm.loop_part_units([s], sure_only=False)], [("1", {"part": "form", "intro": "intro"})])
        s.loop_bar = 0
        self.assertEqual(rhythm.loop_part_units([s], sure_only=False)[0].outcome, "0")          # back to the intro
        s.parts = [(0, 4, None, "A"), (4, 8, None, "B"), (12, 4, 0, "A")]                        # A comes back: no intro
        self.assertEqual(rhythm.loop_part_units([s], sure_only=False)[0].values["intro"], "none")
        s.loop_bar = None
        self.assertEqual(rhythm.loop_part_units([s], sure_only=False), [])
        from bitcomposer.translate import packtables
        self.assertEqual(packtables.KEPT["loop_parts"][3], ("part", "intro"))
        # the plan: the rule without the word; the drawn part with it; the rule where the form lacks the part
        parts = [(0, 4, None, "A"), (4, 8, None, "B"), (12, 8, None, "C")]
        self.assertEqual(whole.loop_bar_of(parts), 4)
        mk = lambda outcome, intro: [tables.Unit(f"s{i}{outcome}{intro}", "g", outcome, {"part": "form", "intro": intro}) for i in range(4)]   # noqa: E731
        t = tables.Table(("part", "intro"), "loop_parts", votes=tables.SHARES).fit(mk("0", "intro") + mk("1", "none"))
        log = []
        self.assertEqual(whole.plan_loop({"loop_parts": t}, parts, random.Random(1), log), 0)    # back to the intro, as the word says
        self.assertTrue(any(l.startswith("loop (loop_parts): back to part 1 of 3, bar 1 (an intro)") for l in log), log)
        self.assertEqual(whole.plan_loop({}, parts, random.Random(1), []), 4)                   # no word: the rule
        far = tables.Table(("part", "intro"), "loop_parts", votes=tables.SHARES).fit(mk("7", "intro"))
        log = []
        self.assertEqual(whole.plan_loop({"loop_parts": far}, parts, random.Random(1), log), 4)  # a part the form lacks: the rule
        self.assertTrue(any("the form has 3" in l for l in log), log)

    def test_the_tune_sounds_its_songs_shares(self):
        """The tune_sounds word counts the median share of its gap a tune's or counter-line's held note sounds, and its
        detached ones apart (FFVI 0.91 and 0.40 for the tune); the plan draws both once a song a part, and the melody and
        counter writers sound their notes by them in place of the constants 0.95 and 0.5."""
        from bitcomposer.translate import tables, writer
        s = self._song()
        s.notes["melody"] = [(4.0 * k + i, 0.9 if i % 2 == 0 else 0.3, 67.0, "m") for k in range(8) for i in range(4)]   # held and detached by turns
        units = {u.values["note"]: u.outcome for u in rhythm.tune_sound_units([s])}
        self.assertEqual(units, {"held": "0.9", "detached": "0.3"})
        self.assertEqual(rhythm.TUNE_KINDS, ("held", "detached"))
        self.assertEqual((writer.sounded_share(None, "held"), writer.sounded_share(None, "detached")), (writer.HELD, writer.DETACHED))
        self.assertEqual(writer.sounded_share({"held": 0.8, "detached": 0.3}, "detached"), 0.3)
        from bitcomposer.translate import packtables
        self.assertEqual(packtables.KEPT["tune_sounds"][3], ("part", "note"))
        # the counter writer: a values table that says held; the song's shares against the constants
        iv_t = tables.Table(("part", "kind", "line", "previous"), "voice_intervals", votes=tables.SHARES).fit(
            [tables.Unit(f"s{i}", "g", "-2", {"part": "counter", "kind": "other", "line": "scale", "previous": p}) for i in range(10) for p in (rhythm.START, "-2")])
        mv_t = tables.Table(("part", "kind", "place"), "voice_moves", votes=tables.SHARES).fit(
            [tables.Unit(f"s{i}", "g", o, {"part": "counter", "kind": "other", "place": pl}) for i in range(10) for o, pl in (("0", "with"), ("1", "alone"))])
        vals = tables.Table(("part", "value", "habit"), "values", votes=tables.SHARES).fit([tables.Unit(f"s{i}", "g", "held", {"part": "counter", "value": "1", "habit": "held"}) for i in range(3)])
        models = {"voice_intervals": iv_t, "voice_moves": mv_t, "values": vals}
        tune = [(4.0 * k + i, 4.0 * k + i + 0.9, 67.0, 0) for k in range(8) for i in range(4)]
        for sounds, want in ((None, writer.HELD), ({"held": 0.8, "detached": 0.3}, 0.8)):
            song = self._song()
            notes, figures, log = writer.counter(song, tune, ["0 1 2 3"] * 8, ["1 1 1 1"] * 8, (48, 96), models, random.Random(3), "other",
                                                 key=(0, "major"), articulation="held", register=(60, 84), tune_sounds=sounds)
            lengths = {round(b - a, 3) for a, b, m in notes[:-1]}
            self.assertEqual(lengths, {round(want, 3)}, (sounds, lengths))                      # a beat's gap sounds the share
        # the plan: both shares drawn once a song for each line, on their own streams
        mk = lambda name, outcome, **vals: [tables.Unit(f"s{i}", "g", outcome, vals) for i in range(3)]   # noqa: E731
        many = lambda outcome, **vals: [tables.Unit(f"t{i}", "g", outcome, vals) for i in range(40)]   # noqa: E731  enough songs that the level holds its draw
        ts = tables.Table(("part", "note"), "tune_sounds", votes=tables.SHARES).fit(
            many("0.9", part="melody", note="held") + many("0.4", part="melody", note="detached")
            + many("1.0", part="counter", note="held") + many("0.3", part="counter", note="detached"))
        token = "melody=main:64-84:0.9:1:0.7:::slead counter=half:55-67:0.8:1:0.5:::sstr bass=half:36-44:0.9:1:1.0:::sbass top=0.30 tempo=medium"
        bal = {"balance": tables.Table(("part",), "balance", votes=tables.SHARES).fit(mk("balance", token, part=rhythm.ARRANGEMENT))}
        p = whole.plan({**bal, "tune_sounds": ts}, 7, "g")
        self.assertEqual(p.extras["melody"]["tune_sounds"], {"held": 0.9, "detached": 0.4})
        self.assertEqual(p.extras["counter"]["tune_sounds"], {"held": 1.0, "detached": 0.3})
        self.assertNotIn("tune_sounds", whole.plan(bal, 7, "g").extras["melody"])


class KitSecondTests(unittest.TestCase):
    """Round 99: a kit slot's second sample on the token, the kit_seconds word, and the writer's hits on it."""

    def _kit_song(self):
        from bitcomposer.translate import vocab
        bars = [(4.0 * k, 4.0 * k + 4.0) for k in range(8)]
        s = rhythm.Song("t", 4, 12, bars, [vocab.Span(0.0, 32.0, 0, "", 1.0)], notes={}, sid="s", game="g", tonic=0, mode="major")
        closed, opened, kick = "aaaaaaaaaa11", "bbbbbbbbbb22", "cccccccccc33"
        hats = [(4.0 * k + i / 2, 0.2, float("nan"), closed if i % 2 == 0 else opened) for k in range(8) for i in range(8)]   # closed on the beats, open on the ands
        kicks = [(4.0 * k + i, 0.2, float("nan"), kick) for k in range(8) for i in (0, 2)]
        s.notes["drums"] = sorted(hats + kicks)
        s.pieces = {closed: "hat", opened: "hat", kick: "kick"}                                  # the readings' piece names
        s.kit_levels = {closed: 0.1, opened: 0.2, kick: 0.5}
        s.kit_rates = {closed: 60, opened: 59, kick: 48}
        s.kit_holds = {closed: 0.2, opened: 0.45, kick: 0.5}
        s.voice_notes = {6: ("drums", s.notes["drums"])}
        return s, closed, opened, kick

    def test_a_kit_slots_second_sample_rides_the_token_and_takes_its_hits(self):
        """The reader finds the letter's second sample (the other one with eight hits or more), the slot's strike class counts
        both samples' hits, the kit token carries the second after a "+" with its level, rate, hold and share, the kit_seconds
        word says which hits take it by their place in the beat, the plan parses it, and the writer's pick holds the letter's
        hits to the token's share."""
        from bitcomposer.translate import tables
        s, closed, opened, kick = self._kit_song()
        self.assertEqual(rhythm.kit_slots(s), {"h": opened, "K": kick})                       # the loudest of the two hats takes the slot
        self.assertEqual(rhythm.kit_second_samples(s), {"h": closed})                          # the other is the second
        self.assertEqual(rhythm.kit_classes(s), {"h": "d", "K": "m"})                          # eight hat hits a bar over both samples: dense; two kicks: medium
        units = rhythm.kit_second_units([s])
        self.assertEqual(len(units), 64)
        self.assertEqual({(u.values["part"], u.values["place"], u.outcome) for u in units}, {("h", "beat", "second"), ("h", "eighth", "main")})
        token = rhythm.kit_token(s, top=0.5)
        hat = next(f for f in token.split(",") if f.startswith("h="))
        self.assertTrue(hat.startswith(f"h=sbbbbbbbbbb@0.40@r59@0.45@d"), hat)
        self.assertIn("+saaaaaaaaaa@0.20@r60@0.20@0.50", hat)                                   # the second: id, level, rate, hold, its half of the hits
        self.assertNotIn("+", next(f for f in token.split(",") if f.startswith("K=")))
        s.notes["drums"] = [n for n in s.notes["drums"] if n[3] != closed][:40] + [n for n in s.notes["drums"] if n[3] == closed][:7]   # under eight hits: no second
        self.assertEqual(rhythm.kit_second_samples(s), {})
        from bitcomposer.translate import packtables
        self.assertEqual(packtables.KEPT["kit_seconds"][3], ("part", "place"))
        # the plan reads the second from the drums field
        mk = lambda name, outcome, **vals: [tables.Unit(f"s{i}", "g", outcome, vals) for i in range(3)]   # noqa: E731
        drums = "drums=main:::Kh:0.5:::K=scccccccccc@1.00@r48@0.50@m@@0.50,h=sbbbbbbbbbb@0.40@r59@0.45@d@@0.50+saaaaaaaaaa@0.20@r60@0.20@0.50"
        token = f"melody=main:64-84:0.9:1:0.7:::slead bass=half:36-44:0.9:1:1.0:::sbass {drums} top=0.30 tempo=medium"
        bal = {"balance": tables.Table(("part",), "balance", votes=tables.SHARES).fit(mk("balance", token, part=rhythm.ARRANGEMENT))}
        p = whole.plan(bal, 7, "g")
        self.assertIn("drums", p.band)
        x = p.extras["drums"]
        self.assertEqual(x["kit"], {"K": "scccccccccc", "h": "sbbbbbbbbbb"})
        self.assertEqual(x["kit_seconds"], {"h": {"sample": "saaaaaaaaaa", "share": 0.5, "level": 0.2, "hold": 0.2, "rate": 60, "degree": None, "pitch": None, "tuned": False}})
        self.assertEqual(x["kit_classes"], {"K": "m", "h": "d"})
        self.assertTrue(any(l.startswith("kit seconds from the balance: h saaaaaaaaaa at 0.50 of the hits") for l in p.log), p.log)
        self.assertEqual(whole.slot_letter("hihat2"), ("h", True))
        self.assertEqual(whole.kit_second(p, "hihat2")["sample"], "saaaaaaaaaa")
        self.assertEqual((whole.kit_piece_level(p, "hihat"), whole.kit_piece_level(p, "hihat2")), (0.4, 0.2))   # each sample its own level
        self.assertEqual((whole.kit_piece_rate(p, "hihat"), whole.kit_piece_rate(p, "hihat2")), (59, 60))
        self.assertEqual((whole.kit_piece_hold(p, "hihat"), whole.kit_piece_hold(p, "hihat2")), (0.45, 0.2))
        self.assertIsNone(whole.kit_second(p, "kick"))
        self.assertIsNone(whole.kit_piece_rate(p, "kick2"))                                    # a second slot with no second: nothing
        # the writer's pick: a word that puts the second on every eighth and never on a beat, held to the token's share
        seconds = tables.Table(("part", "place"), "kit_seconds", votes=tables.SHARES).fit(
            [tables.Unit(f"s{i}", "g", o, {"part": "h", "place": pl}) for i in range(10) for o, pl in (("second", "eighth"), ("main", "beat"))])
        run, rng = [0, 0], random.Random(1)
        picks = [whole.kit_second_pick({"kit_seconds": seconds}, "h", pl, run, 0.5, rng) for pl in ("beat", "eighth") * 16]
        self.assertEqual(picks[:4], [False, True, False, True])
        self.assertEqual(sum(picks), 16)                                                       # half the hits, the eighths
        self.assertEqual(run, [16, 32])
        run = [0, 0]
        picks = [whole.kit_second_pick({"kit_seconds": seconds}, "h", "eighth", run, 0.25, rng) for _ in range(32)]
        self.assertLessEqual(sum(picks), 9)                                                    # held to a quarter: once over, the main
        self.assertGreaterEqual(sum(picks), 8)
        self.assertFalse(any(whole.kit_second_pick({}, "h", "eighth", [0, 0], 0.5, rng) for _ in range(8)))   # no word: no second

    def test_a_whole_song_plays_the_second_sample_on_its_own_slot(self):
        """The second's slot is one the pack's kit does not list: compose adds it to the song's pieces once samples_for has
        given it its sample, so the writer's hits reach it (the first cut had left it out, and no song played a second)."""
        from unittest import mock
        from bitcomposer import instruments
        from bitcomposer.composer import compose_song
        from bitcomposer.packs import PACKS
        from bitcomposer.translate import harness, packtables, tables
        ctx = harness.load_generated(compose_song(seed=5, pack="ffvi"), "seed 5", "test", seconds=40.0)
        models = packtables.read(packtables.build(ctx.db, "test"))
        drums = "drums=main:::Kh:0.5:::K=scccccccccc@1.00@r48@0.50@m@@0.50,h=sbbbbbbbbbb@0.40@r59@0.45@d@@0.50+saaaaaaaaaa@0.20@r60@0.20@0.50"
        token = f"melody=main:64-84:0.9:1:0.7:::slead bass=half:36-44:0.9:1:1.0:::sbass {drums} top=0.30 tempo=medium"
        models["balance"] = tables.Table(("part",), "balance", votes=tables.SHARES).fit([tables.Unit(f"s{i}", "g", token, {"part": rhythm.ARRANGEMENT}) for i in range(3)])
        models["kit_seconds"] = tables.Table(("part", "place"), "kit_seconds", votes=tables.SHARES).fit(
            [tables.Unit(f"s{i}", "g", "second", {"part": "h", "place": pl}) for i in range(10) for pl in ("beat", "eighth", "sixteenth", "triplet", "finer")])
        real = instruments._make_sample
        fake = lambda name: real(name) if not name.startswith("g_") else real("ffvi_bassdrum" if "cccc" in name else "ffvi_hat")   # noqa: E731  the token's own ids on real samples
        own = {"scccccccccc", "sbbbbbbbbbb", "saaaaaaaaaa", "slead", "sbass"}
        with mock.patch.object(instruments, "_make_sample", fake):
            out = whole.compose(models, {"voices": dict(PACKS["ffvi"]["voices"])}, own, "g", 7, "g", max_bars=16, read=False)
        p, song, written = out["plan"], out["song"], out["written"]
        self.assertEqual(p.extras["drums"]["kit_seconds"]["h"]["share"], 0.5)
        self.assertEqual(out["samples"]["drums"]["hihat2"][0], "saaaaaaaaaa")                   # the second's own slot and sample
        self.assertEqual(song.pieces.get("hihat2"), "hat")                                      # on the song's kit, so the writer can reach it
        hats = [n for n in written["drums"].notes if n[2] == "h"]
        seconds = [n for n in hats if n[4] == "hihat2"]
        self.assertTrue(hats, written["drums"].log)
        self.assertTrue(seconds, written["drums"].log)                                          # the word puts every hit on the second: the share holds it to half
        self.assertLessEqual(len(seconds), len(hats) // 2 + 1)
        self.assertGreaterEqual(len(seconds), len(hats) // 2 - 1)
        self.assertTrue(any(l.startswith(f"kit seconds (kit_seconds): h {len(seconds)} of {len(hats)} hits on the second sample") for l in written["drums"].log), written["drums"].log)
        self.assertEqual({n[3] for n in song.notes["drums"]} & {"hihat", "hihat2"}, {"hihat", "hihat2"})   # both samples in the song's notes, for the parts after


class RecallMoveTests(unittest.TestCase):
    """Round 100: how far a recalled tune cell sits from its last occurrence (recall_moves), and the writer's anchor for it."""

    def test_a_recalled_cells_move_is_counted_against_its_last_occurrence_and_the_chord(self):
        from bitcomposer.translate.vocab import Span
        bars = [(4.0 * k, 4.0 * k + 4.0) for k in range(12)]
        def bar(k, ps): return [(4.0 * k + i, 0.9, float(p), "a") for i, p in enumerate(ps)]
        A, B, C = [60, 64, 67, 65], [60, 64, 62, 60], [62, 65, 69, 67]
        up = lambda cell, n: [p + n for p in cell]                                             # noqa: E731
        tune = bar(0, A) + bar(1, B) + bar(2, A) + bar(3, A) + bar(4, C) + bar(5, up(A, 7)) + bar(6, C) + bar(7, up(A, 2)) \
            + bar(8, A) + bar(9, B) + bar(10, A) + bar(11, A)
        chords = [Span(0.0, 16.0, 0, "", 1.0), Span(16.0, 24.0, 7, "", 1.0), Span(24.0, 32.0, 0, "", 1.0), Span(32.0, 48.0, 0, "", 1.0)]
        s = rhythm.Song("t", 4, 12, bars, chords, notes={"melody": tune}, sid="s", game="g", numbers=list(range(12)),
                        parts=[(0, 4, None, "A"), (4, 4, None, "B"), (8, 4, 0, "A")])
        units = rhythm.recall_move_units([s])
        self.assertEqual([(u.outcome, u.values["recall"], u.values["chord"]) for u in units],
                         [("0", "earlier", "same"),       # bar 2: A again at pitch over the same C
                          ("0", "same", "same"),          # bar 3: the bar before's cell again
                          ("root", "earlier", "other"),   # bar 5: A a fifth up over G, as the root moved
                          ("0", "earlier", "other"),      # bar 6: C at pitch, the chord back to C
                          ("-5", "earlier", "other")])    # bar 7: A at 62, a fourth under its last occurrence (67), not the root's move
        self.assertTrue(all(u.values["part"] == "melody" for u in units))                      # the form's repeat of A (bars 8-11) is not counted
        self.assertEqual((rhythm.recall_move(0, None), rhythm.recall_move(12, 5), rhythm.recall_move(7, 7), rhythm.recall_move(-5, 7)), ("0", "0", "root", "root"))
        self.assertEqual((rhythm.recall_move(7, 2), rhythm.recall_move(6, None), rhythm.recall_move(-2, 0)), ("-5", "6", "-2"))
        from bitcomposer.translate import packtables
        self.assertEqual(packtables.KEPT["recall_moves"][3], ("part", "recall", "chord"))

    def test_the_writer_anchors_a_recall_where_the_word_says(self):
        from types import SimpleNamespace
        from bitcomposer.translate.writer import tune
        cell = SimpleNamespace(pitches=[60, 64, 67], root=0)
        self.assertEqual(tune.recall_anchor(cell, (0, ""), "0", (55, 79), 70.0), 60)           # at pitch
        self.assertEqual(tune.recall_anchor(cell, (0, ""), "0", (64, 76), 70.0), 72)           # at pitch, the octave the register holds
        self.assertEqual(tune.recall_anchor(cell, (7, ""), "root", (55, 79), 60.0), 55)        # with the root: C to G, the fourth down (the nearer way)
        self.assertEqual(tune.recall_anchor(cell, (5, ""), "root", (55, 79), 60.0), 65)        # C to F: a fourth up
        self.assertEqual(tune.recall_anchor(cell, None, "+2", (55, 79), 60.0), 62)
        self.assertEqual(tune.recall_anchor(cell, None, "6", (55, 79), 60.0), 66)
        self.assertEqual(tune.recall_anchor(cell, None, "-5", (58, 62), 60.0), 58)             # a register without the pitch class: its nearest note to the move


class SectionDensityTests(unittest.TestCase):
    """Round 101: a part's density tier in a section by the step its level makes (section_densities), and the writers' habit a bar."""

    def test_a_sections_density_tier_is_counted_by_the_step_its_level_makes(self):
        from bitcomposer.translate import tables
        bars = [(4.0 * k, 4.0 * k + 4.0) for k in range(8)]
        eighths = [(4.0 * i + x / 2, 0.4, 36.0, "b") for i in range(4) for x in range(8)]                    # A: eight notes a bar, soft
        halves = [(4.0 * i + x, 0.9, 36.0, "b") for i in range(4, 8) for x in (0.0, 2.0)]                     # B: two a bar, loud (an intro's
        s = rhythm.Song("t", 4, 12, bars, [], notes={"bass": eighths + halves}, sid="s", game="g", numbers=list(range(8)),   # sparse lead, as
                        parts=[(0, 4, None, "A"), (4, 4, None, "B")])                                        # Another World of Beasts')
        s.note_levels = {"bass": [(n[0], 0.1) for n in eighths] + [(n[0], 0.3) for n in halves]}            # the median level is A's: B steps up
        units = rhythm.section_density_units([s])
        self.assertEqual([(u.values["part"], u.values["step"], u.outcome) for u in units], [("bass", "same", "d+"), ("bass", "up", "d-")])   # 8 and 2 a bar over 5
        self.assertEqual((rhythm.level_step(2.0), rhythm.level_step(0.6), rhythm.level_step(1.2), rhythm.level_step(1.5)), ("up", "down", "same", "up"))
        self.assertEqual((rhythm.shift_habit("medium mixed", 1), rhythm.shift_habit("medium mixed", -1), rhythm.shift_habit("dense varied", 1),
                          rhythm.shift_habit("sparse walking no-octaves", -1), rhythm.shift_habit("medium mixed", 0), rhythm.shift_habit(None, 1)),
                         ("dense mixed", "sparse mixed", "dense varied", "sparse walking no-octaves", "medium mixed", None))
        from bitcomposer.translate import packtables
        self.assertEqual(packtables.KEPT["section_densities"][3], ("part", "step"))
        # the plan: a shift a bar by the part and the step, a repeated section copying its source's
        units_ = lambda outcome, **v: [tables.Unit(f"s{i}", "g", outcome, v) for i in range(3)]   # noqa: E731
        t = tables.Table(("part", "step"), "section_densities", votes=tables.SHARES).fit(
            units_("d+", part="bass", step="up") + units_("d=", part="bass", step="same") + units_("d-", part="melody", step="same"))
        parts = [(0, 4, None, "A"), (4, 4, None, "B"), (8, 4, 0, "A")]
        plays = {"bass": [True] * 12, "melody": [True] * 12}
        levels = {"bass": [1.0] * 4 + [2.0] * 4 + [1.0] * 4}
        log = []
        plays["counter"] = [True] * 12
        shifts = whole.plan_section_densities({"section_densities": t}, parts, ["bass", "melody", "drums", "counter"], plays, levels, random.Random(1), log)
        self.assertNotIn("counter", shifts)                                                                 # the counter follows the tune's figures: no draw
        self.assertEqual(shifts["bass"], [0] * 4 + [1] * 4 + [0] * 4)                                      # denser where the level steps up
        self.assertEqual(shifts["melody"], [-1] * 12)                                                       # sparser at level 1.0, as the table says
        self.assertNotIn("drums", shifts)
        self.assertIn("densities by section (section_densities): melody sparser in A; bass denser in B (level 2.0); melody sparser in B", log)
        from types import SimpleNamespace
        plan = SimpleNamespace(section_densities=shifts, habits={"bass": "medium walking", "melody": "dense varied"})
        at = whole.habit_at_for(plan, "bass")
        self.assertEqual((at(0), at(5), at(9), at(40)), ("medium walking", "dense walking", "medium walking", "medium walking"))
        self.assertEqual(whole.habit_at_for(plan, "melody", "medium varied")(3), "sparse varied")        # a given habit (the second voice's) shifted the same
        self.assertIsNone(whole.habit_at_for(SimpleNamespace(section_densities={"bass": [0] * 12}, habits={"bass": "medium"}), "bass"))   # nothing shifts: no habit a bar
        # the shift as an envelope on the bars' figures: DENSITY_STEP times the tier's typical onsets or more, even for a dense part
        self.assertEqual((rhythm.density_bounds("dense mixed", 1), rhythm.density_bounds("medium mixed", 1), rhythm.density_bounds("sparse varied", 1)), ((12, 64), (6, 64), (2, 64)))
        self.assertEqual((rhythm.density_bounds("dense mixed", -1), rhythm.density_bounds("medium mixed", -1), rhythm.density_bounds("sparse varied", -1)), ((0, 5), (0, 2), (0, 1)))
        self.assertIsNone(rhythm.density_bounds("dense mixed", 0)); self.assertIsNone(rhythm.density_bounds("walking", 1))
        self.assertEqual((rhythm.density_bounds("dense mixed", 1, 10), rhythm.density_bounds("dense mixed", -1, 10), rhythm.density_bounds("medium mixed", 1, 0)),
                         ((15, 64), (0, 6), (6, 64)))                                                         # the part's own running density where the writer has one
        env = whole.envelope_at_for(plan, "bass")
        self.assertEqual((env(0), env(5), env(9), env(5, 10.0)), (None, (6, 64), None, (15, 64)))            # the bass's medium tier, denser in B


class TokenWithTests(unittest.TestCase):
    """Round 107: a voice beside a line struck with the line or with a sibling voice: the relation word says so ("wl+24",
    "w1-7"), a double or parallel of a sibling names the sibling's rank, and the writer plays such a voice on the followed
    voice's onsets, on the chord at the nominal interval."""

    def _song(self):
        from bitcomposer.translate.vocab import Span
        bars = [(4.0 * k, 4.0 * k + 4.0) for k in range(8)]
        chords = [Span(0.0, 32.0, 0, "", 1.0)]
        riff = [(4.0 * k + x / 2, 0.4, 48.0, "g") for k in range(8) for x in range(8)]                        # the line: a chugging riff on C
        stabs = [72.0, 72.0, 79.0, 74.0, 76.0]
        upper = [(4.0 * k + x, 0.2, stabs[(4 * k + x) % 5], "s") for k in range(8) for x in range(4)]         # a stab on each beat of the riff: C, C, G, D, E
        lower = [(t, d, m - (7, 5, 3)[i % 3], "s") for i, (t, d, m, _) in enumerate(upper)]                   # struck with it, a fifth, fourth or third under
        bass = [(4.0 * k + x, 0.9, 36.0, "b") for k in range(8) for x in (0.0, 2.0)]
        tune = [(4.0 * k + x, 0.9, 84.0 + x, "m") for k in range(8) for x in (0.0, 1.0, 2.0, 3.0)]
        s = rhythm.Song("t", 4, 12, bars, chords, notes={"accompaniment": riff + upper + lower, "bass": bass, "melody": tune}, sid="s", game="g",
                        numbers=list(range(8)), parts=[(0, 8, None, "A")], tonic=0, mode="major")
        s.voice_notes = {0: ("accompaniment", riff), 1: ("bass", bass), 2: ("melody", tune), 3: ("accompaniment", upper), 4: ("accompaniment", lower)}
        s.voice_levels = {0: 0.3, 1: 0.5, 2: 0.4, 3: 0.3, 4: 0.3}; s.levels = {"accompaniment": 0.3, "bass": 0.5, "melody": 0.4}
        return s

    def test_the_relation_words_say_struck_with(self):
        s = self._song()
        words = rhythm.relation_words(s)
        self.assertEqual(words.get(3), "wl+24", words)                                          # the stabs: struck with the line, two octaves up at the commonest
        self.assertEqual(words.get(4), "w1-7", words)                                           # the lower stab: struck with the first voice beside the line
        tok = rhythm.balance_units([s])[0].outcome
        acc = next(f for f in tok.split() if f.startswith("accompaniment=")).split("=", 1)[1].split(":")
        layers = acc[5].split("/")
        self.assertEqual([x.split("@")[4] for x in layers], ["wl+24", "w1-7"], layers)
        self.assertEqual([x.split("@")[6] for x in layers], ["w0.51~-~0.4~-~-~-~0.2~0.20~0.21", "w1.00~-~0.4~-~-~-~0.2~0.20~0.21"], layers)   # round 108: the
        # stabs strike 32 of the riff's 63 onsets in their span and sound 0.4 of the riff's half-beat gap, 0.2 beats at the longest; the lower stab strikes
        # every upper one; round 115: each sounds 0.20 of its bars' time (32 stabs of 0.2 beats over eight bars); round 116: the cell's repeats
        self.assertEqual(whole.struck_values_of("w0.82~0.2~0.3~1.0~0.6~-~4.9"),
                         {"share": 0.82, "sounds": {"<0.5": 0.2, "0.5-1": 0.3, "1-2": 1.0, "2-4": 0.6, "4+": None}, "longest": 4.9, "sounding": None, "cell": None})
        self.assertEqual(whole.struck_values_of("w0.82~0.2~0.3~1.0~0.6~-~4.9~0.53")["sounding"], 0.53)   # the eighth part (round 115)
        self.assertIsNone(whole.struck_values_of("w0.82~0.2~0.3~1.0~0.6~-~4.9~-")["sounding"])
        self.assertEqual(whole.struck_values_of("w0.82~0.2~0.3~1.0~0.6~-~4.9~0.53~0.72")["cell"], 0.72)   # the ninth (round 116)
        self.assertIsNone(whole.struck_values_of("wl+19"))
        self.assertEqual(whole.relation_stretches("wl+24"), [("with", ("line",), 24, None)])
        self.assertEqual(whole.relation_stretches("w1-7x6>o"), [("with", ("voice", 1), -7, 6), ("own", None, None, None)])
        self.assertEqual(whole.relation_stretches("p2-7"), [("parallel", ("voice", 2), -7, None)])
        self.assertEqual(whole.relation_stretches("dm-12x6>o"), [("double", "melody", -12, 6), ("own", None, None, None)])   # as before

    def test_a_voice_is_struck_with_the_followed_one(self):
        bars = [(4.0 * k, 4.0 * k + 4.0) for k in range(4)]
        song = rhythm.Song("w", 4, 4, bars, [], notes={}, sid="w", game="g", numbers=list(range(4)), parts=[(0, 4, None, "A")], tonic=0, mode="major")
        ref = [(4.0 * k + x / 2, 4.0 * k + x / 2 + 0.4, 48.0 + (x % 2) * 7, 0) for k in range(4) for x in range(8)]   # the line: eighths, C and G
        scale = {0, 2, 4, 5, 7, 9, 11}
        notes, thinned, figs = whole.struck_with(ref, 0, 4, 24, song, "accompaniment", 1, {}, random.Random(1), None, 0.5, scale)
        self.assertEqual([n[0] for n in notes], [n[0] for n in ref])                           # every followed onset, nothing to thin without the word
        self.assertEqual({round(n[2]) - round(r[2]) for n, r in zip(notes, ref)}, {24})          # two octaves up (diatonic without the parallel word)
        self.assertTrue(all(abs((n[1] - n[0]) - 0.25) < 1e-6 for n in notes[:-1]))              # half of the half-beat gap sounds
        self.assertEqual((thinned, figs[0]), (0, rhythm.pattern(rhythm.position(x / 2, 4) for x in range(8))))
        every_other = lambda f: " ".join("1 0" for _ in range(len(f.split()) // 2)) + "|"            # noqa: E731  a mask: with the odd onsets only
        notes2, thinned2, figs2 = whole.struck_with(ref, 1, 3, -7, song, "accompaniment", 2, {}, random.Random(1), None, 0.5, scale, every_other)
        self.assertEqual([n[0] for n in notes2], [4.0 * k + x / 2 for k in (1, 2) for x in range(0, 8, 2)])   # bars 2-3, every other onset
        self.assertEqual(thinned2, 8)
        self.assertTrue(all(abs((n[1] - n[0]) - 0.25) < 1e-6 for n in notes2[:-1]))             # half of the LINE's half-beat gap (round 108), not of
        # the gap to the voice's own next stab

    def test_a_stab_before_the_lines_rest_ends_as_the_token_voice_does(self):
        """Round 108: a stab's gap is to the line's next onset and no stab rings past the token voice's longest note; the last
        stab before a two-bar rest of the line had rung through the rest."""
        bars = [(4.0 * k, 4.0 * k + 4.0) for k in range(6)]
        song = rhythm.Song("w", 4, 4, bars, [], notes={}, sid="w", game="g", numbers=list(range(6)), parts=[(0, 6, None, "A")], tonic=0, mode="major")
        ref = [(4.0 * k + x / 2, 4.0 * k + x / 2 + 0.4, 48.0, 0) for k in (0, 1, 4, 5) for x in range(8)]   # the line: eighths, silent in bars 3-4
        scale = {0, 2, 4, 5, 7, 9, 11}
        struck = {"share": 1.0, "sounds": {"<0.5": None, "0.5-1": 0.5, "1-2": None, "2-4": None, "4+": 0.6}, "longest": 2.0}
        notes, thinned, figs = whole.struck_with(ref, 0, 6, 12, song, "accompaniment", 1, {}, random.Random(1), None, 0.9, scale, None, ref, struck)
        by_start = {round(n[0], 2): round(n[1] - n[0], 3) for n in notes}
        self.assertEqual(by_start[7.5], 2.0)                                                     # the stab before the rest: 0.6 of the 8.5-beat gap would
        self.assertEqual(by_start[4.0], 0.25)                                                    # be 5.1, capped at the token voice's longest; a stab
        self.assertEqual(by_start[16.0], 0.25)                                                   # inside the riff sounds 0.5 of the half-beat gap
        bare = {"share": 1.0, "sounds": {name: None for _, name in rhythm.GAP_CLASSES}, "longest": None}   # a token without the classes or a longest
        notes2, _, _ = whole.struck_with(ref, 0, 6, 12, song, "accompaniment", 1, {}, random.Random(1), None, 0.9, scale, None, ref, bare)
        self.assertAlmostEqual({round(n[0], 2): n[1] - n[0] for n in notes2}[7.5], 0.9 * 8.5)    # the pooled share of the line's gap, uncapped

    def test_the_stabs_sounding_share_is_held_to_the_token_voices(self):
        """Round 115: a stab whose class share would put the voice's sounding share over the token's sounds the token's shortest
        class share of its gap instead; Journey of the Quarry's synth had held 0.9 of its long gaps, an organ where the game stabs."""
        bars = [(4.0 * k, 4.0 * k + 4.0) for k in range(4)]
        song = rhythm.Song("w", 4, 4, bars, [], notes={}, sid="w", game="g", numbers=list(range(4)), parts=[(0, 4, None, "A")], tonic=0, mode="major")
        ref = [(4.0 * k + x, 4.0 * k + x + 0.4, 48.0, 0) for k in range(4) for x in range(4)]   # the line: quarters
        scale = {0, 2, 4, 5, 7, 9, 11}
        struck = {"share": 1.0, "sounds": {"<0.5": 0.7, "0.5-1": 0.2, "1-2": 0.9, "2-4": None, "4+": None}, "longest": 4.9, "sounding": 0.5}
        stats = {}
        notes, _, _ = whole.struck_with(ref, 0, 4, 12, song, "accompaniment", 1, {}, random.Random(1), None, 0.9, scale, None, ref, struck, stats=stats)
        lengths = [round(n[1] - n[0], 2) for n in notes]
        self.assertEqual(set(lengths[:-1]), {0.2, 0.9})                                             # the one-beat gap's 0.9, or the stab: 0.2 of the gap (the
        # last stab's gap is the followed note's own length)
        self.assertLessEqual(stats["sounded"] / stats["played"], 0.5 + 0.05 + 0.05)   # the voice sounds about the token's share of its bars' time (STRUCK_MARGIN 0.05)
        self.assertGreaterEqual(stats["sounded"] / stats["played"], 0.5 - 0.05 - 0.05)
        self.assertEqual(stats["shortened"], sum(1 for x in lengths if x < 0.9))                    # the stabs cut, the last one (its own gap) among them
        loose = dict(struck, sounding=None)                                                        # no share on the token: every stab its class share
        notes2, _, _ = whole.struck_with(ref, 0, 4, 12, song, "accompaniment", 1, {}, random.Random(1), None, 0.9, scale, None, ref, loose)
        self.assertEqual({round(n[1] - n[0], 2) for n in notes2[:-1]}, {0.9})

    def test_the_cell_is_repeated_to_the_token_voices_share(self):
        """Round 116: a stab with a stab of the voice's own at the same place of the bar before takes that stab's pitch while the
        share of such stabs runs under the token's; Battle Theme's synth hammers one cell where the written stabs changed every bar."""
        from bitcomposer.translate import tables
        from bitcomposer.translate.vocab import Span
        bars = [(4.0 * k, 4.0 * k + 4.0) for k in range(8)]
        song = rhythm.Song("w", 4, 4, bars, [Span(0.0, 32.0, 0, "", 1.0)], notes={}, sid="w", game="g", numbers=list(range(8)), parts=[(0, 8, None, "A")], tonic=0, mode="major")
        ref = [(4.0 * k + x, 4.0 * k + x + 0.4, 48.0 + [0, 4, 7, 4][x], 0) for k in range(8) for x in range(4)]   # the line: C E G E every bar
        scale = {0, 2, 4, 5, 7, 9, 11}
        mk = lambda tone, outcome: [tables.Unit(f"s{i}{tone}{outcome}", "g", outcome, {"interval": "11", "tone": tone, "part": "accompaniment", "previous": rhythm.START}) for i in range(3)]   # noqa: E731
        t = tables.Table(("interval", "tone", "part", "previous"), "parallel_intervals", votes=tables.SHARES).fit(mk("root", "fifth") + mk("root", "third") + mk("third", "root") + mk("third", "fifth") + mk("fifth", "root") + mk("fifth", "third"))
        models = {"parallel_intervals": t}
        base = {"share": 1.0, "sounds": {name: None for _, name in rhythm.GAP_CLASSES}, "longest": None, "sounding": None}
        free, _, _ = whole.struck_with(ref, 0, 8, 19, song, "accompaniment", 1, models, random.Random(3), None, 0.5, scale, None, ref, dict(base, cell=None))
        by_bar = lambda notes: [tuple(int(n[2]) for n in notes if 4.0 * k <= n[0] < 4.0 * k + 4.0) for k in range(8)]   # noqa: E731
        self.assertGreater(len(set(by_bar(free))), 1)                                                # drawn anew each bar, the bars differ
        stats = {}
        held, _, _ = whole.struck_with(ref, 0, 8, 19, song, "accompaniment", 1, models, random.Random(3), None, 0.5, scale, None, ref, dict(base, cell=1.0), stats=stats)
        self.assertGreaterEqual(stats["repeats"] / stats["comparable"], 0.85)                         # the cell held bar after bar (the budget counts a stab
        self.assertEqual(stats["comparable"], 28)                                                    # kept until one differs, so a share of one is not exact)
        self.assertLess(len(set(by_bar(held)[1:])), len(set(by_bar(free)[1:])))                      # fewer different bars than drawn free
        some, _, _ = whole.struck_with(ref, 0, 8, 19, song, "accompaniment", 1, models, random.Random(3), None, 0.5, scale, None, ref, dict(base, cell=0.5), stats=stats)
        self.assertTrue(0.4 <= stats["repeats"] / stats["comparable"] <= 0.65, stats)               # held to about the share

    def test_the_mask_is_held_toward_the_token_voices_struck_share(self):
        """Round 108: the second_figures mask thins the followed onsets only as far as the token voice's struck share allows."""
        bars = [(4.0 * k, 4.0 * k + 4.0) for k in range(4)]
        song = rhythm.Song("w", 4, 4, bars, [], notes={}, sid="w", game="g", numbers=list(range(4)), parts=[(0, 4, None, "A")], tonic=0, mode="major")
        ref = [(4.0 * k + x / 2, 4.0 * k + x / 2 + 0.4, 48.0, 0) for k in range(4) for x in range(8)]
        scale = {0, 2, 4, 5, 7, 9, 11}
        every_other = lambda f: " ".join("1 0" for _ in range(len(f.split()) // 2)) + "|"            # noqa: E731  a mask keeping the odd onsets
        full = lambda f: " ".join("1" for _ in f.split()) + "|"                                     # noqa: E731  a mask keeping them all
        for share, mask, want in ((1.0, every_other, 32), (0.5, every_other, 16), (0.5, full, 32), (0.0, every_other, 16)):
            struck = {"share": share, "sounds": {name: None for _, name in rhythm.GAP_CLASSES}, "longest": None}
            notes, thinned, _ = whole.struck_with(ref, 0, 4, 12, song, "accompaniment", 1, {}, random.Random(1), None, 0.5, scale, mask, ref, struck)
            self.assertEqual((len(notes), thinned), (want, 32 - want), (share, want))           # under the share every onset is struck; over it the
            # drawn mask stands (a mask that thins nothing is drawn again, and the same mask comes back)

    def test_struck_stretches_are_counted_into_the_interval_word(self):
        """Round 109: the parallel_intervals word counts the struck-with stretches too, at their own nominal, an off-chord
        landing as semitones from the nominal placing; Battle Theme's synth had no units at its twelfth and drew the thirds'
        and sixths' offsets from the guitar's note."""
        s = self._song()
        units = rhythm.parallel_interval_units([s])
        upper = [u for u in units if u.values["interval"] == "14"]                              # the stabs: struck with the line two octaves up
        self.assertEqual(len(upper), 32)
        self.assertEqual(sorted(set(u.outcome for u in upper)), ["+2", "fifth", "root", "third"])   # C the root, G the fifth, E the third, D two over the nominal C
        self.assertEqual(upper[0].values, {"interval": "14", "tone": "root", "part": "accompaniment", "previous": rhythm.START})
        lower = [u for u in units if u.values["interval"] == "-4"]                              # the lower stab, struck with the upper a fifth under
        self.assertEqual(len(lower), 32)
        self.assertIn("+0", {u.outcome for u in lower})                                         # F a fifth under C: off the chord, at the nominal
        self.assertIn("fifth", {u.outcome for u in lower})

    def test_an_off_chord_pick_lands_near_the_nominal_placing(self):
        """Round 109: an off-chord outcome is semitones from the nominal placing, so a struck voice at a twelfth drawn "+3"
        sits three over the twelfth, not three over the line."""
        from bitcomposer.translate import tables
        from bitcomposer.translate.vocab import Span
        bars = [(4.0 * k, 4.0 * k + 4.0) for k in range(4)]
        song = rhythm.Song("w", 4, 4, bars, [Span(0.0, 16.0, 0, "", 1.0)], notes={}, sid="w", game="g", numbers=list(range(4)), parts=[(0, 4, None, "A")], tonic=0, mode="major")
        t = tables.Table(("interval", "tone", "part", "previous"), "parallel_intervals", votes=tables.SHARES).fit(
            [tables.Unit(f"s{i}", "g", "+3", {"interval": "11", "tone": "root", "part": "accompaniment", "previous": p}) for i in range(8) for p in (rhythm.START, "+3")])
        line = [(float(i), i + 0.4, 48.0, 0) for i in range(16)]                                 # C, the chord's root, every beat
        drawn = whole.parallel(line, 19, {0, 2, 4, 5, 7, 9, 11}, 1, song, "accompaniment", {"parallel_intervals": t}, random.Random(1))
        self.assertEqual({int(m) - 48 for a, b, m, v in drawn}, {22})                           # three over the twelfth, not three over the C

    def test_a_one_song_nominal_keeps_its_own_chain(self):
        """Round 110: where one song alone plays a nominal, the interval word's chain (the landing before) stands with that
        song behind it; the draw had passed over any level under two songs, so Battle Theme's phrase-shaped excursions at
        its twelfth came out as single pops drawn apart."""
        from bitcomposer.translate import tables
        from bitcomposer.translate.vocab import Span
        bars = [(4.0 * k, 4.0 * k + 4.0) for k in range(8)]
        song = rhythm.Song("w", 4, 4, bars, [Span(0.0, 32.0, 0, "", 1.0)], notes={}, sid="w", game="g", numbers=list(range(8)), parts=[(0, 8, None, "A")], tonic=0, mode="major")
        chain = [("start", "root")] + [("root", "+12")] * 40 + [("+12", "root")] * 40                        # one song: root, then an octave up, then back, in turn
        t = tables.Table(("interval", "tone", "part", "previous"), "parallel_intervals", votes=tables.SHARES).fit(
            [tables.Unit("one", "g", o, {"interval": "11", "tone": "root", "part": "accompaniment", "previous": p}) for p, o in chain])
        self.assertEqual(t.songs.get(("11",)), 1)
        line = [(float(i), i + 0.4, 48.0, 0) for i in range(32)]                                   # C, the chord's root, every beat
        drawn = [int(m) for a, b, m, v in whole.parallel(line, 19, {0, 2, 4, 5, 7, 9, 11}, 1, song, "accompaniment", {"parallel_intervals": t}, random.Random(1))]
        alternations = sum(1 for x, y in zip(drawn, drawn[1:]) if x != y)
        self.assertGreater(alternations, 24, drawn)                                                  # the chain: root, +12, root, +12, nearly every step
        self.assertEqual(set(drawn), {72, 79}, drawn)                                                # C, the root nearest the twelfth, and the octave over the nominal
        two = tables.Table(("interval", "tone", "part", "previous"), "parallel_intervals", votes=tables.SHARES).fit(
            [tables.Unit(s, "g", o, {"interval": "11", "tone": "root", "part": "accompaniment", "previous": p}) for s in ("one", "two") for p, o in chain])
        self.assertEqual(two.songs.get(("11",)), 2)                                                 # two songs: the chain stands as before
        drawn2 = [int(m) for a, b, m, v in whole.parallel(line, 19, {0, 2, 4, 5, 7, 9, 11}, 1, song, "accompaniment", {"parallel_intervals": two}, random.Random(1))]
        self.assertGreater(sum(1 for x, y in zip(drawn2, drawn2[1:]) if x != y), 24, drawn2)


class TokenProfileTests(unittest.TestCase):
    """Round 111: a backing line's chord-tone profile rides the balance token, and the chord-part and bass writers hold the line's
    chord tones to it: Battle Theme's guitar plays the root on 0.45 of its notes and the seventh on 0.30, where the written lines
    on its token had played fifths and thirds and never the seventh."""

    def _song(self):
        from bitcomposer.translate.vocab import Span
        bars = [(4.0 * k, 4.0 * k + 4.0) for k in range(8)]
        chords = [Span(0.0, 32.0, 0, "7", 1.0)]                                                                # C7 throughout
        line = [(4.0 * k + i, 0.9, (48.0, 48.0, 55.0, 58.0)[i], "g") for k in range(8) for i in range(4)]   # C C G Bb: root, root, fifth, seventh
        bass = [(4.0 * k + i, 0.9, (36.0, 43.0, 36.0, 46.0)[i], "b") for k in range(8) for i in range(4)]   # C G C Bb
        tune = [(4.0 * k + i, 0.9, 72.0 + i, "m") for k in range(8) for i in range(4)]
        s = rhythm.Song("t", 4, 12, bars, chords, notes={"accompaniment": line, "bass": bass, "melody": tune}, sid="s", game="g",
                        numbers=list(range(8)), parts=[(0, 8, None, "A")], tonic=0, mode="major")
        s.voice_notes = {0: ("accompaniment", line), 1: ("bass", bass), 2: ("melody", tune)}
        s.voice_levels = {0: 0.3, 1: 0.5, 2: 0.4}; s.levels = {"accompaniment": 0.3, "bass": 0.5, "melody": 0.4}
        return s

    def test_the_token_carries_the_lines_chord_tone_profile(self):
        s = self._song()
        self.assertEqual(rhythm.line_tone_profile(s, "accompaniment"), "t50/0/25/25/0/0")                   # root, third, fifth, seventh, sus, other
        self.assertEqual(rhythm.line_tone_profile(s, "bass"), "t50/0/25/25/0/0")
        tok = rhythm.balance_units([s])[0].outcome
        acc = next(f for f in tok.split() if f.startswith("accompaniment=")).split("=", 1)[1].split(":")
        bass = next(f for f in tok.split() if f.startswith("bass=")).split("=", 1)[1].split(":")
        self.assertEqual((acc[15], bass[15]), ("t50/0/25/25/0/0", "t50/0/25/25/0/0"), (acc, bass))
        self.assertEqual(whole.tone_profile_of("t45/2/9/30/2/12"), {"root": 0.45, "third": 0.02, "fifth": 0.09, "seventh": 0.30, "sus": 0.02, "other": 0.12})
        self.assertIsNone(whole.tone_profile_of("b75/70"))

    def test_a_lines_tone_is_held_to_the_profile(self):
        from collections import Counter
        from bitcomposer.translate.writer import parts
        profile = {"root": 0.5, "seventh": 0.5}
        self.assertEqual(parts.profile_tone(0, 0, "7", profile, Counter()), 0)                               # nothing written yet: the tone meant
        self.assertEqual(parts.profile_tone(0, 0, "7", profile, Counter({"root": 6})), 10)                   # roots over their share: the seventh, most under
        self.assertEqual(parts.profile_tone(0, 0, "7", profile, Counter({"root": 3, "seventh": 4})), 0)      # within the margin: the tone meant
        self.assertEqual(parts.profile_tone(7, 0, "7", profile, Counter({"fifth": 2, "root": 1})), 10)       # a fifth the profile never plays: the tone most under
        self.assertEqual(parts.profile_tone(7, 0, "", {"fifth": 1.0}, Counter({"root": 4})), 7)              # the fifth is under its share: kept
        # the bass: its marks' tones under the profile
        from bitcomposer.translate.vocab import Span
        bars = [(0.0, 4.0)]
        song = rhythm.Song("w", 4, 4, bars, [Span(0.0, 4.0, 0, "", 1.0)], notes={}, sid="w", game="g", numbers=[0], parts=[(0, 1, None, "A")], tonic=0, mode="major")
        scale = {0, 2, 4, 5, 7, 9, 11}
        plain, _, _ = parts.realize("0:R 1:5 2:R 3:5", 0.0, 4.0, song, 36, 0.8, scale, 0)
        self.assertEqual([int(m) % 12 for a, b, m in plain], [0, 7, 0, 7])
        counts = Counter()
        held, _, _ = parts.realize("0:R 1:5 2:R 3:5", 0.0, 4.0, song, 36, 0.8, scale, 0, profile={"root": 1.0}, counts=counts)
        self.assertEqual([int(m) % 12 for a, b, m in held], [0, 0, 0, 0])                                     # every fifth over its share of none: the root
        self.assertEqual(counts, Counter({"root": 4}))


class TokenShapeTests(unittest.TestCase):
    """Round 112: the song's chord-shape profile rides the balance token (`shapes=`), and the chord chain holds a changing chord's
    quality to it: Battle Theme's reading has a seventh chord on 0.56 of its beats, the songs written on its token on a tenth of
    their bars, and the guitar held to the riff's sevenths (round 111) had none to play."""

    def _song(self):
        from bitcomposer.translate.vocab import Span
        bars = [(4.0 * k, 4.0 * k + 4.0) for k in range(8)]
        chords = [Span(0.0, 16.0, 0, "7", 1.0), Span(16.0, 32.0, 0, "", 1.0)]                                 # C7 four bars, C four bars
        line = [(4.0 * k + i, 0.9, (48.0, 48.0, 55.0, 55.0)[i], "g") for k in range(8) for i in range(4)]
        bass = [(4.0 * k + i, 0.9, (36.0, 43.0, 36.0, 43.0)[i], "b") for k in range(8) for i in range(4)]
        tune = [(4.0 * k + i, 0.9, 72.0 + i, "m") for k in range(8) for i in range(4)]
        s = rhythm.Song("t", 4, 12, bars, chords, notes={"accompaniment": line, "bass": bass, "melody": tune}, sid="s", game="g",
                        numbers=list(range(8)), parts=[(0, 8, None, "A")], tonic=0, mode="major")
        s.voice_notes = {0: ("accompaniment", line), 1: ("bass", bass), 2: ("melody", tune)}
        s.voice_levels = {0: 0.3, 1: 0.5, 2: 0.4}; s.levels = {"accompaniment": 0.3, "bass": 0.5, "melody": 0.4}
        return s

    def test_the_token_carries_the_songs_chord_shapes(self):
        s = self._song()
        self.assertEqual(rhythm.chord_shape_profile(s), "maj:50/7:50")                                     # equal shares: the plain triad first
        self.assertIn("shapes=maj:50/7:50", rhythm.balance_units([s])[0].outcome.split())
        self.assertEqual(whole.shape_profile_of("maj7:45/5:17/maj:3"), {"maj7": 0.45, "5": 0.17, "": 0.03})
        self.assertIsNone(whole.shape_profile_of("x9:50"))
        for name, shape, want in (("IV", "maj7", "IVmaj7"), ("IVmaj7", "", "IV"), ("iv", "m7", "iv7"), ("V7", "m", "v"), ("bVII", "5", "bVII5"), ("ii7", "7", "II7"), ("vi", "dim", "vidim")):
            self.assertEqual(whole.with_shape(name, shape), want, (name, shape))
            self.assertEqual(whole.chord_of(want, 0, "major")[1], shape, want)                            # the same degree in the shape asked

    def test_a_changing_chords_quality_is_held_to_the_profile(self):
        parts = [(0, 4, None, "A")]
        names, chords = whole.plan_chords({}, parts, 0, 0, "major", random.Random(1), [])                   # no chord word: the home chord a bar
        self.assertEqual(names, ["I"] * 4)
        names, chords = whole.plan_chords({}, parts, 0, 0, "major", random.Random(1), [], shape_profile={"maj7": 1.0})
        self.assertEqual((names, chords), (["Imaj7"] * 4, [(0, "maj7")] * 4))                                # every bar the quality the song has
        log = []
        names, chords = whole.plan_chords({}, parts, 0, 0, "major", random.Random(1), log, shape_profile={"": 0.5, "maj7": 0.5})
        self.assertEqual(names, ["Imaj7", "I", "I", "I"])                                                   # the first bar takes the quality most under its share, the
        # second changes back within the margin, and a chord the chain repeats keeps its quality: the hold acts where the chord changes
        self.assertTrue(any(l.startswith("chord shapes held to the balance's song's profile") for l in log), log)
        names, _ = whole.plan_chords({}, [(0, 4, None, "A"), (4, 4, 0, "A")], 0, 0, "major", random.Random(1), [], shape_profile={"": 0.5, "maj7": 0.5})
        self.assertEqual(names[4:], names[:4])                                                               # a repeated part keeps its chords whole


class TokenFormTests(unittest.TestCase):
    """Round 113: the song's form letters ride the balance token (`form=`), and the plan takes them in place of the letters draw:
    Battle Theme is A B C B D, the B returning after C, and the songs written on its token had come out A B C D E F or A B C C D."""

    def test_the_token_carries_the_form(self):
        from bitcomposer.translate.vocab import Span
        bars = [(4.0 * k, 4.0 * k + 4.0) for k in range(8)]
        line = [(4.0 * k + i, 0.9, 48.0, "g") for k in range(8) for i in range(4)]
        s = rhythm.Song("t", 4, 12, bars, [Span(0.0, 32.0, 0, "", 1.0)], notes={"accompaniment": line}, sid="s", game="g", numbers=list(range(8)),
                        parts=[(0, 2, None, "A"), (2, 2, None, "B"), (4, 2, None, "C"), (6, 2, 1, "B")], tonic=0, mode="major")
        s.voice_notes = {0: ("accompaniment", line)}; s.voice_levels = {0: 0.3}; s.levels = {"accompaniment": 0.3}
        self.assertEqual(rhythm.form_field(s), "A2B2C2B2")
        self.assertIn("form=A2B2C2B2", rhythm.balance_units([s])[0].outcome.split())
        self.assertEqual(whole.form_of("A2B8C9B8D14"), [("A", 2), ("B", 8), ("C", 9), ("B", 8), ("D", 14)])
        self.assertIsNone(whole.form_of("ABCBD"))
        s.parts = [(0, 8, None, "A")]
        self.assertEqual(rhythm.form_field(s), "")                                                 # one part: no form to carry

    def test_the_plan_takes_the_tokens_form(self):
        log = []
        parts = whole.plan_form({}, random.Random(1), log, form=[("A", 2), ("B", 8), ("C", 9), ("B", 8), ("D", 14)])
        self.assertEqual([p[3] for p in parts], ["A", "B", "C", "B", "D"])
        self.assertEqual([p[1] for p in parts], [2, 8, 9, 8, 14])                                        # the token song's bars
        self.assertEqual(parts[3][2], 1)                                                           # the second B repeats the first
        self.assertEqual(parts[3][1], parts[1][1])                                                 # and is as long
        self.assertEqual([p[0] for p in parts], [sum(q[1] for q in parts[:i]) for i in range(5)])   # the bars run on
        self.assertEqual([p[3] for p in whole.plan_form({}, random.Random(1), [])], ["A", "B", "C"])   # without the token: the sizes and form words (defaults)
        parts = whole.plan_form({}, random.Random(1), [], form=[("A", 2), ("B", 15), ("C", 5), ("B", 2)])
        self.assertEqual([p[1] for p in parts], [2, 15, 5, 15])                                          # a part read returning with other bars plays whole, at its first statement's

    def test_a_token_form_short_of_the_bars_asked_leaves_the_draw(self):
        mk = lambda name, outcome, **vals: [tables.Unit(f"s{i}", "g", outcome, vals) for i in range(3)]   # noqa: E731
        token = "melody=main:64-84:0.9:1:0.7:::slead accompaniment=half:60-72:0.8:1:0.6:::sstr bass=half:36-44:0.9:1:1.0:::sbass top=0.30 tempo=medium form=A2B12"
        bal = {"balance": tables.Table(("part",), "balance", votes=tables.SHARES).fit(mk("balance", token, part=rhythm.ARRANGEMENT))}
        p = whole.plan(bal, 7, "g", min_bars=16)
        self.assertEqual([q[3] for q in p.parts], ["A", "B", "C"])                                 # the draw stands (the defaults' three parts)
        self.assertTrue(any("short of the 16 asked: the draw" in l for l in p.log), p.log)
        self.assertEqual([(q[3], q[1]) for q in whole.plan(bal, 7, "g").parts], [("A", 2), ("B", 12)])   # without a minimum the token's form is taken


class SectionFillTests(unittest.TestCase):
    """Round 118: the section_fills word says what a voice does in a section's last bar (fuller, the same, thinner) by its part,
    whether it is the line or a voice beside it, and the section's place; the plan draws it a section and the writers fill."""

    def _song(self):
        from bitcomposer.translate.vocab import Span
        bars = [(4.0 * k, 4.0 * k + 4.0) for k in range(8)]
        line = [(4.0 * k + i, 0.8, 48.0, "g") for k in range(8) for i in range(4)]                          # the guitar: four a bar throughout
        stabs = [(4.0 * k + i, 0.2, 72.0, "s") for k in range(8) for i in ((0, 2) if k != 3 else (0, 0.5, 1, 1.5, 2, 2.5, 3))]   # the synth: two a bar,
        s = rhythm.Song("t", 4, 12, bars, [Span(0.0, 32.0, 0, "", 1.0)], notes={"accompaniment": line + stabs}, sid="s", game="g",   # seven in A's last
                        numbers=list(range(8)), parts=[(0, 4, None, "A"), (4, 4, None, "B")], tonic=0, mode="major")
        s.voice_notes = {0: ("accompaniment", line), 1: ("accompaniment", stabs)}
        return s

    def test_the_word_counts_a_sections_last_bar(self):
        units = rhythm.section_fill_units([self._song()])
        self.assertEqual([(u.values["part"], u.values["voice"], u.values["place"], u.outcome) for u in units],
                         [("accompaniment", "line", "first", "same"), ("accompaniment", "line", "last", "same"),
                          ("accompaniment", "beside", "first", "fuller"), ("accompaniment", "beside", "last", "same")])
        from bitcomposer.translate import packtables
        self.assertEqual(packtables.KEPT["section_fills"][3], ("part", "voice", "place"))
        s = self._song(); s.parts = [(0, 3, None, "A"), (3, 5, None, "B")]                                # a section under FILL_BARS bars counts nothing
        self.assertEqual([u.values["place"] for u in rhythm.section_fill_units([s])], ["last", "last"])

    def test_the_plan_draws_a_fill_and_the_struck_voice_fills(self):
        from bitcomposer.translate import tables
        mk = lambda voice, outcome: [tables.Unit(f"s{i}{voice}", "g", outcome, {"part": "accompaniment", "voice": voice, "place": "first"}) for i in range(3)]   # noqa: E731
        t = tables.Table(("part", "voice", "place"), "section_fills", votes=tables.SHARES).fit(mk("beside", "fuller") + mk("line", "same"))
        parts = [(0, 4, None, "A"), (4, 4, 0, "A"), (8, 2, None, "B")]
        log = []
        fills = whole.plan_section_fills({"section_fills": t}, parts, ["accompaniment", "bass"], {"accompaniment": [True] * 10, "bass": [True] * 10},
                                         {"accompaniment": 3, "bass": 1}, random.Random(1), log)
        self.assertEqual(fills["accompaniment"]["beside"], [0, 0, 0, 1, 0, 0, 0, 1, 0, 0])                 # the fill on A's last bar, and its repeat's
        self.assertEqual(fills["accompaniment"]["line"], [0] * 10)                                        # the line the same; B too short to draw
        self.assertEqual(fills["bass"]["beside"], [0] * 10)                                               # one voice: no beside draw
        self.assertTrue(any("fills by section" in l for l in log), log)
        bars = [(4.0 * k, 4.0 * k + 4.0) for k in range(4)]
        song = rhythm.Song("w", 4, 4, bars, [], notes={}, sid="w", game="g", numbers=list(range(4)), parts=[(0, 4, None, "A")], tonic=0, mode="major")
        ref = [(4.0 * k + x, 4.0 * k + x + 0.4, 48.0, 0) for k in range(4) for x in range(4)]              # the line: quarters
        scale = {0, 2, 4, 5, 7, 9, 11}
        stats = {}
        notes, thinned, figs = whole.struck_with(ref, 0, 4, 12, song, "accompaniment", 1, {}, random.Random(1), None, 0.5, scale, None, ref, None,
                                                 stats=stats, fills=[0, 0, 0, 1])
        per_bar = [sum(1 for n in notes if 4.0 * k <= n[0] < 4.0 * k + 4.0) for k in range(4)]
        self.assertEqual(per_bar, [4, 4, 4, 7])                                                            # the fill bar: every onset and one between each pair
        self.assertEqual(stats["filled"], 3)
        self.assertEqual(figs[3], rhythm.pattern(rhythm.position(x / 2, 4) for x in range(7)))
        thin, thinned2, _ = whole.struck_with(ref, 0, 4, 12, song, "accompaniment", 1, {}, random.Random(1), None, 0.5, scale, None, ref, None, fills=[0, -1, 0, 0])
        self.assertEqual([sum(1 for n in thin if 4.0 * k <= n[0] < 4.0 * k + 4.0) for k in range(4)], [4, 1, 4, 4])   # a thinning: the first onset alone


class TokenStepTests(unittest.TestCase):
    """Round 117: a backing line's step profile rides the balance token (`j63/24/13`: the share of its moves that repeat the pitch, step
    within a whole tone, or leap), and the line is held to it once written: Battle Theme's guitar is a chug on A and B-flat where the
    written guitar leaped between chord tones."""

    def test_the_token_carries_the_steps(self):
        from bitcomposer.translate.vocab import Span
        bars = [(4.0 * k, 4.0 * k + 4.0) for k in range(8)]
        chug = [(4.0 * k + i / 2, 0.4, 45.0 if i % 4 != 3 else 46.0, "g") for k in range(8) for i in range(8)]   # A A A B-flat, eighths
        s = rhythm.Song("t", 4, 12, bars, [Span(0.0, 32.0, 9, "m", 1.0)], notes={"accompaniment": chug}, sid="s", game="g", numbers=list(range(8)),
                        parts=[(0, 8, None, "A")], tonic=9, mode="minor")
        s.voice_notes = {0: ("accompaniment", chug)}; s.voice_levels = {0: 0.3}; s.levels = {"accompaniment": 0.3}
        self.assertEqual(rhythm.step_class(0), "same"); self.assertEqual(rhythm.step_class(-2), "step"); self.assertEqual(rhythm.step_class(3), "leap")
        self.assertEqual(rhythm.line_step_profile(s, "accompaniment"), "j51/49/0")                   # 63 moves: 32 the same pitch, 31 a semitone
        acc = next(f for f in rhythm.balance_units([s])[0].outcome.split() if f.startswith("accompaniment=")).split("=", 1)[1].split(":")
        self.assertEqual(acc[17], "j51/49/0")
        self.assertEqual(whole.step_profile_of("j63/24/13"), {"same": 0.63, "step": 0.24, "leap": 0.13})
        self.assertIsNone(whole.step_profile_of("t63/24/13"))
        self.assertEqual(rhythm.line_step_profile(s, "accompaniment", chug[:10]), "")               # under WORD_NOTES moves: no field

    def test_the_line_is_held_to_the_tokens_steps(self):
        from bitcomposer.translate.vocab import Span
        bars = [(4.0 * k, 4.0 * k + 4.0) for k in range(4)]
        song = rhythm.Song("w", 4, 4, bars, [Span(0.0, 16.0, 0, "", 1.0)], notes={}, sid="w", game="g", numbers=list(range(4)), parts=[(0, 4, None, "A")], tonic=0, mode="major")
        line = [(4.0 * k + i, 4.0 * k + i + 0.8, float([48, 55, 52, 59][i]), 0) for k in range(4) for i in range(4)]   # C G E B: every move a leap
        p = whole.plan({}, 3, "g")
        p.tonic, p.mode = 0, "major"
        p.step_profiles = {"accompaniment": {"same": 0.6, "step": 0.3, "leap": 0.1}}
        shared = {("line", (0, rhythm.position(1.0, 4))): 55.0, ("taken", (0, rhythm.position(1.0, 4))): {55}}
        held, log = whole.hold_line_steps(p, song, "accompaniment", list(line), shared, (40, 64))
        classes = [rhythm.step_class(int(b[2]) - int(a[2])) for a, b in zip(held, held[1:])]
        self.assertGreaterEqual(classes.count("same") / len(classes), 0.5)                            # most moves the pitch again
        self.assertLessEqual(classes.count("leap") / len(classes), 0.2)                               # few leaps left (the first move is free)
        self.assertTrue(all(40 <= n[2] <= 64 for n in held))
        self.assertTrue(log and "notes moved" in log[0], log)
        self.assertEqual(shared[("line", (0, rhythm.position(1.0, 4)))], held[1][2])                 # the voices beside the line see the held note
        same, _ = whole.hold_line_steps(p, song, "accompaniment", list(line), None, (40, 64))
        p.step_profiles = {}
        self.assertEqual(whole.hold_line_steps(p, song, "accompaniment", list(line), None, (40, 64)), (list(line), []))   # no profile: as written


class TokenContinuityTests(unittest.TestCase):
    """Round 114: the bass line's pitch continuity rides the balance token, and the bass writer holds its pitch class across bar lines
    to it: Battle Theme's bass keeps its riff's pitch under the chord reader's changes on 0.57 of its bar lines, the written basses
    walked the chain's roots on 0.26."""

    def test_the_token_carries_the_bass_continuity(self):
        from bitcomposer.translate.vocab import Span
        bars = [(4.0 * k, 4.0 * k + 4.0) for k in range(10)]
        mains = (0, 0, 7, 0, 0, 0, 5, 5, 0, 0)                                                         # C C G C C C F F C C: 9 transitions, 5 kept
        bass = [(4.0 * k + i, 0.9, 36.0 + mains[k], "b") for k in range(10) for i in range(4)]
        tune = [(4.0 * k + i, 0.9, 72.0, "m") for k in range(10) for i in range(4)]
        s = rhythm.Song("t", 4, 12, bars, [Span(0.0, 40.0, 0, "", 1.0)], notes={"bass": bass, "melody": tune}, sid="s", game="g",
                        numbers=list(range(10)), parts=[(0, 10, None, "A")], tonic=0, mode="major")
        s.voice_notes = {0: ("bass", bass), 1: ("melody", tune)}; s.voice_levels = {0: 0.5, 1: 0.4}; s.levels = {"bass": 0.5, "melody": 0.4}
        self.assertEqual(rhythm.bass_continuity_field(s), "k56")
        tok = rhythm.balance_units([s])[0].outcome
        bass_f = next(f for f in tok.split() if f.startswith("bass=")).split("=", 1)[1].split(":")
        self.assertEqual(bass_f[16], "k56")
        self.assertEqual(rhythm.bass_continuity_field(s, bass[:16]), "")                              # under CONTINUITY_BARS transitions: no field

    def test_a_bar_is_realized_on_the_bar_befores_pitch_class(self):
        from bitcomposer.translate.writer import parts
        from bitcomposer.translate.vocab import Span
        song = rhythm.Song("w", 4, 4, [(0.0, 4.0)], [Span(0.0, 4.0, 0, "", 1.0)], notes={}, sid="w", game="g", numbers=[0], parts=[(0, 1, None, "A")], tonic=0, mode="major")
        scale = {0, 2, 4, 5, 7, 9, 11}
        plain, _, _ = parts.realize("0:R 1:5 2:R 3:5", 0.0, 4.0, song, 36, 0.8, scale, 0)
        self.assertEqual([int(m) % 12 for a, b, m in plain], [0, 7, 0, 7])                             # C and G over C
        moved = []
        held, _, _ = parts.realize("0:R 1:5 2:R 3:5", 0.0, 4.0, song, 36, 0.8, scale, 0, root_override=9, moved=moved)
        self.assertEqual([int(m) % 12 for a, b, m in held], [9, 9, 9, 4])                              # the bar on A: A, its fifth E where A outnumbers it (the
        self.assertEqual(moved, [1])                                                                 # earliest fifth moved onto the pedal), the chord's shape kept
        self.assertEqual(int(held[1][2]), 45)                                                        # in the octave nearest its own (E 40 -> A 45, not 33)
        from collections import Counter
        counts = Counter()
        held, _, _ = parts.realize("0:5 1:+ 3/2:5 2:R", 0.0, 4.0, song, 36, 0.8, scale, 0, counts=counts, root_override=0, moved=moved)
        self.assertEqual([int(m) % 12 for a, b, m in held], [0, 0, 7, 0])                              # G A G C: the passing tone first, then the earliest fifth
        self.assertEqual(moved, [1, 2])
        self.assertEqual({k: v for k, v in counts.items() if v}, {"root": 3, "fifth": 1})          # the classes written stay counted true

    def test_a_line_on_the_basss_pedal_is_over_the_riffs_root_for_the_struck_voice(self):
        from bitcomposer.translate import tables
        from bitcomposer.translate.vocab import Span
        mk = lambda tone, outcome: [tables.Unit(f"s{i}", "g", outcome, {"interval": "11", "tone": tone, "part": "accompaniment", "previous": rhythm.START}) for i in range(3)]   # noqa: E731
        t = tables.Table(("interval", "tone", "part", "previous"), "parallel_intervals", votes=tables.SHARES).fit(mk("root", "fifth") + mk("other", "+19"))
        major = {0, 2, 4, 5, 7, 9, 11}
        song = rhythm.Song("w", 4, 4, [(0.0, 4.0)], [Span(0.0, 4.0, 0, "", 1.0)], notes={}, sid="w", game="g", numbers=[0], parts=[(0, 1, None, "A")], tonic=0, mode="major")
        line = [(0.0, 0.9, 62.0, 0)]                                                                  # a D over C major: off the chord
        song.notes["bass"] = [(0.0, 0.9, 36.0, "bass")]                                               # the bass on C: the D is the line's own
        high = whole.parallel(line, 19, major, 1, song, "accompaniment", {"parallel_intervals": t}, random.Random(1))
        self.assertEqual(int(high[0][2]), 62 + 19 + 19)                                              # "other": the game's synth leaps, +19 over the twelfth
        song.notes["bass"] = [(0.0, 0.9, 38.0, "bass")]                                               # the bass pedals on D under the chord: the line rides it
        log = []
        low = whole.parallel(line, 19, major, 1, song, "accompaniment", {"parallel_intervals": t}, random.Random(1), None, log)
        self.assertEqual(int(low[0][2]) % 12, 7)                                                      # drawn as over the riff's root: the chord's fifth near the twelfth
        self.assertLess(int(low[0][2]), 62 + 19 + 6)
        self.assertTrue(any("1 of the line's notes on the bass's pedal" in l for l in log), log)

    def test_the_bass_as_finally_played_is_held(self):
        from bitcomposer.translate.vocab import Span
        bars = [(4.0 * k, 4.0 * k + 4.0) for k in range(4)]
        song = rhythm.Song("w", 4, 4, bars, [Span(4.0 * k, 4.0 * k + 4.0, 0 if k % 2 == 0 else 7, "", 1.0) for k in range(4)], notes={}, sid="w", game="g",
                           numbers=list(range(4)), parts=[(0, 4, None, "A")], tonic=0, mode="major")
        bass = [(4.0 * k + i, 4.0 * k + i + 0.8, 36.0 if k % 2 == 0 else 43.0, 0) for k in range(4) for i in (0, 2)]   # C C | G G | C C | G G: the roots
        song.notes["bass"] = [(a, b - a, m, "bass") for a, b, m, _ in bass]
        rider = [(8.0, 8.8, 48.0, 0), (8.0, 8.8, 67.0, 1), (8.0, 8.8, 64.0, 2), (10.0, 10.8, 62.0, 0)]   # the accompaniment on the bass's C at bar 3 with a
        song.notes["accompaniment"] = [(a, b - a, m, "accompaniment") for a, b, m, _ in rider]      # voice struck with its line (+19) and a stacked E; then a D
        written = {"bass": whole.Part("bass", list(bass), ["0:R 2:R"] * 4, []), "accompaniment": whole.Part("accompaniment", list(rider), [""] * 4, [])}
        p = whole.plan({}, 3, "g")
        p.bass_continuity, p.tone_profiles, p.bounds, p.registers = 0.9, {}, {}, {"bass": (32, 44)}
        p.layer_relations = {"accompaniment": ["wl+19", None]}                                      # the third voice has no relation word
        log = whole.hold_bass_pitch(p, song, written, list(bass))
        mains = [max(set(int(m) % 12 for a, b, m, v in written["bass"].notes if 4 * k <= a < 4 * k + 4), key=lambda pc: sum(1 for a, b, m, v in written["bass"].notes if 4 * k <= a < 4 * k + 4 and int(m) % 12 == pc)) for k in range(4)]
        self.assertEqual(mains, [0, 7, 7, 7])                                                      # the first bar line is free (the budget counts it kept), the
        self.assertTrue(log and "2 of 3 kept" in log[0] and "1 more bars pedaled" in log[0], log)   # second pedals bar 3 on G, the third keeps
        self.assertEqual(int(written["accompaniment"].notes[0][2]), 43)                            # the rider's C at bar 3 moved with the bass to G, nearest
        self.assertEqual(int(written["accompaniment"].notes[1][2]), 62)                            # the voice struck with the line moved the same (67 -> 62)
        self.assertEqual(int(written["accompaniment"].notes[2][2]), 64)                            # the stacked voice, no relation word, stays
        self.assertEqual(int(written["accompaniment"].notes[3][2]), 62)                            # its D, not the bass's pitch class, stays
        self.assertEqual(sorted(int(x[2]) for x in song.notes["accompaniment"]), [43, 62, 62, 64])   # the song's notes follow
        self.assertEqual(sorted(int(x[2]) % 12 for x in song.notes["bass"]), [0, 0, 7, 7, 7, 7, 7, 7])   # the song's bass notes follow
        song.notes["bass"] = [(a, b - a, m, "bass") for a, b, m, _ in bass]
        written = {"bass": whole.Part("bass", list(bass), ["0:R 2:R"] * 4, [])}
        log = whole.hold_bass_pitch(p, song, written, bass[:2] + [(a + 0.5, b + 0.5, m, v) for a, b, m, v in bass[2:]])   # bars 2-4 not as the writer wrote them
        self.assertTrue(log and "0 of 3 kept" in log[0] and "3 bars rewritten" in log[0] and "0 more bars pedaled" in log[0], log)
        self.assertEqual(sorted(int(x[2]) % 12 for x in written["bass"].notes), [0, 0, 0, 0, 7, 7, 7, 7])   # left as they are


class TokenRiffTests(unittest.TestCase):
    """Round 106: a backing part's own period and holds, how far a chord part's line rides the bass, and the song's chord-hold
    share ride the balance token; the plan takes them, and the chord part's line plays the written bass's figure."""

    def _song(self):
        from bitcomposer.translate.vocab import Span
        bars = [(4.0 * k, 4.0 * k + 4.0) for k in range(12)]
        chords = [Span(0.0, 24.0, 0, "", 1.0), Span(24.0, 48.0, 7, "", 1.0)]                                   # C for six bars, G for six
        bass = [(4.0 * k + x / 2, 0.45, 36.0 if x % 2 == 0 else 43.0, "b") for k in range(12) for x in range(8)]   # one bar of root-fifth eighths, every bar
        riff = [(4.0 * k + x / 2, 0.45, (48.0 if x % 2 == 0 else 55.0) if k < 6 else 52.0 + (x % 3), "g") for k in range(12) for x in range(8)]   # six bars on the bass's riff an octave up, six bars its own on the same onsets
        tune = [(4.0 * k + x, 0.9, 72.0 + x, "m") for k in range(12) for x in (0.0, 1.0, 2.0, 3.0)]
        s = rhythm.Song("t", 4, 12, bars, chords, notes={"accompaniment": riff, "bass": bass, "melody": tune}, sid="s", game="g",
                        numbers=list(range(12)), parts=[(0, 12, None, "A")], tonic=0, mode="major")
        s.voice_notes = {0: ("accompaniment", riff), 1: ("bass", bass), 2: ("melody", tune)}
        s.voice_levels = {0: 0.3, 1: 0.5, 2: 0.4}; s.levels = {"accompaniment": 0.3, "bass": 0.5, "melody": 0.4}
        return s

    def test_the_token_carries_the_riff_fields(self):
        s = self._song()
        self.assertEqual(rhythm.line_rides_field(s, "accompaniment"), "b100/50")                # every onset with the bass, six bars of twelve at its pitch class
        self.assertEqual(rhythm.part_period_field(s, "bass"), "p1/91")                          # the bass repeats its bar every bar; at the chord change its
                                                                                                 # marks change (C and G on G: root and fourth), one bar of eleven varied
        self.assertAlmostEqual(rhythm.chord_hold_share(s), 10 / 11)                              # one change at bar line 6 of eleven
        tok = rhythm.balance_units([s])[0].outcome
        acc = next(f for f in tok.split() if f.startswith("accompaniment=")).split("=", 1)[1].split(":")
        self.assertEqual(acc[14], "b100/50", acc)
        bass = next(f for f in tok.split() if f.startswith("bass=")).split("=", 1)[1].split(":")
        self.assertEqual(bass[13], "p1/91", bass)
        self.assertIn("holds=0.91", tok)
        self.assertNotIn("holds", " ".join(f for f in tok.split() if f.startswith("melody=")))

    def test_the_plan_takes_the_riff_fields(self):
        from bitcomposer.translate import tables
        token = ("accompaniment=main:48-55:0.9:1:0.6:::sacc0123456@44-60:dense+repeating:0.50::block:rare::b75/70 "
                 "bass=half:36-44:0.9:1:1.0:::sbass::::::p2/83 top=0.30 tempo=medium holds=0.80")
        units_ = lambda outcome, **v: [tables.Unit(f"s{i}", "g", outcome, v) for i in range(3)]   # noqa: E731
        periods = []
        for length in ("short", "medium", "long"):
            for tempo in ("slow", "medium", "fast"):
                periods += units_("1", part="bass", length=length, tempo=tempo) + units_("1", part="accompaniment", length=length, tempo=tempo)
        models = {"balance": tables.Table(("part",), "balance", votes=tables.SHARES).fit(units_(token, part=rhythm.ARRANGEMENT)),
                  "periods": tables.Table(("part", "length", "tempo"), "periods", votes=tables.SHARES).fit(periods)}
        p = whole.plan(models, 3, "g")
        self.assertEqual(p.extras["accompaniment"]["rides"], (0.75, 0.70))
        self.assertTrue(any(l.startswith("accompaniment's line rides the bass from the balance: 0.75 of its onsets") for l in p.log), p.log)
        self.assertTrue(any(l.startswith("bass period:") and "every 2 bars" in l and "held 0.83" in l for l in p.log), [l for l in p.log if "period" in l])
        self.assertTrue(any(l.startswith("chords held at the balance's song's share 0.80:") for l in p.log), p.log)
        self.assertNotIn("rides", p.extras.get("bass", {}))

    def test_the_line_rides_the_written_bass(self):
        from types import SimpleNamespace
        bars = [(4.0 * k, 4.0 * k + 4.0) for k in range(4)]
        song = rhythm.Song("w", 4, 4, bars, [], notes={}, sid="w", game="g", numbers=list(range(4)), parts=[(0, 4, None, "A")], tonic=0, mode="major")
        plan = SimpleNamespace(parts=[(0, 2, None, "A"), (2, 2, None, "B")], plays={"accompaniment": [True] * 4}, extras={"accompaniment": {}}, bounds={})
        bass = [(4.0 * k + x / 2, 4.0 * k + x / 2 + 0.4, 36.0 + (x % 2) * 7, 0) for k in range(4) for x in range(8)]   # root and fifth eighths
        own = [(4.0 * k + x, 4.0 * k + x + 0.9, 60.0 + x, 0) for k in range(4) for x in range(4)]                     # the line's own: a note a beat
        figures = ["0 1 2 3"] * 4; voicings = ["own"] * 4; shared = {("line", (k, Fraction(x))): 60.0 + x for k in range(4) for x in range(4)}
        notes, figs, vcs, log = whole.ride_the_bass(plan, song, "accompaniment", own, figures, voicings, shared, (48, 60), (1.0, 1.0), bass, random.Random(1))
        self.assertEqual(sorted(k for k in range(4) if vcs[k] == "rides the bass"), [0, 1, 2, 3])                 # a share of 1.0: every part rides
        riding = [n for n in notes if n[0] < 4.0]
        self.assertEqual([n[0] for n in riding], [x / 2 for x in range(8)])                                      # the bass's onsets
        self.assertEqual({round(n[2]) % 12 for n in riding}, {0, 7})                                             # its pitch classes, in the line's register
        self.assertTrue(all(48 <= n[2] <= 60 for n in riding))
        self.assertEqual(figs[0], rhythm.pattern(rhythm.position(x / 2, 4) for x in range(8)))
        self.assertEqual(shared[("line", (0, Fraction(0)))], riding[0][2])
        bar0 = {key_[1][1]: m for key_, m in shared.items() if key_[0] == "line" and key_[1][0] == 0}
        self.assertEqual(sorted(bar0), [Fraction(x, 2) for x in range(8)])                                       # the line's keys of bar 0 are the riding onsets, the old beats' gone or replaced
        self.assertEqual({round(m) % 12 for m in bar0.values()}, {0, 7})
        self.assertIn("rides the bass in 4 bars", log[0])
        notes2, figs2, vcs2, log2 = whole.ride_the_bass(plan, song, "accompaniment", list(own), ["0 1 2 3"] * 4, ["own"] * 4, {}, (48, 60), (0.0, 0.0), bass, random.Random(1))
        self.assertEqual(notes2, sorted(own))                                                                    # a share of 0: nothing rides


class TokenMotionTests(unittest.TestCase):
    """Round 103: a chord part's line motion and off-chord tier ride the balance token, and the plan takes them."""

    def test_the_token_carries_a_chord_parts_line_motion_and_tier_and_the_plan_takes_them(self):
        from bitcomposer.translate import tables
        from bitcomposer.translate.vocab import Span
        bars = [(4.0 * k, 4.0 * k + 4.0) for k in range(8)]
        chords = [Span(0.0, 32.0, 0, "", 1.0)]                                                                  # C throughout
        riff = [(4.0 * k + x / 2, 0.4, 48.0 if x % 8 else 55.0, "g") for k in range(8) for x in range(8)]      # a chugging line: C with a G on each downbeat
        bass = [(4.0 * k + x, 0.9, 36.0, "b") for k in range(8) for x in (0.0, 2.0)]
        tune = [(4.0 * k + x, 0.9, 72.0 + x, "m") for k in range(8) for x in (0.0, 1.0, 2.0, 3.0)]
        s = rhythm.Song("t", 4, 12, bars, chords, notes={"accompaniment": riff, "bass": bass, "melody": tune}, sid="s", game="g",
                        numbers=list(range(8)), parts=[(0, 8, None, "A")], tonic=0, mode="major")
        s.voice_notes = {0: ("accompaniment", riff), 1: ("bass", bass), 2: ("melody", tune)}
        s.voice_levels = {0: 0.3, 1: 0.5, 2: 0.4}; s.levels = {"accompaniment": 0.3, "bass": 0.5, "melody": 0.4}
        self.assertEqual((rhythm.line_motion(s, "accompaniment"), rhythm.line_tone_tier(s, "accompaniment")), ("block", "rare"))   # 0.25 of strikes move, all on the chord
        tok = rhythm.balance_units([s])[0].outcome
        acc = next(f for f in tok.split() if f.startswith("accompaniment=")).split("=", 1)[1].split(":")
        self.assertEqual((acc[11], acc[12]), ("block", "rare"), acc)
        self.assertNotIn("block", next(f for f in tok.split() if f.startswith("bass=")))                   # the bass carries no motion field
        # the plan: the token's motion and tier in place of the draws, the voices beside the line keeping the drawn motion
        token = "accompaniment=main:48-55:0.9:1:0.6:::sacc0123456@44-60:dense+repeating:0.50::block:rare bass=half:36-44:0.9:1:1.0:::sbass top=0.30 tempo=medium"
        units_ = lambda outcome, **v: [tables.Unit(f"s{i}", "g", outcome, v) for i in range(3)]   # noqa: E731
        models = {"balance": tables.Table(("part",), "balance", votes=tables.SHARES).fit(units_(token, part=rhythm.ARRANGEMENT)),
                  "motions": tables.Table(("part",), "motions", votes=tables.SHARES).fit(units_("arpeggiated", part="accompaniment")),
                  "tone_tiers": tables.Table(("part",), "tone_tiers", votes=tables.SHARES).fit(units_("many", part="accompaniment"))}
        p = whole.plan(models, 3, "g")
        x = p.extras["accompaniment"]
        self.assertEqual((x["motion"], x["motion_drawn"], x["tone_tier"], x["tone_tier_drawn"]), ("block", "arpeggiated", "rare", "many"))
        self.assertTrue(any(l.startswith("accompaniment's line motion from the balance: block (the draw arpeggiated)") for l in p.log), p.log)
        bare = "accompaniment=main:48-55:0.9:1:0.6:::sacc0123456@44-60:dense+repeating bass=half:36-44:0.9:1:1.0:::sbass top=0.30 tempo=medium"
        models["balance"] = tables.Table(("part",), "balance", votes=tables.SHARES).fit(units_(bare, part=rhythm.ARRANGEMENT))
        q = whole.plan(models, 3, "g")
        self.assertEqual((q.extras["accompaniment"]["motion"], q.extras["accompaniment"]["tone_tier"]), ("arpeggiated", "many"))   # no field: the draws
        self.assertNotIn("motion_drawn", q.extras["accompaniment"])


if __name__ == "__main__":
    unittest.main()


class NewTablesTests(unittest.TestCase):
    """The tables the whole-song plan added to the kept set."""

    def _song(self, sid="a"):
        from bitcomposer.translate.vocab import Span
        bars = [(4.0 * i, 4.0 * i + 4) for i in range(8)]
        chords = [Span(0.0, 16.0, 0, "", 1.0), Span(16.0, 32.0, 7, "", 1.0)]          # C, then G
        s = rhythm.Song("t", 4, 4, bars, chords, bpm=120.0, sid=sid, game="G", numbers=list(range(8)),
                        parts=[(0, 4, None, "A"), (4, 4, None, "B")], tonic=0, mode="major")
        s.notes["bass"] = [(4.0 * i + x, 0.5, 36.0, "k") for i in range(8) for x in (0.0, 2.0)]
        s.notes["melody"] = [(4.0 * i + x, 0.9, m, "m") for i in range(4, 8) for x, m in ((0.0, 67.0), (1.0, 69.0), (2.0, 71.0), (3.0, 72.0))]
        s.notes["drums"] = [(4.0 * i + x, 0.25, float("nan"), "kick") for i in range(8) for x in (0.0, 2.0)] + \
                           [(4.0 * i + x, 0.25, float("nan"), "crash") for i in range(8) for x in (0.0,) if i % 4 == 0]
        s.pieces = {"kick": "kick", "crash": "cymbal"}
        return s

    def test_part_textures(self):
        units = rhythm.part_texture_units([self._song()])
        self.assertEqual([u.outcome for u in units], ["no melody", "all"])
        self.assertEqual([u.values["form"] for u in units], ["first", "last"])
        self.assertEqual(units[1].values["previous"], "no melody")

    def test_drum_group_habits_and_rests(self):
        units = rhythm.drum_group_habit_units([self._song()])
        parts = {u.values["part"]: u for u in units}
        self.assertIn("drums-KSt", parts)
        self.assertIn("drums-c", parts)
        self.assertTrue(all(u.values["habit"] == parts["drums-KSt"].values["habit"] for u in units))   # the kit's habit beside each group's own
        self.assertTrue(parts["drums-c"].outcome.startswith("sparse"))
        from bitcomposer.translate import writer
        self.assertFalse(writer.FreeManner({"0:K", "-"}).fits("-"))
        self.assertTrue(writer.FreeManner({"0:K", "-"}, rests=True).fits("-"))

    def test_the_whole_kit_writes_from_its_own_table(self):
        """A group of every letter is the kit: its figures come from the kit table's bars (part "drums"), not the floor's runs."""
        from bitcomposer.translate import packtables, writer
        s = self._song()
        s.notes["drums"] = [(4.0 * i + x, 0.25, float("nan"), "kick") for i in range(8) for x in (0.0, 2.0)] + \
                           [(4.0 * i + x, 0.25, float("nan"), "snare") for i in range(8) for x in (1.0, 3.0)]
        s.pieces = {"kick": "kick", "snare": "snare"}
        entry = packtables.fit("drums", rhythm.drum_units([s]))
        model = packtables.read({"tables": {"drums": entry}})["drums"]
        hits, figures = writer.drums(s, {tuple(rhythm.LETTERS.values()): model}, random.Random(1), habit="medium repeating", free=True, plays=[True] * 8)
        self.assertTrue(all(f in model.table.vocabulary for f in figures), figures)
        self.assertTrue(hits)

    def test_rolls_and_the_balance_with_its_layout(self):
        self.assertTrue(rhythm.is_roll(" ".join(f"{i}/12:R" for i in range(0, 48)), 4))
        self.assertFalse(rhythm.is_roll("0:R 1/2:5 1:R 3/2:5 2:R 5/2:5 3:R 7/2:5", 4))
        self.assertTrue(rhythm.is_roll(" ".join(f"{i}/12:h" for i in range(0, 20)) + " 0:K 2:S", 4))   # a hat roll
        self.assertFalse(rhythm.is_roll(" ".join(f"{i}/4:h" for i in range(0, 16)) + " 0:K 2:S", 4))   # sixteenth hats are a bar
        units = rhythm.balance_units([self._song()])
        self.assertEqual(len(units), 1)
        tokens = units[0].outcome.split()
        self.assertTrue(tokens[1].startswith("drums") and tokens[1].endswith("+mixed"), tokens)       # the kit's habit rides too (round 62)
        self.assertTrue(tokens[0].startswith("bass=") and tokens[0].count(":") >= 8 and tokens[0].split(":")[7].split("@")[0] == "k", tokens)   # weight:register:sounded share:voices ... sample (round 60), habit (round 62); a period field after (round 106)
        self.assertIn("36-36", tokens[0])                                                       # the bass on one note
        ranges = rhythm.sample_range_units([self._song()])
        self.assertEqual({u.values["part"] for u in ranges}, {"sk", "sm"})

    def test_layers_and_the_voices_a_part(self):
        s = self._song()
        s.voice_notes = {0: ("bass", s.notes["bass"]), 1: ("melody", s.notes["melody"]),
                         2: ("melody", [(t + d, 0.2, m - 12.0, "m") for t, _, m, _ in s.notes["melody"] if t % 2 == 0 for d in (0.5, 0.75)])}   # a second voice an octave under, its own rhythm, as dense
        units = rhythm.layer_units([s])
        self.assertEqual(len(units), 1)
        self.assertEqual((units[0].values["part"], units[0].values["rank"]), ("melody", "2"))
        self.assertEqual(units[0].outcome, "apart -12 like")
        s.voice_notes[3] = ("melody", [(t, 0.2, m + 12.0, "m") for t, _, m, _ in s.notes["melody"]])   # a third voice doubling the line an octave up
        units = rhythm.layer_units([s])
        self.assertEqual([(u.values["rank"], u.outcome) for u in units], [("2", "apart -12 like"), ("3", "doubling +12")])
        del s.voice_notes[3]
        self.assertIn("melody=main:68-72:0.9:2", rhythm.balance_units([s])[0].outcome)   # the tune's ambitus to the grain, two voices
        self.assertEqual(whole.allot(["bass", "drums", "melody", "counter"], {"bass": 1, "melody": 1, "counter": 2}), {"drums": 2, "bass": 1, "melody": 1, "counter": 2})
        self.assertEqual(sum(whole.allot(["bass", "accompaniment", "counter", "harmony", "melody", "drums"], {"accompaniment": 3, "counter": 3, "harmony": 3}).values()), 8)
        self.assertEqual(whole.layer_of({"layer": "apart -8 sparser"}), ("apart", -8, "sparser"))
        self.assertEqual(whole.layer_of({"layer": "doubling +4"}), ("doubling", 4))
        major = {0, 2, 4, 5, 7, 9, 11}
        self.assertEqual([m for _, _, m, _ in whole.diatonic([(0.0, 1.0, 60.0, 0), (1.0, 2.0, 62.0, 0)], 4, major, 1)], [64.0, 65.0])   # a third up: E, then F

    def test_phrase_letters_and_the_theme_body(self):
        s = self._song()
        # the tune over the song's eight bars: two parts of four; bars 0 and 4 open alike (the theme head), bar 4's phrase
        # keeps the theme's second bar too, bars 2-3 and 6-7 differ
        s.parts = [(0, 4, None, "A"), (4, 4, None, "B")]
        tune = {0: (67, 69, 71, 72), 1: (72, 71, 69, 67), 2: (60, 62, 64, 65), 3: (65, 64, 62, 60),
                4: (67, 69, 71, 72), 5: (72, 71, 69, 67), 6: (74, 76, 77, 79), 7: (79, 77, 76, 74)}
        s.notes["melody"] = [(4.0 * bar + x, 0.9, float(m), "m") for bar, ms in tune.items() for x, m in zip((0.0, 1.0, 2.0, 3.0), ms)]
        s.parts = [(0, 4, None, "A"), (4, 4, None, "B")]
        windows = rhythm.phrase_windows(s)
        self.assertEqual([w for _, w in windows], [[0, 1, 2, 3], [4, 5, 6, 7]])
        heads = rhythm.phrase_heads(s)
        self.assertEqual(heads[0][2], heads[1][2])
        units = rhythm.phrase_letter_units([s])
        self.assertEqual([(u.outcome, u.values["phrases"], u.values["form"]) for u in units], [("T", "1", "first"), ("T", "1", "last")])
        body = rhythm.theme_body_units([s])
        self.assertEqual([u.outcome for u in body], ["1"])                  # bar 5 repeats the theme's bar 1, bar 6 does not
        s.parts = [(0, 8, None, "A")]
        self.assertEqual([u.outcome for u in rhythm.theme_body_units([s])], ["1"])   # within one part: bar 5 repeats the theme's bar 1, bar 6 does not
        self.assertEqual(rhythm.phrase_letter_units([s])[0].outcome, "T T")

    def test_what_comes_back_with_the_theme(self):
        s = self._song()
        s.parts = [(0, 8, None, "A")]
        tune = {0: (67, 69, 71, 72), 1: (72, 71, 69, 67), 2: (60, 62, 64, 65), 3: (65, 64, 62, 60),
                4: (67, 69, 71, 72), 5: (72, 71, 69, 67), 6: (74, 76, 77, 79), 7: (79, 77, 76, 74)}
        s.notes["melody"] = [(4.0 * bar + x, 0.9, float(m), "m") for bar, ms in tune.items() for x, m in zip((0.0, 1.0, 2.0, 3.0), ms)]
        from bitcomposer.translate.vocab import Span
        s.chords = [Span(0.0, 32.0, 0, "", 1.0)]               # one chord throughout: the bass's two-note bar and the chord come back with the theme
        units = rhythm.return_band_units([s])
        self.assertEqual(len(units), 1)
        self.assertEqual(units[0].outcome, "chords bass")
        s.chords = [Span(0.0, 16.0, 0, "", 1.0), Span(16.0, 32.0, 7, "", 1.0)]   # the chord changes under the return: the bass's marks change with it
        self.assertEqual(rhythm.return_band_units([s])[0].outcome, "none")
        from bitcomposer.translate import writer
        s2 = self._song()
        s2.copies = {"bass": [(4, 2, 0)]}                       # the plan: the bass comes back with the theme at bar 4, two bars
        units = [tables.Unit(f"s{i}", "g", f, {"part": "bass", "meter": 4, "habit": "medium walking no-octaves", "previous": rhythm.START})
                 for i, f in enumerate(("0:R 2:5", "0:R 1:+ 2:5 3:+", "0:R 3/2:R 2:5", "0:R 1:R 2:R 3:R"))]
        cache = tables.Cache.fit(units, ("part", "meter", "habit", "previous"), name="bass", votes=tables.SHARES)
        bars = [(a, b, []) for a, b in s2.bars]
        figs = writer._free_figures(s2, "bass", cache, writer.FreeManner(cache.table.vocabulary, division=4), ["0"] * 8, bars,
                                    "medium walking no-octaves", random.Random(3), (), {}, envelope_of=writer.free_envelope("medium"))
        self.assertEqual(figs[4:6], figs[0:2])                 # the theme's bars again under the return
        self.assertTrue(all(f in cache.table.vocabulary for f in figs))

    def test_a_themed_plan_returns_to_its_theme(self):
        """With phrase letters and the tune playing throughout, a themed plan has a later phrase open with the theme."""
        letters = tables.Table(("part", "phrases", "form"), "phrase letters", votes=tables.SHARES).fit(
            [tables.Unit(f"s{i}", "g", o, {"part": "melody", "phrases": "2", "form": f}) for i, (o, f) in enumerate(
                (("T n", "first"), ("n n", "last"), ("n n", "last"), ("n T", "last"), ("n n", "middle")))])
        returns = tables.Table(("part",), "return band", votes=tables.SHARES).fit(
            [tables.Unit(f"s{i}", "g", o, {"part": "return"}) for i, o in enumerate(("none", "none", "chords bass accompaniment", "accompaniment"))])
        sizes = tables.Table(("part",), "sizes", votes=tables.SHARES).fit([tables.Unit("s", "g", "2", {"part": "form"}), tables.Unit("t", "g", "2", {"part": "form"})])
        lengths = tables.Table(("part", "meter", "habit"), "lengths", votes=tables.SHARES).fit(
            [tables.Unit(sid, "g", "8", {"part": "form", "meter": 4, "habit": "short"}) for sid in ("s", "t")])
        habits = tables.Table(("part",), "length habits", votes=tables.SHARES).fit([tables.Unit(sid, "g", "short", {"part": "form"}) for sid in ("s", "t")])
        models = {"phrase_letters": letters, "return_band": returns, "sizes": sizes, "lengths": lengths, "length_habits": habits}
        themed = sum(1 for seed in range(1, 13) if any(r for r in whole.plan(models, seed, "test", themed=True, band_returns=True).extras.get("melody", {}).get("returns", [])))
        self.assertEqual(themed, 12)                            # every themed plan returns to its theme
        p = whole.plan(models, 3, "test", themed=True, band_returns=True)
        self.assertTrue(all(r["with"] for r in p.extras["melody"]["returns"]))   # and never with the tune alone
        self.assertEqual((p.extras["options"]["themed"], p.extras["options"]["band_returns"], p.extras["options"]["plan_draws"]), (True, True, 1))
        plain = sum(1 for seed in range(1, 13) if whole.plan(models, seed, "test").extras.get("melody", {}).get("returns"))
        self.assertLess(plain, 12)                              # without the switch, the table's own rate

    def test_a_themed_plan_is_drawn_again_when_its_tune_has_one_phrase(self):
        """A one-part four-bar form gives the tune one phrase, so no letter draw can bring a theme back: the plan is drawn again
        until the form has room (two four-bar parts), and a game whose forms never have room ends unthemed and says so."""
        letters = tables.Table(("part", "phrases", "form"), "phrase letters", votes=tables.SHARES).fit(
            [tables.Unit(f"s{i}", "g", o, {"part": "melody", "phrases": "2", "form": f}) for i, (o, f) in enumerate((("T n", "first"), ("n T", "last")))])
        lengths = tables.Table(("part", "meter", "habit"), "lengths", votes=tables.SHARES).fit(
            [tables.Unit(sid, "g", "4", {"part": "form", "meter": 4, "habit": "short"}) for sid in ("s", "t")])
        habits = tables.Table(("part",), "length habits", votes=tables.SHARES).fit([tables.Unit(sid, "g", "short", {"part": "form"}) for sid in ("s", "t")])
        mixed = tables.Table(("part",), "sizes", votes=tables.SHARES).fit([tables.Unit("s", "g", "1", {"part": "form"}), tables.Unit("t", "g", "2", {"part": "form"})])
        models = {"phrase_letters": letters, "sizes": mixed, "lengths": lengths, "length_habits": habits}
        plans = [whole.plan(models, seed, "test", themed=True) for seed in range(1, 13)]
        self.assertTrue(all(p.extras["melody"]["returns"] for p in plans))                 # every song came back to its theme
        self.assertTrue(any(p.extras["options"]["plan_draws"] > 1 for p in plans))         # some needed a second form
        self.assertTrue(all(len(p.parts) >= 2 for p in plans))                             # the one-part forms were drawn past
        narrow = tables.Table(("part",), "sizes", votes=tables.SHARES).fit([tables.Unit("s", "g", "1", {"part": "form"}), tables.Unit("t", "g", "1", {"part": "form"})])
        p = whole.plan({**models, "sizes": narrow}, 1, "test", themed=True)
        self.assertFalse(p.extras["melody"].get("returns"))
        self.assertEqual(p.extras["options"]["plan_draws"], whole.PLAN_TRIES)
        self.assertTrue(any("unthemed" in line for line in p.log))

    def test_the_line_and_its_second_voice(self):
        """The figure table counts an upper part's own line where it holds two voices; the second voice's bar is its own unit
        under the line's bar."""
        bars = [(4.0 * k, 4.0 * k + 4.0) for k in range(4)]
        line = [(4.0 * k + 0.5 * i, 0.4, 60.0, "a") for k in range(4) for i in range(8)]        # every eighth
        second = [(4.0 * k + i, 0.9, 52.0, "a") for k in range(4) for i in range(4)]            # the beats, with the line
        s = rhythm.Song("t", 4, 12, bars, [], notes={"accompaniment": line + second}, sid="s", game="g")
        s.voice_notes = {3: ("accompaniment", line), 4: ("accompaniment", second)}
        self.assertEqual(rhythm.line_notes(s, "accompaniment"), line)
        patterns = {u.outcome for u in rhythm.units([s]) if u.values["part"] == "accompaniment"}
        self.assertEqual(patterns, {"0 1/2 1 3/2 2 5/2 3 7/2"})                                 # the line's bar, not the voices merged
        units = rhythm.second_figure_units([s])
        self.assertEqual(len(units), 4)
        self.assertEqual((units[0].outcome, units[0].values), ("1 0 1 0 1 0 1 0", {"part": "accompaniment", "layer": "half", "feel": "duple", "tempo": rhythm.band(120.0), "onsets": "8", "line": "0 1/2 1 3/2 2 5/2 3 7/2"}))   # the extra voices' notes over the line's: half (round 65)
        F = __import__("fractions").Fraction
        self.assertEqual(rhythm.second_mask([F(0), F(1), F(2), F(3)], [F(0), F(2), F(7, 2)]), "1 0 1 0 | 7/2")
        self.assertEqual(rhythm.apply_mask("0 1/2 1 3/2 2 5/2 3 7/2", "1 0 1 0 1 0 1 0"), "0 1 2 3")
        self.assertEqual(rhythm.apply_mask("0 1 2 3", "1 0 | 7/2"), "0 2 7/2")                       # a short mask read around the line
        self.assertEqual(rhythm.apply_mask("0 1 2 3", "-"), "-")
        self.assertEqual([u.outcome for u in rhythm.layer_sample_units([s])], ["sa sa"])      # both voices on sample "a" here
        s.voice_notes = {3: ("accompaniment", line)}
        self.assertIsNone(rhythm.line_notes(s, "accompaniment"))                                 # one voice: the part's bar
        self.assertEqual(rhythm.second_figure_units([s]), [])

    def test_the_theme_doubled_and_carried(self):
        """Where the tune plays its theme cell another part may play it too (theme_doubling, with the interval); a phrase
        whose tune is not the theme may have it carried by the bass (theme_carrier)."""
        bars = [(4.0 * k, 4.0 * k + 4.0) for k in range(8)]
        cell = lambda a, base: [(a, 0.9, base, "m"), (a + 1.0, 0.9, base + 2.0, "m"), (a + 2.0, 1.9, base + 4.0, "m")]   # noqa: E731
        other = lambda a, base: [(a, 0.4, base + 7.0, "m"), (a + 0.5, 0.4, base + 5.0, "m"), (a + 1.0, 2.9, base + 4.0, "m")]   # noqa: E731
        tune = cell(0.0, 60.0) + other(4.0, 60.0) + other(8.0, 60.0) + other(12.0, 60.0) + cell(16.0, 60.0) + other(20.0, 60.0) + other(24.0, 60.0) + other(28.0, 60.0)
        counter = other(0.0, 72.0) + other(4.0, 72.0) + other(8.0, 72.0) + other(12.0, 72.0) + cell(16.0, 72.0) + other(20.0, 72.0)
        s = rhythm.Song("t", 4, 12, bars, [], notes={"melody": tune, "counter": counter}, sid="s", game="g", parts=[(0, 8, None, "A")])
        units = rhythm.theme_doubling_units([s])
        self.assertEqual([(u.outcome, u.values["place"]) for u in units], [("none", "statement"), ("counter:+12", "later")])
        self.assertEqual([u.outcome for u in rhythm.theme_carrier_units([s])], [])             # the second phrase opens with the theme: nothing to carry
        tune2 = cell(0.0, 60.0) + other(4.0, 60.0) + other(8.0, 60.0) + other(12.0, 60.0) + other(16.0, 62.0) + other(20.0, 60.0) + other(24.0, 60.0) + other(28.0, 60.0)
        bass = other(0.0, 36.0) + other(4.0, 36.0) + other(8.0, 36.0) + other(12.0, 36.0) + cell(16.0, 36.0) + other(20.0, 36.0) + other(24.0, 36.0) + other(28.0, 36.0)
        s2 = rhythm.Song("t", 4, 12, bars, [], notes={"melody": tune2, "bass": bass}, sid="s", game="g", parts=[(0, 8, None, "A")])
        self.assertEqual([u.outcome for u in rhythm.theme_carrier_units([s2])], ["bass"])      # bars 4-5 of the bass are the theme phrase's first two
        self.assertEqual([u.outcome for u in rhythm.theme_doubling_units([s2])], ["none"])

    def test_the_band_passes_copy_the_theme_and_the_repeats(self):
        """double_theme copies the tune's theme bar into the drawn part at the drawn interval; carry_theme puts the theme phrase into
        the bass's register under a phrase that is not the theme; copy_repeats makes a repeated part note for note."""
        bars = [(4.0 * k, 4.0 * k + 4.0) for k in range(8)]
        s = rhythm.Song("t", 4, 12, bars, [], notes={}, sid="s", game="g", parts=[(0, 4, None, "A"), (4, 4, 0, "A")])
        tune = [(0.0, 0.9, 60.0, 0), (1.0, 1.9, 62.0, 0), (2.0, 3.9, 64.0, 0)] + [(4.0 + k + 0.5 * i, 4.4 + k + 0.5 * i, 67.0 + i, 0) for k in range(0, 12, 4) for i in range(2)]
        s.notes["melody"] = [(a, b - a, m, "melody") for a, b, m, _ in tune]
        counter = [(t, u, m + 12.0, 0) for t, u, m, _ in tune]
        s.notes["counter"] = [(a, b - a, m, "counter") for a, b, m, _ in counter]
        bass = [(4.0 * k, 3.9, 36.0, 0) for k in range(8)]
        s.notes["bass"] = [(a, b - a, m, "bass") for a, b, m, _ in bass]
        written = {"melody": whole.Part("melody", list(tune), ["0 1 2"] + ["0 1/2 1 3/2"] * 7),
                   "counter": whole.Part("counter", list(counter), ["0 1 2"] + ["0 1/2 1 3/2"] * 7),
                   "bass": whole.Part("bass", list(bass), ["0"] * 8)}
        plays = [True] * 8
        plan = whole.Plan(1, "g", "t", 0, "major", 120.0, s.parts, 0, ["I"] * 8, [None] * 8, ["bass", "melody", "counter"], {}, [], {"melody": plays, "bass": plays, "counter": plays},
                          {"melody": (60, 80), "counter": (60, 84), "bass": (30, 45)}, {}, {}, {"melody": {"theme_bars": [0, 1, 2, 3], "letters": {0: "T"}}}, {}, [])
        doubling = tables.Table(("part", "place"), "theme doubling", votes=tables.SHARES).fit(
            [tables.Unit(f"s{i}", "g", "counter:+12", {"part": "theme", "place": p}) for i, p in enumerate(("statement", "later", "statement"))])
        carrier = tables.Table(("part",), "theme carrier", votes=tables.SHARES).fit([tables.Unit(f"s{i}", "g", "bass", {"part": "carrier"}) for i in range(3)])
        models = {"theme_doubling": doubling, "theme_carrier": carrier}
        rng = random.Random(1)
        log = whole.double_theme(plan, s, written, models, rng)
        self.assertEqual(log, ["bar 0: the counter doubles the theme's cell (+12)"])
        self.assertEqual([n for n in written["counter"].notes if n[0] < 4.0], [(0.0, 0.9, 72.0, 0), (1.0, 1.9, 74.0, 0), (2.0, 3.9, 76.0, 0)])
        self.assertEqual([n[2] for n in s.notes["counter"] if n[0] < 4.0], [72.0, 74.0, 76.0])
        plan.extras["melody"]["letters"] = {0: "T", 1: "n"}
        log = whole.carry_theme(plan, s, written, models, rng)
        self.assertEqual(log, ["bar 4: the bass carries the theme phrase (-24)"])
        self.assertEqual([n for n in written["bass"].notes if 16.0 <= n[0] < 20.0][:3], [(16.0, 16.9, 36.0, 0), (17.0, 17.9, 38.0, 0), (18.0, 19.9, 40.0, 0)])
        log = whole.copy_repeats(plan, s, written)
        self.assertEqual(log, ["A (bars 4-7) plays A (bars 0-3) again note for note"])
        for role in ("melody", "counter", "bass"):
            first = [(round(t, 6), round(u, 6), m) for t, u, m, _ in written[role].notes if t < 16.0]
            again = [(round(t - 16.0, 6), round(u - 16.0, 6), m) for t, u, m, _ in written[role].notes if t >= 16.0]
            self.assertEqual(first, again, role)
            self.assertEqual(written[role].figures[4:], written[role].figures[:4])

    def test_the_backing_period_and_its_holds(self):
        """A bass playing the same two bars through a part has a period of 2 there; the bars inside it are held but the one varied."""
        bars = [(4.0 * k, 4.0 * k + 4.0) for k in range(8)]
        riff = lambda a: [(a, 0.9, 36.0, "b"), (a + 1.5, 0.4, 43.0, "b"), (a + 2.0, 0.9, 36.0, "b"), (a + 4.0, 0.9, 36.0, "b"), (a + 6.0, 1.9, 38.0, "b")]   # noqa: E731
        bass = [n for j in range(4) for n in riff(8.0 * j)]
        bass[-1] = (bass[-1][0], bass[-1][1], 48.0, "b")                                      # the last bar varied: an octave where a passing tone was
        chords = [vocab.Span(0.0, 32.0, 0, "", 1.0)]
        s = rhythm.Song("t", 4, 12, bars, chords, notes={"bass": bass}, sid="s", game="g", parts=[(0, 8, None, "A")], tonic=0)
        self.assertEqual([(u.outcome, u.values) for u in rhythm.period_units([s])], [("2", {"part": "bass", "length": "medium", "tempo": rhythm.band(120.0)})])
        holds = [u.outcome for u in rhythm.period_hold_units([s])]
        self.assertEqual((len(holds), holds.count("varied")), (6, 1))
        self.assertEqual([rhythm.part_length(n) for n in (4, 5, 8, 9)], ["short", "medium", "medium", "long"])
        s.notes["bass"] = [n for j in range(8) for n in riff(4.0 * j)[:3]]                     # one bar, every bar: a period of 1
        self.assertEqual([u.outcome for u in rhythm.period_units([s])], ["1"])

    def test_the_moves_know_their_landing(self):
        """A moves table drawn by the beat and the tone left follows them, and the chord weighting stays out of its way."""
        t = tables.Table(("part", "mode", "place", "tone", "previous"), "moves", votes=tables.SHARES).fit(
            [tables.Unit(f"s{i}", "g", "+4", {"part": "melody", "mode": "major", "place": "strong", "tone": "root", "previous": "start"}) for i in range(6)]
            + [tables.Unit(f"t{i}", "g", "+2", {"part": "melody", "mode": "major", "place": "strong", "tone": "another tone", "previous": "start"}) for i in range(6)])
        rng = random.Random(3)
        every = set(range(12))
        from_root = [writer.draw_move(t, "start", "major", 60.0, rng, (48, 84), every, True, (0, ""), set(), None, tone="root") for _ in range(30)]
        from_other = [writer.draw_move(t, "start", "major", 60.0, rng, (48, 84), every, True, (0, ""), set(), None, tone="another tone") for _ in range(30)]
        self.assertGreaterEqual(from_root.count(4), 22)
        self.assertGreaterEqual(from_other.count(2), 22)

    def test_the_feel_and_the_layered_bass(self):
        """A song's feel is triple from a quarter of its onsets on triplet positions; a two-voice bass's figure table counts its
        sustained line, the busy voice is the second line's unit, and the two voices' note lengths are counted apart."""
        bars = [(4.0 * k, 4.0 * k + 4.0) for k in range(4)]
        straight = [(4.0 * k + 0.5 * i, 0.4, 60.0, "m") for k in range(4) for i in range(8)]
        shuffle = [(4.0 * k + i + d, 0.3, 60.0, "m") for k in range(4) for i in range(4) for d in (0.0, 2 / 3)]
        s = rhythm.Song("t", 4, 12, bars, [], notes={"melody": straight}, sid="s", game="g")
        self.assertEqual(rhythm.song_feel(s), "duple")
        s2 = rhythm.Song("t", 4, 12, bars, [], notes={"melody": shuffle}, sid="s", game="g")
        self.assertEqual((rhythm.song_feel(s2), rhythm.feel_units([s2])[0].outcome), ("triple", "triple"))
        chords = [vocab.Span(0.0, 16.0, 0, "", 1.0)]
        long = [(4.0 * k, 3.9, 36.0, "b") for k in range(4)]                                   # the sustained line
        busy = [(4.0 * k + 0.5 * i, 0.2, 36.0, "b") for k in range(4) for i in range(8)]        # the staccato voice under it
        s3 = rhythm.Song("t", 4, 12, bars, chords, notes={"bass": long + busy}, sid="s", game="g", tonic=0, parts=[(0, 4, None, "A")])
        s3.voice_notes = {2: ("bass", long), 5: ("bass", busy)}
        self.assertEqual(rhythm.line_notes(s3, "bass"), long)
        self.assertEqual({u.outcome for u in rhythm.bass_units([s3])}, {"0:R"})                 # the line's bar, one root held
        seconds = rhythm.second_figure_units([s3])
        self.assertEqual(len(seconds), 4)
        self.assertEqual((seconds[0].values["part"], seconds[0].values["line"], seconds[0].values["onsets"]), ("bass", "0", "1"))
        self.assertEqual(seconds[0].outcome, "1 | 1/2 1 3/2 2 5/2 3 7/2")                         # with the held root, then seven of its own (the mask, round 27)
        sounds = {(u.values["voice"]): u.outcome for u in rhythm.layer_sound_units([s3])}
        self.assertGreater(float(sounds["line"]), float(sounds["second"]))
        self.assertEqual(sounds["second"], "0.4")
        s3.voice_notes = {2: ("bass", [(t, u, m, "long1234567890") for t, u, m, _ in long]), 5: ("bass", [(t, u, m, "short123456789") for t, u, m, _ in busy])}
        self.assertEqual([(u.outcome, u.values) for u in rhythm.layer_sample_units([s3])], [("slong123456 sshort12345", {"part": "bass"})])
        self.assertEqual([u.values["tempo"] for u in rhythm.second_figure_units([s3])][:1], [rhythm.band(120.0)])

    def test_the_kit_from_the_namers_names_and_the_group_caps(self):
        """The pack's kit takes each piece's most-played sample by the drum namer's name, a second hat as the open hat and the
        busiest other sound as the rim; a plan's drum group habits cap a free-drawn kit bar's hits a letter."""
        from collections import Counter
        uses = Counter({"a": 100, "b": 90, "c": 80, "d": 70, "e": 60, "f": 50, "g": 10, "h": 5})
        labels = {"a": "kick", "b": "snare", "c": "hat", "d": "hat", "e": "cymbal", "f": "tom", "g": "other", "h": "snare"}
        self.assertEqual(pack.kit_from_names(uses, labels), {"kick": "a", "snare": "b", "hihat": "c", "open_hihat": "d", "crash": "e", "tom": "f", "rim": "g"})
        self.assertEqual(pack.kit_from_names(uses, {"a": "kick", "c": "hat"}), {})                 # no snare named: the brightness kit instead
        self.assertEqual(writer.group_caps({("c",): "sparse mixed", ("h",): "dense varied", ("K", "S", "t"): "medium mixed"}), {"c": 2, "h": 16})
        self.assertEqual(writer.group_caps("dense mixed"), {})
        env = writer.free_drum_envelope({"K", "S", "c"}, {"c": 2})(None, 4)
        self.assertEqual((env[0]["c"], env[0]["K"]), ((0, 2), (0, 16)))
        self.assertTrue(writer.drum_within("0:K 1:c 2:S 3:c", env))
        self.assertFalse(writer.drum_within("0:K 1/2:c 1:c 3/2:c 2:S", env))

    def test_the_sample_for_a_register_and_the_line_voices_register(self):
        """The sample for a part is the pool's whose game-played range covers the register best, the part's top weighing most; the
        pack's other samples when the pool reaches nowhere near the top; a layered part's register is its line voice's."""
        ranges = tables.Table(("part",), "ranges", votes=tables.SHARES).fit(
            [tables.Unit(f"s{i}", "g", "56-68", {"part": "sa"}) for i in range(3)] + [tables.Unit(f"t{i}", "g", "72-88", {"part": "sb"}) for i in range(3)]
            + [tables.Unit(f"u{i}", "g", "84-96", {"part": "sc"}) for i in range(3)])
        raw = lambda n: n[len("p_"):] if n.startswith("p_") else n   # noqa: E731
        rng = random.Random(1)
        self.assertEqual(whole.best_sample(ranges, ["p_sa", "p_sa", "p_sb"], (60, 70), rng, raw), "p_sa")
        self.assertEqual(whole.best_sample(ranges, ["p_sa", "p_sa", "p_sb"], (74, 88), rng, raw), "p_sb")
        self.assertEqual(whole.best_sample(ranges, ["p_sa", "p_sa"], (84, 96), rng, raw, others=["sc", "sb"]), "sc")   # the pool reaches nowhere near 96
        self.assertEqual(whole.best_sample(ranges, ["p_sa"], (60, 72), rng, raw, others=["sc"]), "p_sa")             # within REACH: the pool's
        bars = [(4.0 * k, 4.0 * k + 4.0) for k in range(4)]
        line = [(4.0 * k + 0.5 * i, 0.4, 60.0 + (i % 4) * 2, "a") for k in range(4) for i in range(8)]
        high = [(4.0 * k + i, 0.9, 88.0 + (i % 2) * 3, "a") for k in range(4) for i in range(4)]
        s = rhythm.Song("t", 4, 12, bars, [], notes={"accompaniment": line + high}, sid="s", game="g")
        s.voice_notes = {3: ("accompaniment", line), 4: ("accompaniment", high)}
        self.assertEqual(rhythm.register_notes(s, "accompaniment"), line)
        self.assertEqual([u.outcome for u in rhythm.register_units([s])], ["60-64"])                  # the line's (its 90th percentile 66, to the grain), not 60-92
        s.voice_notes = {3: ("accompaniment", line)}
        self.assertIsNone(rhythm.register_notes(s, "accompaniment"))

    def test_the_voice_beside_the_line_takes_its_interval_from_the_table(self):
        """voice_intervals counts a voice's interval to the line in scale steps where they strike together, voice_moves its
        own move at every onset by place; the upper writer draws the voice's pitch from the two words' product with the line
        and from its move alone, never a pitch another voice holds."""
        from fractions import Fraction
        from bitcomposer.translate import writer, tables, vocab
        bars = [(4.0 * k, 4.0 * k + 4.0) for k in range(4)]
        line = [(4.0 * k + 0.5 * i, 0.4, [64.0, 67.0, 72.0, 67.0][i % 4], "a") for k in range(4) for i in range(8)]   # eighths on E G C G
        second = []
        for k in range(4):
            second += [(4.0 * k, 0.9, 60.0, "b"), (4.0 * k + 2.0, 0.9, 60.0, "b"), (4.0 * k + 2.25, 0.4, 62.0, "b")]   # with the line a third below, then alone a step up
        s = rhythm.Song("t", 4, 12, bars, [vocab.Span(0.0, 16.0, 0, "", 1.0)], notes={"accompaniment": line + second}, sid="s", game="g", tonic=0, mode="major")
        s.voice_notes = {3: ("accompaniment", line), 4: ("accompaniment", second)}
        iv = rhythm.voice_interval_units([s])
        self.assertEqual({u.outcome for u in iv}, {"-2"})                                      # C under E: a third below, every time
        self.assertEqual([u.values["previous"] for u in iv][:3], [rhythm.START, "-2", "-2"])
        self.assertEqual(iv[0].values["kind"], "apart")
        mv = rhythm.voice_move_units([s])
        self.assertEqual([u.outcome for u in mv if u.values["place"] == "alone"], ["1"] * 4)   # alone: a step up from its own C
        self.assertEqual({u.outcome for u in mv if u.values["place"] == "with"}, {"0", "-1"})  # with the line: back to C from C or from D
        # the writer: tables that say "an octave above the line" and "hold your note" with the line, "a step up" alone
        iv_t = tables.Table(("part", "kind", "line", "previous"), "voice_intervals", votes=tables.SHARES).fit(
            [tables.Unit(f"s{i}", "g", "7", {"part": "accompaniment", "kind": "apart", "line": "scale", "previous": p}) for i in range(20) for p in (rhythm.START, "7")])
        mv_t = tables.Table(("part", "kind", "place"), "voice_moves", votes=tables.SHARES).fit(
            [tables.Unit(f"s{i}", "g", o, {"part": "accompaniment", "kind": "apart", "place": pl}) for i in range(20) for o, pl in (("0", "with"), ("-1", "with"), ("1", "alone"))])   # with the line: hold, or back from the step (the move is from the voice's own last note, round 66)
        song = rhythm.Song("w", 4, 12, bars[:2], [vocab.Span(0.0, 8.0, 0, "", 1.0)], notes={}, sid="w", game="g", tonic=0, mode="major")
        shared = {}
        for k in range(2):
            for pos in range(4):                                                               # a line that repeats middle C on every beat
                shared[(k, Fraction(pos))] = ((0, ""), "R 3 5", ["R", "3", "5"])
                shared[("line", (k, Fraction(pos)))] = 60
                shared.setdefault(("taken", (k, Fraction(pos))), set()).add(60)
        notes, figures, _ = writer.upper(song, "accompaniment", [1], {1: (60, 96)}, {"voice_intervals": iv_t, "voice_moves": mv_t}, random.Random(1),
                                         "dense", "triad", 0.5, key=(0, "major"), plays=[True, True], figures=["0 2 5/2", "0 2 5/2"], shared=shared,
                                         tone_index=writer.ANY_TONE, kind="apart")
        got = {(round(a, 2), int(m)) for a, b, m, v in notes}
        self.assertEqual(got, {(0.0, 72), (2.0, 72), (2.5, 74), (4.0, 72), (6.0, 72), (6.5, 74)})   # the octave above, held; a step up alone (the
        # smoothing leaves the table's other outcome a few percent at every draw: the seed is one where the words' own answers come up)
        self.assertTrue(all(int(m) != 60 for a, b, m, v in notes))

    def test_a_floor_steps_down_from_a_one_outcome_context(self):
        """A chain floored on a habit context with one outcome draws that outcome alone (all rests: a song without drums);
        with FLOOR_OUTCOMES the floor steps down to a level that holds a choice. A one-song context with bars of its own stays."""
        from bitcomposer.translate import tables
        units = [tables.Unit("s1", "g", "-", {"part": "drums", "habit": "thin", "previous": rhythm.START})] * 6
        units += [tables.Unit(f"s{i}", "g", "0:K 2:S", {"part": "drums", "habit": "full", "previous": rhythm.START}) for i in range(2, 6)]
        t = tables.Table(("part", "habit", "previous"), "x").fit(units)
        rng = random.Random(1)
        floored = {t.draw(("drums", "thin", rhythm.START), rng, floored=False, floor_k=2) for _ in range(30)}
        self.assertEqual(floored, {"-"})
        stepped = {t.draw(("drums", "thin", rhythm.START), rng, floored=False, floor_k=2, floor_outcomes=tables.FLOOR_OUTCOMES) for _ in range(30)}
        self.assertIn("0:K 2:S", stepped)
        self.assertEqual(tables.FLOOR_OUTCOMES, 2)
        units2 = [tables.Unit("s1", "g", o, {"part": "drums", "habit": "own", "previous": rhythm.START}) for o in ("-", "0:K", "0:K 2:S")] * 3
        t2 = tables.Table(("part", "habit", "previous"), "x").fit(units2 + units[6:])
        stays = {t2.draw(("drums", "own", rhythm.START), rng, floored=False, floor_k=2, floor_outcomes=tables.FLOOR_OUTCOMES) for _ in range(40)}
        self.assertTrue(stays <= {"-", "0:K", "0:K 2:S"})                                  # one song, three bars: its own vocabulary, kept

    def test_the_pair_of_samples_applies_whole_and_within_reach(self):
        """layer_samples counts the counter-line's pairs too; a pair is taken only from the part's own pairs and only where the
        pack holds both samples; a kit slot takes only a sample the game plays as a drum."""
        from bitcomposer.translate import tables, pack
        bars = [(4.0 * k, 4.0 * k + 4.0) for k in range(2)]
        line = [(4.0 * k + i, 0.9, 72.0, "aaaaaaaaaa1") for k in range(2) for i in range(4)]
        other = [(4.0 * k + i + 0.5, 0.4, 60.0, "bbbbbbbbbb2") for k in range(2) for i in range(4)]
        s = rhythm.Song("t", 4, 12, bars, [], notes={"counter": line + other}, sid="s", game="g")
        s.voice_notes = {3: ("counter", line), 4: ("counter", other)}
        self.assertEqual([(u.values["part"], u.outcome) for u in rhythm.layer_sample_units([s])], [("counter", "saaaaaaaaaa sbbbbbbbbbb")])
        pairs = tables.Table(("part",), "layer_samples", votes=tables.SHARES).fit(
            [tables.Unit(f"s{i}", "g", "sline ssecond", {"part": "accompaniment"}) for i in range(3)])
        rng = random.Random(1)
        self.assertIsNone(whole.pair_for({"layer_samples": pairs}, "counter", {"sline", "ssecond"}, rng))      # no counter pairs: none, not another part's
        self.assertIsNone(whole.pair_for({"layer_samples": pairs}, "accompaniment", {"ssecond"}, rng))         # the pack lacks the line's: none, not half
        self.assertEqual(whole.pair_for({"layer_samples": pairs}, "accompaniment", {"sline", "ssecond"}, rng), ("sline", "ssecond"))
        ranges = tables.Table(("part",), "ranges", votes=tables.SHARES).fit([tables.Unit(f"s{i}", "g", "36-48", {"part": "slow"}) for i in range(3)])
        self.assertFalse(whole.reaches(ranges, "slow", (52, 64), rng))                                          # a bass sample under a voice an octave above it
        self.assertTrue(whole.reaches(ranges, "slow", (40, 52), rng))
        self.assertTrue(whole.reaches(ranges, "unknown", (80, 92), rng))
        g = pack.Gathered(game="g")
        g.uses["drums"].update({"kick": 50, "mallet": 57}); g.uses["melody"].update({"mallet": 300}); g.uses["counter"].update({"mallet": 347})
        self.assertEqual(pack.drum_uses(g), {"kick": 50})

    def test_levels_arc_and_one_timbre_pairs(self):
        """The levels words count a part's level against the song's loudest and a second voice's against its line's; the arc
        words place a tune's climax and the other phrases under it; a pair with one sample for both voices applies as the
        line's sample; the pack carries each sample's envelope and gives the kit's other slot to the game's own other strikes."""
        from bitcomposer.translate import phrases, tables, pack
        s = rhythm.Song("t", 4, 12, [(0.0, 4.0)], [], notes={}, sid="s", game="g")
        s.levels = {"melody": 0.22, "bass": 0.28, "accompaniment": 0.19}
        self.assertEqual({u.values["part"]: u.outcome for u in rhythm.level_units([s])}, {"melody": "0.8", "bass": "1.0", "accompaniment": "0.7"})
        line = [(0.5 * i, 0.4, 60.0, "a") for i in range(8)]; other = [(float(i), 0.9, 52.0, "b") for i in range(4)]
        s.notes = {"accompaniment": line + other}; s.voice_notes = {3: ("accompaniment", line), 4: ("accompaniment", other)}
        s.voice_levels = {3: 0.20, 4: 0.12}
        self.assertEqual([u.outcome for u in rhythm.layer_level_units([s])], ["0.6"])
        self.assertEqual([phrases.place_of(i, 5) for i in range(5)], ["opening", "early", "middle", "late", "closing"])
        self.assertEqual(phrases.place_of(0, 1), "opening")
        self.assertEqual((phrases._class(0, phrases.BELOW), phrases._class(4, phrases.BELOW), phrases._class(12, phrases.BELOW), phrases._class(6, phrases.ABOVE)), ("0", "3-5", "10+", "6+"))
        pairs = tables.Table(("part",), "layer_samples", votes=tables.SHARES).fit([tables.Unit(f"s{i}", "g", "sx sx", {"part": "accompaniment"}) for i in range(3)])
        self.assertEqual(whole.pair_for({"layer_samples": pairs}, "accompaniment", set(), random.Random(1)), ("same", "same"))
        g = pack.Gathered(game="g")
        g.envelopes["k"].update({("adsr", 0xFF, 0xE0): 5, ("gain", 0x7F): 1}); g.envelopes["j"].update({("gain", 0x60): 2})
        self.assertEqual((pack.envelope_of(g, "k"), pack.envelope_of(g, "j"), pack.envelope_of(g, "z")), ({"adsr": [255, 224]}, {"gain": 96}, None))
        g.other.update({"snare": 500, "mallet": 57, "hit": 15})
        self.assertEqual(pack.other_slot(g, {"snare": 1, "mallet": 1}), "snare")
        self.assertIsNone(pack.other_slot(g, {}))

    def test_a_notes_gap_runs_into_the_next_bar_and_its_share_follows_the_gap(self):
        """A bar's last note runs to the next bar's first onset (the gap the share was counted against); the share a note
        sounds may come by the gap's class (gap_sounds); the second bass voice follows the line's pitch where they strike together."""
        from bitcomposer.translate import writer, tables, vocab
        bars = [(0.0, 4.0), (4.0, 8.0)]
        song = rhythm.Song("w", 4, 12, bars, [vocab.Span(0.0, 8.0, 0, "", 1.0)], notes={}, sid="w", game="g", tonic=0, mode="major")
        figures = ["0:R 3:R", "1/2:R 2:R"]
        self.assertEqual(writer.first_onset(figures, bars, 1), 4.5)
        self.assertIsNone(writer.first_onset(figures, bars, 2))
        notes, _, _ = writer.realize(figures[0], 0.0, 4.0, song, 36, 1.0, {0, 2, 4, 5, 7, 9, 11}, 0, None, runs_to=4.5)
        self.assertEqual([(a, b) for a, b, m in notes], [(0.0, 3.0), (3.0, 4.5)])                 # the last note runs on to 4.5, not 4.0
        shares = {"<0.5": 0.9, "0.5-1": 0.5, "1-2": 0.5, "2-4": 1.0, "4+": 1.0}
        self.assertEqual((writer.share_at(shares, 0.25), writer.share_at(shares, 0.5), writer.share_at(shares, 3.0), writer.share_at(0.7, 3.0)), (0.9, 0.5, 1.0, 0.7))
        s = rhythm.Song("t", 4, 12, bars, [], notes={}, sid="s", game="g")
        line = [(0.0, 3.9, 36.0, "a"), (4.0, 1.0, 36.0, "a"), (6.0, 1.9, 38.0, "a")]
        second = [(0.0, 0.25, 36.0, "b"), (0.5, 0.25, 36.0, "b"), (1.0, 2.9, 36.0, "b"), (4.0, 0.25, 36.0, "b"), (4.5, 3.4, 36.0, "b")]
        s.notes = {"bass": line + second}; s.voice_notes = {1: ("bass", line), 2: ("bass", second)}
        units = rhythm.gap_sound_units([s])
        by = {(u.values["voice"], u.values["gap"]): u.outcome for u in units}
        self.assertEqual((by[("line", "4+")], by[("second", "0.5-1")], by[("second", "2-4")]), ("1.0", "0.5", "1.0"))
        self.assertEqual((rhythm.gap_class(0.25), rhythm.gap_class(0.5), rhythm.gap_class(4.0)), ("<0.5", "0.5-1", "4+"))   # split at the half since round 95
        # the second bass voice on the line's pitch: a table that says "the same note" with the line and "hold" alone
        iv = tables.Table(("part", "kind", "line", "previous"), "voice_intervals", votes=tables.SHARES).fit(
            [tables.Unit(f"s{i}", "g", "0", {"part": "bass", "kind": "apart", "line": "scale", "previous": p}) for i in range(20) for p in (rhythm.START, "0")])
        mv = tables.Table(("part", "kind", "place"), "voice_moves", votes=tables.SHARES).fit(
            [tables.Unit(f"s{i}", "g", o, {"part": "bass", "kind": "apart", "place": pl}) for i in range(20) for o, pl in (("2", "with"), ("0", "alone"))])   # with the line it moves as the line does
        shared = {("line", (0, __import__("fractions").Fraction(0))): 40.0, ("line", (0, __import__("fractions").Fraction(2))): 43.0}
        midi, steps = writer.beside_pitch({"voice_intervals": iv, "voice_moves": mv}, "bass", "apart", {0, 2, 4, 5, 7, 9, 11}, random.Random(1), 43.0, "0", 40.0, 2)
        self.assertEqual((midi, steps), (43, "0"))
        midi, steps = writer.beside_pitch({"voice_intervals": iv, "voice_moves": mv}, "bass", "apart", {0, 2, 4, 5, 7, 9, 11}, random.Random(1), None, "0", 43.0, 0)
        self.assertEqual((midi, steps), (43, None))

    def test_the_second_bass_voice_is_a_mask_over_the_line(self):
        """The second bass voice's bar is counted as a mask over the sustained line's onsets plus its own (as the chord parts'
        are), and written from the line's figure: the line's marks where it strikes with the line, the root at its own onsets."""
        from fractions import Fraction
        from bitcomposer.translate import writer
        bars = [(4.0 * k, 4.0 * k + 4.0) for k in range(4)]
        line = [(4.0 * k + i, 0.9, [36.0, 36.0, 43.0, 43.0][i], "a") for k in range(4) for i in range(4)]          # the beats
        slap = [(4.0 * k + t, 0.2, 36.0, "b") for k in range(4) for t in (0.0, 0.5, 1.0, 2.0, 2.5, 3.5)]            # beats 1, 2, 3 and three of its own
        s = rhythm.Song("t", 4, 12, bars, [], notes={"bass": line + slap}, sid="s", game="g", bpm=120.0)
        s.voice_notes = {1: ("bass", line), 2: ("bass", slap)}
        units = [u for u in rhythm.second_figure_units([s]) if u.values["part"] == "bass"]
        self.assertEqual(len(units), 4)
        self.assertEqual((units[0].outcome, units[0].values["onsets"], units[0].values["line"]), ("1 1 1 0 | 1/2 5/2 7/2", "4", "0 1 2 3"))
        self.assertEqual(writer.mask_figure("0:R 1:R 2:5 3:5", "1 1 1 0 | 1/2 5/2 7/2"), "0:R 1/2:R 1:R 2:5 5/2:R 7/2:R")
        self.assertEqual(writer.mask_figure("0:R 1:R 2:5 3:5", "-"), writer.REST)
        self.assertEqual(writer.mask_figure(writer.REST, "1 1"), writer.REST)

    def test_the_bass_locks_to_the_kits_accents(self):
        """The kit's accents are the positions where two pieces strike together; bass_locks counts the share of them the bass
        strikes with; a table's floor may step down where its context has too few songs."""
        from bitcomposer.translate import tables
        bars = [(0.0, 4.0), (4.0, 8.0)]
        drums = [(t, 0.1, float("nan"), "kick") for t in (0.0, 2.0, 4.0, 6.0)] + [(t, 0.1, float("nan"), "hat") for t in (0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0)]
        self.assertEqual(rhythm.kit_accents(drums, bars, 12), {0: {0, 2}, 1: {0, 2}})
        bass = [(0.0, 0.9, 36.0, "b"), (2.0, 0.9, 36.0, "b"), (4.0, 0.9, 36.0, "b"), (5.5, 0.4, 38.0, "b")]
        s = rhythm.Song("t", 4, 12, bars, [], notes={"bass": bass, "drums": drums}, sid="s", game="g")
        s.voice_notes = {1: ("bass", bass)}
        self.assertEqual([u.outcome for u in rhythm.bass_lock_units([s])], ["0.8"])                 # three of the four accents carry a bass note
        units = [tables.Unit("s1", "g", "1 1", {"part": "bass", "onsets": "2"})] * 4 + [tables.Unit(f"s{i}", "g", "1 0 | 1/2", {"part": "bass", "onsets": "3"}) for i in range(2, 6)]
        t = tables.Table(("part", "onsets"), "m").fit(units)
        rng = random.Random(1)
        held = {t.draw(("bass", "2"), rng, floored=False, floor_k=2) for _ in range(20)}
        self.assertEqual(held, {"1 1"})                                                               # the one-song floor, as it stands
        stepped = {t.draw(("bass", "2"), rng, floored=False, floor_k=2, floor_songs=2) for _ in range(40)}
        self.assertIn("1 0 | 1/2", stepped)                                                           # the floor steps down to the part: its other songs' masks reach

    def _tune_and_counter(self):
        """A four-bar song: the tune on the beats of bars 0 to 2 (resting in bar 3), the counter with it on beats 1 and 3,
        its own on the and of 4, and alone in bar 3; the counter on another sample, a third below."""
        from bitcomposer.translate import vocab
        bars = [(4.0 * k, 4.0 * k + 4.0) for k in range(4)]
        tune = [(4.0 * k + i, 0.9, [64.0, 65.0, 67.0, 65.0][i], "lead") for k in range(3) for i in range(4)]
        counter = [(4.0 * k + t, 0.9, m, "ctr") for k in range(3) for t, m in ((0.0, 60.0), (2.0, 64.0), (3.5, 62.0))] + [(12.0, 1.9, 60.0, "ctr"), (14.0, 1.9, 62.0, "ctr")]
        s = rhythm.Song("t", 4, 12, bars, [vocab.Span(0.0, 16.0, 0, "", 1.0)], notes={"melody": tune, "counter": counter}, sid="s", game="g", bpm=120.0, tonic=0, mode="major")
        s.voice_notes = {1: ("melody", tune), 2: ("counter", counter)}
        s.levels = {"melody": 0.20, "counter": 0.20}
        return s, bars

    def test_the_counter_is_a_mask_over_the_tune(self):
        """counter_figures counts the counter-line's bar as a mask over the tune's onsets plus its own (the tune's line as the
        line), and its own onsets alone where the tune rests; apply_mask gives those own onsets at a resting line."""
        s, _ = self._tune_and_counter()
        units = rhythm.counter_figure_units([s])
        self.assertEqual([u.outcome for u in units], ["1 0 1 0 | 7/2"] * 3 + ["| 0 2"])
        self.assertEqual(units[0].values, {"part": "counter", "weight": "half", "feel": "duple", "tempo": rhythm.band(120.0), "onsets": "4", "line": "0 1 2 3"})   # the counter's weight since round 47
        self.assertEqual((units[3].values["onsets"], units[3].values["line"]), ("0", "-"))
        self.assertEqual(rhythm.apply_mask("0 1 2 3", "1 0 1 0 | 7/2"), "0 2 7/2")
        self.assertEqual(rhythm.apply_mask("-", "| 0 2"), "0 2")                                   # the tune rests: the counter's own onsets
        self.assertEqual(rhythm.apply_mask("-", "-"), "-")
        self.assertEqual(rhythm.second_mask([], []), "-")
        s.notes["counter"] = s.notes["counter"][:3]                                                 # the counter in bar 0 only: bars 1 and 2 rest
        s.voice_notes[2] = ("counter", s.notes["counter"])                                          # under the tune, bar 3 (both rest) is not counted
        self.assertEqual([u.outcome for u in rhythm.counter_figure_units([s])], ["1 0 1 0 | 7/2", "-", "-"])
        del s.notes["counter"]
        self.assertEqual(rhythm.counter_figure_units([s]), [])

    def test_the_counter_takes_its_pitch_beside_the_tune(self):
        """The voice words count the counter beside the tune with the kind its sample relation (counter_samples: same or
        other); writer.counter writes it over the mask's positions: the tune's pitch and the drawn interval where they strike
        together, its own move between, its own onsets alone where the tune rests."""
        from fractions import Fraction
        from bitcomposer.translate import writer, tables, vocab
        s, bars = self._tune_and_counter()
        self.assertEqual([u.outcome for u in rhythm.counter_sample_units([s])], ["other"])
        s.notes["counter"] = [n[:3] + ("lead",) for n in s.notes["counter"]]; s.voice_notes[2] = ("counter", s.notes["counter"])
        self.assertEqual(rhythm.counter_kind(s), "same")
        iv = [u for u in rhythm.voice_interval_units([s]) if u.values["part"] == "counter"]
        self.assertEqual(({u.outcome for u in iv}, iv[0].values["kind"], iv[0].values["previous"], iv[1].values["previous"]), ({"-2"}, "same", rhythm.START, "-2"))
        mv = [u for u in rhythm.voice_move_units([s]) if u.values["part"] == "counter"]
        self.assertEqual(sorted({(u.outcome, u.values["place"]) for u in mv}), [("-1", "alone"), ("-1", "with"), ("1", "alone"), ("2", "with")])
        # the writer: a table that says "a third below the tune" and "hold the note" with the tune, "a step up" alone
        iv_t = tables.Table(("part", "kind", "line", "previous"), "voice_intervals", votes=tables.SHARES).fit(
            [tables.Unit(f"s{i}", "g", "-2", {"part": "counter", "kind": "other", "line": "scale", "previous": p}) for i in range(20) for p in (rhythm.START, "-2")])
        mv_t = tables.Table(("part", "kind", "place"), "voice_moves", votes=tables.SHARES).fit(
            [tables.Unit(f"s{i}", "g", o, {"part": "counter", "kind": "other", "place": pl}) for i in range(20) for o, pl in (("0", "with"), ("-1", "with"), ("1", "alone"))])   # back from the step too (round 66)
        vals = tables.Table(("part", "value", "habit"), "values", votes=tables.SHARES).fit([tables.Unit(f"s{i}", "g", "held", {"part": "counter", "value": "1", "habit": "held"}) for i in range(3)])
        song = rhythm.Song("w", 4, 12, bars, [vocab.Span(0.0, 16.0, 0, "", 1.0)], notes={}, sid="w", game="g", tonic=0, mode="major")
        tune = [(4.0 * k + i, 4.0 * k + i + 0.9, 72.0, 0) for k in range(3) for i in range(4)]           # the tune repeats C on every beat
        tune_figs = ["0 1 2 3"] * 3 + [writer.REST]
        notes, figures, log = writer.counter(song, tune, tune_figs, ["1 0 1 0 | 7/2", "1 1 1 1", writer.REST, "| 0 2"], (48, 96),
                                             {"voice_intervals": iv_t, "voice_moves": mv_t, "values": vals}, random.Random(1), "other",
                                             key=(0, "major"), articulation="held", register=(60, 84))
        self.assertEqual(figures, ["0 2 7/2", "0 1 2 3", writer.REST, "0 2"])
        got = {round(a, 2): int(m) for a, b, m in notes}
        self.assertEqual(got, {0.0: 69, 2.0: 69, 3.5: 71, 4.0: 69, 5.0: 69, 6.0: 69, 7.0: 69, 12.0: 71, 14.0: 72})   # A under C; a step up alone, the
        self.assertAlmostEqual(notes[1][1] - notes[1][0], 1.5 * writer.HELD, places=3)           # tune's rest in bar 3 filled from where it left off
        self.assertAlmostEqual(notes[2][1] - notes[2][0], 0.5 * writer.HELD, places=3)           # a bar's last note runs to the next bar's first onset
        self.assertAlmostEqual(notes[6][1] - notes[6][0], 1.0 * writer.HELD, places=3)           # ...but stops at the bar line before a rest bar
        self.assertIn("6 with the tune's onsets, 3 its own", log[0])
        # the plan draws the kind and the level once a song, and the rendering gives a "same" counter the tune's sample
        kinds = tables.Table(("part",), "counter_samples", votes=tables.SHARES).fit([tables.Unit(f"s{i}", "g", "same", {"part": "counter"}) for i in range(3)])
        self.assertEqual(whole._draw({"counter_samples": kinds}, "counter_samples", ("counter",), random.Random(1)), "same")

    def test_a_voice_beside_a_counter_that_follows_the_tune(self):
        """Round 76: the counter's own voices beside its line are counted as an upper part's (voice_intervals and voice_moves
        under the layer relation, second_figures as a mask over the counter's bar), beside the counter-line's units against
        the tune (kind same or other), and writer.counter writes such a voice with the counter's line as its tune. Rounds 29
        to 75 had left every voice beside a counter that follows the tune silent ("no word yet")."""
        from bitcomposer.translate import writer, tables, vocab
        s, bars = self._tune_and_counter()
        third = [(4.0 * k + t, 0.9, m, "ctr") for k in range(3) for t, m in ((0.0, 57.0), (1.0, 59.0), (2.0, 60.0))]   # a third under the line
        s.notes["counter"] = s.notes["counter"] + third                   # on beats 1 and 3 of bars 0 to 2, its own note on beat 2: apart
        s.voice_notes[3] = ("counter", third)                             # (harness.relation: half their events shared, under DOUBLING)
        iv = [u for u in rhythm.voice_interval_units([s]) if u.values["part"] == "counter"]
        self.assertEqual({u.values["kind"] for u in iv}, {"apart", "other"})               # the voice beside the line, and the line beside the tune
        self.assertEqual({u.outcome for u in iv if u.values["kind"] == "apart"}, {"-2"})
        self.assertEqual([u.values["previous"] for u in iv if u.values["kind"] == "apart"][:2], [rhythm.START, "-2"])
        self.assertTrue([u for u in rhythm.voice_move_units([s]) if u.values["part"] == "counter" and u.values["kind"] == "apart"])
        sf = [u for u in rhythm.second_figure_units([s]) if u.values["part"] == "counter"]
        self.assertEqual([u.outcome for u in sf], ["1 1 0 | 1"] * 3 + ["-"])                # with the line's beats 1 and 3, its own on 2; bar 3 the line alone
        self.assertEqual(sf[0].values["layer"], rhythm.layer_share_class(9 / 11))
        # the writer: the voice words under the apart relation, the counter's line as the tune it is written beside
        iv_t = tables.Table(("part", "kind", "line", "previous"), "voice_intervals", votes=tables.SHARES).fit(
            [tables.Unit(f"s{i}", "g", "-2", {"part": "counter", "kind": "apart", "line": "scale", "previous": p}) for i in range(20) for p in (rhythm.START, "-2")])
        mv_t = tables.Table(("part", "kind", "place"), "voice_moves", votes=tables.SHARES).fit(
            [tables.Unit(f"s{i}", "g", o, {"part": "counter", "kind": "apart", "place": pl}) for i in range(20) for o, pl in (("0", "with"), ("-1", "with"), ("1", "alone"))])
        vals = tables.Table(("part", "value", "habit"), "values", votes=tables.SHARES).fit([tables.Unit(f"s{i}", "g", "held", {"part": "counter", "value": "1", "habit": "held"}) for i in range(3)])
        song = rhythm.Song("w", 4, 12, bars, [vocab.Span(0.0, 16.0, 0, "", 1.0)], notes={}, sid="w", game="g", tonic=0, mode="major")
        line = [(4.0 * k + i, 4.0 * k + i + 0.9, 72.0, 0) for k in range(2) for i in range(4)]          # the counter's line: C on every beat
        notes, figures, log = writer.counter(song, line, ["0 1 2 3"] * 2 + [writer.REST] * 2, ["1 1 1 1", "1 0 1 0", writer.REST, writer.REST], (48, 96),
                                             {"voice_intervals": iv_t, "voice_moves": mv_t, "values": vals}, random.Random(1), "apart",
                                             key=(0, "major"), articulation="held", register=(60, 84))
        self.assertEqual(figures, ["0 1 2 3", "0 2", writer.REST, writer.REST])
        self.assertEqual({int(m) for _, _, m in notes}, {69})                                 # A under C, a third below, at every masked onset
        self.assertEqual(len(notes), 6)
        self.assertIn("beside the tune on the apart sample", log[0])

    def test_the_counters_level_is_drawn_under_the_tunes_share(self):
        """counter_shares counts the counter's level as a share of the song's loudest part's, in tenths, by the band the
        tune's own share falls in; the plan draws it after the tune's levels draw, under that draw's band, in place of the
        counter's own levels draw, so the counter can never be louder than the loudest part (round 31; counter_levels,
        the ratio to the tune drawn apart from the tune's share, had put Whole 28's counter at 1.05 of the loudest)."""
        from bitcomposer.translate import tables
        s, _ = self._tune_and_counter()
        s.levels = {"melody": 0.20, "counter": 0.16, "bass": 0.25}
        self.assertEqual([(u.outcome, u.values) for u in rhythm.counter_share_units([s])], [("0.6", {"part": "counter", "tune": "0.7-0.8"})])
        s.levels = {"melody": 0.10, "counter": 0.30}                                                 # the counter the loudest: 1.0, never more
        self.assertEqual([(u.outcome, u.values["tune"]) for u in rhythm.counter_share_units([s])], [("1.0", "<0.7")])
        s.levels = {"melody": 0.30, "counter": 0.12}
        self.assertEqual([(u.outcome, u.values["tune"]) for u in rhythm.counter_share_units([s])], [("0.4", "0.9+")])
        self.assertEqual([rhythm.tune_share_band(x) for x in (0.4, 0.6, 0.7, 0.8, 0.9, 1.0)], ["<0.7", "<0.7", "0.7-0.8", "0.7-0.8", "0.9+", "0.9+"])
        del s.notes["counter"]
        self.assertEqual(rhythm.counter_share_units([s]), [])
        units = lambda name, outcome, part, **more: [tables.Unit(f"s{i}", "g", outcome, {"part": part, **more}) for i in range(3)]   # noqa: E731
        shares = tables.Table(("part", "tune"), "counter_shares", votes=tables.SHARES).fit(
            units("counter_shares", "0.5", "counter", tune="<0.7") + units("counter_shares", "0.7", "counter", tune="0.7-0.8") + units("counter_shares", "1.0", "counter", tune="0.9+"))
        models = {"balance": tables.Table(("part",), "balance", votes=tables.SHARES).fit([tables.Unit(f"s{i}", "g", "bass=half counter=half melody=main", {"part": rhythm.ARRANGEMENT}) for i in range(3)]),
                  "levels": tables.Table(("part",), "levels", votes=tables.SHARES).fit(units("levels", "0.8", "melody") + units("levels", "0.4", "counter") + units("levels", "1.0", "bass")),
                  "counter_shares": shares,
                  "counter_samples": tables.Table(("part",), "counter_samples", votes=tables.SHARES).fit(units("counter_samples", "same", "counter"))}
        for seed in range(1, 6):                                                                     # the tune at 0.8: the counter from its band's own votes
            p = whole.plan(models, seed, "g")                                                        # (three songs, terminal at the part, 3/(3+1) at the band)
            self.assertEqual((p.levels["melody"], p.levels["bass"]), (0.8, 1.0))
            self.assertIn(p.levels["counter"], (0.5, 0.7, 1.0))
            self.assertEqual((p.extras["counter"]["sample"], p.extras["counter"]["level"]), ("same", p.levels["counter"]))
            self.assertLessEqual(p.levels["counter"], 1.0)
            self.assertIn(f"counter beside the tune: same sample, level {p.levels['counter']:.1f} of the loudest under the tune's 0.8", p.log)
        drawn = {whole.plan(models, seed, "g").levels["counter"] for seed in range(1, 40)}
        self.assertIn(0.7, drawn)                                                                    # the band's own outcome comes up
        self.assertEqual({k: round(v, 3) for k, v in shares.weights(("counter", "0.7-0.8"), floor_k=whole.PLAN_FLOOR, min_songs=whole.PLAN_SONGS).items()},
                         {"0.7": 0.833, "0.5": 0.083, "1.0": 0.083})                                 # 3/(3+1) the band's, the part's level the rest
        models["levels"] = tables.Table(("part",), "levels", votes=tables.SHARES).fit(units("levels", "0.5", "melody") + units("levels", "0.4", "counter") + units("levels", "1.0", "bass"))
        p = whole.plan(models, 1, "g")                                                               # a quiet tune: the band under 0.7, where the
        self.assertIn(p.levels["counter"], (0.5, 0.7, 1.0))                                          # counter may be the loudest, as FFVI's is
        self.assertIn("of the loudest under the tune's 0.5", p.log[-1])
        p = whole.plan({k: v for k, v in models.items() if k != "counter_shares"}, 1, "g")         # no table: the counter's own levels draw stands
        self.assertNotIn("level", p.extras["counter"])
        self.assertIn(p.levels["counter"], (0.4,))

    def test_the_bands_levels_are_the_balance_tokens_as_one_unit(self):
        """The balance token carries each part's level as a share of the song's loudest part's (the fifth field, level_units'
        unit; the drums' in the same field of a weightless token); the plan takes every part's level from the token where its
        song has the part, so a song's level layout is one of the game's songs' whole, and falls back to the `levels` draw
        (the counter to counter_shares under the tune's band) for a part the token lacks; the draws stay on the stream, so
        the plan's key, form, band and every other draw are what they were (round 32: drawn apart, the accompaniment had
        landed strictly above the tune in 0.30 of plans against FFVI's 0.17). The loudest part plays at TOP_LEVEL."""
        from bitcomposer.translate import tables
        s = self._song()
        s.voice_notes = {0: ("bass", s.notes["bass"]), 1: ("melody", s.notes["melody"]), 2: ("drums", s.notes["drums"])}
        s.levels = {"melody": 0.22, "bass": 0.28, "drums": 0.14}
        tokens = rhythm.balance_units([s])[0].outcome.split()
        self.assertEqual(tokens[-1], "tempo=medium")                                                # the song's tempo class rides last (round 54)
        self.assertTrue(tokens[-2].startswith("top="), tokens)                                      # the loudest part's level before it (round 59; loud= where measured)
        tokens = [t for t in tokens if not t.startswith(("tempo=", "top=", "loud=", "key="))]
        self.assertEqual([t.split(":")[4] if t.count(":") > 4 else t.split(":")[-1] for t in tokens if not t.startswith(("shapes=", "form="))], ["1.0", "0.5", "0.8"])   # bass, drums, melody: shares of the loudest (the song-level shapes= and form= fields aside, rounds 112-113)
        self.assertTrue(tokens[0].startswith("bass=") and tokens[0].count(":") >= 8 and tokens[0].split(":")[4] == "1.0", tokens)   # weight:register:sounded share:voices:level:::sample:habit (a period field after, round 106)
        self.assertTrue(tokens[1].startswith("drums=:::Kc:0.5:::") and tokens[1].split(":")[8].endswith("+mixed") and tokens[1].split(":")[7].startswith("K="), tokens)   # level, kit, habit                             # the drums keep a level, then their habit (round 62)
        s.levels = {}
        self.assertTrue(rhythm.balance_units([s])[0].outcome.split()[1].startswith("drums=:::Kc::::K="))   # no levels read: the channels, the kit and habit alone (round 87)
        units = lambda name, outcome, part, **more: [tables.Unit(f"s{i}", "g", outcome, {"part": part, **more}) for i in range(3)]   # noqa: E731
        token = "accompaniment=half:56-68:0.8:2 bass=half:36-44:0.9:1:1.0 counter=minor:60-72:0.8:1 drums=::::0.6 melody=main:64-84:0.9:1:0.7"
        models = {"balance": tables.Table(("part",), "balance", votes=tables.SHARES).fit(units("balance", token, rhythm.ARRANGEMENT)),
                  "levels": tables.Table(("part",), "levels", votes=tables.SHARES).fit(
                      units("levels", "0.3", "accompaniment") + units("levels", "0.9", "bass") + units("levels", "0.4", "counter") + units("levels", "0.2", "drums") + units("levels", "0.5", "melody")),
                  "counter_shares": tables.Table(("part", "tune"), "counter_shares", votes=tables.SHARES).fit(units("counter_shares", "0.8", "counter", tune="0.7-0.8")),
                  "counter_samples": tables.Table(("part",), "counter_samples", votes=tables.SHARES).fit(units("counter_samples", "other", "counter"))}
        for seed in range(1, 6):
            p = whole.plan(models, seed, "g")
            self.assertEqual(p.band, ["accompaniment", "bass", "counter", "drums", "melody"])
            self.assertEqual({r: p.levels[r] for r in ("bass", "drums", "melody")}, {"bass": 1.0, "drums": 0.6, "melody": 0.7})   # the token's
            self.assertEqual(p.levels["accompaniment"], 0.3)                                        # the token lacks it: the levels draw
            self.assertEqual(p.levels["counter"], 0.8)                                              # and counter_shares under the tune's 0.7
            self.assertEqual(p.level_from, {"accompaniment": "levels", "bass": "balance", "counter": "counter_shares", "drums": "balance", "melody": "balance"})
            self.assertEqual(p.extras["counter"]["level"], 0.8)
            self.assertIn("levels from the balance: bass=1.0 drums=0.6 melody=0.7; drawn from levels: accompaniment=0.3 counter=0.4; the loudest bass", p.log)
            self.assertIn("counter beside the tune: other sample, level 0.8 of the loudest under the tune's 0.7", p.log)
            self.assertEqual(p.weights, {"accompaniment": "half", "bass": "half", "counter": "minor", "melody": "main"})   # the drums' empty weight is no weight
            self.assertEqual(p.registers["bass"], (36, 44))
        # the token's own counter level stands, and the counter_shares draw is made all the same (the stream as it was)
        full = token.replace("counter=minor:60-72:0.8:1 ", "counter=minor:60-72:0.8:1:0.5 ")
        models["balance"] = tables.Table(("part",), "balance", votes=tables.SHARES).fit(units("balance", full, rhythm.ARRANGEMENT))
        p = whole.plan(models, 1, "g")
        self.assertEqual((p.levels["counter"], p.level_from["counter"], p.extras["counter"]["level"]), (0.5, "balance", 0.5))
        self.assertIn("counter beside the tune: other sample, level 0.5 of the loudest with the band's, the balance's", p.log)
        self.assertEqual(p.levels["accompaniment"], 0.3)
        without = whole.plan({k: v for k, v in models.items() if k != "counter_shares"}, 1, "g")
        self.assertEqual(without.levels, p.levels)                                                  # the draw changed no level
        self.assertEqual((p.extras["counter"]["sample"], p.extras["counter"]["sample_from"], p.kinds), ("other", "counter_samples", {}))
        # the counter's kind with its level (round 39): the token's seventh field stands over the counter_samples draw, the draw made
        kinded = full.replace("counter=minor:60-72:0.8:1:0.5 ", "counter=minor:60-72:0.8:1:0.5::same ")
        pk = whole.plan({**models, "balance": tables.Table(("part",), "balance", votes=tables.SHARES).fit(units("balance", kinded, rhythm.ARRANGEMENT))}, 1, "g")
        self.assertEqual((pk.extras["counter"]["sample"], pk.extras["counter"]["sample_from"], pk.kinds), ("same", "balance", {"counter": "same"}))
        self.assertIn("counter beside the tune: same sample with the band's, level 0.5 of the loudest with the band's, the balance's", pk.log)
        self.assertEqual((pk.tonic, pk.mode, pk.parts, pk.band, pk.registers, pk.habits, pk.levels, pk.layer_levels),
                         (p.tonic, p.mode, p.parts, p.band, p.registers, p.habits, p.levels, p.layer_levels))
        # the unit writes the field for a song with a counter: same where it plays the tune's sample, other where not
        s = self._song()
        s.notes["counter"] = [(4.0 * i + x, 0.9, m - 4, "m") for i in range(4, 8) for x, m in ((0.0, 67.0), (2.0, 71.0))]
        s.voice_notes = {0: ("bass", s.notes["bass"]), 1: ("melody", s.notes["melody"]), 2: ("drums", s.notes["drums"]), 3: ("counter", s.notes["counter"])}
        s.levels = {"melody": 0.22, "bass": 0.28, "drums": 0.14, "counter": 0.22}
        ctr = [t for t in rhythm.balance_units([s])[0].outcome.split() if t.startswith("counter=")][0]
        self.assertTrue(":0.8::same:" in ctr and ctr.count(":") == 8, ctr)
        s.notes["counter"] = [(a, b, c, "x") for a, b, c, _ in s.notes["counter"]]; s.voice_notes[3] = ("counter", s.notes["counter"])
        self.assertIn("::other:", [t for t in rhythm.balance_units([s])[0].outcome.split() if t.startswith("counter=")][0])
        s.levels = {}
        self.assertEqual([t for t in rhythm.balance_units([s])[0].outcome.split() if t.startswith("counter=")][0].split(":")[4:7], ["", "", ""])   # no level: no kind either
        # the same seed with the token's levels and without: every other draw identical (the levels draws stay in place)
        bare = whole.plan({**models, "balance": tables.Table(("part",), "balance", votes=tables.SHARES).fit(
            units("balance", "accompaniment=half:56-68:0.8:2 bass=half:36-44:0.9:1 counter=minor:60-72:0.8:1 drums melody=main:64-84:0.9:1", rhythm.ARRANGEMENT))}, 1, "g")
        self.assertEqual((bare.tonic, bare.mode, bare.parts, bare.band, bare.registers, bare.habits, bare.layer_levels, bare.extras["counter"]["sample"]),
                         (p.tonic, p.mode, p.parts, p.band, p.registers, p.habits, p.layer_levels, p.extras["counter"]["sample"]))
        self.assertEqual(bare.levels, {"accompaniment": 0.3, "bass": 0.9, "counter": 0.8, "drums": 0.2, "melody": 0.5})
        self.assertEqual(set(bare.level_from.values()), {"levels", "counter_shares"})
        self.assertNotIn("levels from the balance", " ".join(bare.log))
        # the token's tempo class: a plan whose tempo draw falls outside it draws the tempo again under the class (round 54)
        slow = tables.Table(("part",), "balance", votes=tables.SHARES).fit(units("balance", token + " tempo=slow", rhythm.ARRANGEMENT))
        tempos = tables.Table(("part", "tempo"), "tempos", votes=tables.SHARES).fit(
            units("tempos", "70", "song", tempo="slow") + units("tempos", "150", "song", tempo="fast"))
        ps = whole.plan({"balance": slow, "tempos": tempos}, 1, "g")
        self.assertEqual((ps.bpm, rhythm.band(ps.bpm)), (70.0, "slow"))
        self.assertEqual(ps.band, ["accompaniment", "bass", "counter", "drums", "melody"])          # the tempo token is no part
        self.assertTrue(any("outside the band's class (slow)" in line for line in ps.log) or rhythm.band(70.0) == "slow")
        # the note level: the loudest part at TOP_LEVEL, the rest at their share, a second voice at its layer share, capped at full
        p.voices["accompaniment"] = 2; p.extras["accompaniment"]["layers"] = ["apart -12 like"]; p.extras["accompaniment"]["layer"] = "apart -12 like"
        p.layer_levels["accompaniment"] = 1.5; p.layer_levels["melody"] = 1.5
        self.assertAlmostEqual(whole.note_level(p, "bass", 0), whole.TOP_LEVEL)
        self.assertAlmostEqual(whole.note_level(p, "melody", 0), whole.TOP_LEVEL * 0.7)
        self.assertAlmostEqual(whole.note_level(p, "accompaniment", 0), whole.TOP_LEVEL * 0.3)
        self.assertAlmostEqual(whole.note_level(p, "accompaniment", 1), whole.TOP_LEVEL * 0.3 * 1.5)
        self.assertAlmostEqual(whole.note_level(p, "melody", 1), whole.TOP_LEVEL * 0.7)             # one voice: no second
        self.assertEqual(whole.note_level(p, "accompaniment", 1, {"accompaniment": {1}}), whole.TOP_LEVEL * 0.3 * 1.5)
        p.levels["accompaniment"] = 1.0
        self.assertEqual(whole.note_level(p, "accompaniment", 1), 1.0)                              # a second voice over its line at the top: the cap

    def test_a_voice_beside_a_lines_stretches_ride_the_token(self):
        """Round 90: each voice beyond a line carries, as a fifth sub-field of its layer entry, what it does beside which
        part stretch by stretch (relation_words: "dm-12x6>o", the tune an octave under through the song's sixth bar, then
        its own line); the melody's line is the heard tune, not its busiest voice (Song.voice_of); the plan parses the
        word into stretches over the written song's bars, and writes a voice by them (stretched_notes)."""
        import importlib
        from bitcomposer.translate import tables
        plan_mod = importlib.import_module("bitcomposer.translate.whole.plan")
        s = self._song()
        line = s.notes["melody"]                                                                # bars 4-7, a note a beat
        layer = [(t, 0.9, m - 12.0, "m2") for t, _, m, _ in line if t < 24] + [(t + 0.5, 0.4, 60.0, "m3") for t, _, m, _ in line if t >= 24]
        s.notes["melody"] = line + layer
        s.voice_notes = {0: ("bass", s.notes["bass"]), 1: ("melody", line), 2: ("melody", layer), 3: ("drums", s.notes["drums"])}
        s.voice_of = {2: 1}
        s.voice_levels = {0: 0.3, 1: 0.2, 2: 0.3, 3: 0.1}
        s.levels = {"bass": 0.3, "melody": 0.2, "drums": 0.1}
        self.assertEqual(rhythm.relation_words(s), {2: "dm-12x6>o"})
        self.assertEqual(rhythm.line_voice({1: line, 2: layer}, "melody", s), 1)               # the heard tune, though no busier
        self.assertEqual(rhythm.line_voice({1: line, 2: layer}, "melody"), 1)                  # without the song: the busiest (the first of equals)
        entries = rhythm.layer_tokens(s, "melody")
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0], "1.5@m2@1.00@56-60@dm-12x6>o@m2~56-60x6>m3~60-60", entries)   # the sixth sub-field its instrument by stretch (round 92)
        self.assertIn("@dm-12x6>o", rhythm.balance_units([s])[0].outcome)
        s.voice_notes[2] = ("melody", [(t + 0.5, 0.4, 60.0, "m3") for t, _, m, _ in line])      # a voice of one own stretch: no word
        self.assertEqual(rhythm.relation_words(s), {})
        self.assertFalse(any("@o" in e for e in rhythm.layer_tokens(s, "melody")), rhythm.layer_tokens(s, "melody"))
        token = "melody=main:64-84:0.9:2:0.7:1.5@sm2@1.00@55-60@dm-12x6>o:::slead bass=half:36-44:0.9:1:1.0:::sbass top=0.30 tempo=medium"
        t = tables.Table(("part",), "balance", votes=tables.SHARES).fit([tables.Unit(f"s{i}", "g", token, {"part": rhythm.ARRANGEMENT}) for i in range(3)])
        p = whole.plan({"balance": t}, 1, "g")
        self.assertEqual(p.layer_relations, {"melody": ["dm-12x6>o"]})
        self.assertEqual((p.layer_ranges["melody"], p.layer_samples["melody"], p.voice_levels["melody"]), ([(55, 60)], ["sm2"], [1.5]))
        self.assertEqual(whole.relation_word(p, "melody", 1), "dm-12x6>o")
        self.assertIsNone(whole.relation_word(p, "melody", 2))
        self.assertEqual(whole.relation_stretches("dm-12x6>o"), [("double", "melody", -12, 6), ("own", None, None, None)])
        self.assertEqual(whole.stretch_spans(whole.relation_stretches("ox9>pc+4x14>o"), 32), [("own", None, None, 0, 9), ("parallel", "counter", 4, 9, 23), ("own", None, None, 23, 32)])
        self.assertEqual(whole.stretch_spans(whole.relation_stretches("dm+12x40>o"), 20), [("double", "melody", 12, 0, 20)])   # a stretch past the end is dropped
        self.assertEqual(whole.relation_stretches("zz"), [("own", None, None, None)])            # a word the writer cannot read is its own
        melody = plan_mod.Part("melody", [(0.0, 1.0, 60.0, 0), (1.0, 2.0, 62.0, 0), (4.0, 5.0, 64.0, 0), (4.5, 5.0, 67.0, 1)], [])
        own = [(0.5, 1.0, 50.0, 1), (4.5, 5.0, 52.0, 1)]
        major = {0, 2, 4, 5, 7, 9, 11}
        log = []
        notes = whole.stretched_notes(1, own, whole.stretch_spans(whole.relation_stretches("dm-12x1>o"), 2), {"melody": melody}, major, 4, log)
        self.assertEqual(notes, [(0.0, 1.0, 48.0, 1), (1.0, 2.0, 50.0, 1), (4.5, 5.0, 52.0, 1)])   # the line (voice 0 alone) an octave under in bar 1, its own in bar 2
        self.assertEqual(log, ["voice 2 double the melody's line at -12 in bars 1-1: 2 notes"])
        notes = whole.stretched_notes(1, own, whole.stretch_spans(whole.relation_stretches("pc+4"), 2), {"melody": melody}, major, 4, log)
        self.assertEqual(notes, own)                                                             # no counter written: its own notes throughout

    def test_a_folded_blip_does_not_widen_its_stretchs_range(self):
        """Round 104: a stretch's range is the ambitus of its own sample's notes; a blip of another sample folded into it
        (roles.stretches_of) does not widen it. Battle Theme's lead stretch had read 40-80 from one synth note at 42 before
        bar 1 where the lead plays 64-79, and the written tune sat an octave under the lead (Song Check 86's The Terminal
        of Glass)."""
        s = self._song()
        line = s.notes["melody"]                                                                # bars 5-8, a note a beat
        first = [(t, d, m, "m") for t, d, m, _ in line if t < 24]
        rest = [(t, d, m - 12.0, "m2") for t, d, m, _ in line if t >= 24]
        blip = [(first[0][0] - 1.0, 0.5, first[0][2] - 24.0, "m2")]                             # one note of the other sample, two octaves under, before the line
        s.notes["melody"] = blip + first + rest
        s.voice_notes = {0: ("bass", s.notes["bass"]), 1: ("melody", s.notes["melody"]), 2: ("drums", s.notes["drums"])}
        self.assertEqual(rhythm.line_stretches(s, "melody"), "m@68-72x6>m2@56-60")             # the blip folds into the first stretch; its range stays the lead's
        mel = next(t for t in rhythm.balance_units([s])[0].outcome.split() if t.startswith("melody="))
        self.assertEqual(mel.split(":")[1], "56-72", mel)                                        # and the token's register field leaves the blip out too (44-72 with it)
        s.notes["melody"] = first + rest + [(rest[-1][0] + 1.0, 0.5, rest[-1][2] + 24.0, "m")]    # a trailing blip two octaves over: the same
        s.voice_notes[1] = ("melody", s.notes["melody"])
        self.assertEqual(rhythm.line_stretches(s, "melody"), "m@68-72x6>m2@56-60")

    def test_the_lines_instrument_by_stretch_rides_the_token(self):
        """Round 91: a line voice that changes instrument carries its stretches as the token's eleventh field
        (line_stretches: each stretch's sample, the range it plays it over, its bars from the song's first bar, the last
        open); the plan parses them, samples_for registers each stretch's sample and bound and writes the line over the
        union of the ranges, fold_line folds a note into its stretch's range by octaves, and the render takes the stretch's
        sample for the line's notes (sample_of)."""
        from types import SimpleNamespace
        from unittest import mock
        from bitcomposer import instruments
        from bitcomposer.translate import tables
        s = self._song()
        line = s.notes["melody"]                                                                # bars 5-8, a note a beat
        s.notes["melody"] = [(t, d, m, "m") for t, d, m, _ in line if t < 24] + [(t, d, m - 12.0, "m2") for t, d, m, _ in line if t >= 24]
        s.voice_notes = {0: ("bass", s.notes["bass"]), 1: ("melody", s.notes["melody"]), 2: ("drums", s.notes["drums"])}
        self.assertEqual(rhythm.line_stretches(s, "melody"), "m@68-72x6>m2@56-60")             # the first stretch through bar 6, then the rest
        self.assertEqual(rhythm.line_stretches(s, "bass"), "")                                   # one instrument: no field
        mel = next(t for t in rhythm.balance_units([s])[0].outcome.split() if t.startswith("melody="))
        self.assertEqual(mel.split(":")[10], "m@68-72x6>m2@56-60", mel)
        self.assertEqual(whole.line_stretch_list("m@68-72x6>m2@56-60"), [("m", (68, 72), 6), ("m2", (56, 60), None)])
        self.assertEqual(whole.line_stretch_list("sax3>sb@1-"), [("sa", None, 3), ("sb", None, None)])
        tok = "melody=main:56-72:0.9:1:0.7:::sm@68-72:::sm@64-76x4>sm2@52-64 bass=half:36-44:0.9:1:1.0:::sbass top=0.30 tempo=medium"
        t = tables.Table(("part",), "balance", votes=tables.SHARES).fit([tables.Unit(f"s{i}", "g", tok, {"part": rhythm.ARRANGEMENT}) for i in range(3)])
        p = whole.plan({"balance": t}, 1, "g")
        self.assertEqual(p.stretches, {"melody": [("sm", (64, 76), 4), ("sm2", (52, 64), None)]})
        self.assertEqual(p.token_samples["melody"], "sm")
        made = []
        fake = lambda name: made.append(name) or SimpleNamespace(c5_speed=32000, data=b"\0\0" * 64, loop=False, sus_loop=False, name=name)   # noqa: E731
        pack = {"voices": {"harmony": ["pad"], "lead": ["pad"], "bass_medium": ["pad"], "arp": ["pad"]}}
        with mock.patch.object(instruments, "_make_sample", fake):
            samples = whole.samples_for(p, pack, {"sm", "sm2", "sbass"}, "g", random.Random(1), {})
        self.assertEqual(samples["melody"][0], "sm")                                             # the eighth field's sample stays the default
        self.assertEqual((samples["melody:stretch:0"][0], samples["melody:stretch:1"][0]), ("sm", "sm2"))
        x = p.extras["melody"]
        reg = p.registers["melody"]
        self.assertEqual(x["stretch_spans"], [(0, 0, 4), (1, 4, p.bars)])
        self.assertEqual(x["stretch_bounds"], {0: whole.bound_of((64, 76), reg), 1: whole.bound_of((52, 64), reg)})
        self.assertEqual(p.bounds["melody"], whole.bound_of((52, 76), reg))                      # the line is written over the union
        self.assertTrue(any(l.startswith("melody's instrument by stretch") for l in p.log), p.log[-3:])
        self.assertEqual([whole.stretch_at(p, "melody", k) for k in (0, 3, 4, p.bars + 3)], [0, 0, 1, 1])
        self.assertIsNone(whole.stretch_at(p, "bass", 0))
        lo0, hi0 = x["stretch_bounds"][0]
        lo1, hi1 = x["stretch_bounds"][1]
        notes = [(0.0, 1.0, float(lo0 - 9)), (1.0, 2.0, float(hi0)), (16.0, 17.0, float(hi1 + 6)), (17.0, 18.0, float(lo1)), (18.0, 19.0, 76.0, 1)]
        folded = whole.fold_line(p, "melody", notes, 4)
        self.assertEqual(folded[0][2], float(lo0 + 3))                                           # up an octave into the first stretch's bound
        self.assertEqual(folded[1], notes[1])                                                    # inside: untouched
        self.assertEqual(folded[2][2], float(hi1 - 6))                                           # down an octave into the second's
        self.assertEqual(folded[3], notes[3])
        self.assertEqual(folded[4], notes[4])                                                    # a voice beside the line is left alone
        self.assertTrue(any("folded by octaves" in l for l in p.log))
        self.assertEqual(whole.fold_line(p, "bass", notes, 4), notes)                            # a part without stretches: as written
        self.assertEqual(whole.sample_of(samples, "melody", 0, {}, 1)[0], "sm2")                 # the line's note in the second stretch
        self.assertEqual(whole.sample_of(samples, "melody", 0, {}, 0)[0], "sm")
        self.assertEqual(whole.sample_of(samples, "melody", 0, {})[0], "sm")
        self.assertEqual(whole.sample_of(samples, "melody", 1, {}, 1)[0], "sm")                  # a voice beside the line keeps its own
        self.assertEqual(whole.sample_of(samples, "bass", 0, {}, 0)[0], "sbass")

    def test_a_line_is_written_in_its_stretchs_register_and_a_layer_voice_changes_instrument(self):
        """Round 92: the writers take a register a bar (bounds_at, spans_at): a line whose token song changes instrument by
        stretch is written in each stretch's register, entering it by octaves, so the fold after writing has nothing to
        move; and a voice beside the line carries its own instrument by stretch (the layer entry's sixth sub-field),
        parsed into Plan.layer_stretches, registered by samples_for and played by sample_of."""
        from types import SimpleNamespace
        from unittest import mock
        from bitcomposer import instruments
        from bitcomposer.composer import compose_song
        from bitcomposer.translate import harness, packtables, tables
        song = compose_song(seed=5, pack="ffvi")
        ctx = harness.load_generated(song, "seed 5", "test", seconds=40.0)
        models = packtables.read(packtables.build(ctx.db, "test"))
        p = whole.plan(models, 3, "g", max_bars=16)
        self.assertIn(R.MELODY, p.band)
        p.plays[R.MELODY] = [True] * p.bars
        x = p.extras.setdefault(R.MELODY, {})
        x["stretch_spans"], x["stretch_bounds"], x["stretch_samples"] = [(0, 0, 4), (1, 4, p.bars)], {0: (72, 84), 1: (52, 64)}, {}
        p.bounds[R.MELODY] = (52, 84)
        written = whole.write(p, whole.song_of(p), models, 3)
        line = [n for n in written[R.MELODY].notes if n[3] == 0]
        early = [n for n in line if n[0] < 16 - 1e-6]
        late = [n for n in line if n[0] >= 16 - 1e-6]
        self.assertTrue(early and late, written[R.MELODY].log)
        inside = [n for n in early if 72 <= n[2] <= 84] + [n for n in late if 52 <= n[2] <= 64]
        self.assertGreaterEqual(len(inside), 0.9 * len(line), (sorted({n[2] for n in early}), sorted({n[2] for n in late}), p.log[-3:]))
        self.assertFalse(any(l.startswith("melody:") and "folded" in l for l in p.log), [l for l in p.log if "folded" in l])   # written in register: nothing to fold
        tok = "melody=main:56-72:0.9:2:0.7:1.5@sm2@1.00@55-60@dm-12x6>o@sm2~55-60x6>sm3~55-60::sm@68-72 bass=half:36-44:0.9:1:1.0:::sbass top=0.30 tempo=medium"
        t = tables.Table(("part",), "balance", votes=tables.SHARES).fit([tables.Unit(f"s{i}", "g", tok, {"part": rhythm.ARRANGEMENT}) for i in range(3)])
        q = whole.plan({"balance": t}, 1, "g")
        self.assertEqual(q.layer_stretches, {"melody": [[("sm2", (55, 60), 6), ("sm3", (55, 60), None)]]})
        self.assertEqual(q.layer_relations, {"melody": ["dm-12x6>o"]})
        made = []
        fake = lambda name: made.append(name) or SimpleNamespace(c5_speed=32000, data=b"\0\0" * 64, loop=False, sus_loop=False, name=name)   # noqa: E731
        pack = {"voices": {"harmony": ["pad"], "lead": ["pad"], "bass_medium": ["pad"], "arp": ["pad"]}}
        with mock.patch.object(instruments, "_make_sample", fake):
            samples = whole.samples_for(q, pack, {"sm", "sm2", "sm3", "sbass"}, "g", random.Random(1), {})
        self.assertEqual((samples["melody:1:stretch:0"][0], samples["melody:1:stretch:1"][0]), ("sm2", "sm3"))
        self.assertEqual(q.extras["melody"]["voice_stretch_spans"][1], [(0, 0, 6), (1, 6, q.bars)])
        self.assertEqual([whole.stretch_at(q, "melody", k, 1) for k in (0, 5, 6, q.bars + 2)], [0, 0, 1, 1])
        self.assertIsNone(whole.stretch_at(q, "melody", 0))                                        # the line has no stretches here
        self.assertEqual(whole.sample_of(samples, "melody", 1, {}, 1)[0], "sm3")                    # the voice's note in its second stretch
        self.assertEqual(whole.sample_of(samples, "melody", 1, {}, 0)[0], "sm2")
        self.assertEqual(whole.sample_of(samples, "melody", 1, {})[0], "sm2")                       # without a stretch: the voice's own token sample
        self.assertEqual(whole.sample_of(samples, "melody", 0, {}, 1)[0], "sm")                     # the line keeps its own
        self.assertTrue(any(l.startswith("melody's voice 2 by stretch") for l in q.log), q.log[-4:])

    def test_off_the_scale_and_clashes_are_counted_words_the_tune_holds(self):
        """Round 93: the off_scale word (a part's share of notes off the song's natural scale, by part, mode and beat) and the
        clashes word (the tune's share of onsets a semitone from a sounding part, by beat) are counted on the readings,
        drawn once a song for the tune on their own streams, and held by the melody writer in place of the STRONG_SCALE and
        CLASH bans: an off-scale move on a beat is barred without the word, takes the drawn share of the mass with it, and
        none while the tune is over the share; a clashing move the same under the clashes word."""
        import importlib
        from collections import Counter
        from bitcomposer.translate import tables
        tune_mod = importlib.import_module("bitcomposer.translate.writer.tune")
        upper_mod = importlib.import_module("bitcomposer.translate.writer.upper")
        s = self._song()                                                                      # C major: the scale C D E F G A B
        s.notes["melody"] = [(4.0 * i + x, 0.9, m, "m") for i in range(8) for x, m in ((0.0, 67.0), (1.0, 70.0), (2.0, 71.0), (3.0, 72.0))]   # Bb off the scale, a quarter
        s.notes["melody"] += [(4.0 * i + 0.5, 0.4, 66.0, "m") for i in range(8) for _ in (0,)] + [(4.0 * i + 2.5, 0.4, 69.0, "m") for i in range(8)]   # weak: F# off, A on
        s.voice_notes = {0: ("bass", s.notes["bass"]), 1: ("melody", s.notes["melody"]), 2: ("drums", s.notes["drums"])}
        units = rhythm.off_scale_units([s])
        by = {(u.values["part"], u.values["mode"], u.values["place"]): u.outcome for u in units}
        self.assertEqual(by[("melody", "major", "strong")], "0.25")                           # 8 of 32 strong-beat notes off the scale
        self.assertEqual(by[("melody", "major", "weak")], "0.50")                             # 8 of 16 weak ones
        self.assertEqual(by[("bass", "major", "strong")], "0.00")
        self.assertNotIn(("bass", "major", "weak"), by)                                       # under sixteen notes: no unit
        clashes = {(u.values["part"], u.values["place"]): u.outcome for u in rhythm.clash_units([s])}
        self.assertEqual(clashes, {("melody", "strong"): "0.50"})                                         # the bass's C sounds under the tune's G and B on beats 1 and 3: the B clashes
        # the plan: the words drawn once a song on their own streams, every other draw as it was
        units = lambda name, outcome, **vals: [tables.Unit(f"s{i}", "g", outcome, vals) for i in range(3)]   # noqa: E731
        off = tables.Table(("part", "mode", "place"), "off_scale", votes=tables.SHARES).fit(
            units("off_scale", "0.20", part="melody", mode="minor", place="strong") + units("off_scale", "0.25", part="melody", mode="minor", place="weak")
            + units("off_scale", "0.10", part="melody", mode="major", place="strong") + units("off_scale", "0.10", part="melody", mode="major", place="weak")
            + [tables.Unit(f"c{i}{mode}{pl}", "g", o, {"part": "counter", "mode": mode, "place": pl}) for i in range(3) for mode in ("major", "minor") for pl, o in (("strong", "0.15"), ("weak", "0.05"))])
        cl = tables.Table(("part", "place"), "clashes", votes=tables.SHARES).fit(units("clashes", "0.06", part="melody", place="strong") + units("clashes", "0.08", part="melody", place="weak")
                                                                                 + units("clashes", "0.04", part="counter", place="strong") + units("clashes", "0.00", part="counter", place="weak"))
        token = "melody=main:64-84:0.9:1:0.7:::slead counter=half:55-67:0.8:1:0.5:::sstr bass=half:36-44:0.9:1:1.0:::sbass top=0.30 tempo=medium"
        bal = {"balance": tables.Table(("part",), "balance", votes=tables.SHARES).fit(units("balance", token, part=rhythm.ARRANGEMENT))}
        p = whole.plan({**bal, "off_scale": off, "clashes": cl}, 7, "g")
        q = whole.plan(bal, 7, "g")
        x = p.extras["melody"]
        self.assertEqual(x["off_scale"], {"strong": 0.20 if p.mode == "minor" else 0.10, "weak": 0.25 if p.mode == "minor" else 0.10})
        self.assertEqual(x["clashes"], {"strong": 0.06, "weak": 0.08})
        self.assertEqual(p.extras["counter"]["off_scale"], {"strong": 0.15, "weak": 0.05})       # the counter-line's own draws
        self.assertEqual(p.extras["counter"]["clashes"], {"strong": 0.04, "weak": 0.0})
        self.assertIsNone(q.extras["melody"].get("off_scale"))
        self.assertEqual((p.chords, p.textures, p.habits, p.parts, x["chord_tones"]), (q.chords, q.textures, q.habits, q.parts, q.extras["melody"]["chord_tones"]))   # own streams
        # draw_move: from E in C major, in a register of an octave, every move the table smooths in is a landing; the off-scale
        # ones (C#, Eb, F#, G#, Bb) are barred on a beat without the word, and take the drawn share of the draws with it
        moves = tables.Table(("part",), "moves", votes=tables.SHARES).fit([tables.Unit(f"s{i}", "g", o, {"part": "melody"}) for i in range(3) for o in ("+1", "+2", "+3", "-1", "-2")])
        major = {0, 2, 4, 5, 7, 9, 11}
        landings = lambda strong, sounding, **kw: Counter((64 + tune_mod.draw_move(moves, "+1", "major", 64.0, random.Random(i), (60, 72), major, strong, None, sounding, None, **kw)) % 12 for i in range(300))   # noqa: E731
        off_of = lambda c: sum(n for pc, n in c.items() if pc not in major)   # noqa: E731
        self.assertEqual(off_of(landings(True, set())), 0)                                   # no word: off the scale barred on the beat (STRONG_SCALE)
        self.assertGreater(off_of(landings(False, set())), 0)                                # and free off it
        self.assertEqual(off_of(landings(True, set(), off_rate=0.3, off_over=True)), 0)      # over the share: barred
        under = off_of(landings(True, set(), off_rate=0.3))
        self.assertTrue(60 < under < 120, under)                                             # under it: the off-scale landings take the share (0.3 of 300)
        self.assertEqual(off_of(landings(True, set(), off_rate=0.0)), 0)                     # a share of none: never
        # held together with the chord-tone rate (C major's tones, half the mass), not thinned by it
        with_chord = Counter((64 + tune_mod.draw_move(moves, "+1", "major", 64.0, random.Random(i), (60, 72), major, True, (0, ""), set(), None, chord_rate=0.5, off_rate=0.3)) % 12 for i in range(300))
        self.assertTrue(60 < off_of(with_chord) < 120, off_of(with_chord))
        chord_hits = sum(n for pc, n in with_chord.items() if pc in (0, 4, 7))
        self.assertTrue(120 < chord_hits < 180, chord_hits)
        # a clashing move: the sounding part holds F (pc 5), so E (the repeated note) and F# sit a semitone from it
        clash_of = lambda c: sum(n for pc, n in c.items() if (pc - 5) % 12 in (1, 11))   # noqa: E731
        self.assertEqual(clash_of(landings(False, {5})), 0)                                  # no word: barred (CLASH)
        with_word = clash_of(landings(False, {5}, clash_rate=0.3))
        self.assertTrue(60 < with_word < 120, with_word)                                     # under the clashes share: drawn at the share
        self.assertEqual(clash_of(landings(False, {5}, clash_rate=0.3, clash_over=True)), 0) # over it: barred
        self.assertEqual(upper_mod.CLASH, (1, 11))

    def test_each_part_holds_its_clashes_against_the_parts_written_before_it(self):
        """Round 94: the clashes word counts each pitched part but the bass against the parts written before it (CLASH_ORDER:
        bass, harmony, accompaniment, arp, melody, counter), and the writers hold the drawn share: the counter writer draws an
        interval again while the line is over its share and the drawn note sits a semitone from a part under it; the upper
        writer gives such a tone to the nearest clear tone of the voicing."""
        from fractions import Fraction
        from bitcomposer.translate import writer, tables, vocab
        self.assertEqual(rhythm.clash_under("bass"), ())
        self.assertEqual(rhythm.clash_under("accompaniment"), ("bass", "harmony"))
        self.assertEqual(rhythm.clash_under("counter"), ("bass", "harmony", "accompaniment", "arp", "melody"))
        s = self._song()                                                                      # C major; the bass C on beats 1 and 3
        s.notes["melody"] = [(4.0 * i + x, 0.9, m, "m") for i in range(8) for x, m in ((0.0, 67.0), (1.0, 69.0), (2.0, 71.0), (3.0, 72.0))]   # G A B C a bar
        s.notes["accompaniment"] = [(4.0 * i + x, 1.0, 64.0, "a") for i in range(8) for x in (0.0, 1.0, 2.0, 3.0)]   # E held a beat at a time
        s.voice_notes = {0: ("bass", s.notes["bass"]), 1: ("melody", s.notes["melody"]), 2: ("drums", s.notes["drums"]), 3: ("accompaniment", s.notes["accompaniment"])}
        units = {(u.values["part"], u.values["place"]): u.outcome for u in rhythm.clash_units([s])}
        self.assertEqual(set(units), {("accompaniment", "strong"), ("melody", "strong")})      # no unit for the bass, written first
        self.assertEqual(units[("accompaniment", "strong")], "0.00")                           # E over the bass's C
        self.assertAlmostEqual(float(units[("melody", "strong")]), 0.25, delta=0.011)           # the B against the accompaniment's... no: against the bass's C on beat 3
        # the counter writer: a table that says "a third below the tune" (A under C), rarely "a fourth below" (G); the bass holds Bb
        bars = [(4.0 * k, 4.0 * k + 4.0) for k in range(4)]
        iv_t = tables.Table(("part", "kind", "line", "previous"), "voice_intervals", votes=tables.SHARES).fit(
            [tables.Unit(f"s{i}", "g", "-2", {"part": "counter", "kind": "other", "line": "scale", "previous": p}) for i in range(20) for p in (rhythm.START, "-2", "-3")]
            + [tables.Unit(f"t{i}", "g", "-3", {"part": "counter", "kind": "other", "line": "scale", "previous": p}) for i in range(2) for p in (rhythm.START, "-2", "-3")])
        mv_t = tables.Table(("part", "kind", "place"), "voice_moves", votes=tables.SHARES).fit(
            [tables.Unit(f"s{i}", "g", o, {"part": "counter", "kind": "other", "place": pl}) for i in range(20) for o, pl in (("0", "with"), ("-1", "with"), ("1", "with"), ("1", "alone"))])
        vals = tables.Table(("part", "value", "habit"), "values", votes=tables.SHARES).fit([tables.Unit(f"s{i}", "g", "held", {"part": "counter", "value": "1", "habit": "held"}) for i in range(3)])
        models = {"voice_intervals": iv_t, "voice_moves": mv_t, "values": vals}
        tune = [(4.0 * k + i, 4.0 * k + i + 0.9, 72.0, 0) for k in range(4) for i in range(4)]           # the tune repeats C on every beat
        tune_figs = ["0 1 2 3"] * 4
        masks = ["1 1 1 1"] * 4

        def counter_notes(rates):
            song = rhythm.Song("w", 4, 12, bars, [vocab.Span(0.0, 16.0, 0, "", 1.0)], notes={}, sid="w", game="g", tonic=0, mode="major")
            song.notes["bass"] = [(4.0 * k, 4.0, 70.0, "bass") for k in range(4)]                  # Bb held through every bar: a semitone from A
            notes, figures, log = writer.counter(song, tune, tune_figs, masks, (48, 96), models, random.Random(3), "other",
                                                 key=(0, "major"), articulation="held", register=(60, 84), clash_rates=rates)
            return [int(m) for a, b, m in notes], log
        free, log_free = counter_notes(None)
        self.assertGreaterEqual(free.count(69), 12)                                            # without the word: A under C, a semitone from the bass, nearly every time
        held, log_held = counter_notes({"strong": 0.0, "weak": 0.0})
        self.assertLessEqual(held.count(69), 1)                                                # with a share of none: the first may clash; from then on the fourth (G)
        self.assertGreaterEqual(held.count(67), 14)
        self.assertTrue(any("a semitone from a part under it: strong" in l and "the song's rate 0.00" in l for l in log_held), log_held)
        self.assertFalse(any("a semitone from a part under it" in l for l in log_free))
        # the upper writer: a voice beside the line an octave above its C, over a bass holding B; the share of none moves it to the
        # voicing's nearest clear tone (G) after the first onset
        iv_u = tables.Table(("part", "kind", "line", "previous"), "voice_intervals", votes=tables.SHARES).fit(
            [tables.Unit(f"s{i}", "g", "7", {"part": "accompaniment", "kind": "apart", "line": "scale", "previous": p}) for i in range(20) for p in (rhythm.START, "7")])
        mv_u = tables.Table(("part", "kind", "place"), "voice_moves", votes=tables.SHARES).fit(
            [tables.Unit(f"s{i}", "g", o, {"part": "accompaniment", "kind": "apart", "place": pl}) for i in range(20) for o, pl in (("0", "with"), ("-1", "with"), ("1", "alone"))])

        def upper_notes(rates):
            song = rhythm.Song("w", 4, 12, bars[:2], [vocab.Span(0.0, 8.0, 0, "", 1.0)], notes={}, sid="w", game="g", tonic=0, mode="major")
            song.notes["bass"] = [(4.0 * k, 4.0, 71.0, "bass") for k in range(2)]                  # B held: a semitone under C
            shared = {}
            for k in range(2):
                for pos in range(4):
                    shared[(k, Fraction(pos))] = ((0, ""), "R 3 5", ["R", "3", "5"])
                    shared[("line", (k, Fraction(pos)))] = 60
                    shared.setdefault(("taken", (k, Fraction(pos))), set()).add(60)
            notes, figures, _ = writer.upper(song, "accompaniment", [1], {1: (60, 96)}, {"voice_intervals": iv_u, "voice_moves": mv_u}, random.Random(1),
                                             "dense", "triad", 0.5, key=(0, "major"), plays=[True, True], figures=["0 2", "0 2"], shared=shared,
                                             tone_index=writer.ANY_TONE, kind="apart", clash_rates=rates)
            return [int(m) % 12 for a, b, m, v in notes]
        self.assertEqual(upper_notes(None), [0, 0, 0, 0])                                      # the octave above C, over the bass's B: a semitone, kept
        self.assertEqual(upper_notes({"strong": 0.0, "weak": 0.0}), [0, 7, 7, 7])              # over the share from the second onset: G, the nearest clear tone
        self.assertEqual(upper_notes({"strong": 1.0, "weak": 1.0}), [0, 0, 0, 0])              # a share of everything: never over
        # the plan draws the chord parts' shares too, on their own streams
        units = lambda name, outcome, **vals: [tables.Unit(f"s{i}", "g", outcome, vals) for i in range(3)]   # noqa: E731
        cl = tables.Table(("part", "place"), "clashes", votes=tables.SHARES).fit(units("clashes", "0.06", part="melody", place="strong") + units("clashes", "0.08", part="melody", place="weak")
                                                                                 + units("clashes", "0.02", part="accompaniment", place="strong") + units("clashes", "0.04", part="accompaniment", place="weak"))
        token = "melody=main:64-84:0.9:1:0.7:::slead accompaniment=half:55-67:0.8:1:0.5:::sstr bass=half:36-44:0.9:1:1.0:::sbass top=0.30 tempo=medium"
        bal = {"balance": tables.Table(("part",), "balance", votes=tables.SHARES).fit(units("balance", token, part=rhythm.ARRANGEMENT))}
        p = whole.plan({**bal, "clashes": cl}, 7, "g")
        self.assertEqual(p.extras["accompaniment"]["clashes"], {"strong": 0.02, "weak": 0.04})
        self.assertEqual(p.extras["melody"]["clashes"], {"strong": 0.06, "weak": 0.08})
        # a relation voice doubling a line note off the scale copies it exactly (a double at two octaves down of G# is G#, not
        # the G a scale-bound shift had given, a semitone under the tune); a third stays diatonic
        major = {0, 2, 4, 5, 7, 9, 11}
        self.assertEqual([m for a, b, m, v in whole.diatonic([(0.0, 1.0, 68.0, 0), (1.0, 2.0, 67.0, 0)], -24, major, 1)], [44.0, 43.0])
        self.assertEqual([m for a, b, m, v in whole.diatonic([(0.0, 1.0, 68.0, 0), (1.0, 2.0, 67.0, 0)], 12, major, 1)], [80.0, 79.0])
        self.assertEqual([m for a, b, m, v in whole.diatonic([(0.0, 1.0, 67.0, 0)], -3, major, 1)], [64.0])                      # a third below G: E

    def test_the_lines_own_note_lengths_ride_the_token_and_a_relation_voice_is_written_where_the_game_plays_its_sample(self):
        """Round 95: the balance token's sounded field is the LINE voice's share (the part's merged voices had put the gap to
        the other voice's note under a note's length) and carries the line's share by gap class, which the plan keeps over
        the pooled gap_sounds draws for the part's only and line voices; and a voice beside a line written by its relation
        word is folded by octaves into where the token song plays its sample, bar by bar, as a line is."""
        from types import SimpleNamespace
        from bitcomposer.translate import tables, vocab
        bars = [(4.0 * k, 4.0 * k + 4.0) for k in range(4)]
        line = [(4.0 * k + i / 2, 0.2, 64.0, "a") for k in range(4) for i in range(8)]      # the line (the busiest voice): staccato eighths, 0.4 of the gap
        second = [(4.0 * k + i / 2 + 0.25, 0.25, 72.0, "b") for k in range(4) for i in range(8)][:-1]   # a second voice between them, legato
        s = rhythm.Song("t", 4, 12, bars, [vocab.Span(0.0, 16.0, 0, "", 1.0)], notes={"accompaniment": sorted(line + second)}, sid="s", game="g", tonic=0, mode="major")
        s.voice_notes = {3: ("accompaniment", second), 4: ("accompaniment", line)}
        self.assertEqual(rhythm.gap_shares(line), {"<0.5": None, "0.5-1": 0.4, "1-2": None, "2-4": None, "4+": None})
        acc = next(t for t in rhythm.balance_units([s])[0].outcome.split() if t.startswith("accompaniment="))
        field = acc.split(":")[2]
        self.assertEqual(field, "0.4@-/0.4/-/-/-", acc)                                    # the line voice's 0.4, not the merged voices' 0.8; by gap class
        self.assertGreaterEqual(rhythm.sounded_share(s.notes["accompaniment"]), 0.8)       # what the merged voices had said
        # the plan: a gap_sounds table that says "hold everything"; the token's own classes stand, the others take the draw
        units = lambda name, outcome, **vals: [tables.Unit(f"s{i}", "g", outcome, vals) for i in range(3)]   # noqa: E731
        gs = tables.Table(("part", "voice", "speed", "gap"), "gap_sounds", votes=tables.SHARES).fit(
            [tables.Unit(f"s{i}{v}{g}", "g", "1.0", {"part": "accompaniment", "voice": v, "speed": "slow", "gap": g}) for i in range(3) for v in ("only", "line", "second") for _, g in rhythm.GAP_CLASSES])
        token = "melody=main:64-84:0.9:1:0.7:::slead accompaniment=half:60-72:0.4@-/0.4/-/0.2/-:1:0.6:::sstr bass=half:36-44:0.9:1:1.0:::sbass top=0.30 tempo=medium"
        bal = {"balance": tables.Table(("part",), "balance", votes=tables.SHARES).fit(units("balance", token, part=rhythm.ARRANGEMENT))}
        p = whole.plan({**bal, "gap_sounds": gs}, 7, "g")
        self.assertEqual(p.token_gap_shares["accompaniment"], {"<0.5": None, "0.5-1": 0.4, "1-2": None, "2-4": 0.2, "4+": None})
        self.assertEqual(p.gap_sounds["accompaniment"]["only"], {"<0.5": 1.0, "0.5-1": 0.4, "1-2": 1.0, "2-4": 0.2, "4+": 1.0})
        self.assertEqual(p.gap_sounds["accompaniment"]["line"]["0.5-1"], 0.4)
        self.assertEqual(p.gap_sounds["accompaniment"]["second"]["0.5-1"], 1.0)           # the second voices keep the pooled word
        self.assertEqual(p.sounds["accompaniment"], 0.4)
        self.assertTrue(any("accompaniment's note lengths from the balance's song" in l for l in p.log))
        # the relation voice: two octaves over a tune written high, folded into the voice's stretches' played ranges, a bar at a time
        fake = SimpleNamespace(layer_stretches={"accompaniment": [[("sa", (68, 80), 2), ("sb", (72, 88), None)]]}, bounds={}, layer_ranges={}, registers={"accompaniment": (60, 72)},
                               extras={"accompaniment": {"voice_stretch_spans": {1: [(0, 0, 2), (1, 2, 4)]}}}, log=[])
        at = whole.voice_bound_at(fake, "accompaniment", 1)
        self.assertEqual((at(0), at(3)), ((68, 80), (72, 88)))
        notes = [(4.0 * k + i, 4.0 * k + i + 0.5, m, 1) for k in range(4) for i, m in enumerate((104.0, 106.0, 108.0, 111.0))]   # the tune two octaves up, at 104-111
        folded = whole.fold_voice(fake, "accompaniment", 1, notes, 4)
        self.assertTrue(all(at(int(n[0] // 4))[0] <= n[2] <= at(int(n[0] // 4))[1] for n in folded), folded)
        self.assertEqual([n[2] for n in folded[:4]], [68.0, 70.0, 72.0, 75.0])             # bars 1-2 (68-80): three octaves down as a whole
        self.assertEqual([n[2] for n in folded[8:12]], [80.0, 82.0, 84.0, 87.0])           # bars 3-4 (72-88): two octaves down, the contour kept
        self.assertEqual([n[2] for n in whole.fold_voice(fake, "accompaniment", 1, [(0.0, 0.5, 76.0, 0)], 4)], [76.0])   # the line voice is not touched
        self.assertTrue(any("accompaniment's voice 2:" in l and "round 95" in l for l in fake.log), fake.log)

    def test_the_second_voices_levels_are_the_balance_tokens_too(self):
        """The balance token carries, for a part with two voices or more, each voice beyond the line's level over the line
        voice's in tenths (the layer_levels unit, capped at 1.5; the busiest voice first) as a sixth field; the plan plays a
        voice beside the line at the token's share for that voice where the token's song has the part layered, and at the
        layer_levels draw where the token lacks the field (a one-voice part, a token built before round 33); the draws stay
        on the stream, so every other draw is what it was (round 33: a second voice at its own 1.5 draw on a line whose
        level was the token's had stacked to 1.8 times the tune in Whole 03 and the cap of full in Whole 15 and 20)."""
        from bitcomposer.translate import tables
        s = self._song()
        line = [(4.0 * k + 0.5 * i, 0.4, 60.0, "a") for k in range(8) for i in range(8)]
        second = [(4.0 * k + i, 0.9, 52.0, "a") for k in range(8) for i in range(4)]
        third = [(4.0 * k, 0.9, 48.0, "a") for k in range(8)]
        s.notes["accompaniment"] = line + second + third
        s.voice_notes = {0: ("bass", s.notes["bass"]), 1: ("melody", s.notes["melody"]), 2: ("drums", s.notes["drums"]),
                         3: ("accompaniment", line), 4: ("accompaniment", second), 5: ("accompaniment", third)}
        s.voice_levels = {0: 0.28, 1: 0.22, 2: 0.14, 3: 0.20, 4: 0.26, 5: 0.50}
        s.levels = {"melody": 0.22, "bass": 0.28, "drums": 0.14, "accompaniment": 0.22}
        self.assertEqual(rhythm.voice_level_shares(s, "accompaniment"), ["1.3", "2.5"])           # the busiest first; uncapped since round 51 (the cap 4.0)
        self.assertIsNone(rhythm.voice_level_shares(s, "bass"))                                      # one voice
        self.assertEqual([u.outcome for u in rhythm.layer_level_units([s])], ["1.3"])               # the word's own unit is the first share
        tokens = [t for t in rhythm.balance_units([s])[0].outcome.split() if not t.startswith(("tempo=", "top=", "loud="))]
        self.assertTrue(tokens[0].startswith("accompaniment=") and ":3:0.8:1.3@" in tokens[0] and "/2.5@" in tokens[0], tokens)   # each voice beyond the line: level@sample@note share (round 65)
        self.assertTrue(tokens[1].startswith("bass=") and tokens[1].split(":")[5] == "", tokens)     # one voice: no layer field
        self.assertTrue(tokens[2].startswith("drums=:::Kc:0.5:::"), tokens)   # the kit's channel (round 87)
        s.voice_levels.pop(5)
        self.assertIsNone(rhythm.voice_level_shares(s, "accompaniment"))                             # a voice without a level: no field
        self.assertIn(":3:0.8:", rhythm.balance_units([s])[0].outcome.split()[0])
        units = lambda name, outcome, part, **more: [tables.Unit(f"s{i}", "g", outcome, {"part": part, **more}) for i in range(3)]   # noqa: E731
        layer = tables.Table(("part",), "layer_levels", votes=tables.SHARES).fit(
            units("layer_levels", "0.5", "accompaniment") + units("layer_levels", "0.5", "bass") + units("layer_levels", "1.5", "counter") + units("layer_levels", "1.5", "harmony"))
        token = "accompaniment=half:56-68:0.8:3:0.6:1.2/0.7 bass=half:36-44:0.9:2:1.0:0.7 counter=minor:60-72:0.8:1:0.4 harmony=minor:64-76:1.0:1:0.5 melody=main:64-84:0.9:1:0.7"
        models = {"balance": tables.Table(("part",), "balance", votes=tables.SHARES).fit(units("balance", token, rhythm.ARRANGEMENT)), "layer_levels": layer}
        for seed in range(1, 6):
            p = whole.plan(models, seed, "g")
            self.assertEqual(p.band, ["accompaniment", "bass", "counter", "harmony", "melody"])
            self.assertEqual(p.voices, {"accompaniment": 3, "bass": 2, "counter": 1, "harmony": 1, "melody": 1})
            self.assertEqual(p.voice_levels, {"accompaniment": [1.2, 0.7], "bass": [0.7]})          # the token's, by rank
            self.assertEqual({r: p.layer_levels[r] for r in ("accompaniment", "bass", "counter", "harmony")}, {"accompaniment": 1.2, "bass": 0.7, "counter": 1.5, "harmony": 1.5})
            self.assertEqual(p.layer_from, {"accompaniment": "balance", "bass": "balance", "counter": "layer_levels", "harmony": "layer_levels", "melody": "layer_levels"})
            self.assertIn("second voices from the balance: accompaniment=1.2/0.7 bass=0.7", p.log)   # no layered part drew: no "drawn from" clause
            self.assertEqual(p.levels, {"accompaniment": 0.6, "bass": 1.0, "counter": 0.4, "harmony": 0.5, "melody": 0.7})
        p.extras["accompaniment"]["layers"] = ["apart -12 like", "doubling +8"]; p.extras["accompaniment"]["layer"] = "apart -12 like"
        p.extras["bass"]["layer"] = "apart +0 like"
        self.assertAlmostEqual(whole.note_level(p, "accompaniment", 0), whole.TOP_LEVEL * 0.6)      # the line at the token's level
        self.assertAlmostEqual(whole.note_level(p, "accompaniment", 1), whole.TOP_LEVEL * 0.6 * 1.2)   # the second voice at the token's share
        self.assertAlmostEqual(whole.note_level(p, "accompaniment", 2), whole.TOP_LEVEL * 0.6 * 0.7)   # a doubling voice at the token's share too (round 70)
        self.assertAlmostEqual(whole.note_level(p, "accompaniment", 2, {"accompaniment": {1, 2}}), whole.TOP_LEVEL * 0.6 * 0.7)   # apart: its own share
        self.assertAlmostEqual(whole.note_level(p, "accompaniment", 3, {"accompaniment": {1, 2, 3}}), whole.TOP_LEVEL * 0.6 * 1.2)   # beyond the token's voices: layer_levels
        self.assertAlmostEqual(whole.note_level(p, "bass", 1), whole.TOP_LEVEL * 0.7)
        p.voices["counter"] = 2; p.extras["counter"]["layers"] = ["apart +12 like"]; p.extras["counter"]["layer"] = "apart +12 like"
        self.assertAlmostEqual(whole.note_level(p, "counter", 1), whole.TOP_LEVEL * 0.4 * 1.5)      # the token's song had one voice: the draw
        # a layered part whose token lacks the field (a pack built before this round): the draw, and said in the log
        old = token.replace("harmony=minor:64-76:1.0:1:0.5", "harmony=minor:64-76:1.0:2:0.5").replace("accompaniment=half:56-68:0.8:3:0.6:1.2/0.7", "accompaniment=half:56-68:0.8:2:0.6:1.2/0.7")
        q = whole.plan({**models, "balance": tables.Table(("part",), "balance", votes=tables.SHARES).fit(units("balance", old, rhythm.ARRANGEMENT))}, 1, "g")
        self.assertEqual((q.voices["harmony"], q.layer_levels["harmony"], q.layer_from["harmony"], q.voice_levels.get("harmony")), (2, 1.5, "layer_levels", None))
        self.assertIn("second voices from the balance: accompaniment=1.2/0.7 bass=0.7; drawn from layer_levels: harmony=1.5", q.log)
        # the same seed with the sixth fields and without: every other draw identical (the layer_levels draws stay in place)
        bare = whole.plan({**models, "balance": tables.Table(("part",), "balance", votes=tables.SHARES).fit(
            units("balance", token.replace(":0.6:1.2/0.7", ":0.6").replace(":1.0:0.7", ":1.0"), rhythm.ARRANGEMENT))}, 1, "g")
        p = whole.plan(models, 1, "g")
        self.assertEqual((bare.tonic, bare.mode, bare.parts, bare.band, bare.registers, bare.habits, bare.levels, bare.voices, bare.extras),
                         (p.tonic, p.mode, p.parts, p.band, p.registers, p.habits, p.levels, p.voices, p.extras))
        self.assertEqual({r: bare.layer_levels[r] for r in ("counter", "harmony", "melody")}, {r: p.layer_levels[r] for r in ("counter", "harmony", "melody")})
        self.assertEqual(({r: bare.layer_levels[r] for r in ("accompaniment", "bass")}, bare.voice_levels, set(bare.layer_from.values())), ({"accompaniment": 0.5, "bass": 0.5}, {}, {"layer_levels"}))
        self.assertNotIn("second voices from the balance", " ".join(bare.log))

    def test_the_counters_sample_is_the_games_pair_with_the_tunes(self):
        """counter_pairs counts the counter's sample under the tune's where the counter plays another (the pack's ids); at the
        rendering the draw under the tune's sample is taken where the pack holds it and it reaches the written register, the
        part's level (over all tunes) is still a count, and only where nothing counted fits does the pool rule remain."""
        s, _ = self._tune_and_counter()
        units = rhythm.counter_pair_units([s])
        self.assertEqual([(u.outcome, u.values) for u in units], [("sctr", {"part": "counter", "tune": "slead"})])
        s.notes["counter"] = [n[:3] + ("lead",) for n in s.notes["counter"]]; s.voice_notes[2] = ("counter", s.notes["counter"])
        self.assertEqual(rhythm.counter_pair_units([s]), [])                                        # on the tune's sample: counter_samples' "same", no pair
        pairs = tables.Table(("part", "tune"), "counter_pairs", votes=tables.SHARES).fit(
            [tables.Unit(f"s{i}", "g", "sb", {"part": "counter", "tune": "sa"}) for i in range(3)]
            + [tables.Unit(f"t{i}", "g", "sd", {"part": "counter", "tune": "sc"}) for i in range(3)])
        ranges = tables.Table(("part",), "ranges", votes=tables.SHARES).fit(
            [tables.Unit(f"s{i}", "g", "60-72", {"part": "sb"}) for i in range(3)] + [tables.Unit(f"t{i}", "g", "36-48", {"part": "sd"}) for i in range(3)])
        models, rng = {"counter_pairs": pairs}, random.Random(1)
        w = pairs.weights(("counter", "sa"), floor_k=whole.PLAN_FLOOR, min_songs=whole.PLAN_SONGS)   # the tune's context at 3 / (3 + 1) of the
        self.assertEqual({k: round(v, 3) for k, v in w.items()}, {"sb": 0.875, "sd": 0.125})           # mass, the part's level (sb and sd even) the rest
        self.assertEqual(pairs.weights(("counter", "sx"), floor_k=whole.PLAN_FLOOR, min_songs=whole.PLAN_SONGS), {"sb": 0.5, "sd": 0.5})   # unseen: the part's alone
        self.assertEqual(pairs.weights(("counter", "sx"), floor_k=None, min_songs=0), {"sb": 0.5, "sd": 0.5})
        self.assertEqual(pairs.weights(("harmony", "sx")), {"sb": 0.5, "sd": 0.5})                    # another part: the root's, as draw() backs off
        for _ in range(8):                                                                               # sd is out of reach two octaves down: sb
            self.assertEqual(whole.counter_pair_for(models, "sa", {"sa", "sb", "sd"}, ranges, (60, 72), rng), ("sb", "tune", ["sd out of reach of 60-72"]))
            self.assertEqual(whole.counter_pair_for(models, "sx", {"sa", "sb", "sd"}, ranges, (60, 72), rng)[:2], ("sb", "part"))   # a tune sample the game never had
        got = whole.counter_pair_for(models, "sa", {"sa", "sd"}, ranges, (60, 72), rng)              # the pack lacks sb: nothing counted fits,
        self.assertEqual(got, (None, None, ["sb not in the pack", "sd out of reach of 60-72"]))       # the pool rule stands
        self.assertEqual(whole.counter_pair_for(models, "sa", {"sa", "sb", "sd"}, ranges, (88, 100), rng)[:2], (None, None))   # out of reach
        one = tables.Table(("part", "tune"), "counter_pairs", votes=tables.SHARES).fit([tables.Unit(f"s{i}", "g", "sb", {"part": "counter", "tune": "sa"}) for i in range(3)])
        self.assertEqual(whole.counter_pair_for({"counter_pairs": one}, "sb", {"sa", "sb"}, ranges, (60, 72), rng), (None, None, ["sb the tune's own"]))   # not "other"
        self.assertEqual(whole.counter_pair_for({}, "sa", {"sa", "sb"}, ranges, (60, 72), rng), (None, None, None))                    # no table: the rule, unlogged

    def test_the_tunes_cells_handed_to_the_band(self):
        """Round 37: a tune's half-bar cell taken up by another part in a later bar is counted (which part, how many bars on;
        none), by the song's echo habit and the cell's place; the half-bar urn's kinds are counted (round 38); a cell re-rooted
        for another part keeps its intervals as scale steps inside the part's register."""
        bars = [(4.0 * k, 4.0 * k + 4.0) for k in range(4)]
        tune = [(0.0, 0.9, 60.0, "a"), (1.0, 0.9, 64.0, "a"), (2.0, 0.9, 67.0, "a"), (3.0, 0.9, 65.0, "a"),
                (4.0, 0.9, 60.0, "a"), (5.0, 0.9, 64.0, "a"), (6.0, 0.9, 62.0, "a"), (7.0, 0.9, 60.0, "a"),
                (8.0, 0.9, 62.0, "a"), (9.0, 0.9, 66.0, "a"), (10.0, 0.9, 64.0, "a"), (11.0, 0.9, 62.0, "a"),
                (12.0, 0.9, 60.0, "a"), (13.0, 0.9, 64.0, "a"), (14.0, 0.9, 67.0, "a"), (15.0, 0.9, 65.0, "a")]
        counter = [(8.0, 0.9, 55.0, "b"), (9.0, 0.9, 59.0, "b"), (10.0, 0.9, 50.0, "b"), (11.0, 0.9, 50.0, "b")]   # bar 2's first half = the tune's bar 0 cell
        s = rhythm.Song("t", 4, 12, bars, [], notes={"melody": tune, "counter": counter}, sid="s", game="g")
        units = rhythm.cell_handoff_units([s])
        self.assertEqual([u.outcome for u in units], ["counter 2", "none", "counter 1", "none", "none", "none", "none", "none"])   # bar 1 opens with the same shape as bar 0
        self.assertEqual({u.values["habit"] for u in units}, {"mixed"})   # 1 of 4 bar cells echoed (bar 3 = bar 0): over a third
        self.assertEqual([u.outcome for u in rhythm.half_recall_units([s])], ["new", "new", "earlier", "earlier", "earlier", "earlier", "earlier", "earlier"])   # two shapes (+4, -2) the whole tune through
        self.assertEqual(rhythm.handoff_class(9), "far")
        scale = {0, 2, 4, 5, 7, 9, 11}
        self.assertEqual(writer.cell_pitches([60, 64, 67], 0, 7, scale, (48, 60), 50.0), [55, 59, 50])   # a C cell on G in 48-60: G B D, the D folded in
        self.assertEqual(writer.cell_pitches([60, 64], 0, 0, scale, (60, 72), None), [60, 64])

    def test_the_tunes_memory_at_the_pair_and_where_its_echoes_point(self):
        """Round 40: a tune's two-bar groups are counted as what they are to the tune so far (pair_recall: same, earlier, new),
        the bars inside a new pair likewise (pair_bar_recall), and each echo by where it points (recall_sources: the section
        it is in, the theme phrase, another section); only the form's own parts are counted. The melody writer with the three
        tables draws a pair at a time and logs it; a pair drawn again brings both bars' cells back."""
        bars = [(4.0 * k, 4.0 * k + 4.0) for k in range(12)]
        def bar(k, ps): return [(4.0 * k + i, 0.9, float(p), "a") for i, p in enumerate(ps)]
        A, B, C = [60, 64, 67, 65], [60, 64, 62, 60], [62, 65, 69, 67]
        tune = bar(0, A) + bar(1, B) + bar(2, A) + bar(3, B) + bar(4, C) + bar(5, A) + bar(6, C) + bar(7, A) + bar(8, A) + bar(9, B) + bar(10, A) + bar(11, B)
        s = rhythm.Song("t", 4, 12, bars, [], notes={"melody": tune}, sid="s", game="g", numbers=list(range(12)),
                        parts=[(0, 4, None, "A"), (4, 4, None, "B"), (8, 4, 0, "A")])
        self.assertEqual([u.outcome for u in rhythm.pair_recall_units([s])], ["new", "same", "new", "same"])          # the repeat of A is not counted
        self.assertEqual([u.outcome for u in rhythm.pair_bar_recall_units([s])], ["new", "new", "new", "earlier"])   # the bars of the two new pairs
        self.assertEqual([u.outcome for u in rhythm.recall_source_units([s])], ["section", "section", "theme", "section", "section"])
        self.assertEqual({u.values["habit"] for u in rhythm.pair_recall_units([s])}, {"repeating"})
        self.assertEqual(rhythm.RECALL_SOURCES, ("section", "theme", "elsewhere"))

    def test_the_instrument_a_part_plays_the_range_it_was_ever_played_over_and_the_tune_doubled(self):
        """Rounds 42-44: a part's sample is counted by the part and its speed class (part_samples) and drawn before the pool
        rule; a sample's whole played range is counted (sample_ambitus) and a tune's bound is the widest the game ever took
        it, cut against the tune's own register; the tune's non-theme bars doubled by another part are counted
        (tune_doubling) as the theme's are."""
        from bitcomposer.translate import tables
        s = self._song()
        s.notes["melody"] = [(4.0 * i + x, 0.9, m, "abcdefghijklmnop") for i in range(4, 8) for x, m in ((0.0, 67.0), (1.0, 69.0), (2.0, 71.0), (3.0, 72.0))]
        s.notes["bass"] = [(4.0 * i + x, 0.5, 36.0 if i < 4 else m - 24, "k") for i in range(8) for x, m in ((0.0, 67.0), (2.0, 71.0))]
        units = rhythm.part_sample_units([s])
        self.assertEqual({(u.values["part"], u.outcome) for u in units}, {("melody", "sabcdefghij"), ("bass", "sk")})
        self.assertTrue(all(u.values.get("speed") in ("slow", "medium", "fast") for u in units))
        amb = {u.values["part"]: u.outcome for u in rhythm.sample_ambitus_units([s])}
        self.assertEqual(amb["sabcdefghij"], "68-72")                                                 # the tune's 67-72 to REGISTER_BIN
        self.assertEqual(amb["sk"], "36-48")                                                          # the bass's 36 and 43-48
        # the widest the game ever took a sample: the union of the word's outcomes, not one song's draw
        t = tables.Table(("part",), "sample_ambitus", votes=tables.SHARES).fit(
            [tables.Unit("a", "g", "56-76", {"part": "sx"}), tables.Unit("b", "g", "60-88", {"part": "sx"}), tables.Unit("c", "g", "48-72", {"part": "sx"})])
        self.assertEqual(whole.ambitus_of({"sample_ambitus": t}, "sx"), (48, 88))
        self.assertIsNone(whole.ambitus_of({"sample_ambitus": t}, "sy"))
        self.assertEqual(whole.bound_of((48, 88), (60, 80)), (60, 80))                              # the tune's own register where the sample reaches it
        # the tune doubled: the bass plays the tune's cell two octaves down in bars 4-7, none of them the theme bar... the
        # theme cell is bar 4's (every tune bar is the same cell here), so tune_doubling has no unit and theme_doubling has four
        self.assertEqual([u.outcome for u in rhythm.tune_doubling_units([s])], [])
        s.notes["melody"] = [(4.0 * i + x, 0.9, m, "a") for i in range(0, 4) for x, m in ((0.0, 67.0), (1.0, 69.0), (2.0, 71.0), (3.0, 72.0))] + \
                            [(4.0 * i + x, 0.9, m, "a") for i in range(4, 8) for x, m in ((0.0, 72.0), (1.0, 71.0), (2.0, 69.0), (3.0, 67.0))]
        s.notes["bass"] = [(4.0 * i + x, 0.9, m - 24, "k") for i in range(5, 8) for x, m in ((0.0, 72.0), (1.0, 71.0), (2.0, 69.0), (3.0, 67.0))]
        s.notes["counter"] = [(4.0 * i + x, 0.9, m, "c") for i in range(5, 7) for x, m in ((0.0, 72.0), (1.0, 71.0), (2.0, 69.0), (3.0, 67.0))]
        units = rhythm.tune_doubling_units([s])
        self.assertEqual([u.outcome for u in units], ["none", "bass:-24 counter:+0", "bass:-24 counter:+0", "bass:-24"])   # bars 4-7, not the theme's 0-3
        self.assertEqual({(u.values["part"], u.values["place"]) for u in units}, {("tune", "other")})

    def test_a_part_enters_and_leaves_inside_the_section_where_the_game_does(self):
        """Round 46: each part present in an own section is counted by where inside it it enters and leaves (part_entries:
        whole, enters:k, leaves:k, by the part, the section's place and its length class); the plan turns the part's bars
        off before its entrance and after its exit, a repeated section copying them; a draw no section this short can
        hold gives way to the part playing it whole. Round 45: the sample word draws among the samples the pack holds."""
        from bitcomposer.translate import tables
        bars = [(4.0 * k, 4.0 * k + 4.0) for k in range(8)]
        s = rhythm.Song("t", 4, 12, bars, [], notes={"melody": [(4.0 * i + x, 0.9, 60.0, "a") for i in range(2, 8) for x in (0.0, 2.0)],
                                                      "bass": [(4.0 * i + x, 0.9, 36.0, "b") for i in range(0, 7) for x in (0.0, 2.0)]},
                        sid="s", game="g", numbers=list(range(8)), parts=[(0, 4, None, "A"), (4, 4, None, "B")])
        units = rhythm.part_entry_units([s])
        self.assertEqual([(u.values["part"], u.values["form"], u.values["length"], u.outcome) for u in units],
                         [("melody", "first", "short", "enters:2"), ("bass", "first", "short", "whole"), ("melody", "last", "short", "whole"), ("bass", "last", "short", "leaves:1")])
        self.assertEqual({u.values["habit"] for u in units}, {rhythm.NO_TIER})                     # no drums: no tier read
        self.assertEqual((rhythm.entry_of("enters:3 leaves:1"), rhythm.entry_of("whole"), rhythm.section_length(4), rhythm.section_length(9)), ((3, 1), (0, 0), "short", "long"))
        units = lambda outcome, **v: [tables.Unit(f"s{i}", "g", outcome, v) for i in range(3)]   # noqa: E731
        entries = tables.Table(("part", "habit", "form", "length"), "part_entries", votes=tables.SHARES).fit(
            units("enters:6", part="counter", habit="-", form="first", length="medium") + units("whole", part="melody", habit="-", form="first", length="medium")
            + units("leaves:1", part="bass", habit="-", form="last", length="medium") + units("enters:6", part="counter", habit="-", form="last", length="short"))
        textures = tables.Table(("part", "habit", "form", "previous"), "part_textures", votes=tables.SHARES).fit(units("all", part=rhythm.ARRANGEMENT, habit="-", form="first", previous=rhythm.START))
        log = []
        parts = [(0, 8, None, "A"), (8, 4, None, "B"), (12, 8, 0, "A")]
        tex, plays = whole.plan_texture({"part_textures": textures, "part_entries": entries}, parts, ["bass", "counter", "melody"], random.Random(1), log)
        self.assertEqual(plays["counter"][:8], [False] * 6 + [True] * 2)                           # enters six bars into A
        self.assertEqual(plays["melody"][:8], [True] * 8)
        self.assertEqual(plays["bass"][8:12], [True, True, True, False])                            # leaves a bar before B's end
        self.assertEqual(plays["counter"][8:12], [True] * 4)                                        # "enters:6" cannot fit four bars: whole
        self.assertEqual(plays["counter"][12:20], plays["counter"][:8])                             # the repeat copies the entrance
        self.assertEqual(plays["bass"][:8], [True] * 7 + [False])                                  # the bass's word backs off to "leaves:1" in A too
        line = next(line for line in log if line.startswith("entrances (part_entries): "))
        self.assertIn("counter enters 6 in A", line); self.assertIn("bass leaves 1 before the end of B", line)
        # round 59: the drums' entrance is drawn under the kit's tier, after the kit's habit, from the tier's own entrances
        d = rhythm.Song("t", 4, 12, bars, [], notes={"drums": [(4.0 * i, 0.5, float("nan"), "k") for i in range(0, 4)] + [(4.0 * i, 0.5, float("nan"), "k") for i in range(4, 8) for _ in range(6)],
                                                      "bass": [(4.0 * i, 0.9, 36.0, "b") for i in range(8)]},
                        sid="d", game="g", numbers=list(range(8)), parts=[(0, 4, None, "A"), (4, 4, None, "B")], pieces={"k": "kick"})
        du = [u for u in rhythm.part_entry_units([d]) if u.values["part"] == "drums"]
        self.assertTrue(du and all(u.values["habit"] in ("sparse", "medium", "dense") for u in du), du)
        kit = tables.Table(("part", "habit", "form", "length"), "part_entries", votes=tables.SHARES).fit(
            units("whole", part="drums", habit="dense", form="first", length="long") + units("leaves:4", part="drums", habit="sparse", form="first", length="long"))
        for tier, tail in (("dense", [True] * 8), ("sparse", [True] * 4 + [False] * 4)):
            tex = ["bass drums"] * 8 + ["bass drums"] * 4 + ["bass drums"] * 8
            log2 = []
            tex, plays2 = whole.drum_entrances({"part_entries": kit}, parts, tex, ["bass", "drums"], tier, random.Random(3), log2)
            self.assertEqual(plays2["drums"][:8], tail, tier)
            self.assertEqual(plays2["drums"][12:20], plays2["drums"][:8])                            # the repeat copies the drums' entrance
            self.assertEqual(plays2["bass"], [True] * 20)
        # the texture word reads the kit's tier too: a dense kit's sections never leave the drums out, a sparse kit's intro does
        tt = tables.Table(("part", "habit", "form", "previous"), "part_textures", votes=tables.SHARES).fit(
            units("all", part=rhythm.ARRANGEMENT, habit="dense", form="first", previous=rhythm.START) + units("no drums", part=rhythm.ARRANGEMENT, habit="sparse", form="first", previous=rhythm.START))
        tu = rhythm.part_texture_units([d])
        self.assertTrue(tu and all(u.values["habit"] in ("sparse", "medium", "dense") for u in tu), tu)
        for tier, first in (("dense", "bass drums"), ("sparse", "bass")):
            tex, _ = whole.plan_texture({"part_textures": tt}, [(0, 8, None, "A")], ["bass", "drums"], random.Random(1), [], tier=tier)
            self.assertEqual(tex[0], first, tier)
        # the sample word over the pack's samples: a sample the pack lacks gives its share to the others
        samples = tables.Table(("part", "speed"), "part_samples", votes=tables.SHARES).fit(
            units("sx", part="melody", speed="slow") * 3 + units("sy", part="melody", speed="slow") + units("sz", part="melody", speed="slow"))
        drawn = {whole.part_sample_for({"part_samples": samples}, "melody", 2.0, {"sy", "sz"}, random.Random(k), []) for k in range(40)}
        self.assertEqual(drawn, {"sy", "sz"})
        self.assertIsNone(whole.part_sample_for({"part_samples": samples}, "melody", 2.0, {"sq"}, random.Random(1), log))

    def test_a_parts_level_moves_by_section_as_the_games_does(self):
        """Round 48: a part's median note level in each own section over its level in the whole song is counted in tenths
        (section_levels, by the part and the section's place); the plan draws a multiplier a part an own section it plays
        in, a repeated section copying it, and a note's level carries its bar's multiplier."""
        from bitcomposer.translate import tables
        bars = [(4.0 * k, 4.0 * k + 4.0) for k in range(8)]
        s = rhythm.Song("t", 4, 12, bars, [], notes={"bass": [(4.0 * i + x, 0.9, 36.0, "b") for i in range(8) for x in (0.0, 1.0, 2.0, 3.0)]},
                        sid="s", game="g", numbers=list(range(8)), parts=[(0, 4, None, "A"), (4, 4, None, "B")])
        s.note_levels = {"bass": [(4.0 * i + x, 0.1 if i < 4 else 0.2) for i in range(8) for x in (0.0, 1.0, 2.0, 3.0)]}
        units = rhythm.section_level_units([s])
        self.assertEqual([(u.values["part"], u.values["form"], u.outcome) for u in units], [("bass", "first", "0.7"), ("bass", "last", "1.3")])   # medians over 0.15
        units_ = lambda outcome, **v: [tables.Unit(f"s{i}", "g", outcome, v) for i in range(3)]   # noqa: E731
        t = tables.Table(("part", "form"), "section_levels", votes=tables.SHARES).fit(
            units_("0.5", part="bass", form="first") + units_("1.0", part="bass", form="last") + units_("1.5", part="melody", form="last") + units_("1.0", part="melody", form="first"))
        parts = [(0, 4, None, "A"), (4, 4, None, "B"), (8, 4, 0, "A")]
        plays = {"bass": [True] * 12, "melody": [False] * 4 + [True] * 8}
        log = []
        levels = whole.plan_section_levels({"section_levels": t}, parts, ["bass", "melody", "drums"], plays, random.Random(1), log)
        self.assertEqual(levels["bass"], [0.5] * 4 + [1.0] * 4 + [0.5] * 4)                         # the repeat of A copies A's
        self.assertEqual(levels["melody"], [1.0] * 4 + [1.5] * 4 + [1.0] * 4)                       # no draw for a section it rests in
        self.assertNotIn("drums", levels)
        self.assertIn("levels by section (section_levels): bass 0.5 in A; melody 1.5 in B", log)
        p = whole.plan({}, 1, "g")
        p.levels = {"bass": 0.8}; p.section_levels = {"bass": [0.5] * 4 + [1.0] * 4}
        self.assertAlmostEqual(whole.note_level(p, "bass", 0, {}, 0), whole.TOP_LEVEL * 0.8 * 0.5)
        self.assertAlmostEqual(whole.note_level(p, "bass", 0, {}, 5), whole.TOP_LEVEL * 0.8)
        self.assertAlmostEqual(whole.note_level(p, "bass", 0, {}), whole.TOP_LEVEL * 0.8)            # no bar: the part's level

    def test_the_songs_loudest_part_plays_at_the_games_level(self):
        """Round 52: a song's loudest part's level of full is counted (top_levels, to 0.05) and drawn once a song on its own
        stream; the band's shares are shares of it (note_level), TOP_LEVEL standing without the word."""
        from bitcomposer.translate import tables
        s = self._song(); s.levels = {"melody": 0.22, "bass": 0.31, "drums": 0.14}
        self.assertEqual([u.outcome for u in rhythm.top_level_units([s])], ["0.30"])
        t = tables.Table(("part",), "top_levels", votes=tables.SHARES).fit([tables.Unit(f"s{i}", "g", "0.30", {"part": rhythm.ARRANGEMENT}) for i in range(3)])
        p = whole.plan({"top_levels": t}, 1, "g")
        self.assertAlmostEqual(p.top_level, min(1.0, 0.30 * whole.TOP_SCALE))                    # the readings' scale bridged to the module's
        p.levels = {"bass": 1.0, "melody": 0.6}
        self.assertAlmostEqual(whole.note_level(p, "bass", 0, {}), p.top_level)
        self.assertAlmostEqual(whole.note_level(p, "melody", 0, {}), p.top_level * 0.6)
        self.assertAlmostEqual(whole.plan({}, 1, "g").top_level, whole.TOP_LEVEL)

    def test_a_samples_register_is_counted_by_the_part_playing_it_and_a_narrow_band_falls_back(self):
        """Round 55: the ranges word is counted by the sample and by the sample with the part playing it; round 53: a chord
        part whose drawn home band is narrower than MIN_SPAN is bound by the sample's whole played range instead."""
        from bitcomposer.translate import tables
        s = self._song()
        s.notes["accompaniment"] = [(4.0 * i + x, 0.9, 84.0 + (x * 2), "k") for i in range(8) for x in (0.0, 1.0, 2.0, 3.0)]   # the bass's sample, two octaves up
        units = rhythm.sample_range_units([s])
        by = {(u.values["part"], u.values.get("role")): u.outcome for u in units}
        self.assertIn(("sk", None), by); self.assertEqual(by[("sk", "bass")], "36-36"); self.assertEqual(by[("sk", "accompaniment")], "84-88")
        self.assertEqual(whole.range_context("sk", "bass"), ("sk", "bass")); self.assertEqual(whole.range_context("sk", None), ("sk",))
        t = tables.Table(("part", "role"), "ranges", votes=tables.SHARES).fit(units * 3)
        self.assertEqual(t.draw(("sk", "accompaniment"), random.Random(1), floored=False, floor_k=1), "84-88")
        self.assertEqual(t.draw(("sk", "bass"), random.Random(1), floored=False, floor_k=1), "36-36")
        amb = tables.Table(("part",), "sample_ambitus", votes=tables.SHARES).fit([tables.Unit(f"s{i}", "g", "36-88", {"part": "sk"}) for i in range(3)])
        self.assertEqual(whole.ambitus_of({"sample_ambitus": amb}, "sk"), (36, 88))
        self.assertLess(36 - 36, whole.MIN_SPAN)                                                    # the bass's one-pitch band: narrower than a voice's room

    def test_a_level_is_counted_and_played_as_loudness(self):
        """Round 56: a reading's level is multiplied by its sample's own loudness over the reference (loudness_factor, the
        pack's loop-body RMS), and a written note plays at its level over its sample's loudness (sample_rms), so the level
        words mean what the ear hears whichever sample a part draws."""
        import array
        from types import SimpleNamespace
        rhythm.set_loudness({"sloudxxxxxx": rhythm.LOUDNESS_REF * 2, "squietxxxxx": rhythm.LOUDNESS_REF / 2})   # "s" + the key's first ten
        try:
            self.assertAlmostEqual(rhythm.loudness_factor("loud" + "x" * 12), 2.0)
            self.assertAlmostEqual(rhythm.loudness_factor("quiet" + "x" * 11), 0.5)
            self.assertEqual(rhythm.loudness_factor("unknown" + "x" * 9), 1.0)
            self.assertEqual(rhythm.loudness_factor(None), 1.0)
        finally:
            rhythm.set_loudness({})
        flat = array.array("h", [8192] * 100 + [0] * 100)                                          # a quarter of full for half its length
        smp = SimpleNamespace(data=flat, loop=True, loop_start=0, loop_end=100)
        self.assertAlmostEqual(whole.sample_rms(smp), 0.25, places=3)                             # the loop body alone
        self.assertAlmostEqual(whole.sample_rms(SimpleNamespace(data=flat.tobytes(), loop=False, loop_start=0, loop_end=0)), 0.25 / 2 ** 0.5, places=3)
        # the strike over the recording's first 150 ms (round 70): by the WAV's rate, not the C5Speed a kit piece doubles
        # (KIT_NOTE 48), and over the WAV's frames, not the release tail the instrument builder writes after a loop
        hit = array.array("h", [8192] * 4800 + [0] * 4800)                                        # 300 ms at 32 kHz: loud, then silent
        kit = SimpleNamespace(data=hit, loop=False, loop_start=0, loop_end=0, c5_speed=64000, source_rate=32000)
        self.assertAlmostEqual(whole.sample_strike_and_body(kit)[0], 0.25, places=3)             # 150 ms of real time: the loud half
        self.assertAlmostEqual(whole.sample_strike_and_body(SimpleNamespace(data=hit, loop=False, loop_start=0, loop_end=0, c5_speed=64000))[0],
                               0.25 / 2 ** 0.5, places=3)                                         # without the rate: 150 ms at the C5Speed, 300 ms read
        tail = array.array("h", [8192] * 32 + [0] * 4000)                                         # a 32-frame loop with a release tail after it
        pad = SimpleNamespace(data=tail, loop=True, loop_start=0, loop_end=32, c5_speed=16000, source_rate=32000, source_frames=32)
        self.assertAlmostEqual(whole.sample_strike_and_body(pad)[0], 0.25, places=3)             # the recording's 32 frames, as the readings read them

    def test_the_kits_pieces_are_the_games(self):
        """Round 58: the pieces a song's drums strike are counted as letters by the kit's habit tier (kit_pieces); the plan
        draws them once a song on its own stream, and the kit figure's hits on other pieces are dropped (no per-group caps)."""
        from bitcomposer.translate import tables
        s = self._song()                                    # kick and crash in the kit
        units = rhythm.kit_piece_units([s])
        self.assertEqual([(u.outcome, u.values["part"]) for u in units], [("Kc", "drums")])
        self.assertIn(units[0].values["habit"], ("sparse", "medium", "dense"))
        t = tables.Table(("part", "habit"), "kit_pieces", votes=tables.SHARES).fit([tables.Unit(f"s{i}", "g", "KSh", {"part": "drums", "habit": h}) for i in range(3) for h in ("sparse", "medium", "dense")])
        p = whole.plan({"kit_pieces": t}, 1, "g")
        if "drums" in p.band:
            self.assertEqual(p.extras["drums"].get("pieces"), "KSh")
            self.assertTrue(any(line.startswith("kit pieces (kit_pieces): KSh") for line in p.log))

    def test_the_token_songs_instruments_come_with_its_levels(self):
        """Round 60: each part's own sample rides the balance token (eighth field, the pack's id); the plan keeps them
        (token_samples) for samples_for to take where the pack holds the sample."""
        from bitcomposer.translate import tables
        s = self._song(); s.levels = {r: 0.3 for r in s.notes}
        toks = rhythm.balance_units([s])[0].outcome.split()
        self.assertEqual(rhythm.part_sample_id(s, "bass"), "k"); self.assertEqual(rhythm.part_sample_id(s, "nothing"), "")
        self.assertEqual(rhythm.part_sample_id(rhythm.Song("t", 4, 12, [(0.0, 4.0)], [], notes={"melody": [(0.0, 1.0, 60.0, "0123456789abcdef")]}), "melody"), "s0123456789")
        token = "bass=half:36-44:0.9:1:1.0:::sbass123456@32-52 melody=main:64-84:0.9:1:0.7:::slead123456 tempo=medium"
        t = tables.Table(("part",), "balance", votes=tables.SHARES).fit([tables.Unit(f"s{i}", "g", token, {"part": rhythm.ARRANGEMENT}) for i in range(3)])
        p = whole.plan({"balance": t}, 1, "g")
        self.assertEqual(p.token_samples, {"bass": "sbass123456", "melody": "slead123456"})
        self.assertEqual(p.sample_ranges, {"bass": (32, 52)})                                     # round 86: where the song plays it

    def test_a_voice_on_the_tokens_sample_is_bound_where_its_song_played_it(self):
        """Round 86: the ranges word, drawn by sample and part over every song sharing the sample, had bound a bass to another
        song's range (11 of 27 written basses narrower than planned by 12 semitones at the median, one an octave up); with
        the token's own range for its own sample the voice is written in its planned register, the pooled draw kept on the
        stream and left unused. Without the field the old binding stands."""
        from bitcomposer.translate import tables
        from bitcomposer import instruments
        from unittest import mock
        from types import SimpleNamespace
        ranges = tables.Table(("part", "role"), "ranges").fit([tables.Unit(f"s{i}", "g", "48-60", {"part": "sbass123456", "role": "bass"}) for i in range(3)])
        fake = lambda name: SimpleNamespace(c5_speed=32000, data=b"\0\0" * 64, loop=False, sus_loop=False, name=name)   # noqa: E731
        pack = {"voices": {"harmony": ["pad"], "lead": ["pad"], "bass_medium": ["pad"], "bass_heavy": ["pad"], "bass_light": ["pad"], "arp": ["pad"]}}
        bounds = {}
        for field in ("sbass123456@32-52", "sbass123456"):
            token = f"bass=half:36-44:0.9:1:1.0:::{field} melody=main:64-84:0.9:1:0.7:::slead123456 tempo=medium"
            t = tables.Table(("part",), "balance", votes=tables.SHARES).fit([tables.Unit(f"s{i}", "g", token, {"part": rhythm.ARRANGEMENT}) for i in range(3)])
            p = whole.plan({"balance": t, "ranges": ranges}, 1, "g")
            if "bass" not in p.band:
                self.skipTest("the bass left out of this seed's textures")
            with mock.patch.object(instruments, "_make_sample", fake):
                whole.samples_for(p, pack, {"sbass123456", "slead123456"}, "g", random.Random(1), {"ranges": ranges})
            bounds[field] = p.bounds["bass"]
        self.assertEqual(bounds["sbass123456@32-52"], (36, 44))                                     # the planned register, whole
        self.assertEqual(bounds["sbass123456"], (48, 60))                                          # the other song's range, as before

    def test_a_kit_voice_given_to_a_pitched_part_plays_by_its_tonal_reading(self):
        """Round 119: the token song's own sample for a part may be a kit voice in the pack (Final Fantasy VI's rhythm guitar,
        Battle Theme's riff line); samples_for takes the pack's tonal reading of it for a pitched voice, the kit voice for a kit
        piece, and says so where the pack has no reading."""
        from bitcomposer.translate import tables
        from bitcomposer import instruments, samples as smp
        from unittest import mock
        from types import SimpleNamespace
        fake = lambda name: SimpleNamespace(c5_speed=32000, data=b"\0\0" * 64, loop=False, sus_loop=False, name=name)   # noqa: E731
        pack = {"voices": {"harmony": ["pad"], "lead": ["pad"], "bass_medium": ["pad"], "bass_heavy": ["pad"], "bass_light": ["pad"], "arp": ["pad"]}}
        token = "bass=half:36-44:0.9:1:1.0:::sgtr1234567@32-52 melody=main:64-84:0.9:1:0.7:::slead123456 tempo=medium"
        t = tables.Table(("part",), "balance", votes=tables.SHARES).fit([tables.Unit(f"s{i}", "g", token, {"part": rhythm.ARRANGEMENT}) for i in range(3)])
        smp.PERCUSSION_PRESETS.add("g_sgtr1234567")
        self.addCleanup(smp.PERCUSSION_PRESETS.discard, "g_sgtr1234567")
        self.addCleanup(smp.TONAL_VIEWS.pop, "g_sgtr1234567", None)
        for view in ("g_sgtr1234567_tonal", None):
            if view:
                smp.TONAL_VIEWS["g_sgtr1234567"] = view
            else:
                smp.TONAL_VIEWS.pop("g_sgtr1234567", None)
            p = whole.plan({"balance": t}, 1, "g")
            if "bass" not in p.band:
                self.skipTest("the bass left out of this seed's textures")
            with mock.patch.object(instruments, "_make_sample", fake):
                out = whole.samples_for(p, pack, {"sgtr1234567", "slead123456"}, "g", random.Random(1), {})
            name, sample = out["bass"]
            self.assertEqual(name, "sgtr1234567")                                                    # the pack's id, as the plan and the tables name it
            if view:
                self.assertEqual(sample.name, "g_sgtr1234567_tonal")                                 # the recording as a pitched instrument
                self.assertTrue(sample.tonal_view)
                self.assertTrue(any("played as pitched instruments by their tonal readings" in l and "sgtr1234567" in l for l in p.log), p.log)
            else:
                self.assertEqual(sample.name, "g_sgtr1234567")                                       # no reading: the kit voice, and the log says so
                self.assertFalse(getattr(sample, "tonal_view", False))
                self.assertTrue(any("no tonal reading" in l and "sgtr1234567" in l for l in p.log), p.log)
            self.assertEqual(out["melody"][1].name, "g_slead123456")                                 # a tonal voice is itself

    def test_the_kit_takes_its_songs_channels(self):
        """Round 87: the kit gets as many voices as its token song gave it channels, so a one-channel kit no longer costs the
        band a pitched voice, and each piece plays on the channel the game put it on; the fixed split stands without the
        field."""
        from bitcomposer.translate import tables
        band = ["accompaniment", "bass", "counter", "drums", "melody"]
        counts = {"accompaniment": 3, "bass": 1, "counter": 2, "melody": 1}
        self.assertEqual(whole.allot(band, counts, 1), {"drums": 1, "accompaniment": 3, "bass": 1, "counter": 2, "melody": 1})   # eight, untrimmed
        self.assertEqual(whole.allot(band, counts, 2)["accompaniment"], 2)                           # the old two: the accompaniment trimmed
        self.assertEqual(whole.allot(band, counts)["drums"], 2)
        self.assertEqual([whole.drum_voice_of(["KS", "h"], x) for x in "KSh"], [0, 0, 1])
        self.assertEqual([whole.drum_voice_of(None, x) for x in "KSthco"], [0, 0, 0, 1, 1, 1])      # no channels: the fixed split
        self.assertEqual(whole.drum_voice_of(["S"], "K", 1), 0)                                      # a letter on no channel, one voice: the first
        self.assertEqual(whole.drum_voice_of(["h", "K", "S"], "S", 3), 2)
        token = ("accompaniment=half:56-68:0.8:3:0.6:1.2@sacc1234567@0.50/1.1@sacc7654321@0.40::sacc0000001:dense+varied "
                 "bass=half:36-44:0.9:1:1.0 counter=minor:60-80:0.9:2:0.5:1.0@scnt0000001@0.5 "
                 "drums=:::S:0.2:::S=s1279e119a1@0.70@@@m:dense+varied melody=main:64-84:0.9:1:0.7 tempo=medium")
        t = tables.Table(("part",), "balance", votes=tables.SHARES).fit([tables.Unit(f"s{i}", "g", token, {"part": rhythm.ARRANGEMENT}) for i in range(3)])
        p = whole.plan({"balance": t}, 1, "g")
        if "drums" not in p.band or "accompaniment" not in p.band:
            self.skipTest("a part left out of this seed's textures")
        self.assertEqual(p.extras["drums"]["channels"], ["S"])
        self.assertEqual((p.voices["drums"], p.voices["accompaniment"]), (1, 3))                    # the eight: 3 + 1 + 2 + 1 + 1
        self.assertTrue(any(line.startswith("kit channels from the balance: 1 (S)") for line in p.log), p.log)

    def test_a_tuned_slots_rate_stays_inside_the_games_rates(self):
        """Round 88: a tuned slot's rate, moved with the written key, is held inside the rates the game struck the sample at
        as that piece (the kit_rates word, kit_rate_wall); without the word the move stands as round 79 made it."""
        import importlib
        from types import SimpleNamespace
        from bitcomposer.translate import tables
        render_mod = importlib.import_module("bitcomposer.translate.whole.render")
        token = ("bass=half:36-44:0.9:1:1.0 drums=:::S|h|K:0.5:::K=kick_sample@1.54@r60@0.94@m,S=snare_sample@0.61@r56t@0.46@d@e,h=hat_sample@0.49@r60@0.21@m:dense+varied "
                 "melody=main:64-84:0.9:1:0.7 key=7:major top=0.30 tempo=fast")
        t = tables.Table(("part",), "balance", votes=tables.SHARES).fit([tables.Unit(f"s{i}", "g", token, {"part": rhythm.ARRANGEMENT}) for i in range(3)])
        p = whole.plan({"balance": t}, 1, "g")
        if "drums" not in p.band:
            self.skipTest("the drums left out of this seed's textures")
        rates = tables.Table(("part", "piece"), "kit_rates").fit([tables.Unit(f"s{i}", "g", str(r), {"part": "snare_sample", "piece": "S"}) for i, r in enumerate((56, 62, 63, 63))])
        self.assertEqual(whole.kit_rate_wall({"kit_rates": rates}, "snare_sample", "S"), (56, 63))   # FFVI's snare: -4 to +3
        self.assertIsNone(whole.kit_rate_wall({"kit_rates": rates}, "snare_sample", "K"))             # never struck as a kick: no wall
        self.assertIsNone(whole.kit_rate_wall({}, "snare_sample", "S"))
        p.tonic, p.mode = 1, "minor"                                                                  # C# minor, a tritone from the token's G
        bell = SimpleNamespace(c5_speed=32000, source_rate=32000)
        self.assertEqual(render_mod.kit_note_of(p, "snare", "snare_sample", bell), 48.0 - 10)          # round 79 alone: -4 moved by -6
        p.extras["drums"]["kit_rate_walls"] = {"S": (56, 63)}
        self.assertEqual(render_mod.kit_note_of(p, "snare", "snare_sample", bell), 48.0 - 4)           # held at the game's lowest, Fanfare's own
        p.tonic = 9                                                                                  # A minor: -4 moved by +2 = -2, inside
        self.assertEqual(render_mod.kit_note_of(p, "snare", "snare_sample", bell), 48.0 - 2)
        self.assertEqual(render_mod.kit_note_of(p, "kick", "kick_sample", bell), 48.0)                 # an untuned slot: as the game struck it
        s = rhythm.Song("t", 4, 4, [(0.0, 4.0)], [], pieces={"snare0123456789": "snare"})
        s.kit_rates = {"snare0123456789": 56}
        units = rhythm.kit_rate_units([s])
        self.assertEqual((units[0].outcome, units[0].values), ("56", {"part": "ssnare01234", "piece": "S"}))

    def test_the_token_songs_kit_rides_the_drums_token(self):
        """Round 63: the song's kit (a piece letter and the pack id of the sample it strikes it with most) is the drums
        token's eighth field; the plan takes its pieces and samples from it, the kit_pieces draw standing without one."""
        from bitcomposer.translate import tables
        s = self._song()
        self.assertTrue(rhythm.kit_token(s).startswith("K=") and ",c=" in rhythm.kit_token(s), rhythm.kit_token(s))
        token = "bass=half:36-44:0.9:1:1.0 drums=::::0.6:::K=sbfe716b9b6,S=s1279e119a1:dense+varied melody=main:64-84:0.9:1:0.7 tempo=medium"
        t = tables.Table(("part",), "balance", votes=tables.SHARES).fit([tables.Unit(f"s{i}", "g", token, {"part": rhythm.ARRANGEMENT}) for i in range(3)])
        p = whole.plan({"balance": t}, 1, "g")
        if "drums" in p.band:
            self.assertEqual(p.extras["drums"].get("pieces"), "KS")
            self.assertEqual(p.extras["drums"].get("kit"), {"K": "sbfe716b9b6", "S": "s1279e119a1"})
            self.assertNotIn("kit_levels", p.extras["drums"])                                     # the old field: no piece levels
            self.assertEqual(p.habits["drums"], "dense varied")

    def test_each_kit_piece_plays_at_its_own_level(self):
        """Round 68: the kit field carries each piece's level beside its sample (`K=sbfe716b9b6@1.7`, a share of the
        loudest part's); the plan keeps them (extras.drums.kit_levels) and note_level plays a drum note on a kit slot at
        its piece's share (the open hat at the hat's), a piece without one at the part's level, a share over the top
        at the cap of full. Blackjack's token had said drums at 0.2 (the hat's median) where its kick plays at 1.7."""
        from bitcomposer.translate import tables
        token = ("bass=half:36-44:0.9:1:1.0 drums=::::0.2:::K=sbfe716b9b6@1.7,S=s1279e119a1@0.7,h=sd1c4c7ce33@0.2,c=sa64e6372fc:dense+varied "
                 "melody=main:64-84:0.9:1:0.7 top=0.30 tempo=medium")
        t = tables.Table(("part",), "balance", votes=tables.SHARES).fit([tables.Unit(f"s{i}", "g", token, {"part": rhythm.ARRANGEMENT}) for i in range(3)])
        p = whole.plan({"balance": t}, 1, "g")
        if "drums" not in p.band:
            self.skipTest("the drums left out of this seed's textures")
        self.assertEqual(p.extras["drums"]["kit"], {"K": "sbfe716b9b6", "S": "s1279e119a1", "h": "sd1c4c7ce33", "c": "sa64e6372fc"})
        self.assertEqual(p.extras["drums"]["kit_levels"], {"K": 1.7, "S": 0.7, "h": 0.2})
        self.assertTrue(any(line.startswith("kit from the balance: KShc (K sbfe716b9b6 at 1.70, S s1279e119a1 at 0.70, h sd1c4c7ce33 at 0.20, c sa64e6372fc)") for line in p.log), p.log)   # a tenths token still reads
        self.assertAlmostEqual(p.top_level, 0.30)
        self.assertAlmostEqual(whole.note_level(p, "drums", 0, piece="kick"), 0.30 * 1.7)          # the kick at its own share
        self.assertAlmostEqual(whole.note_level(p, "drums", 1, piece="hihat"), 0.30 * 0.2)         # the hat at its own
        self.assertAlmostEqual(whole.note_level(p, "drums", 1, piece="open_hihat"), 0.30 * 0.2)    # the open hat on the hat's sample, at its level
        self.assertAlmostEqual(whole.note_level(p, "drums", 0, piece="crash"), 0.30 * 0.2)         # no level for the crash: the part's (the token's 0.2)
        self.assertAlmostEqual(whole.note_level(p, "drums", 0), 0.30 * 0.2)                        # no slot named: the part's
        self.assertEqual(whole.kit_piece_level(p, "kick"), 1.7); self.assertIsNone(whole.kit_piece_level(p, "rim"))
        p.top_level = 0.8
        self.assertEqual(whole.note_level(p, "drums", 0, piece="kick"), 1.0)                       # 0.8 x 1.7 reaches the cap of full

    def test_a_kit_pieces_hold_follows_its_note_in_the_token(self):
        """Round 77: the kit field carries each piece's hold, the median length the game keys it for in beats, after the
        note's slot (`o=sf89f5aedfd@0.38@62@0.25`; `K=s48bab384c7@1.00@27@6.95`); the plan keeps them (extras.drums.kit_holds,
        kit_piece_hold by slot) and the writer gives a piece on a sustaining sample that length instead of the kit's beat."""
        from bitcomposer.translate import tables
        token = ("bass=half:36-44:0.9:1:1.0 drums=::::0.2:::K=sbfe716b9b6@1.7@r48@0.50,S=s1279e119a1@0.7@56,o=sf89f5aedfd@0.38@62@0.25:dense+varied "
                 "melody=main:64-84:0.9:1:0.7 top=0.30 tempo=medium")
        t = tables.Table(("part",), "balance", votes=tables.SHARES).fit([tables.Unit(f"s{i}", "g", token, {"part": rhythm.ARRANGEMENT}) for i in range(3)])
        p = whole.plan({"balance": t}, 1, "g")
        if "drums" not in p.band:
            self.skipTest("the drums left out of this seed's textures")
        self.assertEqual(p.extras["drums"]["kit_holds"], {"K": 0.5, "o": 0.25})                 # the snare's slot carries a note and no hold
        self.assertEqual(p.extras["drums"]["kit_pitches"], {"S": 56, "o": 62})
        self.assertEqual(p.extras["drums"]["kit_rates"], {"K": 48})                              # the kick's slot: the chip's rate, an octave under
        self.assertEqual(whole.kit_piece_rate(p, "kick"), 48); self.assertIsNone(whole.kit_piece_rate(p, "rim"))
        self.assertEqual(whole.kit_piece_hold(p, "kick"), 0.5)
        self.assertEqual(whole.kit_piece_hold(p, "rim"), 0.25)                                    # the "o" slot's sample
        self.assertIsNone(whole.kit_piece_hold(p, "hihat"))
        self.assertTrue(any("o sf89f5aedfd at 0.38 struck at 62 held 0.25 beats" in line for line in p.log), p.log)
        self.assertTrue(any("K sbfe716b9b6 at 1.70 struck -12 semitones from the recording held 0.50 beats" in line for line in p.log), p.log)

    def test_a_kit_pieces_degree_is_realized_in_the_written_key(self):
        """Round 79: the balance token carries its song's key; a tonal piece's note slot is a degree of it (`d9`, scale steps
        from the tonic; `c-3` semitones off the scale) and a tuned drum's rate carries a t. The plan keeps them, and the
        kit's note is realized in the written key from the written tonic nearest the song's: Cyan's sizzle on the minor
        sixth stays a minor sixth, where the absolute note had landed on A minor's leading tone."""
        import importlib
        from types import SimpleNamespace
        from bitcomposer.translate import tables
        render_mod = importlib.import_module("bitcomposer.translate.whole.render")
        token = ("bass=half:36-44:0.9:1:1.0 drums=::::0.2:::K=sbfe716b9b6@1.7@r48t@0.50,S=s1279e119a1@0.7@r60,o=sf89f5aedfd@0.38@d9@0.25,c=s3bfa4539ca@0.4@c-3:dense+varied "
                 "melody=main:64-84:0.9:1:0.7 key=2:minor top=0.30 tempo=medium")
        t = tables.Table(("part",), "balance", votes=tables.SHARES).fit([tables.Unit(f"s{i}", "g", token, {"part": rhythm.ARRANGEMENT}) for i in range(3)])
        p = whole.plan({"balance": t}, 1, "g")
        if "drums" not in p.band:
            self.skipTest("the drums left out of this seed's textures")
        self.assertEqual(whole.kit_token_key(p), (2, "minor"))
        self.assertEqual(p.extras["drums"]["kit_degrees"], {"o": ("d", 9), "c": ("c", -3)})
        self.assertEqual(p.extras["drums"]["kit_rates"], {"K": 48, "S": 60})
        self.assertEqual(p.extras["drums"]["kit_tuned"], {"K"})
        self.assertEqual(whole.kit_piece_degree(p, "rim"), ("d", 9)); self.assertIsNone(whole.kit_piece_degree(p, "kick"))
        self.assertTrue(whole.kit_piece_tuned(p, "kick")); self.assertFalse(whole.kit_piece_tuned(p, "snare"))
        p.extras["drums"]["kit"] = {"K": "kick_sample", "S": "snare_sample", "o": "bell", "c": "crash_sample"}
        p.tonic, p.mode = 9, "minor"                                                   # written in A minor; the token's song in D minor
        bell = SimpleNamespace(c5_speed=32000, source_rate=32000)
        self.assertEqual(render_mod.kit_note_of(p, "rim", "bell", bell), 72.0)              # d9 from the A nearest D4 (A3, 57): an octave and a third up, C5
        p.tonic = 2
        self.assertEqual(render_mod.kit_note_of(p, "rim", "bell", bell), 77.0)              # the same key as the token's: D4 + 9 steps = F5, the game's note
        p.tonic = 7                                                                        # G minor: G4 (67) is the G nearest D4; d9 = Bb5 (82)
        self.assertEqual(render_mod.kit_note_of(p, "rim", "bell", bell), 82.0)
        from bitcomposer import samples as samples_mod
        self.assertTrue(samples_mod.is_percussion("kick_sample"))
        self.assertEqual(render_mod.kit_note_of(p, "kick", "kick_sample", bell), 48.0 - 12 + 5)   # a tuned rate moves with the key: D to G is +5
        self.assertEqual(render_mod.kit_note_of(p, "snare", "snare_sample", bell), 48.0)       # an untuned one does not
        p.extras["drums"]["kit"]["c"] = "crash_sample"
        self.assertEqual(render_mod.kit_note_of(p, "crash", "crash_sample", bell), 48.0)       # a percussion sample takes no degree

    def test_a_doubling_voice_takes_the_tokens_level_and_sample(self):
        """Round 70: a voice beside the line plays at the token's share for that voice and on the token's sample for it,
        doubling or not (the layer word gives a doubling voice its interval only); without a token share a doubling voice
        keeps the line's level and sample, as before. 163's counter second had played at 1.0 on the line's sf89f5aedfd
        where Troops March on plays it at 2.5 on sfd6accf98a; Good Night's four extra voices had all taken the first's."""
        from types import SimpleNamespace
        from unittest import mock
        from bitcomposer import instruments
        from bitcomposer.translate import tables
        token = ("accompaniment=half:56-68:0.8:3:0.6:2.5@sx@0.5/0.4@sy@0.3::sline bass=half:36-44:0.9:1:1.0:::sbass "
                 "melody=main:64-84:0.9:1:0.7:::slead top=0.30 tempo=medium")
        t = tables.Table(("part",), "balance", votes=tables.SHARES).fit([tables.Unit(f"s{i}", "g", token, {"part": rhythm.ARRANGEMENT}) for i in range(3)])
        p = whole.plan({"balance": t}, 1, "g")
        self.assertEqual(p.voices["accompaniment"], 3)
        p.extras["accompaniment"]["layers"] = ["doubling +4", "apart -8 like"]; p.extras["accompaniment"]["layer"] = "doubling +4"
        self.assertAlmostEqual(whole.note_level(p, "accompaniment", 0), 0.30 * 0.6)
        self.assertAlmostEqual(whole.note_level(p, "accompaniment", 1), 0.30 * 0.6 * 2.5)          # the doubling voice at the token's share
        self.assertAlmostEqual(whole.note_level(p, "accompaniment", 2), 0.30 * 0.6 * 0.4)
        p.voice_levels.pop("accompaniment")                                                       # no token shares: the draw for the apart voice,
        p.layer_levels["accompaniment"] = 1.3                                                     # the line's level for the doubling one
        self.assertAlmostEqual(whole.note_level(p, "accompaniment", 1), 0.30 * 0.6)
        self.assertAlmostEqual(whole.note_level(p, "accompaniment", 2), 0.30 * 0.6 * 1.3)
        made = []
        fake = lambda name: made.append(name) or SimpleNamespace(c5_speed=32000, data=b"\0\0" * 64, loop=False, sus_loop=False, name=name)   # noqa: E731
        pack = {"voices": {"harmony": ["pad"], "lead": ["pad"], "bass_medium": ["pad"], "arp": ["pad"]}}
        with mock.patch.object(instruments, "_make_sample", fake):
            samples = whole.samples_for(p, pack, {"sx", "sy", "sline", "sbass"}, "g", random.Random(1), {})
        self.assertEqual(samples["accompaniment"][0], "sline")
        self.assertEqual((samples["accompaniment:1"][0], samples["accompaniment:2"][0]), ("sx", "sy"))   # each voice's own, by rank
        self.assertEqual(samples["accompaniment:second"][0], "sx")                                 # the old field, kept for a voice without its own
        self.assertIn("accompaniment's voices beside the line on the balance's song's own samples: 2 sx, 3 sy", p.log)
        second = {"accompaniment": {2}}
        self.assertEqual(whole.sample_of(samples, "accompaniment", 0, second)[0], "sline")
        self.assertEqual(whole.sample_of(samples, "accompaniment", 1, second)[0], "sx")           # the doubling voice on the token's sample
        self.assertEqual(whole.sample_of(samples, "accompaniment", 2, second)[0], "sy")
        del samples["accompaniment:2"]
        self.assertEqual(whole.sample_of(samples, "accompaniment", 2, second)[0], "sx")           # without its own: the second's
        del samples["accompaniment:1"]
        self.assertEqual(whole.sample_of(samples, "accompaniment", 1, second)[0], "sline")        # a doubling voice without its own: the line's
        self.assertEqual(whole.sample_of(samples, "bass", 0, second)[0], "sbass")

    def test_a_written_note_plays_its_packs_envelope(self):
        """Round 71: a pack's own sample is registered as pack_name_id and the written song's sample table names it by
        its bare id, so the render's envelope lookup by the bare name alone had found nothing and every written note on
        a pack sample played flat at full gain since the envelope was added (Whole 169's bass flat where Blackjack's
        decays on the same sample). sample_envelope reads the pack's envelope under either name, and score_of's notes
        carry it (ADSR as the registers, GAIN as the register with ADSR off); a sample without one stays flat and full."""
        from types import SimpleNamespace
        from bitcomposer import samples as sm, score
        sm.SAMPLE_ENVELOPES["g_sx"] = {"adsr": [255, 238]}
        sm.SAMPLE_ENVELOPES["g_sy"] = {"gain": 0x9F}
        try:
            self.assertEqual(whole.sample_envelope("sx", "g"), {"adsr": [255, 238]})
            self.assertEqual(whole.sample_envelope("g_sx", "g"), {"adsr": [255, 238]})
            self.assertIsNone(whole.sample_envelope("sx", ""))                                   # no pack: the bare name alone
            self.assertIsNone(whole.sample_envelope("sz", "g"))
            p = whole.plan({}, 1, "g")                                                               # bass, drums, melody; 12 bars
            smp = lambda: SimpleNamespace(c5_speed=32000, data=b"\x00\x10" * 64, loop=False, sus_loop=False, loop_start=0, loop_end=0,   # noqa: E731
                                          sus_loop_start=0, sus_loop_end=0)
            written = {"bass": SimpleNamespace(notes=[(0.0, 1.0, 40, 0)]), "melody": SimpleNamespace(notes=[(0.0, 1.0, 64, 0), (1.0, 2.0, 66, 0)])}
            samples = {"bass": ("sx", smp()), "melody": ("sy", smp())}
            sc, first = whole.score_of(p, written, samples, loops=1, fade=0.0, pack_name="g")
            by = {n.voice: n for n in sc.notes}
            self.assertEqual((by[first["bass"]].adsr, by[first["bass"]].gain), ((255, 238), 0))        # the pack's ADSR
            self.assertEqual((by[first["melody"]].adsr, by[first["melody"]].gain), ((0, 0), 0x9F))     # the pack's GAIN
            samples = {"bass": ("sz", smp()), "melody": ("sy", smp())}
            sc, first = whole.score_of(p, written, samples, loops=1, fade=0.0, pack_name="g")
            by = {n.voice: n for n in sc.notes}
            self.assertEqual((by[first["bass"]].adsr, by[first["bass"]].gain), ((0, 0), score.GAIN_FULL))   # none in the pack: flat and full
        finally:
            sm.SAMPLE_ENVELOPES.pop("g_sx", None)
            sm.SAMPLE_ENVELOPES.pop("g_sy", None)

    def test_the_echo_is_the_games_own_drawn_on_its_own_stream(self):
        """Round 70: with an `echo` word the written song's echo is the counted triple (volume of full, delay as the chip's
        nearest step, feedback) with the parts that send and the parts that stay dry, drawn once on the song's own echo
        stream (whole:SEED:echo), in place of score.ECHO_WET 0.4 and the generator's delay names; a part the word's song
        lacked keeps the writer's old rule (the upper parts send); a word whose song sent nothing leaves the song dry;
        without the word the sound set's habits stand (echo_of), as before."""
        from bitcomposer.packs import PACKS
        from bitcomposer.translate import tables
        unit = lambda outcome, i: tables.Unit(f"s{i}", "g", outcome, {"part": rhythm.ECHO_PART})   # noqa: E731
        t = tables.Table(("part",), "echo", votes=tables.SHARES).fit([unit("0.20:80:0.78:bass+melody:accompaniment+drums", i) for i in range(3)])
        p = whole.plan({}, 1, "g")
        echo = whole.echo_word({"echo": t}, p, random.Random("whole:1:echo"))
        self.assertEqual((echo["wet"], echo["seconds"], echo["feedback"], echo["delay"]), (0.2, 0.08, 0.78, "80 ms"))
        self.assertEqual((echo["sends"], echo["dry"]), (["bass", "melody"], ["accompaniment", "drums"]))
        self.assertTrue(any(line.startswith("echo (echo): volume 0.20 of full, 80 ms, feedback 0.78; sends bass+melody; dry accompaniment+drums") for line in p.log), p.log)
        self.assertEqual([whole.sends_to_echo(echo, r) for r in ("melody", "bass", "accompaniment", "drums", "counter", "harmony")],
                         [True, True, False, False, True, True])                                   # the counter and harmony: not the word's song's parts, the old rule
        self.assertFalse(whole.sends_to_echo(None, "melody"))
        self.assertTrue(whole.sends_to_echo({"delay": "slap", "seconds": 0.1, "wet": 0.4, "feedback": 0.5}, "melody"))   # the habits' echo: the old rule
        self.assertFalse(whole.sends_to_echo({"delay": "slap", "seconds": 0.1, "wet": 0.4, "feedback": 0.5}, "bass"))
        self.assertEqual(whole.echo_word({"echo": tables.Table(("part",), "echo", votes=tables.SHARES).fit([unit("0.00:0:0.00:-:bass+melody", i) for i in range(3)])},
                                         whole.plan({}, 1, "g"), random.Random(1)), None)         # the song sent nothing: dry
        self.assertEqual(whole.echo_word({"echo": tables.Table(("part",), "echo", votes=tables.SHARES).fit([unit("0.20:250:0.78:melody:-", i) for i in range(3)])},
                                         whole.plan({}, 1, "g"), random.Random(1))["seconds"], 15 * 0.016)   # the chip's longest step
        self.assertIsNone(whole.echo_word({}, p, random.Random(1)))
        out = whole.compose({"echo": t}, PACKS["ffvi"], set(), "ffvi", 1, "g", max_bars=16, read=False)
        self.assertEqual(out["echo"]["word"], "0.20:80:0.78:bass+melody:accompaniment+drums")
        first, voices = out["first"], out["plan"].voices
        for role, start in first.items():
            mine = [n for n in out["score"].notes if start <= n.voice < start + voices[role]]
            if mine:
                self.assertEqual({n.echo for n in mine}, {whole.sends_to_echo(out["echo"], role)}, role)
                self.assertEqual({n.echo_volume for n in mine if n.echo}, {(0.2, 0.2)} if any(n.echo for n in mine) else set(), role)
        dry = whole.compose({"echo": t}, PACKS["ffvi"], set(), "ffvi", 1, "g", max_bars=16, read=False, echo=None)
        self.assertIsNone(dry["echo"])
        habit = whole.compose({}, PACKS["ffvi"], set(), "ffvi", 1, "g", max_bars=16, read=False)   # no word: the sound set's habits
        self.assertTrue(habit["echo"] is None or "word" not in habit["echo"])

    def test_the_mix_level_and_the_master_that_holds_it(self):
        """Round 59: a song's mix level is its perceived note levels squared over quarter-beat frames, in dB; the balance token
        carries it (and the top level) so the written song's master volume brings its own mix to its token song's."""
        self.assertAlmostEqual(rhythm.mix_level([(0.0, 1.0, 0.5)]), 20 * math.log10(0.5), places=3)
        self.assertAlmostEqual(rhythm.mix_level([(0.0, 1.0, 0.5), (0.0, 1.0, 0.5)]), 10 * math.log10(0.5), places=3)   # two at once: double the power
        self.assertAlmostEqual(rhythm.mix_level([(0.0, 8.0, 1.0), (4.0, 1.0, 1.0)]), 0.0, places=3)                 # a held note counts two beats
        self.assertIsNone(rhythm.mix_level([]))
        bridge = whole.RENDER_BRIDGE
        self.assertEqual(whole.master_of(-25.0, -25.0 - bridge), (127, 1.0))                                  # renders on target: full
        m, g = whole.master_of(-31.0, -25.0 - bridge)
        self.assertEqual((m, g), (round(127 * 10 ** (-6 / 20)), 1.0))                                         # 6 dB over: the master takes it
        m, g = whole.master_of(-19.0, -25.0 - bridge)
        self.assertEqual(m, 127); self.assertAlmostEqual(g, 10 ** (6 / 20), places=6)                         # 6 dB under: the notes come up
        s = self._song()
        s.levels = {r: 0.3 for r in s.notes}                 # the parts' levels, as the readings give them
        self.assertIsNotNone(rhythm.song_mix_level(s))
        s.loudness = -24.3
        self.assertIn("loud=-24", rhythm.balance_units([s])[0].outcome.split())                              # the song's rendered loudness rides the token
        p = whole.plan({}, 1, "g")
        self.assertIsNone(p.loudness)                                                                         # no token: no target, the master full

    def test_a_kit_writes_on_its_own_pieces_and_never_silent(self):
        """Round 58: the kit's pieces (kit_value) narrow the writer's kit, so a figure drawn from another kit's songs is one
        this kit can play; where no draw fits, the kit's last resort is any bar the table knows on its pieces, never a
        silent played bar (the drums table conditions on the kit before the habit and feel for the same reason)."""
        from bitcomposer.translate import packtables, writer
        a, b = self._song(), self._song()
        a.notes["drums"] = [(4.0 * i + x, 0.25, float("nan"), "kick") for i in range(8) for x in (0.0, 2.0)]; a.pieces = {"kick": "kick"}; a.sid = "a"
        b.notes["drums"] = [(4.0 * i + x, 0.25, float("nan"), "snare") for i in range(8) for x in (1.0, 3.0)]; b.pieces = {"snare": "snare"}; b.sid = "b"
        self.assertEqual(packtables.KEPT["drums"][3][:3], ("part", "meter", "kit"))
        entry = packtables.fit("drums", rhythm.drum_units([a, b]))
        model = packtables.read({"tables": {"drums": entry}})["drums"]
        s = self._song(); s.pieces = {"kick": "kick", "snare": "snare"}
        for kit_value, letter in (("K", "K"), ("S", "S")):
            hits, figures = writer.drums(s, {tuple(rhythm.LETTERS.values()): model}, random.Random(1), habit="medium repeating", free=True, plays=[True] * 8, kit_value=kit_value)
            self.assertEqual({x for _, x in hits}, {letter}, (kit_value, figures))
            self.assertTrue(all(f != "-" for f in figures), figures)   # every played bar sounds
        manner = writer.FreeManner({"0:K 2:K", "1:S 3:S", "-"}, {"S"}, 12, rests=True)
        self.assertEqual(writer.last_resort(manner, model, None, {}, random.Random(2)), "1:S 3:S")

    def test_a_recalled_passage_goes_on_as_the_games_do(self):
        """Round 50: each echo of the tune with a bar after it is counted by whether the next bar goes on with the bar after
        the echo's source (recall_continues: yes, no), by part and echo habit; the CONTINUE constant is the fallback alone."""
        bars = [(4.0 * k, 4.0 * k + 4.0) for k in range(8)]
        def bar(k, ps): return [(4.0 * k + i, 0.9, float(p), "a") for i, p in enumerate(ps)]
        A, B, C = [60, 64, 67, 65], [60, 64, 62, 60], [62, 65, 69, 67]
        tune = bar(0, A) + bar(1, B) + bar(2, C) + bar(3, A) + bar(4, B) + bar(5, C) + bar(6, A) + bar(7, C)
        s = rhythm.Song("t", 4, 12, bars, [], notes={"melody": tune}, sid="s", game="g", numbers=list(range(8)), parts=[(0, 8, None, "A")])
        units = rhythm.recall_continue_units([s])
        self.assertEqual([u.outcome for u in units], ["yes", "yes", "yes", "no"])   # bars 3-5 go on as bars 0-2 did; bar 6's A is followed by C, never B
        self.assertEqual({(u.values["part"], u.values["habit"]) for u in units}, {("melody", "mixed")})   # 5 of 8 bars echo: under two thirds

    def test_every_voice_writes_where_the_game_plays_its_sample(self):
        """Round 34: a voice's register is where the game plays the sample chosen for it (bound_of over the ranges word's
        drawn range and the planned register: the overlap, a sliver widened to the register grain, the sample's range
        where they miss, the plan's where the word knows nothing), the sample chosen before the writing on the part's
        drawn speed (part_speeds); the bass keeps under its ceiling; the reach check keeps the range it drew."""
        self.assertEqual(whole.bound_of(None, (48, 72)), (48, 72))
        self.assertEqual(whole.bound_of((56, 68), (48, 72)), (56, 68))
        self.assertEqual(whole.bound_of((40, 88), (48, 72)), (48, 72))
        self.assertEqual(whole.bound_of((72, 88), (48, 60)), (72, 88))
        self.assertEqual(whole.bound_of((60, 76), (48, 62)), (60, 68))
        self.assertEqual(whole.bound_of((48, 64), (62, 80)), (56, 64))
        self.assertEqual(writer.place(0, 36, 50.0), 48)
        self.assertEqual(writer.place(0, 36, 50.0, high=44), 36)
        ranges = tables.Table(("part",), "ranges", votes=tables.SHARES).fit([tables.Unit(f"s{i}", "g", "36-48", {"part": "slow"}) for i in range(3)])
        drawn = {}
        self.assertTrue(whole.reaches(ranges, "slow", (40, 52), random.Random(1), drawn))
        self.assertEqual(drawn, {"slow": (36, 48)})
        bars = [(4.0 * k, 4.0 * k + 4.0) for k in range(4)]
        tune = [(4.0 * k + 0.5 * i, 0.4, 60.0 + (i % 4) * 2, "a") for k in range(4) for i in range(8)]
        s = rhythm.Song("t", 4, 12, bars, [], notes={"melody": tune}, sid="s", game="g")
        self.assertEqual([(u.values["part"], u.values["habit"], u.outcome) for u in rhythm.part_speed_units([s])], [("melody", "dense", "4")])

    def test_the_samples_playing_habits(self):
        """A sample's shortest note and fastest bars in the game are counted per song; the sample choice weighs the part's speed;
        a drawn floor holds a note's length."""
        bars = [(4.0 * k, 4.0 * k + 4.0) for k in range(4)]
        fast = [(4.0 * k + 0.25 * i, 0.1, 60.0, "quick12345678") for k in range(4) for i in range(16)]    # sixteenths, 50 ms at 120 BPM
        slow = [(4.0 * k + i, 0.9, 48.0, "pad1234567890") for k in range(4) for i in range(4)]              # quarters, 450 ms
        s = rhythm.Song("t", 4, 12, bars, [], notes={"accompaniment": fast, "bass": slow}, sid="s", game="g", bpm=120.0)
        lengths = {u.values["part"]: (u.outcome, u.values["speed"]) for u in rhythm.sample_length_units([s])}
        speeds = {u.values["part"]: u.outcome for u in rhythm.sample_speed_units([s])}
        self.assertEqual((lengths["squick12345"], lengths["spad1234567"]), (("60", "fast"), ("long", "slow")))   # the floor by the sample's speed class (round 36)
        self.assertEqual((speeds["squick12345"], speeds["spad1234567"]), ("8", "2"))
        ranges = tables.Table(("part",), "ranges", votes=tables.SHARES).fit([tables.Unit(f"s{i}", "g", "56-68", {"part": n}) for i in range(3) for n in ("sa", "sb")])
        sp = tables.Table(("part",), "speeds", votes=tables.SHARES).fit([tables.Unit(f"s{i}", "g", o, {"part": n}) for i in range(3) for n, o in (("sa", "3"), ("sb", "12"))])
        raw = lambda n: n   # noqa: E731
        rng = random.Random(2)
        self.assertEqual(whole.best_sample(ranges, ["sa", "sb"], (58, 66), rng, raw, speed=8.0, models={"sample_speeds": sp}), "sb")   # the part runs at 8 a second: the pad loses
        self.assertIn(whole.best_sample(ranges, ["sa", "sb"], (58, 66), rng, raw, speed=1.0, models={"sample_speeds": sp}), ("sa", "sb"))
        self.assertEqual(whole.best_sample(ranges, ["sa", "sb"], (58, 66), rng, raw, speed=20.0, models={"sample_speeds": sp}), "sb")   # none this fast: the least excess over the game's fastest ever
        self.assertEqual(whole.sample_speed({"sample_speeds": sp}, "sb", rng), (12.0, 12.0))
        fl = tables.Table(("part", "speed"), "lengths", votes=tables.SHARES).fit([tables.Unit(f"s{i}", "g", o, {"part": "sa", "speed": sp_}) for i in range(3) for o, sp_ in (("80", "fast"), ("240", "slow"))])
        self.assertEqual(whole.sample_floor({"sample_lengths": fl}, "sa", rng, speed=8.0), 0.08)    # a fast part takes the fast songs' floor
        self.assertEqual(whole.sample_floor({"sample_lengths": fl}, "sa", rng, speed=2.0), 0.24)
        self.assertEqual(whole.sample_floor({"sample_lengths": fl}, "sz", rng), 0.0)

    def test_a_plan_draw_stays_at_the_part(self):
        """A register drawn for a counter never comes from the bass's: the draw stops at the part's level."""
        units = [tables.Unit(f"s{i}", "g", "28-40", {"part": "bass"}) for i in range(10)] + [tables.Unit(f"s{i}", "g", f"{60 + 4 * (i % 3)}-80", {"part": "counter"}) for i in range(3)]
        t = tables.Table(("part",), "registers", votes=tables.SHARES).fit(units)
        draws = {t.draw(("counter",), random.Random(i), floored=False, floor_k=1) for i in range(200)}
        self.assertNotIn("28-40", draws)
        self.assertIn("28-40", {t.draw(("counter",), random.Random(i), floored=False) for i in range(200)})   # without the floor it could

    def test_new_cell_rhythms(self):
        s = self._song()
        s.notes["melody"] = [(4.0 * i + x, 0.9, m, "m") for i in range(8) for x, m in ((0.0, 67.0), (1.0, 69.0), (2.0, 71.0), (3.0, 72.0 + (i % 3)))]
        units = rhythm.new_cell_rhythm_units([s])
        self.assertEqual(units[0].outcome, "new")                      # the first bar's cell is new, its rhythm too
        self.assertTrue(all(u.outcome == "previous" for u in units[1:3]))   # the same rhythm with a changed last interval: the bar before's rhythm
        self.assertEqual(len(units), 3)                                # three distinct cells in eight bars (i % 3)

    def test_chord_tone_habit_and_contour_sizes(self):
        units = rhythm.chord_tone_habit_units([self._song()])
        self.assertEqual(len(units), 1)
        self.assertEqual(units[0].outcome, "0.5")            # G and B on the G chord, A and C off it
        from bitcomposer.translate import phrases, writer
        line = [(0.0, 1.0, 60.0), (4.0, 1.0, 64.0), (8.0, 1.0, 67.0), (12.0, 1.0, 72.0)]
        self.assertEqual(phrases.contour(line, 0.0, 16.0), "rising")
        x, y, z = phrases.thirds(line, 0.0, 16.0)
        self.assertLess(x, z)
        self.assertEqual(writer.contour_targets("rising", 8.0), (0, 4.0, 8.0))
        self.assertEqual(writer.contour_targets("valley", 3.0), (0, -3.0, 0))
        self.assertEqual(writer.contour_targets("rising"), (0, 2.0, 4.0))   # without a size, as before


class TuneGrainTests(unittest.TestCase):
    def test_tune_grain_counted_by_part_and_habit(self):
        """A line's grain is its share of onsets off the beat (rhythm.GRAINS), one unit a song and tune part, under the part's habit."""
        bars = [(4.0 * k, 4.0 * k + 4.0) for k in range(8)]
        s = rhythm.Song("t", 4, 12, bars, [], notes={}, sid="s", game="g", parts=[(0, 8, None, "A")])
        s.notes["melody"] = [(a + p, 0.4, 60.0 + i, "melody") for a, _ in bars for i, p in enumerate((0.0, 0.5, 1.0, 1.5, 2.0, 3.0))]   # 2 of 6 off the beat
        s.notes["counter"] = [(a + 0.5 * i, 0.4, 72.0, "counter") for a, _ in bars for i in range(8)]                              # 4 of 8
        units = rhythm.tune_grain_units([s])
        self.assertEqual({u.values["part"]: u.outcome for u in units}, {"melody": "eighths", "counter": "fine"})
        self.assertTrue(all(u.values["habit"].split()[0] in ("sparse", "medium", "dense") for u in units))
        s.notes["counter"] = s.notes["counter"][:4]                                                                                 # under GRAIN_NOTES: no unit
        self.assertEqual([u.values["part"] for u in rhythm.tune_grain_units([s])], ["melody"])

    def test_grain_and_tier_bounds(self):
        self.assertEqual(writer.grain_bounds("on-beat"), (0.0, 0.25 + writer.GRAIN_SLACK))
        self.assertEqual(writer.grain_bounds("eighths"), (0.25 - writer.GRAIN_SLACK, 0.5 + writer.GRAIN_SLACK))
        self.assertEqual(writer.grain_bounds("fine"), (0.5 - writer.GRAIN_SLACK, 1.0))
        self.assertEqual(writer.grain_bounds(None), (0.0, 1.0))
        self.assertEqual(writer.tier_bounds("medium varied"), (2 - writer.TIER_SLACK, 6 + writer.TIER_SLACK))
        self.assertEqual(writer.tier_bounds("sparse mixed")[0], 0.0)
        self.assertEqual(writer.offbeats(["0", "1/2", "1", "3/2:x", "3"]), 2)


class AlteredVoiceTests(unittest.TestCase):
    def test_a_voice_against_a_line_note_off_the_scale_is_counted_in_semitones(self):
        """voice_intervals counts the interval in scale steps against a line note on the scale and in semitones ("s-4")
        against one off it (the value "line"); the writer's interval_pitch inverts both, so a unison with the tune's
        leading tone is the leading tone (round 66)."""
        from bitcomposer.translate import vocab, tables
        bars = [(4.0 * k, 4.0 * k + 4.0) for k in range(4)]
        tune = [(4.0 * k + i, 0.9, [72.0, 73.0, 74.0, 73.0][i], "lead") for k in range(4) for i in range(4)]    # C, C#, D, C# in C major
        counter = [(4.0 * k + i, 0.9, [72.0, 73.0, 71.0, 69.0][i], "ctr") for k in range(4) for i in range(4)]  # unison, unison on C#, B under D, A under C#
        s = rhythm.Song("t", 4, 12, bars, [vocab.Span(0.0, 16.0, 0, "", 1.0)], notes={"melody": tune, "counter": counter}, sid="s", game="g", bpm=120.0, tonic=0, mode="major")
        s.voice_notes = {1: ("melody", tune), 2: ("counter", counter)}
        iv = [u for u in rhythm.voice_interval_units([s]) if u.values["part"] == "counter"]
        self.assertEqual([u.outcome for u in iv][:4], ["0", "s0", "-2", "s-4"])
        self.assertEqual([u.values["line"] for u in iv][:4], ["scale", "altered", "scale", "altered"])
        self.assertEqual([u.values["previous"] for u in iv][:5], [rhythm.START, "0", "s0", "-2", "s-4"])
        scale = {0, 2, 4, 5, 7, 9, 11}
        self.assertEqual(writer.line_state(73.0, scale), "altered"); self.assertEqual(writer.line_state(72.0, scale), "scale")
        self.assertEqual(writer.interval_pitch("s0", 73.0, scale), 73)
        self.assertEqual(writer.interval_pitch("s-4", 73.0, scale), 69)
        self.assertEqual(writer.interval_pitch("-2", 74.0, scale), 71)
        self.assertEqual(writer.interval_entry("s-4"), ("semis", -4)); self.assertEqual(writer.interval_entry("7"), ("steps", 7))
        t = tables.Table(("part", "kind", "line", "previous"), "voice_intervals", votes=tables.SHARES).fit(
            [tables.Unit(f"s{i}", "g", o, {"part": "counter", "kind": "other", "line": ln, "previous": rhythm.START}) for i in range(8) for o, ln in (("s0", "altered"), ("-2", "scale"))])
        self.assertEqual(list(writer.interval_weights(t, ("counter", "other", "altered", rhythm.START), (), 73.0, scale)), ["s0"])   # the entries of the line's state alone
        self.assertEqual(list(writer.interval_weights(t, ("counter", "other", "scale", rhythm.START), (), 72.0, scale)), ["-2"])
        midi, entry = writer.beside_pitch({"voice_intervals": t, "voice_moves": t}, "counter", "other", scale, random.Random(1), 73.0, rhythm.START, None, 0)
        self.assertEqual((midi, entry), (73, "s0"))
        midi, entry = writer.beside_pitch({"voice_intervals": t, "voice_moves": t}, "counter", "other", scale, random.Random(1), 74.0, rhythm.START, None, 0)
        self.assertEqual((midi, entry), (71, "-2"))


class AttackClassTests(unittest.TestCase):
    def test_a_built_in_set_s_pool_rule_matches_the_part_s_attack_class(self):
        """A built-in set's voices carry whether they decay after the attack (packs.profile "struck"); given the attacks
        word's class, the pool rule lets the other class stand down where one of the class fits (round 73: FFVI's tunes
        sustain in 63 of 66 songs, and the keys had taken 6 of 10 default tunes by range and speed alone)."""
        from bitcomposer.packs import profile
        from bitcomposer.translate.whole import render
        self.assertTrue(profile("bit_piano")["struck"])
        self.assertFalse(profile("bit_square")["struck"])
        names = ["bit_square", "bit_epiano", "bit_piano"]
        for cls, expect in (("sustaining", {"bit_square"}), ("struck", {"bit_epiano", "bit_piano"})):
            picks = {render.best_sample(None, names, (60, 72), random.Random(k), lambda n: n, speed=4.0, models={}, pack="bit", attack=cls) for k in range(12)}
            self.assertTrue(picks <= expect, (cls, picks))
        self.assertIsNone(render.attack_for({}, "melody", random.Random(1), []))
        picks = {render.best_sample(None, names, (60, 72), random.Random(k), lambda n: n, speed=4.0, models={}, pack="bit") for k in range(12)}
        self.assertTrue(len(picks) >= 1)


class TonalKitPieceTests(unittest.TestCase):
    def _songs(self):
        """Two songs in 4/4 at a medium tempo: a dense one-piece "o" kit (eighths), and a kick-and-other kit whose "o" strikes
        once a bar (the limbs' table knows that bar; the kit table files it under the kit "Ko")."""
        from bitcomposer.translate.vocab import Span
        bars = [(4.0 * i, 4.0 * i + 4) for i in range(8)]
        chords = [Span(0.0, 16.0, 0, "", 1.0), Span(16.0, 32.0, 7, "", 1.0)]
        a = rhythm.Song("a", 4, 4, bars, chords, bpm=110.0, sid="a", game="G", numbers=list(range(8)), parts=[(0, 8, None, "A")], tonic=0, mode="major")
        a.notes["drums"] = [(4.0 * i + x / 2, 0.25, 62.0, "lead") for i in range(8) for x in range(8)]
        a.pieces = {"lead": "other"}
        d = rhythm.Song("d", 4, 4, bars, chords, bpm=110.0, sid="d", game="G", numbers=list(range(8)), parts=[(0, 8, None, "A")], tonic=0, mode="major")
        d.notes["drums"] = [(4.0 * i + x, 0.25, float("nan"), "kick") for i in range(8) for x in (0.0, 2.0)] + [(4.0 * i + 2.0, 0.25, 70.0, "bell") for i in range(8)]
        d.pieces = {"kick": "kick", "bell": "other"}
        return a, d

    def test_a_tonal_kit_piece_plays_its_own_sample_where_the_game_struck_it(self):
        """Round 75: the kit field carries the note each piece is struck at after its level (`o=stonal@0.4@62`, `c=sbell@@79`);
        the plan keeps them (extras.drums.kit_pitches); every kit sample of the token's song the pack holds takes its slot
        (round 74's stand-in rule is gone), and kit_note_of writes a hit on a tonal one at the game's note, or at the
        recording's own rate where the readings heard none; a percussion sample and the pack's own kit stay at KIT_NOTE."""
        from types import SimpleNamespace
        from unittest import mock
        from bitcomposer import instruments, samples as sm
        from bitcomposer.translate import tables
        token = ("bass=half:36-44:0.9:1:1.0 drums=::::0.4:::K=sbfe716b9b6@1.2,o=stonal@0.4@62,c=sbell@@79:sparse+repeating "
                 "melody=main:64-84:0.9:1:0.7 top=0.30 tempo=medium")
        t = tables.Table(("part",), "balance", votes=tables.SHARES).fit([tables.Unit(f"s{i}", "g", token, {"part": rhythm.ARRANGEMENT}) for i in range(3)])
        p = whole.plan({"balance": t}, 1, "g")
        if "drums" not in p.band:
            self.skipTest("the drums left out of this seed's textures")
        self.assertEqual(p.extras["drums"]["kit"], {"K": "sbfe716b9b6", "o": "stonal", "c": "sbell"})
        self.assertEqual(p.extras["drums"]["kit_levels"], {"K": 1.2, "o": 0.4})
        self.assertEqual(p.extras["drums"]["kit_pitches"], {"o": 62, "c": 79})
        self.assertTrue(any(line.startswith("kit from the balance: Kco (K sbfe716b9b6 at 1.20, o stonal at 0.40 struck at 62, c sbell struck at 79)") for line in p.log), p.log)
        fake = lambda name: SimpleNamespace(c5_speed=32000, source_rate=16000, data=b"\0\0" * 64, loop=False, sus_loop=False, name=name)   # noqa: E731
        pack = {"voices": {"harmony": ["pad"], "lead": ["pad"], "bass_medium": ["pad"], "arp": ["pad"],
                           "drums": {"kick": "kickvoice", "snare": "snarevoice", "hihat": "hatvoice", "crash": "crashvoice", "rim": "rimvoice"}}}
        sm.PERCUSSION_PRESETS.add("g_sbfe716b9b6"); sm.PERCUSSION_PRESETS.discard("g_stonal"); sm.PERCUSSION_PRESETS.discard("g_sbell")
        try:
            with mock.patch.object(instruments, "_make_sample", fake):
                samples = whole.samples_for(p, pack, {"sbfe716b9b6", "stonal", "sbell"}, "g", random.Random(1), {})
            self.assertEqual([samples["drums"][k][0] for k in ("kick", "rim", "crash", "snare")], ["sbfe716b9b6", "stonal", "sbell", "snarevoice"])
            self.assertIn("kit samples from the balance's song: kick sbfe716b9b6, rim stonal, crash sbell", p.log)
            self.assertIn("kit pieces on the balance's song's tonal samples, played where the game struck them: o stonal struck at 62, c sbell struck at 79", p.log)
            self.assertEqual(whole.kit_note_of(p, "kick", "sbfe716b9b6", samples["drums"]["kick"][1], "g"), 48.0)   # percussion: as recorded, at KIT_NOTE
            self.assertEqual(whole.kit_note_of(p, "rim", "stonal", samples["drums"]["rim"][1], "g"), 62.0)         # the game's note
            self.assertEqual(whole.kit_note_of(p, "crash", "sbell", samples["drums"]["crash"][1], "g"), 79.0)
            self.assertEqual(whole.kit_note_of(p, "snare", "snarevoice", samples["drums"]["snare"][1], "g"), 48.0)   # the pack's own kit
            del p.extras["drums"]["kit_pitches"]["o"]
            self.assertEqual(whole.kit_note_of(p, "rim", "stonal", samples["drums"]["rim"][1], "g"), 48.0)   # no note heard: the recording's own rate,
        finally:                                                                                            # 16000 under a C5Speed of 32000, an octave under middle C
            sm.PERCUSSION_PRESETS.discard("g_sbfe716b9b6")

    def test_a_kit_the_table_knows_only_dense_bars_for_writes_from_its_limbs(self):
        """Round 75: the drums table conditions on the kit before the habit, so a one-piece kit with no song behind it in this
        meter and tempo took another song's bars at that song's density (The Phantom Forest's lead, 13 hits a bar under
        "sparse repeating"). kit_table_reaches says whether the kit table holds a bar this kit can play within its habit's
        tier; where not, the plan writes the kit from its limbs' tables at their own counted habits."""
        from collections import Counter
        from bitcomposer.translate import packtables, writer
        a, d = self._songs()
        models = packtables.read({"tables": {"drums": packtables.fit("drums", rhythm.drum_units([a, d])),
                                             "drums-o": packtables.fit("drums-o", rhythm.drum_group_units([a, d], ("o",)))}})
        s = rhythm.Song("t", 4, 4, [(4.0 * i, 4.0 * i + 4) for i in range(8)], [], bpm=110.0, sid="t", game="G", numbers=list(range(8)), parts=[(0, 8, None, "A")])
        s.pieces = {"kick": "kick", "rim": "other"}
        self.assertFalse(writer.kit_table_reaches(models["drums"], s, {"o"}, "o", "sparse varied"))   # the kit "o" in 4/4: only the dense song's bars
        self.assertTrue(writer.kit_table_reaches(models["drums"], s, {"o"}, "o", "dense varied"))
        self.assertTrue(writer.kit_table_reaches(models["drums"], s, {"K", "o"}, "Ko", "medium varied"))   # the kit "Ko": its own song's bars, 3 hits, a medium tier
        every = tuple(rhythm.LETTERS.values())
        hits, _ = writer.drums(s, {every: models["drums"]}, random.Random(1), habit={every: "sparse varied"}, free=True, plays=[True] * 8, kit_value="o")
        self.assertGreater(max(Counter(int(t // 4) for t, _ in hits).values()), 2, "the kit table writes the dense song's bars whatever the habit")
        hits, _ = writer.drums(s, {("o",): models["drums-o"]}, random.Random(1), habit={("o",): "sparse varied"}, free=True, plays=[True] * 8, kit_value="o")
        per_bar = Counter(int(t // 4) for t, _ in hits)
        self.assertTrue(hits and all(n <= 2 for n in per_bar.values()), per_bar)                   # the limb's table at its habit: the once-a-bar strike

    def test_a_limbs_figure_follows_its_slots_strike_class(self):
        """Round 81: the kit token's slot carries its sample's strike class (rare under half a hit a bar, an accent under one,
        sparse to two, medium to six, dense over), the limb tables and the group habits condition on the group's classes, and a written letter plays
        bars from songs that strike its sample as the token song does: the once-a-bar "o" draws once-a-bar bars under "os",
        the eighths under "od", whatever habit the kit was given."""
        from collections import Counter
        from bitcomposer.translate import packtables, writer
        a, d = self._songs()
        self.assertEqual(rhythm.kit_classes(a), {"o": "d"})
        self.assertEqual(rhythm.kit_classes(d), {"K": "m", "o": "s"})
        self.assertEqual(rhythm.classes_value(rhythm.kit_classes(d), ("K", "S", "t")), "Km")
        self.assertEqual({u.values["classes"] for u in rhythm.drum_units([d])}, {"Km os"})
        self.assertEqual({u.values["classes"] for u in rhythm.drum_group_units([a, d], ("o",))}, {"od", "os"})
        self.assertEqual({(u.values["limb1"], u.values["limb2"], u.values["limb3"]) for u in rhythm.drum_group_units([d], ("K", "S", "t"))}, {("Km", "-", "-")})
        self.assertEqual({(u.values["part"], u.values["classes"]) for u in rhythm.drum_group_habit_units([a, d])}, {("drums-o", "od"), ("drums-o", "os"), ("drums-KSt", "Km")})
        import copy, importlib
        plan_mod = importlib.import_module("bitcomposer.translate.whole.plan")
        a2, d2 = copy.deepcopy(a), copy.deepcopy(d)                                   # two songs a class: a plan's draw asks that many
        a2.sid, d2.sid = "a2", "d2"
        songs = [a, a2, d, d2]
        models = packtables.read({"tables": {"drums-o": packtables.fit("drums-o", rhythm.drum_group_units(songs, ("o",))),
                                             "drum_group_habits": packtables.fit("drum_group_habits", rhythm.drum_group_habit_units(songs))}})
        s = rhythm.Song("t", 4, 4, [(4.0 * i, 4.0 * i + 4) for i in range(8)], [], bpm=110.0, sid="t", game="G", numbers=list(range(8)), parts=[(0, 8, None, "A")])
        s.pieces = {"kick": "kick", "rim": "other"}
        for cls, tier, low, high in (("os", "sparse", 1, 1), ("od", "dense", 5, 8)):
            habit = plan_mod._draw_values(models, "drum_group_habits", {"part": "drums-o", "classes": cls, "habit": "medium varied"}, random.Random(1))
            self.assertTrue(habit.startswith(tier), (cls, habit))                       # the group's habit given its slot's class, not the kit's habit
            hits, _ = writer.drums(s, {("o",): models["drums-o"]}, random.Random(1), habit={("o",): habit}, free=True, plays=[True] * 8, kit_value="o",
                                   class_values={("o",): {"classes": cls}})
            per_bar = Counter(int(t // 4) for t, _ in hits)
            self.assertTrue(hits and low <= min(per_bar.values()) and max(per_bar.values()) <= high, (cls, per_bar))
        # the plan reads the class from the token and hands the group its classes
        from bitcomposer.translate import tables
        token = ("bass=half:36-44:0.9:1:1.0 drums=::::0.2:::K=sbfe716b9b6@1.7@r48@0.50@m,S=s1279e119a1@0.7@r60@@a,o=sf89f5aedfd@0.38@d9@0.25@s:dense+varied "
                 "melody=main:64-84:0.9:1:0.7 key=2:minor top=0.30 tempo=medium")
        t = tables.Table(("part",), "balance", votes=tables.SHARES).fit([tables.Unit(f"s{i}", "g", token, {"part": rhythm.ARRANGEMENT}) for i in range(3)])
        p = whole.plan({"balance": t}, 1, "g")
        if "drums" not in p.band:
            self.skipTest("the drums left out of this seed's textures")
        self.assertEqual(p.extras["drums"]["kit_classes"], {"K": "m", "S": "a", "o": "s"})
        self.assertEqual(p.extras["drums"]["kit_holds"], {"K": 0.5, "o": 0.25})
        self.assertTrue(any("S s1279e119a1 at 0.70 struck +0 semitones from the recording, an accent" in line for line in p.log), p.log)

    def test_the_pans_ride_the_token(self):
        """Round 84: the plan reads a pitched part's voices' pans (the token's tenth field) and a kit slot's pan (after the echo
        mark); render.pan_of pans a voice or a kit piece there and falls to plan.PANS for a token without the field."""
        from bitcomposer.translate import tables
        token = ("bass=half:36-44:0.9:1:1.0:::sbass123456:medium+roots:0.50 "
                 "drums=::::0.2:::K=sbfe716b9b6@1.7@r48@0.50@m@@0.45,h=sd1c4c7ce33@0.2@@@d@e@0.65:dense+varied "
                 "melody=main:64-84:0.9:1:0.7:::slead123456:medium+mixed:0.40 "
                 "accompaniment=half:56-68:0.8:2:0.6:1.2@sacc1234567@0.50::sacc7654321:dense+varied:0.35/0.65 "
                 "echo=0.20:80:0.78:melody:bass+drums key=2:minor top=0.30 tempo=medium")
        t = tables.Table(("part",), "balance", votes=tables.SHARES).fit([tables.Unit(f"s{i}", "g", token, {"part": rhythm.ARRANGEMENT}) for i in range(3)])
        p = whole.plan({"balance": t}, 1, "g")
        self.assertEqual(p.pans, {"bass": [0.5], "melody": [0.4], "accompaniment": [0.35, 0.65]})
        self.assertTrue(any(line.startswith("pans from the balance: ") and "accompaniment=0.35/0.65" in line for line in p.log), p.log)
        self.assertEqual(whole.pan_of(p, "melody", 0), 0.4)
        self.assertEqual(whole.pan_of(p, "accompaniment", 1), 0.65)
        self.assertEqual(whole.pan_of(p, "accompaniment", 2), whole.PANS["accompaniment"][0])          # a voice past the token's list: the old rule
        if "drums" in p.band:
            self.assertEqual(p.extras["drums"]["kit_pans"], {"K": 0.45, "h": 0.65})
            self.assertEqual(p.extras["drums"]["kit_echo"], ["h"])                                     # the mark reads as before, the pan after it
            self.assertEqual(whole.pan_of(p, "drums", 1, letter="h"), 0.65)
            self.assertEqual(whole.pan_of(p, "drums", 0, letter="S"), whole.PANS["drums"][0])          # a slot without a pan: the old rule
        p.pans = {}
        self.assertEqual(whole.pan_of(p, "melody", 0), whole.PANS["melody"][0])

    def test_a_voice_in_two_places_moves_at_its_bars(self):
        """Round 85: a pan word with two places is kept as written and pan_at puts the voice at the first place for its
        bars, then the second, back and forth or once; a number is the pan at every bar."""
        from bitcomposer.translate import tables
        token = ("bass=half:36-44:0.9:1:1.0:::sbass123456:medium+roots:0.50 "
                 "melody=main:64-84:0.9:1:0.7:::slead123456:medium+mixed:0.35x4>0.65 "
                 "accompaniment=half:56-68:0.8:2:0.6:1.2@sacc1234567@0.50::sacc7654321:dense+varied:0.60x5|0.45x13/0.50 "
                 "key=2:minor top=0.30 tempo=medium")
        t = tables.Table(("part",), "balance", votes=tables.SHARES).fit([tables.Unit(f"s{i}", "g", token, {"part": rhythm.ARRANGEMENT}) for i in range(3)])
        p = whole.plan({"balance": t}, 1, "g")
        self.assertEqual(p.pans, {"bass": [0.5], "melody": ["0.35x4>0.65"], "accompaniment": ["0.60x5|0.45x13", 0.5]})
        self.assertTrue(any("melody=0.35x4>0.65" in line and "accompaniment=0.60x5|0.45x13/0.50" in line for line in p.log), p.log)
        self.assertEqual([whole.pan_of(p, "melody", 0, bar=b) for b in (0, 3, 4, 40)], [0.35, 0.35, 0.65, 0.65])
        self.assertEqual([whole.pan_of(p, "accompaniment", 0, bar=b) for b in (0, 4, 5, 17, 18, 22, 23)], [0.6, 0.6, 0.45, 0.45, 0.6, 0.6, 0.45])
        self.assertEqual(whole.pan_of(p, "accompaniment", 1, bar=9), 0.5)
        self.assertEqual(whole.pan_of(p, "melody", 0), 0.35)                                            # no bar: the first place
        self.assertEqual(whole.pan_at(0.7, 12), 0.7)

    def test_the_kits_echo_rides_the_token(self):
        """Round 82: the plan reads the token's echo word (extras.echo.word) and the slots' echo marks (extras.drums.kit_echo);
        render.echo_word takes the word in place of a draw, a vocabulary without an echo table included; piece_sends sends a
        marked piece's notes and keeps an unmarked piece dry while a pitched part follows the word's say."""
        from bitcomposer.translate import tables
        token = ("bass=half:36-44:0.9:1:1.0 drums=::::0.2:::K=sbfe716b9b6@1.7@r48@0.50@m,o=sf89f5aedfd@0.38@d9@0.25@s@e:dense+varied "
                 "melody=main:64-84:0.9:1:0.7 echo=0.20:80:0.78:melody:bass+drums key=2:minor top=0.30 tempo=medium")
        t = tables.Table(("part",), "balance", votes=tables.SHARES).fit([tables.Unit(f"s{i}", "g", token, {"part": rhythm.ARRANGEMENT}) for i in range(3)])
        p = whole.plan({"balance": t}, 1, "g")
        if "drums" not in p.band:
            self.skipTest("the drums left out of this seed's textures")
        self.assertEqual(p.extras["echo"]["word"], "0.20:80:0.78:melody:bass+drums")
        self.assertEqual(p.extras["drums"]["kit_echo"], ["o"])
        self.assertTrue(any("o sf89f5aedfd at 0.38 struck at d+9 of the key held 0.25 beats, sparse, to echo" in line for line in p.log), p.log)
        echo = whole.echo_word({}, p, random.Random(1))                                               # no echo table: the token's word stands
        self.assertEqual((echo["wet"], echo["seconds"], echo["feedback"], echo["sends"], echo["dry"]), (0.2, 0.08, 0.78, ["melody"], ["bass", "drums"]))
        self.assertTrue(any(line.startswith("echo (balance): volume 0.20 of full, 80 ms, feedback 0.78; sends melody; dry bass+drums; kit pieces to echo o") for line in p.log), p.log)
        self.assertTrue(whole.piece_sends(p, echo, "drums", letter="o"))                              # the marked piece sends though the part is dry
        self.assertFalse(whole.piece_sends(p, echo, "drums", letter="K"))
        self.assertTrue(whole.piece_sends(p, echo, "melody"))
        self.assertFalse(whole.piece_sends(p, echo, "bass"))
        self.assertFalse(whole.piece_sends(p, None, "drums", letter="o"))                             # no echo: nothing sends
        del p.extras["drums"]["kit_echo"]
        self.assertFalse(whole.piece_sends(p, echo, "drums", letter="o"))                             # no marks: the part's say

    def test_the_tempo_drawn_again_under_the_tokens_class_stays_in_it(self):
        """Round 75: the redraw under the balance token's tempo class is terminal at the class. Without the floor it gave the
        class its Witten-Bell share and every class's tempos the rest, and 8 of 46 written songs sat outside their token's
        class, their kits and figures drawn under the wrong tempo."""
        from bitcomposer.translate import tables
        tempos = tables.Table(("part", "tempo"), "tempos", votes=tables.SHARES).fit(
            [tables.Unit(f"m{i}", "g", str(100 + 5 * i), {"part": "song", "tempo": "medium"}) for i in range(4)]
            + [tables.Unit(f"f{i}", "g", str(160 + 5 * i), {"part": "song", "tempo": "fast"}) for i in range(4)])
        balance = tables.Table(("part",), "balance", votes=tables.SHARES).fit(
            [tables.Unit(f"s{i}", "g", "bass=half:36-44:0.9:1:1.0 melody=main:64-84:0.9:1:0.7 tempo=medium", {"part": rhythm.ARRANGEMENT}) for i in range(3)])
        for seed in range(1, 40):
            p = whole.plan({"balance": balance, "tempos": tempos}, seed, "g")
            self.assertEqual(rhythm.band(p.bpm), "medium", (seed, p.bpm))
        edges = tables.Table(("part", "tempo"), "tempos", votes=tables.SHARES).fit(      # the word rounds to five: a medium song at 128 counts as
            [tables.Unit(f"m{i}", "g", "130", {"part": "song", "tempo": "medium"}) for i in range(3)]   # 130, the first fast value
            + [tables.Unit(f"s{i}", "g", "85", {"part": "song", "tempo": "slow"}) for i in range(3)])
        slow = tables.Table(("part",), "balance", votes=tables.SHARES).fit(
            [tables.Unit(f"s{i}", "g", "bass=half:36-44:0.9:1:1.0 melody=main:64-84:0.9:1:0.7 tempo=slow", {"part": rhythm.ARRANGEMENT}) for i in range(3)])
        self.assertEqual(rhythm.within_band(130.0, "medium"), 129.0); self.assertEqual(rhythm.within_band(85.0, "slow"), 84.0)
        self.assertEqual(rhythm.within_band(100.0, "medium"), 100.0); self.assertEqual(rhythm.within_band(80.0, "medium"), 85.0)
        for seed in range(1, 20):
            self.assertEqual(rhythm.band(whole.plan({"balance": balance, "tempos": edges}, seed, "g").bpm), "medium", seed)
            self.assertEqual(rhythm.band(whole.plan({"balance": slow, "tempos": edges}, seed, "g").bpm), "slow", seed)
