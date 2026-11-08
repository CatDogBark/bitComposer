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

from . import render as render_mod   # noqa: E402  the package's other sections


METER = 4                             # beats a bar: the form and texture tables were kept at one meter (FFVI: 64 of its 69 metered songs)
DIVISION = 12                         # grid steps a beat: sixteenths and triplets both, so any figure the tables know fits
VOICES = 8                            # the SNES chip's voices
LETTERS = "ABCDEFGHIJKLMNOP"          # the form's labels
MAX_PARTS = 12
DRUM_VOICES = (("K", "S", "t"), ("h", "c", "o"))   # the kit on two voices: the kick, snare and toms; the hat, cymbals and the rest
                                      # (the fallback since round 87: a token's kit sits on the channels its game song gave it, extras.drums.channels)


def kit_second_pick(models: dict, letter: str, place: str, run: list, share: float, rng: random.Random) -> bool:
    """Whether a kit letter's hit takes the slot's second sample (round 99): the kit_seconds word's draw under the letter and
    the hit's place in the beat, none while the letter's hits so far are over the token's share for the second; `run` the
    letter's [hits on the second, hits] so far, kept here. Without the word no hit takes it."""
    t = (models or {}).get("kit_seconds")
    pick = False
    if t is not None and (run[1] == 0 or run[0] / run[1] <= share):
        t = t.table if hasattr(t, "table") else t
        pick = t.draw((letter, place), rng, floored=False, floor_k=1, min_songs=PLAN_SONGS) == "second"
    run[1] += 1
    run[0] += int(pick)
    return pick


def drum_voice_of(channels, letter: str, voices: int = 2) -> int:
    """The kit voice a piece letter plays on (round 87): the token's channel whose pieces include it ("KS|h": K and S on the
    first, h on the second), the fixed split (DRUM_VOICES) where the token carries no channels or the letter is on none,
    never past the kit's voices."""
    v = next((i for i, g in enumerate(channels or ()) if letter in g), None)
    if v is None:
        v = next((i for i, g in enumerate(DRUM_VOICES) if letter in g), 1)
    return max(0, min(max(1, voices) - 1, v))
SECOND_SLOT = "2"                     # a kit slot's second sample plays as the slot's name with this suffix ("hihat2"; round 99)
KIT_PIECES = {"kick": "kick", "snare": "snare", "hihat": "hat", "open_hihat": "hat", "tom": "tom", "crash": "cymbal", "rim": "other"}   # a pack's kit -> the readings' pieces
KIT_PIECES.update({name + SECOND_SLOT: piece for name, piece in list(KIT_PIECES.items())})   # a slot's second sample is the same piece (round 99)
KIT_SLOT = {"K": "kick", "S": "snare", "h": "hihat", "t": "tom", "c": "crash", "o": "rim"}   # a piece letter -> the pack kit slot its song's sample fills (round 63)
SLOT_LETTER = {slot: letter for letter, slot in KIT_SLOT.items()} | {"open_hihat": "h"}   # a kit slot -> the piece letter whose level it plays at (round 68:
                                                                                          # the open hat takes the hat's sample and its level with it)


def slot_letter(slot: str) -> tuple:
    """A kit slot's name as (its piece letter, whether it is the slot's second sample): "hihat" -> ("h", False), "hihat2" ->
    ("h", True); (None, False) for a name no letter plays (round 99)."""
    second = slot.endswith(SECOND_SLOT) and slot[:-len(SECOND_SLOT)] in SLOT_LETTER
    return SLOT_LETTER.get(slot[:-len(SECOND_SLOT)] if second else slot), second


def kit_second(plan, slot: str) -> dict | None:
    """The balance token's second sample for the slot's letter (round 99): {"sample": the pack id, "level": its share of the
    loudest part's or None, "rate": the chip's rate as a note or None, "degree": ("d"/"c", steps) or None, "pitch": an
    absolute note or None, "hold": beats or None, "share": its share of the letter's hits}; None without one."""
    letter, _ = slot_letter(slot)
    return (plan.extras.get(R.DRUMS, {}).get("kit_seconds") or {}).get(letter) if letter else None


def _second_or(plan, slot: str, field: str, own):
    """A second slot's own value for `field` where the token carries one, else `own` (the letter's main value)."""
    _, second = slot_letter(slot)
    if second:
        x = kit_second(plan, slot)
        if x is not None and x.get(field) is not None:
            return x[field]
    return own


def kit_piece_level(plan, slot: str) -> float | None:
    """The balance token's own level for the kit slot's piece, as a share of the song's loudest part's (round 68:
    `K=sbfe716b9b6@1.7` on the drums' kit field); None for a slot the token gave no level, which plays at the part's."""
    levels = plan.extras.get(R.DRUMS, {}).get("kit_levels") or {}
    letter, _ = slot_letter(slot)
    return _second_or(plan, slot, "level", levels.get(letter) if letter else None)


def kit_piece_pitch(plan, slot: str) -> int | None:
    """The note the balance token's song strikes the kit slot's piece at most (round 75: `o=sf89f5aedfd@0.38@62` on the
    drums' kit field, after the level's slot); None where the token gave none."""
    pitches = plan.extras.get(R.DRUMS, {}).get("kit_pitches") or {}
    letter, second = slot_letter(slot)
    if second:                                              # a second slot's own note, or none: never the main's (round 99)
        return (kit_second(plan, slot) or {}).get("pitch")
    return pitches.get(letter) if letter else None
def kit_piece_rate(plan, slot: str) -> int | None:
    """The rate the balance token's song strikes the kit slot's piece at most, as a note (round 78: `c=s3bfa4539ca@0.96@r48`
    on the drums' kit field, 60 the sample as recorded, 48 an octave under; a piece the namer called a drum); None where the
    token gave none."""
    rates = plan.extras.get(R.DRUMS, {}).get("kit_rates") or {}
    letter, second = slot_letter(slot)
    if second:
        return (kit_second(plan, slot) or {}).get("rate")
    return rates.get(letter) if letter else None


def kit_piece_degree(plan, slot: str) -> tuple | None:
    """A tonal kit piece's struck note as a degree of the balance token's song's key (round 79: `o=sfd6accf98a@2.08@d9@0.19`
    on the drums' kit field): ("d", scale steps from the tonic) or ("c", semitones from it, off the scale); None where the
    token gave none (an absolute note, kit_piece_pitch, or nothing)."""
    degrees = plan.extras.get(R.DRUMS, {}).get("kit_degrees") or {}
    letter, second = slot_letter(slot)
    if second:
        return (kit_second(plan, slot) or {}).get("degree")
    return degrees.get(letter) if letter else None


def kit_piece_tuned(plan, slot: str) -> bool:
    """Whether the game tunes the kit slot's percussion sample to the key (round 79: `r63t`): its rate then moves with the
    written key."""
    letter, second = slot_letter(slot)
    if second:
        return bool((kit_second(plan, slot) or {}).get("tuned"))
    return bool(letter) and letter in (plan.extras.get(R.DRUMS, {}).get("kit_tuned") or ())


def kit_token_key(plan) -> tuple | None:
    """The balance token's song's key, (tonic pitch class, "major"/"minor"), round 79; None for a token without one."""
    return plan.extras.get(R.DRUMS, {}).get("token_key")


def kit_piece_hold(plan, slot: str) -> float | None:
    """How long the balance token's song keys the kit slot's piece for, in beats (round 77: `o=sf89f5aedfd@0.38@62@0.25` on
    the drums' kit field, after the note's slot); None where the token gave none. The writer gives the hold to a piece on a
    sustaining sample (samples_for's tonal_slots); a percussion one-shot plays out whatever the count, as before."""
    holds = plan.extras.get(R.DRUMS, {}).get("kit_holds") or {}
    letter, second = slot_letter(slot)
    if second:
        return (kit_second(plan, slot) or {}).get("hold")
    return holds.get(letter) if letter else None


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
RENDER_BRIDGE = -17.4                 # dB: what a written song renders at (RMS dBFS over its first minute, the Song Check method) less its mix
                                      # estimate (rhythm.mix_level over the notes as scored), at a full master: measured over 20 written songs
                                      # 2026-10-29 (median -21.7 once the sample loudness read the sustain loop, quartiles -23.0 and -19.8;
                                      # -20.5 before it); the master brings estimate + bridge to the token's song's rendered loudness. Read
                                      # again if the estimate or the renderer changes. 2026-10-30: -17.4. Those 20 songs had rendered with
                                      # every sustaining voice as a one-shot (score._Pcm read the plain loop flag alone); with the sustain
                                      # loops carried, Song Check 53's ten seeds rendered a median 4.3 dB over their targets (quartiles
                                      # +3.7 and +4.7), so the bridge moves by that much.
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
            "chord_tones": str(writer.CHORD_ON_BEAT), "part_textures": None, "section_levels": "1.0", "section_densities": "d=", "top_levels": str(TOP_LEVEL), "kit_pieces": "KShtco",
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
GROUP_HABIT_FLOOR = 2                 # a drum group's habit draw is terminal at (part, classes): the group's backbone class (round 81)
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
    token_gap_shares: dict = field(default_factory=dict)   # a chord part or the bass -> {gap class: the token song's line's share, or None} (round 95):
                                      # the song's own note lengths for the part's only or line voice, kept over the gap_sounds draws
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
    section_densities: dict = field(default_factory=dict)   # a part -> [its density tier's shift a bar: +1, 0, -1] (section_densities, round 101:
                                      # a section's density against the part's, drawn a part an own section by the step its level makes;
                                      # the writers shift the habit's tier for those bars, habit_at_for)
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
    sample_ranges: dict = field(default_factory=dict)   # a part -> the range its token song plays the token's sample over (round 86): the voice on
                                      # that sample is bound there (render.samples_for), never to another song's range drawn for the sample
    layer_ranges: dict = field(default_factory=dict)    # a layered part -> each voice beyond the line's range on its own token sample, or None
    layer_relations: dict = field(default_factory=dict)  # a layered part -> each voice beyond the line's relation word by stretch (the sixth field's
                                      # fifth sub-field, round 90: "ox9>dm-12x14>o", what it does beside which part, bar by bar), or None
    stretches: dict = field(default_factory=dict)       # a pitched part -> its line's instrument by stretch (the eleventh field, round 91): [(sample,
                                      # (low, high) or None, bars or None)] in time order, the last open; samples_for sets extras[part]["stretch_*"]
    layer_stretches: dict = field(default_factory=dict)  # a layered part -> each voice beyond the line's instrument by stretch (the sixth field's sixth
                                      # sub-field, round 92), the same shape, or None
    pans: dict = field(default_factory=dict)          # a pitched part -> its voices' pans, the right side's share, the line first (the balance
                                      # token's tenth field, round 84); render.pan_of pans a voice there, by plan.PANS without the field; a
                                      # voice in two places keeps the token's word, "0.60x5|0.45x13" or "0.35x4>0.65" (round 85)

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
                "sounds": self.sounds, "habits": self.habits, "extras": self.extras, "voices": self.voices, "log": self.log, "feel": self.feel, "pans": self.pans,
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


def _draw_values(models: dict, name: str, values: dict, rng: random.Random, log: list | None = None, floor_k: int | None = None) -> str:
    """_draw with the context built from the table's own conditionings (round 81): a table fitted before a conditioning
    was added keeps its shape, and a value it does not condition on is dropped rather than misread as another. `floor_k`
    as _draw's: the level the draw is terminal at when seen (the group habits' class level: a dense hat's habit is drawn
    among dense hats' habits, never the part's root, whose sparse habit had capped the hat to silence)."""
    t = models.get(name)
    if t is None:
        return _draw(models, name, (values["part"],), rng, log)
    t = t.table if hasattr(t, "table") else t
    return _draw(models, name, tuple(values.get(c, "?") for c in t.conditionings), rng, log, floor_k=floor_k)


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


def plan_loop(models: dict, parts: list, rng: random.Random, log: list) -> int:
    """The bar the loop returns to (round 98): the form's part the loop_parts word draws, by whether the form opens with an
    intro (a first part it never comes back to), that part's first bar; loop_bar_of's rule without the word, or for a
    part the form has not. FFVI returns to its intro in 15 of 53 intro songs where the rule never did."""
    bar = loop_bar_of(parts)
    if "loop_parts" not in render_mod.models_or_empty(models):
        return bar
    intro = len(parts) > 1 and parts[0][3] not in {p[3] for p in parts[1:]}
    drawn = _draw(models, "loop_parts", ("form", "intro" if intro else "none"), rng, log)
    idx = int(drawn) if drawn.isdigit() else None
    if idx is not None and idx < len(parts):
        bar = parts[idx][0]
        log.append(f"loop (loop_parts): back to part {idx + 1} of {len(parts)}, bar {bar + 1}" + (" (an intro)" if intro else ""))
    else:
        log.append(f"loop (loop_parts): part {drawn} drawn, the form has {len(parts)}: the rule's bar {bar + 1}")
    return bar


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


def plan_section_densities(models: dict, parts: list, band: list, plays: dict, section_levels: dict, rng: random.Random, log: list) -> dict:
    """Each pitched part's density tier shift a bar but the counter's (section_densities, round 101): drawn a part an own section it plays in,
    by the part and the step the section's level makes (level_step of the section_levels draw, "same" without one): "d+"
    a tier denser than the song's, "d-" a tier sparser, "d=" the song's; a repeated section copies its source's. Drawn on
    an own stream (`whole:{seed}:section densities`). Returns {part: [shift a bar]}; logs the sections off the song's tier.
    FFVI's level steps ride a density change more often than not (the accompaniment's), and a quarter of its level-1.0
    sections change tier too; the written parts had kept one density all song."""
    total = parts[-1][0] + parts[-1][1]
    out = {role: [0] * total for role in band if role not in (R.DRUMS, R.COUNTER)}   # the counter follows the tune's figures (its masks):
    said = []                                                                        # no tier of its own to shift; FFVI's counter steps are mostly bare
    for i, (bar, n, of, letter) in enumerate(parts):
        for role in out:
            if of is not None:
                src = parts[of][0]
                out[role][bar:bar + n] = out[role][src:src + n]
                continue
            if not any(plays[role][bar:bar + n]):
                continue
            levels = section_levels.get(role)
            ratio = levels[bar] if levels and bar < len(levels) else 1.0
            tier = _draw(models, "section_densities", (role, rhythm.level_step(ratio)), rng, log)
            shift = 1 if tier == "d+" else -1 if tier == "d-" else 0
            if shift:
                out[role][bar:bar + n] = [shift] * n
                said.append(f"{role} {'denser' if shift > 0 else 'sparser'} in {letter}" + (f" (level {ratio:.1f})" if abs(ratio - 1.0) > 1e-9 else ""))
    if said:
        log.append("densities by section (section_densities): " + "; ".join(said))
    return out


def habit_at_for(plan, role: str, habit=None):
    """A part's habit a bar for its writer (round 101): the song's habit with its density tier shifted where the
    section_densities draw says; None where no bar shifts (the writer keeps its one habit)."""
    shifts = plan.section_densities.get(role)
    if not shifts or not any(shifts):
        return None
    base = habit if habit is not None else plan.habits[role]
    return lambda k: rhythm.shift_habit(base, shifts[k] if 0 <= k < len(shifts) else 0)


def envelope_at_for(plan, role: str, habit=None):
    """A part's figure envelope a bar for its writer (round 101): the onsets a bar the section_densities shift asks
    (rhythm.density_bounds: a tier denser, DENSITY_STEP times the tier's typical or more; a tier sparser, the typical over
    it or fewer), None for a bar without a shift; None where no bar shifts."""
    shifts = plan.section_densities.get(role)
    if not shifts or not any(shifts):
        return None
    base = habit if habit is not None else plan.habits[role]
    return lambda k: rhythm.density_bounds(base, shifts[k] if 0 <= k < len(shifts) else 0)


def allot(band: list, counts: dict | None = None, drum_voices: int = 2) -> dict:
    """How the eight voices are shared out. With the balance's counts (a
    song's voices a part, FFVI: the accompaniment and the counter-line two
    each as often as not), each pitched part takes its count and the drums
    `drum_voices` (the token's kit channels since round 87, two before: a
    one-channel kit given two had cost a pitched voice in 14 of FFVI's 48
    kit songs), trimmed from the largest parts down while the eight are passed.
    Without counts: the drums two, the bass and the melody one each, every
    upper part one, then the harmony up to three and the accompaniment up
    to two while voices remain, the counter last."""
    out = {}
    if R.DRUMS in band:
        out[R.DRUMS] = max(1, drum_voices)
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
    """A line again at an interval, in the scale (a third, fourth or fifth stays diatonic), on another voice; at a unison or
    octaves (a double) the line's notes exactly, off the scale where the line is (round 94: a double put back on the scale
    had sat a semitone from the tune's altered notes once round 93 let the tune off the scale, 22 of a counter voice's 55
    strong onsets in First Meridian Return; FFVI's doublings leave the scale with the tune)."""
    steps = int(round(interval * 7 / 12))
    if steps % 7 == 0:
        return [(a, b, float(int(round(m)) + 12 * (steps // 7)), voice) for a, b, m, *_ in notes]
    return [(a, b, float(scale_pitch(scale_index(int(round(m)), scale) + steps, scale)), voice) for a, b, m, *_ in notes]


PARALLEL_FLOOR = 2                    # a parallel voice's interval draw never backs off below (interval, tone): the nominal interval and the
                                      # chord decide where the voice lands (round 97); the part and the interval before are taken where they reach


def parallel(notes: list, interval: int, scale: set, voice: int, song=None, role: str | None = None, models: dict | None = None,
             rng: random.Random | None = None, clash_rates: dict | None = None, log: list | None = None) -> list:
    """A line again at an interval on another voice, as the game's parallel voices sit (round 97): at each note where
    the voice's note sits against the chord is drawn from the parallel_intervals word by the stretch's nominal interval
    in scale steps, the tone class of the line's note against the chord sounding and the landing before (START at the
    first): a chord tone (root, third, fifth, seventh, sus), placed as that tone of the chord nearest the line's note at
    the nominal interval (the chord's own third or fifth, major or minor), or semitones from the line's note (`+4`) off
    the chord; `diatonic` without the word (or a song, or a stream), under a note no chord fits, and at a unison or
    octaves (a double: the line exactly). FFVI's parallel voice sits at its nominal semitones on 0.61 of its shared onsets and
    on a chord tone on 0.62, where the line again in the scale matched it on 0.31 and landed on the chord on 0.42: a
    third over the chord's third is a major third or a minor sixth (the root), over the fifth a fourth (the root again)
    or a minor third (the seventh). A chord part's voice with `clash_rates` (the part's clashes draw) holds the share
    as the part's other voices do: an interval a semitone from a part written before the part (rhythm.clash_under)
    while the voice is over its share for the beat is drawn again, VOICE_TRIES times, the last kept."""
    t = (models or {}).get("parallel_intervals")
    steps = int(round(interval * 7 / 12))
    if t is None or song is None or rng is None or steps % 7 == 0:
        return diatonic(notes, interval, scale, voice)
    t = t.table if hasattr(t, "table") else t
    nominal = str(R.generic(interval))
    hold = bool(clash_rates) and role in rhythm.UPPER
    under = sorted(n for r in rhythm.clash_under(role) for n in song.notes.get(r, [])) if hold else []
    run = {"strong": [0, 0], "weak": [0, 0]}                # the voice's onsets a semitone from a part under it, and its onsets under one
    out, previous, drawn, redrawn = [], rhythm.START, 0, 0
    for n in sorted(notes, key=lambda x: x[0]):
        a, b, m = n[0], n[1], n[2]
        ref = int(round(m))
        c = rhythm._chord_at(song.chords, a)
        if c is None or c.root is None or c.fit < vocab.FIT:
            out += diatonic([n], interval, scale, voice)
            continue
        tone = vocab.tone_of(ref % 12, c.root, c.shape)
        place = "strong" if abs(a - round(a)) < NEAR else "weak"
        pcs = writer.sounding_pcs(under, a) if under else set()
        over = bool(pcs) and run[place][1] > 0 and run[place][0] / run[place][1] > clash_rates.get(place, 1.0)
        chord_pcs = {(c.root + i) % 12 for i in harmony.SHAPES.get(c.shape, harmony.SHAPES[""])}
        aim = ref + interval                                # the nominal placing: the drawn chord tone sits nearest it
        midi = fallback = landing = None
        for _ in range(writer.VOICE_TRIES):
            pick = t.draw((nominal, tone, role or "?", previous), rng, floored=False, floor_k=PARALLEL_FLOOR, min_songs=PLAN_SONGS)
            if pick.startswith(("+", "-")):                # off the chord: the semitones from the line's note
                try:
                    midi = ref + int(pick)
                except ValueError:
                    midi = None
            else:                                           # a chord tone: that tone of the written chord nearest the nominal placing
                targets = [pc for pc in chord_pcs if vocab.tone_of(pc, c.root, c.shape) == pick] or sorted(chord_pcs)
                midi = min((aim + ((pc - aim) % 12) - 12 * k for pc in targets for k in (0, 1)), key=lambda x: (abs(x - aim), x))
            if midi is None:
                break
            if over and any((midi - q) % 12 in writer.CLASH for q in pcs):   # over the share and a semitone from a part under it: drawn again
                fallback, midi = midi, None
                redrawn += 1
                continue
            landing = pick
            break
        if midi is None:
            if fallback is None:
                out += diatonic([n], interval, scale, voice)
                continue
            midi = fallback
        if pcs:
            run[place][1] += 1
            run[place][0] += int(any((midi - q) % 12 in writer.CLASH for q in pcs))
        previous = landing if landing is not None else (vocab.tone_of(midi % 12, c.root, c.shape) if vocab.tone_of(midi % 12, c.root, c.shape) != "other" else f"{midi - ref:+d}")
        drawn += 1
        out.append((a, b, float(midi), voice))
    if log is not None and drawn:
        log.append(f"voice {voice + 1} parallel at {interval:+d} by the parallel_intervals word (round 97): {drawn} notes at the interval the line's tone under the chord draws"
                   + (("; a semitone from a part under it: " + ", ".join(f"{pl} {x[0]}/{x[1]} ({x[0] / x[1]:.2f}; the song's rate {clash_rates[pl]:.2f})" for pl, x in run.items() if x[1])
                       + (f"; {redrawn} draws given up for a clash" if redrawn else "")) if hold and any(x[1] for x in run.values()) else ""))
    return out


RELATION_PARTS = {"m": R.MELODY, "c": R.COUNTER, "a": R.ACCOMP, "h": R.HARMONY, "r": R.ARP, "b": R.BASS}   # the token's relation letters


def relation_word(plan: "Plan", role: str, v: int) -> str | None:
    """The balance token's relation word for a part's voice v beside the line (round 90), None without one."""
    words = plan.layer_relations.get(role) or []
    return words[v - 1] if 0 < v <= len(words) else None


def relation_stretches(word: str) -> list:
    """A layer voice's relation word (round 90) as stretches: "ox9>dm-12x14>o" -> [("own", None, None, 9), ("double",
    melody, -12, 14), ("own", None, None, None)]: the kind, the part followed, the semitones, the bars (None: to the end).
    A stretch the writer cannot read is its own."""
    out = []
    for part in word.split(">"):
        body, _, n = part.partition("x")
        bars = int(n) if n.isdigit() else None
        kind = {"d": "double", "p": "parallel"}.get(body[:1])
        target = RELATION_PARTS.get(body[1:2])
        try:
            semi = int(body[2:])
        except ValueError:
            semi = None
        out.append((kind, target, semi, bars) if kind and target and semi is not None else ("own", None, None, bars))
    return out


def stretch_spans(stretches: list, bars: int) -> list:
    """The stretches' bars in a song of `bars` bars, as round 85's pan word counts them: [(kind, target, semitones, first
    bar, the bar after the last)], the last stretch to the end, one past the end dropped."""
    out, at = [], 0
    for i, (kind, target, semi, n) in enumerate(stretches):
        end = bars if (n is None or i == len(stretches) - 1) else min(bars, at + n)
        if at < end:
            out.append((kind, target, semi, at, end))
        at = end
        if at >= bars:
            break
    return out


def stretched_notes(v: int, own: list, spans: list, written: dict, scale: set, meter: int, log: list, song=None, role: str | None = None,
                    models: dict | None = None, rng: random.Random | None = None, clash_rates: dict | None = None) -> list:
    """A layer voice's notes stretch by stretch (round 90): in a double stretch the followed part's line again at the
    semitones (diatonic: exact), in a parallel stretch the line again at the intervals the parallel_intervals word draws
    by the chord (`parallel`, round 97; in the scale without the word), over the stretch's bars; in an own stretch the
    voice's own notes (`own`, written as the layer word has them) over those bars. A part not written, or with no line
    in those bars, leaves the stretch to the own notes. `song`, `role`, `models`, `rng`, `clash_rates`: for `parallel`."""
    out = []
    for kind, target, semi, a, b in spans:
        lo, hi = a * meter, b * meter
        if kind != "own" and target in written:
            line = [n for n in written[target].notes if (len(n) < 4 or n[3] == 0) and lo - NEAR <= n[0] < hi - NEAR]
            if line:
                out += parallel(line, semi, scale, v, song, role, models, rng, clash_rates, log) if kind == "parallel" else diatonic(line, semi, scale, v)
                log.append(f"voice {v + 1} {kind} the {target}'s line at {semi:+d} in bars {a + 1}-{b}: {len(line)} notes")
                continue
            log.append(f"voice {v + 1}: no {target} line to {kind} in bars {a + 1}-{b}; its own notes there")
        out += [n for n in own if lo - NEAR <= n[0] < hi - NEAR]
    return out


def line_stretch_list(word: str) -> list:
    """The balance token's eleventh field (round 91) as stretches: "s77ca10e2568@52-64x6>sf89f5aedfd@60-80" ->
    [("s77ca10e2568", (52, 64), 6), ("sf89f5aedfd", (60, 80), None)]: each stretch's sample, the range it is played over
    (None unknown), its bars (None: to the end)."""
    out = []
    for part in word.split(">"):
        body, _, n = part.partition("x")
        sid, _, rng = body.partition("@")
        played = None
        if "-" in rng:
            try:
                lo, hi = (int(x) for x in rng.split("-"))
                played = (lo, hi)
            except ValueError:
                played = None
        out.append((sid, played, int(n) if n.isdigit() else None))
    return out


def stretch_bars(stretches: list, bars: int) -> list:
    """A line's stretches over a song of `bars` bars, as round 85's pan word counts them: [(index, first bar, the bar after
    the last)], the last stretch to the end, one past the end dropped."""
    out, at = [], 0
    for i, (_, _, n) in enumerate(stretches):
        end = bars if (n is None or i == len(stretches) - 1) else min(bars, at + n)
        if at < end:
            out.append((i, at, end))
        at = end
        if at >= bars:
            break
    return out


def stretch_at(plan: "Plan", role: str, bar: int, voice: int = 0) -> int | None:
    """Which of a voice's stretches bar `bar` falls in (round 91, extras[part]["stretch_spans"] for the line as samples_for
    set them; round 92, extras[part]["voice_stretch_spans"][voice] for a voice beside it); None for a voice without
    stretches."""
    x = plan.extras.get(role) or {}
    spans = x.get("stretch_spans") if not voice else (x.get("voice_stretch_spans") or {}).get(voice)
    if not spans:
        return None
    for i, a, b in spans:
        if a <= bar < b:
            return i
    return spans[-1][0]


def fold_line(plan: "Plan", role: str, notes: list, meter: int) -> list:
    """A line's notes folded by octaves into each stretch's bound in its bars (round 91: where the token song played that
    stretch's sample, extras[part]["stretch_bounds"]; writer.in_register's fold), notes as the writers give them, (start,
    end, midi) or (start, end, midi, voice), the line voice's alone folded. A part without stretches is left as written.
    The line is written over the union of its stretches' ranges (plan.bounds, samples_for), so a note sits outside a
    stretch's range only where the game's line changes register with its instrument."""
    bounds = (plan.extras.get(role) or {}).get("stretch_bounds")
    if not bounds:
        return notes
    # each bar of a stretch first as a whole: the octave count that puts most of its notes inside the stretch's bound (a tie
    # keeps the bar before's count, else the smaller move), so the bar's contour survives; then the leftovers one by one,
    # the house fold. A stretch's bound is often narrower than the line's written span (Setzer's tune, written over 56-80,
    # has stretches of 56-64, 68-80 and 60-72), and one count a stretch had left 62 of its notes to single folds
    by_bar = {}
    for k, n in enumerate(notes):
        if len(n) > 3 and n[3] != 0:
            continue
        bar = int(n[0] // meter)
        i = stretch_at(plan, role, bar)
        if i is not None and bounds.get(i) is not None:
            by_bar.setdefault(bar, []).append(k)
    shift, prev = {}, 0
    for bar in sorted(by_bar):
        lo, hi = bounds[stretch_at(plan, role, bar)]
        ks = by_bar[bar]
        best = max(sorted((-24, -12, 0, 12, 24), key=lambda d: (d != prev, abs(d))), key=lambda d: sum(1 for k in ks if lo <= notes[k][2] + d <= hi))
        shift[bar] = prev = best
    out, moved, shifted = [], 0, Counter()
    for k, n in enumerate(notes):
        if len(n) > 3 and n[3] != 0:
            out.append(n)
            continue
        bar = int(n[0] // meter)
        i = stretch_at(plan, role, bar)
        bound = bounds.get(i) if i is not None else None
        if bound is None:
            out.append(n)
            continue
        m = n[2] + shift.get(bar, 0)
        if shift.get(bar):
            shifted[i] += 1
        if not bound[0] <= m <= bound[1]:
            m = float(writer.in_register(int(round(m)), bound))
        if m != n[2]:
            moved += shift.get(bar, 0) == 0 or m != n[2] + shift.get(bar, 0)
            out.append((n[0], n[1], float(m), *n[3:]))
        else:
            out.append(n)
    if moved or shifted:
        plan.log.append(f"{role}: " + ", ".join(f"stretch {i + 1} moved by octaves ({c} notes)" for i, c in sorted(shifted.items()))
                        + ("; " if shifted and moved else "") + (f"{moved} notes folded by octaves into their stretch's register" if moved else "") + " (round 91)")
    return out


def voice_bound_at(plan: "Plan", role: str, v: int):
    """A bar's register for a voice beside a line (round 95), as a function of the bar: the range the token song plays the
    voice's sample over in that bar's stretch (layer_stretches, where the voice changes instrument by stretch), else the
    token's range for the voice's sample over the song (layer_ranges), else the voice's writing span (plan.bounds["part:v"],
    an apart voice's offset span), else the part's; None where nothing is known."""
    sts_all = plan.layer_stretches.get(role) or []
    sts = sts_all[v - 1] if 0 < v <= len(sts_all) else None
    ranges = plan.layer_ranges.get(role) or []
    fallback = tuple(ranges[v - 1]) if 0 < v <= len(ranges) and ranges[v - 1] else None
    if fallback is None:
        fallback = plan.bounds.get(f"{role}:{v}")
    if fallback is None:
        fallback = plan.bounds.get(role) or plan.registers.get(role)

    def at(bar: int):
        if sts:
            i = stretch_at(plan, role, bar, v)
            if i is not None and i < len(sts) and sts[i][1]:
                return tuple(sts[i][1])
        return tuple(fallback) if fallback else None
    return at


def fold_voice(plan: "Plan", role: str, v: int, notes: list, meter: int) -> list:
    """A voice beside a line, written by its relation word, folded by octaves into where the token song plays its sample
    (voice_bound_at), as fold_line folds a line: each bar first as a whole, the octave count that puts most of its notes
    inside (a tie keeps the bar before's count, else the smaller move), then the leftovers one by one. Round 95: a relation
    voice had been written at its word's semitones from the line wherever the written line sat, and Umaro's accompaniment
    voice, two octaves over a tune the game has low in those bars, reached midi 112 where the game plays its sample at 72-88,
    a beep two octaves above the song (45 % of relation-voice notes sat outside their sample's played range over sixty
    seeds). Notes (start, end, midi, voice); only voice v's are touched."""
    at = voice_bound_at(plan, role, v)
    mine = lambda n: len(n) > 3 and n[3] == v   # noqa: E731
    by_bar = {}
    for k, n in enumerate(notes):
        if mine(n) and at(int(n[0] // meter)) is not None:
            by_bar.setdefault(int(n[0] // meter), []).append(k)
    shift, prev = {}, 0
    for bar in sorted(by_bar):
        lo, hi = at(bar)
        ks = by_bar[bar]
        best = max(sorted((-36, -24, -12, 0, 12, 24, 36), key=lambda d: (d != prev, abs(d))), key=lambda d: sum(1 for k in ks if lo <= notes[k][2] + d <= hi))
        shift[bar] = prev = best
    out, moved, shifted = [], 0, 0
    for k, n in enumerate(notes):
        bound = at(int(n[0] // meter)) if mine(n) else None
        if bound is None:
            out.append(n)
            continue
        bar = int(n[0] // meter)
        m = n[2] + shift.get(bar, 0)
        shifted += bool(shift.get(bar))
        if not bound[0] <= m <= bound[1]:
            m = float(writer.in_register(int(round(m)), bound))
            moved += m != n[2] + shift.get(bar, 0)
        out.append((n[0], n[1], float(m), *n[3:]) if m != n[2] else n)
    if shifted or moved:
        plan.log.append(f"{role}'s voice {v + 1}: {shifted} notes moved by octaves" + (f", {moved} folded one by one" if moved else "")
                        + " into where the game plays its sample (round 95)")
    return out


def line_bounds_at(plan: "Plan", role: str):
    """A bar's register for a part's line (round 92): its stretch's bound where the token song's line changes instrument
    (extras[part]["stretch_bounds"], set by samples_for), as a function of the bar for the writers; None without
    stretches, and the writers take the part's one register."""
    bounds = (plan.extras.get(role) or {}).get("stretch_bounds")
    if not bounds:
        return None
    return lambda k: bounds.get(stretch_at(plan, role, k))


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
    loop_bar = plan_loop(models, parts, random.Random(f"whole:{seed}:loop part"), log)   # the form's part the loop returns to (round 98), an own stream
    band, weights, layout, shares, counts, token_levels, token_layers, token_kinds, token_samples, token_habits = [], {}, {}, {}, {}, {}, {}, {}, {}, {}
    token_kit, token_kit_levels, token_kit_pitches, token_kit_rates, token_kit_holds, token_layer_samples, token_layer_shares = {}, {}, {}, {}, {}, {}, {}
    token_kit_degrees, token_kit_tuned, token_key, token_kit_classes = {}, set(), None, {}
    token_kit_seconds = {}                                  # each kit letter's second sample (round 99)
    token_kit_echo, token_echo, token_pans, token_kit_pans = set(), None, {}, {}
    token_sample_ranges, token_layer_ranges = {}, {}       # where the token song plays its own samples (round 86)
    token_layer_relations = {}                              # what each voice beyond a line does beside which part, by stretch (round 90)
    token_stretches = {}                                    # the line's instrument by stretch (round 91)
    token_layer_stretches = {}                              # each voice beyond a line's instrument by stretch (round 92)
    token_gap_shares = {}                                   # a chord part's or the bass's line: the share a note sounds by its gap class (round 95)
    token_kit_channels = []                                # the kit's channels, each one's pieces (round 87)
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
        if role == "key":                                   # the token's song's key (round 79): the kit's degrees and tuned rates read against it
            t, _, m = rest.partition(":")
            token_key = (int(t), m or "major")
            continue
        if role == "echo":                                  # the token's song's echo word (round 82): the written song sits in its room
            token_echo = rest
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
                head, _, by_gap = fields[2].partition("@")   # the line voice's sounded share, and since round 95 its share by gap class
                shares[role] = float(head)
                if by_gap:
                    token_gap_shares[role] = {g: (float(x) if x not in ("", "-") else None) for (_, g), x in zip(rhythm.GAP_CLASSES, by_gap.split("/"))}
            if len(fields) > 3 and fields[3]:
                if role == R.DRUMS:                         # the kit's channels (round 87): the pieces each game channel plays, "KS|h"
                    token_kit_channels = fields[3].split("|")
                else:
                    counts[role] = int(fields[3])
            if len(fields) > 4 and fields[4] and math.isfinite(float(fields[4])):   # a "nan" level (tables counted before the
                token_levels[role] = float(fields[4])                             # readings skipped a kit's unread levels) falls to the levels draw
            if len(fields) > 5 and fields[5]:               # the voices beyond the line, the busiest first, each over the line's level; since
                parts_ = [x.split("@") for x in fields[5].split("/")]   # round 65 with each one's sample and its notes over the line's
                token_layers[role] = [float(x[0]) for x in parts_]
                if any(len(x) > 1 and x[1] for x in parts_):
                    token_layer_samples[role] = [x[1] if len(x) > 1 else "" for x in parts_]
                if any(len(x) > 2 for x in parts_):
                    token_layer_shares[role] = [float(x[2]) if len(x) > 2 and x[2] else 1.0 for x in parts_]
                if any(len(x) > 3 and "-" in x[3] for x in parts_):   # each voice's range on its own sample in the token song (round 86)
                    token_layer_ranges[role] = [tuple(int(y) for y in x[3].split("-")) if len(x) > 3 and "-" in x[3] else None for x in parts_]
                if any(len(x) > 4 and x[4] for x in parts_):   # and what each does beside which part, stretch by stretch (round 90)
                    token_layer_relations[role] = [x[4] if len(x) > 4 and x[4] else None for x in parts_]
                if any(len(x) > 5 and x[5] for x in parts_):   # and each one's instrument by stretch (round 92; "~" between a sample and its range)
                    token_layer_stretches[role] = [line_stretch_list(x[5].replace("~", "@")) if len(x) > 5 and x[5] else None for x in parts_]
            if len(fields) > 6 and fields[6]:               # the counter's kind: on the tune's sample or another (round 39)
                token_kinds[role] = fields[6]
            if len(fields) > 7 and fields[7] and role == R.DRUMS:   # the song's kit (round 63): a piece letter and its sample, by the comma;
                for x in fields[7].split(","):                       # since round 68 each piece's own level after an "@", where its song read one
                    if "=" not in x:
                        continue
                    letter, _, value = x.partition("=")
                    value, _, second_text = value.partition("+")   # the letter's second sample after a "+" (round 99)
                    sid, _, rest = value.partition("@")
                    level, _, rest = rest.partition("@")    # since round 75 the note the piece is struck at follows the level's slot,
                    pitch, _, rest = rest.partition("@")    # since round 77 a tonal piece's hold in beats follows the note's,
                    hold, _, rest = rest.partition("@")     # since round 81 the slot's strike class the hold's (a/s/m/d),
                    cls, _, rest = rest.partition("@")      # since round 82 an e where the game sends the piece to echo,
                    mark, _, pan = rest.partition("@")      # since round 84 the piece's pan after the mark (the right side's share)
                    token_kit[letter] = sid
                    if cls and cls[0] in rhythm.SLOT_NAMES:
                        token_kit_classes[letter] = cls[0]
                    if mark.startswith("e"):
                        token_kit_echo.add(letter)
                    if pan and math.isfinite(float(pan)):
                        token_kit_pans[letter] = float(pan)
                    if level and math.isfinite(float(level)):
                        token_kit_levels[letter] = float(level)
                    if pitch.startswith("r"):               # the chip's rate as a note (round 78), for a piece the namer called a drum;
                        if pitch.endswith("t"):              # "t": the game tunes this sample to the key (round 79)
                            token_kit_tuned.add(letter)
                        token_kit_rates[letter] = int(round(float(pitch[1:].rstrip("t"))))
                    elif pitch.startswith(("d", "c")):      # a degree of the token song's key (round 79): scale steps, or semitones off it
                        token_kit_degrees[letter] = (pitch[0], int(pitch[1:]))
                    elif pitch:                             # the absolute note (round 75's form, read still)
                        token_kit_pitches[letter] = int(round(float(pitch)))
                    if hold and float(hold) > 0:
                        token_kit_holds[letter] = float(hold)
                    if second_text:                         # the second sample's id, level, note or rate, hold and share (round 99)
                        s2, l2, n2, h2, sh2 = (second_text.split("@") + [""] * 5)[:5]
                        try:
                            share2 = float(sh2)
                        except ValueError:
                            share2 = None
                        if s2 and share2 is not None:
                            second = {"sample": s2, "share": share2, "level": float(l2) if l2 and math.isfinite(float(l2)) else None,
                                      "hold": float(h2) if h2 and float(h2) > 0 else None, "rate": None, "degree": None, "pitch": None, "tuned": False}
                            if n2.startswith("r"):
                                second["rate"] = int(round(float(n2[1:].rstrip("t"))))
                                second["tuned"] = n2.endswith("t")
                            elif n2.startswith(("d", "c")):
                                second["degree"] = (n2[0], int(n2[1:]))
                            elif n2:
                                second["pitch"] = int(round(float(n2)))
                            token_kit_seconds[letter] = second
            elif len(fields) > 7 and fields[7]:             # the part's own sample (round 60): the song's instruments with its levels,
                sid, _, played = fields[7].partition("@")   # and since round 86 the range the song plays it over ("s1d296a2572@32-52")
                token_samples[role] = sid
                if "-" in played:
                    token_sample_ranges[role] = tuple(int(x) for x in played.split("-"))
            if len(fields) > 8 and fields[8]:               # the part's habit (round 62): the song's density tiers together
                token_habits[role] = fields[8].replace("+", " ")
            if len(fields) > 9 and fields[9]:               # the part's voices' pans (round 84): the line's first, then the voices beyond it;
                token_pans[role] = [float(x) if re.fullmatch(r"[0-9.]+", x) else x for x in fields[9].split("/")]   # a voice's two
                                                            # places kept as written, "0.60x5|0.45x13" or "0.35x4>0.65" (round 85, render.pan_of)
            if len(fields) > 10 and fields[10]:             # the line's instrument by stretch (round 91): each stretch's sample, range and bars
                token_stretches[role] = line_stretch_list(fields[10])
    log.append("band " + " ".join(f"{r}={weights[r]}" + (f" {layout[r][0]}-{layout[r][1]}" if r in layout else "") + (f" x{counts[r]}" if r in counts else "")
                                  if r in weights else r for r in band))
    if token_class and rhythm.band(bpm) != token_class:     # the band's own pace (round 54): the tempo drawn again under the token's class, on
        was = bpm                                           # an own stream so no other draw moves
        bpm = float(_draw(models, "tempos", ("song", token_class), random.Random(f"whole:{seed}:tempo"), log, floor_k=2))   # terminal at the
        # class (round 75): without the floor the draw gave the class's own votes their Witten-Bell share and backed off to every
        # class's tempos for the rest, and 8 of 46 written songs sat in another class than their token's, their kits drawn there
        if rhythm.band(bpm) != token_class:                 # the word's rounding to five put the tempo on the next class's first value
            bpm = rhythm.within_band(bpm, token_class)      # (85 under slow, 130 under medium): the class's edge, inside
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
                     if "top_levels" in render_mod.models_or_empty(models) else TOP_LEVEL)
    registers, sounds, habits, extras = {}, {}, {}, {}
    if token_echo is not None:                              # the token song's echo word (round 82): render.echo_word takes it in place of a draw
        extras["echo"] = {"word": token_echo}
        log.append(f"echo from the balance's song: {token_echo}")
    for role in band:
        if role == R.DRUMS:
            habits[role] = drum_habit
            groups_rng = random.Random(f"whole:{seed}:drum-groups")   # own stream (round 81): the classes change what a draw visits
            extras[role] = {"".join(g): _draw_values(models, "drum_group_habits", {"part": "drums-" + "".join(g), "classes": rhythm.habit_class(token_kit_classes, g),
                                                                                    "habit": habits[role]}, groups_rng, log, floor_k=GROUP_HABIT_FLOOR)
                            for g in rhythm.DRUM_GROUPS}    # terminal at the class (round 81): a dense hat never takes a sparse habit from the root
            if token_kit:                                   # the token song's own kit (round 63): its pieces are these, its samples theirs
                extras[role]["pieces"] = "".join(x for x in rhythm.LETTERS.values() if x in token_kit)
                extras[role]["kit"] = token_kit
                if token_kit_levels:                        # each piece at its own level of the loudest part's (round 68); a piece without
                    extras[role]["kit_levels"] = token_kit_levels   # one plays at the part's level (the fifth field)
                if token_kit_pitches:                       # the note each piece is struck at (round 75): a piece on a tonal sample plays there
                    extras[role]["kit_pitches"] = token_kit_pitches
                if token_kit_rates:                         # the rate a drum piece is struck at (round 78), as a note: 60 as recorded
                    extras[role]["kit_rates"] = token_kit_rates
                if token_kit_degrees:                       # a tonal piece's note as a degree of the token song's key (round 79)
                    extras[role]["kit_degrees"] = token_kit_degrees
                if token_kit_tuned:                         # the percussion pieces the game tunes to the key (round 79)
                    extras[role]["kit_tuned"] = token_kit_tuned
                if token_key is not None:
                    extras[role]["token_key"] = token_key
                if token_kit_holds:                         # how long a tonal piece is keyed for (round 77): its hit lasts that, not the kit's beat
                    extras[role]["kit_holds"] = token_kit_holds
                if token_kit_classes:                       # each slot's strike class (round 81): the letter's figure follows its sample's use
                    extras[role]["kit_classes"] = token_kit_classes
                if token_echo is not None:                  # the slots the game sends to echo (round 82): per piece, as the chip's channels
                    extras[role]["kit_echo"] = sorted(token_kit_echo)
                if token_kit_pans:                          # where each piece sits in the stereo field (round 84)
                    extras[role]["kit_pans"] = token_kit_pans
                if token_kit_seconds:                       # each letter's second sample and its share of the letter's hits (round 99)
                    extras[role]["kit_seconds"] = token_kit_seconds
                    log.append("kit seconds from the balance: " + ", ".join(f"{k} {v['sample']} at {v['share']:.2f} of the hits" for k, v in token_kit_seconds.items()))
                if token_kit_channels:                      # the channels the game gave the kit, each one's pieces (round 87)
                    extras[role]["channels"] = token_kit_channels
                    log.append(f"kit channels from the balance: {len(token_kit_channels)} ({'|'.join(token_kit_channels)})")
                log.append(f"kit from the balance: {extras[role]['pieces']} (" + ", ".join(f"{k} {v}" + (f" at {token_kit_levels[k]:.2f}" if k in token_kit_levels else "")
                                                                                            + (f" struck at {token_kit_pitches[k]}" if k in token_kit_pitches else "")
                                                                                            + (f" struck {token_kit_rates[k] - 60:+d} semitones from the recording" if k in token_kit_rates else "")
                                                                                            + (", tuned to the key" if k in token_kit_tuned else "")
                                                                                            + (f" struck at {token_kit_degrees[k][0]}{token_kit_degrees[k][1]:+d} of the key" if k in token_kit_degrees else "")
                                                                                            + (f" held {token_kit_holds[k]:.2f} beats" if k in token_kit_holds else "")
                                                                                            + (f", {rhythm.SLOT_NAMES[token_kit_classes[k]]}" if k in token_kit_classes else "")
                                                                                            + (", to echo" if k in token_kit_echo else "")
                                                                                            for k, v in token_kit.items()) + ")")
            elif "kit_pieces" in render_mod.models_or_empty(models):    # the pieces the song's kit strikes (round 58), on an own stream
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
            extras[role] = {"richness": _draw(models, "voicing_habits", (role,), rng, log), "motion": _draw(models, "motions", (role,), rng, log),
                            "clashes": ({pl: float(_draw(models, "clashes", (role, pl), random.Random(f"whole:{seed}:clashes:{role}:{pl}"), log)) for pl in ("strong", "weak")}
                                        if "clashes" in render_mod.models_or_empty(models) else None),   # its share of onsets a semitone from the bass and the chord parts under it (round 94), own streams
                            "tone_tier": (_draw(models, "tone_tiers", (role,), random.Random(f"whole:{seed}:tone_tier:{role}"), log)
                                          if "tone_tiers" in render_mod.models_or_empty(models) else None)}   # how much of its line leaves the chord (round 96), an own stream
        elif role in (R.MELODY, R.COUNTER):                  # the phrase tables count both lines as the tune's: drawn under the melody's part
            extras[role] = {"articulation": _draw(models, "articulation", (role,), rng, log),
                            "echo": _draw(models, "echo_habits", (R.MELODY, tempo, weight), rng, log),
                            "steps": _draw(models, "step_habits", (R.MELODY,), rng, log),
                            "repeats": _draw(models, "repeat_habits", (R.MELODY,), rng, log),
                            "chord_tones": float(_draw(models, "chord_tones", (R.MELODY,), rng, log)),
                            "off_scale": ({pl: float(_draw(models, "off_scale", (role, mode, pl), random.Random(f"whole:{seed}:off_scale:{role}:{pl}"), log)) for pl in ("strong", "weak")}
                                          if "off_scale" in render_mod.models_or_empty(models) else None),   # the line's share off the scale by the beat (round 93), own streams,
                            "clashes": ({pl: float(_draw(models, "clashes", (role, pl), random.Random(f"whole:{seed}:clashes:{role}:{pl}"), log)) for pl in ("strong", "weak")}
                                        if "clashes" in render_mod.models_or_empty(models) else None),   # the melody's and the counter's each its own; its onsets a semitone from a sounding part
                            "repeat_rate": _maybe(models, "repeat_rates", (R.MELODY,), rng),
                            "grain": (_draw(models, "tune_grain", (role, str(habits[role]).split()[0]), random.Random(f"whole:{seed}:grain:{role}"), log, floor_k=GRAIN_FLOOR)
                                      if "tune_grain" in render_mod.models_or_empty(models) else None)}   # an own stream, floored at the tier (round 66)
            if role == R.COUNTER and "chord_tones" in render_mod.models_or_empty(models):   # the counter-line's own chord-tone share (round 96), on an
                extras[role]["chord_tones"] = float(_draw(models, "chord_tones", (R.COUNTER,), random.Random(f"whole:{seed}:chord_tones:{role}"), log))   # own stream
            if "tune_sounds" in render_mod.models_or_empty(models):   # the share of its gap a held and a detached note sounds (round 98), own streams
                extras[role]["tune_sounds"] = {kind: float(_draw(models, "tune_sounds", (role, kind), random.Random(f"whole:{seed}:tune_sounds:{role}:{kind}"), log))
                                               for kind in rhythm.TUNE_KINDS}
    if R.DRUMS in band and "part_entries" in render_mod.models_or_empty(models):   # the drums' entrances under the kit's tier (round 59), on an own stream
        textures, plays = drum_entrances(models, parts, textures, band, str(habits[R.DRUMS]).split()[0], random.Random(f"whole:{seed}:entries"), log)
    section_levels = (plan_section_levels(models, parts, band, plays, random.Random(f"whole:{seed}:levels"), log)   # an own stream: drawn on the
                      if "section_levels" in render_mod.models_or_empty(models) else {})                                  # plan's, every later draw had shifted
    section_densities = (plan_section_densities(models, parts, band, plays, section_levels, random.Random(f"whole:{seed}:section densities"), log)
                         if "section_densities" in render_mod.models_or_empty(models) else {})   # a section's density tier by the step its level makes (round 101)
    voices = allot(band, counts, len(token_kit_channels) or 2)   # the kit on its song's channels (round 87), two without the field
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
                  for role in band if role in rhythm.UPPER + (R.BASS,)} if "gap_sounds" in render_mod.models_or_empty(models) else {}
    _own_gap_sounds(gap_sounds, token_gap_shares, log)      # the balance's song's own note lengths for the line (round 95), the draw where it lacks a class
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
    if token_pans or token_kit_pans:                        # the song's stereo picture (round 84): the token song's pans, voice by voice
        log.append("pans from the balance: " + " ".join(f"{r}={'/'.join(f'{x:.2f}' if isinstance(x, float) else x for x in token_pans[r])}" for r in band if r in token_pans)
                   + (" kit " + " ".join(f"{k}={v:.2f}" for k, v in token_kit_pans.items()) if token_kit_pans and R.DRUMS in band else ""))
    return Plan(seed, game, title or f"Whole {seed}", tonic, mode, bpm, parts, loop_bar, names, chords, band, weights, textures, plays,
                registers, sounds, habits, extras, voices, log, feel=feel, levels=levels, layer_levels=layer_levels, gap_sounds=gap_sounds, token_gap_shares=token_gap_shares, locks=locks,
                level_from=level_from, voice_levels=voice_levels, layer_from=layer_from, kinds=token_kinds, token_samples=token_samples, token_habits=token_habits, layer_samples=token_layer_samples, layer_shares=token_layer_shares, section_levels=section_levels, section_densities=section_densities,
                top_level=top_level, loudness=token_loud, pans=token_pans, sample_ranges=token_sample_ranges, layer_ranges=token_layer_ranges, layer_relations=token_layer_relations, stretches=token_stretches, layer_stretches=token_layer_stretches)


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
        drawn = _draw(models, "part_speeds", (role, tier), rng, p.log, floor_k=2) if "part_speeds" in render_mod.models_or_empty(models) else DEFAULTS["part_speeds"]
        p.speeds[role] = SPEED_FASTER if drawn == "faster" else float(drawn)   # floored at the part and tier: a dense accompaniment had drawn 2 a second
                                                                           # from the coarser level's mass, a value FFVI's dense accompaniments never have


def _own_gap_sounds(gap_sounds: dict, token_gap_shares: dict, log: list | None) -> None:
    """The token song's own sounded shares by gap class for a chord part's or the bass's only and line voices (round 95), over
    the gap_sounds draws (made all the same, so the stream is as it was); a class the token lacks keeps the draw. The second
    voices keep the pooled word. Umaro's accompaniment line pecks 0.4 of its gap under a beat where the pooled word for a
    layered line said 1.0, and the written line had held every note to the next."""
    for role, own in token_gap_shares.items():
        if role not in gap_sounds:
            continue
        for voice in ("only", "line"):
            gap_sounds[role][voice] = {g: (own[g] if own.get(g) is not None else gap_sounds[role][voice][g]) for _, g in rhythm.GAP_CLASSES}
        if log is not None and not any(l.startswith(f"{role}'s note lengths from the balance's song") for l in log):
            log.append(f"{role}'s note lengths from the balance's song (its line's share by gap): " + " ".join(f"{g} {own[g]:.1f}" if own.get(g) is not None else f"{g} drawn" for _, g in rhythm.GAP_CLASSES))


def _plan_sounds(models: dict, p: Plan, rng: random.Random) -> None:
    """The share of its gap a note sounds, drawn again under the part's speed class (gap_sounds: part, voice, speed, gap; round
    35) once the part's speed is drawn, after every other plan draw. FFVI's string pad played fast sounds a fifth to a third
    of its gap (the battle tremolo), played slow nearly all of it; one share by the gap alone had put Whole 02's fast
    arpeggio between the two, a staccato pad neither held nor tremolo. The draw in _plan_once stays in the stream."""
    if "gap_sounds" not in render_mod.models_or_empty(models) or not p.speeds:
        return
    for role in list(p.gap_sounds):
        if role not in p.speeds:
            continue
        tier = rhythm.speed_tier(p.speeds[role])
        p.gap_sounds[role] = {voice: {g: float(_draw(models, "gap_sounds", (role, voice, tier, g), rng, p.log)) for _, g in rhythm.GAP_CLASSES}
                              for voice in ("only", "line", "second")}
    _own_gap_sounds(p.gap_sounds, p.token_gap_shares, None)   # the token song's own shares stand over the speed's redraw too (round 95)


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
    have = render_mod.models_or_empty(models)
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


def _voices_of(song: rhythm.Song, exclude: set, channels: list | None = None) -> list:
    """The onsets of every voice written so far but the part's: a pitched part one voice, the drums their channels (the
    token's since round 87, the fixed two without)."""
    out = []
    for role, ns in song.notes.items():
        if role in exclude:
            continue
        if role == R.DRUMS:
            for group in (channels or DRUM_VOICES):
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
    voices = _voices_of(song, exclude, plan.extras.get(R.DRUMS, {}).get("channels") if plan is not None else None)
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
    if R.MELODY not in written or "cell_handoffs" not in render_mod.models_or_empty(models):
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
        kit_value = "".join(x for x in rhythm.LETTERS.values() if x in kit_letters)   # the kit's pieces: the kit figure is drawn from songs with this kit
        kit_classes = plan.extras.get(R.DRUMS, {}).get("kit_classes") or {}     # the slots' strike classes (round 81): a letter's bars from songs that strike
        limbs = {g: models[name] for g in rhythm.DRUM_GROUPS if (name := "drums-" + "".join(g)) in models and set(g) & kit_letters}   # its sample as this one does
        whole_kit = "drums" in models and (not limbs or (not kit_classes and writer.kit_table_reaches(models["drums"], song, kit_letters, kit_value, plan.habits[R.DRUMS])))
        # with classes the kit is written from its limbs (round 81): the kit table's bar is one song's, hat and all, and under a rare kit the
        # draw smooths that song's bars with every kit's; a limb's table under the slot's class pools the songs that strike the sample as this one does
        if whole_kit:                                       # the kit as one figure: its bars repeat and vary together, as a kit's do
            groups = {tuple(rhythm.LETTERS.values()): models["drums"]}
        else:                                               # the kit's limbs, each from its own table at its own counted habit (round 75): where the
            groups = limbs                                  # kit table holds no bar this kit can play within its habit's density tier (The Phantom
                                                            # Forest's one-piece kit in 3/4 had backed off to Johnny C. Bad's dense snare bars in
                                                            # 4/4: 13 hits a bar under "sparse repeating"), or a pack with the groups alone
        if groups:
            group_habits = {g: (plan.habits[R.DRUMS] if len(g) > 3 else plan.extras.get(R.DRUMS, {}).get("".join(g)) or plan.habits[R.DRUMS]) for g in groups}
            # until round 58 the one-letter groups' own habits capped their hits in the kit's draw (writer.group_caps): a kit drawn as one
            # figure is one song's bar, hat and all, and another song's "sparse hat" cutting it had left a dense kit at 8 hits a bar
            # against the game's 12.8; the song's pieces (kit_pieces) now say which sounds the kit has at all
            group_classes = {g: rhythm.class_values(kit_classes, set(g) & kit_letters) for g in groups} if kit_classes else {}
            hits, figures = writer.drums(song, groups, random.Random(f"{seed}:drums"), habit=group_habits, free=True, plays=plan.plays[R.DRUMS], kit_value=kit_value,
                                         class_values=group_classes)
            by_voice, notes, dropped = {}, [], Counter()
            seconds_of = plan.extras.get(R.DRUMS, {}).get("kit_seconds") or {}   # the letters with a second sample (round 99), its hits drawn
            runs, rng_seconds = {}, random.Random(f"{seed}:drums:seconds")      # by the kit_seconds word on an own stream, held to the token's share
            for t, letter in hits:
                if letter not in kit_letters:               # a piece the song's kit does not strike (kit_pieces)
                    dropped[letter] += 1
                    continue
                sample = next((name for name in KIT_FOR.get(letter, ()) if name in song.pieces), None)
                if sample is None:
                    dropped[letter] += 1
                    continue
                if letter in seconds_of and sample + SECOND_SLOT in song.pieces:   # the letter's second sample takes this hit or not (round 99)
                    place = rhythm.place(rhythm.position(t - METER * math.floor(t / METER), DIVISION))
                    if kit_second_pick(models, letter, place, runs.setdefault(letter, [0, 0]), seconds_of[letter]["share"], rng_seconds):
                        sample += SECOND_SLOT
                v = drum_voice_of(plan.extras.get(R.DRUMS, {}).get("channels"), letter, plan.voices.get(R.DRUMS, 2))   # the game's channel (round 87)
                by_voice.setdefault(v, []).append((t, letter, sample))
            rank = {name: i for i, (_, name) in enumerate(rhythm.SLOT_CLASSES)}
            sparser = lambda letter: (rank.get(kit_classes.get(letter, ""), len(rank)), letter)   # noqa: E731  the rarer slot first, then by letter
            for v, mine in by_voice.items():
                mine.sort(key=lambda x: (x[0], sparser(x[1]), x[2]))
                seen = set()
                for i, (t, letter, sample) in enumerate(mine):
                    if round(t, 3) in seen:                 # two pieces on one voice at once: the sparser slot's hit stands (round 81: the hat had
                        continue                            # taken every beat it shared with Wild West's blip; on the game's channel the blip's hit replaces the hat's)
                    seen.add(round(t, 3))
                    after = next((u for u, *_ in mine[i + 1:] if u > t + NEAR), None)
                    held = kit_piece_hold(plan, sample) if sample in (plan.extras.get(R.DRUMS, {}).get("tonal_slots") or ()) else None
                    length = held or DRUM_LENGTH            # a piece on a sustaining sample for as long as the game keys it (round 77), cut by the next hit
                    notes.append((t, min(after if after is not None else t + length, t + length), letter, v, sample))
            song.notes[R.DRUMS] = [(t, end - t, float("nan"), sample) for t, end, _, _, sample in notes]
            written[R.DRUMS] = Part(R.DRUMS, notes, figures, [f"kit habit {plan.habits[R.DRUMS]}; groups " + ", ".join(f"{'+'.join(g)} {h}" + (" under " + " ".join(v for v in group_classes[g].values() if v != "-") if group_classes.get(g) else "") for g, h in group_habits.items())
                                                              + f"; {sum(1 for f in figures if f != writer.REST)} bars written, {len(notes)} hits"
                                                              + (f"; pieces {''.join(sorted(kit_letters, key=list(rhythm.LETTERS.values()).index))}")
                                                              + (f"; dropped (not in the kit) {dict(dropped)}" if dropped else "")
                                                              + ("; the slots' strike classes: the kit from its limbs' tables under them (round 81)" if kit_classes and limbs else
                                                                 "; the kit table holds no bar this kit plays within its habit's density: the limbs' tables at their own habits (round 75)" if "drums" in models and not whole_kit else "")])
            if runs:                                        # the second samples' hits (round 99)
                written[R.DRUMS].log.append("kit seconds (kit_seconds): " + ", ".join(f"{k} {r[0]} of {r[1]} hits on the second sample (the token's share {seconds_of[k]['share']:.2f})" for k, r in runs.items())
                                            + ("" if "kit_seconds" in models else "; no kit_seconds word: the slot's sample throughout"))
    if R.BASS in plan.band and "bass" in models:
        # the bass sits on the kit's accents (two pieces together) at the game's share (bass_locks): FFVI's on 0.94 of them;
        # locked to the whole planned band it had met the threshold in no bar, written second with two drum voices to hand
        lock = {k: (ps, set()) for k, ps in rhythm.kit_accents(song.notes.get(R.DRUMS, []), song.bars, song.division).items()} if R.BASS in plan.locks else locks_of(song, {R.BASS}, plan)
        lock_share = plan.locks.get(R.BASS, 1.0)
        layered = plan.voices.get(R.BASS, 1) >= 2 and layer_of(plan.extras.get(R.BASS))[0] == "apart"
        sounds_line = float(_draw(models, "layer_sounds", (R.BASS, "line"), random.Random(f"{seed}:bass:line sounds"))) if layered and "layer_sounds" in models else plan.sounds[R.BASS]
        gs = plan.gap_sounds.get(R.BASS)                    # the share a note sounds by its gap (gap_sounds), the one share without it
        shared_bass = {}                                    # the line's notes, for a second voice following it
        notes, figures = writer.bass(song, models["bass"], random.Random(f"{seed}:bass"), habit=plan.habits[R.BASS], habit_at=habit_at_for(plan, R.BASS), envelope_at=envelope_at_for(plan, R.BASS), key=key, lock=lock,
                                     free=True, plays=plan.plays[R.BASS], register=plan.bounds.get(R.BASS, plan.registers[R.BASS])[0],
                                     sounds=gs["line" if layered else "only"] if gs else sounds_line, shared=shared_bass, lock_share=lock_share,
                                     ceiling=plan.bounds.get(R.BASS, plan.registers[R.BASS])[1], bounds_at=line_bounds_at(plan, R.BASS))
        notes = fold_line(plan, R.BASS, notes, song.meter)  # the line in each stretch's register (round 91)
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
                masks = [p if p == writer.REST else _draw(models, "second_figures", (R.BASS, render_mod.layer_class(plan, R.BASS), plan.feel, rhythm.band(plan.bpm), str(len(p.split())), p), rng2, floor_k=MASK_FLOOR, floor_songs=PLAN_SONGS)
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
    pending = []                                            # the voices beside a line the token says what they do by stretch (round 90): written last
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
        tlog = []                                           # what the tone figure word did to the line (round 96)
        notes, figures, voicings = writer.upper(song, role, [0], {0: (low, high)}, models, random.Random(f"{seed}:{role}"), plan.habits[role],
                                                plan.extras[role]["richness"], sounds, key=key, lock=lock, motion=plan.extras[role]["motion"], habit_at=habit_at_for(plan, role), envelope_at=envelope_at_for(plan, role),
                                                pedals={0: (low + high) // 2}, plays=plan.plays[role], shared=shared, tone_index=0, bounds_at=line_bounds_at(plan, role), clash_rates=plan.extras[role].get("clashes"),
                                                tone_rng=random.Random(f"{seed}:{role}:tones"), log=tlog, tone_tier=plan.extras[role].get("tone_tier"))   # the tone figures on their own stream (round 96)
        notes = fold_line(plan, role, notes, song.meter)   # the line in each stretch's register (round 91)
        song.notes[role] = [(a, b - a, m, role) for a, b, m, _ in notes]
        log = [f"voices {n}, register {(low, high)}, habit {plan.habits[role]}, voicing {plan.extras[role]['richness']}, "
               f"motion {plan.extras[role]['motion']}, sounded {render_mod._sounds_text(sounds)}; {sum(1 for f in figures if f != writer.REST)} bars written, "
               f"{len(notes)} notes; locked to the band in {len(lock)} bars"] + tlog
        all_figures = [f"{f} / {vc}" for f, vc in zip(figures, voicings)]
        line_notes = list(notes)
        scale = {(plan.tonic + i) % 12 for i in harmony.MODES["major" if plan.mode == "major" else "natural_minor"]}
        beside_v = set()                                    # the voices whose pitch is drawn beside the line under the span rule
        for v, word in enumerate(layers, start=1):
            rel = layer_of({"layer": word})
            if rel[0] == "doubling":
                notes_v = parallel(line_notes, rel[1], scale, v, song, role, models, random.Random(f"{seed}:{role}:voice {v}:layer parallel"),
                                   plan.extras[role].get("clashes"), log)   # the line again at the interval, by the chord where the word reaches (round 97)
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
                        drawn = _draw(models, "second_figures", (role, render_mod.layer_class(plan, role), plan.feel, rhythm.band(plan.bpm), str(len(f.split())), f), rng_v, floor_k=MASK_FLOOR)
                        return rhythm.apply_mask(f, drawn)
                    given = [f if f == writer.REST else (memo.setdefault(f, masked(f)) if SECOND_MEMO else masked(f)) for f in figures]
                drawn_pitch = "voice_intervals" in models and "voice_moves" in models
                if drawn_pitch:
                    beside_v.add(v)
                # the voice's pitch is its drawn interval from the line, folded into its own span: the line's span at the layer word's
                # offset, within the range the game plays its sample over (round 70, plan.bounds["role:v"], render.voice_bounds). The
                # one `:second` bound had been the first extra voice's sample's home band, so Whole 166's "apart +8" voices were
                # folded into the line's own band and sat at a median 0 semitones from it (round 69)
                span_v = plan.bounds.get(f"{role}:{v}") or (plan.bounds.get(f"{role}:second", reg_v) if drawn_pitch else reg_v)
                notes_v, figures_v, voicings_v = writer.upper(song, role, [v], {v: span_v}, models, rng_v, plan.habits[role], plan.extras[role]["richness"], gs["second"] if gs else sounds,   # interval from the
                                                              key=key, lock=locks_of(song, {role}, plan), motion=plan.extras[role]["motion"],   # line, kept within the span FFVI's
                                                              pedals={v: (reg_v[0] + reg_v[1]) // 2}, plays=plan.plays[role], figures=given, shared=shared,   # voices beside a line sit in
                                                              tone_index=(writer.ANY_TONE if SECOND_ANY_TONE else v), kind=rel[0], clash_rates=plan.extras[role].get("clashes"))   # (the layer offset's cap), not folded into its offset register
                log.append(f"voice {v + 1} {rel[0]}: register {reg_v} ({offset:+d}, {density}), "
                           + ("its interval to the line and its own moves drawn, " if drawn_pitch else f"the line's voicing {v} tone{'s' if v > 1 else ''} up, ")
                           + f"{sum(1 for f in figures_v if f != writer.REST)} bars, {len(notes_v)} notes" + ("; its bars beside the line's" if given else ""))
            word_v = relation_word(plan, role, v)
            if word_v:                                      # what the voice does beside which part, by stretch (round 90): after every line is written
                pending.append((role, v, notes_v, word_v))
                log.append(f"voice {v + 1} by the token's stretches ({word_v}): written after the lines")
            else:
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
                                                  key=key, articulation=x["articulation"], register=span, spans_at=line_bounds_at(plan, R.COUNTER), clash_rates=x.get("clashes"),
                                                  chord_rate=x.get("chord_tones"), tune_sounds=x.get("tune_sounds"))   # its own chord-tone share held (round 96), its note lengths (round 98)
        else:
            notes, figures, plog = writer.melody(song, [], plan.bounds.get(role, plan.registers[role]), models, random.Random(f"{seed}:{role}"), plan.habits[role],
                                                 key=key, hold=(), reference=reference, articulation=x["articulation"], echo_habit=x["echo"],
                                                 recall=models.get("melody_recall"), step_habit=x["steps"], repeat_habit=x["repeats"], plays=plan.plays[role],
                                                 role=role, chord_rate=x.get("chord_tones"), repeat_rate=x.get("repeat_rate"), grain=x.get("grain"), off_scale=x.get("off_scale"), clash_rates=x.get("clashes"),
                                                 tune_sounds=x.get("tune_sounds"), letters=x.get("letters") if role == R.MELODY else None, theme_body=models.get("theme_body"),
                                                 bounds_at=line_bounds_at(plan, role), recall_moves=models.get("recall_moves"),
                                                 moves_rng=random.Random(f"{seed}:{role}:recall moves"),   # the recalls' places on an own stream (round 100)
                                                 habit_at=habit_at_for(plan, role), envelope_at=envelope_at_for(plan, role))   # the habit and envelope a bar: the tier by the section (round 101)
        notes = fold_line(plan, role, notes, song.meter)   # the line in each stretch's register (round 91)
        song.notes[role] = [(a, b - a, m, role) for a, b, m in notes]
        line = [(a, b, m, 0) for a, b, m in notes]
        log = [f"register {plan.bounds.get(role, plan.registers[role])}, habit {plan.habits[role]}, " + ", ".join(f"{k} {v}" for k, v in x.items() if k not in ("layer", "letters"))
               + f"; {sum(1 for f in figures if f != writer.REST)} bars written, {len(notes)} notes; the reference set "
               + ("checked" if reference is not None and not beside else "not on this machine" if reference is None else "not asked: the line follows the tune")] + plog
        n = plan.voices[role]
        words = layers_of(plan, role) if n >= 2 else []
        scale = {(plan.tonic + i) % 12 for i in harmony.MODES["major" if plan.mode == "major" else "natural_minor"]}
        beside_v = {0} if beside else set()
        line_only, line_figures = list(line), list(figures)   # the line voice alone and its bars: what the voices beside it are written against
        for v, word in enumerate(words, start=1):
            layer = layer_of({"layer": word})
            word_v = relation_word(plan, role, v)           # what the voice does beside which part, by stretch (round 90)
            if layer[0] == "doubling" and notes:            # the line again at the interval, by the chord where the word reaches (round 97)
                second = parallel(line_only, layer[1], scale, v, song, role, models, random.Random(f"{seed}:{role}:voice {v}:layer parallel"), None, log)
                if word_v:
                    pending.append((role, v, second, word_v))
                    log.append(f"voice {v + 1} by the token's stretches ({word_v}): written after the lines")
                else:
                    song.notes[role] += [(a, b - a, m, role) for a, b, m, _ in second]
                    line = line + second
                    log.append(f"voice {v + 1} doubles the line at {layer[1]:+d} semitones, in the scale")
            elif beside and all(k in models for k in ("voice_intervals", "voice_moves", "second_figures")):
                # a voice beside a counter that follows the tune (round 76): written as the counter is beside the tune (writer.counter
                # with the counter's line as its tune), its bar a second_figures mask over the line's bar and its pitch the voice words'
                # under the layer relation (apart, alternating), both counted for the counter's voices beside its line as for an upper
                # part's. Rounds 29 to 75 had left these voices silent ("no word yet"): FFVI's layered counters beside a tune hold two
                # to four voices in 11 of 46 kit tokens' songs, block chords and parallel lines, and the written band there sat 6 to
                # 12 dB thinner than the game's, which put a kit at the game's own volume out in front (Song Check 63's verdict).
                offset, density = (layer[1], layer[2]) if layer[0] == "apart" else (0, "like")
                low, high = plan.bounds.get(role, plan.registers[role])
                reg_v = (max(24, low + offset), min(100, high + offset))
                span_v = plan.bounds.get(f"{role}:{v}") or plan.bounds.get(f"{role}:second", reg_v)
                rng_v = random.Random(f"{seed}:{role}:voice {v}")
                memo = {}

                def masked(f):
                    drawn = _draw(models, "second_figures", (role, render_mod.layer_class(plan, role), plan.feel, tempo, str(len(f.split())), f), rng_v, floor_k=MASK_FLOOR)
                    return drawn
                masks_v = [f if f == writer.REST else (memo.setdefault(f, masked(f)) if SECOND_MEMO else masked(f)) for f in line_figures]
                notes_v, figures_v, plog_v = writer.counter(song, line_only, line_figures, masks_v, span_v, models, rng_v, layer[0], key=key,
                                                            articulation=x["articulation"], register=span_v, clash_rates=x.get("clashes"), tune_sounds=x.get("tune_sounds"))
                if word_v:
                    pending.append((role, v, [(a, b, m, v) for a, b, m in notes_v], word_v))
                    log.append(f"voice {v + 1} by the token's stretches ({word_v}): written after the lines")
                else:
                    song.notes[role] += [(a, b - a, m, role) for a, b, m in notes_v]
                    line = line + [(a, b, m, v) for a, b, m in notes_v]
                figures = [f"{f} || {g}" for f, g in zip(figures, figures_v)]
                beside_v.add(v)
                log.append(f"voice {v + 1} {layer[0]} ({offset:+d}, {density}) beside the line, register {span_v}: " + plog_v[0])
            elif layer[0] == "apart" and beside:            # the vocabulary lacks a word for a voice beside the line: the voice stays silent, and says so
                log.append(f"voice {v + 1} apart ({layer[1]:+d}, {layer[2]}) not written: no voice_intervals, voice_moves or second_figures word")
            elif layer[0] == "apart" and role == R.COUNTER and v == 1:   # a second counter-line of its own, clear of the first (a band without a tune)
                _, offset, density = layer
                low, high = plan.registers[role]
                reg2 = plan.bounds.get(f"{role}:second", (max(24, low + offset), min(100, high + offset)))
                habit2 = habit_near(models, role, tempo, plan.weights.get(role, "half"), random.Random(f"{seed}:{role}:second habit"), plan.habits[role], density)
                notes2, figures2, plog2 = writer.melody(song, [], reg2, models, random.Random(f"{seed}:{role}:second"), habit2,
                                                    key=key, hold=(), reference=reference, articulation=x["articulation"], echo_habit=x["echo"],
                                                    recall=models.get("melody_recall"), step_habit=x["steps"], repeat_habit=x["repeats"], plays=plan.plays[role],
                                                    role=role, chord_rate=x.get("chord_tones"), repeat_rate=x.get("repeat_rate"), grain=x.get("grain"), off_scale=x.get("off_scale"), clash_rates=x.get("clashes"),
                                                    tune_sounds=x.get("tune_sounds"), recall_moves=models.get("recall_moves"),
                                                    moves_rng=random.Random(f"{seed}:{role}:second:recall moves"), habit_at=habit_at_for(plan, role, habit2), envelope_at=envelope_at_for(plan, role, habit2))
                song.notes[role] += [(a, b - a, m, role) for a, b, m in notes2]
                line = line + [(a, b, m, 1) for a, b, m in notes2]
                figures = [f"{f} || {g}" for f, g in zip(figures, figures2)]
                log.append(f"a second line apart: register {reg2} ({offset:+d}), habit {habit2} ({density}); {sum(1 for f in figures2 if f != writer.REST)} bars, {len(notes2)} notes")
                log += [f"second: {l}" for l in plog2[-2:]]
            elif word_v:                                    # a voice the vocabulary cannot write beside the line: its own stretches stay silent, its
                pending.append((role, v, [], word_v))       # doubling and parallel ones are written (round 90)
                log.append(f"voice {v + 1} by the token's stretches ({word_v}) alone: no word for its own stretches")
        written[role] = Part(role, line, figures, log, beside=beside_v)
    scale = {(plan.tonic + i) % 12 for i in harmony.MODES["major" if plan.mode == "major" else "natural_minor"]}
    for role, v, own, word in pending:                      # the voices beside a line written by the token's stretches (round 90), every line in place
        spans = stretch_spans(relation_stretches(word), len(song.bars))
        notes_v = fold_voice(plan, role, v, stretched_notes(v, own, spans, written, scale, song.meter, written[role].log, song=song, role=role, models=models,
                                                            rng=random.Random(f"{seed}:{role}:voice {v}:stretch parallel"), clash_rates=(plan.extras.get(role) or {}).get("clashes")), song.meter)   # rounds 95, 97
        song.notes[role] += [(a, b - a, m, role) for a, b, m, *_ in notes_v]
        written[role].notes += notes_v
        written[role].notes.sort(key=lambda n: (n[0], n[3] if len(n) > 3 else 0))
    if R.MELODY in written:                                 # the theme in the band: doubled where the tune plays it, carried where it does not
        rng_theme = random.Random(f"{seed}:theme band")
        for line in double_theme(plan, song, written, models, rng_theme) + carry_theme(plan, song, written, models, rng_theme):
            written[R.MELODY].log.append(line)
    for line in hand_off_cells(plan, song, written, models, random.Random(f"{seed}:handoff")):
        written[R.MELODY].log.append(line)
    for line in copy_repeats(plan, song, written):
        for part in written.values():
            part.log.append(line)
    for role, part in written.items():                      # what the theme band, the hand-offs and the form's repeats copied across a
        if role != R.DRUMS and (plan.extras.get(role) or {}).get("stretch_bounds"):   # stretch line goes into its bars' registers too (round 92)
            part.notes[:] = fold_line(plan, role, part.notes, song.meter)
    return written
