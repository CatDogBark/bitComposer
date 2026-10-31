"""The product's performance of a written song (bitcomposer/performance.py) and
its wall against the writer: the bare performance is the writer byte for
byte, the engine never imports the product layer, the player's choices are
what they say."""
import subprocess
import sys
import tempfile
import unittest

from bitcomposer import performance, vocabularies, written
from bitcomposer.cli import build_parser, compose_from_args
from bitcomposer.packs import PACKS
from bitcomposer.performance import Performance
from bitcomposer.translate import whole


def _notes(score):
    return [(n.voice, round(n.start, 6), n.pitch, n.volume, None if n.end is None else round(n.end, 6), tuple(n.bends), n.echo)
            for n in score.notes]


class PerformanceTests(unittest.TestCase):
    def test_the_bare_performance_is_the_writer_byte_for_byte(self):
        """compose_written under Performance.none() writes what whole.compose writes with the writer's own constants:
        the product's door adds a title and a message, no note, no bend, no echo of its own."""
        for seed in (7, 201):
            ours = written.compose_written(seed=seed, performance=Performance.none())
            label = vocabularies.label(vocabularies.DEFAULT)
            theirs = whole.compose(vocabularies.load(vocabularies.DEFAULT), PACKS["bit"], set(), "bit", seed, game=label,
                                   title=f"{label} {seed}", max_bars=written.MAX_BARS, min_bars=written.MIN_BARS,
                                   tail_bars=written.TAIL_BARS, themed=False, band_returns=False, read=False, fade=written.FADE, loops=1)
            self.assertEqual(_notes(ours["score"]), _notes(theirs["score"]), seed)
            self.assertEqual(ours["plan"].letters, theirs["plan"].letters)
            self.assertEqual(ours["info"]["performance"], "bare")
            self.assertEqual(ours["info"]["vibrato"], 0)
            self.assertIn("performance: none", ours["score"].message[4])

    def test_the_engine_never_imports_the_product_layer(self):
        """translate/ is tuned against the games and measured by the tools; the player's choices stay outside it."""
        code = ("import sys, bitcomposer.translate.whole, bitcomposer.translate.pack, bitcomposer.translate.packtables; "
                "print('bitcomposer.performance' in sys.modules)")
        out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
        self.assertEqual(out.stdout.strip(), "False")

    def test_the_players_performance_asks_and_adds_what_it_says(self):
        """The default: the theme returns with the band, at least sixteen bars, the loop twice, the echo the
        vocabulary's word (round 72: the delay in ms as the word carries it), vibrato on held notes of the tune and the
        counter only, as bends within the depth, no note moved."""
        echoes, vib = [], 0
        for seed in range(1, 13):
            out = written.compose_written(seed=seed)
            info, plan, score = out["info"], out["plan"], out["score"]
            self.assertEqual((info["performance"], info["carry_theme"], info["band_returns"]), ("player", True, True))
            self.assertGreaterEqual(plan.bars, 16, seed)
            if info["echo"] is not None:
                echoes.append(info["echo"])
                self.assertRegex(info["echo"], r"^\d+ ms$")
            vib += info["vibrato"]
            voices = set()
            for role in performance.VIBRATO_PARTS:
                if role in out["first"] if "first" in out else False:
                    voices.update(range(out["first"][role], out["first"][role] + plan.voices.get(role, 1)))
            for n in score.notes:
                if n.bends:
                    self.assertGreaterEqual(n.end - n.start, performance.VIBRATO_HOLD)
                    for _, p in n.bends:
                        self.assertLessEqual(abs(1200 * __import__("math").log2(p / n.pitch)), performance.VIBRATO_DEPTH + 1.5)   # the register rounds to about a cent
                    self.assertGreater(n.bends[0][0], n.start)
                    self.assertLess(n.bends[-1][0], n.end)
            self.assertIn("performance:", score.message[4])
        self.assertGreater(len(echoes), 0)
        self.assertGreater(vib, 0)

    def test_the_players_echo_is_the_vocabularys_word_on_its_own_stream(self):
        """Round 72: the default player's echo is the `echo` word's outcome (volume, delay, feedback, the sending parts),
        drawn by the writer's own draw on the performance's stream, not a rule by tempo and density over ECHO_WET; the
        message says so. Without the word, the sound set's habits stand, and the message says that instead."""
        import random
        models = vocabularies.load(vocabularies.DEFAULT)
        for seed in (68554, 87326, 5):
            out = written.compose_written(seed=seed)
            self.assertIsNotNone(out["info"]["echo"], seed)
            plan = out["plan"]
            plan.log = []
            word = whole.render.echo_word(models, plan, random.Random(f"written:{seed}:performance:echo"))
            self.assertEqual(word["delay"], out["info"]["echo"])
            self.assertTrue({n.voice for n in out["score"].notes if n.echo})
            self.assertIn(f"echo {word['delay']} at {word['wet']:.2f} of full (the vocabulary's word)", out["score"].message[4])
            self.assertLessEqual(word["wet"], 0.3)                        # FFVI's 0.20, never the old 0.4 slap
            self.assertEqual(set(n.echo_delay for n in out["score"].notes), {word["seconds"]})
        # a vocabulary without the word: the sound set's habits, said so
        bare = {k: v for k, v in models.items() if k != "echo"}
        import unittest.mock as mock
        with mock.patch.object(vocabularies, "load", lambda name: bare):
            out = written.compose_written(seed=7)
        self.assertIn("(the sound set's habit)" if out["info"]["echo"] else "no echo", out["score"].message[4])
        self.assertTrue(any("the vocabulary having no echo word" in l for l in out["plan"].log))

    def test_echo_off_on_the_command_line_holds_for_a_written_song(self):
        with tempfile.TemporaryDirectory() as d:
            args = build_parser().parse_args(["-s", "7", "-d", d, "--echo", "off"])
            _path, info = compose_from_args(args)
            self.assertIsNone(info["echo"])
            args = build_parser().parse_args(["-s", "7", "-d", d, "--prefix", "b "])
            _path, info = compose_from_args(args)
            self.assertIsNotNone(info["echo"])

    def test_the_bare_song_and_the_performed_song_share_their_notes(self):
        """The performance adds to a song and asks the writer for things; where it asks for nothing (the switches off,
        the same bounds), the notes are the writer's with bends on top: the tune is the tune."""
        bare = written.compose_written(seed=11, performance=Performance.none())
        plain = Performance("plain", themed=False, band_returns=False, min_bars=written.MIN_BARS, max_bars=written.MAX_BARS,
                            loops=1, tail_bars=written.TAIL_BARS, fade=written.FADE, echo="song", vibrato=True)
        done = written.compose_written(seed=11, performance=plain)
        strip = lambda score: [(n.voice, round(n.start, 6), n.pitch, None if n.end is None else round(n.end, 6)) for n in score.notes]  # noqa: E731
        self.assertEqual(strip(bare["score"]), strip(done["score"]))

    def test_the_command_line_switches_and_bare(self):
        with tempfile.TemporaryDirectory() as d:
            for argv, want in ((["-s", "7"], ("player", True, True)),
                               (["-s", "7", "--no-carry-theme"], ("player", False, True)),
                               (["-s", "7", "--no-band-returns"], ("player", True, False)),
                               (["-s", "7", "--bare"], ("bare", False, False)),
                               (["-s", "7", "--bare", "--carry-theme"], ("bare", True, False))):
                args = build_parser().parse_args(argv + ["-d", d, "--prefix", "case" + str(len(argv)) + " "])
                _path, info = compose_from_args(args)
                self.assertEqual((info["performance"], info["carry_theme"], info["band_returns"]), want, argv)


if __name__ == "__main__":
    unittest.main()
