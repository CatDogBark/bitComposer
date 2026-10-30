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
from __future__ import annotations
import math
import random
from fractions import Fraction
import re
import statistics
from collections import Counter
from dataclasses import dataclass, field

from .. import harmony, harness, rhythm, tables, vocab, writer
from ..writer import scale_index, scale_pitch
from .. import roles as R
from ..vocab import Span

from . import plan as plan_mod, measures as measures_mod   # noqa: E402  the package's other sections


# --- the rendering: the written notes on the pack's samples, through the converter's back end ---

REACH = 7                             # semitones a part's top may sit above the best pool sample's game-played range before the pack's
                                      # other tonal samples are tried for it


SPEED_WEIGHT = 3                      # a sample's score loses this a note a second the part's fastest bar runs past the sample's fastest in the game


def builtin_profile(rid: str, pack: str | None = None) -> dict | None:
    """A built-in voice's profile (packs.profile: its range, speed and floor, set for the voice itself), the stand-in for
    the tables' answers about a game's own sample where the sample is a built-in voice (phase 6). `rid` is the id as the
    pool gives it, the set's prefix stripped ("harp" of "ffvi_harp"), so the set's name `pack` puts it back. Before it,
    a written song on a built-in set drew every part's voice at random from its pool: the vocabulary names samples by
    the game's ids, the pool's voices carried none, and the fit found nothing to score."""
    from ...packs import profile
    return (profile(f"{pack}_{rid}") if pack else None) or profile(rid)


def sample_speed(models, rid: str, rng: random.Random, pack: str | None = None) -> tuple[float, float] | None:
    """How fast the game plays a sample, notes a second (the sample_speeds table's class tops): a song's fastest bars on
    it, drawn (a song plays a pad at eight notes a second where most hold it), and the fastest bars of any song; a
    built-in voice's own speed for both; None unknown."""
    t = (models or {}).get("sample_speeds")
    if t is None or t.songs.get((rid,), 0) == 0:
        prof = builtin_profile(rid, pack)
        return (prof["speed"], prof["speed"]) if prof else None
    top = lambda c: float(c) if c != "faster" else 48.0   # noqa: E731
    drawn = t.draw((rid,), rng, floored=False, floor_k=plan_mod.PLAN_FLOOR)
    return top(drawn), max(top(c) for c in (t.votes.get((rid,)) or {drawn: 1}))


def written_speed(plan: plan_mod.Plan, written: dict, role: str, voices: set | None = None) -> float:
    """A written part's fastest bar, notes a second, over its voices (`voices`: a set of voice indices, all without)."""
    if role not in written:
        return 0.0
    counts = Counter((n[3], int(n[0] // plan_mod.METER)) for n in written[role].notes if voices is None or n[3] in voices)
    return max(counts.values(), default=0) * plan.bpm / (60.0 * plan_mod.METER)


def floors_for(plan: plan_mod.Plan, written: dict, samples: dict, models: dict | None, pack_name: str, rng: random.Random) -> dict:
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
        beside = {v for v, w in enumerate(plan_mod.layers_of(plan, role), start=1) if not w.startswith("doubling")}
        voices = beside if which == "second" else ({0} | ({v for v in range(1, plan.voices.get(role, 1))} - beside))
        fastest[chosen[0]] = max(fastest.get(chosen[0], 0.0), written_speed(plan, written, role, voices))
    return {name_: sample_floor(models, raw(name_), rng, speed if written else None, pack=pack_name) for name_, speed in fastest.items()}


def sample_floor(models, rid: str, rng: random.Random, speed: float | None = None, pack: str | None = None) -> float:
    """The shortest note the game plays a sample at, in seconds (the sample_lengths table's class top); 0 unknown. `speed`:
    the fastest bar of the part playing it, notes a second: the floor is drawn under the sample's speed class (round 36),
    a fast part taking a fast song's floor. A floor drawn by the sample alone had taken a slow song's 120 ms for Whole 02's
    string pad at sixteenths, raising the notes round 35 had shortened to 50 ms back past where they were."""
    t = (models or {}).get("sample_lengths")
    if t is None or t.songs.get((rid,), 0) == 0:
        prof = builtin_profile(rid, pack)
        return prof["floor"] if prof else 0.0
    context = (rid, rhythm.speed_tier(speed)) if speed is not None else (rid,)
    drawn = t.draw(context, rng, floored=False, floor_k=plan_mod.PLAN_FLOOR)
    return (float(drawn) if drawn != "long" else 400.0) / 1000.0


def best_sample(ranges, names: list, register: tuple, rng: random.Random, raw, others: list = (), speed: float = 0.0, models: dict | None = None,
                drawn: dict | None = None, role: str | None = None, pack: str | None = None) -> str:
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
        if ranges is not None and ranges.songs.get((rid,), 0):
            lo, hi = (int(x) for x in ranges.draw(range_context(rid, role), rng, floored=False, floor_k=plan_mod.PLAN_FLOOR).split("-"))
        else:
            prof = builtin_profile(rid, pack)           # a built-in voice: its own range (phase 6)
            if prof is None:
                return None
            lo, hi = prof["range"]
        if drawn is not None:
            drawn[rid] = (lo, hi)
        a, b = register
        fastest = sample_speed(models, rid, rng, pack)       # the part's fastest bar against the sample's fastest in the game
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


def second_register(plan: plan_mod.Plan, role: str) -> tuple:
    """The register of a layered part's first voice beside the line, as write() gives it: the part's at the layer word's
    offset (apart), or the part's own (alternating)."""
    low, high = plan.registers[role]
    for w in plan_mod.layers_of(plan, role):
        rel = plan_mod.layer_of({"layer": w})
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
    lo, hi = (int(x) for x in ranges.draw(range_context(rid, role), rng, floored=False, floor_k=plan_mod.PLAN_FLOOR).split("-"))
    if drawn is not None:
        drawn[rid] = (lo, hi)
    if min(hi, register[1]) - max(lo, register[0]) >= plan_mod.MIN_SPAN:   # the voice is then written in the overlap (bound_of): a planned
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
    if hi - lo < plan_mod.MIN_SPAN:
        centre = (lo + hi) / 2
        lo = int(max(played[0], min(centre - plan_mod.MIN_SPAN / 2, played[1] - plan_mod.MIN_SPAN)))
        hi = int(min(played[1], lo + plan_mod.MIN_SPAN))
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
    pair = t.draw((role,), rng, floored=False, floor_k=plan_mod.PLAN_FLOOR, min_songs=plan_mod.PLAN_SONGS).split()
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
    weights = t.weights((R.COUNTER, tune), floor_k=plan_mod.PLAN_FLOOR, min_songs=plan_mod.PLAN_SONGS)
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
    fine = t.votes.get((R.COUNTER, tune), {}) if t.songs.get((R.COUNTER, tune), 0) >= plan_mod.PLAN_SONGS else {}
    return sid, "tune" if sid in fine else "part", over


def _weighted(rng: random.Random, options: list, weights: list):
    """One of the options by their weights."""
    x = rng.random() * sum(weights)
    for o, w in zip(options, weights):
        x -= w
        if x < 0:
            return o
    return options[-1]


def wide_enough(models: dict | None, rid: str, played: tuple | None, role: str, log: list, pack: str | None = None) -> tuple | None:
    """A chord part's home band (the ranges word's draw) where it is at least MIN_SPAN wide, else the sample's whole played
    range (sample_ambitus) in its place (round 53): a song that strikes a sample at one pitch had bound a three-voice
    accompaniment to that pitch for 45 bars. A sample the game only ever plays at one pitch (a drum sample as a rhythmic
    chord part, FFVI's accompaniment in 0.08 of songs) keeps its one pitch: that is how the game plays it."""
    if played is None or played[1] - played[0] >= plan_mod.MIN_SPAN:
        return played
    whole_range = ambitus_of(models, rid, pack=pack)
    if whole_range is None or whole_range == tuple(played):
        return played
    log.append(f"{role}'s home band on {rid} {played} is under {plan_mod.MIN_SPAN} semitones: bound by the sample's whole range {whole_range}")
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


def ambitus_of(models: dict | None, rid: str, rng: random.Random = None, pack: str | None = None) -> tuple | None:
    """The whole range the game ever played a sample over (sample_ambitus, round 43): the lowest low and the highest high
    of the word's outcomes for it, not one song's draw. A tune's register is its balance token's (one song's ambitus,
    20 semitones at FFVI's median), and a bound drawn from another song's ambitus and cut against it had left the
    tune the overlap of two songs' ranges (Whole 38: 76-84 of a planned 76-92); the sample's wall is where the game
    took it at all. None without the word, or for a sample it has no song for."""
    t = (models or {}).get("sample_ambitus")
    t = t.table if hasattr(t, "table") else t
    if t is None or not t.songs.get((rid,), 0):
        prof = builtin_profile(rid, pack)               # a built-in voice: its whole range is where it sounds right
        return prof["range"] if prof else None
    spans = [tuple(int(x) for x in o.split("-")) for o in t.votes.get((rid,), {})]
    if not spans:
        return None
    return min(lo for lo, _ in spans), max(hi for _, hi in spans)


def samples_for(plan: plan_mod.Plan, pack: dict, own: set, pack_name: str, rng: random.Random, models: dict | None = None) -> dict:
    """Each part's sample from the pack's pools: {role: (voice name, ITSample)}; the drums' kit {piece: (name, ITSample)}.
    `own`: the pack file's own sample names (registered as pack_name_voice), the rest built-in voices. With the pack's
    ranges table, a pitched part takes a sample of its pool the game played in the part's register (the pool's own
    weights among those), fitted for speed to the part's drawn fastest bar (part_speeds); the pool's draw where none is
    known to fit. Chosen BEFORE the writing (round 34): the range drawn for the chosen sample is the register the voice
    is then written in (plan.bounds, bound_of), so every voice plays where the game plays its sample. The sample had
    come after the writing, fitted to the written notes' speed, and three rules with a fold had covered the seam."""
    from ...instruments import _make_sample

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
                slot = plan_mod.KIT_SLOT.get(letter)
                if slot and sid in own:
                    out[role][slot] = make(sid)
                    taken.append(f"{slot} {sid}")
                    if slot == "hihat" and "open_hihat" in out[role]:
                        out[role]["open_hihat"] = make(sid)
            if taken:
                plan.log.append("kit samples from the balance's song: " + ", ".join(taken))
            continue
        pool = plan_mod.POOLS.get(role)
        if role == R.BASS:
            pool = plan_mod.BASS_POOLS.get(plan.weights.get(R.BASS, "half"), "bass_medium")
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
                drawn[given] = tuple(int(x) for x in ranges.draw(range_context(given, role), rng, floored=False, floor_k=plan_mod.PLAN_FLOOR).split("-"))
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
                    drawn[sid] = tuple(int(x) for x in ranges.draw(range_context(sid, role), rng, floored=False, floor_k=plan_mod.PLAN_FLOOR).split("-"))
        if role not in out:
            out[role] = make(best_sample(ranges, names, register, rng, raw, tonal, speed=plan.speeds.get(role, 0.0), models=models, drawn=drawn, role=role,
                                         pack=pack_name)
                             if register else rng.choice(names))
            if register:
                fit = drawn.get(raw(out[role][0]))
                plan.log.append(f"{role}'s voice {out[role][0]} by the pool rule for {register[0]}-{register[1]} at {plan.speeds.get(role, 0.0):.1f} a second"
                                + (f": it plays {fit[0]}-{fit[1]}" if fit else ": nothing known of its range, drawn from the pool"))
        if register:
            played = drawn.get(raw(out[role][0]))
            if role in (R.MELODY, R.COUNTER):               # a tune's bound is the whole range the game took the sample over (round 43)
                played = ambitus_of(models, raw(out[role][0]), pack=pack_name) or played
            else:
                played = wide_enough(models, raw(out[role][0]), played, role, plan.log, pack=pack_name)
            plan.bounds[role] = bound_of(played, register)
        # a layered part apart: its line and its second voice on the game's own pair of samples (layer_samples) where the
        # pack holds both and each reaches its voice's register; else the second voice's sample by its own register and
        # speed, as the line's is chosen
        if any(not w.startswith("doubling") for w in plan_mod.layers_of(plan, role)) and role in plan.registers:
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
                plan.bounds[role] = bound_of(wide_enough(models, pair[0], drawn.get(pair[0]), role, plan.log, pack=pack_name), plan.registers[role])
            if second is None:
                second = make(best_sample(ranges, names, reg2, rng, raw, tonal, speed=plan.speeds.get(role, 0.0), models=models, drawn=drawn, role=role, pack=pack_name))
            out[f"{role}:second"] = second
            plan.bounds[f"{role}:second"] = bound_of(wide_enough(models, raw(second[0]), drawn.get(raw(second[0])), f"{role}:second", plan.log, pack=pack_name), reg2)
    floors, fastest = {}, {}                                # each chosen sample's shortest note in the game (sample_lengths): a note's floor on
    for key, chosen in list(out.items()):                   # it, under the speed class of the fastest part it serves (round 36)
        if isinstance(chosen, tuple):
            fastest[chosen[0]] = max(fastest.get(chosen[0], 0.0), plan.speeds.get(key.split(":")[0], 0.0))
    for name_, speed in fastest.items():
        floors[name_] = sample_floor(models, raw(name_), rng, speed if plan.speeds else None, pack=pack_name)
    out["floors"] = floors
    if plan.bounds:
        plan.log.append("written where the game plays each sample: " + ", ".join(f"{k} {lo}-{hi}" for k, (lo, hi) in plan.bounds.items()))
    return out


def models_or_empty(models) -> dict:
    return models or {}


def echo_of(habits: dict, bpm: float, rng: random.Random) -> dict | None:
    """The echo as the pack's habits give it (score.of_song's reading of the generator's): None for a dry song."""
    from ...echo import ECHO_DELAYS, ECHO_WETNESS
    from ...score import ECHO_STEP, ECHO_WET
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


def voice_map(plan: plan_mod.Plan, written: dict) -> dict:
    """The score's voices: {role: first voice}, the parts in the band's order, each its allotted voices."""
    out, n = {}, 0
    for role in plan.band:
        if role in written and written[role].notes:
            out[role] = n
            n += plan.voices[role]
    return out


def note_level(plan: plan_mod.Plan, role: str, voice: int, second_voice: dict | None = None, bar: int | None = None) -> float:
    """A note's level of full: the part's share of the song's loudest part's (plan.levels: the balance token's where its
    song has the part, so the band's levels are one FFVI song's as one unit and the loudest part plays at TOP_LEVEL and
    the rest at their share; the `levels` table's for a part the token lacks; the counter-line's from counter_shares
    under the tune's share band; LEVELS without a levels word), a voice beside the line at its own share of the line's
    (the balance token's share for that voice where its song has the part layered, plan.voice_levels by rank, so the
    line and the voices beside it are one FFVI song's together; the layer_levels draw for a voice the token has no share
    for; `second_voice` those voices by part, layers_of's apart and alternating voices; a doubling voice plays the line's
    level). Never under 0.05 nor over 1.0 of full: a share is at most 1.0, so only a second voice over 1.0 of its line
    can reach the cap."""
    base = plan.top_level * plan.levels[role] if role in plan.levels else plan_mod.LEVELS[role]   # the loudest part at the song's top level (round 52)
    if bar is not None and role in plan.section_levels and 0 <= bar < len(plan.section_levels[role]):
        base *= plan.section_levels[role][bar]              # the section's level over the part's (section_levels, round 48)
    if second_voice is None:
        second_voice = {role: {v for v, w in enumerate(plan_mod.layers_of(plan, role), start=1) if not w.startswith("doubling")}}
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


def score_of(plan: plan_mod.Plan, written: dict, samples: dict, loops: int = 2, fade: float = 2.0, echo: dict | None = None, tail_bars: int = 0, pack_name: str = "",
             master: tuple | None = None):
    """The written parts as a score (spc.convert.Score) on the pack's
    samples: the form once, then the loop (from the loop's bar to the
    form's end) `loops` - 1 times more, fading at the end; with
    `tail_bars`, the loop's first bars once more after the last pass,
    fading through them, so a listener hears the song come back round to
    its hook; the echo as given (echo_of). Returns the score and {role:
    first voice}."""
    floors = samples.get("floors") or {}
    second_voice = {role: {v for v, w in enumerate(plan_mod.layers_of(plan, role), start=1) if not w.startswith("doubling")}   # a layered part's own
                    for role in plan.band if role != R.DRUMS}                                                            # lines, on their sample
    from ... import score as score_mod
    from ...drums import KIT_NOTE
    from ...spc import convert, it_song, notes as notes_mod
    beat_s = 60.0 / plan.bpm
    form_beats = plan.bars * plan_mod.METER
    loop_start = plan.loop_bar * plan_mod.METER
    loop_beats = form_beats - loop_start
    tail = min(max(0, tail_bars), plan.bars - plan.loop_bar) * plan_mod.METER
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

    from ... import samples as samples_mod

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
        pan = plan_mod.PANS[role][j % len(plan_mod.PANS[role])]
        send = echo is not None and role in plan_mod.SENDS
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
                    put(first[role] + n[3], role, t0, t1, float(n[2]), name, sample, n[3], int(a // plan_mod.METER))   # the bar's section level (round 48)
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
        plan.log.append(f"master: the mix estimated at {estimate:.1f} dB renders near {estimate + plan_mod.RENDER_BRIDGE:.1f} dBFS against the song's "
                        f"{plan.loudness:.0f}: master {master} of 127" + (f", notes raised {20 * math.log10(gain_up):.1f} dB" if gain_up > 1.0 else ""))
    message = [f"{plan.title} - {harmony.NAMES[plan.tonic]} {plan.mode} - {round(plan.bpm)} BPM - form {plan.letters}",
               "Written by bitComposer from the pack's tables (docs/IDIOM.md, phase 4: the",
               "integration): every part free on a skeleton the tables gave, rendered as a game's song is."]
    score = convert.Score(notes, seconds, n_voices, [(0.0, master, master)], fade, plan.title[:25], plan.game, "bitComposer", row_hz, tempo,
                          0.0, 0.0, False, None, pcm_of, key_of, message=message)
    return score, first


def layer_class(plan: plan_mod.Plan, role: str) -> str:
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
    factor = 10 ** ((target - (estimate + plan_mod.RENDER_BRIDGE)) / 20)
    if factor <= 1.0:
        return max(plan_mod.MASTER_FLOOR, round(127 * factor)), 1.0
    return 127, factor


def stems_of(plan: plan_mod.Plan, written: dict, samples: dict, out_dir: str, loops: int = 1, fade: float = 3.0, echo: dict | None = None,
             tail_bars: int = 0, pack_name: str = "") -> list[str]:
    """Each written part alone as a module of its own (`<title> <part>.it`),
    for a page that plays the parts in sync and switches each: the same
    length, echo and samples as the whole, so their sum is the whole.
    Returns the paths."""
    import os
    from ...spc import convert
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


def read_back(score, plan: plan_mod.Plan, first: dict, samples: dict) -> rhythm.Song | None:
    """The score read by the readers on the plan's own beat, the roles the
    plan's (its voices are known), the kit's pieces the pack's: the Song
    the measures are taken on; None where the readers kept nothing."""
    from .. import beat, reading, store
    from .. import roles as roles_mod
    period = 60.0 / plan.bpm
    n = max(2, int(math.ceil(score.seconds / period)) + 1)
    beats = [k * period for k in range(n)]
    section = beat.Section(0.0, beats[-1], period / plan_mod.DIVISION, 0.0, first=0.0, meter=plan_mod.METER, downbeat=0, division=plan_mod.DIVISION)
    grid = beat.Grid(period / plan_mod.DIVISION, plan_mod.DIVISION, [section], beats, [t for t in beats[::plan_mod.METER] if t < score.seconds - 1e-6], 1.0, 0.5)
    r = reading.of_score(score, game=plan.game, title=plan.title, grid=grid)
    if r.grid is None:
        return None
    r.file, r.folder = f"{plan.title}.whole", plan.game
    role_of = {first[role] + v: role for role in first for v in range(plan.voices[role])}
    pieces = {name: plan_mod.KIT_PIECES[piece] for piece, (name, _) in samples.get(R.DRUMS, {}).items()}
    r.roles = [roles_mod.Role(v, role) for v, role in sorted(role_of.items())]
    for p in r.song.notes:
        if p.sample is not None:
            p.sample.piece = pieces.get(p.sample.key, "none") if role_of.get(p.voice) == R.DRUMS else "none"
    db = store.connect(":memory:")
    store.keep(db, r)
    songs, _ = rhythm.load(db)
    db.close()
    return songs[0] if songs else None
