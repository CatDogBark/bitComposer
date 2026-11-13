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
import bisect
import math
import random
from fractions import Fraction
import re
import statistics
from collections import Counter
from dataclasses import dataclass, field

from .. import harmony, harness, rhythm, tables, vocab, writer
from ..writer import scale_index, scale_pitch
from ..writer.upper import in_register as line_in_register   # the module, not the package's `upper` function
from ..writer.tune import share_at as sounded_share
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
            "chord_tones": str(writer.CHORD_ON_BEAT), "part_textures": None, "section_levels": "1.0", "section_densities": "d=", "section_fills": "same", "top_levels": str(TOP_LEVEL), "kit_pieces": "KShtco",
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
    feel: str = "duple"               # the song's feel (rhythm.song_feel): every figure table is drawn by it. Its token song's where the
                                      # vocabulary's tokens say their songs' feel (round 148), else the pooled `feels` word's draw
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
    section_fills: dict = field(default_factory=dict)   # a part -> {"line": [a fill's shift a bar], "beside": [the same for its voices beside the
                                      # line]}: +1 the last bar of a section drawn fuller, -1 thinner (section_fills, round 118)
    section_onsets: dict = field(default_factory=dict)   # a backing part -> [its line's onsets a bar in the token song's part of the form, or
                                      # None, a bar] (round 125): the writers keep the line's figures within writer.TIGHT of it (envelope_at_for)
    kit_bounds: list = field(default_factory=list)      # a bar -> {a kit piece's letter: (the least, the most hits it takes there)}, or None (round
                                      # 125, kit_piece_bounds): each piece as the token song strikes it in the part of the form
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
    ceilings: dict = field(default_factory=dict)        # a sample slot of samples_for (the part, part:second, part:v, part:stretch:i, part:v:stretch:i)
                                      # -> the highest note the SNES chip can play of the sample chosen for it (round 120; score.pitch_ceiling)
    layer_relations: dict = field(default_factory=dict)  # a layered part -> each voice beyond the line's relation word by stretch (the sixth field's
                                      # fifth sub-field, round 90: "ox9>dm-12x14>o", what it does beside which part, bar by bar), or None
    stretches: dict = field(default_factory=dict)       # a pitched part -> its line's instrument by stretch (the eleventh field, round 91): [(sample,
                                      # (low, high) or None, bars or None)] in time order, the last open; samples_for sets extras[part]["stretch_*"]
    tone_profiles: dict = field(default_factory=dict)   # a backing part -> its line's chord-tone profile from the token (round 111: field 15)
    step_profiles: dict = field(default_factory=dict)   # a backing part -> its line's step profile from the token (round 117: field 17)
    chord_shapes: dict | None = None                    # the token song's chord-shape profile ({shape: share}; round 112), or None
    form_letters: list | None = None                    # the token song's form, [(letter, bars)] (round 113), or None
    bass_continuity: float | None = None                # the token song's bass line pitch continuity (round 114), or None
    bass_downbeat: float | None = None                  # the share of its bars' first beats the token song's bass strikes on the chord's root (round 129), or None
    tune_shortest: dict = field(default_factory=dict)   # the melody, the counter -> the token song's line's shortest usual note in ms (round 136)
    tones_kept: dict = field(default_factory=dict)      # a chord part -> (the share of its bars with an earlier bar on their root that sound
                                                        # such a bar's pitch classes again in the token song, of those the share that sound
                                                        # the bar before's) (round 142)
    tune_together: dict = field(default_factory=dict)   # the tune's part (the melody; the counter-line in a band without one) -> (the share
                                                        # of the bars in which the bass plays an earlier bar again that the tune plays again
                                                        # too, where that bar is further back than the bar before; the same where it is the
                                                        # bar right before; either None where the song has under TOGETHER_BARS such bars;
                                                        # the share of the tune's bars with an earlier one that are an earlier bar note for
                                                        # note) in the token song (round 146)
    beat: int = 1                                       # 2 where the token's song is counted in double time (round 131): its kit's bars are
                                                        # the kit tables' counted so (round 145)
    together: dict = field(default_factory=dict)        # a chord part, the counter-line beside a tune -> the share of the bars in which its lead
                                                        # (the bass, the tune) plays an earlier bar again that the part plays again too in
                                                        # the token song (round 144)
    tune_places: dict = field(default_factory=dict)     # the melody, the counter -> the share of the token song's line's onsets on a quarter of
                                                        # the beat, on a third and finer than either (rhythm.FINE_PLACES; round 147)
    token_feel: str = "duple"                           # the token song's feel (round 147): its tune's places are held where the song is written in it
    with_kit: dict = field(default_factory=dict)        # the bass -> (the share of the token song's bass line's onsets struck with a kit hit, of
                                                        # the kit's hits struck with a bass note), the melody -> (its onsets' share,), over
                                                        # the bars both strike in (rhythm.with_kit_field; round 149)
    tune_lengths: dict = field(default_factory=dict)    # the melody, the counter -> how the token song's line sounds its notes (round 141):
                                                        # {the whole line (rhythm.LENGTH_WHOLE) or a gap class: (the share of the notes held,
                                                        # the share of its gap a held note sounds, a detached one; None where it has none)}
    first_beats: dict = field(default_factory=dict)     # a part -> the share of its bars the token song's part strikes on the first beat: the
                                                        # bass (round 133), a chord part (round 135)
    loops: dict = field(default_factory=dict)           # a voice (the part for its line, "part:v" for a voice beside it, the drums for the kit,
                                      # LOOP_CHORDS for the harmony) -> {the form's letter: (the figure's bars, the share of the voice's bars on it,
                                      # the bars off it counted from the part's first)} where the token song's voice loops (round 121); only where
                                      # the form is the token song's
    layer_struck: dict = field(default_factory=dict)    # a layered part -> each voice beyond the line's struck facts where it is struck with
                                                      # another (round 108: the seventh sub-field, struck_values_of), or None
    layer_stretches: dict = field(default_factory=dict)  # a layered part -> each voice beyond the line's instrument by stretch (the sixth field's sixth
                                      # sub-field, round 92), the same shape, or None
    pans: dict = field(default_factory=dict)          # a pitched part -> its voices' pans, the right side's share, the line first (the balance
                                      # token's tenth field, round 84); render.pan_of pans a voice there, by plan.PANS without the field; a
                                      # voice in two places keeps the token's word, "0.60x5|0.45x13" or "0.35x4>0.65" (round 85)

    @property
    def bass_first(self) -> float | None:
        """The share of its bars the token song's bass strikes on the first beat (round 133), or None."""
        return self.first_beats.get(R.BASS)

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


def tokens_say_feel(balance) -> bool:
    """Whether a vocabulary's balance tokens say their songs' feel (round 148): one of them at least carries the `feel=`
    word (rhythm.balance_units, round 147: a song that is not in duple feel says so, so a token without the word is a
    duple song's). False for a table counted before the word: its tokens say nothing of the feel, and a song planned
    from it keeps the pooled `feels` draw. `balance`: the vocabulary's balance table, or None."""
    table = getattr(balance, "table", balance)
    return table is not None and any(" feel=" in outcome for votes in table.votes.values() for outcome in votes)


def mask_strikes(tune_pat: str, mask: str) -> int:
    """The onsets of the bar a counter_figures mask makes of the tune's bar (rhythm.apply_mask); none for a rest."""
    bar = "-" if mask in (writer.REST, "-", "") else rhythm.apply_mask(tune_pat, mask)
    return 0 if bar == "-" else len(bar.split())


MASK_SLACK = 0.5                      # of the song's own onsets a bar (a note at the least): how far a part of the form's bars so far may run from them


def counter_mask(models: dict, context: tuple, tune_pat: str, mask: str, bounds: tuple | None, rng: random.Random, tries: int | None = None,
                 want: tuple | None = None, placed=None) -> tuple[str, str]:
    """A counter-line's bar's mask within its token song's own onsets for the part of the form (round 143): `mask`, the
    counter_figures draw for the bar (`context`, over the tune's bar `tune_pat`), where the bar it makes of the tune's
    (mask_strikes) strikes within `bounds` (least, most: plan.envelope_at_for's own envelope, half to one and a half
    times the song's onsets a bar there) and within `want` (least, most: what keeps the part of the form's bars so far
    at the song's own onsets a bar, MASK_SLACK of them either way; bars within the envelope alone, the first to fit
    taken, ran thin: 0.89 of the game's counter-lines' notes a bar at the median, a third of them under three
    quarters); else the word drawn again on `rng`, the bar's own stream, `tries` times (writer.TRIES); else one among
    the masks the table knows that fit, by its probabilities in the bar's context (evenly where it gives them none:
    parts.among's way, round 133); and where no mask is within both, the same asked of the envelope alone; else the
    first draw. `placed` (round 147): whether the bar a mask makes of the tune's (its pattern, "-" for a rest) keeps the
    line within its token song's places in the beat (rhythm.keeps_places over the line's bars before it) and, given the
    bar a mask is moved from as a second argument, puts no onset on a held fine place that bar had fewer on
    (rhythm.adds_places). The mask is come by as above, and where the bar it makes does not keep the places it gives
    way to the nearest mask the table knows that does: one that strikes with the same of the tune's onsets and has as
    many onsets of its own, those moved the least in time ("moved": the line then strikes as often, and its notes
    after the bar are drawn on the draws they had). Where the table knows none, the askings are made again with the
    places asked of every mask, on the same stream; where none keeps them the first answer stands. A line with no own
    onsets (`bounds` None) keeps its first draw unless that is off the places. Returns (the mask, how it was come by:
    "first", "again", "among", "moved", "none")."""
    if bounds is None and placed is None:
        return mask, "first"
    t = models["counter_figures"]
    t = t.table if hasattr(t, "table") else t
    drawn = [mask]
    made = lambda m: "-" if m in (writer.REST, "-", "") else rhythm.apply_mask(tune_pat, m)   # noqa: E731

    def asked(held: bool) -> tuple | None:
        """The mask by the askings above, the places asked too where `held`; None where no mask is within them."""
        for both in ((True, False) if want is not None else (False,)):
            fits = lambda m: ((bounds is None or bounds[0] <= mask_strikes(tune_pat, m) <= bounds[1])   # noqa: E731,B023
                              and (not both or want[0] <= mask_strikes(tune_pat, m) <= want[1]) and (not held or placed(made(m))))
            if fits(mask):
                return mask, "first"
            for i in range(writer.TRIES if tries is None else tries):
                if i >= len(drawn) - 1:
                    drawn.append(t.draw(tuple(context), rng, floored=False, floor_k=COUNTER_MASK_FLOOR, min_songs=PLAN_SONGS, floor_songs=PLAN_SONGS))
                if fits(drawn[i + 1]):                      # the draws made for the first asking are the second's too: one stream a bar
                    return drawn[i + 1], "again"
            known = [m for m in sorted(t.vocabulary) if fits(m)]
            if known:
                weights = [t.p(m, tuple(context)) for m in known]
                return (rng.choices(known, weights)[0] if sum(weights) > 0 else rng.choice(known)), "among"
        return None

    def nearest(m0: str) -> str | None:
        """The mask the table knows nearest `m0` that keeps the places: the same of the tune's onsets struck with, as many
        of its own, moved the least in time (the first in the masks' order of two as near); None where there is none, or
        the mask has no onsets of its own to move."""
        flags, bar, own = m0.partition("|")
        own0 = sorted(Fraction(x) for x in own.split())
        if not bar or not own0:
            return None
        best = None
        for m in sorted(t.vocabulary):
            f, b, o = m.partition("|")
            at = sorted(Fraction(x) for x in o.split()) if b else []
            if f.split() != flags.split() or len(at) != len(own0) or mask_strikes(tune_pat, m) != mask_strikes(tune_pat, m0) or not placed(made(m), made(m0)):
                continue
            far = sum(abs(float(x - y)) for x, y in zip(at, own0))
            if best is None or far < best[0] - 1e-9:
                best = (far, m)
        return best[1] if best is not None else None

    got = (asked(False) if bounds is not None else None) or (mask, "first" if bounds is None else "none")
    if placed is None or placed(made(got[0])):
        return got
    near = nearest(got[0])
    if near is not None:
        return near, "moved"
    return asked(True) or got


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


def form_of(text: str) -> list | None:
    """The balance token's `form=` field read (round 113, arrangement.form_field): "A2B8C9B8D14" -> [("A", 2), ("B", 8), ("C", 9),
    ("B", 8), ("D", 14)]; None where it cannot be read or has fewer than FORM_PARTS parts."""
    if not re.fullmatch(r"(?:[A-Za-z]\d+)+", text):
        return None
    form = [(m.group(1).upper(), int(m.group(2))) for m in re.finditer(r"([A-Za-z])(\d+)", text)]
    return form if len(form) >= rhythm.FORM_PARTS and all(n > 0 for _, n in form) else None


LOOP_CHORDS = "cycle"                 # the harmony's key among a plan's loops (round 121): the balance token's `cycle=` word


def loops_of(text: str) -> dict:
    """A voice's loops read from the balance token (round 121, arrangement.loops_text): "B1~75!3.7+D2~100" -> {"B": (1, 0.75,
    (3, 7)), "D": (2, 1.0, ())}, by the form's letter the figure's bars, the share of the voice's bars on it and the bars off
    it counted from the part's first; {} where it cannot be read."""
    out = {}
    for item in text.split("+"):
        m = re.fullmatch(r"([A-Za-z])(\d+)~(\d+)(?:!(\d+(?:\.\d+)*))?", item)
        if not m or int(m.group(2)) < 1:
            return {}
        out[m.group(1).upper()] = (int(m.group(2)), int(m.group(3)) / 100, tuple(int(x) for x in m.group(4).split(".")) if m.group(4) else ())
    return out


def looped_parts(parts: list, spec: dict | None) -> list:
    """The parts of the form a voice loops in (round 121): (the part's first bar, its bars, the figure's bars, the bars off
    the figure) for each part whose letter the voice's loops name (`spec`, loops_of) and that is long enough to play the
    figure twice; a part that repeats another carries its letter, and so its loop."""
    out = []
    for bar, n, _, label in parts:
        got = (spec or {}).get(label)
        if got and n >= 2 * got[0]:
            out.append((bar, n, got[0], {bar + j for j in got[2] if j < n}))
    return out


def spans_of(text: str) -> dict:
    """The parts of the form a part sounds in, read from the balance token (round 124, arrangement.part_spans_field):
    "A+B2.0+D0.4" -> {"A": (0, 0), "B": (2, 0), "D": (0, 4)}, by the form's letter the bars after the part's start it
    enters and the bars before its end it leaves; {} where it cannot be read."""
    out = {}
    for item in text.split("+"):
        m = re.fullmatch(r"([A-Za-z])(?:(\d+)\.(\d+))?", item)
        if not m:
            return {}
        out[m.group(1).upper()] = (int(m.group(2) or 0), int(m.group(3) or 0))
    return out


def token_textures(parts: list, band: list, spans: dict, log: list) -> tuple[list, dict]:
    """Which parts sound in each bar, as the token song has them (round 124): a part of the form holds the parts whose
    spans name its letter (spans_of), each from the bar it enters to the bar it leaves (whole where the plan's part is
    too short for the entrance); a part that repeats one copies its bars, as plan_texture's do. Returns the textures a
    bar and each part's bars, in plan_texture's shapes."""
    total = parts[-1][0] + parts[-1][1]
    textures = [""] * total
    cuts = []
    for bar, n, of, label in parts:
        if of is not None:
            src, m = parts[of][0], parts[of][1]
            for j in range(n):
                textures[bar + j] = textures[src + min(j, m - 1)]
            continue
        for role in band:
            got = (spans.get(role) or {}).get(label)
            if got is None:
                continue
            enters, leaves = got if got[0] + got[1] < n else (0, 0)
            for k in range(bar + enters, bar + n - leaves):
                textures[k] = f"{textures[k]} {role}".strip()
            if enters or leaves:
                cuts.append(f"{role} " + " ".join(x for x in (f"enters {enters} in" if enters else "", f"leaves {leaves} before the end of" if leaves else "") if x) + f" {label}")
    plays = {role: [role in textures[k].split() for k in range(total)] for role in band}
    log.append("textures from the balance's song (round 124): " + " | ".join(f"{p[3]}: {textures[p[0]] or 'none'}" for p in parts))
    if cuts:
        log.append("entrances from the balance's song (round 124): " + "; ".join(cuts))
    return textures, plays


def onsets_of(text: str) -> dict:
    """A voice's onsets a bar by the form's letters, read from the balance token (round 125, arrangement.section_onsets_text):
    "A6+B2!1+C4.5!7" -> {"A": (6.0, None), "B": (2.0, 1), "C": (4.5, 7)}, by the letter the median of its onsets a bar there
    and its onsets in the part's last bar where that is a fill or a thinning; {} where it cannot be read."""
    out = {}
    for item in text.split("+"):
        m = re.fullmatch(r"([A-Za-z])(\d+(?:\.\d)?)(?:!(\d+))?", item)
        if not m or float(m.group(2)) <= 0:
            return {}
        out[m.group(1).upper()] = (float(m.group(2)), int(m.group(3)) if m.group(3) is not None else None)
    return out


def kit_onsets_of(text: str) -> dict:
    """The kit's pieces' hits a bar by the form's letters, read from the balance token (round 125, arrangement.kit_onsets_field):
    "AS28.5@100,c1@50+BS20@75" -> {"A": {"S": (28.5, 1.0), "c": (1.0, 0.5)}, "B": {"S": (20.0, 0.75)}}, by the letter each
    piece's median hits a bar over the bars it plays there and the share of the part's bars it plays in; {} where it cannot
    be read."""
    out = {}
    for item in text.split("+"):
        if not item or not item[0].isalpha():
            return {}
        pieces = {}
        for piece in item[1:].split(","):
            m = re.fullmatch(r"([A-Za-z])(\d+(?:\.\d)?)@(\d+)", piece)
            if not m:
                return {}
            pieces[m.group(1)] = (float(m.group(2)), int(m.group(3)) / 100)
        out[item[0].upper()] = pieces
    return out


KIT_THROUGH = 0.75                    # a kit piece the token song plays in this share of a part of the form's bars or more plays in every bar of it
KIT_SOME = 0.25                       # one it plays in this share or more may play in a bar; one under it strikes a bar once at most
KIT_FLOOR_CAP = 12                    # hits a bar the least a piece's bar must hold is never set over: a snare the game rolls at 28 a bar is asked
                                      # for twelve or more, and the writers' grid gives it sixteen


def kit_piece_bounds(stats: dict | None) -> dict:
    """The hits a bar each kit piece keeps to in a part of the form (round 125): a piece's median hits there within the
    writers' own TIGHT (figures.TIGHT: half to one and a half times), for a piece the token song plays through the part
    (KIT_THROUGH of its bars); none to that many for one it plays in some bars (KIT_SOME); one at most for one it strikes
    more rarely; none for a piece the part of the form never hears. {piece letter: (least, most)} for every letter."""
    out = {}
    low, high = writer.TIGHT
    cap = writer.FREE_HITS[1]
    for letter in rhythm.LETTERS.values():
        got = (stats or {}).get(letter)
        if not got:
            out[letter] = (0, 0)
            continue
        n = min(cap, got[0])
        least, most = min(KIT_FLOOR_CAP, max(1, math.ceil(low * n))), max(1, math.floor(high * n))
        out[letter] = (least, most) if got[1] >= KIT_THROUGH else (0, most) if got[1] >= KIT_SOME else (0, 1)
    return out


def token_sections(parts: list, band: list, plays: dict, voices: dict, onsets: dict, kit_onsets: dict, layer_onsets: dict, log: list) -> tuple[dict, list, dict, dict]:
    """How busy each part is in each part of the form, as the token song has it (round 125), where the form's letters are
    its own. Returns ({a backing part: [its line's onsets a bar, or None, a bar]}, [the kit's pieces' bounds a bar
    (kit_piece_bounds), or None], {a part: [its density tier's shift a bar]}, {a part: {"line": [a fill's shift a bar],
    "beside": [...]}}), the last two in plan_section_densities' and plan_section_fills' shapes. A backing part's line
    (the bass, a chord part) takes its onsets a bar from the token's part of the form, its last bar that bar's own where
    the token says a fill or a thinning; since round 138 the tune's line takes its onsets a bar the same way (the
    melody's, or the counter's in a band without one: the new bars its writer draws keep within them), where it had
    kept its own density and taken only the token song's tier against it (a part of the form at DENSITY_STEP times the
    tune's typical onsets a bar or more a tier up, at the inverse or less a tier down: still returned, for a part
    without the onsets); since round 143 the counter-line beside a tune takes its line's onsets a bar too (its bar's
    mask is drawn within them, counter_mask): its bar had been a mask over the tune's bar from the pooled
    counter_figures word, whatever the song's own counter-line plays (the written Locke's ran 4.4 notes a bar where the
    game's plays 2.8, a quarter of its moves a sixteenth apart where the game's has none); the counter's last bar
    beside a tune, and the last bar of the first voice beside any line,
    take the token's fill or thinning; a part of the form that returns takes its first statement's. The section_densities and
    section_fills words are not drawn: they are drawn on their own streams, so no other draw moves."""
    total = parts[-1][0] + parts[-1][1]
    tune_role = R.MELODY if R.MELODY in band else R.COUNTER   # the part that carries the tune: the counter's where the band has no melody
    lines = {role: [None] * total for role in band if role in rhythm.UPPER + (R.BASS, tune_role, R.COUNTER) and onsets.get(role)}   # the tune's too (round 138),
                                                            # and the counter-line's beside it (round 143)
    kit = [None] * total
    densities = {role: [0] * total for role in band if role not in (R.DRUMS, R.COUNTER)}
    fills = {role: {"line": [0] * total, "beside": [0] * total} for role in band if role != R.DRUMS}
    step = rhythm.DENSITY_STEP
    fill_of = lambda pair: 0 if not pair or pair[1] is None else 1 if pair[1] >= pair[0] else -1   # noqa: E731  the token's "!": over the median a fill, under it a thinning
    tune = onsets.get(R.MELODY) or {}
    tune_bars = [tune[label][0] for bar, n, of, label in parts if label in tune for k in range(bar, bar + n) if plays.get(R.MELODY, [False] * total)[k]]
    typical = statistics.median(tune_bars) if tune_bars else None
    said = []
    for bar, n, of, label in parts:
        if of is not None:
            src, m = parts[of][0], parts[of][1]
            for j in range(n):
                at = src + min(j, m - 1)
                kit[bar + j] = kit[at]
                for role in lines:
                    lines[role][bar + j] = lines[role][at]
                for role in densities:
                    densities[role][bar + j] = densities[role][at]
                for role in fills:
                    for kind in ("line", "beside"):
                        fills[role][kind][bar + j] = fills[role][kind][at]
            continue
        if R.DRUMS in band and kit_onsets:
            bounds = kit_piece_bounds(kit_onsets.get(label))
            for k in range(bar, bar + n):
                kit[k] = bounds
        for role in lines:
            got = onsets[role].get(label)
            if got is None:
                continue
            for k in range(bar, bar + n):
                lines[role][k] = got[0]
            if got[1] is not None:
                lines[role][bar + n - 1] = float(max(1, got[1]))
            said.append(f"{role} {got[0]:g} in {label}" + (f" ({got[1]} in its last bar)" if got[1] is not None else ""))
        if typical and R.MELODY in densities and label in tune:
            shift = 1 if tune[label][0] >= step * typical else -1 if tune[label][0] <= typical / step else 0
            if shift:
                densities[R.MELODY][bar:bar + n] = [shift if plays[R.MELODY][k] else 0 for k in range(bar, bar + n)]
                said.append(f"melody {'denser' if shift > 0 else 'sparser'} in {label}")
        if n >= rhythm.FILL_BARS:
            for role in fills:
                if role in (R.MELODY, R.COUNTER):
                    fills[role]["line"][bar + n - 1] = fill_of((onsets.get(role) or {}).get(label))
                if voices.get(role, 1) >= 2:
                    fills[role]["beside"][bar + n - 1] = fill_of(((layer_onsets.get(role) or {}).get(1) or {}).get(label))
    filled = [f"{role}'s {'line' if kind == 'line' else 'voices beside the line'} {'fuller' if x > 0 else 'thinner'} in the last bar of {label}"
              for bar, n, of, label in parts if of is None for role, kinds in fills.items() for kind in ("line", "beside") for x in (kinds[kind][bar + n - 1],) if x]
    if said:
        log.append("onsets a bar by section from the balance's song (round 125): " + "; ".join(said))
    if any(b is not None for b in kit):
        log.append("kit pieces by section from the balance's song (round 125): " + " | ".join(
            f"{label}: " + (" ".join(f"{letter} {lo}-{hi}" for letter, (lo, hi) in kit[bar].items() if hi) or "none") for bar, n, of, label in parts if of is None and kit[bar] is not None))
    if filled:
        log.append("fills by section from the balance's song (round 125): " + "; ".join(filled))
    return lines, kit, densities, fills


def hold_loop(plan: "Plan", key: str, notes: list, meter: int = None) -> tuple[list, int, set]:
    """A voice's bars made its figure's where the token song's voice loops (round 121). In each part of the form the voice's
    loops name (plan.loops[key], looped_parts), the figure is the first bar the voice plays at each place of the figure's
    length that the token song has on its figure; every later bar on the figure plays it again note for note, pitch and
    place and length. A bar the token song has off its figure (a fill, a turn) and a bar the voice rests in stay as written.
    FFVI repeats a backing voice's bar: the figure holds half the bars or more in 0.45 of its accompaniment lines' parts of
    the form, 0.47 of the voices' beside them and of its basses', 0.69 of its kits', and Battle Theme's guitar plays one bar
    through all eight of its B. The periods word (round 30) repeats a bar's rhythm, and the writers drew its notes again, so
    no written bar came out twice. Notes of any writer's shape, (start, end, ...); returns the notes, the bars copied and the
    bars held on the figure (its own bars and the copies), for the passes after the writing to leave as they are."""
    meter = meter or METER
    parts = looped_parts(plan.parts, (plan.loops or {}).get(key))   # (by the attribute: the map of the vocabulary reads a table's name in quotes as its use)
    if not parts or not notes:
        return notes, 0, set()
    by = {}
    for x in notes:
        by.setdefault(int((x[0] + rhythm.NEAR) // meter), []).append(x)
    copied, held = 0, set()
    for bar, n, lag, off in parts:
        figure = {}
        for k in range(bar, bar + n):
            if k in off or not by.get(k):
                continue
            src = figure.setdefault((k - bar) % lag, k)
            held.add(k)
            if src != k:
                shift = float(meter * (k - src))
                again = [(x[0] + shift, x[1] + shift) + tuple(x[2:]) for x in by[src]]
                copied += sorted((round(x[0], 3),) + tuple(x[2:3]) for x in again) != sorted((round(x[0], 3),) + tuple(x[2:3]) for x in by[k])
                by[k] = again
    return sorted((x for ns in by.values() for x in ns), key=lambda x: x[0]), copied, held


TEMPO_NEAR = 0.1                      # a written song's tempo sits within this share of its token song's own (round 137)


def tempo_near(models: dict, cls: str | None, own: float, rng: random.Random) -> float:
    """A tempo for a song whose token song runs at `own` beats a minute (round 137): one of the tempos word's tempos in
    the token's class within TEMPO_NEAR of it, by the word's own probabilities under the class; the song's own tempo,
    kept inside the class, where the word has none so near. The class alone (round 54) is a third of the game's tempos
    wide: a song on Edgar and Sabin's token, 90 beats a minute in the game, was written at 125."""
    table = render_mod.models_or_empty(models).get("tempos")
    low, high = (1 - TEMPO_NEAR) * own, (1 + TEMPO_NEAR) * own
    near = sorted(float(o) for o in (table.vocabulary if table is not None else ()) if o.replace(".", "", 1).isdigit()
                  and low <= float(o) <= high and (cls is None or rhythm.band(float(o)) == cls))
    if not near:
        return rhythm.within_band(own, cls) if cls else own
    weights = [table.p(str(int(o)) if o == int(o) else str(o), ("song", cls or rhythm.band(o))) for o in near]
    return rng.choices(near, weights)[0] if sum(weights) > 0 else rng.choice(near)


def plan_form(models: dict, rng: random.Random, log: list, max_bars: int | None = None, form: list | None = None) -> list:
    """The form: one of the game's forms whole (the letters table: "A B A B
    C", a part returning after another in 29 % of FFVI's songs where a
    chain by index returned in 15 %), each new part's length by the song's
    length habit (the lengths table), a repeat as long as the part it
    repeats; without a letters table, how many parts (the sizes table) and
    each part new, again or back by its index (the form table). (first
    bar, bars, the part repeated or None, letter). `form`: the token
    song's own form (round 113, [(letter, bars)]), its letters taken in
    place of the letters draw and its bars in place of the lengths draws;
    a repeat is as long as the part it repeats, so a part read returning
    with other bars (15 of FFVI's 62 token forms: a fragment, or a longer
    second statement) plays whole at its first statement's bars; a form
    past the bars asked is cut as any (one short of them leaves the
    plan's draw standing: _plan_once)."""
    habit = _draw(models, "length_habits", ("form",), rng, log)
    sizes = {}
    for l, n in form or []:                                 # a letter's bars are its first statement's (round 113)
        sizes.setdefault(l, n)
    if "letters" in models or form:
        drawn_letters = _draw(models, "letters", ("form",), rng, log).split()[:MAX_PARTS] if "letters" in models else []
        letters = [l for l, _ in form[:MAX_PARTS]] if form else drawn_letters
        parts, bar = [], 0
        for i, label in enumerate(letters):
            of = letters.index(label) if label in letters[:i] else None
            if of is None and label in sizes:               # the token song's bars for the part (round 113)
                n = max(1, int(sizes[label]))
            elif of is None:
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


SHAPE_MARGIN = 0.05                   # how far over its share of the token song's chord-shape profile a quality may run before a
                                      # changing chord takes the quality most under its share (round 112)


def shape_profile_of(text: str) -> dict | None:
    """The balance token's `shapes=` field read (round 112, arrangement.chord_shape_profile): "maj7:45/5:17/maj:3" -> {"maj7":
    0.45, "5": 0.17, "": 0.03}; None where it cannot be read."""
    out = {}
    for part in text.split("/"):
        name, _, pct = part.partition(":")
        shape = "" if name == "maj" else name
        if shape not in harmony.SHAPES or not pct.isdigit():
            return None
        out[shape] = int(pct) / 100
    return out or None


def with_shape(name: str, shape: str) -> str:
    """A numeral with another quality on the same degree (round 112): "IV" with "maj7" is "IVmaj7", "V7" with "m" is "v", as
    vocab.numeral spells them (a minor-family shape a lower-case numeral with its m dropped)."""
    m = NUMERAL.match(name)
    if not m:
        return name
    acc, roman, _ = m.groups()
    base = acc + roman.upper()
    return base.lower() + vocab.MINOR_SHAPES[shape] if shape in vocab.MINOR_SHAPES else base + shape


def reshaped_name(name: str, tonic: int, mode: str, profile: dict, counts) -> tuple[str, int]:
    """A changing chord's quality held to the token song's chord-shape profile (round 112): the name as drawn while its shape,
    with this bar counted, is within SHAPE_MARGIN of the profile's share (`counts`: the shapes of the bars so far), else the
    same degree in the profile's shape most under its share, where one is; (the name, 1 where it was re-qualified)."""
    ch = chord_of(name, tonic, mode)
    if ch is None:
        return name, 0
    cur = ch[1]
    total = sum(counts.values())
    if (counts[cur] + 1) / (total + 1) <= profile.get(cur, 0.0) + SHAPE_MARGIN:
        return name, 0
    under = {sh: profile[sh] - counts[sh] / (total + 1) for sh in profile if sh != cur}
    best = max(under, key=lambda sh: (under[sh], sh)) if under else None
    if best is None or under[best] <= 0:
        return name, 0
    new = with_shape(name, best)
    return (new, 1) if chord_of(new, tonic, mode) is not None else (name, 0)


THIRDLESS = ("5", "sus2", "sus4")      # the chord shapes with no third: a chord of either third may take one


def chord_third(name: str, tonic: int, mode: str) -> str | None:
    """A chord's third as its name has it (round 127): "m" for a minor-family shape (vocab.MINOR_SHAPES), "M" for a major
    one; for a shape with no third (THIRDLESS) the third its root has in the key's scale (a minor key's with its raised
    seventh too, so its dominant may be major or minor), None where the scale gives its root neither or both."""
    ch = chord_of(name, tonic, mode)
    if ch is None:
        return None
    root, shape = ch
    if shape in vocab.MINOR_SHAPES:
        return "m"
    if shape not in THIRDLESS:
        return "M"
    scale = {(tonic + i) % 12 for i in harmony.MODES["major" if mode == "major" else "natural_minor"]} | ({(tonic + 11) % 12} if mode != "major" else set())
    minor, major = (root + 3) % 12 in scale, (root + 4) % 12 in scale
    return "m" if minor and not major else "M" if major and not minor else None


def quals_of(text: str) -> dict:
    """The balance token's `quals=` field read (round 127, arrangement.chord_degree_shapes): "1~maj7:86+0~5:45/sus4:25" ->
    {1: [("maj7", 0.86)], 0: [("5", 0.45), ("sus4", 0.25)]}, by a degree's semitones over the tonic the qualities its song
    gives it with their share of the degree's beats, the most heard first; {} where it cannot be read."""
    out = {}
    for item in text.split("+"):
        offset, _, shapes = item.partition("~")
        pairs = [x.partition(":") for x in shapes.split("/")] if shapes else []
        if not offset.isdigit() or not 0 <= int(offset) < 12 or not pairs or any((n != "maj" and n not in harmony.SHAPES) or not pct.isdigit() for n, _, pct in pairs):
            return {}
        out[int(offset)] = [("" if n == "maj" else n, int(pct) / 100) for n, _, pct in pairs]
    return out


DEGREE_OWN = 0.6                      # a quality a degree has on this share of its beats or more in the token song is the degree's own (round 127)


def hold_chord_shapes(names: list, drawn: list, parts: list, tonic: int, mode: str, degree_shapes: dict | None = None) -> tuple[int, int]:
    """A chord takes the quality its degree has in the token song, and keeps one quality through the song (round 127), on
    the bars as the chain drew and re-qualified them. `drawn` holds, for each bar whose chord the chain drew anew, the
    chord's name before the token song's shape profile was held on it (round 112, reshaped_name), None for a bar that
    holds the bar before's chord. A chord as drawn on a degree that has one quality in the token song (`degree_shapes`,
    quals_of: by its semitones over the tonic; DEGREE_OWN of the degree's beats or more) takes that quality: Battle
    Theme's major sevenths sit on its flat second, and the profile's hold, which knows no degrees, had put one on the
    written song's tonic and left its flat second a bare fifth. Any other chord takes, of the qualities the profile's
    hold gave it bar by bar, the one it took in the most bars among those the song gives its degree and those that keep
    its own third (chord_third: a major chord is not made minor, nor a minor one major; a shape with no third suits
    either), the name as drawn at a tie or where none fits. A held bar takes the bar before's chord again, and a part of the form
    that repeats one its chords. In place; returns (the bars that took their degree's quality, the other bars changed).
    The profile's hold decides bar by bar from the shapes so far, so one drawn chord came out in two or three qualities
    in a song (Gogo's G minor, G major, G5, G7 in four bars): a chord changed its quality on its own degree in 0.19 of
    the written songs' chord changes against 0.09 of FFVI's."""
    took = {}
    for k, d in enumerate(drawn):
        if d is not None and names[k] is not None:
            took.setdefault(d, Counter())[names[k]] += 1
    final, by_degree = {}, set()
    for d, c in took.items():
        ch = chord_of(d, tonic, mode)
        own = (degree_shapes or {}).get((ch[0] - tonic) % 12) if ch is not None else None
        if own:
            by_degree.add(d)
        if own and own[0][1] >= DEGREE_OWN:                 # the degree has one quality in the token song: the chord takes it
            new = d if ch[1] == own[0][0] else with_shape(d, own[0][0])
            final[d] = new if chord_of(new, tonic, mode) is not None else d
            continue
        third = chord_third(d, tonic, mode)                 # else, of the qualities the profile's hold gave it, the one it took in the most
        songs = {sh for sh, _ in own} if own else set()     # bars among those the song gives the degree and those that keep its third
        fits = {n: x for n, x in c.items() if chord_of(n, tonic, mode)[1] in songs or third is None or chord_of(n, tonic, mode)[1] in THIRDLESS
                or chord_third(n, tonic, mode) == third}
        final[d] = max(fits, key=lambda n: (fits[n], n == d, n)) if fits else d
    changed, taken = 0, 0
    for bar, n, of, _ in parts:
        if of is not None:
            continue
        for k in range(bar, bar + n):
            want = final.get(drawn[k]) if drawn[k] is not None else (names[k - 1] if k > bar else names[k])
            if want is not None and want != names[k]:
                names[k] = want
                changed += 1
            if drawn[k] in by_degree:
                taken += 1
    for bar, n, of, _ in parts:
        if of is not None:
            names[bar:bar + n] = names[parts[of][0]:parts[of][0] + n]
    return taken, changed


def plan_chords(models: dict, parts: list, loop_bar: int, tonic: int, mode: str, rng: random.Random, log: list,
                hold_share: float | None = None, hold_rng: random.Random | None = None, shape_profile: dict | None = None,
                cycle: dict | None = None, degree_shapes: dict | None = None) -> tuple[list, list]:
    """A chord a bar, as numerals and as (root, shape): drawn bar by bar
    from the chord mixture (a new part starts the chain's context over,
    the song's urn going on), the loop's first bar from the loops table, a
    repeated part keeping the chords of the part it repeats. `shape_profile`:
    the token song's chord shapes (round 112): a changing chord whose quality
    runs over its share takes the quality most under its share on the same
    degree (reshaped_name); a held bar keeps its chord whole. `cycle`: the
    token song's harmony's loops (round 121, loops_of): once every bar is
    drawn as before (the chain, its holds and its shapes untouched, so no
    other draw moves), a bar on the figure of a part of the form the loops
    name takes the chord of the first bar at its place of the figure, a bar
    off it keeps its own draw, and a part that repeats one takes its chords
    again."""
    total = parts[-1][0] + parts[-1][1]
    home = "I" if mode == "major" else "i"
    names = [None] * total
    cache, loops = models.get("chords"), models.get("loops")
    played, previous = Counter(), None
    held_lines, bar_lines = 0, 0
    shape_counts, reshaped = Counter(), 0                   # the bars' chord shapes so far, for the token's profile (round 112)
    drawn = [None] * total                                  # a bar's chord as the chain drew it, before the profile's hold (round 127)
    for bar, n, of, _ in parts:
        if of is not None:
            src = parts[of][0]
            names[bar:bar + n] = names[src:src + n]
            for x in names[src:src + n]:
                ch = chord_of(x, tonic, mode) if x else None
                if ch is not None:
                    shape_counts[ch[1]] += 1
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
            if hold_share is not None and hold_rng is not None and k > bar and previous is not None:   # the chord held as the token's
                bar_lines += 1                              # song holds its chords (round 106): the chain's draw above is still made, on an
                if hold_rng.random() < hold_share:          # own stream the hold, so no other draw moves
                    name = previous
                    held_lines += 1
                elif name == previous and cache is not None:   # the share says change: a chord the chain repeated is drawn again on the own
                    unit = tables.Unit("", "", "", {"part": R.HARMONY, "mode": mode, "previous": prev_name})   # stream, so the song holds at the
                    again = cache.draw(unit, previous, played, hold_rng, keep=lambda o: o not in (rhythm.NO_CHORD, previous))   # share, not over it
                    if again and chord_of(again, tonic, mode) is not None:
                        name = again
            if (shape_profile or degree_shapes) and (k == bar or name != previous):
                drawn[k] = name                             # the chord as the chain drew it (round 127)
            if shape_profile and (k == bar or name != previous):   # a changing chord's quality held to the token song's shapes (round 112)
                name, re_ = reshaped_name(name, tonic, mode, shape_profile, shape_counts)
                reshaped += re_
            ch = chord_of(name, tonic, mode)
            if ch is not None:
                shape_counts[ch[1]] += 1
            played[name] += 1
            previous = prev_name = name
            names[k] = name
    by_degree, one_shape = hold_chord_shapes(names, drawn, parts, tonic, mode, degree_shapes) if shape_profile or degree_shapes else (0, 0)
    if one_shape:                                           # a chord's quality its degree's in the token song, and one through the song (round
        shape_counts = Counter(ch[1] for ch in (chord_of(x, tonic, mode) for x in names if x) if ch is not None)   # 127), once the chain is
                                                            # drawn: its draws, its holds and its shapes stand, so no other draw moves
    looped = 0                                              # the harmony's loops (round 121), on the bars as drawn: a bar on the figure takes
    for bar, n, lag, off in looped_parts([p for p in parts if p[2] is None], cycle):   # the chord of the first bar at its place of it, whole
        figure = {}
        for k in range(bar, bar + n):
            if k in off or names[k] is None:
                continue
            src = figure.setdefault((k - bar) % lag, k)
            if src != k and names[k] != names[src]:
                names[k] = names[src]
                looped += 1
    if looped:
        for bar, n, of, _ in parts:                         # a part that repeats one: its chords again, as looped
            if of is not None:
                names[bar:bar + n] = names[parts[of][0]:parts[of][0] + n]
        shape_counts = Counter(ch[1] for ch in (chord_of(x, tonic, mode) for x in names if x) if ch is not None)
        held_now = sum(1 for bar, n, of, _ in parts if of is None for k in range(bar + 1, bar + n) if names[k] == names[k - 1])
        lines = sum(n - 1 for _, n, of, _ in parts if of is None)
        log.append(f"the balance's song's harmony loops (round 121): {looped} bars take their figure's chord; {held_now} of {lines} bar lines inside the parts hold their chord now")
    log.append("chords " + " ".join(names))
    if hold_share is not None:
        log.append(f"chords held at the balance's song's share {hold_share:.2f}: {held_lines} of {bar_lines} bar lines inside the parts")
    if shape_profile:
        tot = max(1, sum(shape_counts.values()))
        log.append(f"chord shapes held to the balance's song's profile (round 112): {reshaped} of {tot} bars re-qualified, "
                   f"{by_degree} chords on a degree the song has and {one_shape} bars put to their chord's one quality (round 127); written "
                   + " ".join(f"{sh or 'maj'} {c / tot:.2f}" for sh, c in shape_counts.most_common()) + " (the song's "
                   + " ".join(f"{sh or 'maj'} {v:.2f}" for sh, v in shape_profile.items()) + ")")
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


def section_levels_of(text: str) -> list:
    """A part's level in each part of its song's form, read from the balance token (round 150, arrangement.section_levels_field):
    "vA1.0+B0.4+C-" -> [("A", 1.0), ("B", 0.4), ("C", None)], the form's own parts in its order, None where the song's part
    has no count; [] where it cannot be read."""
    if not text.startswith("v"):
        return []
    out = []
    for item in text[1:].split("+"):
        m = re.fullmatch(r"([A-Za-z])(\d\.\d|-)", item)
        if not m:
            return []
        out.append((m.group(1).upper(), None if m.group(2) == "-" else float(m.group(2))))
    return out


def tokens_say_levels(balance) -> bool:
    """Whether a vocabulary's balance tokens say their songs' parts' levels by section (round 150): one of them at least
    carries the field (arrangement.section_levels_field), so a part whose token carries none has no section of its own
    to step in. False for a table counted before the word, whose songs keep the pooled section_levels draws. `balance`:
    the vocabulary's balance table, or None."""
    table = getattr(balance, "table", balance)
    return table is not None and any(SECTION_LEVELS_FIELD.search(outcome) for votes in table.votes.values() for outcome in votes)


SECTION_LEVELS_FIELD = re.compile(r":v[A-Za-z](?:\d\.\d|-)(?:\+[A-Za-z](?:\d\.\d|-))*(?= |$)")   # a part's token ending in its section levels field


def own_section_levels(drawn: dict, token: dict, parts: list, plays: dict, own_form: bool, log: list) -> dict:
    """Each part's level a bar as its token song's part has it by section (round 150), over plan_section_levels' draws
    (`drawn`), for a vocabulary whose tokens say it (tokens_say_levels). `token`: a part -> [(the form's letter, its
    level there over its level in the song, or None)] for the token song's own parts of the form (section_levels_of).
    Where the form's letters are the token song's (`own_form`) a part of the form takes its letter's level, 1.0 where
    the song's part has no count there. Everywhere else the part holds its level, 1.0: in a form that is not the token
    song's (one drawn because the song's is short of the bars asked) no section is a section of its song, and a part
    the token says nothing of has none of its own to step in. A repeated part copies its source's. The pooled
    section_levels word draws a section's level by the part and its place in the form: a tune on Fanfare's token,
    which holds one level through its song, drew 0.8 and then 2.0 and played a four-bar section 8 dB over the rest.
    Returns the levels; logs what it took against the draw."""
    out = {role: list(levels) for role, levels in drawn.items()}
    said = []
    for role in out:
        by_letter = dict(token.get(role) or ()) if own_form else {}
        for bar, n, of, letter in parts:
            if of is not None:
                src = parts[of][0]
                out[role][bar:bar + n] = out[role][src:src + n]
                continue
            if not any(plays[role][bar:bar + n]):
                continue
            level = by_letter.get(letter)
            level = 1.0 if level is None else level
            was = out[role][bar]
            out[role][bar:bar + n] = [level] * n
            if abs(level - was) > 1e-9:
                said.append(f"{role} {level:.1f} in {letter} (the draw {was:.1f})")
    if said:
        log.append("levels by section from the balance (round 150)" + ("" if own_form else ", the form not the balance's song's and every part at its own level")
                   + ": " + "; ".join(said))
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


def plan_section_fills(models: dict, parts: list, band: list, plays: dict, voices: dict, rng: random.Random, log: list) -> dict:
    """What each pitched part does in each own section's last bar (section_fills, round 118): drawn a section for the part's
    line and, where it has voices beside the line, for those, by the part, the voice kind and the section's place in the form:
    "fuller" a fill, +1 on the section's last bar (a tier denser for the line through the density shift its writer reads; every
    followed onset and one between each pair for a struck voice), "thinner" -1, "same" nothing; a section under FILL_BARS bars
    draws nothing, a repeated section copies its source's. Drawn on an own stream. Returns {part: {"line": [shift a bar],
    "beside": [shift a bar]}}; logs the fills. Battle Theme's synth plays 15 notes into C against 8 a bar and 7 into D against
    4; the written synths never filled."""
    total = parts[-1][0] + parts[-1][1]
    out, said = {}, []
    for i, (bar, n, of, letter) in enumerate(parts):
        for role in band:
            if role == R.DRUMS:
                continue
            kinds = ["line"] + (["beside"] if voices.get(role, 1) >= 2 else [])
            mine = out.setdefault(role, {"line": [0] * total, "beside": [0] * total})
            if of is not None:
                src = parts[of][0]
                for kind in kinds:
                    mine[kind][bar:bar + n] = mine[kind][src:src + n]
                continue
            if n < rhythm.FILL_BARS or not any(plays[role][bar:bar + n]):
                continue
            for kind in kinds:
                drawn = _draw(models, "section_fills", (role, kind, rhythm.form_place_of(i, len(parts))), rng, log)
                shift = 1 if drawn == "fuller" else -1 if drawn == "thinner" else 0
                if shift:
                    mine[kind][bar + n - 1] = shift
                    said.append(f"{role}'s {'line' if kind == 'line' else 'voices beside the line'} {'fuller' if shift > 0 else 'thinner'} in the last bar of {letter}")
    if said:
        log.append("fills by section (section_fills): " + "; ".join(said))
    return out


def habit_at_for(plan, role: str, habit=None):
    """A part's habit a bar for its writer (round 101): the song's habit with its density tier shifted where the
    section_densities draw says; None where no bar shifts (the writer keeps its one habit)."""
    own = getattr(plan, "section_onsets", {}).get(role) if habit is None else None
    if own and any(own):                                    # the token song's own onsets a bar by section (round 125): the tier they sit in
        base = plan.habits[role]
        tier = lambda n: " ".join([rhythm.habit_of(n, rhythm.DENSITIES)] + str(base).split()[1:]) if n and isinstance(base, str) and base.split() else base   # noqa: E731
        return lambda k: tier(own[k] if 0 <= k < len(own) else None)
    shifts = plan.section_densities.get(role)
    if not shifts or not any(shifts):
        return None
    base = habit if habit is not None else plan.habits[role]
    return lambda k: rhythm.shift_habit(base, shifts[k] if 0 <= k < len(shifts) else 0)


def envelope_at_for(plan, role: str, habit=None):
    """A part's figure envelope a bar for its writer (round 101): the onsets a bar the section_densities shift asks
    (rhythm.density_bounds: a tier denser, DENSITY_STEP times the part's typical or more; a tier sparser, the typical over
    it or fewer; the writer hands in the part's own running density as the typical, the tier's FFVI median standing in),
    None for a bar without a shift; None where no bar shifts. Where the plan has the token song's own onsets a bar for
    the part (round 125) the envelope is half to one and a half times them, and it says so (`own`: round 134)."""
    own = getattr(plan, "section_onsets", {}).get(role) if habit is None else None
    if own and any(own):                                    # the token song's own onsets a bar by section (round 125): within the writers' TIGHT of them
        low, high = writer.TIGHT

        def own_envelope(k, typical=None):
            return (max(1, math.ceil(low * own[k])), max(1, math.floor(high * own[k]))) if 0 <= k < len(own) and own[k] else None
        own_envelope.own = True                             # the song's own, not a tier's shift: a bar copied for a theme's return keeps within it
        return own_envelope                                 # too (round 134, parts._free_figures)
    shifts = plan.section_densities.get(role)
    if not shifts or not any(shifts):
        return None
    base = habit if habit is not None else plan.habits[role]
    return lambda k, typical=None: rhythm.density_bounds(base, shifts[k] if 0 <= k < len(shifts) else 0, typical)


def lengths_of(text: str) -> dict:
    """A tune's note lengths as its token's twenty-sixth field carries them (round 141, rhythm.tune_lengths_field, without
    the "h"): {rhythm.LENGTH_WHOLE or a gap class: (the share of the notes held, the share of its gap a held note sounds, a
    detached one; None where the line has none of the kind)}, a class the field leaves out ("-") left out; {} where the
    text is not the field's."""
    names = [rhythm.LENGTH_WHOLE] + [name for _, name in rhythm.GAP_CLASSES]
    entries = text.split("/")
    if len(entries) != len(names):
        return {}
    out = {}
    for name, e in zip(names, entries):
        if e == "-":
            continue
        m = re.fullmatch(r"(\d+)~([\d.]+|-)~([\d.]+|-)", e)
        if not m:
            return {}
        out[name] = (int(m.group(1)) / 100, None if m.group(2) == "-" else float(m.group(2)), None if m.group(3) == "-" else float(m.group(3)))
    return out if rhythm.LENGTH_WHOLE in out else {}


def own_lengths(plan, role: str) -> dict | None:
    """How the token song's tune sounds its notes (round 141, Plan.tune_lengths), for the tune's writer; None where the
    token carries none."""
    return (getattr(plan, "tune_lengths", None) or {}).get(role) or None


def own_places(plan, role: str) -> tuple | None:
    """Where in the beat the token song's tune plays (round 147, Plan.tune_places: its share of onsets on a quarter of the
    beat, on a third, finer), as the plan's feel holds them (rhythm.held_places: the third is not held in a triple
    feel), for the tune's and the counter-line's writers; None where the token carries none or the song is written in
    another feel than its token song's."""
    return rhythm.held_places((getattr(plan, "tune_places", None) or {}).get(role) or None, plan.feel, getattr(plan, "token_feel", rhythm.FEELS[0]))


def shortest_beats(plan, role: str) -> float | None:
    """The token song's tune's shortest usual note (round 136, Plan.tune_shortest, in milliseconds) in beats at the plan's
    tempo, for the tune's writer; None where the token carries none."""
    ms = (getattr(plan, "tune_shortest", None) or {}).get(role)
    return ms * plan.bpm / 60000.0 if ms else None


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


BASS_LAYER_KINDS = ("apart", "doubling")   # what the bass writer writes of a second voice: a line of its own, the line again at an interval
                                           # (round 126); a bass whose voices alternate (one of FFVI's fifteen, Fanfare's) keeps the layers draw


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
    the nominal interval (the chord's own third or fifth, major or minor), or semitones from the nominal placing (`+4`;
    round 109: from the line's note itself before, so a backed-off draw at a nominal the word had never seen, Battle
    Theme's synth at a twelfth, put the voice a third under its line) off the chord; `diatonic` without the word (or a song, or a stream), under a note no chord fits, and at a unison or
    octaves (a double: the line exactly). FFVI's parallel voice sits at its nominal semitones on 0.61 of its shared onsets and
    on a chord tone on 0.62, where the line again in the scale matched it on 0.31 and landed on the chord on 0.42: a
    third over the chord's third is a major third or a minor sixth (the root), over the fifth a fourth (the root again)
    or a minor third (the seventh). A chord part's voice with `clash_rates` (the part's clashes draw) holds the share
    as the part's other voices do: an interval a semitone from a part written before the part (rhythm.clash_under)
    while the voice is over its share for the beat is drawn again, VOICE_TRIES times, the last kept. A nominal that one song
    plays draws its chain levels with that song alone behind them (round 110; PLAN_SONGS otherwise). A line note off the
    chord but at the pitch class the written bass sounds under it is drawn as over the chord's root (round 114): a chord
    part riding the bass's pedal (round 106, ride_the_bass) is on the riff's root whatever the chain's chord, where Battle
    Theme's reader hears the riff's pitch as the chord root; drawn as "other", the synth struck with it took the cells where
    the game's synth leaps over the riff's neighbours (+19, +14 over the twelfth) on every pedaled bar."""
    t = (models or {}).get("parallel_intervals")
    steps = int(round(interval * 7 / 12))
    if t is None or song is None or rng is None or steps % 7 == 0:
        return diatonic(notes, interval, scale, voice)
    t = t.table if hasattr(t, "table") else t
    nominal = str(R.generic(interval))
    own = t.songs.get((nominal,), 0) < PLAN_SONGS       # a nominal one song plays is that song's own (round 110): its chain levels, the part
                                                        # and the landing before, stand with one song behind them; Battle Theme alone plays a
                                                        # twelfth, and with the chain passed over its octave-up stabs, a phrase in the game, had
                                                        # come out as single pops drawn apart (Song Check 92)
    hold = bool(clash_rates) and role in rhythm.UPPER
    under = sorted(n for r in rhythm.clash_under(role) for n in song.notes.get(r, [])) if hold else []
    run = {"strong": [0, 0], "weak": [0, 0]}                # the voice's onsets a semitone from a part under it, and its onsets under one
    bass_notes = sorted(song.notes.get(R.BASS, [])) if role in rhythm.UPPER else []   # the written bass, for a line riding its pedal (round 114)
    out, previous, drawn, redrawn, on_pedal = [], rhythm.START, 0, 0, 0
    for n in sorted(notes, key=lambda x: x[0]):
        a, b, m = n[0], n[1], n[2]
        ref = int(round(m))
        c = rhythm._chord_at(song.chords, a)
        if c is None or c.root is None or c.fit < vocab.FIT:
            out += diatonic([n], interval, scale, voice)
            continue
        tone = vocab.tone_of(ref % 12, c.root, c.shape)
        if tone == "other" and any(x[0] - NEAR <= a < x[0] + x[1] and int(round(x[2])) % 12 == ref % 12 for x in bass_notes
                                   if not (isinstance(x[2], float) and math.isnan(x[2]))):
            tone, on_pedal = "root", on_pedal + 1          # the line on the bass's pedal: the riff's root (round 114)
        place = "strong" if abs(a - round(a)) < NEAR else "weak"
        pcs = writer.sounding_pcs(under, a) if under else set()
        over = bool(pcs) and run[place][1] > 0 and run[place][0] / run[place][1] > clash_rates.get(place, 1.0)
        chord_pcs = {(c.root + i) % 12 for i in harmony.SHAPES.get(c.shape, harmony.SHAPES[""])}
        aim = ref + interval                                # the nominal placing: the drawn chord tone sits nearest it
        midi = fallback = landing = None
        for _ in range(writer.VOICE_TRIES):
            pick = t.draw((nominal, tone, role or "?", previous), rng, floored=False, floor_k=PARALLEL_FLOOR, min_songs=1 if own else PLAN_SONGS)
            if pick.startswith(("+", "-")):                # off the chord: the semitones from the line's note
                try:
                    midi = aim + int(pick)                 # from the nominal placing (round 109; from the line's note before)
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
        previous = landing if landing is not None else (vocab.tone_of(midi % 12, c.root, c.shape) if vocab.tone_of(midi % 12, c.root, c.shape) != "other" else f"{midi - aim:+d}")
        drawn += 1
        out.append((a, b, float(midi), voice))
    if log is not None and drawn:
        log.append(f"voice {voice + 1} parallel at {interval:+d} by the parallel_intervals word (round 97): {drawn} notes at the interval the line's tone under the chord draws"
                   + (f"; {on_pedal} of the line's notes on the bass's pedal drawn as over the riff's root (round 114)" if on_pedal else "")
                   + (("; a semitone from a part under it: " + ", ".join(f"{pl} {x[0]}/{x[1]} ({x[0] / x[1]:.2f}; the song's rate {clash_rates[pl]:.2f})" for pl, x in run.items() if x[1])
                       + (f"; {redrawn} draws given up for a clash" if redrawn else "")) if hold and any(x[1] for x in run.values()) else ""))
    return out


RELATION_PARTS = {"m": R.MELODY, "c": R.COUNTER, "a": R.ACCOMP, "h": R.HARMONY, "r": R.ARP, "b": R.BASS}   # the token's relation letters


def relation_word(plan: "Plan", role: str, v: int) -> str | None:
    """The balance token's relation word for a part's voice v beside the line (round 90), None without one."""
    words = plan.layer_relations.get(role) or []
    return words[v - 1] if 0 < v <= len(words) else None


def struck_values_of(text: str) -> dict | None:
    """The balance token's struck sub-field (round 108, arrangement._struck_text) read: "w0.82~0.2~0.3~1.0~0.6~-~4.9~0.53" ->
    {"share": 0.82, "sounds": {gap class: share, or None where the token lacks it}, "longest": 4.9 beats, or None, "sounding":
    0.53 (round 115: the beats the voice sounds over the beats of the bars it strikes in), or None, "cell": 0.72 (round 116: of
    its notes with a note at the same position of the bar before, the share on that note's pitch again), or None}; None where
    it cannot be read."""
    parts = text.split("~")
    n = len(rhythm.GAP_CLASSES)
    if len(parts) not in (2 + n, 3 + n, 4 + n) or not parts[0].startswith("w"):
        return None
    try:
        share, longest = float(parts[0][1:]), float(parts[1 + n])
        sounds = {name: (float(x) if x != "-" else None) for (_, name), x in zip(rhythm.GAP_CLASSES, parts[1:1 + n])}
        sounding = float(parts[2 + n]) if len(parts) >= 3 + n and parts[2 + n] != "-" else None   # the voice's sounding share (round 115)
        cell = float(parts[3 + n]) if len(parts) >= 4 + n and parts[3 + n] != "-" else None       # its cell's repeats (round 116)
    except ValueError:
        return None
    return {"share": share, "sounds": sounds, "longest": longest if longest > 0 else None, "sounding": sounding, "cell": cell}


def step_profile_of(text: str) -> dict | None:
    """The balance token's step profile field (round 117, arrangement.line_step_profile) read: "j63/24/13" -> {"same": 0.63,
    "step": 0.24, "leap": 0.13}; None where it cannot be read."""
    m = re.fullmatch(r"j(\d+)/(\d+)/(\d+)", text or "")
    if not m:
        m = re.fullmatch(r"j(\d+)/(\d+)/(\d+)/(\d+)", text or "")   # a tune's, of four classes (round 130, arrangement.tune_step_profile)
        return {k: int(v) / 100 for k, v in zip(rhythm.TUNE_MOVES, m.groups())} if m else None
    return {k: int(v) / 100 for k, v in zip(rhythm.STEP_CLASSES, m.groups())}


def tone_profile_of(text: str) -> dict | None:
    """The balance token's chord-tone profile field (round 111, arrangement.line_tone_profile) read: "t45/2/9/30/2/12" -> {"root":
    0.45, "third": 0.02, "fifth": 0.09, "seventh": 0.30, "sus": 0.02, "other": 0.12}; None where it cannot be read."""
    m = re.fullmatch(r"t(\d+)/(\d+)/(\d+)/(\d+)/(\d+)/(\d+)", text)
    if not m:
        return None
    return {k: int(x) / 100 for k, x in zip(rhythm.TONE_PROFILE_CLASSES, m.groups())}


def struck_values(plan: "Plan", role: str, v: int) -> dict | None:
    """The token song's struck facts for a part's voice v beside the line (round 108), None without them."""
    xs = plan.layer_struck.get(role) or []
    return xs[v - 1] if 0 < v <= len(xs) else None


def relation_stretches(word: str) -> list:
    """A layer voice's relation word (round 90) as stretches: "ox9>dm-12x14>o" -> [("own", None, None, 9), ("double",
    melody, -12, 14), ("own", None, None, None)]: the kind, the part followed, the semitones, the bars (None: to the end).
    A stretch the writer cannot read is its own."""
    out = []
    for part in word.split(">"):
        body, _, n = part.partition("x")
        bars = int(n) if n.isdigit() else None
        kind = {"d": "double", "p": "parallel", "w": "with"}.get(body[:1])
        target = RELATION_PARTS.get(body[1:2])
        if body[1:2] == "l":                                # the part's own line (round 107)
            target = ("line",)
        elif body[1:2].isdigit():                           # a sibling voice, by its rank among the part's voices beside the line (round 107)
            target = ("voice", int(body[1:2]))
        try:
            semi = int(body[2:])
        except ValueError:
            semi = None
        out.append((kind, target, semi, bars) if kind and target and semi is not None else ("own", None, None, bars))
    return out


STRUCK_TRIES = 6                      # draws of the second_figures mask for a bar whose mask thins nothing while the struck voice is over
STRUCK_MARGIN = 0.05                  # the token song's struck share (round 108), and how far under or over it the running share may sit


def _mask_count(g: str) -> int:
    """The onsets a masked figure keeps."""
    return 0 if g in ("", writer.REST) else len(g.split())


def struck_with(ref: list, at: int, end: int, semi: int, song, role: str, v: int, models: dict, rng: random.Random, clash_rates, sounds, scale: set,
                mask_draw=None, gaps_ref=None, struck=None, stats: dict | None = None, fills: list | None = None) -> tuple:
    """A voice struck with another (round 107): over bars [at, end) the followed voice's onsets (`ref`: (start, end, midi, voice)),
    thinned bar by bar by the second_figures word where `mask_draw` gives a bar's mask (which of the followed voice's onsets
    the voice strikes with), then placed by the parallel_intervals word at the nominal semitones on the chord (`parallel`),
    each note sounding a share of its gap. Since round 108 the token song's struck facts (`struck`: plan.struck_values_of)
    rule both: the mask is held toward the token's share of the followed onsets (under it a bar strikes every followed
    onset, over it a mask that thins nothing is drawn again, STRUCK_TRIES times), a note's gap is to the next onset of the
    part's line (`gaps_ref`, else `ref`), never to the voice's own next stab, its share by gap class is the token voice's
    where the token has the class (else `sounds`), and no note rings past the token voice's longest. Battle Theme's synth
    strikes 0.82 of the guitar riff's onsets, a chord tone an octave and more up, a fifth or a fourth apart in its two
    voices, 0.19 beats long at the median and never past 4.9 beats; measured against its own next stab, the last stab
    before a twelve-bar rest of the part had rung through the rest (Song Check 90's Journey of the Quarry). Since round 115
    the voice's sounding share is the token voice's too (`struck["sounding"]`: the beats it sounds over the beats of the bars
    it strikes in): a stab whose length by its gap class would put the share so far, this stab counted, over the token's by
    STRUCK_MARGIN sounds the token's shortest class share of its gap instead (Battle Theme's synth 0.2: a stab), so a sparse
    line's long gaps no longer turn the stabs into held organ tones (Journey of the Quarry's synth had sounded 0.68 of its
    bars' time at 0.9 beats a note where Battle Theme's sounds 0.53 at 0.19). Since round 116 the voice's cell is the token
    voice's too (`struck["cell"]`): a stab with a stab of the voice's own at the same position of the bar before takes that
    stab's pitch while the share of such stabs so far, this one counted, runs under the token's by STRUCK_MARGIN, and the
    interval word's landing otherwise (Battle Theme's synth hammers C D E F bar after bar, the hook; the written stabs
    changed their pitches every bar, loud and never the same). `stats`, where given, takes the sounded and played beats,
    the stabs shortened, and the cell's repeats and comparable stabs. `fills` (round 118, plan.section_fills): a bar's shift,
    +1 a fill (the voice strikes every followed onset and one between each pair half a beat or more apart, Battle Theme's
    synth's 15 notes into C against its 8 a bar), -1 a thinning (the bar's first onset alone). Returns the notes, the onsets
    thinned away and {bar: the bar's figure}."""
    kept, thinned, figs, filled = [], 0, {}, 0
    struck_n = followed_n = 0                               # the followed onsets struck so far, and seen so far (round 108)
    target = struck["share"] if struck else None
    for k in range(at, min(end, len(song.bars))):
        a, b = song.bars[k]
        in_bar = sorted(x for x in ref if a - rhythm.NEAR <= x[0] < b - rhythm.NEAR)
        if not in_bar:
            continue
        f = rhythm.pattern(rhythm.position(x[0] - a, song.division) for x in in_bar)
        shift = fills[k] if fills and 0 <= k < len(fills) else 0   # a fill or a thinning in this bar (round 118)
        g = rhythm.apply_mask(f, mask_draw(f)) if mask_draw is not None and shift <= 0 else f
        if target is not None and mask_draw is not None and shift <= 0:   # the mask held toward the token song's share (round 108)
            n_g = _mask_count(g)
            if (struck_n + n_g + 1) / (followed_n + len(in_bar) + 1) < target - STRUCK_MARGIN:
                g = f                                       # under the share: the bar strikes every followed onset
            else:
                for _ in range(STRUCK_TRIES):               # over it with a mask that thins nothing: another draw
                    if n_g < len(in_bar) or (struck_n + n_g) / (followed_n + len(in_bar)) <= target + STRUCK_MARGIN:
                        break
                    g = rhythm.apply_mask(f, mask_draw(f))
                    n_g = _mask_count(g)
        followed_n += len(in_bar)
        if g in ("", writer.REST):
            thinned += len(in_bar)
            figs[k] = writer.REST
            continue
        pos = {Fraction(tok.partition(":")[0]) for tok in g.split()}
        chosen = [x for x in in_bar if rhythm.position(x[0] - a, song.division) in pos]
        thinned += len(in_bar) - len(chosen)
        if shift > 0:                                       # a fill (round 118): every followed onset and one between each pair half a beat or more apart
            extra = [(x[0] + (y[0] - x[0]) / 2, x[1], x[2], x[3]) for x, y in zip(chosen, chosen[1:]) if y[0] - x[0] >= 0.5 - rhythm.NEAR]
            chosen = sorted(chosen + extra, key=lambda x: x[0])
            filled += len(extra)
        elif shift < 0 and len(chosen) > 1:                 # a thinning: the bar's first onset alone
            thinned += len(chosen) - 1
            chosen = chosen[:1]
        struck_n += len(chosen)
        kept += chosen
        figs[k] = rhythm.pattern(rhythm.position(x[0] - a, song.division) for x in chosen) if shift else g
    placed = sorted(parallel([(x[0], x[1], x[2], v) for x in kept], semi, scale, v, song, role, models, rng, clash_rates, None), key=lambda x: x[0])
    cell = struck.get("cell") if struck else None           # the token voice's cell repeats (round 116)
    repeats = comparable = 0
    if cell is not None:
        at_pos, held = {}, []
        bar_starts = [x[0] for x in song.bars]
        for a, b, m, vv in placed:
            k = bisect.bisect_right(bar_starts, a + rhythm.NEAR) - 1
            pos = round((a - bar_starts[k]) * 4) / 4 if k >= 0 else None
            before = at_pos.get((k - 1, pos)) if pos is not None else None
            if before is not None:
                if (repeats + 1) / (comparable + 1) < cell - STRUCK_MARGIN:   # under the share, this stab counted: the bar before's pitch here
                    m = before
                comparable += 1
                repeats += int(round(m)) == int(round(before))
            if pos is not None:
                at_pos[(k, pos)] = int(round(m))
            held.append((a, b, m, vv))
        placed = held
    line_on = sorted(x[0] for x in (gaps_ref if gaps_ref is not None else ref))   # the line's onsets: a stab's gap is to the line's next (round 108)
    sounds_w = struck["sounds"] if struck else None
    longest = struck["longest"] if struck else None
    sounding = struck.get("sounding") if struck else None   # the token voice's sounding share (round 115)
    stab = min((x for x in sounds_w.values() if x is not None), default=None) if sounds_w else None   # its shortest class share: a stab
    sounded, bars_seen, shortened = 0.0, set(), 0
    out = []
    for a, b, m, vv in placed:
        j = bisect.bisect_right(line_on, a + rhythm.NEAR)
        gap = (line_on[j] - a) if j < len(line_on) else max(b - a, 0.25)   # after the line's last onset, the followed note's own length
        share = sounds_w.get(rhythm.gap_class(gap)) if sounds_w else None
        length = gap * (share if share is not None else sounded_share(sounds, gap))
        if longest:
            length = min(length, longest)
        if sounding is not None and stab is not None:      # the sounding share held (round 115): over it, this stab counted, a stab's length
            k = bisect.bisect_right([x[0] for x in song.bars], a + rhythm.NEAR) - 1
            beats = sum(song.bars[i][1] - song.bars[i][0] for i in bars_seen | {k})
            if beats > 0 and (sounded + length) / beats > sounding + STRUCK_MARGIN:
                short = min(length, gap * stab)
                shortened += short < length
                length = short
            bars_seen.add(k)
        sounded += length
        out.append((a, a + length, m, vv))
    if stats is not None:
        stats.update(sounded=sounded, played=sum(song.bars[i][1] - song.bars[i][0] for i in bars_seen), shortened=shortened,
                     repeats=repeats, comparable=comparable, filled=filled)
    return out, thinned, figs


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


def late_stretch_notes(plan: "Plan", song, role: str, v: int, own: list, word: str, written: dict, scale: set, models: dict | None,
                       rng: random.Random, struck_too: bool = False) -> list:
    """A voice beside a line by the token's stretches once every line is written (round 90): its stretches on another
    part's line written over those bars (stretched_notes) and the voice folded into where the token song plays its sample
    (fold_voice, round 95). `struck_too` (round 122): the voice is struck with another voice in some parts of the form and
    doubles or runs parallel to a part's line in others (Battle Theme's synths, with the guitar's riff through B and C, on
    the tune in D); its struck stretches were written in place as the game strikes them (round 107) and stand as they are,
    and the stretches on another part's line alone are folded."""
    spans = stretch_spans(relation_stretches(word), len(song.bars))
    got = stretched_notes(v, own, spans, written, scale, song.meter, written[role].log, song=song, role=role, models=models, rng=rng,
                          clash_rates=(plan.extras.get(role) or {}).get("clashes"))
    if not struck_too:
        return fold_voice(plan, role, v, got, song.meter)
    late = [(a, b) for kind, target, _, a, b in spans if kind in ("double", "parallel") and not isinstance(target, tuple)]
    inside = lambda t: any(a * song.meter - rhythm.NEAR <= t < b * song.meter - rhythm.NEAR for a, b in late)   # noqa: E731
    return sorted([n for n in got if not inside(n[0])] + fold_voice(plan, role, v, [n for n in got if inside(n[0])], song.meter), key=lambda n: n[0])


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


def voice_bound_at(plan: "Plan", role: str, v: int, part: bool = True):
    """A bar's register for a voice beside a line (round 95), as a function of the bar: the range the token song plays the
    voice's sample over in that bar's stretch (layer_stretches, where the voice changes instrument by stretch), else the
    token's range for the voice's sample over the song (layer_ranges), else the voice's writing span (plan.bounds["part:v"],
    an apart voice's offset span), else the part's; None where nothing is known. Without `part` the part's range is not
    taken for the voice's (round 120: it is the line's sample's, not the voice's)."""
    sts_all = plan.layer_stretches.get(role) or []
    sts = sts_all[v - 1] if 0 < v <= len(sts_all) else None
    ranges = plan.layer_ranges.get(role) or []
    fallback = tuple(ranges[v - 1]) if 0 < v <= len(ranges) and ranges[v - 1] else None
    if fallback is None:
        fallback = plan.bounds.get(f"{role}:{v}")
    if fallback is None and part:
        fallback = plan.bounds.get(role) or plan.registers.get(role)

    def at(bar: int):
        if sts:
            i = stretch_at(plan, role, bar, v)
            if i is not None and i < len(sts) and sts[i][1]:
                return tuple(sts[i][1])
        return tuple(fallback) if fallback else None
    return at


def fold_voice(plan: "Plan", role: str, v: int, notes: list, meter: int, at=None, why: str = "into where the game plays its sample (round 95)") -> list:
    """A voice beside a line, written by its relation word, folded by octaves into where the token song plays its sample
    (voice_bound_at), as fold_line folds a line: each bar first as a whole, the octave count that puts most of its notes
    inside (a tie keeps the bar before's count, else the smaller move), then the leftovers one by one. Round 95: a relation
    voice had been written at its word's semitones from the line wherever the written line sat, and Umaro's accompaniment
    voice, two octaves over a tune the game has low in those bars, reached midi 112 where the game plays its sample at 72-88,
    a beep two octaves above the song (45 % of relation-voice notes sat outside their sample's played range over sixty
    seeds). Notes (start, end, midi, voice); only voice v's are touched. `at`: another bound a bar (hold_under_ceilings,
    round 120), `why` its words for the log."""
    at = at or voice_bound_at(plan, role, v)
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
        plan.log.append(f"{role}'s voice {v + 1}: {shifted} notes moved by octaves" + (f", {moved} folded one by one" if moved else "") + " " + why)
    return out


CEILING_SLACK = 0.05                  # semitones a note may sit over its sample's ceiling on the SNES chip and still sound its pitch (round 119)


def sample_slot(slots, role: str, voice: int, second: bool, stretch: int | None = None) -> str:
    """The slot of samples_for's choices a part's voice plays from: its stretch's where the token song changes instrument
    there (`role:stretch:i` the line's, round 91; `role:v:stretch:i` a voice beside it, round 92), else the token song's
    own for that voice (`role:v`, round 70), else the part's second sample for a voice beside the line that is no doubling
    (`second`), else the line's. One order for the sample a note plays (render.sample_of) and for the ceiling the SNES
    chip sets on it (voice_ceiling_at)."""
    if stretch is not None:
        key = f"{role}:stretch:{stretch}" if not voice else f"{role}:{voice}:stretch:{stretch}"
        if key in slots:
            return key
    if voice and slots.get(f"{role}:{voice}") is not None:
        return f"{role}:{voice}"
    if second and f"{role}:second" in slots:
        return f"{role}:second"
    return role


def voice_ceiling_at(plan: "Plan", role: str, v: int):
    """A bar's ceiling for a part's voice (round 120), as a function of the bar: the highest note the SNES chip can play of
    the sample the voice plays there (plan.ceilings, set by samples_for; the slot by sample_slot, as the render chooses the
    sample), None where the plan holds none (a plan no samples were chosen for)."""
    layers = layers_of(plan, role)
    second = 0 < v <= len(layers) and not layers[v - 1].startswith("doubling")
    return lambda bar: plan.ceilings.get(sample_slot(plan.ceilings, role, v, second, stretch_at(plan, role, bar, v)))


def hold_under_ceilings(plan: "Plan", song: rhythm.Song, written: dict) -> None:
    """No voice plays over what the SNES chip can play of its sample, on the notes as finally written (round 120). The
    chip's pitch register stops at four times a recording's rate, so a sample sounds no higher than two octaves over the
    note it plays at 32 kHz (score.pitch_ceiling) and a note written higher sounds at that ceiling whatever its pitch
    class. The lines are written where the game plays their samples and round 95 folds a voice written after the lines by
    its relation word (fold_voice), but a voice beside a line written by its layer word alone (a doubling at its
    interval, a pedal at its offset) and one struck with another voice (round 107) are placed from the line and never
    folded: The Wandering Bazaar's third accompaniment voice doubled its line a twelfth up to midi 121 on a sample the
    chip stops at 87, and sounded that one pitch on 764 notes. Here a voice that holds a note over its ceiling is folded
    whole, as round 95 folds: into where the token song plays its sample (voice_bound_at without the part's range: the
    voice's stretches, its range, its writing span), cut at the ceiling; where the plan knows no range for the voice, into
    the span it was written over, cut at the ceiling; a line into its own bound. A voice with no note over its ceiling is
    left exactly as written."""
    meter = song.meter
    for role, part in written.items():
        if role == R.DRUMS:
            continue
        for v in sorted({n[3] for n in part.notes if len(n) > 3}):
            top = voice_ceiling_at(plan, role, v)
            mine = [n for n in part.notes if len(n) > 3 and n[3] == v]
            over = [n for n in mine if top(int(n[0] // meter)) is not None and n[2] - top(int(n[0] // meter)) > CEILING_SLACK]
            if not over:
                continue
            if v:
                known = voice_bound_at(plan, role, v, part=False)
            else:
                line_at = line_bounds_at(plan, role)
                whole = plan.bounds.get(role) or plan.registers.get(role)
                known = lambda bar, line_at=line_at, whole=whole: (line_at(bar) if line_at else None) or whole   # noqa: E731
            floor = int(math.floor(min(n[2] for n in mine)))

            def at(bar, top=top, known=known, floor=floor):
                ceiling, bound = top(bar), known(bar)
                low, high = bound if bound else (floor, max(int(math.ceil(n[2])) for n in mine))
                if ceiling is not None:
                    high = min(high, int(math.floor(ceiling + CEILING_SLACK)))
                return (low if low <= high else high - 11, high)   # a range wholly over the ceiling: the octave under it
            was = list(part.notes)
            part.notes[:] = fold_voice(plan, role, v, part.notes, meter, at=at,
                                       why=f"under what the SNES chip can play of its sample (round 120): {len(over)} of its {len(mine)} notes sat over "
                                           f"it, no higher than {int(math.floor(min(top(int(n[0] // meter)) for n in over) + CEILING_SLACK))}")
            moved = Counter((round(a[0], 3), int(round(a[2]))) for a, b in zip(was, part.notes) if a[2] != b[2])
            to = {}
            for a, b in zip(was, part.notes):
                if a[2] != b[2]:
                    to.setdefault((round(a[0], 3), int(round(a[2]))), []).append(b[2])
            sung = []
            for y in song.notes.get(role, []):              # the song's own copy of the part, a note for a note
                key = (round(y[0], 3), int(round(y[2])))
                if moved.get(key):
                    moved[key] -= 1
                    y = (y[0], y[1], float(to[key].pop(0)), *y[3:])
                sung.append(y)
            song.notes[role] = sung


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


def ride_the_bass(plan: "Plan", song: rhythm.Song, role: str, notes: list, figures: list, voicings: list, shared: dict | None,
                  register: tuple, rides: tuple, bass: list, rng: random.Random, word: str | None = None) -> tuple:
    """A chord part's line on the bass's figure (round 106). The token's rides field gives the share of the line's onsets
    struck with the bass and the share of those at the bass's pitch class; their product (Battle Theme 0.75 x 0.70: the
    half of the riff that is the bass an octave up) is the share of the form's parts that ride, each new part drawn on
    an own stream, a repeated part as its source. In a riding bar the line plays the written bass's notes (`bass`: its
    line voice, (start, end, midi, voice)), each in the line's register of the bar (in_register, the house fold) on the
    bass's lengths; the bar's figure is the bass's onsets, and the voices beside the line see the riding notes
    (`shared`). A part of the form where the line or the bass rests throughout draws nothing (two of Battle Theme's seven
    token seeds had drawn their riding part where the accompaniment or the bass sat out). `word` (round 123): the token
    song's line by stretch (extras[part]["company"], arrangement.line_company_field: "db+12x2>ox8>db+12x9>ox8>pb+12"); the
    line then rides in the bars of the word's stretches on the bass and nowhere else, no part drawn, and plays the bass's
    notes at the stretch's semitones, moved by octaves only where that leaves where the token song plays the line's sample
    (the stretch's range, else the sample's). Battle Theme's guitar is its bass an octave up through A, C and D and its
    own riff through B; drawn by the share, the written guitar rode in other parts than the song's, and folded into its
    register it sat at the bass's own pitch on a quarter to a third of the onsets they shared and an octave over it on a
    sixth (the game: an octave over on 0.66). Returns the notes, figures, voicings and a log line."""
    c, s = rides
    share = c * s
    plays = plan.plays.get(role) or []
    bass_bars = {k for k, (a, b) in enumerate(song.bars) if any(a - rhythm.NEAR <= x[0] < b - rhythm.NEAR for x in bass)}
    decided, riding, semi_at = {}, set(), {}
    if word:                                                # the token song's line by stretch (round 123)
        for kind, target, semi, a, b in stretch_spans(relation_stretches(word), len(song.bars)):
            if kind in ("double", "parallel") and target == R.BASS:
                semi_at.update({k: semi for k in range(a, b)})
        riding = set(semi_at)
    else:
        for i, (bar, n, of, label) in enumerate(plan.parts):
            if of is not None:
                decided[i] = decided.get(of, False)
            else:                                           # a part where the line or the bass rests throughout is no riff's: no draw for it
                both = any(k < len(plays) and plays[k] and k in bass_bars for k in range(bar, bar + n))
                decided[i] = both and rng.random() < share
            if decided[i]:
                riding.update(range(bar, bar + n))
    bounds_at = line_bounds_at(plan, role)
    new_notes = list(notes)
    done = 0
    for k in sorted(riding):
        if k >= len(plays) or not plays[k] or k >= len(song.bars) or k >= len(figures):
            continue
        a, b = song.bars[k]
        in_bar = [x for x in bass if a - rhythm.NEAR <= x[0] < b - rhythm.NEAR]
        if not in_bar:
            continue
        reg = (bounds_at(k) if bounds_at else None) or register
        if word:                                            # the bass at the word's semitones, inside where the game plays the line's sample
            room = (bounds_at(k) if bounds_at else None) or (getattr(plan, "sample_ranges", None) or {}).get(role) or register
            copied = [(x[0], x[1], float(m if room[0] <= m <= room[1] else line_in_register(int(round(m)), room)), 0) for x in in_bar for m in (x[2] + semi_at[k],)]
        else:
            copied = [(x[0], x[1], float(line_in_register(int(round(x[2])), reg)), 0) for x in in_bar]
        new_notes = [x for x in new_notes if not (a - rhythm.NEAR <= x[0] < b - rhythm.NEAR)] + copied
        figures[k] = rhythm.pattern(rhythm.position(x[0] - a, song.division) for x in in_bar)
        voicings[k] = "rides the bass"
        if shared is not None:
            for key_ in [key_ for key_ in shared if isinstance(key_, tuple) and len(key_) == 2 and isinstance(key_[1], tuple) and key_[1][0] == k]:
                del shared[key_]
            for st, en, m, v in copied:
                pos = rhythm.position(st - a, song.division)
                shared[("line", (k, pos))] = m
                shared[("taken", (k, pos))] = {m}
        done += 1
    new_notes.sort(key=lambda x: x[0])
    if word:
        return new_notes, figures, voicings, [f"{role}'s line doubles the bass in {done} bars, at the semitones of the balance's song's line by stretch ({word}; round 123)"]
    parts_ = [plan.parts[i][3] for i in sorted(decided) if decided[i]]
    return new_notes, figures, voicings, [f"{role}'s line rides the bass in {done} bars (parts {' '.join(parts_) if parts_ else 'none'}: the balance's song "
                                           f"{c:.2f} of its onsets with the bass, {s:.2f} at its pitch class, so {share:.2f} of the parts drawn)"]


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
    token_motions, token_tone_tiers = {}, {}                # a chord part's line motion and off-chord tier (round 103): the song's own
    token_profiles = {}                                     # a backing line's chord-tone profile (round 111)
    token_steps = {}                                        # a backing line's step profile (round 117)
    token_shapes = None                                     # the token song's chord-shape profile (round 112)
    token_quals = {}                                        # the qualities each degree has in the token song (round 127)
    token_form = None                                       # the token song's form letters (round 113)
    token_continuity = None                                 # the token song's bass line pitch continuity (round 114)
    token_downbeat = None                                   # how often the token song's bass roots a bar's first beat (round 129)
    token_first = {}                                        # and how often it strikes it (round 133), and a chord part (round 135)
    token_shortest = {}                                     # a tune's shortest usual note in the token song, in milliseconds (round 136)
    token_lengths = {}                                      # and how it sounds its notes, by the gap to the next (round 141)
    token_tones = {}                                        # how often a chord part sounds a chord's tones again in the token song (round 142)
    token_together = {}                                     # and how often a part comes back with its lead (round 144)
    token_tune_together = {}                                # the tune's with the bass, and how often its bars come back at all (round 146)
    token_places = {}                                       # where in the beat a tune's notes fall in the token song (round 147)
    token_with_kit = {}                                     # how often the bass's and the tune's notes are struck with the kit there (round 149)
    token_section_levels = {}                               # a part's level in each part of the token song's form, by its letters (round 150)
    token_loops = {}                                        # each voice's loops by the form's letters, the harmony's among them (round 121)
    token_spans = {}                                        # the parts of the form each part sounds in, with its entrances (round 124)
    token_onsets, token_kit_onsets, token_layer_onsets = {}, {}, {}   # each line's onsets a bar by the form's letters, the kit's pieces', each
                                                            # voice beside a line's (round 125)
    token_layer_words = {}                                  # the bass's voices beside its line: what each does, the layers word's outcome (round 126)
    token_line_company = {}                                 # where a chord part's line doubles the bass or runs parallel to it, by stretch (round 123)
    token_periods, token_rides, token_holds = {}, {}, None   # a backing part's own period and holds, how far a chord part's line rides the
                                                            # bass, the song's chord-hold share (round 106): the riff as the song's own
    token_layer_stretches = {}                              # each voice beyond a line's instrument by stretch (round 92)
    token_layer_struck = {}                                 # how each voice struck with another strikes (round 108)
    token_gap_shares = {}                                   # a chord part's or the bass's line: the share a note sounds by its gap class (round 95)
    token_kit_channels = []                                # the kit's channels, each one's pieces (round 87)
    token_class, token_top, token_loud = None, None, None
    token_tempo = None                                      # the token's song's own tempo, where the token carries it (round 137)
    token_beat = 1                                          # 2 where the token's song is counted in double time (round 131)
    token_feel = rhythm.FEELS[0]                            # the token's song's feel (round 147): duple where the token does not say
    token_loop = None                                       # the part of its form the token's song's loop returns to (round 132)
    for token in _draw(models, "balance", (rhythm.ARRANGEMENT,), rng, log).split():
        role, _, rest = token.partition("=")
        if role == "loop":                                  # the part of its form the token's song's loop returns to (round 132), not a part
            token_loop = int(rest) if rest.isdigit() else None
            continue
        if role == "beat":                                  # the token's song is counted in double time (round 131), not a part
            token_beat = int(rest) if rest.isdigit() and int(rest) > 0 else 1
            continue
        if role == "feel":                                  # the token's song's feel (round 147), not a part
            token_feel = rest if rest in rhythm.FEELS else rhythm.FEELS[0]
            continue
        if role == "tempo":                                 # the token's song's tempo class (round 54) and its own tempo (round 137:
            token_class, _, own = rest.partition(":")       # `fast:140`), not a part
            token_tempo = float(own) if own.replace(".", "", 1).isdigit() and float(own) > 0 else None
            continue
        if role == "top":                                   # the token's song's loudest part, of full (round 59), not a part
            token_top = float(rest)
            continue
        if role == "holds":                                 # the token's song's chord-hold share (round 106), not a part
            token_holds = float(rest)
            continue
        if role == "form":                                  # the token's song's form (round 113), not a part
            token_form = form_of(rest)
            if token_form:
                log.append("the balance's song's form: " + " ".join(f"{l}{n}" for l, n in token_form))
            continue
        if role == "cycle":                                 # the token's song's harmony's loops (round 121), not a part
            got = loops_of(rest)
            if got:
                token_loops[LOOP_CHORDS] = got
            continue
        if role == "quals":                                 # the qualities each degree has in the token's song (round 127), not a part
            token_quals = quals_of(rest)
            continue
        if role == "shapes":                                # the token's song's chord shapes (round 112), not a part
            token_shapes = shape_profile_of(rest)
            if token_shapes:
                log.append("the balance's song's chord shapes: " + " ".join(f"{sh or 'maj'} {v:.2f}" for sh, v in token_shapes.items()))
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
                if any(len(x) > 6 and x[6] for x in parts_):   # and how a voice struck with another strikes (round 108): its share of the
                    token_layer_struck[role] = [struck_values_of(x[6]) if len(x) > 6 and x[6] else None for x in parts_]   # followed onsets, its
                for i, x in enumerate(parts_, start=1):     # and each one's loops by the form's letters (round 121): "lB1~75!3.7"
                    if len(x) > 7 and x[7].startswith("l") and loops_of(x[7][1:]):
                        token_loops[f"{role}:{i}"] = loops_of(x[7][1:])
                    if len(x) > 8 and x[8].startswith("n") and onsets_of(x[8][1:]):   # and its onsets a bar by them (round 125)
                        token_layer_onsets.setdefault(role, {})[i] = onsets_of(x[8][1:])
                    if len(x) > 9 and x[9].startswith("v") and layer_of({"layer": x[9][1:].replace("_", " ")})[0] in BASS_LAYER_KINDS:   # and what a
                        token_layer_words.setdefault(role, {})[i] = x[9][1:].replace("_", " ")   # bass's voice does beside the line (round 126)
                                                                                                                        # lengths by the line's gap, its longest
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
            if len(fields) > 11 and fields[11]:             # the line's motion (round 103): block, mixed or arpeggiated, the token song's own
                token_motions[role] = fields[11]
            if len(fields) > 12 and fields[12]:             # the line's off-chord tier (round 103): rare, some or many, the token song's own
                token_tone_tiers[role] = fields[12]
            if len(fields) > 13 and fields[13]:             # the part's own period and hold share (round 106): `p2/83`
                m_ = re.fullmatch(r"p(\d+)/(\d+)", fields[13])
                if m_:
                    token_periods[role] = (int(m_.group(1)), int(m_.group(2)) / 100)
            if len(fields) > 14 and fields[14]:             # how far the line rides the bass (round 106): `b75/70`, onsets with it / at its pitch class
                m_ = re.fullmatch(r"b(\d+)/(\d+)", fields[14])
                if m_:
                    token_rides[role] = (int(m_.group(1)) / 100, int(m_.group(2)) / 100)
            if len(fields) > 16 and fields[16] and role == R.BASS:   # the bass line's pitch continuity (round 114): `k58`
                m_ = re.fullmatch(r"k(\d+)", fields[16])
                if m_:
                    token_continuity = int(m_.group(1)) / 100
                    log.append(f"the bass keeps its pitch class across {token_continuity:.2f} of its bar lines in the balance's song")
            if len(fields) > 15 and fields[15]:             # the line's chord-tone profile (round 111): `t45/2/9/30/2/12`
                prof = tone_profile_of(fields[15])
                if prof:
                    token_profiles[role] = prof
                    log.append(f"{role}'s line plays the balance's song's chord tones: " + " ".join(f"{k} {v:.2f}" for k, v in prof.items()))
            if len(fields) > 17 and fields[17]:             # the line's step profile (round 117): `j63/24/13`
                steps = step_profile_of(fields[17])
                if steps:
                    token_steps[role] = steps
                    log.append(f"{role}'s line moves as the balance's song's: " + " ".join(f"{k} {v:.2f}" for k, v in steps.items()))
            if len(fields) > 18 and fields[18].startswith("l") and loops_of(fields[18][1:]):   # the line's loops, the kit's (round 121): `lB1~100`
                token_loops[role] = loops_of(fields[18][1:])
            if len(fields) > 19 and fields[19].startswith("r") and any(st[0] != "own" for st in relation_stretches(fields[19][1:])):   # where the line
                token_line_company[role] = fields[19][1:]   # doubles the bass, by stretch (round 123): `rdb+12x2>ox8>db+12`
            if len(fields) > 20 and fields[20].startswith("e") and spans_of(fields[20][1:]):   # the parts of the form the part sounds
                token_spans[role] = spans_of(fields[20][1:])   # in, with its entrances (round 124): `eA+B2.0+D0.4`
            if len(fields) > 22 and role == R.BASS and re.fullmatch(r"d\d+", fields[22]):   # how often the bass strikes a bar's first beat on the
                token_downbeat = int(fields[22][1:]) / 100   # chord's root (round 129): `d73`
                log.append(f"the bass strikes a bar's first beat on the chord's root in {token_downbeat:.2f} of its bars in the balance's song")
            if len(fields) > 23 and role in rhythm.UPPER + (R.BASS,) and re.fullmatch(r"f\d+", fields[23]):   # how often the part strikes a
                token_first[role] = int(fields[23][1:]) / 100   # bar's first beat: the bass (round 133), a chord part (round 135): `f93`
                log.append(f"the {role} strikes a bar's first beat in {token_first[role]:.2f} of its bars in the balance's song")
            if len(fields) > 24 and role in (R.MELODY, R.COUNTER) and re.fullmatch(r"m\d+", fields[24]) and int(fields[24][1:]) > 0:   # a tune's
                token_shortest[role] = int(fields[24][1:])  # shortest usual note (round 136): `m150`
                log.append(f"the {role}'s shortest usual note sounds {token_shortest[role]} ms in the balance's song")
            if len(fields) > 25 and role in (R.MELODY, R.COUNTER) and fields[25].startswith("h") and lengths_of(fields[25][1:]):   # how the tune
                token_lengths[role] = lengths_of(fields[25][1:])   # sounds its notes, by the gap (round 141): `h50~0.90~0.40/-/26~0.90~0.55/...`
                log.append(f"the {role} holds {token_lengths[role][rhythm.LENGTH_WHOLE][0]:.2f} of its notes in the balance's song; its note lengths by the gap (round 141): {fields[25][1:]}")
            if len(fields) > 26 and role in rhythm.UPPER and re.fullmatch(r"c\d+/\d+", fields[26]):   # how often a chord part sounds again
                token_tones[role] = tuple(int(x) / 100 for x in fields[26][1:].split("/"))   # the pitch classes it played on a chord before, and
                log.append(f"the {role} sounds an earlier bar's pitch classes on a chord again in {token_tones[role][0]:.2f} of such bars in the balance's song, "   # how often the bar before's
                           f"the bar before's in {token_tones[role][1]:.2f} of those (round 142)")   # (round 142): `c60/47`
            if len(fields) > 27 and role in rhythm.UPPER + (R.COUNTER,) and re.fullmatch(r"w\d+", fields[27]):   # how often it plays an earlier bar
                token_together[role] = int(fields[27][1:]) / 100   # again where its lead does (round 144): `w66`
                log.append(f"the {role} plays an earlier bar again where the {'tune' if role == R.COUNTER else 'bass'} does in {token_together[role]:.2f} of such bars in the balance's song (round 144)")
            if len(fields) > 27 and role in (R.MELODY, R.COUNTER) and re.fullmatch(r"w(\d+|-)/(\d+|-)/\d+", fields[27]):   # the tune: how often it
                token_tune_together[role] = tuple(None if x == "-" else int(x) / 100 for x in fields[27][1:].split("/"))   # plays an earlier bar again
                far, near, overall = token_tune_together[role]   # where the bass brings one back from further off, where it stands on the bar before,
                said = lambda x: "by no count (under four such bars)" if x is None else f"in {x:.2f} of such bars"   # noqa: E731    # and how often
                log.append(f"the {role} plays an earlier bar again where the bass plays one from further back again {said(far)} in the balance's song, "   # at all (round
                           f"where it plays the bar before again {said(near)}, and an earlier bar again in {overall:.2f} of its bars (round 146)")   # 146): `w48/-/29`
            if len(fields) > 28 and role in (R.MELODY, R.COUNTER) and re.fullmatch(r"p\d+/\d+/\d+", fields[28]):   # where in the beat a tune's
                token_places[role] = tuple(int(x) / 100 for x in fields[28][1:].split("/"))   # notes fall (round 147): `p12/0/3`
                log.append(f"the {role} plays {token_places[role][0]:.2f} of its notes on a quarter of the beat in the balance's song, {token_places[role][1]:.2f} on a third, "
                           f"{token_places[role][2]:.2f} finer (round 147)")
            if len(fields) > 29 and re.fullmatch(r"x\d+/\d+" if role == R.BASS else r"x\d+", fields[29]) and role in rhythm.KIT_PARTS:   # how often its
                token_with_kit[role] = tuple(int(x) / 100 for x in fields[29][1:].split("/"))   # notes are struck with the kit (round 149): `x100/84`, `x91`
                log.append(f"the {role} strikes {token_with_kit[role][0]:.2f} of its notes with a kit hit in the balance's song"
                           + (f", and {token_with_kit[role][1]:.2f} of the kit's hits carry a bass note" if role == R.BASS else "") + " (round 149)")
            if len(fields) > 30 and role != R.DRUMS and section_levels_of(fields[30]):   # its level in each part of the form over its level in
                token_section_levels[role] = section_levels_of(fields[30])   # the song (round 150): `vA1.0+B0.4`
            if len(fields) > 21 and fields[21].startswith("n"):   # how busy it is in each (round 125): the line's onsets a bar `nA6+B2!1`,
                if role == R.DRUMS:                         # the kit's pieces' hits a bar `nAS28.5@100,c1@50`
                    token_kit_onsets = kit_onsets_of(fields[21][1:])
                elif onsets_of(fields[21][1:]):
                    token_onsets[role] = onsets_of(fields[21][1:])
    log.append("band " + " ".join(f"{r}={weights[r]}" + (f" {layout[r][0]}-{layout[r][1]}" if r in layout else "") + (f" x{counts[r]}" if r in counts else "")
                                  if r in weights else r for r in band))
    if token_form and [(p[3], p[1]) for p in parts] != token_form:   # the token song's form (round 113): its letters and their bars, after the
        drawn_form = " ".join(f"{p[3]}{p[1]}" for p in parts)   # balance is read (the form's own draw above stands, so no other draw moves); a
        form_log = []                                           # form past the bars asked is cut as any; the loop's part drawn again for it
        own_max = max_bars if max_bars is None or token_beat == 1 else max_bars * token_beat   # a song counted in double time has twice the
        if own_max != max_bars:                                 # bars for the same music (round 131): its form's bound doubles with them
            log.append(f"the balance's song is counted in double time: its form may run to {own_max} bars")
        taken = plan_form(models, random.Random(f"whole:{seed}:form"), form_log, own_max, form=token_form)
        taken_bars = taken[-1][0] + taken[-1][1]
        if min_bars is not None and taken_bars < min_bars:     # a token form short of the bars asked (4 of FFVI's 62): the draw stands
            log.append(f"the balance's song's form {''.join(f'{l}{n}' for l, n in token_form)} is {taken_bars} bars, short of the {min_bars} asked: "
                       f"the draw {drawn_form} stands")
        else:
            parts = taken
            log += form_log[-1:] + ["form from the balance's song: " + " ".join(f"{p[3]}{p[1]}" for p in parts) + f" (the draw {drawn_form})"]
            loop_bar = plan_loop(models, parts, random.Random(f"whole:{seed}:loop part"), log)
    own_form = bool(token_form) and [p[3] for p in parts] == [l for l, _ in token_form][:len(parts)]   # the form's letters are the token song's
    own_loop = parts[token_loop][0] if own_form and token_loop is not None and token_loop < len(parts) else None   # the token song's loop's part (round 132)
    loops = {}                                              # the loops (round 121): the token song's, where the form's letters are its own
    if token_loops and own_form:
        loops = token_loops
        said = lambda spec: ", ".join(f"{l} {'every bar' if lag == 1 else f'every {lag} bars'} on {share:.2f}"   # noqa: E731
                                      + (" but bar" + ("s " if len(off) > 1 else " ") + " ".join(str(j + 1) for j in off) if off else "")
                                      for l, (lag, share, off) in spec.items())
        log.append("loops from the balance's song (round 121): " + "; ".join(
            ("the harmony" if key == LOOP_CHORDS else "the kit" if key == R.DRUMS else f"{key.partition(':')[0]}'s voice {int(key.partition(':')[2]) + 1}" if ":" in key else f"{key}'s line")
            + " " + said(spec) for key, spec in loops.items()))
    elif token_loops:
        log.append("loops from the balance's song (round 121): none taken, the form is not its own")
    if token_class and rhythm.band(bpm) != token_class:     # the band's own pace (round 54): the tempo drawn again under the token's class, on
        was = bpm                                           # an own stream so no other draw moves
        bpm = float(_draw(models, "tempos", ("song", token_class), random.Random(f"whole:{seed}:tempo"), log, floor_k=2))   # terminal at the
        # class (round 75): without the floor the draw gave the class's own votes their Witten-Bell share and backed off to every
        # class's tempos for the rest, and 8 of 46 written songs sat in another class than their token's, their kits drawn there
        if rhythm.band(bpm) != token_class:                 # the word's rounding to five put the tempo on the next class's first value
            bpm = rhythm.within_band(bpm, token_class)      # (85 under slow, 130 under medium): the class's edge, inside
        tempo = rhythm.band(bpm)
        log.append(f"tempo {was:.0f} BPM is outside the band's class ({token_class}): {bpm:.0f} BPM drawn under it")
    if token_tempo and not (1 - TEMPO_NEAR) * token_tempo <= bpm <= (1 + TEMPO_NEAR) * token_tempo:   # the band's own pace nearer (round
        was = bpm                                           # 137): within a tenth of the token song's tempo, one of its class's tempos
        bpm = tempo_near(models, token_class, token_tempo, random.Random(f"whole:{seed}:tempo near"))   # on an own stream, the draws
        tempo = rhythm.band(bpm)                            # above standing as draws, so no other draw moves
        log.append(f"tempo {was:.0f} BPM is not within a tenth of the balance's song's {token_tempo:.0f}: {bpm:.0f} BPM drawn near it")
    names, chords = plan_chords(models, parts, loop_bar, tonic, mode, rng, log,
                                hold_share=token_holds, hold_rng=random.Random(f"{seed}:chords:holds"),   # held as the token's song holds (round 106)
                                shape_profile=token_shapes,                                        # its qualities the token's song's (round 112)
                                degree_shapes=token_quals,                                         # each on the degree the song has it on (round 127)
                                cycle=loops.get(LOOP_CHORDS))                                      # its harmony's loops (round 121)
    if own_loop is not None and own_loop != loop_bar:       # the loop returns to the token song's own part of the form (round 132), once the
        log.append(f"loop from the balance's song: back to part {token_loop + 1} of {len(parts)}, bar {own_loop + 1} "   # chords are drawn: the
                   f"(the loop_parts draw: bar {loop_bar + 1})")   # loop_parts draw and the chain's draw at its bar stand, so no other draw moves
        loop_bar = own_loop
    drum_habit = (token_habits.get(R.DRUMS) or _draw(models, "drum_habits", (R.DRUMS,), random.Random(f"whole:{seed}:drum-habit"), log)) if R.DRUMS in band else None   # before the
    tier = str(drum_habit).split()[0] if drum_habit else rhythm.NO_TIER   # textures, on an own stream: the kit's tier conditions them (round 59)
    own_textures = bool(token_spans) and own_form           # the token song's own textures and entrances (round 124), where the form's letters
    textures, plays = plan_texture(models, parts, band, rng, [] if own_textures else log, defer=(R.DRUMS,), tier=tier)   # are its own: the pooled
    if own_textures:                                        # draw is made all the same (its lines unsaid), so no other draw moves
        textures, plays = token_textures(parts, band, token_spans, log)
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
            if role in token_line_company:                  # where the line doubles the bass, by stretch (round 123): the token song's own
                extras[role]["company"] = token_line_company[role]
                log.append(f"{role}'s line doubles the bass where the balance's song's does (round 123): {token_line_company[role]}")
            if role in token_rides:                         # how far the line rides the bass (round 106): the token song's own
                extras[role]["rides"] = token_rides[role]
                log.append(f"{role}'s line rides the bass from the balance: {token_rides[role][0]:.2f} of its onsets with the bass, "
                           f"{token_rides[role][1]:.2f} of those at its pitch class")
            if role in token_motions:                       # the token song's own line motion (round 103); the draw made all the same, so the streams stand
                extras[role]["motion_drawn"] = extras[role]["motion"]
                extras[role]["motion"] = token_motions[role]
                log.append(f"{role}'s line motion from the balance: {token_motions[role]} (the draw {extras[role]['motion_drawn']}); its voices beside the line keep the draw")
            if role in token_tone_tiers and extras[role].get("tone_tier") is not None:   # and its off-chord tier (round 103)
                extras[role]["tone_tier_drawn"] = extras[role]["tone_tier"]
                extras[role]["tone_tier"] = token_tone_tiers[role]
                log.append(f"{role}'s off-chord tier from the balance: {token_tone_tiers[role]} (the draw {extras[role]['tone_tier_drawn']})")
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
    if R.DRUMS in band and "part_entries" in render_mod.models_or_empty(models) and not own_textures:   # the drums' entrances under the kit's tier (round 59), on an own stream; the token song's own stand (round 124)
        textures, plays = drum_entrances(models, parts, textures, band, str(habits[R.DRUMS]).split()[0], random.Random(f"whole:{seed}:entries"), log)
    section_levels = (plan_section_levels(models, parts, band, plays, random.Random(f"whole:{seed}:levels"), log)   # an own stream: drawn on the
                      if "section_levels" in render_mod.models_or_empty(models) else {})                                  # plan's, every later draw had shifted
    if section_levels and tokens_say_levels(models.get("balance")):   # each part's level by section as its token song's part's (round 150): the
        section_levels = own_section_levels(section_levels, token_section_levels, parts, plays, own_form, log)   # pooled draws above are made all the same
    voices = allot(band, counts, len(token_kit_channels) or 2)   # the kit on its song's channels (round 87), two without the field
    own_density = own_form and bool(token_onsets or token_kit_onsets)   # how busy each part is in each part of the form: the token song's own
    section_onsets, kit_bounds = {}, []                     # (round 125), where the form's letters are its own
    if own_density:
        section_onsets, kit_bounds, section_densities, section_fills = token_sections(parts, band, plays, voices, token_onsets, token_kit_onsets, token_layer_onsets, log)
    else:
        section_densities = (plan_section_densities(models, parts, band, plays, section_levels, random.Random(f"whole:{seed}:section densities"), log)
                             if "section_densities" in render_mod.models_or_empty(models) else {})   # a section's density tier by the step its level makes (round 101)
        section_fills = (plan_section_fills(models, parts, band, plays, voices, random.Random(f"whole:{seed}:section fills"), log)   # what each voice does in a
                         if "section_fills" in render_mod.models_or_empty(models) else {})                                        # section's last bar (round 118)
    for role, kinds in section_fills.items():               # the line's fill rides the density shift its writer reads (habit_at_for, envelope_at_for)
        if any(kinds["line"]):
            shifts = section_densities.setdefault(role, [0] * len(kinds["line"]))
            for k, x in enumerate(kinds["line"]):
                if x and k < len(shifts):
                    shifts[k] = max(-1, min(2, shifts[k] + x))
    for role in band:                                       # a part with two voices or more: what each voice beside its line does (the layers table)
        if role != R.DRUMS and voices.get(role, 1) >= 2:
            layers = [_draw(models, "layers", (role, str(min(rank, 4))), rng, log) if "layers" in models else "apart +0 like"
                      for rank in range(2, voices[role] + 1)]
            for i, word in sorted((token_layer_words.get(role) or {}).items()):   # the bass's voices as the token song's own (round 126): the draw
                if 1 <= i <= len(layers) and layers[i - 1] != word:               # above is made all the same, so no other draw moves
                    log.append(f"{role}'s voice {i + 1} beside the line from the balance (round 126): {word} (the draw {layers[i - 1]})")
                    layers[i - 1] = word
            extras.setdefault(role, {})["layers"] = layers
            extras[role]["layer"] = layers[0]
    feel = _draw(models, "feels", ("song",), rng, log) if "feels" in models else "duple"
    if tokens_say_feel(models.get("balance")) and feel != token_feel:   # the song is written in its token song's feel (round 148): the pooled
        log.append(f"the song's feel from the balance (round 148): {token_feel} (the draw {feel})")   # draw above is made all the same, so no
        feel = token_feel                                   # other draw moves; a vocabulary whose tokens do not say their songs' feel keeps the draw
    if token_places and feel != token_feel:                 # a tune's places in the beat are its song's feel's (round 147)
        log.append(f"the balance's song is in {token_feel} feel and the song in {feel}: its tune's places in the beat are not held (round 147)")
    if "periods" in models:                                 # the riff under the tune: a backing part's period inside a part of the form, and the bars it holds
        tempo_band = rhythm.band(bpm)
        for role in band:
            if role not in rhythm.BACKING:
                continue
            held, of_part = {}, {}
            own = token_periods.get(role)                   # the token song's own period and hold share (round 106)
            own_rng = random.Random(f"{seed}:{role}:period holds")
            for i, (bar, n, of, label) in enumerate(parts):
                if of is not None:
                    continue
                drawn = _draw(models, "periods", (role, rhythm.part_length(n), tempo_band), rng, log)
                if drawn == "none":
                    continue
                lag = int(drawn)
                if own and own[0] < n:                      # the song's lag where the part is long enough for it
                    lag = own[0]
                of_part[i] = lag
                for k in range(bar + lag, bar + n):
                    held_draw = "period_holds" not in models or _draw(models, "period_holds", (role, drawn), rng) == "held"
                    if own:                                 # the pooled draw above is still made, so no other draw moves
                        held_draw = own_rng.random() < own[1]
                    if held_draw:
                        held[k] = lag
            if of_part:
                extras.setdefault(role, {})["periods"] = held
                log.append(f"{role} period: " + ", ".join(f"{parts[i][3]} every {lag} bar{'s' if lag > 1 else ''}" for i, lag in of_part.items())
                           + f"; {len(held)} bars held" + (f" (the balance's song's: every {own[0]} bar{'s' if own[0] > 1 else ''}, held {own[1]:.2f})" if own else ""))
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
                level_from=level_from, voice_levels=voice_levels, layer_from=layer_from, kinds=token_kinds, token_samples=token_samples, token_habits=token_habits, layer_samples=token_layer_samples, layer_shares=token_layer_shares, section_levels=section_levels, section_onsets=section_onsets, kit_bounds=kit_bounds, section_densities=section_densities, section_fills=section_fills,
                top_level=top_level, loudness=token_loud, pans=token_pans, sample_ranges=token_sample_ranges, layer_ranges=token_layer_ranges, layer_relations=token_layer_relations, stretches=token_stretches, layer_stretches=token_layer_stretches, layer_struck=token_layer_struck, tone_profiles=token_profiles, step_profiles=token_steps, chord_shapes=token_shapes, form_letters=token_form, loops=loops, bass_continuity=token_continuity, bass_downbeat=token_downbeat, first_beats=token_first, tune_shortest=token_shortest, tune_lengths=token_lengths, tones_kept=token_tones, together=token_together, tune_together=token_tune_together, beat=token_beat, tune_places=token_places, with_kit=token_with_kit, token_feel=token_feel)


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


def tune_lead(plan: "Plan", song: rhythm.Song, role: str, written: dict) -> dict | None:
    """What the tune's writer needs to bring the tune back with the bass (round 146, Plan.tune_together): the bass line's
    bars as they will be played (rhythm.bar_cells of its line; a bar of a part of the form played again as the bar it
    plays, played_again), the token song's shares of the bars in which the bass plays an earlier bar again that the tune
    plays again too, where that bar is further back (`far`) and where it is the bar right before (`near`; either None
    where the song has no count), and its share of the tune's bars that are an earlier bar note for note; None for a
    tune without the token's field or a song without a bass."""
    own = (getattr(plan, "tune_together", None) or {}).get(role)
    if own is None or R.BASS not in written:
        return None
    cells = rhythm.bar_cells([(x[0], x[1] - x[0], x[2]) for x in written[R.BASS].notes if len(x) < 4 or x[3] == 0], song.bars)
    for k, j in sorted(played_again(plan, song).items()):
        if k < len(cells) and j < len(cells):
            cells[k] = cells[j]
    return {"cells": cells, "far": own[0], "near": own[1], "overall": own[2]}


def played_again(plan: "Plan", song: rhythm.Song) -> dict:
    """The bars of a part of the form that plays an earlier part again -> the bar each plays (round 142), as copy_repeats
    copies them after the writers: the bars both parts have, the whole of them inside the song; a part that plays a part
    that plays another is followed to the bars first written."""
    plays = {}
    for bar, n, *rest in plan.parts:
        of = rest[0] if rest else None
        if of is not None:
            src, m = plan.parts[of][0], min(n, plan.parts[of][1])
            if m > 0 and bar + m <= len(song.bars) and src + m <= len(song.bars):
                plays.update({bar + i: plays.get(src + i, src + i) for i in range(m)})
    return plays


def kit_hits(plan: "Plan", song: rhythm.Song) -> dict:
    """The positions the kit strikes a bar, any piece, as the song will play it (round 149): {bar: the positions}, a bar of
    a part of the form played again as the bar it plays (played_again: copy_repeats copies the kit with the rest); a bar
    the kit rests in is left out. What the bass's and the tune's writers hold their notes to (Plan.with_kit)."""
    at = {}
    for k, (a, b) in enumerate(song.bars):
        struck = frozenset(rhythm.position(n[0] - a, song.division) for n in song.notes.get(R.DRUMS, []) if a - rhythm.NEAR <= n[0] < b - rhythm.NEAR)
        if struck:
            at[k] = struck
    plays = played_again(plan, song)
    return {k: at[plays.get(k, k)] for k in range(len(song.bars)) if plays.get(k, k) in at}


def played_as(plan: "Plan", song: rhythm.Song, key: str, playing: list) -> list:
    """Each bar -> the written bar whose notes a voice will hold in it (round 149), once the passes after its writer have
    copied them: the loop's figure (hold_loop: a later bar on the figure plays the first bar at its place of the figure's
    length again) and the form's repeats (played_again, copy_repeats). `playing`: whether the voice plays in each bar as
    written (a bar it rests in is never on a figure). A hold counts a written bar for every bar that will play it."""
    src = {}
    for bar, n, lag, off in looped_parts(plan.parts, (plan.loops or {}).get(key)) or ():
        figure = {}
        for k in range(bar, min(bar + n, len(playing))):
            if k in off or not playing[k]:
                continue
            first = figure.setdefault((k - bar) % lag, k)
            if first != k:
                src[k] = first
    plays = played_again(plan, song)
    out = []
    for k in range(len(playing)):
        k = plays.get(k, k)
        out.append(src.get(k, k) if k < len(playing) else None)
    return out


def hold_together(plan: "Plan", song: rhythm.Song, role: str, part, lead, held: dict | None = None, leave=(), over=()) -> list:
    """A part held to its token song's share of the bars in which it comes back with its lead (round 144, Plan.together;
    rhythm.together_field counts it): where the lead's line (`lead`: its notes, the bass's for a chord part, the tune's
    for the counter-line) plays an earlier bar again note for note, the nearest within rhythm.TONES_BACK, and the part
    plays in both bars, the part's line plays that bar again too. Counted as the token counts it, on the lines' bars
    (rhythm.bar_cells), the song as it will be played (played_again: a bar of a part of the form played again counts
    with the bars it plays, and is left), and the share over the whole song. While it is under the song's, such a bar
    in which the part plays another bar takes the earlier bar whole, every voice of the part with its onsets and
    lengths, where that bar is this bar's: the plan's same chord under both, the bar within the part's own onsets for
    this part of the form (own_keeps), and no more of its notes a semitone from a note of `over` sounding at their
    onset than the bar's own had (`over`: the tune and the counter-line over a chord part; the parts under the
    counter-line). A bar on its loop's figure (`held`, round 121) and a bar the line rides the bass in (`leave`) stand.
    The game's bars come back whole; the written parts each came back by their own draws, so the bass under a tune's
    bar played again was the bass of that bar in 0.52 of cases (FFVI's 0.79) and the chord reader heard another chord
    on the root. Returns a log line."""
    own = (getattr(plan, "together", None) or {}).get(role)
    if own is None or not part.notes or not lead:
        return []
    bars = song.bars[:len(plan.chords)]
    plays, played_by = played_again(plan, song), {}
    for k, j in plays.items():
        played_by.setdefault(j, []).append(k)
    line = lambda notes: rhythm.bar_cells([(x[0], x[1] - x[0], x[2]) for x in notes if len(x) < 4 or x[3] == 0], bars)   # noqa: E731
    lead_cells, cells = line(lead), line(part.notes)
    for k in sorted(plays):
        if k < len(bars) and plays[k] < len(bars):
            lead_cells[k], cells[k] = lead_cells[plays[k]], cells[plays[k]]
    in_bar = lambda x, k: bars[k][0] - rhythm.NEAR <= x[0] < bars[k][1] - rhythm.NEAR   # noqa: E731
    keeps = own_keeps(plan, role)

    def clashes(notes: list) -> int:
        """The notes a semitone from a note of `over` sounding at their onset."""
        return sum(1 for x in notes if any(t[0] - rhythm.NEAR <= x[0] < t[1] - rhythm.NEAR and (int(round(x[2])) - int(round(t[2]))) % 12 in (1, 11) for t in over))
    seen, both = rhythm.together(lead_cells, cells)
    moved, stood = 0, Counter()
    for k in range(1, len(bars)):
        if not both < own * seen:
            break
        j = rhythm.bar_back(lead_cells, k)
        if j is None or not cells[k] or not cells[j] or cells[k] == cells[j]:
            continue
        if k in plays:
            stood["in a part of the form played again"] += 1
            continue
        if k in leave or _on_figure(held, role, bars[k][0], bars[k][1], song.meter):
            stood["on a loop's figure or riding the bass"] += 1
            continue
        if plan.chords[k] != plan.chords[j]:                # another chord under it: the earlier bar is not this bar's
            stood["over another chord"] += 1
            continue
        if not keeps(k, len(cells[j])):                     # more or fewer notes than this part of the form's bars hold
            stood["not within the part's own onsets"] += 1
            continue
        at = plays.get(j, j)                                # where the earlier bar's notes are written
        shift = bars[k][0] - bars[at][0]
        mine = [x for x in part.notes if in_bar(x, k)]
        again = [(x[0] + shift, x[1] + shift) + tuple(x[2:]) for x in part.notes if in_bar(x, at)]
        if over and clashes(again) > clashes(mine):
            stood["a semitone from a line over or under it"] += 1
            continue
        part.notes[:] = sorted([x for x in part.notes if not in_bar(x, k)] + again, key=lambda n: (n[0], n[3] if len(n) > 3 else 0))
        if k < len(part.figures) and at < len(part.figures):
            part.figures[k] = part.figures[at]
        cells[k] = cells[j]
        for r in played_by.get(k, ()):                      # and the bars that play this one again
            cells[r] = cells[k]
        moved += 1
        seen, both = rhythm.together(lead_cells, cells)
    if moved:
        song.notes[role] = [(x[0], x[1] - x[0], x[2], role) for x in part.notes]
    return [f"{role}: an earlier bar played again where the {'tune' if role == R.COUNTER else 'bass'} plays it again in {both} of {seen} such bars ({both / seen:.2f}; the balance's song's {own:.2f}); "
            f"{moved} bars given the earlier bar" + ("; stood: " + ", ".join(f"{n} {why}" for why, n in stood.most_common()) if stood else "") + " (round 144)"] if seen else []


def hold_chord_tones(plan: "Plan", song: rhythm.Song, role: str, part, bass=(), held: dict | None = None, leave=(), over=()) -> list:
    """A chord part held to its token song's share of bars that sound again the pitch classes the part played on the root
    before (round 142, Plan.tones_kept: the share of such bars, and of those the share that sound the bar before's own;
    rhythm.tones_kept_field counts both). The count is the token's own: a bar with earlier bars on its root,
    rhythm.TONES_BACK bars back at most, in which the part sounds is such a bar, and its root is the bass's
    (rhythm.bass_roots of `bass`, the bass's notes as written), whatever the plan's chord and the part of the form. The
    song is counted as it will be played: a bar of a part of the form that plays an earlier part again (copy_repeats,
    after this hold) counts with the notes and the root of the bar it plays, and is left as it is (what is written in
    it is not played), and the share held to the song's is the part's over the whole song (a share run bar by bar from
    the song's start gave a part its first bars where it ends at the song's share without them). Counted by the plan's
    chords, with the repeats as first written and bar by bar, a part at its song's share read far under it and was
    given bars all the same (the written Terra's harmony: of its line of four bars that comes round, the second and
    the fourth given the first's).
    Bar by bar: one that sounds none of those bars' pitch classes, while the part's share of such bars that do is
    under the song's, keeps its own onsets and lengths and takes, voice by voice, the pitches of one of them that is on
    the plan's same chord in the bar's own part of the form (where an earlier bar's notes fit again):
    the bar before's while the share of the kept bars that sound the bar before's runs under the
    song's, else the nearest bar further back that sounds another set than the bar before (a figure of two bars or more,
    as the song's); and of those only a bar with this bar's own rhythm, voice by voice, so that the earlier bar's notes
    come again one for one (the written parts repeat a rhythm on a chord more often than the game's do, and its pitch
    classes far less; onto another rhythm an earlier bar's pitches fall as a part of its set, and a voice with one note
    there holds it through). Where there is no such bar the bar stands, the figure's next bar. A bar on its loop's figure (round 121,
    `held`) and a bar the line rides the bass in or doubles it (`leave`: bar indices) stand as written, and so does a
    bar one of whose notes would then sit a semitone from a note of the tune or the counter-line sounding at its onset
    (`over`: their notes, written before this hold and over the part as it stood) where its own did not. The part's tones are drawn a bar at a time (a voicing at each bar's first onset, the motion's walk
    along it, the tone figure's onsets off the chord, the profile's hold), so under one chord two bars seldom sounded one
    set of pitch classes, and the chord reader heard the chord change its shape. Returns a log line."""
    own = (getattr(plan, "tones_kept", None) or {}).get(role)
    if own is None or not part.notes:
        return []
    share, near_share = own
    bars = song.bars[:len(plan.chords)]
    part_of, plays, played_by = {}, {}, {}                  # a bar's part of the form; a bar of a part played again -> the bar it plays; and back
    for i, (bar, n, *rest) in enumerate(plan.parts):
        part_of.update({k: i for k in range(bar, bar + n)})
        of = rest[0] if rest else None
        if of is not None:                                  # as copy_repeats copies it: the bars both parts have, the whole of them inside the song
            src, m = plan.parts[of][0], min(n, plan.parts[of][1])
            if m > 0 and bar + m <= len(song.bars) and src + m <= len(song.bars):
                plays.update({bar + i_: plays.get(src + i_, src + i_) for i_ in range(m)})
    chords = [(part_of.get(k),) + tuple(c) if c is not None else None for k, c in enumerate(plan.chords[:len(bars)])]   # a chord in its part of the form
    in_bar = lambda x, k: bars[k][0] - rhythm.NEAR <= x[0] < bars[k][1] - rhythm.NEAR   # noqa: E731
    lengths = lambda: [(x[0], x[1] - x[0], x[2]) for x in part.notes]   # noqa: E731
    rhythm_of = lambda b_: sorted((x[3], round((x[0] - bars[b_][0]) * 12)) for x in part.notes if in_bar(x, b_))   # noqa: E731  a bar's onsets, voice by voice
    tones = rhythm.bar_tones(lengths(), bars)
    roots = rhythm.bass_roots([(x[0], x[1] - x[0], x[2]) for x in bass], bars)   # a bar's root as the token counts it: the bass's
    for k in sorted(plays):                                 # a bar that plays an earlier one: that bar's notes and root
        if k < len(bars) and plays[k] < len(bars):
            tones[k], roots[k] = tones[plays[k]], roots[plays[k]]
            played_by.setdefault(plays[k], []).append(k)
    seen_all, kept_all, _ = rhythm.tones_kept(tones, roots)  # the part over the whole song, as it will be played
    kept = near = moved = 0                                 # the bars so far that sound an earlier bar's again, and the bar before's
    for k in range(1, len(bars)):
        before = rhythm.tones_before(tones, roots, k)
        if not before:
            continue
        match = next((j for j in before if tones[j] == tones[k]), None)
        j = None
        if match is None and kept_all < share * seen_all and k not in plays and k not in leave and not _on_figure(held, role, bars[k][0], bars[k][1], song.meter):
            fit = [i for i in before if chords[i] == chords[k] and i not in plays]   # of them the bars whose notes fit this one: the plan's same chord, in its part of the form
            last = bool(fit) and fit[0] == k - 1            # the bar before is on the chord: its pitch classes again is a figure of one bar
            further = [i for i in fit if not (last and tones[i] == tones[k - 1])]   # the bars back that sound another set than the bar before's
            pool = ([k - 1] if last and near < near_share * (kept + 1) else []) + [i for i in further if i != k - 1]
            j = next((i for i in pool if rhythm_of(i) == rhythm_of(k)), None)   # the nearest of them with this bar's own rhythm, voice by voice: its
                                                            # notes then come again one for one (none: the bar stands, a figure's new bar)
        if j is not None:
            source = {(y[3], round((y[0] - bars[j][0]) * 12)): y[2] for y in part.notes if in_bar(y, j)}   # the earlier bar's notes, by voice and place
            again = {}
            for i, x in enumerate(part.notes):
                if not in_bar(x, k):
                    continue
                pitch = source[(x[3], round((x[0] - bars[k][0]) * 12))]
                above = {int(round(t[2])) % 12 for t in over if t[0] - rhythm.NEAR <= x[0] < t[1] - rhythm.NEAR}
                clash = lambda m: any((int(round(m)) - pc) % 12 in (1, 11) for pc in above)   # noqa: E731
                if clash(pitch) and not clash(x[2]):        # a semitone from the tune as it sounds there, where the bar's own note is not:
                    again = None                            # the bar stands whole (a bar part the earlier one's and part its own is neither's)
                    break
                again[i] = pitch
            if again:
                for i, pitch in again.items():
                    part.notes[i] = part.notes[i][:2] + (pitch,) + tuple(part.notes[i][3:])
                moved += 1
                tones[k] = rhythm.bar_tones(lengths(), [bars[k]])[0]
                for r in played_by.get(k, ()):              # and the bars that play this one again
                    tones[r] = tones[k]
                kept_all = rhythm.tones_kept(tones, roots)[1]   # the whole song again: a bar further on may have lost the bar it sounded again
                match = next((j for j in before if tones[j] == tones[k]), None)
        kept += match is not None
        near += match == k - 1
    if moved:
        song.notes[role] = [(x[0], x[1] - x[0], x[2], role) for x in part.notes]
    seen, kept, near = rhythm.tones_kept(tones, roots)
    return [f"{role}: an earlier bar's pitch classes on the bass's root sounded again in {kept} of {seen} such bars ({kept / seen:.2f}; the balance's song's {share:.2f}), "
            f"the bar before's in {near} of them ({near_share:.2f} of the song's); {moved} bars given an earlier bar's pitches (round 142)"] if seen else []


def _on_figure(held: dict | None, role: str, a: float, b: float, meter: int) -> bool:
    """Whether a part holds a loop's figure (round 121, hold_loop's held bars by (part, voice)) in a bar of [a, b): the theme
    band and the hand-offs leave such a bar as it is, as the token song's riff plays on under its tune."""
    first, last = int((a + rhythm.NEAR) // meter), int((b - 2 * rhythm.NEAR) // meter)
    return any(k in bars for (r, _), bars in (held or {}).items() if r == role for k in range(first, last + 1))


def own_keeps(plan: Plan, role: str):
    """A part's test of a bar against its token song's own onsets for the part of the form (round 139): (bar, onsets of the
    part's line there) -> whether the bar is within them (envelope_at_for's own envelope: half to one and a half times,
    rounds 125 and 134); always so for a part without them. The theme band and the hand-offs put the tune's bar into
    another part's, and since round 138 the tune's bars are as thin as its token song's: a bass doubling a tune's bar of
    one note stopped for the bar where the game's bass plays six or seven (the written Terra, four bars)."""
    env = envelope_at_for(plan, role)
    if not getattr(env, "own", False):
        return lambda k, n: True

    def keeps(k: int, n: int) -> bool:
        e = env(k)
        return e is None or e[0] <= n <= e[1]
    return keeps


def _kept_line(kept: Counter, what: str) -> list:
    """The log line for the bars a part kept as its own (round 139), or none."""
    if not kept:
        return []
    return [f"the tune's {what} in {sum(kept.values())} bars fewer, the bar not within the part's own onsets for its part of the form "
            f"(round 139): " + ", ".join(f"{role} {n}" for role, n in sorted(kept.items()))]


def double_theme(plan: Plan, song: rhythm.Song, written: dict, models: dict, rng: random.Random, held: dict | None = None) -> list:
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
    log, kept, keeps = [], Counter(), {}
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
            if _on_figure(held, role, a, b, song.meter):    # the part loops here (round 121): its figure stands
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
            if role not in keeps:
                keeps[role] = own_keeps(plan, role)
            if not keeps[role](k, len({round(t * 12) for t, *_ in copied})):   # the bar would not be within the part's own onsets (round 139):
                kept[role] += 1                                              # the part keeps its bar
                continue
            _replace_bars(written[role], song, role, a, b, copied)
            log.append(f"bar {k}: the {role} doubles the {'theme' if c == theme else 'tune'}'s cell ({int(off):+d})")
    return log + _kept_line(kept, "cell doubled")


def carry_theme(plan: Plan, song: rhythm.Song, written: dict, models: dict, rng: random.Random, held: dict | None = None) -> list:
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
    counts, log, kept = {}, [], Counter()
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
        if _on_figure(held, carrier, a, b, song.meter):     # the carrier loops here (round 121): its figure stands
            continue
        low, high = plan.bounds.get(carrier, plan.registers.get(carrier, (24, 100)))   # where the game plays the carrier's sample (round 34)
        octaves = round(((low + high) / 2 - statistics.median(m for _, _, m, _ in theme_notes)) / 12)
        copied = [(t + shift, u + shift, float(min(high, max(low, m + 12 * octaves))), 0) for t, u, m, _ in theme_notes if t + shift < b - rhythm.NEAR]
        keeps = own_keeps(plan, carrier)
        if not all(keeps(k, len({round(t * 12) for t, *_ in copied if song.bars[k][0] - rhythm.NEAR <= t < song.bars[k][1] - rhythm.NEAR}))
                   for k in range(w[0], w[0] + n)):         # a bar of the phrase would not be within the carrier's own onsets (round 139)
            kept[carrier] += n
            continue
        _replace_bars(written[carrier], song, carrier, a, b, copied)
        log.append(f"bar {w[0]}: the {carrier} carries the theme phrase ({12 * octaves:+d})")
    return log + _kept_line(kept, "theme phrase carried")


def hand_off_cells(plan: Plan, song: rhythm.Song, written: dict, models: dict, rng: random.Random, held: dict | None = None) -> list:
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
    log, taken, kept = [], set(), Counter()
    lines, keeps = {}, {}
    for role in rhythm.HANDOFF_PARTS:
        if role in written and role in plan.band:
            lines[role] = lambda role=role: sorted(rhythm._line([(a, b - a, m, 0) for a, b, m, v in written[role].notes if v == 0]))
            keeps[role] = own_keeps(plan, role)
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
        if _on_figure(held, role, lo, hi, song.meter):      # the part loops here (round 121): its figure stands
            continue
        beside = {round(n[0] * 12) for n in written[role].notes
                  if n[3] == 0 and a_t - rhythm.NEAR <= n[0] < b_t - rhythm.NEAR and not lo - rhythm.NEAR <= n[0] < hi - rhythm.NEAR}
        if not keeps[role](target, len(beside) + len(copied)):   # the bar, with the cell in its half, would not be within the part's own
            kept[role] += 1                                     # onsets (round 139): the part keeps its half
            continue
        _replace_span(written[role], song, role, lo, hi, copied)
        taken.add((role, target, i % 2))
        log.append(f"bar {target}: the {role} takes up the tune's cell from bar {bar} ({far} on)")
    return log + _kept_line(kept, "cell taken up")


def _replace_span(part, song: rhythm.Song, role: str, a: float, b: float, copied: list) -> None:
    """The part's LINE voice's notes in [a, b) replaced by `copied` [(start, end, midi, 0)], the other voices kept, in the
    written part and the song."""
    inside = lambda n: a - rhythm.NEAR <= n[0] < b - rhythm.NEAR and n[3] == 0   # noqa: E731
    gone = {(round(n[0], 3), int(round(n[2]))) for n in part.notes if inside(n)}
    part.notes[:] = sorted([n for n in part.notes if not inside(n)] + copied, key=lambda n: n[0])
    song.notes[role] = sorted([n for n in song.notes.get(role, []) if (round(n[0], 3), int(round(n[2]))) not in gone]
                              + [(t, u - t, m, role) for t, u, m, _ in copied], key=lambda n: n[0])


def _repeat_last(notes: list, kept: list, bars: list, lo: float, hi: float, shift: float) -> tuple | None:
    """The last note of a tune's line in a part of the form played again (round 140), as copy_repeats copies it: (its
    start in the repeat, its pitch, the end it takes there), or None where it stands as copied. The note sounds the share of
    its gap it sounds in the part it repeats, the gap measured to the note that follows the repeat (rhythm.tune_gap): the copy had
    kept the length the note has before what follows the first statement, so a note held to a bar line there stopped at it
    in the repeat too where the next bar opens with a rest (the written Terra's B, a pickup a beat long before three beats
    of nothing), and one held over the bar line ran into the note that follows the repeat."""
    line = sorted((x for x in notes if x[3] == 0), key=lambda x: x[0])
    inside = [x for x in line if lo - rhythm.NEAR <= x[0] < hi - rhythm.NEAR]
    if not inside:
        return None
    last = inside[-1]
    after_s = next((x[0] for x in line if x[0] > last[0] + rhythm.NEAR), None)
    after_t = min((x[0] for x in kept if x[3] == 0 and x[0] > last[0] + shift + rhythm.NEAR), default=None)
    gap_s, gap_t = rhythm.tune_gap(bars, last[0], after_s), rhythm.tune_gap(bars, last[0] + shift, after_t)
    if gap_s <= rhythm.NEAR or gap_t <= rhythm.NEAR or abs(gap_t - gap_s) <= rhythm.NEAR:
        return None
    return last[0] + shift, last[2], last[0] + shift + min(1.0, (last[1] - last[0]) / gap_s) * gap_t


def copy_repeats(plan: Plan, song: rhythm.Song, written: dict) -> list:
    """A part of the form that repeats an earlier one plays it note for note in every part written, as a driver replays
    a part (the writers copy their own figures for it already; the notes under them, the second lines and the voicings
    had been written fresh, so the form reader, which finds parts by such repeats, heard one part where the plan had
    four). The tune's and the counter-line's last note of the part sounds against the note that follows the repeat
    (round 140, _repeat_last). Returns a log line a repeat."""
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
            last = _repeat_last(part.notes, kept, song.bars, lo_s, hi_s, shift) if role in (R.MELODY, R.COUNTER) else None
            if last is not None:                            # the tune's last note there, against the note that follows the repeat (round 140)
                i = next((j for j, x in enumerate(copied) if x[3] == 0 and abs(x[0] - last[0]) < 1e-6 and x[2] == last[1]), None)
                if i is not None:
                    copied[i] = (copied[i][0], last[2]) + tuple(copied[i][2:])
            part.notes[:] = sorted(kept + copied, key=lambda x: x[0])
            for k in range(m):
                if bar + k < len(part.figures) and src_bar + k < len(part.figures):
                    part.figures[bar + k] = part.figures[src_bar + k]
            if role in song.notes:
                kept = [x for x in song.notes[role] if not inside(x[0], lo_t, hi_t)]
                copied = [(x[0] + shift,) + tuple(x[1:]) for x in song.notes[role] if inside(x[0], lo_s, hi_s)]
                if last is not None:
                    i = next((j for j, x in enumerate(copied) if abs(x[0] - last[0]) < 1e-6 and x[2] == last[1]), None)
                    if i is not None:
                        copied[i] = (copied[i][0], last[2] - last[0]) + tuple(copied[i][2:])
                song.notes[role] = sorted(kept + copied, key=lambda x: x[0])
        log.append(f"{label} (bars {bar}-{bar + m - 1}) plays {plan.parts[of][3]} (bars {src_bar}-{src_bar + m - 1}) again note for note")
    return log


def write(plan: Plan, song: rhythm.Song, models: dict, seed: int, reference=None) -> dict:
    """The parts written in turn on the song: the drums, the bass, the upper
    parts, the melody; each put into song.notes for the next to read.
    {role: Part}."""
    written, key = {}, (plan.tonic, plan.mode)
    held_bars = {}                                          # (part, voice) -> the bars it holds on its loop's figure (round 121, hold_loop)
    kit_letters = {rhythm.LETTERS[p] for p in song.pieces.values() if p in rhythm.LETTERS}
    pieces = plan.extras.get(R.DRUMS, {}).get("pieces")     # the pieces the song's kit strikes (kit_pieces, round 58); every piece without the word
    if pieces:
        kit_letters &= set(pieces)
    if R.DRUMS in plan.band and kit_letters:
        kit_value = "".join(x for x in rhythm.LETTERS.values() if x in kit_letters)   # the kit's pieces: the kit figure is drawn from songs with this kit
        kit_classes = plan.extras.get(R.DRUMS, {}).get("kit_classes") or {}     # the slots' strike classes (round 81): a letter's bars from songs that strike
        kit_models = models                                 # the kit's bar tables: for a song counted in double time (round 131) the tables counted
        if getattr(plan, "beat", 1) == 2:                   # so, where the pack keeps them (round 145): its bars are its token song's kind of bar
            kit_models = {**models, **{name[:-len(rhythm.DOUBLE_TABLE)]: t for name, t in models.items() if name.endswith(rhythm.DOUBLE_TABLE)}}
        limbs = {g: kit_models[name] for g in rhythm.DRUM_GROUPS if (name := "drums-" + "".join(g)) in kit_models and set(g) & kit_letters}   # its sample as this one does
        whole_kit = "drums" in kit_models and (not limbs or (not kit_classes and writer.kit_table_reaches(kit_models["drums"], song, kit_letters, kit_value, plan.habits[R.DRUMS])))
        # with classes the kit is written from its limbs (round 81): the kit table's bar is one song's, hat and all, and under a rare kit the
        # draw smooths that song's bars with every kit's; a limb's table under the slot's class pools the songs that strike the sample as this one does
        if whole_kit:                                       # the kit as one figure: its bars repeat and vary together, as a kit's do
            groups = {tuple(rhythm.LETTERS.values()): kit_models["drums"]}
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
            kit_bounds = getattr(plan, "kit_bounds", None) or []
            hits, figures = writer.drums(song, groups, random.Random(f"{seed}:drums"), habit=group_habits, free=True, plays=plan.plays[R.DRUMS], kit_value=kit_value,
                                         class_values=group_classes,
                                         bounds_at=(lambda k: kit_bounds[k] if 0 <= k < len(kit_bounds) else None) if any(b is not None for b in kit_bounds) else None)   # each piece as the token song strikes it in the part of the form (round 125)
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
            notes, kit_looped, _ = hold_loop(plan, R.DRUMS, notes, song.meter)   # the kit's figure again where the token song's kit loops (round 121)
            song.notes[R.DRUMS] = [(t, end - t, float("nan"), sample) for t, end, _, _, sample in notes]
            written[R.DRUMS] = Part(R.DRUMS, notes, figures, [f"kit habit {plan.habits[R.DRUMS]}; groups " + ", ".join(f"{'+'.join(g)} {h}" + (" under " + " ".join(v for v in group_classes[g].values() if v != "-") if group_classes.get(g) else "") for g, h in group_habits.items())
                                                              + f"; {sum(1 for f in figures if f != writer.REST)} bars written, {len(notes)} hits"
                                                              + (f"; pieces {''.join(sorted(kit_letters, key=list(rhythm.LETTERS.values()).index))}")
                                                              + (f"; dropped (not in the kit) {dict(dropped)}" if dropped else "")
                                                              + ("; the slots' strike classes: the kit from its limbs' tables under them (round 81)" if kit_classes and limbs else
                                                                 "; the kit table holds no bar this kit plays within its habit's density: the limbs' tables at their own habits (round 75)" if "drums" in models and not whole_kit else "")])
            if kit_models is not models:                    # a song counted in double time: its kit's bars from the tables counted so (round 145)
                written[R.DRUMS].log.append("the kit's bars from the kit tables counted in double time, as the balance's song is (round 145)")
            if kit_looped:
                written[R.DRUMS].log.append(f"the kit's figure again, hit for hit, in {kit_looped} bars where the balance's song's kit loops (round 121)")
            if runs:                                        # the second samples' hits (round 99)
                written[R.DRUMS].log.append("kit seconds (kit_seconds): " + ", ".join(f"{k} {r[0]} of {r[1]} hits on the second sample (the token's share {seconds_of[k]['share']:.2f})" for k, r in runs.items())
                                            + ("" if "kit_seconds" in models else "; no kit_seconds word: the slot's sample throughout"))
    bass_as_written = []                                    # the bass writer's line, to tell its bars from those rewritten after it (round 114)
    if R.BASS in plan.band and "bass" in models:
        # the bass sits on the kit's accents (two pieces together) at the game's share (bass_locks): FFVI's on 0.94 of them;
        # locked to the whole planned band it had met the threshold in no bar, written second with two drum voices to hand
        lock = {k: (ps, set()) for k, ps in rhythm.kit_accents(song.notes.get(R.DRUMS, []), song.bars, song.division).items()} if R.BASS in plan.locks else locks_of(song, {R.BASS}, plan)
        lock_share = plan.locks.get(R.BASS, 1.0)
        layered = plan.voices.get(R.BASS, 1) >= 2 and layer_of(plan.extras.get(R.BASS))[0] == "apart"
        sounds_line = float(_draw(models, "layer_sounds", (R.BASS, "line"), random.Random(f"{seed}:bass:line sounds"))) if layered and "layer_sounds" in models else plan.sounds[R.BASS]
        gs = plan.gap_sounds.get(R.BASS)                    # the share a note sounds by its gap (gap_sounds), the one share without it
        shared_bass = {}                                    # the line's notes, for a second voice following it
        bass_log = []                                       # what the bass writer's holds did (round 114)
        bass_kit = (getattr(plan, "with_kit", None) or {}).get(R.BASS)   # the token song's bass's shares with the kit (round 149)
        notes, figures = writer.bass(song, models["bass"], random.Random(f"{seed}:bass"), habit=plan.habits[R.BASS], habit_at=habit_at_for(plan, R.BASS), envelope_at=envelope_at_for(plan, R.BASS), key=key, lock=lock,
                                     free=True, plays=plan.plays[R.BASS], register=plan.bounds.get(R.BASS, plan.registers[R.BASS])[0],
                                     sounds=gs["line" if layered else "only"] if gs else sounds_line, shared=shared_bass, lock_share=lock_share,
                                     ceiling=plan.bounds.get(R.BASS, plan.registers[R.BASS])[1], bounds_at=line_bounds_at(plan, R.BASS),
                                     tone_profile=plan.tone_profiles.get(R.BASS),   # the line's chord tones as the token song's (round 111)
                                     continuity=plan.bass_continuity, log=bass_log,   # and its pitch held across bar lines as the song's (round 114)
                                     downbeat=getattr(plan, "bass_downbeat", None),   # and a bar's first beat on the chord's root as often as the song's (round 129)
                                     first_beat=getattr(plan, "first_beats", {}).get(R.BASS),   # and struck as often as the song's bass strikes it (round 133)
                                     with_kit=bass_kit, kit=kit_hits(plan, song) if bass_kit else None,   # and its notes struck with the kit as often as the
                                     played_as=lambda playing: played_as(plan, song, R.BASS, playing), keeps=own_keeps(plan, R.BASS))   # song's (round 149)
        notes = fold_line(plan, R.BASS, notes, song.meter)  # the line in each stretch's register (round 91)
        notes, bass_looped, held_bars[(R.BASS, 0)] = hold_loop(plan, R.BASS, notes, song.meter)   # the line's figure again where the token song's bass loops (round 121)
        if bass_looped:
            bass_log.append(f"the line's figure again, note for note, in {bass_looped} bars where the balance's song's bass loops (round 121)")
        song.notes[R.BASS] = [(a, b - a, m, "bass") for a, b, m in notes]
        line = [(a, b, m, 0) for a, b, m in notes]
        bass_as_written = list(line)
        log = [f"habit {plan.habits[R.BASS]}, register {plan.bounds.get(R.BASS, plan.registers[R.BASS])}, {sum(1 for f in figures if f != writer.REST)} bars written, "
               f"{len(notes)} notes; " + (f"on the kit's accents in {len(lock)} bars at {lock_share:.1f}" if R.BASS in plan.locks else f"locked to the band in {len(lock)} bars")]
        log += bass_log
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
            notes2, _, held_bars[(R.BASS, 1)] = hold_loop(plan, f"{R.BASS}:1", notes2, song.meter)   # the second line's figure again (round 121)
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
    riding = {}                                             # a chord part -> the bars its line rides the bass in
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
                                                tone_rng=random.Random(f"{seed}:{role}:tones"), log=tlog, tone_tier=plan.extras[role].get("tone_tier"),   # the tone figures on their own stream (round 96)
                                                tone_profile=plan.tone_profiles.get(role),   # the line's chord tones as the token song's (round 111)
                                                first_beat=getattr(plan, "first_beats", {}).get(role))   # and a bar's first beat as often as the song's part (round 135)
        rides = plan.extras[role].get("rides")
        company = plan.extras[role].get("company")          # where the token song's line doubles its bass, by stretch (round 123)
        if rides and not company and R.BASS in written and written[R.BASS].notes:   # the line on the written bass's figure where the token song's rides it (round 106)
            notes, figures, voicings, ride_log = ride_the_bass(plan, song, role, notes, figures, voicings, shared, (low, high), rides,
                                                               [x for x in written[R.BASS].notes if x[3] == 0], random.Random(f"{seed}:{role}:rides"))
            tlog += ride_log
        notes = fold_line(plan, role, notes, song.meter)   # the line in each stretch's register (round 91)
        if role in plan.step_profiles:                      # the line's steps held to the token song's (round 117), the ride's bars among them
            notes, step_log = hold_line_steps(plan, song, role, notes, shared, (low, high))
            tlog += step_log
        if company and R.BASS in written and written[R.BASS].notes:   # the line the bass's double in the token song's stretches (round 123), once it is
            notes, figures, voicings, ride_log = ride_the_bass(plan, song, role, notes, figures, voicings, shared, (low, high), rides or (0.0, 0.0),   # held and
                                                               [x for x in written[R.BASS].notes if x[3] == 0], random.Random(f"{seed}:{role}:rides"), word=company)   # folded: the
            tlog += ride_log                                # double stands as the bass's, at its interval
        notes, line_looped, held_bars[(role, 0)] = hold_loop(plan, role, notes, song.meter)   # the line's figure again where the token song's line loops (round
        if line_looped:                                     # 121): before the voices beside it, which are written against the line as it loops
            tlog.append(f"the line's figure again, note for note, in {line_looped} bars where the balance's song's line loops (round 121)")
        song.notes[role] = [(a, b - a, m, role) for a, b, m, _ in notes]
        log = [f"voices {n}, register {(low, high)}, habit {plan.habits[role]}, voicing {plan.extras[role]['richness']}, "
               f"motion {plan.extras[role]['motion']}, sounded {render_mod._sounds_text(sounds)}; {sum(1 for f in figures if f != writer.REST)} bars written, "
               f"{len(notes)} notes; locked to the band in {len(lock)} bars"] + tlog
        all_figures = [f"{f} / {vc}" for f, vc in zip(figures, voicings)]
        line_notes = list(notes)
        scale = {(plan.tonic + i) % 12 for i in harmony.MODES["major" if plan.mode == "major" else "natural_minor"]}
        beside_v = set()                                    # the voices whose pitch is drawn beside the line under the span rule
        voice_written = {}                                  # each voice beside the line as written, for a sibling struck with it (round 107)
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
                                                              key=key, lock=locks_of(song, {role}, plan), motion=plan.extras[role].get("motion_drawn", plan.extras[role]["motion"]),   # line, kept within the span FFVI's
                                                              pedals={v: (reg_v[0] + reg_v[1]) // 2}, plays=plan.plays[role], figures=given, shared=shared,   # voices beside a line sit in
                                                              tone_index=(writer.ANY_TONE if SECOND_ANY_TONE else v), kind=rel[0], clash_rates=plan.extras[role].get("clashes"))   # (the layer offset's cap), not folded into its offset register
                log.append(f"voice {v + 1} {rel[0]}: register {reg_v} ({offset:+d}, {density}), "
                           + ("its interval to the line and its own moves drawn, " if drawn_pitch else f"the line's voicing {v} tone{'s' if v > 1 else ''} up, ")
                           + f"{sum(1 for f in figures_v if f != writer.REST)} bars, {len(notes_v)} notes" + ("; its bars beside the line's" if given else ""))
            word_v = relation_word(plan, role, v)
            spans_v = stretch_spans(relation_stretches(word_v), len(song.bars)) if word_v else []
            inline = [sp for sp in spans_v if sp[0] == "with" or isinstance(sp[1], tuple)]   # struck with, or a sibling followed (round 107): written now
            if inline:
                figures_v, voicings_v = list(figures_v), list(voicings_v)
                rng_w = random.Random(f"{seed}:{role}:voice {v}:with")
                mask_draw = (lambda f: _draw(models, "second_figures", (role, render_mod.layer_class(plan, role), plan.feel, rhythm.band(plan.bpm), str(len(f.split())), f),
                                             rng_w, floor_k=MASK_FLOOR)) if "second_figures" in models else None
                for kind_w, target, semi_w, at, end in inline:
                    ref = line_notes if target == ("line",) else voice_written.get(target[1])
                    if ref is None:
                        ref = line_notes
                    a0, b0 = song.bars[at][0], song.bars[min(end, len(song.bars)) - 1][1]
                    in_span = [x for x in ref if a0 - rhythm.NEAR <= x[0] < b0 - rhythm.NEAR]
                    sv = struck_values(plan, role, v) if kind_w == "with" else None   # how the token song's voice strikes (round 108)
                    if kind_w == "with":
                        stats_w = {}
                        struck, thinned, figs = struck_with(ref, at, end, semi_w, song, role, v, models, rng_w, plan.extras[role].get("clashes"),
                                                            gs["second"] if gs else sounds, scale, mask_draw, line_notes, sv, stats=stats_w,
                                                            fills=(plan.section_fills.get(role) or {}).get("beside"))   # a fill at a section's end (round 118)
                        for k, f in figs.items():
                            figures_v[k] = f
                    elif kind_w == "double":
                        struck, thinned = diatonic([(x[0], x[1], x[2], v) for x in in_span], semi_w, scale, v), 0
                    else:
                        struck, thinned = parallel([(x[0], x[1], x[2], v) for x in in_span], semi_w, scale, v, song, role, models, rng_w, plan.extras[role].get("clashes"), None), 0
                    notes_v = [x for x in notes_v if not (a0 - rhythm.NEAR <= x[0] < b0 - rhythm.NEAR)] + struck
                    for k in range(at, min(end, len(voicings_v))):
                        voicings_v[k] = f"{kind_w} {'the line' if target == ('line',) else 'voice ' + str(target[1] + 1)} {semi_w:+d}"
                    log.append(f"voice {v + 1} {'struck with' if kind_w == 'with' else kind_w} {'the line' if target == ('line',) else f'voice {target[1] + 1}'} at {semi_w:+d} "
                               f"in bars {at + 1}-{end} (the token's stretches {word_v}): {len(struck)} notes"
                               + (f" on the chord by the parallel_intervals word, {thinned} of the followed onsets thinned by the second_figures word" if kind_w == "with" else "")
                               + ("" if sv is None else f", the mask held toward the token's share {sv['share']:.2f}; lengths by the line's gap"
                                  + (f", at most {sv['longest']:.1f} beats" if sv.get("longest") else "")
                                  + (f"; sounding {stats_w['sounded'] / stats_w['played']:.2f} of its bars' time against the token's {sv['sounding']:.2f}, "
                                     f"{stats_w['shortened']} stabs cut to the token's shortest class share (round 115)"
                                     if kind_w == "with" and sv.get("sounding") is not None and stats_w.get("played") else "")
                                  + (f"; the cell repeated on {stats_w['repeats']} of {stats_w['comparable']} stabs with a stab at the same place of the bar "
                                     f"before, the token's {sv['cell']:.2f} (round 116)" if kind_w == "with" and sv.get("cell") is not None and stats_w.get("comparable") else "")
                                  + (f"; {stats_w['filled']} stabs added in the fill bars (round 118)" if stats_w.get("filled") else "")))
                late = [sp for sp in spans_v if sp not in inline and sp[0] != "own"]   # its stretches on another part's line (round 122)
                notes_v.sort(key=lambda x: x[0])
                beside_v.discard(v)
                notes_v, looped_v, held_bars[(role, v)] = hold_loop(plan, f"{role}:{v}", notes_v, song.meter)   # its figure again where the token song's voice loops (round 121)
                if looped_v:
                    log.append(f"voice {v + 1}: its figure again, note for note, in {looped_v} bars where the balance's song's voice loops (round 121)")
                if late:                                    # a voice struck with another in some parts of the form that doubles or runs parallel to a
                    pending.append((role, v, notes_v, word_v, True))   # part's line in others (round 122): those written once every line is, as any
                    log.append(f"voice {v + 1}: its stretches on another part's line in {word_v} written after the lines, its struck ones as they stand (round 122)")
                else:
                    song.notes[role] += [(a, b - a, m, role) for a, b, m, _ in notes_v]
                    notes = notes + notes_v
            elif word_v:                                    # what the voice does beside which part, by stretch (round 90): after every line is written
                pending.append((role, v, notes_v, word_v))
                log.append(f"voice {v + 1} by the token's stretches ({word_v}): written after the lines")
            else:
                notes_v, looped_v, held_bars[(role, v)] = hold_loop(plan, f"{role}:{v}", notes_v, song.meter)   # its figure again (round 121)
                if looped_v:
                    log.append(f"voice {v + 1}: its figure again, note for note, in {looped_v} bars where the balance's song's voice loops (round 121)")
                song.notes[role] += [(a, b - a, m, role) for a, b, m, _ in notes_v]
                notes = notes + notes_v
            voice_written[v] = notes_v
            all_figures = [f"{x} || {f} / {vc}" for x, f, vc in zip(all_figures, figures_v, voicings_v)]
        written[role] = Part(role, notes, all_figures, log, beside=beside_v)
        riding[role] = {k for k, vc in enumerate(voicings) if vc == "rides the bass"}   # the bars the line is the bass's (rounds 106, 123)
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
            mask_ctx = lambda pat: (R.COUNTER, plan.weights.get(R.COUNTER, "minor"), plan.feel, tempo, "0" if pat == writer.REST else str(len(pat.split())), "-" if pat == writer.REST else pat)   # noqa: E731
            masks = [writer.REST if not plan.plays[role][k] else
                     _draw(models, "counter_figures", mask_ctx(pat), rng_c, floor_k=COUNTER_MASK_FLOOR, floor_songs=PLAN_SONGS)
                     for k, pat in enumerate(tune_figs + [writer.REST] * (len(song.bars) - len(tune_figs)))]
            own_env = envelope_at_for(plan, R.COUNTER)      # the line's own onsets a bar for its part of the form (round 143): a bar's mask
            mask_said = Counter()                           # within them, drawn again on the bar's own stream (the first draws above stand,
            own_on = getattr(own_env, "own", False)         # so the line's stream is as it was wherever the first mask fits)
            places_c = own_places(plan, R.COUNTER)          # and within its token song's line's places in the beat (round 147), the same way
            place_said, line_n, line_fine = Counter(), 0, Counter()   # for the log; the line's onsets so far and those on each fine place
            if own_on or places_c is not None:
                own_c, starts, owed = (plan.section_onsets[R.COUNTER] if own_on else None), {bar for bar, *_ in plan.parts}, 0.0
                at_of = lambda bar: [] if bar == "-" else [rhythm.position(float(Fraction(t)), song.division) for t in bar.split()]   # noqa: E731
                least = sum((own_env(k) or (1,))[0] if own_on else 1 for k, m in enumerate(masks) if m != writer.REST)   # the least the line will play
                for k, pat in enumerate(tune_figs + [writer.REST] * (len(song.bars) - len(tune_figs))):
                    if k in starts:
                        owed = 0.0                          # the onsets the part of the form's bars so far are short of the song's own (over: under 0)
                    tune_pat = "-" if pat == writer.REST else pat
                    bounds = own_env(k) if own_on and masks[k] != writer.REST else None
                    placed = ((lambda bar, was=None, n=line_n, fine=Counter(line_fine): rhythm.keeps_places(places_c, n, fine, at_of(bar), least)   # noqa: E731
                               and (was is None or not rhythm.adds_places(places_c, at_of(was), at_of(bar))))
                              if places_c is not None and masks[k] != writer.REST else None)
                    if bounds is not None or placed is not None:
                        first = masks[k]
                        slack = max(1.0, MASK_SLACK * own_c[k]) if bounds is not None else None
                        masks[k], how = counter_mask(models, mask_ctx(pat), tune_pat, masks[k], bounds, random.Random(f"{seed}:{role}:mask {k}"),
                                                     want=(owed + own_c[k] - slack, owed + own_c[k] + slack) if bounds is not None else None, placed=placed)
                        if bounds is not None:
                            owed += own_c[k] - mask_strikes(tune_pat, masks[k])
                            mask_said["again" if how == "moved" else how] += 1   # a mask moved onto the places (round 147) is not the first draw
                        if placed is not None:
                            bar_of = lambda m: "-" if m in (writer.REST, "-", "") else rhythm.apply_mask(tune_pat, m)   # noqa: E731
                            place_said["moved"] += how == "moved"
                            place_said["again"] += how != "moved" and not placed(bar_of(first))
                            place_said["none"] += not placed(bar_of(masks[k]))
                    if masks[k] != writer.REST:             # the bar the mask makes of the tune's, into the line's places so far
                        at = at_of(rhythm.apply_mask(tune_pat, masks[k]) if masks[k] not in ("-", "") else "-")
                        line_n += len(at)
                        line_fine.update(rhythm.fine_places(at))
            span = plan.bounds.get(R.COUNTER, plan.registers[R.COUNTER])   # where the game plays the counter's sample (round 34)
            notes, figures, plog = writer.counter(song, written[R.MELODY].notes, tune_figs, masks, span, models, rng_c, x.get("sample", "other"),
                                                  key=key, articulation=x["articulation"], register=span, spans_at=line_bounds_at(plan, R.COUNTER), clash_rates=x.get("clashes"),
                                                  chord_rate=x.get("chord_tones"), tune_sounds=x.get("tune_sounds"),   # its own chord-tone share held (round 96), its note lengths (round 98)
                                                  shortest=shortest_beats(plan, R.COUNTER),   # and no note under its token song's shortest usual one (round 136)
                                                  lengths=own_lengths(plan, R.COUNTER), lengths_rng=random.Random(f"{seed}:{role}:note lengths"),   # held as its token song's line is, on an own stream (round 141)
                                                  move_profile=(getattr(plan, "step_profiles", None) or {}).get(R.COUNTER))   # and no more far moves than its song's line (round 143)
        else:
            tune_kit = ((getattr(plan, "with_kit", None) or {}).get(role) or (None,))[0] if role == R.MELODY else None   # the token song's tune's share with the kit (round 149)
            notes, figures, plog = writer.melody(song, [], plan.bounds.get(role, plan.registers[role]), models, random.Random(f"{seed}:{role}"), plan.habits[role],
                                                 key=key, hold=(), reference=reference, articulation=x["articulation"], echo_habit=x["echo"],
                                                 recall=models.get("melody_recall"), step_habit=x["steps"], repeat_habit=x["repeats"], plays=plan.plays[role],
                                                 role=role, chord_rate=x.get("chord_tones"), repeat_rate=x.get("repeat_rate"), grain=x.get("grain"), off_scale=x.get("off_scale"), clash_rates=x.get("clashes"),
                                                 tune_sounds=x.get("tune_sounds"), letters=x.get("letters") if role == R.MELODY else None, theme_body=models.get("theme_body"),
                                                 move_profile=(getattr(plan, "step_profiles", None) or {}).get(role),   # the tune's moves held to its token song's (round 130)
                                                 shortest=shortest_beats(plan, role),   # and no note under its token song's shortest usual one (round 136)
                                                 lengths=own_lengths(plan, role), lengths_rng=random.Random(f"{seed}:{role}:note lengths"),   # held as its token song's tune is, on an own stream (round 141)
                                                 places=own_places(plan, role),   # and within its token song's tune's places in the beat (round 147)
                                                 with_kit=tune_kit, kit=kit_hits(plan, song) if tune_kit is not None else None,   # and struck with the kit as often as
                                                                                                                                 # its token song's tune (round 149)
                                                 bounds_at=line_bounds_at(plan, role), recall_moves=models.get("recall_moves"),
                                                 with_lead=tune_lead(plan, song, role, written),   # the tune comes back with the bass as its token song's does (round 146)
                                                 moves_rng=random.Random(f"{seed}:{role}:recall moves"),   # the recalls' places on an own stream (round 100)
                                                 habit_at=habit_at_for(plan, role), envelope_at=envelope_at_for(plan, role))   # the habit and envelope a bar: the tier by the section (round 101)
        if beside and sum(mask_said.values()):              # the counter-line's bars by its part of the form's own onsets (round 143)
            plog.append(f"bars' masks within the balance's song's own onsets for their part of the form (round 143): {sum(mask_said.values()) - mask_said['none']} of {sum(mask_said.values())}"
                        + f"; {mask_said['again']} drawn again, {mask_said['among']} among the table's masks that fit, {mask_said['none']} no mask fits")
        if beside and places_c is not None:                 # and its places in the beat against its token song's line's (round 147)
            plog.append("notes on a quarter of the beat, a third, finer, by the bars' masks: "
                        + ", ".join(f"{line_fine[kind]}/{line_n} ({line_fine[kind] / max(1, line_n):.2f}; " + ("the song's feel's own, not held)" if share is None else f"the balance's song's line {share:.2f})")
                                    for kind, share in zip(rhythm.FINE_PLACES, places_c))
                        + f"; {place_said['moved']} bars' own onsets moved onto them, {place_said['again']} bars' masks drawn again for them"
                        + (f", {place_said['none']} with none that keeps them" if place_said["none"] else "") + " (round 147)")
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
    if R.COUNTER in written and R.MELODY in written:        # the counter-line comes back with the tune as often as its token song's does (round 144)
        under = [x for r in rhythm.UPPER + (R.BASS,) if r in written for x in written[r].notes]
        written[R.COUNTER].log += hold_together(plan, song, R.COUNTER, written[R.COUNTER], written[R.MELODY].notes, held_bars, over=under)
    tune_notes = [x for r in (R.MELODY, R.COUNTER) if r in written for x in written[r].notes]
    for role in rhythm.UPPER:                               # a chord part comes back with the bass as often as its token song's part does (round 144), and
        if role in written:                                 # sounds a chord's pitch classes again as often (round 142): once the tune is written, so the
            if R.BASS in written:                           # tune stands as it was written over the part,
                written[role].log += hold_together(plan, song, role, written[role], written[R.BASS].notes, held_bars, leave=riding.get(role, ()), over=tune_notes)
            written[role].log += hold_chord_tones(plan, song, role, written[role], written[R.BASS].notes if R.BASS in written else (), held_bars,
                                                  leave=riding.get(role, ()), over=tune_notes)   # and before the
    scale = {(plan.tonic + i) % 12 for i in harmony.MODES["major" if plan.mode == "major" else "natural_minor"]}   # voices that follow a line by the token's stretches
    for role, v, own, word, *struck_too in pending:         # the voices beside a line written by the token's stretches (round 90), every line in place
        notes_v = late_stretch_notes(plan, song, role, v, own, word, written, scale, models, random.Random(f"{seed}:{role}:voice {v}:stretch parallel"),
                                     struck_too=bool(struck_too))
        notes_v, looped_v, held_bars[(role, v)] = hold_loop(plan, f"{role}:{v}", notes_v, song.meter)   # its figure again where the token song's voice loops (round 121)
        if looped_v:
            written[role].log.append(f"voice {v + 1}: its figure again, note for note, in {looped_v} bars where the balance's song's voice loops (round 121)")
        song.notes[role] += [(a, b - a, m, role) for a, b, m, *_ in notes_v]
        written[role].notes += notes_v
        written[role].notes.sort(key=lambda n: (n[0], n[3] if len(n) > 3 else 0))
    # every voice under what the SNES chip can play of its sample (round 120): here, beside round 95's fold, so the theme band
    # and the form's repeats copy the voices as folded, and once more on the notes as finally played (the last line)
    hold_under_ceilings(plan, song, written)
    if R.MELODY in written:                                 # the theme in the band: doubled where the tune plays it, carried where it does not
        rng_theme = random.Random(f"{seed}:theme band")
        for line in double_theme(plan, song, written, models, rng_theme, held_bars) + carry_theme(plan, song, written, models, rng_theme, held_bars):
            written[R.MELODY].log.append(line)                # (a part's bars on its loop's figure left as they are, round 121)
    for line in hand_off_cells(plan, song, written, models, random.Random(f"{seed}:handoff"), held_bars):
        written[R.MELODY].log.append(line)
    for line in copy_repeats(plan, song, written):
        for part in written.values():
            part.log.append(line)
    for role, part in written.items():                      # what the theme band, the hand-offs and the form's repeats copied across a
        if role != R.DRUMS and (plan.extras.get(role) or {}).get("stretch_bounds"):   # stretch line goes into its bars' registers too (round 92)
            part.notes[:] = fold_line(plan, role, part.notes, song.meter)
    if R.BASS in written:
        written[R.BASS].log += hold_bass_pitch(plan, song, written, bass_as_written, held=held_bars)   # the bass's pitch continuity as finally played (round 114)
        written[R.BASS].log += double_bass(plan, song, written)   # a second voice that doubles the line: the line as finally played, again (round 126)
    hold_under_ceilings(plan, song, written)               # the notes as finally played: whatever the passes since have moved over a ceiling
    return written


def doubling_own_of(text: str) -> tuple:
    """What a doubling voice does of its own, read from the layer word's words after its interval (round 151,
    arrangement.doubling_own): "doubling +0 sounds 0.10 between -5 0.50" -> (0.1, (-5, 0.5)): the share of the line's
    note its note sounds (None: the line's length), and the interval and the place in the line's gap of a note between
    the line's (None: none)."""
    words = (text or "").split()
    sounds = between = None
    for i, w in enumerate(words):
        try:
            if w == "sounds" and i + 1 < len(words):
                sounds = float(words[i + 1])
            elif w == "between" and i + 2 < len(words):
                between = (int(words[i + 1]), float(words[i + 2]))
        except ValueError:
            pass
    if sounds is not None and not 0 < sounds <= 1:
        sounds = None
    if between is not None and not 0 < between[1] < 1:
        between = None
    return sounds, between


def double_bass(plan: Plan, song: rhythm.Song, written: dict) -> list:
    """A bass's second voice that doubles its line (round 126): the line as finally played, again on the second voice at
    the layer word's interval (in the scale; a unison or an octave the line's notes exactly, `diatonic`). Two of FFVI's
    fifteen two-voice basses are one line on two samples (Returners, Overture part 3), and the bass writer wrote a second
    voice only where the word was a line of its own, so a doubling left the second channel silent (seven of Song Check
    100's songs, the layers word's pooled draw). Written last, after the theme band, the form's repeats and the bass's
    last pass have moved the line, so the double stays the line's. Since round 151 the double does what the token song's
    does of its own (doubling_own_of): its notes sound the song's share of the line's notes they are struck with, and
    in the line's gaps as long as its usual one (the median) or longer it strikes a note between, at the song's
    interval from the line's note and at the song's place in the gap, as long as its other notes there. Overture (part
    3)'s double is a pulse over its line's held note, a tenth as long and a fourth below at the half of the gap; written
    as the line again, both voices held one note through the song's first thirty seconds. Returns a log line."""
    layer = layer_of(plan.extras.get(R.BASS))
    if plan.voices.get(R.BASS, 1) < 2 or layer[0] != "doubling" or R.BASS not in written:
        return []
    part = written[R.BASS]
    line = sorted(n for n in part.notes if n[3] == 0)
    if not line:
        return []
    scale = {(plan.tonic + i) % 12 for i in harmony.MODES["major" if plan.mode == "major" else "natural_minor"]}
    double = diatonic(line, layer[1], scale, 1)
    sounds, between = doubling_own_of((plan.extras.get(R.BASS) or {}).get("layer", ""))
    said = ""
    if sounds is not None:
        double = [(a, a + (b - a) * sounds, m, v) for a, b, m, v in double]
        said += f", each sounding {sounds:.2f} of the line's note"
    if between is not None:
        interval, place = between
        gaps = [y[0] - x[0] for x, y in zip(line, line[1:])]
        usual = statistics.median(gaps) if gaps else 0.0
        extra = []
        for x, y, d in zip(line, line[1:], double):
            gap = y[0] - x[0]
            if gap >= usual - rhythm.NEAR and gap > rhythm.NEAR:
                start = x[0] + place * gap
                extra.append((start, min(start + (d[1] - d[0]), y[0]), float(int(round(d[2])) + interval), 1))
        double += extra
        said += f", and {len(extra)} notes between the line's at {interval:+d} semitones, {place:.2f} of the gap"
    part.notes[:] = sorted(line + double, key=lambda n: (n[0], n[3]))
    song.notes[R.BASS] = [(n[0], n[1] - n[0], n[2], R.BASS) for n in part.notes]
    return [f"voice 2 doubles the line at {layer[1]:+d} semitones, the line as finally played: {len(line)} notes" + said + " (round 126" + ("; round 151)" if said else ")")]


STEP_MARGIN = 0.05                    # how far over its share of the token song's step profile a line's move class may run before the
                                      # note takes the class most under instead (round 117)


def hold_line_steps(plan: Plan, song: rhythm.Song, role: str, notes: list, shared: dict | None, register: tuple) -> tuple:
    """A chord part's line held to the token song's step profile (round 117, plan.step_profiles: the share of its moves that
    repeat the pitch, step within a whole tone, or leap a minor third or more), once the line is written and rides the bass,
    so every move counts as the reader counts them. Each note after the first: its move's class with the note counted over
    its share by STEP_MARGIN gives way to the class most under its share, where one has room: "same" plays the note before
    again, "step" the chord's tone within a whole tone of it (the scale's where the chord has none, the whole tone up else),
    "leap" keeps the note as written (a leap is never forced). The voices beside the line see the held note (`shared`).
    Returns the line's notes and a log line. Battle Theme's guitar repeats its pitch on 0.63 of its moves and leaps on 0.07,
    a chug on A and B-flat; the written guitar, from the figures' chord-tone marks and the walking bass it rides, leaped on
    0.34 and drove the song (Song Check 96)."""
    profile = plan.step_profiles.get(role)
    line = [n for n in notes if len(n) < 4 or n[3] == 0]
    if not profile or len(line) < 2:
        return notes, []
    scale = {(plan.tonic + i) % 12 for i in harmony.MODES["major" if plan.mode == "major" else "natural_minor"]}
    low, high = register
    counts, moved, out, prev = Counter(), 0, [], None
    for n in sorted(line, key=lambda x: x[0]):
        midi = int(round(n[2]))
        if prev is not None:
            cls = rhythm.step_class(midi - prev)
            total = sum(counts.values())
            if (counts[cls] + 1) / (total + 1) > profile.get(cls, 0.0) + STEP_MARGIN:
                room = {k: profile.get(k, 0.0) - counts[k] / (total + 1) for k in rhythm.STEP_CLASSES if k != cls}
                best = max(room, key=lambda k: (room[k], k == "same"))
                if room[best] > 0:
                    c = rhythm._chord_at(song.chords, n[0])
                    chord_pcs = {(c.root + i) % 12 for i in harmony.SHAPES.get(c.shape, harmony.SHAPES[""])} if c is not None and c.root is not None and c.fit >= vocab.FIT else set()
                    new = None
                    if best == "same":
                        new = prev
                    elif best == "step":
                        near = [prev + d for d in (1, -1, 2, -2) if low <= prev + d <= high]
                        new = next((m for m in near if m % 12 in chord_pcs), None) or next((m for m in near if m % 12 in scale), None) or (prev + 2 if prev + 2 <= high else prev - 2)
                    if new is not None and new != midi:
                        midi, moved = new, moved + 1
                    cls = rhythm.step_class(midi - prev)
            counts[cls] += 1
        prev = midi
        out.append((n[0], n[1], float(midi)) + tuple(n[3:]))
        if shared is not None and midi != int(round(n[2])):
            k = int(n[0] // song.meter)
            pos = rhythm.position(n[0] - song.bars[k][0], song.division) if k < len(song.bars) else None
            if pos is not None:
                shared[("line", (k, pos))] = float(midi)
                if ("taken", (k, pos)) in shared:
                    shared[("taken", (k, pos))] = {midi}
    total = sum(counts.values())
    log = [f"the line's steps held to the balance's song's profile (round 117): " + " ".join(f"{k} {counts[k] / total:.2f}" for k in rhythm.STEP_CLASSES)
           + " (the song's " + " ".join(f"{k} {profile.get(k, 0.0):.2f}" for k in rhythm.STEP_CLASSES) + f"); {moved} notes moved"] if total else []
    others = [n for n in notes if len(n) >= 4 and n[3] != 0]
    return sorted(out + others, key=lambda x: (x[0], x[3] if len(x) > 3 else 0)), log


def hold_bass_pitch(plan: Plan, song: rhythm.Song, written: dict, as_written: list, held: dict | None = None) -> list:
    """The bass's pitch continuity as the token song's on the line as finally played (round 114). The bass writer holds it
    (writer.bass, `continuity`), and the theme band, the hand-offs and the form's repeats rewrite bars of the bass after it
    (a fifth of Journey of the Quarry's), each a bar line or two lost, so the bass kept its pitch class across 0.28 of its bar
    lines where the writer had kept 0.53. Here the bars are walked again as the reader counts them (consecutive bars the bass
    plays in, a rest bar breaking the chain): where the share runs under the token song's, with the bar line counted, a bar
    the writer's own notes still stand in is pedaled on the bar before's main pitch class (writer.pedal: the fewest notes
    moved, a passing mark first, the tone classes written kept counted against the token song's profile relative to the bar's
    chord); a bar rewritten after the writer is left as it is. A chord part riding the bass moves with it: its line's note at
    a moved onset on the bass's old pitch class takes the new, and the voices its relation words have following the line
    there (struck with it, parallel, doubling; and theirs) move the same, so what the token said they do beside the line
    holds. Returns a log line."""
    share = getattr(plan, "bass_continuity", None)
    if share is None or R.BASS not in written or not written[R.BASS].notes:
        return []
    part, meter = written[R.BASS], song.meter
    profile = (getattr(plan, "tone_profiles", None) or {}).get(R.BASS)
    bar_of = lambda t: int((t + rhythm.NEAR) // meter)       # noqa: E731
    by_bar, was = {}, {}
    for n in part.notes:
        if n[3] == 0:
            by_bar.setdefault(bar_of(n[0]), []).append(n)
    for n in as_written:
        was.setdefault(bar_of(n[0]), set()).add((round(n[0], 3), int(round(n[2])) % 12))
    rewritten = {k for k, ns in by_bar.items() if {(round(n[0], 3), int(round(n[2])) % 12) for n in ns} != was.get(k, set())}
    held = held or {}                                       # the bars each voice holds on its loop's figure (round 121): left as they are, the
    on_figure = held.get((R.BASS, 0), set())                # bass's own and a riding voice's

    def chord_of(k):
        c = rhythm._chord_at(song.chords, song.bars[k][0]) if k < len(song.bars) else None
        return (c.root % 12, c.shape) if c is not None and c.root is not None and c.fit >= vocab.FIT else (plan.tonic % 12, "")
    counts = Counter()                                      # the line's tone classes as played, for the profile's budget in pedal
    for k, ns in by_bar.items():
        root, shape = chord_of(k)
        for n in ns:
            counts[vocab.tone_of(int(round(n[2])) % 12, root, shape)] += 1
    low, high = plan.bounds.get(R.BASS, plan.registers[R.BASS])

    def followers(role, k):
        """The part's voices (by number) that follow its line in bar k by their relation words: the line's and, in turn, theirs."""
        words = (getattr(plan, "layer_relations", None) or {}).get(role) or []
        target = {}
        for v, word in enumerate(words, start=1):
            if not word:                                    # a voice without a relation word: its own
                continue
            bar = 0
            for kind, who, _, bars in relation_stretches(word):
                end = None if bars is None else bar + bars
                if bar <= k and (end is None or k < end):
                    if kind != "own" and who is not None:
                        target[v] = 0 if who == ("line",) else who[1] if who[0] == "voice" else None
                    break
                bar = end
        out = {0}
        while True:
            more = {v for v, t in target.items() if t in out and v not in out}
            if not more:
                return out - {0}
            out |= more
    prev_main, same, trans, pedaled, moved, riders = None, 0, 0, 0, 0, 0
    for k in range(len(song.bars)):
        ns = by_bar.get(k)
        if not ns:
            prev_main = None                                # a rest bar: no bar line counted across it
            continue
        main = Counter(int(round(n[2])) % 12 for n in ns).most_common(1)[0][0]
        if prev_main is not None:
            if main != prev_main and k not in rewritten and k not in on_figure and (same + 1) / (trans + 1) < share - writer.CONTINUITY_MARGIN:
                out = [(n[0], n[1], n[2]) for n in ns]
                figure = (part.figures[k] if k < len(part.figures) else "").split(" || ")[0]
                marks = {}
                for tok in (rhythm._tokens(figure) if figure and figure != writer.REST else []):
                    pos, _, mark = tok.partition(":")
                    marks[round(song.bars[k][0] + float(Fraction(pos)), 3)] = mark
                old = [int(round(m)) % 12 for _, _, m in out]
                moved += writer.pedal(out, [marks.get(round(s, 3), "") for s, _, _ in out], [chord_of(k)] * len(out), prev_main, low, high, profile, counts)
                gone = {(round(n[0], 3), int(round(n[2]))) for n in ns}
                part.notes[:] = sorted([n for n in part.notes if not (n[3] == 0 and bar_of(n[0]) == k)] + [(s, e, m, 0) for s, e, m in out], key=lambda n: (n[0], n[3]))
                song.notes[R.BASS] = sorted([x for x in song.notes.get(R.BASS, []) if (round(x[0], 3), int(round(x[2]))) not in gone]
                                            + [(s, e - s, m, R.BASS) for s, e, m in out], key=lambda x: x[0])
                for (s, _, m), op in zip(out, old):         # the chord parts riding the bass move with it
                    npc = int(round(m)) % 12
                    if npc == op:
                        continue
                    delta = ((npc - op + 6) % 12) - 6
                    for role in rhythm.UPPER:
                        up = written.get(role)
                        if up is None:
                            continue
                        at = [i for i, x in enumerate(up.notes) if abs(x[0] - s) < rhythm.NEAR]
                        if not any(up.notes[i][3] == 0 and int(round(up.notes[i][2])) % 12 == op for i in at):
                            continue                        # the part's line is not on the bass's pitch here: not riding it
                        voices = {0} | followers(role, k)
                        for i in at:
                            x = up.notes[i]
                            if x[3] not in voices or (x[3] == 0 and int(round(x[2])) % 12 != op) or k in held.get((role, x[3]), ()):
                                continue
                            key = (round(x[0], 3), int(round(x[2])))
                            up.notes[i] = (x[0], x[1], float(x[2] + delta)) + tuple(x[3:])
                            song.notes[role] = [(y[0], y[1], float(y[2] + delta), y[3]) if (round(y[0], 3), int(round(y[2]))) == key else y
                                                for y in song.notes.get(role, [])]
                            riders += 1
                by_bar[k] = [(s, e, m, 0) for s, e, m in out]
                pedaled += 1
                main = prev_main
            trans += 1
            same += main == prev_main
        prev_main = main
    if not trans:
        return []
    return [f"bass pitch as finally played held across bar lines to the balance's song's {share:.2f} (round 114): {same} of {trans} kept; {len(rewritten)} bars "
            f"rewritten after the writer (the theme band, the hand-offs, the repeats)" + (f" and {len(on_figure)} on the loop's figure (round 121)" if on_figure else "")
            + f" left as they are, {pedaled} more bars pedaled, {moved} notes moved, "
            f"{riders} riding notes (and the voices following them) with them"]
