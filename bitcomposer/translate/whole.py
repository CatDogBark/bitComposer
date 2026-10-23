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
                "band": self.band, "weights": self.weights, "textures": self.textures, "registers": {k: list(v) for k, v in self.registers.items()},
                "sounds": self.sounds, "habits": self.habits, "extras": self.extras, "voices": self.voices, "log": self.log}


@dataclass
class Part:
    """A part written for the plan."""
    role: str
    notes: list                       # pitched: (start, end in beats, midi, the part's voice); drums: (start, end, letter, voice, kit sample)
    figures: list
    log: list = field(default_factory=list)


def _draw(models: dict, name: str, context: tuple, rng: random.Random, log: list | None = None) -> str:
    """A draw from a pack's table under a context (a mixture's own table alone); the default where the pack has no such table."""
    t = models.get(name)
    if t is None:
        default = DEFAULTS[name]
        if isinstance(default, dict):
            default = default[context[0]]
        if log is not None and f"no {name} table" not in " ".join(log):
            log.append(f"no {name} table: {default!r} assumed")
        return default
    t = t.table if hasattr(t, "table") else t
    return t.draw(tuple(context), rng)


def plan_form(models: dict, rng: random.Random, log: list, max_bars: int | None = None) -> list:
    """The form: how many parts (the sizes table), each part new, again or
    back by its index (the form table), a new part's length by the song's
    length habit (the lengths table), a repeat as long as the part it
    repeats; (first bar, bars, the part repeated or None, letter)."""
    size = max(1, min(MAX_PARTS, int(_draw(models, "sizes", ("form",), rng, log))))
    habit = _draw(models, "length_habits", ("form",), rng, log)
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
    from the part-textures table among the band's parts (given the part's
    place in the form and the part before's texture), a repeated part
    keeping its texture; a bar's texture is its part's. Returns the
    textures a bar and each part's bars."""
    total = parts[-1][0] + parts[-1][1]
    textures = [None] * total
    table = models.get("part_textures")
    allowed = lambda t: t != rhythm.SILENCE and set(t.split()) <= set(band)   # noqa: E731
    previous = rhythm.START
    n_parts = len(parts)
    for i, (bar, n, of, _) in enumerate(parts):
        if of is not None:
            src = parts[of][0]
            textures[bar:bar + n] = textures[src:src + n]
            continue
        if table is None:
            t = " ".join(band)
        else:
            form = "only" if n_parts == 1 else "first" if i == 0 else "last" if i == n_parts - 1 else "middle"
            ctx = (rhythm.ARRANGEMENT, form, previous)
            for _ in range(20):
                t = table.draw(ctx, rng)
                if allowed(t):
                    break
            else:
                t = " ".join(sorted(set(t.split()) & set(band))) or " ".join(band)
        textures[bar:bar + n] = [t] * n
        previous = t
    plays = {role: [role in (textures[k] or "").split() for k in range(total)] for role in band}
    log.append("textures " + " | ".join(f"{p[3]}: {textures[p[0]]}" for p in parts))
    return textures, plays


def allot(band: list) -> dict:
    """How the eight voices are shared out: the drums two, the bass and the
    melody one each, every upper part one, then the harmony up to three
    and the accompaniment up to two while voices remain, the counter last."""
    out = {}
    if R.DRUMS in band:
        out[R.DRUMS] = 2
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


def plan(models: dict, seed: int, game: str = "", title: str | None = None, max_bars: int | None = None) -> Plan:
    """The skeleton of song `seed` from the tables."""
    rng = random.Random(f"whole:{seed}")
    log = []
    tonic_s, mode = _draw(models, "keys", ("song",), rng, log).split()
    tonic = int(tonic_s)
    bpm = float(_draw(models, "tempos", ("song",), rng, log))
    tempo = rhythm.band(bpm)
    log.append(f"key {harmony.NAMES[tonic]} {mode}, {bpm:.0f} BPM ({tempo})")
    for attempt in range(FORM_TRIES):                       # a form longer than asked is drawn again (the form's own distribution, cut to length)
        form_log = []
        parts = plan_form(models, rng, form_log, max_bars if attempt == FORM_TRIES - 1 else None)
        if max_bars is None or parts[-1][0] + parts[-1][1] <= max_bars:
            break
    log += form_log + ([f"the form drawn {attempt + 1} times to fit {max_bars} bars"] if attempt else [])
    loop_bar = loop_bar_of(parts)
    band, weights = [], {}
    for token in _draw(models, "balance", (rhythm.ARRANGEMENT,), rng, log).split():
        role, _, w = token.partition("=")
        band.append(role)
        if w:
            weights[role] = w
    log.append("band " + " ".join(f"{r}={weights[r]}" if r in weights else r for r in band))
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
        low, high = _draw(models, "registers", (role,), rng, log).split("-")
        registers[role] = (int(low), int(high))
        sounds[role] = float(_draw(models, "sounds", (role,), rng, log))
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
                            "chord_tones": float(_draw(models, "chord_tones", (R.MELODY,), rng, log))}
    for role in band:
        log.append(f"{role}: " + ", ".join(x for x in (
            f"weight {weights[role]}" if role in weights else "", f"register {registers[role]}" if role in registers else "",
            f"sounds {sounds[role]:.1f}" if role in sounds else "", f"habit {habits[role]}",
            " ".join(f"{k} {v}" for k, v in extras.get(role, {}).items()),
            f"plays {sum(plays[role])}/{len(plays[role])} bars") if x))
    return Plan(seed, game, title or f"Whole {seed}", tonic, mode, bpm, parts, loop_bar, names, chords, band, weights, textures, plays,
                registers, sounds, habits, extras, allot(band), log)


def song_of(plan: Plan, kit=()) -> rhythm.Song:
    """The plan as the Song the writers write on: its bars, its chords as
    spans, its form; `kit` the pack's kit pieces (song.pieces)."""
    bars = [(float(METER * k), float(METER * (k + 1))) for k in range(plan.bars)]
    chords = [Span(a, b, c[0], c[1], 1.0) if c else Span(a, b, None, "", 0.0) for (a, b), c in zip(bars, plan.chords)]
    song = rhythm.Song(plan.title, METER, DIVISION, bars, chords, bpm=plan.bpm, sid=plan.sid, game=plan.game,
                       numbers=list(range(plan.bars)), parts=list(plan.parts), tonic=plan.tonic, mode=plan.mode, loop_bar=plan.loop_bar)
    song.pieces = {name: KIT_PIECES[name] for name in kit if name in KIT_PIECES}
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


def write(plan: Plan, song: rhythm.Song, models: dict, seed: int, reference=None) -> dict:
    """The parts written in turn on the song: the drums, the bass, the upper
    parts, the melody; each put into song.notes for the next to read.
    {role: Part}."""
    written, key = {}, (plan.tonic, plan.mode)
    kit_letters = {rhythm.LETTERS[p] for p in song.pieces.values() if p in rhythm.LETTERS}
    if R.DRUMS in plan.band and kit_letters:
        groups = {g: models[name] for g in rhythm.DRUM_GROUPS if (name := "drums-" + "".join(g)) in models and set(g) & kit_letters}
        if groups:
            group_habits = {g: plan.extras.get(R.DRUMS, {}).get("".join(g)) or plan.habits[R.DRUMS] for g in groups}
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
        notes, figures = writer.bass(song, models["bass"], random.Random(f"{seed}:bass"), habit=plan.habits[R.BASS], key=key, lock=lock,
                                     free=True, plays=plan.plays[R.BASS], register=plan.registers[R.BASS][0], sounds=plan.sounds[R.BASS])
        song.notes[R.BASS] = [(a, b - a, m, "bass") for a, b, m in notes]
        written[R.BASS] = Part(R.BASS, [(a, b, m, 0) for a, b, m in notes], figures,
                               [f"habit {plan.habits[R.BASS]}, floor {plan.registers[R.BASS][0]}, {sum(1 for f in figures if f != writer.REST)} bars written, "
                                f"{len(notes)} notes; locked to the band in {len(lock)} bars"])
    for role in rhythm.UPPER:
        if role not in plan.band or not all(k in models for k in ("rhythm", "voicings")):
            continue
        voices = list(range(plan.voices[role]))
        low, high = plan.registers[role]
        registers = {v: (low, high) for v in voices}
        pedals = {v: (low + high) // 2 for v in voices}
        sounds = harness.UPPER_SOUNDS.get(role) or plan.sounds[role]
        lock = locks_of(song, {role}, plan)
        notes, figures, voicings = writer.upper(song, role, voices, registers, models, random.Random(f"{seed}:{role}"), plan.habits[role],
                                                plan.extras[role]["richness"], sounds, key=key, lock=lock, motion=plan.extras[role]["motion"],
                                                pedals=pedals, plays=plan.plays[role])
        song.notes[role] = [(a, b - a, m, role) for a, b, m, _ in notes]
        written[role] = Part(role, notes, [f"{f} / {vc}" for f, vc in zip(figures, voicings)],
                             [f"voices {len(voices)}, register {plan.registers[role]}, habit {plan.habits[role]}, voicing {plan.extras[role]['richness']}, "
                              f"motion {plan.extras[role]['motion']}, sounded {sounds:.2f}; {sum(1 for f in figures if f != writer.REST)} bars written, "
                              f"{len(notes)} notes; locked to the band in {len(lock)} bars"])
    for role in (R.MELODY, R.COUNTER):                    # the counter-line written as the melody is, after it and clear of it
        if role not in plan.band or not all(k in models for k in ("rhythm", "moves", "contours", "endings", "relations", "values")):
            continue
        x = plan.extras[role]
        notes, figures, plog = writer.melody(song, [], plan.registers[role], models, random.Random(f"{seed}:{role}"), plan.habits[role],
                                             key=key, hold=(), reference=reference, articulation=x["articulation"], echo_habit=x["echo"],
                                             recall=models.get("melody_recall"), step_habit=x["steps"], repeat_habit=x["repeats"], plays=plan.plays[role],
                                             role=role, chord_rate=x.get("chord_tones"))
        song.notes[role] = [(a, b - a, m, role) for a, b, m in notes]
        written[role] = Part(role, [(a, b, m, 0) for a, b, m in notes], figures,
                             [f"register {plan.registers[role]}, habit {plan.habits[role]}, " + ", ".join(f"{k} {v}" for k, v in x.items())
                              + f"; {sum(1 for f in figures if f != writer.REST)} bars written, {len(notes)} notes; the reference set "
                              + ("checked" if reference is not None else "not on this machine")] + plog)
    return written


# --- the rendering: the written notes on the pack's samples, through the converter's back end ---

def samples_for(plan: Plan, pack: dict, own: set, pack_name: str, rng: random.Random) -> dict:
    """Each part's sample from the pack's pools: {role: (voice name, ITSample)}; the drums' kit {piece: (name, ITSample)}.
    `own`: the pack file's own sample names (registered as pack_name_voice), the rest built-in voices."""
    from ..instruments import _make_sample

    def make(name):
        return name, _make_sample(f"{pack_name}_{name}" if name in own else name)
    voices = pack["voices"]
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
        names = voices.get(pool) or voices.get("harmony") or voices.get("lead")
        out[role] = make(rng.choice(list(names)))
    return out


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


def score_of(plan: Plan, written: dict, samples: dict, loops: int = 2, fade: float = 2.0, echo: dict | None = None):
    """The written parts as a score (spc.convert.Score) on the pack's
    samples: the form once, then the loop (from the loop's bar to the
    form's end) `loops` - 1 times more, fading at the end; the echo as given
    (echo_of). Returns the score and {role: first voice}."""
    from .. import score as score_mod
    from ..drums import KIT_NOTE
    from ..spc import convert, it_song, notes as notes_mod
    beat_s = 60.0 / plan.bpm
    form_beats = plan.bars * METER
    loop_start = plan.loop_bar * METER
    loop_beats = form_beats - loop_start
    seconds = (form_beats + max(0, loops - 1) * loop_beats) * beat_s
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
    for role, part in written.items():
        if role not in first:
            continue
        for j, offset in enumerate(offsets):
            for n in part.notes:
                a, b = n[0], n[1]
                if j and a < loop_start - 1e-9:
                    continue
                t0, t1 = (a + offset) * beat_s, (b + offset) * beat_s
                if t0 >= seconds:
                    continue
                if role == R.DRUMS:
                    _, _, _, v, kit_name = n
                    name, sample = samples[R.DRUMS][kit_name]
                    put(first[role] + v, role, t0, t1, float(KIT_NOTE), name, sample, v)
                else:
                    name, sample = samples[role]
                    put(first[role] + n[3], role, t0, t1, float(n[2]), name, sample, n[3])
    notes.sort(key=lambda x: (x.start, x.voice))
    tempo, row_hz = it_song.tempo_for(convert.FINE_GRID)
    message = [f"{plan.title} - {harmony.NAMES[plan.tonic]} {plan.mode} - {round(plan.bpm)} BPM - form {plan.letters}",
               "Written by bitComposer from the pack's tables (docs/IDIOM.md, phase 4: the",
               "integration): every part free on a skeleton the tables gave, rendered as a game's song is."]
    score = convert.Score(notes, seconds, n_voices, [(0.0, 127, 127)], fade, plan.title[:25], plan.game, "bitComposer", row_hz, tempo,
                          0.0, 0.0, False, None, pcm_of, key_of, message=message)
    return score, first


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
    return {"chord_tones": on_chord / max(1, len(strong)), "repeats": (len(moves) - len(moving)) / max(1, len(moves)),
            "steps": sum(1 for m in moving if abs(m) <= 2) / max(1, len(moving)), "leaps": sum(1 for m in moving if abs(m) >= 7) / max(1, len(moving)),
            "distinct": len(set(cells[:SPAN])), "echoes": sum(1 for i, c in enumerate(cells) if c in cells[:i]) / max(1, len(cells)),
            "range": max(n[2] for n in line) - min(n[2] for n in line)}


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
            max_bars: int | None = None, loops: int = 2, reference=None, read: bool = True, fade: float = 2.0) -> dict:
    """One whole song: the plan, the parts written, the score (and {role: first voice}), the song read back and its
    measures; {"plan", "song", "written", "score", "first", "samples", "echo", "read", "measures"}."""
    p = plan(models, seed, game, title, max_bars)
    kit = (pack.get("voices") or {}).get("drums") or {}
    song = song_of(p, kit)
    written = write(p, song, models, seed, reference)
    rng = random.Random(f"whole:{seed}:render")
    samples = samples_for(p, pack, own, pack_name, rng)
    echo = echo_of(pack.get("habits") or {}, p.bpm, rng)
    score, first = score_of(p, written, samples, loops=loops, fade=fade, echo=echo)
    out = {"plan": p, "song": song, "written": written, "score": score, "first": first, "samples": samples, "echo": echo, "read": None, "measures": None}
    if read:
        once, _ = score_of(p, written, samples, loops=1, fade=0.0, echo=echo)
        back = read_back(once, p, first, samples)
        out["read"] = back
        out["measures"] = measures(back) if back is not None else None
    return out
