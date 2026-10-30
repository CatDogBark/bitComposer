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
from fractions import Fraction
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
KIT_SLOT = {"K": "kick", "S": "snare", "h": "hihat", "t": "tom", "c": "crash", "o": "rim"}   # a piece letter -> the pack kit slot its song's sample fills (round 63)
KIT_FOR = {"K": ("kick",), "S": ("snare", "rim"), "h": ("hihat", "open_hihat"), "t": ("tom", "kick"),
           "c": ("crash", "open_hihat", "hihat"), "o": ("rim", "hihat")}   # a figure's letter -> its sample, the first the kit has
DRUM_LENGTH = 1.0                     # beats a drum hit sounds at most (to the next hit on its voice otherwise)
WANTS = {R.HARMONY: 3, R.ACCOMP: 2, R.ARP: 1, R.COUNTER: 1}   # voices an upper part takes when the eight allow (one each first)
LEVELS = {R.MELODY: 0.85, R.COUNTER: 0.6, R.HARMONY: 0.5, R.ACCOMP: 0.6, R.ARP: 0.55, R.BASS: 0.8, R.DRUMS: 0.8}   # of full, by part: the
TOP_LEVEL = 0.85                      # the loudest part's level of full without a top_levels table (round 52: with one, the song's own draw;
                                      # FFVI's loudest parts sit at 0.2 to 0.4, and 0.85 had rendered 5 dB hotter than the game's songs)
TOP_SCALE = 1.0                       # the readings' level (a voice's two sides' mean over 128) to the module's note level: one since round 59,
                                      # the song's master volume carrying the mix's loudness (mix level, RENDER_BRIDGE). It had been 1.7:
                                      # THE OLD NOTE: the readings' level to the module's note level, measured: by the
                                      # converter's own sums the two scales agree (a voice at 38 a side is IT volume 38 of 64 under FFVI's
                                      # master of 63, 0.29 of full either way), but the written songs rendered 4.5 dB under FFVI's converted
                                      # songs at the readings' top level as drawn (-29.0 against -24.5 dBFS, the same player), and 5 dB over
                                      # at 0.85; 1.7 (4.6 dB) is the measured bridge, to be read again when the readings' level is understood
RENDER_BRIDGE = -21.7                 # dB: what a written song renders at (RMS dBFS over its first minute, the Song Check method) less its mix
                                      # estimate (rhythm.mix_level over the notes as scored), at a full master: measured over 20 written songs
                                      # 2026-10-29 (median -21.7 once the sample loudness read the sustain loop, quartiles -23.0 and -19.8;
                                      # -20.5 before it); the master brings estimate + bridge to the token's song's rendered loudness. Read
                                      # again if the estimate or the renderer changes.
MASTER_FLOOR = 8                      # the master volume's least value (of 127): under it a song is not a song
STRIKE_WINDOW = 0.1                   # seconds of a sample a note hears as its strike (sample_strike_and_body, heard_rms)
PANS = {R.MELODY: (0.5,), R.COUNTER: (0.6,), R.HARMONY: (0.35, 0.65, 0.5), R.ACCOMP: (0.6, 0.4), R.ARP: (0.4,), R.BASS: (0.5,),
        R.DRUMS: (0.5, 0.58)}        # the right side's share, a part's voices in turn
POOLS = {R.MELODY: "lead", R.COUNTER: "counter", R.HARMONY: "harmony", R.ARP: "arp"}   # a part's voice pool in a pack; the
BASS_POOLS = {"main": "bass_heavy", "half": "bass_medium", "minor": "bass_light"}      # accompaniment's by its motion, the bass's by its weight
SENDS = {R.MELODY, R.COUNTER, R.HARMONY, R.ACCOMP, R.ARP}   # the parts that send to the echo (score.SENDS; the accompaniment is a harmony channel there)
DEFAULTS = {"keys": "0 minor", "tempos": "120", "sizes": "3", "length_habits": "short", "form": "new", "lengths": "4",
            "balance": "bass=half drums melody=main", "drum_habits": "medium mixed", "drum_group_habits": "medium mixed",
            "bass_habits": "medium roots no-octaves", "habits": "medium mixed", "voicing_habits": "full", "motions": "block",
            "articulation": "mixed", "echo_habits": "mixed", "step_habits": "mixed", "repeat_habits": "some", "sounds": "0.8", "loops": "I",
            "levels": "0.8", "layer_levels": "0.9", "gap_sounds": "0.8", "bass_locks": "0.9", "counter_samples": "other", "counter_shares": "0.6", "part_speeds": "6", "cell_handoffs": "none",
            "chord_tones": str(writer.CHORD_ON_BEAT), "part_textures": None, "section_levels": "1.0", "top_levels": str(TOP_LEVEL), "kit_pieces": "KShtco",
            "registers": {R.BASS: "36-52", R.HARMONY: "56-72", R.ACCOMP: "56-72", R.ARP: "60-80", R.MELODY: "64-84", R.COUNTER: "60-80"}}
ENTRY_TRIES = 6                       # part_entries draws for a part before it plays a short section whole
DRUM_ENTRY_FLOOR = 2                  # the drums' entrance draw never backs off past the kit's tier (part, habit): the tier's own entrances
FORM_TRIES = 20                       # forms drawn before one longer than asked is cut
SPEED_FASTER = 30.0                   # notes a second a part_speeds draw of "faster" (past SPEED_BINS' top) is fitted at
MIN_SPAN = 2 * rhythm.REGISTER_BIN    # semitones: the narrowest register a voice is written in (two of the register word's bins)
SECOND_MEMO = False                   # a voice beside the line: its mask drawn a bar (on: the same line bar gets the same mask within a song; that
                                      # had put voices at 0.88 of the line's strikes against FFVI's 0.60, a bar at a time 0.72)
SECOND_ANY_TONE = True                # ...and takes any tone of the line's voicing but the line's, drawn a span (off: its rank's tone)
PLAN_FLOOR = 1                        # a plan's one-shot draw never backs off past the part (the first conditioning): the root of a
                                      # table keyed by part mixes every part, and under Witten-Bell a register draw reached it in a
                                      # third of draws (a counter at bass depth 8 % of the time, a bass above middle C 19 %)
PLAN_SONGS = 2                        # a finer level is used only with this many songs behind it
GRAIN_FLOOR = 2                       # the tune_grain draw never backs off past the part's density tier: the part level had given a dense tune
                                      # "on-beat" (under 0.25 of its onsets off the beat), which no dense tune of FFVI is (round 66)
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
    gap_sounds: dict = field(default_factory=dict)    # a chord part or the bass -> {only/line/second: {gap class: the share a note sounds}}
    locks: dict = field(default_factory=dict)         # the bass -> the share of the kit's accents it strikes with (bass_locks)
    levels: dict = field(default_factory=dict)        # a part -> its level as a share of the loudest part's (the balance token's field where
                                      # its song has the part; the levels table where not; the counter's from counter_shares)
    layer_levels: dict = field(default_factory=dict)  # a layered part -> its second voice's level against its line's (the balance token's
                                      # sixth field's first share where its song has the part layered; the layer_levels draw where not)
    level_from: dict = field(default_factory=dict)    # a part -> where its level came from: "balance", "levels" or "counter_shares"
    voice_levels: dict = field(default_factory=dict)  # a layered part -> the token's song's shares for every voice beyond the line, the
                                      # busiest first (the sixth field): voice j beside the line plays at entry j - 1
    layer_from: dict = field(default_factory=dict)    # a pitched part -> where its second voices' levels came from: "balance" or "layer_levels"
    top_level: float = 0.85                               # the loudest part's level of full (top_levels, round 52; TOP_LEVEL without the word)
    loudness: float | None = None                         # the balance token's song's rendered loudness, RMS dBFS (round 59): the master holds the song's own to it
    master: tuple | None = None                           # (the master volume of 127, the gain the notes took) score_of decided for the whole song: the stems take it
    section_levels: dict = field(default_factory=dict)   # a part -> [its level's multiplier a bar] (section_levels, round 48: a section's level
                                      # over the part's song level, drawn a part an own section, a repeated section copying it)
    token_samples: dict = field(default_factory=dict)   # a part -> the balance token's song's sample for it, the pack's id (the eighth field,
                                      # round 60): samples_for takes it where the pack holds the sample, the part_samples draw else
    layer_samples: dict = field(default_factory=dict)   # a layered part -> the token song's sample for each voice beyond the line (round 65)
    layer_shares: dict = field(default_factory=dict)    # a layered part -> each voice beyond the line's notes over the line's (round 65): the
                                      # mask word is drawn under its class (sparse, half, full)
    token_habits: dict = field(default_factory=dict)    # a part -> the balance token's song's habit for it (the ninth field, round 62): the song's
                                      # density tiers come together; the habits draws stand where the token lacks one
    kinds: dict = field(default_factory=dict)         # the counter -> the balance token's song's kind for it, same or other (the seventh field,
                                      # round 39): the counter_samples draw is made and overwritten where the token has it
    speeds: dict = field(default_factory=dict)        # a pitched part -> its fastest bar, notes a second (part_speeds): what its sample is fitted to
    bounds: dict = field(default_factory=dict)        # a part or "part:second" -> the register it is written in: where the game plays the sample
                                      # chosen for it (the ranges word's drawn range, bound_of), set by samples_for before the writing (round 34)

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
                "band": self.band, "weights": self.weights, "textures": self.textures, "plays": self.plays, "top_level": self.top_level, "loudness": self.loudness, "token_samples": self.token_samples, "token_habits": self.token_habits, "layer_samples": self.layer_samples, "layer_shares": self.layer_shares,
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
    beside: set = field(default_factory=set)   # the part's voices written beside a line under the span rule (their pitch the voice words'
                                      # draw, folded into the line's register widened by the layer offset): kept within the register
                                      # the game plays their sample in (the sample chosen before the writing, round 34; its drawn range is the voice's register)


COUNTER_MASK_FLOOR = 5                # counter_figures' draw never backs off below the tune's onset count with the counter's weight in front
                                      # (part, weight, feel, tempo, onsets; round 47)
MASK_FLOOR = 5                        # second_figures' draw never backs off below the line's onset count (part, feel, tempo, onsets): a mask is
                                      # read onset by onset, and one from a shorter line read around a longer one had filled it


def _draw(models: dict, name: str, context: tuple, rng: random.Random, log: list | None = None, floor_k: int | None = None,
          floor_songs: int = 0) -> str:
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
    return t.draw(tuple(context), rng, floored=False, floor_k=PLAN_FLOOR if floor_k is None else floor_k, min_songs=PLAN_SONGS, floor_songs=floor_songs)


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


def plan_texture(models: dict, parts: list, band: list, rng: random.Random, log: list, defer=(), tier: str = rhythm.NO_TIER) -> tuple[list, dict]:
    """Which parts sound in each bar: a texture a part of the form, drawn
    from the part-textures table against the band (ALL, or the band's
    parts that rest: "no drums melody"; given the part's place in the form
    and the part before's outcome), a repeated part keeping its texture;
    a bar's texture is its part's. Then, with the part_entries word (round
    46), each part the section has enters and leaves where the word says
    inside it (so many bars after its start, so many before its end): FFVI's
    parts join inside a section more often than at its edge (61 to 45),
    and a texture a section had let them join only at its lines. A
    repeated part copies the bars, entrances and all. The parts in `defer`
    draw no entrance here (the drums': drawn under the kit's tier once the
    kit's habit is known, drum_entrances); `tier` is the kit's density tier
    the textures are drawn under (round 59; NO_TIER without drums). Returns
    the textures a bar and each part's bars."""
    total = parts[-1][0] + parts[-1][1]
    textures = [None] * total
    entries = []
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
                outcome = table.draw((rhythm.ARRANGEMENT, tier, form, previous), rng, floored=False)
                resting = set(outcome[3:].split()) if outcome.startswith("no ") else set()
                t = " ".join(r for r in band if r not in resting)
                if t:
                    break
            else:
                t = " ".join(band)
        textures[bar:bar + n] = [t] * n
        previous = outcome
        if "part_entries" in models:                        # where inside the section each present part enters and leaves (round 46)
            entrances(models, parts, i, textures, [r for r in t.split() if r not in defer], rhythm.NO_TIER, rng, entries, PLAN_FLOOR)
    plays = {role: [role in (textures[k] or "").split() for k in range(total)] for role in band}
    log.append("textures " + " | ".join(f"{p[3]}: {textures[p[0]]}" for p in parts))
    if entries:
        log.append("entrances (part_entries): " + "; ".join(entries))
    return textures, plays


def entrances(models: dict, parts: list, i: int, textures: list, roles: list, tier: str, rng: random.Random, entries: list, floor_k: int) -> None:
    """The entrance and exit of each of `roles` inside section i, drawn from
    the part_entries word under the part, `tier` (the kit's for the drums,
    NO_TIER else), the section's place and length, and cut from `textures`
    in place (ENTRY_TRIES draws for one the section can hold, else whole);
    each cut described in `entries`."""
    bar, n = parts[i][0], parts[i][1]
    place, length = rhythm.form_place_of(i, len(parts)), rhythm.section_length(n)
    for role in roles:
        for _ in range(ENTRY_TRIES):
            drawn = models["part_entries"].draw((role, tier, place, length), rng, floored=False, floor_k=floor_k)
            enters, leaves = rhythm.entry_of(drawn)
            if enters + leaves < n:
                break
        else:
            continue                                        # no draw fits a section this short: the part plays it whole
        if enters or leaves:
            for k in list(range(bar, bar + enters)) + list(range(bar + n - leaves, bar + n)):
                textures[k] = " ".join(r for r in textures[k].split() if r != role)
            entries.append(f"{role} " + " ".join(x for x in (f"enters {enters} in" if enters else "", f"leaves {leaves} before the end of" if leaves else "") if x) + f" {parts[i][3]}")


def drum_entrances(models: dict, parts: list, textures: list, band: list, tier: str, rng: random.Random, log: list) -> tuple[list, dict]:
    """The drums' entrances and exits, section by section, under the kit's
    density tier (round 59: the word by part, place and length alone had a
    dense kit leave eight bars before a section's end, where FFVI's dense
    kits play 101 sections of 106 whole and its sparse kits 20 of 27; the
    tier's own entrances alone, DRUM_ENTRY_FLOOR), a repeated section
    copying its source. Returns the textures and every part's bars."""
    entries = []
    for i, (bar, n, of, _) in enumerate(parts):
        if of is not None:
            src = parts[of][0]
            textures[bar:bar + n] = textures[src:src + n]
        elif R.DRUMS in (textures[bar] or "").split():
            entrances(models, parts, i, textures, [R.DRUMS], tier, rng, entries, DRUM_ENTRY_FLOOR)
    if entries:
        log.append("entrances (part_entries, the drums by the kit's tier): " + "; ".join(entries))
    total = parts[-1][0] + parts[-1][1]
    return textures, {role: [role in (textures[k] or "").split() for k in range(total)] for role in band}


def plan_section_levels(models: dict, parts: list, band: list, plays: dict, rng: random.Random, log: list) -> dict:
    """Each part's level a bar as a multiplier of its song level (section_levels, round 48): drawn a part an own section
    it plays in, by the part and the section's place in the form; a repeated section copies its source's; the drums
    keep one level (the word counts the pitched parts). Drawn on an own stream (`whole:{seed}:levels`): drawn on the
    plan's, the new draws had shifted every habit, register and sample drawn after them, and a before-and-after of one
    seed compared two different songs (Song Check 40's first cut). Returns {part: [multiplier a bar]}; logs the
    sections off 1.0."""
    total = parts[-1][0] + parts[-1][1]
    out = {role: [1.0] * total for role in band if role != R.DRUMS}
    n_parts = len(parts)
    said = []
    for i, (bar, n, of, letter) in enumerate(parts):
        for role in out:
            if of is not None:
                src = parts[of][0]
                out[role][bar:bar + n] = out[role][src:src + n]
                continue
            if not any(plays[role][bar:bar + n]):
                continue
            ratio = float(_draw(models, "section_levels", (role, rhythm.form_place_of(i, n_parts)), rng, log))
            if abs(ratio - 1.0) > 1e-9:
                out[role][bar:bar + n] = [ratio] * n
                said.append(f"{role} {ratio:.1f} in {letter}")
    if said:
        log.append("levels by section (section_levels): " + "; ".join(said))
    return out


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
    _plan_counter(models, p, rng)
    _plan_speeds(models, p, rng)
    _plan_sounds(models, p, rng)
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
    band, weights, layout, shares, counts, token_levels, token_layers, token_kinds, token_samples, token_habits = [], {}, {}, {}, {}, {}, {}, {}, {}, {}
    token_kit, token_layer_samples, token_layer_shares = {}, {}, {}
    token_class, token_top, token_loud = None, None, None
    for token in _draw(models, "balance", (rhythm.ARRANGEMENT,), rng, log).split():
        role, _, rest = token.partition("=")
        if role == "tempo":                                 # the token's song's tempo class (round 54), not a part
            token_class = rest
            continue
        if role == "top":                                   # the token's song's loudest part, of full (round 59), not a part
            token_top = float(rest)
            continue
        if role == "loud":                                  # the token's song's rendered loudness in dBFS (round 59), not a part
            token_loud = float(rest)
            continue
        band.append(role)
        if rest:
            fields = rest.split(":")
            if fields[0]:
                weights[role] = fields[0]
            if len(fields) > 1 and "-" in fields[1]:        # the song's layout, note lengths, voices and levels a part come with its balance
                lo, hi = fields[1].split("-")
                layout[role] = (int(lo), int(hi))
            if len(fields) > 2 and fields[2]:
                shares[role] = float(fields[2])
            if len(fields) > 3 and fields[3]:
                counts[role] = int(fields[3])
            if len(fields) > 4 and fields[4]:
                token_levels[role] = float(fields[4])
            if len(fields) > 5 and fields[5]:               # the voices beyond the line, the busiest first, each over the line's level; since
                parts_ = [x.split("@") for x in fields[5].split("/")]   # round 65 with each one's sample and its notes over the line's
                token_layers[role] = [float(x[0]) for x in parts_]
                if any(len(x) > 1 and x[1] for x in parts_):
                    token_layer_samples[role] = [x[1] if len(x) > 1 else "" for x in parts_]
                if any(len(x) > 2 for x in parts_):
                    token_layer_shares[role] = [float(x[2]) if len(x) > 2 and x[2] else 1.0 for x in parts_]
            if len(fields) > 6 and fields[6]:               # the counter's kind: on the tune's sample or another (round 39)
                token_kinds[role] = fields[6]
            if len(fields) > 7 and fields[7] and role == R.DRUMS:   # the song's kit (round 63): a piece letter and its sample, by the comma
                token_kit = dict(x.split("=") for x in fields[7].split(",") if "=" in x)
            elif len(fields) > 7 and fields[7]:             # the part's own sample (round 60): the song's instruments with its levels
                token_samples[role] = fields[7]
            if len(fields) > 8 and fields[8]:               # the part's habit (round 62): the song's density tiers together
                token_habits[role] = fields[8].replace("+", " ")
    log.append("band " + " ".join(f"{r}={weights[r]}" + (f" {layout[r][0]}-{layout[r][1]}" if r in layout else "") + (f" x{counts[r]}" if r in counts else "")
                                  if r in weights else r for r in band))
    if token_class and rhythm.band(bpm) != token_class:     # the band's own pace (round 54): the tempo drawn again under the token's class, on
        was = bpm                                           # an own stream so no other draw moves
        bpm = float(_draw(models, "tempos", ("song", token_class), random.Random(f"whole:{seed}:tempo"), log))
        tempo = rhythm.band(bpm)
        log.append(f"tempo {was:.0f} BPM is outside the band's class ({token_class}): {bpm:.0f} BPM drawn under it")
    names, chords = plan_chords(models, parts, loop_bar, tonic, mode, rng, log)
    drum_habit = (token_habits.get(R.DRUMS) or _draw(models, "drum_habits", (R.DRUMS,), random.Random(f"whole:{seed}:drum-habit"), log)) if R.DRUMS in band else None   # before the
    tier = str(drum_habit).split()[0] if drum_habit else rhythm.NO_TIER   # textures, on an own stream: the kit's tier conditions them (round 59)
    textures, plays = plan_texture(models, parts, band, rng, log, defer=(R.DRUMS,), tier=tier)
    silent = [r for r in band if not any(plays[r])]
    if silent:
        log.append(f"never in a texture, left out of the band: {silent}")
        band = [r for r in band if r not in silent]
        plays = {r: plays[r] for r in band}
    if token_top is not None:                               # the song's own top with its own levels (round 59)
        top_level = min(1.0, TOP_SCALE * token_top)
        log.append(f"top level from the balance: {token_top:.2f} of full, {top_level:.2f} in the module")
    else:
        top_level = (min(1.0, TOP_SCALE * float(_draw(models, "top_levels", (rhythm.ARRANGEMENT,), random.Random(f"whole:{seed}:top"), log)))
                     if "top_levels" in models_or_empty(models) else TOP_LEVEL)
    registers, sounds, habits, extras = {}, {}, {}, {}
    for role in band:
        if role == R.DRUMS:
            habits[role] = drum_habit
            extras[role] = {"".join(g): _draw(models, "drum_group_habits", ("drums-" + "".join(g), habits[role]), rng, log) for g in rhythm.DRUM_GROUPS}
            if token_kit:                                   # the token song's own kit (round 63): its pieces are these, its samples theirs
                extras[role]["pieces"] = "".join(x for x in rhythm.LETTERS.values() if x in token_kit)
                extras[role]["kit"] = token_kit
                log.append(f"kit from the balance: {extras[role]['pieces']} (" + ", ".join(f"{k} {v}" for k, v in token_kit.items()) + ")")
            elif "kit_pieces" in models_or_empty(models):    # the pieces the song's kit strikes (round 58), on an own stream
                extras[role]["pieces"] = _draw(models, "kit_pieces", (R.DRUMS, str(habits[role]).split()[0]), random.Random(f"whole:{seed}:kit"), log,
                                               floor_k=2)   # the tier's own kits alone (seven medium songs, seven kits: the smoothing had handed a
                                                            # medium song a dense kit, and the kit-first drums table then wrote the dense kit's bars)
                log.append(f"kit pieces (kit_pieces): {extras[role]['pieces']}")
            continue
        if role in layout:                                  # the song's own layout; the tables a part at a time where the pack has none
            registers[role] = layout[role]
        else:
            low, high = _draw(models, "registers", (role,), rng, log).split("-")
            registers[role] = (int(low), int(high))
        sounds[role] = shares[role] if role in shares else float(_draw(models, "sounds", (role,), rng, log))
        weight = weights.get(role, "half")
        if role in token_habits:                            # the token song's own habit for the part (round 62), the draw where it lacks one
            habits[role] = token_habits[role]
        elif role == R.BASS:
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
                            "repeat_rate": _maybe(models, "repeat_rates", (R.MELODY,), rng),
                            "grain": (_draw(models, "tune_grain", (role, str(habits[role]).split()[0]), random.Random(f"whole:{seed}:grain:{role}"), log, floor_k=GRAIN_FLOOR)
                                      if "tune_grain" in models_or_empty(models) else None)}   # an own stream, floored at the tier (round 66)
    if R.DRUMS in band and "part_entries" in models_or_empty(models):   # the drums' entrances under the kit's tier (round 59), on an own stream
        textures, plays = drum_entrances(models, parts, textures, band, str(habits[R.DRUMS]).split()[0], random.Random(f"whole:{seed}:entries"), log)
    section_levels = (plan_section_levels(models, parts, band, plays, random.Random(f"whole:{seed}:levels"), log)   # an own stream: drawn on the
                      if "section_levels" in models_or_empty(models) else {})                                  # plan's, every later draw had shifted
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
            if of is not None or n < rhythm.PHRASE:         # a section shorter than a phrase (a one-bar pickup) carries no phrase letter: it
                continue                                    # can hold no theme (round 62: Whole 112's one-bar A section had made a one-bar hook)
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
    gap_sounds = {role: {voice: {g: float(_draw(models, "gap_sounds", (role, voice, g), rng, log)) for _, g in rhythm.GAP_CLASSES}
                         for voice in ("only", "line", "second")}
                  for role in band if role in rhythm.UPPER + (R.BASS,)} if "gap_sounds" in models_or_empty(models) else {}
    locks = {R.BASS: float(_draw(models, "bass_locks", (R.BASS,), rng, log))} if R.BASS in band and R.DRUMS in band else {}
    levels = {role: float(_draw(models, "levels", (role,), rng, log)) for role in band}
    layer_levels = {role: float(_draw(models, "layer_levels", (role,), rng, log)) for role in band if role != R.DRUMS}
    # the band's levels as one unit (round 32): a part's level is the balance token's where its song has the part, the
    # `levels` draw above where not. The draws stay in place and are overwritten: removing them would shift every draw
    # after them on this stream (the layer levels, a themed plan drawn again, the counter's words) and so the songs known.
    level_from = {role: "balance" if role in token_levels else "levels" for role in band}
    levels.update({role: token_levels[role] for role in band if role in token_levels})
    if token_levels:
        top = max(levels.values())
        log.append("levels from the balance: " + " ".join(f"{r}={levels[r]:.1f}" for r in band if level_from[r] == "balance")
                   + ("; drawn from levels: " + " ".join(f"{r}={levels[r]:.1f}" for r in band if level_from[r] == "levels") if "levels" in level_from.values() else "")
                   + "; the loudest " + "/".join(r for r in band if levels[r] >= top - 1e-9))
    # the second voices' levels with the band's (round 33): a voice beside the line plays at the token's song's share of the
    # line's for that voice (the sixth field, one share a voice beyond the line, the busiest first) where the token's song
    # has the part with two voices or more; the `layer_levels` draw above where not (a token without the field, or a part
    # the token's song has as one voice). The draws stay in place as the `levels` draws do, and the first share overwrites
    # the draw's result, so the stack of a line and its second voice is one song's.
    layer_from = {role: "balance" if role in token_layers else "layer_levels" for role in layer_levels}
    voice_levels = {role: list(token_layers[role]) for role in layer_levels if role in token_layers}
    layer_levels.update({role: token_layers[role][0] for role in voice_levels})
    if token_layers:
        layered = [r for r in band if voices.get(r, 1) >= 2 and r in layer_levels]
        log.append("second voices from the balance: " + " ".join(f"{r}={'/'.join(f'{x:.1f}' for x in voice_levels[r])}" for r in band if r in voice_levels)
                   + ("; drawn from layer_levels: " + " ".join(f"{r}={layer_levels[r]:.1f}" for r in layered if layer_from[r] == "layer_levels")
                      if any(layer_from[r] == "layer_levels" for r in layered) else ""))
    return Plan(seed, game, title or f"Whole {seed}", tonic, mode, bpm, parts, loop_bar, names, chords, band, weights, textures, plays,
                registers, sounds, habits, extras, voices, log, feel=feel, levels=levels, layer_levels=layer_levels, gap_sounds=gap_sounds, locks=locks,
                level_from=level_from, voice_levels=voice_levels, layer_from=layer_from, kinds=token_kinds, token_samples=token_samples, token_habits=token_habits, layer_samples=token_layer_samples, layer_shares=token_layer_shares, section_levels=section_levels,
                top_level=top_level, loudness=token_loud)


def _plan_speeds(models: dict, p: Plan, rng: random.Random) -> None:
    """Each pitched part's fastest bar (part_speeds, round 34), drawn once a song after every other plan draw under the part
    and its habit's density tier: what its sample is fitted to for speed before the part is written. The fit had read the
    speed off the written notes, so a sample was chosen after the writing and a voice's register could not come from the
    sample it plays; three rules and a fold had covered that seam (the span a voice beside a line wrote in, the bass's
    floor plus REACH, the reach check, round 32a's fold to the sample's widest band)."""
    for role in p.band:
        if role == R.DRUMS or role not in p.habits:
            continue
        tier = str(p.habits[role]).split()[0]
        drawn = _draw(models, "part_speeds", (role, tier), rng, p.log, floor_k=2) if "part_speeds" in models_or_empty(models) else DEFAULTS["part_speeds"]
        p.speeds[role] = SPEED_FASTER if drawn == "faster" else float(drawn)   # floored at the part and tier: a dense accompaniment had drawn 2 a second
                                                                           # from the coarser level's mass, a value FFVI's dense accompaniments never have


def _plan_sounds(models: dict, p: Plan, rng: random.Random) -> None:
    """The share of its gap a note sounds, drawn again under the part's speed class (gap_sounds: part, voice, speed, gap; round
    35) once the part's speed is drawn, after every other plan draw. FFVI's string pad played fast sounds a fifth to a third
    of its gap (the battle tremolo), played slow nearly all of it; one share by the gap alone had put Whole 02's fast
    arpeggio between the two, a staccato pad neither held nor tremolo. The draw in _plan_once stays in the stream."""
    if "gap_sounds" not in models_or_empty(models) or not p.speeds:
        return
    for role in list(p.gap_sounds):
        if role not in p.speeds:
            continue
        tier = rhythm.speed_tier(p.speeds[role])
        p.gap_sounds[role] = {voice: {g: float(_draw(models, "gap_sounds", (role, voice, tier, g), rng, p.log)) for _, g in rhythm.GAP_CLASSES}
                              for voice in ("only", "line", "second")}


def _plan_counter(models: dict, p: Plan, rng: random.Random) -> None:
    """The counter-line beside the tune (round 29), drawn once a song after every other plan draw: on the tune's sample or
    another (counter_samples: the kind its voice words are drawn under, and its sample at the rendering), and its level
    as a share of the song's loudest part's under the band the tune's own `levels` draw falls in (counter_shares, round
    31: FFVI's counter is never above the loudest part, and its counters louder than the tune sit on quiet tunes; the
    counter's level over the tune's drawn apart from the tune's share and multiplied into it had put Whole 28's counter
    at 1.05 of the loudest). The share replaces the counter's own `levels` draw where the balance token's song has no
    counter level (round 32: the band's levels are the token's as one unit; the token's counter level stands, and the
    `counter_shares` draw is still made so the stream is as it was). Its kind, the tune's sample or another, is the
    token's too where the token has it (round 39: the level one song's and the kind another's had put The Serpent
    Trench's descant level on a same-sample doubling in Whole 33), the `counter_samples` draw made and overwritten
    the same way. Drawn here, after `plan`'s retries, not inside
    `_plan_once`: a themed plan is drawn again on the same stream when its tune cannot come back, and two draws inside
    the attempt had shifted every draw of the next one (Whole 14's band, key and form changed)."""
    if R.COUNTER not in p.band or R.MELODY not in p.band:
        return
    have = models_or_empty(models)
    x = p.extras[R.COUNTER]
    if "counter_samples" in have:
        x["sample"] = _draw(models, "counter_samples", (R.COUNTER,), rng, p.log)
        x["sample_from"] = "counter_samples"
    if R.COUNTER in p.kinds:                                # the token's song's kind stands with its level (round 39): the draw is made all the same
        x["sample"] = p.kinds[R.COUNTER]
        x["sample_from"] = "balance"
    if "counter_shares" in have:
        tune = p.levels.get(R.MELODY, float(DEFAULTS["levels"]))
        drawn = float(_draw(models, "counter_shares", (R.COUNTER, rhythm.tune_share_band(tune)), rng, p.log))
        if p.level_from.get(R.COUNTER) == "balance":
            x["level"] = p.levels[R.COUNTER]
        else:
            x["level"] = p.levels[R.COUNTER] = drawn
            p.level_from[R.COUNTER] = "counter_shares"
    p.log.append(f"counter beside the tune: {x.get('sample', 'any')} sample" + (" with the band's" if x.get("sample_from") == "balance" else "")
                 + (f", level {x['level']:.1f} of the loudest " + ("with the band's, the balance's" if p.level_from.get(R.COUNTER) == "balance"
                                                                   else f"under the tune's {p.levels[R.MELODY]:.1f}") if "level" in x else ""))


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
    bar at a time; in every other bar of the tune, the parts the tune_doubling table draws (round 44: FFVI doubles the
    tune's half-bar cells at once 0.24, the written songs 0.03 with the theme cell alone doubled). Returns a log line a
    bar doubled."""
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
        if not c:
            continue
        if c == theme:
            drawn = _draw(models, "theme_doubling", ("theme", "statement" if k in theme_bars else "later"), rng)
        elif "tune_doubling" in models:                     # any other bar of the tune, doubled as FFVI doubles it (round 44)
            drawn = _draw(models, "tune_doubling", ("tune", "other"), rng)
        else:
            continue
        a, b = song.bars[k]
        bar_notes = [n for n in tune if a - rhythm.NEAR <= n[0] < b - rhythm.NEAR]
        for token in drawn.split():
            role, _, off = token.partition(":")
            if role not in plan.band or role not in written or role == R.MELODY or not off or not bar_notes:
                continue
            low, high = plan.bounds.get(role, plan.registers.get(role, (24, 100)))   # where the game plays the part's sample (round 34)
            copied = []
            for t, u, m, _ in bar_notes:
                p = m + int(off)
                while p < low:
                    p += 12
                while p > high:
                    p -= 12
                copied.append((t, u, float(p), 0))
            _replace_bars(written[role], song, role, a, b, copied)
            log.append(f"bar {k}: the {role} doubles the {'theme' if c == theme else 'tune'}'s cell ({int(off):+d})")
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
        low, high = plan.bounds.get(carrier, plan.registers.get(carrier, (24, 100)))   # where the game plays the carrier's sample (round 34)
        octaves = round(((low + high) / 2 - statistics.median(m for _, _, m, _ in theme_notes)) / 12)
        copied = [(t + shift, u + shift, float(min(high, max(low, m + 12 * octaves))), 0) for t, u, m, _ in theme_notes if t + shift < b - rhythm.NEAR]
        _replace_bars(written[carrier], song, carrier, a, b, copied)
        log.append(f"bar {w[0]}: the {carrier} carries the theme phrase ({12 * octaves:+d})")
    return log


def hand_off_cells(plan: Plan, song: rhythm.Song, written: dict, models: dict, rng: random.Random) -> list:
    """The tune's half-bar cells taken up by the band (cell_handoffs, round 37): for each cell of the written tune, the
    word draws which other part plays it how many bars on (or none), under the song's echo habit and the cell's place
    (theme or other); where that part does not already play the cell later, its line's half bar there is replaced by
    the cell, re-rooted on that bar's chord in the part's own register (writer.cell_pitches), the tune's note lengths
    kept to the half. FFVI's themed songs hand half their tune's half-bar cells to another part later (all songs 0.34);
    the written songs had 0.05, each part faithful to its own word and none to the theme. Returns a log line a hand-off."""
    if R.MELODY not in written or "cell_handoffs" not in models_or_empty(models):
        return []
    tune = sorted(rhythm._line([(a, b - a, m, 0) for a, b, m, v in written[R.MELODY].notes if v == 0]))
    cells = rhythm.half_cells(tune, song.bars)
    if not any(cells):
        return []
    x = plan.extras.get(R.MELODY, {})
    theme_bars = set(x.get("theme_bars") or []) | {k for r in (x.get("returns") or []) for k in r.get("bars", [])}
    scale = {(plan.tonic + i) % 12 for i in harmony.MODES["major" if plan.mode == "major" else "natural_minor"]}
    log, taken = [], set()
    lines = {}
    for role in rhythm.HANDOFF_PARTS:
        if role in written and role in plan.band:
            lines[role] = lambda role=role: sorted(rhythm._line([(a, b - a, m, 0) for a, b, m, v in written[role].notes if v == 0]))
    for i, c in enumerate(cells):
        if not c:
            continue
        bar = i // 2
        drawn = _draw(models, "cell_handoffs", (R.MELODY, x.get("echo", "mixed"), "theme" if bar in theme_bars else "other"), rng)
        if drawn == "none" or " " not in drawn:
            continue
        role, _, far = drawn.partition(" ")
        if role not in lines or far == "far":
            continue
        target = bar + int(far)
        if target >= len(song.bars) or not (target < len(plan.plays[role]) and plan.plays[role][target]) or (role, target, i % 2) in taken:
            continue
        others = rhythm.half_cells(lines[role](), song.bars)
        if any(oc and oc[2] == c[2] for oc in others[2 * (bar + 1):]):   # the part plays the cell later already
            continue
        a_t, b_t = song.bars[target]
        lo, hi = (a_t, (a_t + b_t) / 2) if i % 2 == 0 else ((a_t + b_t) / 2, b_t)
        chord = rhythm._chord_at(song.chords, lo)
        root = chord.root if chord is not None and chord.root is not None else plan.tonic
        source = rhythm._chord_at(song.chords, c[0])
        source_root = source.root if source is not None and source.root is not None else plan.tonic
        bound = plan.bounds.get(role, plan.registers.get(role, (24, 100)))
        before = [n for n in written[role].notes if n[3] == 0 and n[0] < lo - rhythm.NEAR]
        previous = before[-1][2] if before else None
        pitches = writer.cell_pitches(c[4], source_root, root, scale, bound, previous)
        starts = [lo + pos for pos in c[3]]
        ends = [min(hi, s_ + (t_ - c[0]) - 0.0) for s_, t_ in zip(starts, [n[0] + n[1] for n in tune if c[0] - rhythm.NEAR <= n[0] < c[1] - rhythm.NEAR])]
        copied = [(s_, max(s_ + 0.05, e_), float(m), 0) for s_, e_, m in zip(starts, ends, pitches)]
        _replace_span(written[role], song, role, lo, hi, copied)
        taken.add((role, target, i % 2))
        log.append(f"bar {target}: the {role} takes up the tune's cell from bar {bar} ({far} on)")
    return log


def _replace_span(part, song: rhythm.Song, role: str, a: float, b: float, copied: list) -> None:
    """The part's LINE voice's notes in [a, b) replaced by `copied` [(start, end, midi, 0)], the other voices kept, in the
    written part and the song."""
    inside = lambda n: a - rhythm.NEAR <= n[0] < b - rhythm.NEAR and n[3] == 0   # noqa: E731
    gone = {(round(n[0], 3), int(round(n[2]))) for n in part.notes if inside(n)}
    part.notes[:] = sorted([n for n in part.notes if not inside(n)] + copied, key=lambda n: n[0])
    song.notes[role] = sorted([n for n in song.notes.get(role, []) if (round(n[0], 3), int(round(n[2]))) not in gone]
                              + [(t, u - t, m, role) for t, u, m, _ in copied], key=lambda n: n[0])


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
    pieces = plan.extras.get(R.DRUMS, {}).get("pieces")     # the pieces the song's kit strikes (kit_pieces, round 58); every piece without the word
    if pieces:
        kit_letters &= set(pieces)
    if R.DRUMS in plan.band and kit_letters:
        if "drums" in models:                               # the kit as one figure: its bars repeat and vary together, as a kit's do
            groups = {tuple(rhythm.LETTERS.values()): models["drums"]}
        else:                                               # a pack with the groups alone: each its own habit and rests
            groups = {g: models[name] for g in rhythm.DRUM_GROUPS if (name := "drums-" + "".join(g)) in models and set(g) & kit_letters}
        if groups:
            group_habits = {g: (plan.habits[R.DRUMS] if len(g) > 3 else plan.extras.get(R.DRUMS, {}).get("".join(g)) or plan.habits[R.DRUMS]) for g in groups}
            # until round 58 the one-letter groups' own habits capped their hits in the kit's draw (writer.group_caps): a kit drawn as one
            # figure is one song's bar, hat and all, and another song's "sparse hat" cutting it had left a dense kit at 8 hits a bar
            # against the game's 12.8; the song's pieces (kit_pieces) now say which sounds the kit has at all
            kit_value = "".join(x for x in rhythm.LETTERS.values() if x in kit_letters)   # the kit's pieces: the kit figure is drawn from songs with this kit
            hits, figures = writer.drums(song, groups, random.Random(f"{seed}:drums"), habit=group_habits, free=True, plays=plan.plays[R.DRUMS], kit_value=kit_value)
            by_voice, notes, dropped = {}, [], Counter()
            for t, letter in hits:
                if letter not in kit_letters:               # a piece the song's kit does not strike (kit_pieces)
                    dropped[letter] += 1
                    continue
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
                                                              + (f"; pieces {''.join(sorted(kit_letters, key=list(rhythm.LETTERS.values()).index))}")
                                                              + (f"; dropped (not in the kit) {dict(dropped)}" if dropped else "")])
    if R.BASS in plan.band and "bass" in models:
        # the bass sits on the kit's accents (two pieces together) at the game's share (bass_locks): FFVI's on 0.94 of them;
        # locked to the whole planned band it had met the threshold in no bar, written second with two drum voices to hand
        lock = {k: (ps, set()) for k, ps in rhythm.kit_accents(song.notes.get(R.DRUMS, []), song.bars, song.division).items()} if R.BASS in plan.locks else locks_of(song, {R.BASS}, plan)
        lock_share = plan.locks.get(R.BASS, 1.0)
        layered = plan.voices.get(R.BASS, 1) >= 2 and layer_of(plan.extras.get(R.BASS))[0] == "apart"
        sounds_line = float(_draw(models, "layer_sounds", (R.BASS, "line"), random.Random(f"{seed}:bass:line sounds"))) if layered and "layer_sounds" in models else plan.sounds[R.BASS]
        gs = plan.gap_sounds.get(R.BASS)                    # the share a note sounds by its gap (gap_sounds), the one share without it
        shared_bass = {}                                    # the line's notes, for a second voice following it
        notes, figures = writer.bass(song, models["bass"], random.Random(f"{seed}:bass"), habit=plan.habits[R.BASS], key=key, lock=lock,
                                     free=True, plays=plan.plays[R.BASS], register=plan.bounds.get(R.BASS, plan.registers[R.BASS])[0],
                                     sounds=gs["line" if layered else "only"] if gs else sounds_line, shared=shared_bass, lock_share=lock_share,
                                     ceiling=plan.bounds.get(R.BASS, plan.registers[R.BASS])[1])
        song.notes[R.BASS] = [(a, b - a, m, "bass") for a, b, m in notes]
        line = [(a, b, m, 0) for a, b, m in notes]
        log = [f"habit {plan.habits[R.BASS]}, register {plan.bounds.get(R.BASS, plan.registers[R.BASS])}, {sum(1 for f in figures if f != writer.REST)} bars written, "
               f"{len(notes)} notes; " + (f"on the kit's accents in {len(lock)} bars at {lock_share:.1f}" if R.BASS in plan.locks else f"locked to the band in {len(lock)} bars")]
        layer = layer_of(plan.extras.get(R.BASS))
        beside_bass = set()
        if plan.voices.get(R.BASS, 1) >= 2 and layer[0] == "apart":   # a second bass line of its own (FFVI's layered basses are all apart)
            _, offset, density = layer
            rng2 = random.Random(f"{seed}:bass:second")
            habit2 = habit_near(models, R.BASS, rhythm.band(plan.bpm), plan.weights.get(R.BASS, "half"), random.Random(f"{seed}:bass:second habit"),
                                plan.habits[R.BASS], density, table="bass_habits")
            given = None
            if "second_figures" in models:                  # the second voice's bar as a mask over the line's onsets (which it strikes with,
                line_pat = [f if f == writer.REST else rhythm.pattern(Fraction(t.partition(":")[0]) for t in rhythm._tokens(f)) for f in figures]
                masks = [p if p == writer.REST else _draw(models, "second_figures", (R.BASS, layer_class(plan, R.BASS), plan.feel, rhythm.band(plan.bpm), str(len(p.split())), p), rng2, floor_k=MASK_FLOOR, floor_songs=PLAN_SONGS)
                         for p in line_pat]                 # plus its own), drawn a bar as the chord parts' are (round 20): one draw a line
                                                            # pattern had given a whole song the doubling mask where FFVI's slap fills half its bars
                given = [writer.mask_figure(f, m) for f, m in zip(figures, masks)]
            sounds2 = float(_draw(models, "layer_sounds", (R.BASS, "second"), rng2)) if "layer_sounds" in models else plan.sounds[R.BASS]
            floor2 = max(24, plan.registers[R.BASS][0] + offset)
            bound2 = plan.bounds.get(f"{R.BASS}:second", (floor2, floor2 + writer.BESIDE_SPAN))   # where the game plays its sample (round 34)
            notes2, figures2 = writer.bass(song, models["bass"], rng2, habit=habit2, key=key, lock=locks_of(song, {R.BASS}, plan),
                                           free=True, plays=plan.plays[R.BASS], register=bound2[0],
                                           sounds=gs["second"] if gs else sounds2, figures=given, shared=shared_bass,
                                           kind=layer_of(plan.extras.get(R.BASS))[0], models=models, ceiling=bound2[1])
            song.notes[R.BASS] += [(a, b - a, m, "bass") for a, b, m in notes2]
            line += [(a, b, m, 1) for a, b, m in notes2]
            figures = [f"{f} || {g}" for f, g in zip(figures, figures2)]
            log.append(f"a second line apart: register {bound2} ({offset:+d}), habit {habit2} ({density}), sounds {sounds2:.1f}; "
                       f"{sum(1 for f in figures2 if f != writer.REST)} bars, {len(notes2)} notes" + ("; its figures drawn under the line's" if given else ""))
            if layer[0] in writer.VOICE_KINDS and "voice_intervals" in models and "voice_moves" in models:
                beside_bass = {1}                           # its pitch drawn beside the line, within its sample's register (writer.bass)
        written[R.BASS] = Part(R.BASS, line, figures, log, beside=beside_bass)
    tempo = rhythm.band(plan.bpm)
    for role in rhythm.UPPER:
        if role not in plan.band or not all(k in models for k in ("rhythm", "voicings")):
            continue
        n = plan.voices[role]
        layers = layers_of(plan, role)
        low, high = plan.bounds.get(role, plan.registers[role])   # where the game plays the line's sample (round 34)
        sounds = harness.UPPER_SOUNDS.get(role) or plan.sounds[role]
        if layers and "layer_sounds" in models:               # a layered part's line takes its own note lengths
            sounds = float(_draw(models, "layer_sounds", (role, "line"), random.Random(f"{seed}:{role}:line sounds")))
        gs = plan.gap_sounds.get(role)                        # by the gap (gap_sounds) where the pack has the word
        if gs and not harness.UPPER_SOUNDS.get(role):
            sounds = gs["line" if layers else "only"]
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
        log = [f"voices {n}, register {(low, high)}, habit {plan.habits[role]}, voicing {plan.extras[role]['richness']}, "
               f"motion {plan.extras[role]['motion']}, sounded {_sounds_text(sounds)}; {sum(1 for f in figures if f != writer.REST)} bars written, "
               f"{len(notes)} notes; locked to the band in {len(lock)} bars"]
        all_figures = [f"{f} / {vc}" for f, vc in zip(figures, voicings)]
        line_notes = list(notes)
        scale = {(plan.tonic + i) % 12 for i in harmony.MODES["major" if plan.mode == "major" else "natural_minor"]}
        beside_v = set()                                    # the voices whose pitch is drawn beside the line under the span rule
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
                        drawn = _draw(models, "second_figures", (role, layer_class(plan, role), plan.feel, rhythm.band(plan.bpm), str(len(f.split())), f), rng_v, floor_k=MASK_FLOOR)
                        return rhythm.apply_mask(f, drawn)
                    given = [f if f == writer.REST else (memo.setdefault(f, masked(f)) if SECOND_MEMO else masked(f)) for f in figures]
                drawn_pitch = "voice_intervals" in models and "voice_moves" in models
                if drawn_pitch:
                    beside_v.add(v)
                span_v = plan.bounds.get(f"{role}:second", reg_v) if drawn_pitch else reg_v   # the voice's pitch is its drawn interval from the line, kept where the game plays its sample (round 34)
                notes_v, figures_v, voicings_v = writer.upper(song, role, [v], {v: span_v}, models, rng_v, plan.habits[role], plan.extras[role]["richness"], gs["second"] if gs else sounds,   # interval from the
                                                              key=key, lock=locks_of(song, {role}, plan), motion=plan.extras[role]["motion"],   # line, kept within the span FFVI's
                                                              pedals={v: (reg_v[0] + reg_v[1]) // 2}, plays=plan.plays[role], figures=given, shared=shared,   # voices beside a line sit in
                                                              tone_index=(writer.ANY_TONE if SECOND_ANY_TONE else v), kind=rel[0])   # (the layer offset's cap), not folded into its offset register
                log.append(f"voice {v + 1} {rel[0]}: register {reg_v} ({offset:+d}, {density}), "
                           + ("its interval to the line and its own moves drawn, " if drawn_pitch else f"the line's voicing {v} tone{'s' if v > 1 else ''} up, ")
                           + f"{sum(1 for f in figures_v if f != writer.REST)} bars, {len(notes_v)} notes" + ("; its bars beside the line's" if given else ""))
            song.notes[role] += [(a, b - a, m, role) for a, b, m, _ in notes_v]
            notes = notes + notes_v
            all_figures = [f"{x} || {f} / {vc}" for x, f, vc in zip(all_figures, figures_v, voicings_v)]
        written[role] = Part(role, notes, all_figures, log, beside=beside_v)
    tempo = rhythm.band(plan.bpm)
    for role in (R.MELODY, R.COUNTER):                    # the tune, then the counter-line beside it
        if role not in plan.band or not all(k in models for k in ("rhythm", "moves", "contours", "endings", "relations", "values")):
            continue
        x = plan.extras[role]
        beside = role == R.COUNTER and R.MELODY in written and all(k in models for k in ("counter_figures", "voice_intervals", "voice_moves"))
        if beside:
            # the counter-line as a mask over the tune's bar (counter_figures, drawn a bar as the second bass voice's is: which of
            # the tune's onsets it strikes with and its own; its own alone where the tune rests) and its pitch beside the tune by
            # the voice words under the drawn sample relation (writer.counter). FFVI's counter plays WITH the tune: 0.67 of its
            # onsets on the tune's, 1.42 times its notes, 2.5 semitones under; run through the melody writer a second time with its
            # own stream it had known nothing of the tune but the planned register (0.43 of its onsets on the tune's; Whole 28
            # 0.19, on the tune's sample in the tune's register: two tunes interleaved on one timbre)
            rng_c = random.Random(f"{seed}:{role}")
            tune_figs = [f if f == writer.REST else rhythm.pattern(rhythm.position(float(Fraction(t)), song.division) for t in f.split()) for f in written[R.MELODY].figures]
            masks = [writer.REST if not plan.plays[role][k] else
                     _draw(models, "counter_figures", (R.COUNTER, plan.weights.get(R.COUNTER, "minor"), plan.feel, tempo, "0" if pat == writer.REST else str(len(pat.split())), "-" if pat == writer.REST else pat),
                           rng_c, floor_k=COUNTER_MASK_FLOOR, floor_songs=PLAN_SONGS)
                     for k, pat in enumerate(tune_figs + [writer.REST] * (len(song.bars) - len(tune_figs)))]
            span = plan.bounds.get(R.COUNTER, plan.registers[R.COUNTER])   # where the game plays the counter's sample (round 34)
            notes, figures, plog = writer.counter(song, written[R.MELODY].notes, tune_figs, masks, span, models, rng_c, x.get("sample", "other"),
                                                  key=key, articulation=x["articulation"], register=span)
        else:
            notes, figures, plog = writer.melody(song, [], plan.bounds.get(role, plan.registers[role]), models, random.Random(f"{seed}:{role}"), plan.habits[role],
                                                 key=key, hold=(), reference=reference, articulation=x["articulation"], echo_habit=x["echo"],
                                                 recall=models.get("melody_recall"), step_habit=x["steps"], repeat_habit=x["repeats"], plays=plan.plays[role],
                                                 role=role, chord_rate=x.get("chord_tones"), repeat_rate=x.get("repeat_rate"), grain=x.get("grain"),
                                                 letters=x.get("letters") if role == R.MELODY else None, theme_body=models.get("theme_body"))
        song.notes[role] = [(a, b - a, m, role) for a, b, m in notes]
        line = [(a, b, m, 0) for a, b, m in notes]
        log = [f"register {plan.bounds.get(role, plan.registers[role])}, habit {plan.habits[role]}, " + ", ".join(f"{k} {v}" for k, v in x.items() if k not in ("layer", "letters"))
               + f"; {sum(1 for f in figures if f != writer.REST)} bars written, {len(notes)} notes; the reference set "
               + ("checked" if reference is not None and not beside else "not on this machine" if reference is None else "not asked: the line follows the tune")] + plog
        n, layer = plan.voices[role], layer_of(x)
        if n >= 2 and layer[0] == "doubling" and notes:     # the line again at the interval, in the scale
            scale = {(plan.tonic + i) % 12 for i in harmony.MODES["major" if plan.mode == "major" else "natural_minor"]}
            second = diatonic(line, layer[1], scale, 1)
            song.notes[role] += [(a, b - a, m, role) for a, b, m, _ in second]
            line = line + second
            log.append(f"doubled {layer[1]:+d} semitones, in the scale, on a second voice")
        elif n >= 2 and layer[0] == "apart" and beside:     # no word yet for a second counter voice beside a counter that follows the tune
            log.append(f"a second line apart ({layer[1]:+d}, {layer[2]}) not written: the counter follows the tune, and no word counts a voice beside it")
        elif n >= 2 and layer[0] == "apart" and role == R.COUNTER:   # a second counter-line of its own, clear of the first
            _, offset, density = layer
            low, high = plan.registers[role]
            reg2 = plan.bounds.get(f"{role}:second", (max(24, low + offset), min(100, high + offset)))
            habit2 = habit_near(models, role, tempo, plan.weights.get(role, "half"), random.Random(f"{seed}:{role}:second habit"), plan.habits[role], density)
            notes2, figures2, plog2 = writer.melody(song, [], reg2, models, random.Random(f"{seed}:{role}:second"), habit2,
                                                    key=key, hold=(), reference=reference, articulation=x["articulation"], echo_habit=x["echo"],
                                                    recall=models.get("melody_recall"), step_habit=x["steps"], repeat_habit=x["repeats"], plays=plan.plays[role],
                                                    role=role, chord_rate=x.get("chord_tones"), repeat_rate=x.get("repeat_rate"), grain=x.get("grain"))
            song.notes[role] += [(a, b - a, m, role) for a, b, m in notes2]
            line = line + [(a, b, m, 1) for a, b, m in notes2]
            figures = [f"{f} || {g}" for f, g in zip(figures, figures2)]
            log.append(f"a second line apart: register {reg2} ({offset:+d}), habit {habit2} ({density}); {sum(1 for f in figures2 if f != writer.REST)} bars, {len(notes2)} notes")
            log += [f"second: {l}" for l in plog2[-2:]]
        written[role] = Part(role, line, figures, log, beside={0} if beside else set())
    if R.MELODY in written:                                 # the theme in the band: doubled where the tune plays it, carried where it does not
        rng_theme = random.Random(f"{seed}:theme band")
        for line in double_theme(plan, song, written, models, rng_theme) + carry_theme(plan, song, written, models, rng_theme):
            written[R.MELODY].log.append(line)
    for line in hand_off_cells(plan, song, written, models, random.Random(f"{seed}:handoff")):
        written[R.MELODY].log.append(line)
    for line in copy_repeats(plan, song, written):
        for part in written.values():
            part.log.append(line)
    return written


# --- the rendering: the written notes on the pack's samples, through the converter's back end ---

REACH = 7                             # semitones a part's top may sit above the best pool sample's game-played range before the pack's
                                      # other tonal samples are tried for it


SPEED_WEIGHT = 3                      # a sample's score loses this a note a second the part's fastest bar runs past the sample's fastest in the game


def sample_speed(models, rid: str, rng: random.Random) -> tuple[float, float] | None:
    """How fast the game plays a sample, notes a second (the sample_speeds table's class tops): a song's fastest bars on
    it, drawn (a song plays a pad at eight notes a second where most hold it), and the fastest bars of any song; None
    unknown."""
    t = (models or {}).get("sample_speeds")
    if t is None or t.songs.get((rid,), 0) == 0:
        return None
    top = lambda c: float(c) if c != "faster" else 48.0   # noqa: E731
    drawn = t.draw((rid,), rng, floored=False, floor_k=PLAN_FLOOR)
    return top(drawn), max(top(c) for c in (t.votes.get((rid,)) or {drawn: 1}))


def written_speed(plan: Plan, written: dict, role: str, voices: set | None = None) -> float:
    """A written part's fastest bar, notes a second, over its voices (`voices`: a set of voice indices, all without)."""
    if role not in written:
        return 0.0
    counts = Counter((n[3], int(n[0] // METER)) for n in written[role].notes if voices is None or n[3] in voices)
    return max(counts.values(), default=0) * plan.bpm / (60.0 * METER)


def floors_for(plan: Plan, written: dict, samples: dict, models: dict | None, pack_name: str, rng: random.Random) -> dict:
    """Each chosen sample's note floor (sample_floor) under the speed class of the fastest written voice playing it, drawn
    on a stream of its own once the parts are written (round 36). The plan's drawn speed (part_speeds) fits the sample;
    the figures decide what the part then plays, and a part drawn at 6 a second that writes sixteenths at 120 BPM plays
    8: its floor must follow the notes it has, not the class it was fitted under, or a medium-class floor of 240 ms sits
    on 125 ms sixteenths."""
    raw = lambda n: n[len(pack_name) + 1:] if n.startswith(pack_name + "_") else n   # noqa: E731
    fastest = {}
    for key, chosen in samples.items():
        if not isinstance(chosen, tuple):
            continue
        role, _, which = key.partition(":")
        beside = {v for v, w in enumerate(layers_of(plan, role), start=1) if not w.startswith("doubling")}
        voices = beside if which == "second" else ({0} | ({v for v in range(1, plan.voices.get(role, 1))} - beside))
        fastest[chosen[0]] = max(fastest.get(chosen[0], 0.0), written_speed(plan, written, role, voices))
    return {name_: sample_floor(models, raw(name_), rng, speed if written else None) for name_, speed in fastest.items()}


def sample_floor(models, rid: str, rng: random.Random, speed: float | None = None) -> float:
    """The shortest note the game plays a sample at, in seconds (the sample_lengths table's class top); 0 unknown. `speed`:
    the fastest bar of the part playing it, notes a second: the floor is drawn under the sample's speed class (round 36),
    a fast part taking a fast song's floor. A floor drawn by the sample alone had taken a slow song's 120 ms for Whole 02's
    string pad at sixteenths, raising the notes round 35 had shortened to 50 ms back past where they were."""
    t = (models or {}).get("sample_lengths")
    if t is None or t.songs.get((rid,), 0) == 0:
        return 0.0
    context = (rid, rhythm.speed_tier(speed)) if speed is not None else (rid,)
    drawn = t.draw(context, rng, floored=False, floor_k=PLAN_FLOOR)
    return (float(drawn) if drawn != "long" else 400.0) / 1000.0


def best_sample(ranges, names: list, register: tuple, rng: random.Random, raw, others: list = (), speed: float = 0.0, models: dict | None = None,
                drawn: dict | None = None, role: str | None = None) -> str:
    """The sample for a part's register and speed: of the pool's samples (`names`, repeated by their share), one the game
    plays as fast as the part's fastest bar (the sample_speeds table) whose game-played range (the ranges table, by the
    pack's own sample id, `raw(name)`) covers the register best, the part's top weighing most; when none of the pool
    reaches the register's top within REACH or none plays this fast, the pack's other tonal samples (`others`) are
    tried; then one some song plays this fast in its fastest bars; where none does, the speed's excess over the
    game's fastest ever on the sample weighs against the range's fit (SPEED_WEIGHT a note a second); the pool's share
    decides a tie. Never a random one: a sample pushed far above where the game played it
    turns shrill (8 to 10 % of written notes had sat over an octave above the recording against FFVI's 0 to 2 %; the
    fit had asked only that the register's centre lie near the range, and by the pack's prefixed names it had found no
    range at all and drawn at random), and a slow-attack pad played at sixteenths never reaches its body (Song Check
    14's Whole 02: FFVI plays that pad under six notes a second; the part ran at eight)."""
    def score(name):
        rid = raw(name)
        if ranges is None or ranges.songs.get((rid,), 0) == 0:
            return None
        lo, hi = (int(x) for x in ranges.draw(range_context(rid, role), rng, floored=False, floor_k=PLAN_FLOOR).split("-"))
        if drawn is not None:
            drawn[rid] = (lo, hi)
        a, b = register
        fastest = sample_speed(models, rid, rng)             # the part's fastest bar against the sample's fastest in the game
        slow = max(0.0, speed - fastest[0]) if fastest is not None else 0.0     # past a song's fastest on it
        ever = max(0.0, speed - fastest[1]) if fastest is not None else 0.0     # past any song's
        return max(0, min(b, hi) - max(a, lo)) - 2 * max(0, b - hi) - max(0, lo - a), hi, slow, ever

    def scored(pool):
        return [(s, n) for s, n in ((score(n), n) for n in pool) if s is not None]

    def choose(cands):
        """The best of the candidates, in three reaches: among those overlapping the register that a song of the game
        plays this fast, by the fit; else among those some song plays this fast in its fastest bars; else by the fit
        less the speed's excess over the game's fastest ever on the sample. (reach 2, 1 or 0, value, names at it)."""
        for reach, held in ((2, lambda s: s[0] > 0 and s[2] == 0), (1, lambda s: s[0] > 0 and s[3] == 0)):
            fitting = [(s, n) for s, n in cands if held(s)]
            if fitting:
                best = max(s[0] for s, _ in fitting)
                return reach, best, [n for s, n in fitting if s[0] == best]
        value = lambda s: s[0] - SPEED_WEIGHT * s[3]   # noqa: E731
        best = max(value(s) for s, _ in cands)
        return 0, best, [n for s, n in cands if value(s) == best]

    known = scored(names)
    if not known:
        return rng.choice(names)
    got, best, top = choose(known)
    reach = max(s[1] for s, _ in known)
    if others and (register[1] - reach > REACH or got < 2):
        wider = scored([n for n in others if n not in names])
        if wider:
            got2, best2, top2 = choose(wider)
            if (got2, best2) > (got, best):
                top = top2
    return rng.choice(top)


def _sounds_text(sounds) -> str:
    """A sounded share for a log: one share, or the gap_sounds word's by gap class."""
    if isinstance(sounds, dict):
        return " ".join(f"{g} {sounds[g]:.1f}" for _, g in rhythm.GAP_CLASSES if g in sounds)
    return f"{float(sounds):.2f}"


def second_register(plan: Plan, role: str) -> tuple:
    """The register of a layered part's first voice beside the line, as write() gives it: the part's at the layer word's
    offset (apart), or the part's own (alternating)."""
    low, high = plan.registers[role]
    for w in layers_of(plan, role):
        rel = layer_of({"layer": w})
        if rel[0] != "doubling":
            offset = rel[1] if rel[0] == "apart" else 0
            return (max(24, low + offset), min(100, high + offset))
    return (low, high)


def range_context(rid: str, role: str | None) -> tuple:
    """The ranges word's context for a sample as a part plays it (round 55: by the sample and the part, the sample alone where
    no part is named or the table knows no songs of the pair, which the draw's back-off handles)."""
    return (rid, role) if role else (rid,)


def reaches(ranges, rid: str, register: tuple, rng: random.Random, drawn: dict | None = None, role: str | None = None) -> bool:
    """Whether a sample's game-played range (the ranges table) comes within REACH of a register at both ends; True where
    the table knows nothing of the sample. `drawn`: a dict the drawn range is kept in by the sample's id (the register the
    voice is then written in, bound_of)."""
    if ranges is None or ranges.songs.get((rid,), 0) == 0:
        return True
    lo, hi = (int(x) for x in ranges.draw(range_context(rid, role), rng, floored=False, floor_k=PLAN_FLOOR).split("-"))
    if drawn is not None:
        drawn[rid] = (lo, hi)
    if min(hi, register[1]) - max(lo, register[0]) >= MIN_SPAN:   # the voice is then written in the overlap (bound_of): a planned
        return True                                             # register wider than any one song's range (the counter's 48-88) fits
    return register[1] - hi <= REACH and lo - register[0] <= REACH


def bound_of(played: tuple | None, planned: tuple) -> tuple:
    """The register a voice is written in: where the game plays the sample chosen for it (`played`, the ranges word's
    drawn range), within the part's planned register where the two overlap; the sample's range alone where they do not;
    a sliver widened to MIN_SPAN inside the sample's range; the planned register where the word knows nothing of the
    sample. Round 34: the register used to come first and the sample was found for it after the writing, so three rules
    (the span a voice beside a line wrote in, the bass's floor plus REACH, the reach check) and a fold covered the seam,
    and the bass line still wrote 24 % of its notes past its sample's widest band, the melody 2 %."""
    if played is None:
        return tuple(planned)
    lo, hi = max(played[0], planned[0]), min(played[1], planned[1])
    if hi < lo:
        return tuple(played)
    if hi - lo < MIN_SPAN:
        centre = (lo + hi) / 2
        lo = int(max(played[0], min(centre - MIN_SPAN / 2, played[1] - MIN_SPAN)))
        hi = int(min(played[1], lo + MIN_SPAN))
    return (int(lo), int(hi))


def pair_for(models: dict | None, role: str, own: set, rng: random.Random) -> tuple | None:
    """The game's own pair of samples for a layered part (layer_samples), drawn from the part's pairs alone and only
    where the pack holds both: (line's, second's) as the pack's own ids; None otherwise. A pair drawn from another
    part's (a counter-line with no pairs of its own took an accompaniment's) or applied by halves (the pack lacking the
    line's sample, the second's taken anyway) had put a bass sample an octave and a half above where the game plays it
    (Song Check 17's Whole 22, Whole 24)."""
    t = (models or {}).get("layer_samples")
    if t is None:
        return None
    t = t.table if hasattr(t, "table") else t
    if t.songs.get((role,), 0) == 0:
        return None
    pair = t.draw((role,), rng, floored=False, floor_k=PLAN_FLOOR, min_songs=PLAN_SONGS).split()
    if len(pair) == 2 and pair[0] == pair[1]:
        return ("same", "same")                             # one sample for both voices: the second takes the line's, whatever the pack gave it
    return (pair[0], pair[1]) if len(pair) == 2 and pair[0] in own and pair[1] in own else None


def counter_pair_for(models: dict | None, tune: str, own: set, ranges, register: tuple, rng: random.Random, drawn: dict | None = None) -> tuple | None:
    """The counter-line's sample beside the tune's where it plays another (counter_pairs): drawn once a song under the
    tune's sample (the pack's id) from the table's distribution as a plan draw sees it (the tune's context mixed with its
    back-off, the counter's sample over all tunes, the part's level still a count), restricted to the samples that fit:
    ones the pack holds, not the tune's own, reaching the register the counter was written in (reaches, as pair_for checks
    a layered part's pair). (the sample, "tune" where the game pairs it with this tune sample or "part" where it plays it
    as a counter against other tunes only, what was passed over and why), the sample and level None where nothing counted
    fits (the pool rule by register and speed is the last fallback then), all three None without the table or its units.
    A draw refused at the first misfit had left the table for the rule in eight songs of ten (a sample the pack lacks, or
    one drawn range short of the register); the rule had given Whole 28's counter sdbd05ab4d5 beside a tune on sf89f5aedfd
    at a 0.28 chance, a sample 4.2 dB louder in its body and nearly twice as bright, which FFVI never plays as a counter
    against another tune sample; FFVI's partners for that tune sample are sfd6accf98a four times in ten and s256b199ccf
    three (round 30)."""
    t = (models or {}).get("counter_pairs")
    if t is None:
        return None, None, None
    t = t.table if hasattr(t, "table") else t
    if t.songs.get((R.COUNTER,), 0) == 0:
        return None, None, None
    weights = t.weights((R.COUNTER, tune), floor_k=PLAN_FLOOR, min_songs=PLAN_SONGS)
    passed, fitting = {}, {}
    for sid, w in weights.items():                          # the pack and the tune's own first: no stream spent on them
        if sid not in own:
            passed.setdefault("not in the pack", []).append(sid)
        elif sid == tune:
            passed.setdefault("the tune's own", []).append(sid)
        elif not reaches(ranges, sid, register, rng, drawn, R.COUNTER):
            passed.setdefault(f"out of reach of {register[0]}-{register[1]}", []).append(sid)
        else:
            fitting[sid] = w
    over = [f"{' '.join(sids)} {why}" for why, sids in passed.items()]
    if not fitting:
        return None, None, over
    sid = rng.choices(list(fitting), weights=list(fitting.values()))[0]
    fine = t.votes.get((R.COUNTER, tune), {}) if t.songs.get((R.COUNTER, tune), 0) >= PLAN_SONGS else {}
    return sid, "tune" if sid in fine else "part", over


def _weighted(rng: random.Random, options: list, weights: list):
    """One of the options by their weights."""
    x = rng.random() * sum(weights)
    for o, w in zip(options, weights):
        x -= w
        if x < 0:
            return o
    return options[-1]


def wide_enough(models: dict | None, rid: str, played: tuple | None, role: str, log: list) -> tuple | None:
    """A chord part's home band (the ranges word's draw) where it is at least MIN_SPAN wide, else the sample's whole played
    range (sample_ambitus) in its place (round 53): a song that strikes a sample at one pitch had bound a three-voice
    accompaniment to that pitch for 45 bars. A sample the game only ever plays at one pitch (a drum sample as a rhythmic
    chord part, FFVI's accompaniment in 0.08 of songs) keeps its one pitch: that is how the game plays it."""
    if played is None or played[1] - played[0] >= MIN_SPAN:
        return played
    whole_range = ambitus_of(models, rid)
    if whole_range is None or whole_range == tuple(played):
        return played
    log.append(f"{role}'s home band on {rid} {played} is under {MIN_SPAN} semitones: bound by the sample's whole range {whole_range}")
    return whole_range


def part_sample_for(models: dict, role: str, speed: float | None, own: set, rng: random.Random, log: list) -> str | None:
    """The sample the part_samples word gives a part (round 42): drawn under the part and the speed class of its fastest
    bar (the table backs off to the part alone) from the word's shares over the samples the pack holds (round 45: a
    sample the pack lacks gives its share to the others, as an echo's empty source does); None, logged, where the pack
    holds none of the word's samples, and the pool rule then chooses."""
    t = models["part_samples"]
    t = t.table if hasattr(t, "table") else t
    ctx = (role, rhythm.speed_tier(speed)) if speed else (role,)
    held = sorted(o for o in t.vocabulary if o in own)   # round 45: the word's shares over the samples the pack holds (a draw the pack
    if not held:                                         # could not serve had fallen to the pool rule in 25 of 45 plans, the pack holding
        log.append(f"{role}'s samples (part_samples): none in the pack; the pool rule chooses")   # 0.86 of the word's mass a part)
        return None
    weights = [t.p(o, ctx) for o in held]
    return _weighted(rng, held, weights) if sum(weights) > 0 else rng.choice(held)


def ambitus_of(models: dict | None, rid: str, rng: random.Random = None) -> tuple | None:
    """The whole range the game ever played a sample over (sample_ambitus, round 43): the lowest low and the highest high
    of the word's outcomes for it, not one song's draw. A tune's register is its balance token's (one song's ambitus,
    20 semitones at FFVI's median), and a bound drawn from another song's ambitus and cut against it had left the
    tune the overlap of two songs' ranges (Whole 38: 76-84 of a planned 76-92); the sample's wall is where the game
    took it at all. None without the word, or for a sample it has no song for."""
    t = (models or {}).get("sample_ambitus")
    t = t.table if hasattr(t, "table") else t
    if t is None or not t.songs.get((rid,), 0):
        return None
    spans = [tuple(int(x) for x in o.split("-")) for o in t.votes.get((rid,), {})]
    if not spans:
        return None
    return min(lo for lo, _ in spans), max(hi for _, hi in spans)


def samples_for(plan: Plan, pack: dict, own: set, pack_name: str, rng: random.Random, models: dict | None = None) -> dict:
    """Each part's sample from the pack's pools: {role: (voice name, ITSample)}; the drums' kit {piece: (name, ITSample)}.
    `own`: the pack file's own sample names (registered as pack_name_voice), the rest built-in voices. With the pack's
    ranges table, a pitched part takes a sample of its pool the game played in the part's register (the pool's own
    weights among those), fitted for speed to the part's drawn fastest bar (part_speeds); the pool's draw where none is
    known to fit. Chosen BEFORE the writing (round 34): the range drawn for the chosen sample is the register the voice
    is then written in (plan.bounds, bound_of), so every voice plays where the game plays its sample. The sample had
    come after the writing, fitted to the written notes' speed, and three rules with a fold had covered the seam."""
    from ..instruments import _make_sample

    def make(name):
        return name, _make_sample(f"{pack_name}_{name}" if name in own else name)
    voices = pack["voices"]
    ranges = (models or {}).get("ranges")
    out, drawn = {}, {}                                     # drawn: each sample's range as the fit drew it, by the pack's id
    kind = plan.extras.get(R.COUNTER, {}).get("sample")   # the counter-line's sample relation to the tune's (counter_samples), where drawn
    for role in sorted(plan.band, key=lambda r: r == R.COUNTER):   # the counter last: its sample is the tune's, or another
        if role == R.DRUMS:
            out[role] = {piece: make(name) for piece, name in (voices.get("drums") or {}).items()}
            given_kit = plan.extras.get(R.DRUMS, {}).get("kit") or {}   # the token song's own kit (round 63), slot by piece letter, where
            taken = []                                                  # the pack holds the sample; the pack's slot else
            for letter, sid in given_kit.items():
                slot = KIT_SLOT.get(letter)
                if slot and sid in own:
                    out[role][slot] = make(sid)
                    taken.append(f"{slot} {sid}")
                    if slot == "hihat" and "open_hihat" in out[role]:
                        out[role]["open_hihat"] = make(sid)
            if taken:
                plan.log.append("kit samples from the balance's song: " + ", ".join(taken))
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
        register = plan.registers.get(role)
        given = plan.token_samples.get(role)                # the token song's own instrument for the part (round 60), where the pack holds it
        if given and given in own:
            out[role] = make(given)
            if ranges is not None and ranges.songs.get((given,), 0):
                drawn[given] = tuple(int(x) for x in ranges.draw(range_context(given, role), rng, floored=False, floor_k=PLAN_FLOOR).split("-"))
            plan.log.append(f"{role}'s sample {given}: the balance's song's own (its levels were counted on it)")
        if role == R.COUNTER and kind and R.MELODY in out and role not in out:   # the counter beside the tune (round 29): on the tune's sample as the plan drew it
            if kind == "same":                              # (counter_samples: 18 of FFVI's 52 songs with both; the pool's own choice had given
                out[role] = out[R.MELODY]                   # 3 of 14, and 10 of 14 once the counter sat in the tune's register), else on another,
                continue                                    # chosen for where the counter was written, which is where the tune is
            tune = raw(out[R.MELODY][0])                    # by the pack's id: the pool names the sample with the pack's prefix and the pack's
            names = [n for n in names if raw(n) != tune] or names   # other tonal samples without it, and a name-for-name exclusion had let the
            tonal = [n for n in tonal if n != tune]         # rule give an "other" counter the tune's own sample under its other name
            if register:                                    # the game's own pair for the tune's sample (counter_pairs, round 30) before the
                sid, level, passed = counter_pair_for(models, tune, own, ranges, register, rng, drawn)   # pool rule: FFVI's counter sample is
                over = f" (passed over: {'; '.join(passed)})" if passed else ""                    # darker than the tune's in 17 pairs of 23
                if sid is not None:
                    out[role] = make(sid)
                    plan.log.append(f"counter's sample {sid}: " + (f"the game's pair under the tune's {tune}" if level == "tune"
                                                                    else "the counter's sample over all tunes") + f" (counter_pairs){over}")
                elif passed is not None:
                    plan.log.append(f"counter's sample by the pool rule for {register[0]}-{register[1]}: no counted pair fits{over}")
        if role not in out and role in rhythm.SAMPLE_PARTS and (models or {}).get("part_samples") is not None:
            sid = part_sample_for(models, role, plan.speeds.get(role), own, random.Random(f"whole:{plan.seed}:sample:{role}"), plan.log)   # the instrument
            # the game gives the part (round 42), on its own stream (round 56: on the render stream it moved with every draw before it)
            if sid is not None:
                out[role] = make(sid)
                if ranges is not None and ranges.songs.get((sid,), 0):
                    drawn[sid] = tuple(int(x) for x in ranges.draw(range_context(sid, role), rng, floored=False, floor_k=PLAN_FLOOR).split("-"))
        if role not in out:
            out[role] = make(best_sample(ranges, names, register, rng, raw, tonal, speed=plan.speeds.get(role, 0.0), models=models, drawn=drawn, role=role)
                             if register else rng.choice(names))
        if register:
            played = drawn.get(raw(out[role][0]))
            if role in (R.MELODY, R.COUNTER):               # a tune's bound is the whole range the game took the sample over (round 43)
                played = ambitus_of(models, raw(out[role][0])) or played
            else:
                played = wide_enough(models, raw(out[role][0]), played, role, plan.log)
            plan.bounds[role] = bound_of(played, register)
        # a layered part apart: its line and its second voice on the game's own pair of samples (layer_samples) where the
        # pack holds both and each reaches its voice's register; else the second voice's sample by its own register and
        # speed, as the line's is chosen
        if any(not w.startswith("doubling") for w in layers_of(plan, role)) and role in plan.registers:
            reg2 = second_register(plan, role)
            pair = pair_for(models, role, own, rng)
            second = None
            given2 = (plan.layer_samples.get(role) or [""])[0]   # the token song's own sample for its voice beside the line (round 65)
            if given2 and given2 in own:
                second = make(given2)
                plan.log.append(f"{role}'s second voice's sample {given2}: the balance's song's own")
            elif pair == ("same", "same"):                  # FFVI gives one sample to both voices in half its layered chord parts
                second = out[role]
            elif pair is not None and reaches(ranges, pair[0], plan.registers[role], rng, drawn, role) and reaches(ranges, pair[1], reg2, rng, drawn, role):
                out[role] = make(pair[0])
                second = make(pair[1])
                plan.bounds[role] = bound_of(wide_enough(models, pair[0], drawn.get(pair[0]), role, plan.log), plan.registers[role])
            if second is None:
                second = make(best_sample(ranges, names, reg2, rng, raw, tonal, speed=plan.speeds.get(role, 0.0), models=models, drawn=drawn, role=role))
            out[f"{role}:second"] = second
            plan.bounds[f"{role}:second"] = bound_of(wide_enough(models, raw(second[0]), drawn.get(raw(second[0])), f"{role}:second", plan.log), reg2)
    floors, fastest = {}, {}                                # each chosen sample's shortest note in the game (sample_lengths): a note's floor on
    for key, chosen in list(out.items()):                   # it, under the speed class of the fastest part it serves (round 36)
        if isinstance(chosen, tuple):
            fastest[chosen[0]] = max(fastest.get(chosen[0], 0.0), plan.speeds.get(key.split(":")[0], 0.0))
    for name_, speed in fastest.items():
        floors[name_] = sample_floor(models, raw(name_), rng, speed if plan.speeds else None)
    out["floors"] = floors
    if plan.bounds:
        plan.log.append("written where the game plays each sample: " + ", ".join(f"{k} {lo}-{hi}" for k, (lo, hi) in plan.bounds.items()))
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


def note_level(plan: Plan, role: str, voice: int, second_voice: dict | None = None, bar: int | None = None) -> float:
    """A note's level of full: the part's share of the song's loudest part's (plan.levels: the balance token's where its
    song has the part, so the band's levels are one FFVI song's as one unit and the loudest part plays at TOP_LEVEL and
    the rest at their share; the `levels` table's for a part the token lacks; the counter-line's from counter_shares
    under the tune's share band; LEVELS without a levels word), a voice beside the line at its own share of the line's
    (the balance token's share for that voice where its song has the part layered, plan.voice_levels by rank, so the
    line and the voices beside it are one FFVI song's together; the layer_levels draw for a voice the token has no share
    for; `second_voice` those voices by part, layers_of's apart and alternating voices; a doubling voice plays the line's
    level). Never under 0.05 nor over 1.0 of full: a share is at most 1.0, so only a second voice over 1.0 of its line
    can reach the cap."""
    base = plan.top_level * plan.levels[role] if role in plan.levels else LEVELS[role]   # the loudest part at the song's top level (round 52)
    if bar is not None and role in plan.section_levels and 0 <= bar < len(plan.section_levels[role]):
        base *= plan.section_levels[role][bar]              # the section's level over the part's (section_levels, round 48)
    if second_voice is None:
        second_voice = {role: {v for v, w in enumerate(layers_of(plan, role), start=1) if not w.startswith("doubling")}}
    if voice in second_voice.get(role, ()):
        shares = plan.voice_levels.get(role) or []
        base *= shares[voice - 1] if 0 < voice <= len(shares) else plan.layer_levels.get(role, 1.0)
    return max(0.05, min(1.0, base))


def sample_rms(sample) -> float:
    """A module sample's own loudness: the RMS of its loop body (the whole sample without a loop), 0-1 (round 56)."""
    return sample_strike_and_body(sample)[1]


def sample_strike_and_body(sample) -> tuple[float, float]:
    """A module sample's loudness in two numbers, 0-1: the RMS of its strike
    (its first STRIKE_WINDOW seconds at its own rate) and of its loop body
    (the whole sample without a loop). A note hears the strike first and
    the body after (`heard_rms`): a short chord on a struck sample is as
    loud as its attack, not as its tail (round 59: Whole 79's accompaniment
    rendered 8 dB over its estimate by the body alone)."""
    import array
    data = sample.data
    x = data if isinstance(data, array.array) else array.array("h", bytes(data)[: (len(data) // 2) * 2])
    if not len(x):
        return 0.0, 0.0
    a, b = 0, len(x)
    for flag, start, end in (("loop", "loop_start", "loop_end"), ("sus_loop", "sus_loop_start", "sus_loop_end")):
        lo, hi = getattr(sample, start, 0), getattr(sample, end, 0)
        if getattr(sample, flag, False) and hi > lo:         # the loop a held note sits in: the ordinary loop, else the sustain loop (a pack
            a, b = lo, hi                                   # voice with a release holds its sustain loop; read as the whole sample, its quiet
            break                                           # release tail had halved the loudness and the writer boosted the note, round 59)
    body = x[a:b] if b <= len(x) and b > a else x
    rate = getattr(sample, "c5_speed", 0) or 32000
    strike = x[:max(1, min(len(x), int(rate * rhythm.STRIKE_SECONDS)))]
    rms = lambda seg: math.sqrt(sum(v * v for v in seg) / len(seg)) / 32768   # noqa: E731
    return rms(strike), rms(body)


def heard_rms(strike: float, body: float, seconds: float) -> float:
    """rhythm.heard_rms: the loudness a note of `seconds` hears from its sample, its strike then its body (round 65 shares it with the readings)."""
    return rhythm.heard_rms(strike, body, seconds)


def score_of(plan: Plan, written: dict, samples: dict, loops: int = 2, fade: float = 2.0, echo: dict | None = None, tail_bars: int = 0, pack_name: str = "",
             master: tuple | None = None):
    """The written parts as a score (spc.convert.Score) on the pack's
    samples: the form once, then the loop (from the loop's bar to the
    form's end) `loops` - 1 times more, fading at the end; with
    `tail_bars`, the loop's first bars once more after the last pass,
    fading through them, so a listener hears the song come back round to
    its hook; the echo as given (echo_of). Returns the score and {role:
    first voice}."""
    floors = samples.get("floors") or {}
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

    from .. import samples as samples_mod

    loud_of, strike_of, drum_loud_of, capped = {}, {}, {}, Counter()   # a sample's own loudness (round 56): a note plays at its level over it
    heard = []                                            # (start in beats, length in beats, perceived level): the mix level (round 59)

    def level_of(role, j, bar=None, name=None, sample=None, seconds=0.0):
        level = note_level(plan, role, j, second_voice, bar)
        if sample is None:
            return level, level
        if role == R.DRUMS:                                 # a drum at its level over its strike's loudness (round 63): the readings count
            if name not in drum_loud_of:                    # the kit's levels the same way (its own table: a song may strike a tonal voice)
                strike, _ = sample_strike_and_body(sample)
                drum_loud_of[name] = rhythm.LOUDNESS_REF / strike if strike > 0 else 1.0
            played = min(1.0, level * drum_loud_of[name])
            if level * drum_loud_of[name] > 1.0:
                capped[name] += 1
            return played, played / drum_loud_of[name]
        if name not in loud_of:                             # the module sample's own loudness (round 59): the instrument builder scales a
            strike, rms = sample_strike_and_body(sample)    # sustaining voice's loop to one loudness (samples.LOUDNESS_TARGET), so the pack
            if rms <= 0:                                    # table's numbers (the game's samples as the game plays them, which the readings'
                rid = name[len(pack_name) + 1:] if name.startswith(pack_name + "_") else name   # levels are counted with) are not what
                rms = rhythm.SAMPLE_LOUDNESS.get(rid, 0.0)  # the module plays; round 56 had read the table first and boosted "quiet" samples
            loud_of[name] = rhythm.LOUDNESS_REF / rms if rms > 0 else 1.0   # the module had already brought up
            strike_of[name] = (strike, rms)
        strike, body = strike_of[name]                      # what this note hears of the sample: its strike, then its body (round 65: the level
        heard = heard_rms(strike, body, seconds) if body > 0 else 0.0   # too, as the readings count it, not the body alone)
        factor = rhythm.LOUDNESS_REF / heard if heard > 0 else loud_of[name]
        wanted = level * factor
        if wanted > 1.0:
            capped[name] += 1
        played = min(1.0, wanted)
        return played, played / factor

    def put(voice, role, t0, t1, midi, name, sample, j, bar=None):
        idx, addr, c5 = instrument(name, sample)
        pan = PANS[role][j % len(PANS[role])]
        send = echo is not None and role in SENDS
        env = samples_mod.SAMPLE_ENVELOPES.get(name)        # the envelope the game plays the sample with; flat and full without one
        adsr, gain = ((env["adsr"][0], env["adsr"][1]), 0) if env and "adsr" in env else ((0, 0), env["gain"] if env else score_mod.GAIN_FULL)
        played, perceived = level_of(role, j, bar, name, sample, min(t1, seconds) - t0)
        heard.append((t0 / beat_s, (min(t1, seconds) - t0) / beat_s, perceived))
        notes.append(notes_mod.Note(voice, t0, idx, score_mod._pitch(c5, midi), score_mod._sides(played, pan), adsr, gain,
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
                    t1 = max(t1, t0 + floors.get(name, 0.0))   # never shorter than the game plays the sample (the next key-on cuts an overlap)
                    put(first[role] + n[3], role, t0, t1, float(n[2]), name, sample, n[3], int(a // METER))   # the bar's section level (round 48)
    if capped:
        plan.log.append("loudness: notes capped at full, their sample too quiet for their level: " + ", ".join(f"{k} {v}" for k, v in capped.most_common()))
    notes.sort(key=lambda x: (x.start, x.voice))
    last = {}                                                # a floored note never runs into the voice's next: the key-on cuts it
    for n in notes:
        prev = last.get(n.voice)
        if prev is not None and prev.end is not None and prev.end > n.start:
            prev.end = n.start
        last[n.voice] = n
    tempo, row_hz = it_song.tempo_for(convert.FINE_GRID)
    given = master
    master, gain_up = 127, 1.0
    estimate = rhythm.mix_level(heard)
    if given is not None:                                   # a stem: the whole song's master and gain, so the stems sum to the whole
        master, gain_up = given
        if gain_up > 1.0:
            for n in notes:
                n.volume = tuple(int(max(-127, min(127, round(v * gain_up)))) for v in n.volume)
    elif plan.loudness is not None and estimate is not None:   # the song's master volume holds its loudness to the token's song's (round 59)
        master, gain_up = master_of(plan.loudness, estimate)
        plan.master = (master, gain_up)
        if gain_up > 1.0:                                   # a song under its target with the master already full: the notes come up
            for n in notes:
                n.volume = tuple(int(max(-127, min(127, round(v * gain_up)))) for v in n.volume)
        plan.log.append(f"master: the mix estimated at {estimate:.1f} dB renders near {estimate + RENDER_BRIDGE:.1f} dBFS against the song's "
                        f"{plan.loudness:.0f}: master {master} of 127" + (f", notes raised {20 * math.log10(gain_up):.1f} dB" if gain_up > 1.0 else ""))
    message = [f"{plan.title} - {harmony.NAMES[plan.tonic]} {plan.mode} - {round(plan.bpm)} BPM - form {plan.letters}",
               "Written by bitComposer from the pack's tables (docs/IDIOM.md, phase 4: the",
               "integration): every part free on a skeleton the tables gave, rendered as a game's song is."]
    score = convert.Score(notes, seconds, n_voices, [(0.0, master, master)], fade, plan.title[:25], plan.game, "bitComposer", row_hz, tempo,
                          0.0, 0.0, False, None, pcm_of, key_of, message=message)
    return score, first


def layer_class(plan: Plan, role: str) -> str:
    """The class the mask word is drawn under for a part's voices beside the line (round 65): the token song's extra
    voices' notes over the line's (sparse, half, full; rhythm.LAYER_SHARES), "half" where the token has no share."""
    shares = plan.layer_shares.get(role)
    return rhythm.layer_share_class(max(shares)) if shares else "half"


def master_of(target: float, estimate: float) -> tuple[int, float]:
    """The master volume (of 127) that brings a written song to its target
    loudness (the token's song's rendered loudness, dBFS) from its mix
    estimate (what it renders at is the estimate plus RENDER_BRIDGE):
    (master, the gain the notes take where the master is full already and
    the song still under). The master is the SNES chip's own lever, a
    song's from its first bar (FFVI's sit at 32 to 61 of 128 at a song's
    start); the converter trades it against the channels' volumes
    loudness-neutrally."""
    factor = 10 ** ((target - (estimate + RENDER_BRIDGE)) / 20)
    if factor <= 1.0:
        return max(MASTER_FLOOR, round(127 * factor)), 1.0
    return 127, factor


def stems_of(plan: Plan, written: dict, samples: dict, out_dir: str, loops: int = 1, fade: float = 3.0, echo: dict | None = None,
             tail_bars: int = 0, pack_name: str = "") -> list[str]:
    """Each written part alone as a module of its own (`<title> <part>.it`),
    for a page that plays the parts in sync and switches each: the same
    length, echo and samples as the whole, so their sum is the whole.
    Returns the paths."""
    import os
    from ..spc import convert
    os.makedirs(out_dir, exist_ok=True)
    paths = []
    if plan.master is None and plan.loudness is not None:   # the whole song's master first: every stem takes it (round 59), so the stems
        score_of(plan, written, samples, loops=loops, fade=fade, echo=echo, tail_bars=tail_bars, pack_name=pack_name)   # still sum to the whole
    for role, part in written.items():
        if not part.notes:
            continue
        score, _ = score_of(plan, {role: part}, samples, loops=loops, fade=fade, echo=echo, tail_bars=tail_bars, pack_name=pack_name,
                            master=plan.master or (127, 1.0))
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
    rng = random.Random(f"whole:{seed}:render")
    samples = samples_for(p, pack, own, pack_name, rng, models)   # before the writing: every voice writes where the game plays its sample
    written = write(p, song, models, seed, reference)
    echo = echo_of(pack.get("habits") or {}, p.bpm, rng)
    samples["floors"] = floors_for(p, written, samples, models, pack_name, random.Random(f"whole:{seed}:floors"))   # by the written speed
    score, first = score_of(p, written, samples, loops=loops, fade=fade, echo=echo, tail_bars=tail_bars, pack_name=pack_name)
    out = {"plan": p, "song": song, "written": written, "score": score, "first": first, "samples": samples, "echo": echo, "read": None, "measures": None}
    if read:
        once, _ = score_of(p, written, samples, loops=1, fade=0.0, echo=echo, pack_name=pack_name)
        back = read_back(once, p, first, samples)
        out["read"] = back
        out["measures"] = measures(back) if back is not None else None
        if out["measures"] is not None:                      # the reader's form, heard as a player hears it: with the loop
            twice, _ = score_of(p, written, samples, loops=2, fade=0.0, echo=echo, pack_name=pack_name)
            looped = read_back(twice, p, first, samples)
            out["measures"]["parts"] = len(looped.parts) if looped is not None else 0
            out["measures"]["loop_heard"] = int(looped is not None and looped.loop_bar is not None)
    return out
