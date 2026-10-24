"""Whole songs written from a pack's tables (phase 4 of docs/IDIOM.md, the
integration): no original to follow, every part free, on a skeleton the
tables give.

    python tools/whole.py --pack PACK.json --seeds 1-20 -o DIR

The plan comes first, each draw from the pack's tables, once a song: the
key and the tempo; the form, part by part (new, again or back by index,
each new part's length by the song's length habit, a repeat as long as the
part it repeats) and the bar the loop returns to (after an intro: a first
part the form never comes back to); the band with each part's weight (one
of the game's songs' balances); the chords, bar by bar from the chord
mixture (a repeated part keeps its chords; the loop's first bar from the
loops table); the texture a part of the form (which parts sound through
it, among the band's: the part-textures table, a part keeping one texture
through nine bars in ten in the readings); each part's register, sounded
share and habits, the drums' each group's own. Then the parts are written
in turn by the free writers on a Song built from the plan: the drums, the
bass, the upper parts (harmony, accompaniment, arp), the melody and the
counter-line, each reading the band written before it (its shared hits
to lock to, counted against the band the plan has playing in the bar; its
sounding tones to stay clear of), as a part substituted into a game's
song reads the song. The band's energy is not read here: the texture is
the arrangement, and a part the plan has play alone plays. Last the notes
become a score on the pack's samples, rendered by the converter's back
end as a game's song is (spc.convert.render), and the score is read back
by the readers for the measures.

What is hand-set here is the rendering, not the writing: the voices'
levels and pans (LEVELS, PANS), how the eight voices are shared out
(WANTS, allot) and the pool a part's sample comes from (POOLS); the echo
follows the pack's own echo habits as the generator's did (score.of_song).
"""
import math
import random
import re
import statistics
from collections import Counter
from dataclasses import dataclass, field

from . import harmony, harness, rhythm, tables, vocab, writer
from .writer import scale_index, scale_pitch
from . import roles as R
from .vocab import Span

METER = 4                             # beats a bar: the form and texture tables were kept at one meter (FFVI: 64 of its 69 metered songs)
DIVISION = 12                         # grid steps a beat: sixteenths and triplets both, so any figure the tables know fits
VOICES = 8                            # the SNES chip's voices
LETTERS = "ABCDEFGHIJKLMNOP"          # the form's labels
MAX_PARTS = 12
DRUM_VOICES = (("K", "S", "t"), ("h", "c", "o"))   # the kit on two voices: the kick, snare and toms; the hat, cymbals and the rest
KIT_PIECES = {"kick": "kick", "snare": "snare", "hihat": "hat", "open_hihat": "hat", "tom": "tom", "crash": "cymbal", "rim": "other"}   # a pack's kit -> the readings' pieces
KIT_FOR = {"K": ("kick",), "S": ("snare", "rim"), "h": ("hihat", "open_hihat"), "t": ("tom", "kick"),
           "c": ("crash", "open_hihat", "hihat"), "o": ("rim", "hihat")}   # a figure's letter -> its sample, the first the kit has
DRUM_LENGTH = 1.0                     # beats a drum hit sounds at most (to the next hit on its voice otherwise)
WANTS = {R.HARMONY: 3, R.ACCOMP: 2, R.ARP: 1, R.COUNTER: 1}   # voices an upper part takes when the eight allow (one each first)
LEVELS = {R.MELODY: 0.85, R.COUNTER: 0.6, R.HARMONY: 0.5, R.ACCOMP: 0.6, R.ARP: 0.55, R.BASS: 0.8, R.DRUMS: 0.8}   # of full, by part
PANS = {R.MELODY: (0.5,), R.COUNTER: (0.6,), R.HARMONY: (0.35, 0.65, 0.5), R.ACCOMP: (0.6, 0.4), R.ARP: (0.4,), R.BASS: (0.5,),
        R.DRUMS: (0.5, 0.58)}        # the right side's share, a part's voices in turn
POOLS = {R.MELODY: "lead", R.COUNTER: "counter", R.HARMONY: "harmony", R.ARP: "arp"}   # a part's voice pool in a pack; the
BASS_POOLS = {"main": "bass_heavy", "half": "bass_medium", "minor": "bass_light"}      # accompaniment's by its motion, the bass's by its weight
SENDS = {R.MELODY, R.COUNTER, R.HARMONY, R.ACCOMP, R.ARP}   # the parts that send to the echo (score.SENDS; the accompaniment is a harmony channel there)
DEFAULTS = {"keys": "0 minor", "tempos": "120", "sizes": "3", "length_habits": "short", "form": "new", "lengths": "4",
            "balance": "bass=half drums melody=main", "drum_habits": "medium mixed", "drum_group_habits": "medium mixed",
            "bass_habits": "medium roots no-octaves", "habits": "medium mixed", "voicing_habits": "full", "motions": "block",
            "articulation": "mixed", "echo_habits": "mixed", "step_habits": "mixed", "repeat_habits": "some", "sounds": "0.8", "loops": "I",
            "chord_tones": str(writer.CHORD_ON_BEAT), "part_textures": None,
            "registers": {R.BASS: "36-52", R.HARMONY: "56-72", R.ACCOMP: "56-72", R.ARP: "60-80", R.MELODY: "64-84", R.COUNTER: "60-80"}}
FORM_TRIES = 20                       # forms drawn before one longer than asked is cut
SECOND_MEMO = False                   # a voice beside the line: its mask drawn a bar (on: the same line bar gets the same mask within a song; that
                                      # had put voices at 0.88 of the line's strikes against FFVI's 0.60, a bar at a time 0.72)
SECOND_ANY_TONE = True                # ...and takes any tone of the line's voicing but the line's, drawn a span (off: its rank's tone)
PLAN_FLOOR = 1                        # a plan's one-shot draw never backs off past the part (the first conditioning): the root of a
                                      # table keyed by part mixes every part, and under Witten-Bell a register draw reached it in a
                                      # third of draws (a counter at bass depth 8 % of the time, a bass above middle C 19 %)
PLAN_SONGS = 2                        # a finer level is used only with this many songs behind it
NUMERAL = re.compile(r"^([b#]?)([ivIV]+)(.*)$")
TOGETHER = harness.TOGETHER           # the share of the playing voices striking a position together for it to be a shared hit
NEAR = rhythm.NEAR


@dataclass
class Plan:
    """A song's skeleton, every draw from the tables once a song."""
    seed: int
    game: str
    title: str
    tonic: int
    mode: str
    bpm: float
    parts: list                       # the form: (first bar, bars, the index of the part repeated or None, letter)
    loop_bar: int                     # the bar the loop returns to
    names: list                       # a bar -> its chord as a numeral
    chords: list                      # a bar -> (root, shape)
    band: list                        # the parts, in the readings' order
    weights: dict                     # a pitched part -> minor, half or main
    textures: list                    # a bar -> the parts sounding in it, as the texture table names them
    plays: dict                       # a part -> [whether it plays in bar k]
    registers: dict                   # a part -> (low, high) midi
    sounds: dict                      # a part -> the share of its gap a note sounds
    habits: dict                      # a part -> its habit (the drums' and the bass's their own tables')
    extras: dict                      # an upper part -> {richness, motion}; the melody -> {articulation, echo, steps, repeats}
    voices: dict                      # a part -> how many voices it gets
    log: list = field(default_factory=list)
    feel: str = "duple"               # the song's feel (rhythm.song_feel), drawn once: every figure table is drawn by it

    @property
    def bars(self) -> int:
        return self.parts[-1][0] + self.parts[-1][1]

    @property
    def sid(self) -> str:
        return f"whole:{self.seed}"

    @property
    def letters(self) -> str:
        return " ".join(p[3] for p in self.parts)

    def to_json(self) -> dict:
        return {"seed": self.seed, "game": self.game, "title": self.title, "key": f"{harmony.NAMES[self.tonic]} {self.mode}", "bpm": self.bpm,
                "form": self.letters, "parts": [list(p) for p in self.parts], "loop_bar": self.loop_bar, "chords": self.names,
                "band": self.band, "weights": self.weights, "textures": self.textures, "plays": self.plays,
                "registers": {k: list(v) for k, v in self.registers.items()},
                "sounds": self.sounds, "habits": self.habits, "extras": self.extras, "voices": self.voices, "log": self.log, "feel": self.feel,
                "theme": {"bars": self.extras.get(R.MELODY, {}).get("theme_bars"), "returns": self.extras.get(R.MELODY, {}).get("returns")}}


@dataclass
class Part:
    """A part written for the plan."""
    role: str
    notes: list                       # pitched: (start, end in beats, midi, the part's voice); drums: (start, end, letter, voice, kit sample)
    figures: list
    log: list = field(default_factory=list)


MASK_FLOOR = 4                        # second_figures' draw never backs off below the line's onset count (part, feel, tempo, onsets): a mask is
                                      # read onset by onset, and one from a shorter line read around a longer one had filled it


def _draw(models: dict, name: str, context: tuple, rng: random.Random, log: list | None = None, floor_k: int | None = None) -> str:
    """A draw from a pack's table under a context (a mixture's own table alone; `floor_k` the level the draw never backs off
    below, PLAN_FLOOR, the part, without); the default where the pack has no such table."""
    t = models.get(name)
    if t is None:
        default = DEFAULTS[name]
        if isinstance(default, dict):
            default = default[context[0]]
        if log is not None and f"no {name} table" not in " ".join(log):
            log.append(f"no {name} table: {default!r} assumed")
        return default
    t = t.table if hasattr(t, "table") else t
    return t.draw(tuple(context), rng, floored=False, floor_k=PLAN_FLOOR if floor_k is None else floor_k, min_songs=PLAN_SONGS)


def _maybe(models: dict, name: str, context: tuple, rng: random.Random):
    """A one-shot draw as a number, None where the pack has no such table."""
    return float(_draw(models, name, context, rng)) if name in models else None


def plan_form(models: dict, rng: random.Random, log: list, max_bars: int | None = None) -> list:
    """The form: one of the game's forms whole (the letters table: "A B A B
    C", a part returning after another in 29 % of FFVI's songs where a
    chain by index returned in 15 %), each new part's length by the song's
    length habit (the lengths table), a repeat as long as the part it
    repeats; without a letters table, how many parts (the sizes table) and
    each part new, again or back by its index (the form table). (first
    bar, bars, the part repeated or None, letter)."""
    habit = _draw(models, "length_habits", ("form",), rng, log)
    if "letters" in models:
        letters = _draw(models, "letters", ("form",), rng, log).split()[:MAX_PARTS]
        parts, bar = [], 0
        for i, label in enumerate(letters):
            of = letters.index(label) if label in letters[:i] else None
            if of is None:
                drawn = _draw(models, "lengths", ("form", METER, habit), rng, log)
                n = rhythm.LONG if drawn.endswith("+") else max(1, int(drawn))
            else:
                n = parts[of][1]
            if max_bars is not None and parts and bar + n > max_bars:
                log.append(f"the form cut at {len(parts)} parts: {bar + n} bars would pass {max_bars}")
                break
            parts.append((bar, n, of, label))
            bar += n
        log.append(f"form {' '.join(p[3] for p in parts)}: {bar} bars, parts of {[p[1] for p in parts]} (length habit {habit})")
        return parts
    size = max(1, min(MAX_PARTS, int(_draw(models, "sizes", ("form",), rng, log))))
    parts, labels, bar = [], [], 0
    for i in range(size):
        kind = _draw(models, "form", ("form", METER, min(i + 1, 5)), rng, log) if i else "new"
        distinct = list(dict.fromkeys(labels))
        if kind == "again" and not labels:
            kind = "new"
        if kind == "back" and len(distinct) < 2:
            kind = "new"
        if kind == "new":
            label, of = LETTERS[min(len(distinct), len(LETTERS) - 1)], None
            drawn = _draw(models, "lengths", ("form", METER, habit), rng, log)
            n = rhythm.LONG if drawn.endswith("+") else max(1, int(drawn))
        else:
            label = labels[-1] if kind == "again" else rng.choice([x for x in distinct if x != labels[-1]])
            of = labels.index(label)
            n = parts[of][1]
        if max_bars is not None and parts and bar + n > max_bars:
            log.append(f"the form cut at {len(parts)} parts: {bar + n} bars would pass {max_bars}")
            break
        parts.append((bar, n, of, label))
        labels.append(label)
        bar += n
    log.append(f"form {' '.join(labels)}: {bar} bars, parts of {[p[1] for p in parts]} (length habit {habit})")
    return parts


def loop_bar_of(parts: list) -> int:
    """The bar the loop returns to: after the intro where the first part is one the form never comes back to, else the first."""
    if len(parts) > 1 and parts[0][3] not in {p[3] for p in parts[1:]}:
        return parts[1][0]
    return 0


def chord_of(name: str, tonic: int, mode: str):
    """A numeral in a key back to (root, shape): the inverse of vocab.numeral; None where the name is no numeral."""
    m = NUMERAL.match(name)
    if not m:
        return None
    acc, roman, rest = m.groups()
    degrees = vocab.DEGREES["major" if mode == "major" else "minor"]
    key = acc + roman.upper()
    if key not in degrees:
        return None
    root = (tonic + degrees.index(key)) % 12
    if roman.islower():
        shape = {v: k for k, v in vocab.MINOR_SHAPES.items()}.get(rest, "m")
    else:
        shape = rest if rest in harmony.SHAPES else ""
    return root, shape


def plan_chords(models: dict, parts: list, loop_bar: int, tonic: int, mode: str, rng: random.Random, log: list) -> tuple[list, list]:
    """A chord a bar, as numerals and as (root, shape): drawn bar by bar
    from the chord mixture (a new part starts the chain's context over,
    the song's urn going on), the loop's first bar from the loops table, a
    repeated part keeping the chords of the part it repeats."""
    total = parts[-1][0] + parts[-1][1]
    home = "I" if mode == "major" else "i"
    names = [None] * total
    cache, loops = models.get("chords"), models.get("loops")
    played, previous = Counter(), None
    for bar, n, of, _ in parts:
        if of is not None:
            src = parts[of][0]
            names[bar:bar + n] = names[src:src + n]
            continue
        prev_name = rhythm.START
        for k in range(bar, bar + n):
            if cache is None:
                name = home
            elif k == loop_bar and k > 0 and loops is not None:
                name = loops.draw((R.HARMONY,), rng)
            else:
                unit = tables.Unit("", "", "", {"part": R.HARMONY, "mode": mode, "previous": prev_name})
                name = cache.draw(unit, previous, played, rng, keep=lambda o: o != rhythm.NO_CHORD)
            if name == rhythm.NO_CHORD or chord_of(name, tonic, mode) is None:
                name = previous if previous is not None else home
            played[name] += 1
            previous = prev_name = name
            names[k] = name
    log.append("chords " + " ".join(names))
    return names, [chord_of(x, tonic, mode) for x in names]


def plan_texture(models: dict, parts: list, band: list, rng: random.Random, log: list) -> tuple[list, dict]:
    """Which parts sound in each bar: a texture a part of the form, drawn
    from the part-textures table against the band (ALL, or the band's
    parts that rest: "no drums melody"; given the part's place in the form
    and the part before's outcome), a repeated part keeping its texture;
    a bar's texture is its part's. Returns the textures a bar and each
    part's bars."""
    total = parts[-1][0] + parts[-1][1]
    textures = [None] * total
    table = models.get("part_textures")
    previous = rhythm.START
    n_parts = len(parts)
    for i, (bar, n, of, _) in enumerate(parts):
        if of is not None:
            src = parts[of][0]
            textures[bar:bar + n] = textures[src:src + n]
            continue
        t, outcome = " ".join(band), rhythm.ALL
        if table is not None:
            form = "only" if n_parts == 1 else "first" if i == 0 else "last" if i == n_parts - 1 else "middle"
            for _ in range(20):
                outcome = table.draw((rhythm.ARRANGEMENT, form, previous), rng, floored=False)
                resting = set(outcome[3:].split()) if outcome.startswith("no ") else set()
                t = " ".join(r for r in band if r not in resting)
                if t:
                    break
            else:
                t = " ".join(band)
        textures[bar:bar + n] = [t] * n
        previous = outcome
    plays = {role: [role in (textures[k] or "").split() for k in range(total)] for role in band}
    log.append("textures " + " | ".join(f"{p[3]}: {textures[p[0]]}" for p in parts))
    return textures, plays


def allot(band: list, counts: dict | None = None) -> dict:
    """How the eight voices are shared out. With the balance's counts (a
    song's voices a part, FFVI: the accompaniment and the counter-line two
    each as often as not), each pitched part takes its count and the drums
    two, trimmed from the largest parts down while the eight are passed.
    Without counts: the drums two, the bass and the melody one each, every
    upper part one, then the harmony up to three and the accompaniment up
    to two while voices remain, the counter last."""
    out = {}
    if R.DRUMS in band:
        out[R.DRUMS] = 2
    if counts:
        for role in band:
            if role != R.DRUMS:
                out[role] = max(1, counts.get(role, 1))
        while sum(out.values()) > VOICES:
            biggest = max((r for r in out if r != R.DRUMS and out[r] > 1), key=lambda r: out[r], default=None)
            if biggest is None:
                break
            out[biggest] -= 1
        return out
    for role in (R.BASS, R.MELODY):
        if role in band:
            out[role] = 1
    upper = [r for r in (R.HARMONY, R.ACCOMP, R.ARP, R.COUNTER) if r in band]
    for role in upper:
        out[role] = 1
    spare = VOICES - sum(out.values())
    for role in upper:
        give = min(WANTS[role] - 1, max(0, spare))
        out[role] += give
        spare -= give
    return out


DENSITY_WORDS = ("sparse", "medium", "dense")


def habit_near(models: dict, role: str, tempo: str, weight: str, rng: random.Random, first: str, density: str, table: str = "habits") -> str:
    """A second line's habit, drawn as the first's was (from `table`) but of the density the layers table says it has
    against the first (sparser, like, denser), the last draw where none in twenty is."""
    tier = next((i for i, w in enumerate(DENSITY_WORDS) if first.startswith(w)), 1)
    want = {"sparser": lambda t: t < tier, "like": lambda t: t == tier, "denser": lambda t: t > tier}.get(density, lambda t: True)
    habit = first
    for _ in range(20):
        habit = _draw(models, table, (role, tempo, weight), rng)
        if want(next((i for i, w in enumerate(DENSITY_WORDS) if habit.startswith(w)), 1)):
            return habit
    return habit


def layers_of(plan: "Plan", role: str) -> list:
    """What each voice of a part beside its line does, as the plan drew them (a list of layer words, the busiest voice first);
    [] for a part of one voice."""
    x = plan.extras.get(role) or {}
    if plan.voices.get(role, 1) < 2:
        return []
    return list(x.get("layers") or ([x["layer"]] if x.get("layer") else []))


def layer_of(extras: dict) -> tuple:
    """A part's second voice as the plan drew it: ("apart", offset, density), ("doubling", interval) or ("alternating",)."""
    words = (extras or {}).get("layer", "").split()
    if not words:
        return ("stack",)
    if words[0] == "apart" and len(words) >= 3:
        return ("apart", int(words[1]), words[2])
    if words[0] == "doubling" and len(words) >= 2:
        return ("doubling", int(words[1]))
    return (words[0],)


def diatonic(notes: list, interval: int, scale: set, voice: int) -> list:
    """A line again at an interval, in the scale (a third, fourth or fifth stays diatonic), on another voice."""
    steps = int(round(interval * 7 / 12))
    return [(a, b, float(scale_pitch(scale_index(int(round(m)), scale) + steps, scale)), voice) for a, b, m, *_ in notes]


THEME_TRIES = 40                      # letter draws before a themed song's letters are given up (none in forty: a table without returns)
PLAN_TRIES = 10                       # whole plans drawn for a themed song whose tune has nowhere to come back (fewer than two phrases)


def plan(models: dict, seed: int, game: str = "", title: str | None = None, max_bars: int | None = None, min_bars: int | None = None,
         themed: bool = False, band_returns: bool = False) -> Plan:
    """The skeleton of song `seed` from the tables; forms longer than `max_bars` or shorter than `min_bars` are drawn
    again (a listening round has no use for a four-bar jingle, which the game's tables hold). `themed`: the tune's
    phrase letters are drawn again until the theme comes back later in the song (the game's songs that carry a tune,
    43 % of FFVI's; the tables are the same, the draw is conditioned on what they count), and a plan whose tune has
    fewer than two phrases, so nothing could come back, is drawn again whole. `band_returns`: a return never comes
    with the tune alone; one of the chords, the bass and the accompaniment comes back with it, in the game's own mix
    of which."""
    rng = random.Random(f"whole:{seed}")
    for attempt in range(PLAN_TRIES if themed else 1):
        p = _plan_once(models, seed, rng, game, title, max_bars, min_bars, themed, band_returns)
        if not themed or p.extras.get(R.MELODY, {}).get("returns"):
            break
    if themed:
        p.extras["options"]["plan_draws"] = attempt + 1
        if attempt:
            p.log.append(f"themed: the plan drawn {attempt + 1} times until the tune had a phrase to come back in")
        if not p.extras.get(R.MELODY, {}).get("returns"):
            p.log.append(f"themed: no return in {PLAN_TRIES} plans; the song is unthemed")
    return p


def _plan_once(models: dict, seed: int, rng: random.Random, game: str, title: str | None, max_bars: int | None, min_bars: int | None,
               themed: bool, band_returns: bool) -> Plan:
    """One plan from the stream `rng`; `plan` draws it again for a themed song whose tune cannot come back."""
    log = []
    tonic_s, mode = _draw(models, "keys", ("song",), rng, log).split()
    tonic = int(tonic_s)
    bpm = float(_draw(models, "tempos", ("song",), rng, log))
    tempo = rhythm.band(bpm)
    log.append(f"key {harmony.NAMES[tonic]} {mode}, {bpm:.0f} BPM ({tempo})")
    for attempt in range(FORM_TRIES):                       # a form longer than asked is drawn again (the form's own distribution, cut to length)
        form_log = []
        parts = plan_form(models, rng, form_log, max_bars if attempt == FORM_TRIES - 1 else None)
        total = parts[-1][0] + parts[-1][1]
        if (max_bars is None or total <= max_bars) and (min_bars is None or total >= min_bars):
            break
    log += form_log + ([f"the form drawn {attempt + 1} times to fit {min_bars or 0} to {max_bars or 'any'} bars"] if attempt else [])
    loop_bar = loop_bar_of(parts)
    band, weights, layout, shares, counts = [], {}, {}, {}, {}
    for token in _draw(models, "balance", (rhythm.ARRANGEMENT,), rng, log).split():
        role, _, rest = token.partition("=")
        band.append(role)
        if rest:
            fields = rest.split(":")
            weights[role] = fields[0]
            if len(fields) > 1 and "-" in fields[1]:        # the song's layout, note lengths and voices a part come with its balance
                lo, hi = fields[1].split("-")
                layout[role] = (int(lo), int(hi))
            if len(fields) > 2 and fields[2]:
                shares[role] = float(fields[2])
            if len(fields) > 3 and fields[3]:
                counts[role] = int(fields[3])
    log.append("band " + " ".join(f"{r}={weights[r]}" + (f" {layout[r][0]}-{layout[r][1]}" if r in layout else "") + (f" x{counts[r]}" if r in counts else "")
                                  if r in weights else r for r in band))
    names, chords = plan_chords(models, parts, loop_bar, tonic, mode, rng, log)
    textures, plays = plan_texture(models, parts, band, rng, log)
    silent = [r for r in band if not any(plays[r])]
    if silent:
        log.append(f"never in a texture, left out of the band: {silent}")
        band = [r for r in band if r not in silent]
        plays = {r: plays[r] for r in band}
    registers, sounds, habits, extras = {}, {}, {}, {}
    for role in band:
        if role == R.DRUMS:
            habits[role] = _draw(models, "drum_habits", (R.DRUMS,), rng, log)
            extras[role] = {"".join(g): _draw(models, "drum_group_habits", ("drums-" + "".join(g), habits[role]), rng, log) for g in rhythm.DRUM_GROUPS}
            continue
        if role in layout:                                  # the song's own layout; the tables a part at a time where the pack has none
            registers[role] = layout[role]
        else:
            low, high = _draw(models, "registers", (role,), rng, log).split("-")
            registers[role] = (int(low), int(high))
        sounds[role] = shares[role] if role in shares else float(_draw(models, "sounds", (role,), rng, log))
        weight = weights.get(role, "half")
        if role == R.BASS:
            habits[role] = _draw(models, "bass_habits", (R.BASS, tempo, weight), rng, log)
        else:
            habits[role] = _draw(models, "habits", (role, tempo, weight), rng, log)
        if role in rhythm.UPPER:
            extras[role] = {"richness": _draw(models, "voicing_habits", (role,), rng, log), "motion": _draw(models, "motions", (role,), rng, log)}
        elif role in (R.MELODY, R.COUNTER):                  # the phrase tables count both lines as the tune's: drawn under the melody's part
            extras[role] = {"articulation": _draw(models, "articulation", (role,), rng, log),
                            "echo": _draw(models, "echo_habits", (R.MELODY, tempo, weight), rng, log),
                            "steps": _draw(models, "step_habits", (R.MELODY,), rng, log),
                            "repeats": _draw(models, "repeat_habits", (R.MELODY,), rng, log),
                            "chord_tones": float(_draw(models, "chord_tones", (R.MELODY,), rng, log)),
                            "repeat_rate": _maybe(models, "repeat_rates", (R.MELODY,), rng)}
    voices = allot(band, counts)
    for role in band:                                       # a part with two voices or more: what each voice beside its line does (the layers table)
        if role != R.DRUMS and voices.get(role, 1) >= 2:
            layers = [_draw(models, "layers", (role, str(min(rank, 4))), rng, log) if "layers" in models else "apart +0 like"
                      for rank in range(2, voices[role] + 1)]
            extras.setdefault(role, {})["layers"] = layers
            extras[role]["layer"] = layers[0]
    feel = _draw(models, "feels", ("song",), rng, log) if "feels" in models else "duple"
    if "periods" in models:                                 # the riff under the tune: a backing part's period inside a part of the form, and the bars it holds
        tempo_band = rhythm.band(bpm)
        for role in band:
            if role not in rhythm.BACKING:
                continue
            held, of_part = {}, {}
            for i, (bar, n, of, label) in enumerate(parts):
                if of is not None:
                    continue
                drawn = _draw(models, "periods", (role, rhythm.part_length(n), tempo_band), rng, log)
                if drawn == "none":
                    continue
                lag = int(drawn)
                of_part[i] = lag
                for k in range(bar + lag, bar + n):
                    if "period_holds" not in models or _draw(models, "period_holds", (role, drawn), rng) == "held":
                        held[k] = lag
            if of_part:
                extras.setdefault(role, {})["periods"] = held
                log.append(f"{role} period: " + ", ".join(f"{parts[i][3]} every {lag} bar{'s' if lag > 1 else ''}" for i, lag in of_part.items())
                           + f"; {len(held)} bars held")
    if R.MELODY in band and "phrase_letters" in models:   # the tune's phrases a part: the theme again, an earlier head again, or new
        n_parts = len(parts)
        counts_by_part = {}
        for i, (bar, n, of, label) in enumerate(parts):
            if of is not None:
                continue
            windows = []                                    # the part's phrases the tune plays in, as the writer cuts them (a short tail joins the one before)
            for j in range(0, n, rhythm.PHRASE):
                chunk = list(range(bar + j, bar + min(n, j + rhythm.PHRASE)))
                if len(chunk) < rhythm.PHRASE and windows:
                    windows[-1] += chunk
                else:
                    windows.append(chunk)
            count = sum(1 for w in windows if any(plays[R.MELODY][k] for k in w))
            if count:
                counts_by_part[i] = count
        windows_total = sum(counts_by_part.values())
        for attempt in range(THEME_TRIES if themed and windows_total > 1 else 1):
            letters, first_set = {}, False
            for i, count in counts_by_part.items():
                form = "only" if n_parts == 1 else "first" if i == 0 else "last" if i == n_parts - 1 else "middle"
                drawn = _draw(models, "phrase_letters", (R.MELODY, str(min(count, 5)), form), rng, log).split()
                drawn = (drawn + [rhythm.NEW] * count)[:count]
                if not first_set:
                    drawn[0] = rhythm.THEME                 # the song's theme is the first phrase its tune plays
                    first_set = True
                letters[i] = " ".join(drawn)
            if not themed or sum(v.split().count(rhythm.THEME) for v in letters.values()) > 1:
                break
        if themed:
            if windows_total < 2:
                log.append("themed: the tune has fewer than two phrases, nowhere to come back; the plan is drawn again")
            elif sum(v.split().count(rhythm.THEME) for v in letters.values()) > 1:
                if attempt:
                    log.append(f"themed: the phrase letters drawn {attempt + 1} times until the theme came back")
            else:
                log.append(f"themed: {THEME_TRIES} letter draws gave no return; the plan is drawn again")
        extras.setdefault(R.MELODY, {})["letters"] = letters
        log.append("phrases " + " | ".join(f"{parts[i][3]}: {v}" for i, v in letters.items()))
        # the theme's bars and its returns, and what comes back with each (the return-band table: the chords, the bass,
        # the accompaniment, in any set); the chords copied here, the band's bars by the writers (song.copies)
        theme_bars, returns = None, []
        for i, (bar, n, of, label) in enumerate(parts):
            if i not in letters:
                continue
            windows = []
            for j in range(0, n, rhythm.PHRASE):
                chunk = list(range(bar + j, bar + min(n, j + rhythm.PHRASE)))
                if len(chunk) < rhythm.PHRASE and windows:
                    windows[-1] += chunk
                else:
                    windows.append(chunk)
            live = [w for w in windows if any(plays[R.MELODY][k] for k in w)]
            for w, letter in zip(live, letters[i].split()):
                if letter != rhythm.THEME:
                    continue
                if theme_bars is None:
                    theme_bars = w[:rhythm.PHRASE]
                    continue
                back = _draw(models, "return_band", ("return",), rng, log) if "return_band" in models else "none"
                if band_returns:                            # never the tune alone: the game's own mix of what comes back, the "none" left out
                    for _ in range(20):
                        if back != "none" and any(x == "chords" or x in band for x in back.split()):
                            break
                        back = _draw(models, "return_band", ("return",), rng, log) if "return_band" in models else "chords"
                with_ = [x for x in back.split() if x != "none" and (x == "chords" or x in band)]
                returns.append({"bars": w[:len(theme_bars)], "with": with_})
        if theme_bars is not None:
            extras[R.MELODY]["theme_bars"] = theme_bars
            extras[R.MELODY]["returns"] = returns
            for r in returns:
                if "chords" in r["with"]:
                    for a, b in zip(theme_bars, r["bars"]):
                        names[b], chords[b] = names[a], chords[a]
            if returns:
                log.append("theme at bars " + "-".join(str(theme_bars[0]) + "" if len(theme_bars) == 1 else [str(theme_bars[0]), str(theme_bars[-1])]) + "; returns "
                           + ", ".join(f"bar {r['bars'][0]} with {' + '.join(r['with']) or 'the tune alone'}" for r in returns))
    for role in band:
        log.append(f"{role}: " + ", ".join(x for x in (
            f"weight {weights[role]}" if role in weights else "", f"register {registers[role]}" if role in registers else "",
            f"sounds {sounds[role]:.1f}" if role in sounds else "", f"voices {voices.get(role, 1)}", f"habit {habits[role]}",
            " ".join(f"{k} {v}" for k, v in extras.get(role, {}).items()),
            f"plays {sum(plays[role])}/{len(plays[role])} bars") if x))
    if themed or band_returns:
        extras.setdefault("options", {}).update({"themed": themed, "band_returns": band_returns})
    return Plan(seed, game, title or f"Whole {seed}", tonic, mode, bpm, parts, loop_bar, names, chords, band, weights, textures, plays,
                registers, sounds, habits, extras, voices, log, feel=feel)


def song_of(plan: Plan, kit=()) -> rhythm.Song:
    """The plan as the Song the writers write on: its bars, its chords as
    spans, its form; `kit` the pack's kit pieces (song.pieces)."""
    bars = [(float(METER * k), float(METER * (k + 1))) for k in range(plan.bars)]
    chords = [Span(a, b, c[0], c[1], 1.0) if c else Span(a, b, None, "", 0.0) for (a, b), c in zip(bars, plan.chords)]
    song = rhythm.Song(plan.title, METER, DIVISION, bars, chords, bpm=plan.bpm, sid=plan.sid, game=plan.game,
                       numbers=list(range(plan.bars)), parts=list(plan.parts), tonic=plan.tonic, mode=plan.mode, loop_bar=plan.loop_bar)
    song.pieces = {name: KIT_PIECES[name] for name in kit if name in KIT_PIECES}
    song.feel = plan.feel
    x = plan.extras.get(R.MELODY, {})
    if x.get("theme_bars") and x.get("returns"):            # the band back with the theme: each part copies its theme bars there
        for r in x["returns"]:
            for role in r["with"]:
                if role != "chords":
                    song.copies.setdefault(role, []).append((r["bars"][0], len(r["bars"]), x["theme_bars"][0]))
    for role in rhythm.BACKING:                             # the riff: a backing part's held bars play the bar a period before again
        held = (plan.extras.get(role) or {}).get("periods")
        if held:
            song.periods[role] = {int(k): int(v) for k, v in held.items()}
    return song


def _voices_of(song: rhythm.Song, exclude: set) -> list:
    """The onsets of every voice written so far but the part's: a pitched part one voice, the drums their two."""
    out = []
    for role, ns in song.notes.items():
        if role in exclude:
            continue
        if role == R.DRUMS:
            for group in DRUM_VOICES:
                starts = sorted(n[0] for n in ns if rhythm.LETTERS.get(song.pieces.get(n[3]), "o") in group)
                if starts:
                    out.append(starts)
        else:
            out.append(sorted(n[0] for n in ns))
    return out


def locks_of(song: rhythm.Song, exclude: set, plan: "Plan | None" = None) -> dict:
    """The band's shared hits a bar (harness.locks on the parts written so
    far): positions where TOGETHER of the voices playing in the bar strike
    within NEAR; {bar index: (positions, no stop beats)}. With a plan, the
    voices playing are counted as the plan has them in the bar (every
    part but the one written, written yet or not), so a part written early
    locks to nothing (two drum voices alone are no band) and one written
    late locks to the band's real accents."""
    voices = _voices_of(song, exclude)
    out = {}
    for k, (a, b) in enumerate(song.bars):
        playing = [starts for starts in voices if any(a - NEAR <= t < b - NEAR for t in starts)]
        if len(playing) < 2:
            continue
        total = len(playing)
        if plan is not None:
            total = max(total, sum(plan.voices.get(r, 0) for r in plan.band if r not in exclude and k < len(plan.plays[r]) and plan.plays[r][k]))
        must = set()
        for step in range(int(round(b - a)) * 4):
            t = a + step / 4
            if sum(1 for starts in playing if any(abs(x - t) < NEAR for x in starts)) >= TOGETHER * total:
                must.add(rhythm.position(t - a, song.division))
        if must:
            out[k] = (must, set())
    return out


def _replace_bars(part, song: rhythm.Song, role: str, a: float, b: float, copied: list) -> None:
    """The part's notes in [a, b) replaced by `copied` [(start, end, midi, voice)], in the written part and the song."""
    inside = lambda t: a - rhythm.NEAR <= t < b - rhythm.NEAR   # noqa: E731
    part.notes[:] = sorted([n for n in part.notes if not inside(n[0])] + copied, key=lambda n: n[0])
    song.notes[role] = sorted([n for n in song.notes.get(role, []) if not inside(n[0])] + [(t, u - t, m, role) for t, u, m, _ in copied], key=lambda n: n[0])


def double_theme(plan: Plan, song: rhythm.Song, written: dict, models: dict, rng: random.Random) -> list:
    """Where the tune plays its theme cell (its statement and its echoes), the parts the theme_doubling table draws
    play the cell with it, at the drawn interval, in the tune's rhythm: FFVI's hook doubled by a second instrument a
    bar at a time. Returns a log line a bar doubled."""
    x = plan.extras.get(R.MELODY, {})
    if R.MELODY not in written or "theme_doubling" not in models or not x.get("theme_bars"):
        return []
    cells = rhythm.melody_cells(song)
    theme_bars = x["theme_bars"]
    theme = next((cells[k] for k in theme_bars if k < len(cells) and cells[k]), None)
    if theme is None:
        return []
    tune = [n for n in written[R.MELODY].notes if n[3] == 0]
    log = []
    for k, c in enumerate(cells):
        if c != theme:
            continue
        drawn = _draw(models, "theme_doubling", ("theme", "statement" if k in theme_bars else "later"), rng)
        a, b = song.bars[k]
        bar_notes = [n for n in tune if a - rhythm.NEAR <= n[0] < b - rhythm.NEAR]
        for token in drawn.split():
            role, _, off = token.partition(":")
            if role not in plan.band or role not in written or role == R.MELODY or not off or not bar_notes:
                continue
            low, high = plan.registers.get(role, (24, 100))
            copied = []
            for t, u, m, _ in bar_notes:
                p = m + int(off)
                while p < low:
                    p += 12
                while p > high:
                    p -= 12
                copied.append((t, u, float(p), 0))
            _replace_bars(written[role], song, role, a, b, copied)
            log.append(f"bar {k}: the {role} doubles the theme's cell ({int(off):+d})")
    return log


def carry_theme(plan: Plan, song: rhythm.Song, written: dict, models: dict, rng: random.Random) -> list:
    """A phrase whose tune is not the theme may have the theme phrase carried by another part (the theme_carrier
    table: the bass, the counter, the accompaniment, mostly none), the tune's own theme bars played there in that
    part's register while the tune plays what it drew. Returns a log line a phrase carried."""
    x = plan.extras.get(R.MELODY, {})
    if R.MELODY not in written or "theme_carrier" not in models or not x.get("theme_bars") or not x.get("letters"):
        return []
    theme_bars = x["theme_bars"]
    tune = [n for n in written[R.MELODY].notes if n[3] == 0]
    a0, b0 = song.bars[theme_bars[0]][0], song.bars[theme_bars[-1]][1]
    theme_notes = [n for n in tune if a0 - rhythm.NEAR <= n[0] < b0 - rhythm.NEAR]
    if not theme_notes:
        return []
    letters = {int(k): v for k, v in x["letters"].items()}
    counts, log = {}, []
    for i, w in rhythm.phrase_windows(song):
        if i is None or not any(plan.plays[R.MELODY][k] for k in w if k < len(plan.plays[R.MELODY])):
            continue                                        # the letters count the live windows only
        j = counts.get(i, 0)
        counts[i] = j + 1
        ls = str(letters.get(i, "")).split()
        if w[0] <= theme_bars[0] or (ls[j] if j < len(ls) else rhythm.NEW) == rhythm.THEME:
            continue
        carrier = _draw(models, "theme_carrier", ("carrier",), rng)
        if carrier == "none" or carrier not in plan.band or carrier not in written:
            continue
        n = min(len(theme_bars), len(w))
        shift = song.bars[w[0]][0] - a0
        a, b = song.bars[w[0]][0], song.bars[w[0] + n - 1][1]
        low, high = plan.registers.get(carrier, (24, 100))
        octaves = round(((low + high) / 2 - statistics.median(m for _, _, m, _ in theme_notes)) / 12)
        copied = [(t + shift, u + shift, float(min(high, max(low, m + 12 * octaves))), 0) for t, u, m, _ in theme_notes if t + shift < b - rhythm.NEAR]
        _replace_bars(written[carrier], song, carrier, a, b, copied)
        log.append(f"bar {w[0]}: the {carrier} carries the theme phrase ({12 * octaves:+d})")
    return log


def copy_repeats(plan: Plan, song: rhythm.Song, written: dict) -> list:
    """A part of the form that repeats an earlier one plays it note for note in every part written, as a driver replays
    a part (the writers copy their own figures for it already; the notes under them, the second lines and the voicings
    had been written fresh, so the form reader, which finds parts by such repeats, heard one part where the plan had
    four). Returns a log line a repeat."""
    log = []
    for i, (bar, n, of, label) in enumerate(plan.parts):
        if of is None:
            continue
        src_bar, src_n = plan.parts[of][0], plan.parts[of][1]
        m = min(n, src_n)
        if m <= 0 or bar + m > len(song.bars) or src_bar + m > len(song.bars):
            continue
        shift = song.bars[bar][0] - song.bars[src_bar][0]
        lo_s, hi_s = song.bars[src_bar][0], song.bars[src_bar + m - 1][1]
        lo_t, hi_t = song.bars[bar][0], song.bars[bar + m - 1][1]
        inside = lambda t, lo, hi: lo - rhythm.NEAR <= t < hi - rhythm.NEAR   # noqa: E731
        for role, part in written.items():
            kept = [x for x in part.notes if not inside(x[0], lo_t, hi_t)]
            copied = [(x[0] + shift, x[1] + shift) + tuple(x[2:]) for x in part.notes if inside(x[0], lo_s, hi_s)]
            part.notes[:] = sorted(kept + copied, key=lambda x: x[0])
            for k in range(m):
                if bar + k < len(part.figures) and src_bar + k < len(part.figures):
                    part.figures[bar + k] = part.figures[src_bar + k]
            if role in song.notes:
                kept = [x for x in song.notes[role] if not inside(x[0], lo_t, hi_t)]
                copied = [(x[0] + shift,) + tuple(x[1:]) for x in song.notes[role] if inside(x[0], lo_s, hi_s)]
                song.notes[role] = sorted(kept + copied, key=lambda x: x[0])
        log.append(f"{label} (bars {bar}-{bar + m - 1}) plays {plan.parts[of][3]} (bars {src_bar}-{src_bar + m - 1}) again note for note")
    return log


def write(plan: Plan, song: rhythm.Song, models: dict, seed: int, reference=None) -> dict:
    """The parts written in turn on the song: the drums, the bass, the upper
    parts, the melody; each put into song.notes for the next to read.
    {role: Part}."""
    written, key = {}, (plan.tonic, plan.mode)
    kit_letters = {rhythm.LETTERS[p] for p in song.pieces.values() if p in rhythm.LETTERS}
    if R.DRUMS in plan.band and kit_letters:
        if "drums" in models:                               # the kit as one figure: its bars repeat and vary together, as a kit's do
            groups = {tuple(rhythm.LETTERS.values()): models["drums"]}
        else:                                               # a pack with the groups alone: each its own habit and rests
            groups = {g: models[name] for g in rhythm.DRUM_GROUPS if (name := "drums-" + "".join(g)) in models and set(g) & kit_letters}
        if groups:
            group_habits = {g: (plan.habits[R.DRUMS] if len(g) > 3 else plan.extras.get(R.DRUMS, {}).get("".join(g)) or plan.habits[R.DRUMS]) for g in groups}
            for g in rhythm.DRUM_GROUPS:                    # the one-letter groups' own habits cap their hits in the kit's draw (writer.group_caps)
                if len(g) == 1 and plan.extras.get(R.DRUMS, {}).get("".join(g)):
                    group_habits.setdefault(g, plan.extras[R.DRUMS]["".join(g)])
            hits, figures = writer.drums(song, groups, random.Random(f"{seed}:drums"), habit=group_habits, free=True, plays=plan.plays[R.DRUMS])
            by_voice, notes, dropped = {}, [], Counter()
            for t, letter in hits:
                sample = next((name for name in KIT_FOR.get(letter, ()) if name in song.pieces), None)
                if sample is None:
                    dropped[letter] += 1
                    continue
                v = next((i for i, g in enumerate(DRUM_VOICES) if letter in g), 1)
                by_voice.setdefault(v, []).append((t, letter, sample))
            for v, mine in by_voice.items():
                mine.sort()
                seen = set()
                for i, (t, letter, sample) in enumerate(mine):
                    if round(t, 3) in seen:                 # two pieces on one voice at once: the first by the group's order
                        continue
                    seen.add(round(t, 3))
                    after = next((u for u, *_ in mine[i + 1:] if u > t + NEAR), None)
                    notes.append((t, min(after if after is not None else t + DRUM_LENGTH, t + DRUM_LENGTH), letter, v, sample))
            song.notes[R.DRUMS] = [(t, end - t, float("nan"), sample) for t, end, _, _, sample in notes]
            written[R.DRUMS] = Part(R.DRUMS, notes, figures, [f"kit habit {plan.habits[R.DRUMS]}; groups " + ", ".join(f"{'+'.join(g)} {h}" for g, h in group_habits.items())
                                                              + f"; {sum(1 for f in figures if f != writer.REST)} bars written, {len(notes)} hits"
                                                              + (f"; dropped (no sample) {dict(dropped)}" if dropped else "")])
    if R.BASS in plan.band and "bass" in models:
        lock = locks_of(song, {R.BASS}, plan)
        layered = plan.voices.get(R.BASS, 1) >= 2 and layer_of(plan.extras.get(R.BASS))[0] == "apart"
        sounds_line = float(_draw(models, "layer_sounds", (R.BASS, "line"), random.Random(f"{seed}:bass:line sounds"))) if layered and "layer_sounds" in models else plan.sounds[R.BASS]
        notes, figures = writer.bass(song, models["bass"], random.Random(f"{seed}:bass"), habit=plan.habits[R.BASS], key=key, lock=lock,
                                     free=True, plays=plan.plays[R.BASS], register=plan.registers[R.BASS][0], sounds=sounds_line)
        song.notes[R.BASS] = [(a, b - a, m, "bass") for a, b, m in notes]
        line = [(a, b, m, 0) for a, b, m in notes]
        log = [f"habit {plan.habits[R.BASS]}, floor {plan.registers[R.BASS][0]}, {sum(1 for f in figures if f != writer.REST)} bars written, "
               f"{len(notes)} notes; locked to the band in {len(lock)} bars"]
        layer = layer_of(plan.extras.get(R.BASS))
        if plan.voices.get(R.BASS, 1) >= 2 and layer[0] == "apart":   # a second bass line of its own (FFVI's layered basses are all apart)
            _, offset, density = layer
            rng2 = random.Random(f"{seed}:bass:second")
            habit2 = habit_near(models, R.BASS, rhythm.band(plan.bpm), plan.weights.get(R.BASS, "half"), random.Random(f"{seed}:bass:second habit"),
                                plan.habits[R.BASS], density, table="bass_habits")
            given = None
            if "second_figures" in models:                  # the second voice's figure under the line's, as the game's second basses play
                memo = {}
                given = [f if f == writer.REST else memo.setdefault(f, _draw(models, "second_figures", (R.BASS, plan.feel, rhythm.band(plan.bpm), str(len(f.split())), f), rng2, floor_k=MASK_FLOOR))
                         for f in figures]
            sounds2 = float(_draw(models, "layer_sounds", (R.BASS, "second"), rng2)) if "layer_sounds" in models else plan.sounds[R.BASS]
            notes2, figures2 = writer.bass(song, models["bass"], rng2, habit=habit2, key=key, lock=locks_of(song, {R.BASS}, plan),
                                           free=True, plays=plan.plays[R.BASS], register=max(24, plan.registers[R.BASS][0] + offset), sounds=sounds2, figures=given)
            song.notes[R.BASS] += [(a, b - a, m, "bass") for a, b, m in notes2]
            line += [(a, b, m, 1) for a, b, m in notes2]
            figures = [f"{f} || {g}" for f, g in zip(figures, figures2)]
            log.append(f"a second line apart: floor {max(24, plan.registers[R.BASS][0] + offset)} ({offset:+d}), habit {habit2} ({density}), sounds {sounds2:.1f}; "
                       f"{sum(1 for f in figures2 if f != writer.REST)} bars, {len(notes2)} notes" + ("; its figures drawn under the line's" if given else ""))
        written[R.BASS] = Part(R.BASS, line, figures, log)
    tempo = rhythm.band(plan.bpm)
    for role in rhythm.UPPER:
        if role not in plan.band or not all(k in models for k in ("rhythm", "voicings")):
            continue
        n = plan.voices[role]
        layers = layers_of(plan, role)
        low, high = plan.registers[role]
        sounds = harness.UPPER_SOUNDS.get(role) or plan.sounds[role]
        if layers and "layer_sounds" in models:               # a layered part's line takes its own note lengths
            sounds = float(_draw(models, "layer_sounds", (role, "line"), random.Random(f"{seed}:{role}:line sounds")))
        lock = locks_of(song, {role}, plan)
        # the line, one voice, on the part's own figures and voicing; each voice beside it by its own relation (the layers
        # table: doubling at an interval, alternating, apart). An upper part is about one note loud an onset in FFVI (1.2 to
        # 1.5 of its voices strike together); a stack of voices all striking at every onset had been the writer's own
        # construction, three to four notes loud where the tune has one (Song Check 11's Whole 01).
        shared = {}                                         # the line's voicing at each onset, for the voices beside it
        notes, figures, voicings = writer.upper(song, role, [0], {0: (low, high)}, models, random.Random(f"{seed}:{role}"), plan.habits[role],
                                                plan.extras[role]["richness"], sounds, key=key, lock=lock, motion=plan.extras[role]["motion"],
                                                pedals={0: (low + high) // 2}, plays=plan.plays[role], shared=shared, tone_index=0)
        song.notes[role] = [(a, b - a, m, role) for a, b, m, _ in notes]
        log = [f"voices {n}, register {plan.registers[role]}, habit {plan.habits[role]}, voicing {plan.extras[role]['richness']}, "
               f"motion {plan.extras[role]['motion']}, sounded {sounds:.2f}; {sum(1 for f in figures if f != writer.REST)} bars written, "
               f"{len(notes)} notes; locked to the band in {len(lock)} bars"]
        all_figures = [f"{f} / {vc}" for f, vc in zip(figures, voicings)]
        line_notes = list(notes)
        scale = {(plan.tonic + i) % 12 for i in harmony.MODES["major" if plan.mode == "major" else "natural_minor"]}
        for v, word in enumerate(layers, start=1):
            rel = layer_of({"layer": word})
            if rel[0] == "doubling":
                notes_v = diatonic(line_notes, rel[1], scale, v)
                figures_v, voicings_v = figures, [f"doubling {rel[1]:+d}"] * len(figures)
                log.append(f"voice {v + 1} doubles the line at {rel[1]:+d}: {len(notes_v)} notes")
            else:                                           # alternating, or apart: beside the line, on the line's own voicing and lengths
                offset, density = (rel[1], rel[2]) if rel[0] == "apart" else (0, "like")
                reg_v = (max(24, low + offset), min(100, high + offset))
                rng_v = random.Random(f"{seed}:{role}:voice {v}")
                given = None
                if "second_figures" in models:              # which of the line's onsets it strikes with, and its own (second_mask), bar by bar
                    memo = {}
                    def masked(f):
                        drawn = _draw(models, "second_figures", (role, plan.feel, rhythm.band(plan.bpm), str(len(f.split())), f), rng_v, floor_k=MASK_FLOOR)
                        return rhythm.apply_mask(f, drawn)
                    given = [f if f == writer.REST else (memo.setdefault(f, masked(f)) if SECOND_MEMO else masked(f)) for f in figures]
                notes_v, figures_v, voicings_v = writer.upper(song, role, [v], {v: reg_v}, models, rng_v, plan.habits[role], plan.extras[role]["richness"], sounds,
                                                              key=key, lock=locks_of(song, {role}, plan), motion=plan.extras[role]["motion"],
                                                              pedals={v: (reg_v[0] + reg_v[1]) // 2}, plays=plan.plays[role], figures=given, shared=shared,
                                                              tone_index=(writer.ANY_TONE if SECOND_ANY_TONE else v))
                log.append(f"voice {v + 1} {rel[0]}: register {reg_v} ({offset:+d}, {density}), the line's voicing {v} tone{'s' if v > 1 else ''} up, "
                           f"{sum(1 for f in figures_v if f != writer.REST)} bars, {len(notes_v)} notes" + ("; its bars beside the line's" if given else ""))
            song.notes[role] += [(a, b - a, m, role) for a, b, m, _ in notes_v]
            notes = notes + notes_v
            all_figures = [f"{x} || {f} / {vc}" for x, f, vc in zip(all_figures, figures_v, voicings_v)]
        written[role] = Part(role, notes, all_figures, log)
    tempo = rhythm.band(plan.bpm)
    for role in (R.MELODY, R.COUNTER):                    # the counter-line written as the melody is, after it and clear of it
        if role not in plan.band or not all(k in models for k in ("rhythm", "moves", "contours", "endings", "relations", "values")):
            continue
        x = plan.extras[role]
        notes, figures, plog = writer.melody(song, [], plan.registers[role], models, random.Random(f"{seed}:{role}"), plan.habits[role],
                                             key=key, hold=(), reference=reference, articulation=x["articulation"], echo_habit=x["echo"],
                                             recall=models.get("melody_recall"), step_habit=x["steps"], repeat_habit=x["repeats"], plays=plan.plays[role],
                                             role=role, chord_rate=x.get("chord_tones"), repeat_rate=x.get("repeat_rate"),
                                             letters=x.get("letters") if role == R.MELODY else None, theme_body=models.get("theme_body"))
        song.notes[role] = [(a, b - a, m, role) for a, b, m in notes]
        line = [(a, b, m, 0) for a, b, m in notes]
        log = [f"register {plan.registers[role]}, habit {plan.habits[role]}, " + ", ".join(f"{k} {v}" for k, v in x.items() if k not in ("layer", "letters"))
               + f"; {sum(1 for f in figures if f != writer.REST)} bars written, {len(notes)} notes; the reference set "
               + ("checked" if reference is not None else "not on this machine")] + plog
        n, layer = plan.voices[role], layer_of(x)
        if n >= 2 and layer[0] == "doubling" and notes:     # the line again at the interval, in the scale
            scale = {(plan.tonic + i) % 12 for i in harmony.MODES["major" if plan.mode == "major" else "natural_minor"]}
            second = diatonic(line, layer[1], scale, 1)
            song.notes[role] += [(a, b - a, m, role) for a, b, m, _ in second]
            line = line + second
            log.append(f"doubled {layer[1]:+d} semitones, in the scale, on a second voice")
        elif n >= 2 and layer[0] == "apart" and role == R.COUNTER:   # a second counter-line of its own, clear of the first
            _, offset, density = layer
            low, high = plan.registers[role]
            reg2 = (max(24, low + offset), min(100, high + offset))
            habit2 = habit_near(models, role, tempo, plan.weights.get(role, "half"), random.Random(f"{seed}:{role}:second habit"), plan.habits[role], density)
            notes2, figures2, plog2 = writer.melody(song, [], reg2, models, random.Random(f"{seed}:{role}:second"), habit2,
                                                    key=key, hold=(), reference=reference, articulation=x["articulation"], echo_habit=x["echo"],
                                                    recall=models.get("melody_recall"), step_habit=x["steps"], repeat_habit=x["repeats"], plays=plan.plays[role],
                                                    role=role, chord_rate=x.get("chord_tones"), repeat_rate=x.get("repeat_rate"))
            song.notes[role] += [(a, b - a, m, role) for a, b, m in notes2]
            line = line + [(a, b, m, 1) for a, b, m in notes2]
            figures = [f"{f} || {g}" for f, g in zip(figures, figures2)]
            log.append(f"a second line apart: register {reg2} ({offset:+d}), habit {habit2} ({density}); {sum(1 for f in figures2 if f != writer.REST)} bars, {len(notes2)} notes")
            log += [f"second: {l}" for l in plog2[-2:]]
        written[role] = Part(role, line, figures, log)
    if R.MELODY in written:                                 # the theme in the band: doubled where the tune plays it, carried where it does not
        rng_theme = random.Random(f"{seed}:theme band")
        for line in double_theme(plan, song, written, models, rng_theme) + carry_theme(plan, song, written, models, rng_theme):
            written[R.MELODY].log.append(line)
    for line in copy_repeats(plan, song, written):
        for part in written.values():
            part.log.append(line)
    return written


# --- the rendering: the written notes on the pack's samples, through the converter's back end ---

REACH = 7                             # semitones a part's top may sit above the best pool sample's game-played range before the pack's
                                      # other tonal samples are tried for it


def best_sample(ranges, names: list, register: tuple, rng: random.Random, raw, others: list = ()) -> str:
    """The sample for a part's register: of the pool's samples (`names`, repeated by their share), the one whose
    game-played range (the ranges table, by the pack's own sample id, `raw(name)`) covers the register best, the part's
    top weighing most; when the pool's best still falls more than REACH short of the top, the pack's other tonal samples
    (`others`) are tried; the pool's share decides a tie. Never a random one: a sample pushed far above where the game
    played it turns shrill (8 to 10 % of written notes had sat over an octave above the recording against FFVI's 0 to 2
    %; the fit had asked only that the register's centre lie near the range, and by the pack's prefixed names it had
    found no range at all and drawn at random)."""
    def score(name):
        rid = raw(name)
        if ranges is None or ranges.songs.get((rid,), 0) == 0:
            return None
        lo, hi = (int(x) for x in ranges.draw((rid,), rng, floored=False, floor_k=PLAN_FLOOR).split("-"))
        a, b = register
        return max(0, min(b, hi) - max(a, lo)) - 2 * max(0, b - hi) - max(0, lo - a), hi
    known = [(score(n), n) for n in names]
    known = [(s, n) for s, n in known if s is not None]
    if not known:
        return rng.choice(names)
    best = max(s[0] for s, _ in known)
    top = [n for s, n in known if s[0] == best]
    reach = max(s[1] for s, _ in known)
    if register[1] - reach > REACH and others:
        wider = [(score(n), n) for n in others if n not in names]
        wider = [(s, n) for s, n in wider if s is not None and s[0] > best]
        if wider:
            best = max(s[0] for s, _ in wider)
            top = [n for s, n in wider if s[0] == best]
    return rng.choice(top)


def sample_fits(ranges, name: str, register: tuple, rng: random.Random) -> bool | None:
    """Whether a sample was played in the part's register in the game: a range the ranges table draws for it overlaps the
    register's middle octave; None where the table knows nothing of the sample."""
    if ranges is None or ranges.songs.get((name,), 0) == 0:
        return None
    lo, hi = (int(x) for x in ranges.draw((name,), rng, floored=False, floor_k=PLAN_FLOOR).split("-"))
    centre = (register[0] + register[1]) / 2
    return lo - 6 <= centre <= hi + 6


def samples_for(plan: Plan, pack: dict, own: set, pack_name: str, rng: random.Random, models: dict | None = None) -> dict:
    """Each part's sample from the pack's pools: {role: (voice name, ITSample)}; the drums' kit {piece: (name, ITSample)}.
    `own`: the pack file's own sample names (registered as pack_name_voice), the rest built-in voices. With the pack's
    ranges table, a pitched part takes a sample of its pool the game played in the part's register (the pool's own
    weights among those); the pool's draw where none is known to fit."""
    from ..instruments import _make_sample

    def make(name):
        return name, _make_sample(f"{pack_name}_{name}" if name in own else name)
    voices = pack["voices"]
    ranges = (models or {}).get("ranges")
    out = {}
    for role in plan.band:
        if role == R.DRUMS:
            out[role] = {piece: make(name) for piece, name in (voices.get("drums") or {}).items()}
            continue
        pool = POOLS.get(role)
        if role == R.BASS:
            pool = BASS_POOLS.get(plan.weights.get(R.BASS, "half"), "bass_medium")
        elif role == R.ACCOMP:
            pool = "arp" if plan.extras.get(R.ACCOMP, {}).get("motion") == "arpeggiated" else "harmony"
        names = list(voices.get(pool) or voices.get("harmony") or voices.get("lead"))
        raw = lambda n: n[len(pack_name) + 1:] if n.startswith(pack_name + "_") else n   # noqa: E731  the pack's own id, as the ranges table names it
        drums = {raw(n) for n in (voices.get("drums") or {}).values()}
        tonal = sorted(n for n in own if n not in drums)
        out[role] = make(best_sample(ranges, names, plan.registers[role], rng, raw, tonal) if role in plan.registers else rng.choice(names))
        # a layered part apart: its line and its second voice on the game's own pair of samples (layer_samples), where the
        # pack holds them; the second voice on the line's sample otherwise
        if any(not w.startswith("doubling") for w in layers_of(plan, role)) and "layer_samples" in models_or_empty(models):
            pair = _draw(models, "layer_samples", (role,), rng).split()   # the pack's own sample ids (`own`), registered as pack_name_id
            if len(pair) == 2 and pair[0] in own:
                out[role] = make(pair[0])
            out[f"{role}:second"] = make(pair[1]) if len(pair) == 2 and pair[1] in own else out[role]
    return out


def models_or_empty(models) -> dict:
    return models or {}


def echo_of(habits: dict, bpm: float, rng: random.Random) -> dict | None:
    """The echo as the pack's habits give it (score.of_song's reading of the generator's): None for a dry song."""
    from ..echo import ECHO_DELAYS, ECHO_WETNESS
    from ..score import ECHO_STEP, ECHO_WET
    chance = habits.get("echo", 0.0)
    if rng.random() >= float(chance or 0.0):
        return None

    def pick(weights, default):
        if isinstance(weights, dict):
            names = [k for k, w in weights.items() if w]
            return rng.choices(names, [weights[k] for k in names])[0] if names else default
        return weights if isinstance(weights, str) else default
    delay, wet = pick(habits.get("echo_delay"), "eighth"), pick(habits.get("echo_wet"), "normal")
    fb = habits.get("echo_feedback", 0.5)
    feedback = rng.uniform(*fb) if isinstance(fb, (list, tuple)) else float(fb)
    row_s = 60.0 / (bpm * 4)
    steps = max(1, min(15, round(ECHO_DELAYS.get(delay, 2) * row_s / ECHO_STEP)))
    return {"delay": delay, "seconds": steps * ECHO_STEP, "wet": ECHO_WETNESS.get(wet, 1.0) * ECHO_WET, "feedback": feedback}


def voice_map(plan: Plan, written: dict) -> dict:
    """The score's voices: {role: first voice}, the parts in the band's order, each its allotted voices."""
    out, n = {}, 0
    for role in plan.band:
        if role in written and written[role].notes:
            out[role] = n
            n += plan.voices[role]
    return out


def score_of(plan: Plan, written: dict, samples: dict, loops: int = 2, fade: float = 2.0, echo: dict | None = None, tail_bars: int = 0):
    """The written parts as a score (spc.convert.Score) on the pack's
    samples: the form once, then the loop (from the loop's bar to the
    form's end) `loops` - 1 times more, fading at the end; with
    `tail_bars`, the loop's first bars once more after the last pass,
    fading through them, so a listener hears the song come back round to
    its hook; the echo as given (echo_of). Returns the score and {role:
    first voice}."""
    second_voice = {role: {v for v, w in enumerate(layers_of(plan, role), start=1) if not w.startswith("doubling")}   # a layered part's own
                    for role in plan.band if role != R.DRUMS}                                                            # lines, on their sample
    from .. import score as score_mod
    from ..drums import KIT_NOTE
    from ..spc import convert, it_song, notes as notes_mod
    beat_s = 60.0 / plan.bpm
    form_beats = plan.bars * METER
    loop_start = plan.loop_bar * METER
    loop_beats = form_beats - loop_start
    tail = min(max(0, tail_bars), plan.bars - plan.loop_bar) * METER
    seconds = (form_beats + max(0, loops - 1) * loop_beats + tail) * beat_s
    if tail:
        fade = max(fade, tail * beat_s)
    first = voice_map(plan, written)
    n_voices = sum(plan.voices[r] for r in first)
    pcm_of, key_of, instruments = {}, {}, {}

    def instrument(name, sample):
        if name not in instruments:
            idx = len(instruments) + 1
            addr = (0x100 * idx, 0)
            pcm_of[addr], key_of[addr] = score_mod._Pcm(sample), name
            instruments[name] = (idx, addr, sample.c5_speed)
        return instruments[name]
    steps_s, wet, feedback = (echo["seconds"], echo["wet"], echo["feedback"]) if echo else (0.0, 0.0, 0.0)
    notes = []

    def put(voice, role, t0, t1, midi, name, sample, j):
        idx, addr, c5 = instrument(name, sample)
        pan = PANS[role][j % len(PANS[role])]
        send = echo is not None and role in SENDS
        notes.append(notes_mod.Note(voice, t0, idx, score_mod._pitch(c5, midi), score_mod._sides(LEVELS[role], pan), (0, 0), score_mod.GAIN_FULL,
                                    send, False, brr=addr, echo_delay=steps_s, echo_volume=(wet, wet) if send else (0.0, 0.0),
                                    echo_feedback=feedback, echo_filter=score_mod.ECHO_FILTER, echo_writes=True, end=min(t1, seconds)))
    offsets = [0.0] + [form_beats - loop_start + j * loop_beats for j in range(max(0, loops - 1))]
    if tail:
        offsets.append(form_beats - loop_start + max(0, loops - 1) * loop_beats)
    for role, part in written.items():
        if role not in first:
            continue
        for j, offset in enumerate(offsets):
            for n in part.notes:
                a, b = n[0], n[1]
                if j and a < loop_start - 1e-9:
                    continue
                if tail and j == len(offsets) - 1 and a >= loop_start + tail - 1e-9:
                    continue
                t0, t1 = (a + offset) * beat_s, (b + offset) * beat_s
                if t0 >= seconds:
                    continue
                if role == R.DRUMS:
                    _, _, _, v, kit_name = n
                    name, sample = samples[R.DRUMS][kit_name]
                    put(first[role] + v, role, t0, t1, float(KIT_NOTE), name, sample, v)
                else:
                    name, sample = samples[f"{role}:second"] if f"{role}:second" in samples and n[3] in second_voice.get(role, ()) else samples[role]
                    put(first[role] + n[3], role, t0, t1, float(n[2]), name, sample, n[3])
    notes.sort(key=lambda x: (x.start, x.voice))
    tempo, row_hz = it_song.tempo_for(convert.FINE_GRID)
    message = [f"{plan.title} - {harmony.NAMES[plan.tonic]} {plan.mode} - {round(plan.bpm)} BPM - form {plan.letters}",
               "Written by bitComposer from the pack's tables (docs/IDIOM.md, phase 4: the",
               "integration): every part free on a skeleton the tables gave, rendered as a game's song is."]
    score = convert.Score(notes, seconds, n_voices, [(0.0, 127, 127)], fade, plan.title[:25], plan.game, "bitComposer", row_hz, tempo,
                          0.0, 0.0, False, None, pcm_of, key_of, message=message)
    return score, first


def stems_of(plan: Plan, written: dict, samples: dict, out_dir: str, loops: int = 1, fade: float = 3.0, echo: dict | None = None,
             tail_bars: int = 0) -> list[str]:
    """Each written part alone as a module of its own (`<title> <part>.it`),
    for a page that plays the parts in sync and switches each: the same
    length, echo and samples as the whole, so their sum is the whole.
    Returns the paths."""
    import os
    from ..spc import convert
    os.makedirs(out_dir, exist_ok=True)
    paths = []
    for role, part in written.items():
        if not part.notes:
            continue
        score, _ = score_of(plan, {role: part}, samples, loops=loops, fade=fade, echo=echo, tail_bars=tail_bars)
        score.title = f"{plan.title} {role}"[:25]
        score.message = [f"{plan.title}: the {role} alone (a stem for the Song Check)"] + list(score.message or [])[1:]
        path = os.path.join(out_dir, f"{plan.title} {role}.it")
        convert.render(score, path)
        paths.append(path)
    return paths


def read_back(score, plan: Plan, first: dict, samples: dict) -> rhythm.Song | None:
    """The score read by the readers on the plan's own beat, the roles the
    plan's (its voices are known), the kit's pieces the pack's: the Song
    the measures are taken on; None where the readers kept nothing."""
    from . import beat, reading, store
    from . import roles as roles_mod
    period = 60.0 / plan.bpm
    n = max(2, int(math.ceil(score.seconds / period)) + 1)
    beats = [k * period for k in range(n)]
    section = beat.Section(0.0, beats[-1], period / DIVISION, 0.0, first=0.0, meter=METER, downbeat=0, division=DIVISION)
    grid = beat.Grid(period / DIVISION, DIVISION, [section], beats, [t for t in beats[::METER] if t < score.seconds - 1e-6], 1.0, 0.5)
    r = reading.of_score(score, game=plan.game, title=plan.title, grid=grid)
    if r.grid is None:
        return None
    r.file, r.folder = f"{plan.title}.whole", plan.game
    role_of = {first[role] + v: role for role in first for v in range(plan.voices[role])}
    pieces = {name: KIT_PIECES[piece] for piece, (name, _) in samples.get(R.DRUMS, {}).items()}
    r.roles = [roles_mod.Role(v, role) for v, role in sorted(role_of.items())]
    for p in r.song.notes:
        if p.sample is not None:
            p.sample.piece = pieces.get(p.sample.key, "none") if role_of.get(p.voice) == R.DRUMS else "none"
    db = store.connect(":memory:")
    store.keep(db, r)
    songs, _ = rhythm.load(db)
    db.close()
    return songs[0] if songs else None


# --- the measures: the same numbers over a written song read back and over a game's songs ---

SPAN = 32                             # bars the distinct figures are counted over (tools/slice1.py)


def tune_measures(song: rhythm.Song) -> dict:
    """The tune's numbers: chord tones on the beat, repeated notes, steps and leaps among its moves, distinct bar
    cells over SPAN bars, bars echoing an earlier bar, its range."""
    line = rhythm._line(song.notes.get(R.MELODY, []))
    if not line:
        return {}
    strong = [n for n in line if abs(n[0] - round(n[0])) < NEAR]
    on_chord = 0
    for n in strong:
        c = rhythm._chord_at(song.chords, n[0])
        if c is not None and c.root is not None and c.fit >= vocab.FIT:
            if round(n[2]) % 12 in {(c.root + i) % 12 for i in harmony.SHAPES.get(c.shape, harmony.SHAPES[""])}:
                on_chord += 1
    moves = [round(b[2] - a[2]) for a, b in zip(line, line[1:])]
    moving = [m for m in moves if m]
    cells = []
    for _, a, b, struck in rhythm.all_bars_of(song, R.MELODY):
        if struck:
            ms = [max(ns, key=lambda x: x[2])[2] for _, ns in struck]
            cells.append((tuple(float(p) for p, _ in struck), tuple(round(y - x) for x, y in zip(ms, ms[1:]))))
    heads = [h for i, w, h in rhythm.phrase_heads(song) if i is not None and h]
    theme_back = sum(1 for h in heads[1:] if h == heads[0]) / max(1, len(heads) - 1) if heads else 0.0
    live = [c for c in rhythm.melody_cells(song) if c]
    echoes_at = [i for i in range(len(live)) if live[i] in live[:i]]
    of_opening = sum(1 for i in echoes_at if live[i] in set(live[:4])) / max(1, len(echoes_at))
    return {"chord_tones": on_chord / max(1, len(strong)), "repeats": (len(moves) - len(moving)) / max(1, len(moves)),
            "steps": sum(1 for m in moving if abs(m) <= 2) / max(1, len(moving)), "leaps": sum(1 for m in moving if abs(m) >= 7) / max(1, len(moving)),
            "distinct": len(set(cells[:SPAN])), "echoes": sum(1 for i, c in enumerate(cells) if c in cells[:i]) / max(1, len(cells)),
            "range": max(n[2] for n in line) - min(n[2] for n in line),
            "theme_heads": theme_back, "theme_returns": int(theme_back > 0), "echoes_of_opening": of_opening}


def measures(song: rhythm.Song) -> dict:
    """A song's numbers, part by part: the share of bars it plays, strikes a bar, bars repeating the bar before,
    distinct bars over SPAN; the band, the form, the tune's (tune_measures)."""
    out = {"bars": len(song.bars), "parts": len(song.parts), "band": len(song.notes), "seconds": len(song.bars) * song.meter * 60.0 / song.bpm}
    for role in rhythm.PARTS:
        if role not in song.notes:
            continue
        bars = list(rhythm.all_bars_of(song, role))
        patterns = [rhythm.pattern(p for p, _ in struck) if struck else None for _, _, _, struck in bars]
        live = [p for p in patterns if p]
        if not live:
            continue
        out[role] = {"plays": len(live) / max(1, len(bars)), "strikes": statistics.mean(len(p.split()) for p in live),
                     "repeats": sum(1 for x, y in zip(live, live[1:]) if x == y) / max(1, len(live) - 1), "distinct": len(set(live[:SPAN]))}
    if R.MELODY in song.notes:
        out["tune"] = tune_measures(song)
    return out


def compose(models: dict, pack: dict, own: set, pack_name: str, seed: int, game: str = "", title: str | None = None,
            max_bars: int | None = None, loops: int = 2, reference=None, read: bool = True, fade: float = 2.0,
            min_bars: int | None = None, tail_bars: int = 0, themed: bool = False, band_returns: bool = False) -> dict:
    """One whole song: the plan, the parts written, the score (and {role: first voice}), the song read back and its
    measures; {"plan", "song", "written", "score", "first", "samples", "echo", "read", "measures"}."""
    p = plan(models, seed, game, title, max_bars, min_bars, themed=themed, band_returns=band_returns)
    kit = (pack.get("voices") or {}).get("drums") or {}
    song = song_of(p, kit)
    written = write(p, song, models, seed, reference)
    rng = random.Random(f"whole:{seed}:render")
    samples = samples_for(p, pack, own, pack_name, rng, models)
    echo = echo_of(pack.get("habits") or {}, p.bpm, rng)
    score, first = score_of(p, written, samples, loops=loops, fade=fade, echo=echo, tail_bars=tail_bars)
    out = {"plan": p, "song": song, "written": written, "score": score, "first": first, "samples": samples, "echo": echo, "read": None, "measures": None}
    if read:
        once, _ = score_of(p, written, samples, loops=1, fade=0.0, echo=echo)
        back = read_back(once, p, first, samples)
        out["read"] = back
        out["measures"] = measures(back) if back is not None else None
        if out["measures"] is not None:                      # the reader's form, heard as a player hears it: with the loop
            twice, _ = score_of(p, written, samples, loops=2, fade=0.0, echo=echo)
            looped = read_back(twice, p, first, samples)
            out["measures"]["parts"] = len(looped.parts) if looped is not None else 0
            out["measures"]["loop_heard"] = int(looped is not None and looped.loop_bar is not None)
    return out
