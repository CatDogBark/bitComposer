"""The balance token, read (the refactor after round 178; the record is docs/idiom/phase-4-writing.md).

A written song takes its skeleton from one song's balance token: one line of text, a field a part of the band and a
word for each fact of the song as a whole, written by `rhythm.balance_units` and kept as the `balance` table's outcome.
`read_token` reads that line into a Token: every fact under a name, as `plan._plan_once` goes on to use it. Until this
module the reading was three hundred lines in the middle of that function, each fact a local of it. The text is as it
was: a pack counted by an earlier version reads as it did, a word it lacks left at the value a song without it has.
"""
from __future__ import annotations

import math
import re

from .. import rhythm
from .. import roles as R


class Token:
    """A balance token's facts, each an attribute under the name the plan uses for it: `band` the parts in the token's
    order, `token_song` the id of the song it is, `token_form` its form's letters, and so on, as read_token leaves
    them (its last statement lists every one). The names are attributes and never text here: a kept table's name as a
    string in the writer's source reads as a draw site to tools/vocab_map.py."""

    def __init__(self, **facts):
        self.__dict__.update(facts)


def read_token(text: str, log: list) -> Token:
    """The balance token `text` read: a Token. `log`: the plan's log, which the reading adds its lines to."""
    from .plan import (                                     # noqa: PLC0415  the plan imports this module: its readers are looked up when asked
        BASS_LAYER_KINDS, LOOP_CHORDS, follow_pair, form_of, kit_onsets_of, layer_of, lengths_of, line_pulse_of, line_stretch_list,
        line_turn_moves_of, line_turns_of, loops_of, onsets_of, quals_of, relation_stretches, section_levels_of, shape_profile_of, spans_of,
        step_profile_of, struck_places_of, struck_values_of, tone_profile_of, voice_places_of, voice_rubs_of,
    )
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
    token_struck_places = {}                                # and where in the bar it does, by the form's letters (round 159)
    token_voice_places = {}                                 # where each voice beside a line plays in its bar, by the form's letters (round 166)
    token_turns = {}                                        # where a block line's note changes in the token song, bar by bar (round 160)
    token_turn_moves = {}                                   # and the move it makes there (round 168)
    token_pulse = {}                                        # a moving line by its place in the beat in the token song (round 161)
    token_rubs = {}                                         # how often a voice sits a semitone from its own part in the token song (round 165)
    token_keeps = {}                                        # how often a voice keeps its note where its line keeps its own (round 167)
    token_follows = {}                                      # how far the tune and the counter go with a chord off the key (round 171)
    token_song = ""                                         # the token's song's id (round 172)
    token_gap_shares = {}                                   # a chord part's or the bass's line: the share a note sounds by its gap class (round 95)
    token_kit_channels = []                                # the kit's channels, each one's pieces (round 87)
    token_class, token_top, token_loud = None, None, None
    token_tempo = None                                      # the token's song's own tempo, where the token carries it (round 137)
    token_beat = 1                                          # 2 where the token's song is counted in double time (round 131)
    token_feel = rhythm.FEELS[0]                            # the token's song's feel (round 147): duple where the token does not say
    token_loop = None                                       # the part of its form the token's song's loop returns to (round 132)
    for token in text.split():
        role, _, rest = token.partition("=")
        if role == "loop":                                  # the part of its form the token's song's loop returns to (round 132), not a part
            token_loop = int(rest) if rest.isdigit() else None
            continue
        if role == "follows":                               # how far the token's song's tune and counter go with a chord off the key (round 171)
            by = {v: k for k, v in rhythm.FOLLOW_LETTERS.items()}
            for w in rest.split(","):
                pair = follow_pair(w[1:], 100)
                if w[:1] in by and pair:
                    token_follows[by[w[:1]]] = pair
            continue
        if role == "keeps":                                 # how often the token's song's voices keep their note with their line (round 167)
            token_keeps = voice_rubs_of(rest)
            continue
        if role == "rubs":                                  # how often the token's song's voices sit a semitone from their own part (round 165)
            token_rubs = voice_rubs_of(rest)
            continue
        if role == "pulse":                                 # the token's song's moving lines by their place in the beat (round 161), not a part
            token_pulse = line_pulse_of(rest)
            continue
        if role == "turns":                                 # where the token's song's block lines turn (round 160), not a part
            token_turns = line_turns_of(rest)
            token_turn_moves = line_turn_moves_of(rest)
            continue
        if role == "struck":                                # where the token's song's struck voices strike (round 159), not a part
            token_struck_places = struck_places_of(rest)
            token_voice_places = voice_places_of(rest)      # the same word: every voice beside a line (round 166)
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
        if role == "song":                                  # which song the token is (round 172), not a part
            token_song = rest
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
            f = rhythm.PartFields(rest)                     # the part's fields by name (rhythm.PART_FIELDS)
            if f.weight:
                weights[role] = f.weight
            if "-" in f.register:        # the song's layout, note lengths, voices and levels a part come with its balance
                lo, hi = f.register.split("-")
                layout[role] = (int(lo), int(hi))
            if f.sounds:
                head, _, by_gap = f.sounds.partition("@")   # the line voice's sounded share, and since round 95 its share by gap class
                shares[role] = float(head)
                if by_gap:
                    token_gap_shares[role] = {g: (float(x) if x not in ("", "-") else None) for (_, g), x in zip(rhythm.GAP_CLASSES, by_gap.split("/"))}
            if f.voices:
                if role == R.DRUMS:                         # the kit's channels (round 87): the pieces each game channel plays, "KS|h"
                    token_kit_channels = f.voices.split("|")
                else:
                    counts[role] = int(f.voices)
            if f.level and math.isfinite(float(f.level)):   # a "nan" level (tables counted before the
                token_levels[role] = float(f.level)                             # readings skipped a kit's unread levels) falls to the levels draw
            if f.layers:               # the voices beyond the line, the busiest first, each over the line's level; since
                parts_ = [x.split("@") for x in f.layers.split("/")]   # round 65 with each one's sample and its notes over the line's
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
            if f.kind:               # the counter's kind: on the tune's sample or another (round 39)
                token_kinds[role] = f.kind
            if f.sample and role == R.DRUMS:   # the song's kit (round 63): a piece letter and its sample, by the comma;
                for x in f.sample.split(","):                       # since round 68 each piece's own level after an "@", where its song read one
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
            elif f.sample:             # the part's own sample (round 60): the song's instruments with its levels,
                sid, _, played = f.sample.partition("@")   # and since round 86 the range the song plays it over ("s1d296a2572@32-52")
                token_samples[role] = sid
                if "-" in played:
                    token_sample_ranges[role] = tuple(int(x) for x in played.split("-"))
            if f.habit:               # the part's habit (round 62): the song's density tiers together
                token_habits[role] = f.habit.replace("+", " ")
            if f.pans:               # the part's voices' pans (round 84): the line's first, then the voices beyond it;
                token_pans[role] = [float(x) if re.fullmatch(r"[0-9.]+", x) else x for x in f.pans.split("/")]   # a voice's two
                                                            # places kept as written, "0.60x5|0.45x13" or "0.35x4>0.65" (round 85, render.pan_of)
            if f.stretches:             # the line's instrument by stretch (round 91): each stretch's sample, range and bars
                token_stretches[role] = line_stretch_list(f.stretches)
            if f.motion:             # the line's motion (round 103): block, mixed or arpeggiated, the token song's own
                token_motions[role] = f.motion
            if f.tone_tier:             # the line's off-chord tier (round 103): rare, some or many, the token song's own
                token_tone_tiers[role] = f.tone_tier
            if f.period:             # the part's own period and hold share (round 106): `p2/83`
                m_ = re.fullmatch(r"p(\d+)/(\d+)", f.period)
                if m_:
                    token_periods[role] = (int(m_.group(1)), int(m_.group(2)) / 100)
            if f.rides:             # how far the line rides the bass (round 106): `b75/70`, onsets with it / at its pitch class
                m_ = re.fullmatch(r"b(\d+)/(\d+)", f.rides)
                if m_:
                    token_rides[role] = (int(m_.group(1)) / 100, int(m_.group(2)) / 100)
            if f.continuity and role == R.BASS:   # the bass line's pitch continuity (round 114): `k58`
                m_ = re.fullmatch(r"k(\d+)", f.continuity)
                if m_:
                    token_continuity = int(m_.group(1)) / 100
                    log.append(f"the bass keeps its pitch class across {token_continuity:.2f} of its bar lines in the balance's song")
            if f.tones:             # the line's chord-tone profile (round 111): `t45/2/9/30/2/12`
                prof = tone_profile_of(f.tones)
                if prof:
                    token_profiles[role] = prof
                    log.append(f"{role}'s line plays the balance's song's chord tones: " + " ".join(f"{k} {v:.2f}" for k, v in prof.items()))
            if f.steps:             # the line's step profile (round 117): `j63/24/13`
                steps = step_profile_of(f.steps)
                if steps:
                    token_steps[role] = steps
                    log.append(f"{role}'s line moves as the balance's song's: " + " ".join(f"{k} {v:.2f}" for k, v in steps.items()))
            if f.loops.startswith("l") and loops_of(f.loops[1:]):   # the line's loops, the kit's (round 121): `lB1~100`
                token_loops[role] = loops_of(f.loops[1:])
            if f.company.startswith("r") and any(st[0] != "own" for st in relation_stretches(f.company[1:])):   # where the line
                token_line_company[role] = f.company[1:]   # doubles the bass, by stretch (round 123): `rdb+12x2>ox8>db+12`
            if f.spans.startswith("e") and spans_of(f.spans[1:]):   # the parts of the form the part sounds
                token_spans[role] = spans_of(f.spans[1:])   # in, with its entrances (round 124): `eA+B2.0+D0.4`
            if role == R.BASS and re.fullmatch(r"d\d+", f.downbeat):   # how often the bass strikes a bar's first beat on the
                token_downbeat = int(f.downbeat[1:]) / 100   # chord's root (round 129): `d73`
                log.append(f"the bass strikes a bar's first beat on the chord's root in {token_downbeat:.2f} of its bars in the balance's song")
            if role in rhythm.UPPER + (R.BASS,) and re.fullmatch(r"f\d+", f.first):   # how often the part strikes a
                token_first[role] = int(f.first[1:]) / 100   # bar's first beat: the bass (round 133), a chord part (round 135): `f93`
                log.append(f"the {role} strikes a bar's first beat in {token_first[role]:.2f} of its bars in the balance's song")
            if role in (R.MELODY, R.COUNTER) and re.fullmatch(r"m\d+", f.shortest) and int(f.shortest[1:]) > 0:   # a tune's
                token_shortest[role] = int(f.shortest[1:])  # shortest usual note (round 136): `m150`
                log.append(f"the {role}'s shortest usual note sounds {token_shortest[role]} ms in the balance's song")
            if role in (R.MELODY, R.COUNTER) and f.lengths.startswith("h") and lengths_of(f.lengths[1:]):   # how the tune
                token_lengths[role] = lengths_of(f.lengths[1:])   # sounds its notes, by the gap (round 141): `h50~0.90~0.40/-/26~0.90~0.55/...`
                log.append(f"the {role} holds {token_lengths[role][rhythm.LENGTH_WHOLE][0]:.2f} of its notes in the balance's song; its note lengths by the gap (round 141): {f.lengths[1:]}")
            if role in rhythm.UPPER and re.fullmatch(r"c\d+/\d+", f.tones_kept):   # how often a chord part sounds again
                token_tones[role] = tuple(int(x) / 100 for x in f.tones_kept[1:].split("/"))   # the pitch classes it played on a chord before, and
                log.append(f"the {role} sounds an earlier bar's pitch classes on a chord again in {token_tones[role][0]:.2f} of such bars in the balance's song, "   # how often the bar before's
                           f"the bar before's in {token_tones[role][1]:.2f} of those (round 142)")   # (round 142): `c60/47`
            if role in rhythm.UPPER + (R.COUNTER,) and re.fullmatch(r"w\d+", f.together):   # how often it plays an earlier bar
                token_together[role] = int(f.together[1:]) / 100   # again where its lead does (round 144): `w66`
                log.append(f"the {role} plays an earlier bar again where the {'tune' if role == R.COUNTER else 'bass'} does in {token_together[role]:.2f} of such bars in the balance's song (round 144)")
            if role in (R.MELODY, R.COUNTER) and re.fullmatch(r"w(\d+|-)/(\d+|-)/\d+", f.together):   # the tune: how often it
                token_tune_together[role] = tuple(None if x == "-" else int(x) / 100 for x in f.together[1:].split("/"))   # plays an earlier bar again
                far, near, overall = token_tune_together[role]   # where the bass brings one back from further off, where it stands on the bar before,
                said = lambda x: "by no count (under four such bars)" if x is None else f"in {x:.2f} of such bars"   # noqa: E731    # and how often
                log.append(f"the {role} plays an earlier bar again where the bass plays one from further back again {said(far)} in the balance's song, "   # at all (round
                           f"where it plays the bar before again {said(near)}, and an earlier bar again in {overall:.2f} of its bars (round 146)")   # 146): `w48/-/29`
            if role in rhythm.PLACE_PARTS and re.fullmatch(r"p\d+/\d+/\d+(/\d+)?", f.places):   # where in the beat a tune's
                token_places[role] = tuple(int(x) / 100 for x in f.places[1:].split("/"))   # notes fall (round 147): `p12/0/3`, and since round 169
                log.append(f"the {role} plays {token_places[role][0]:.2f} of its notes on a quarter of the beat in the balance's song, {token_places[role][1]:.2f} on a third, "   # the half
                           f"{token_places[role][2]:.2f} finer (round 147)"                                                                                                   # beat: `p12/0/3/20`
                           + (f", {token_places[role][3]:.2f} on the half beat (round 169)" if len(token_places[role]) > 3 else ""))
            if re.fullmatch(r"x\d+/\d+" if role == R.BASS else r"x\d+", f.with_kit) and role in rhythm.KIT_PARTS:   # how often its
                token_with_kit[role] = tuple(int(x) / 100 for x in f.with_kit[1:].split("/"))   # notes are struck with the kit (round 149): `x100/84`, `x91`
                log.append(f"the {role} strikes {token_with_kit[role][0]:.2f} of its notes with a kit hit in the balance's song"
                           + (f", and {token_with_kit[role][1]:.2f} of the kit's hits carry a bass note" if role == R.BASS else "") + " (round 149)")
            if role != R.DRUMS and section_levels_of(f.section_levels):   # its level in each part of the form over its level in
                token_section_levels[role] = section_levels_of(f.section_levels)   # the song (round 150): `vA1.0+B0.4`
            if f.onsets.startswith("n"):   # how busy it is in each (round 125): the line's onsets a bar `nA6+B2!1`,
                if role == R.DRUMS:                         # the kit's pieces' hits a bar `nAS28.5@100,c1@50`
                    token_kit_onsets = kit_onsets_of(f.onsets[1:])
                elif onsets_of(f.onsets[1:]):
                    token_onsets[role] = onsets_of(f.onsets[1:])
    return Token(
        band=band, counts=counts, layout=layout, shares=shares, token_beat=token_beat, token_class=token_class, token_continuity=token_continuity,
        token_downbeat=token_downbeat, token_echo=token_echo, token_feel=token_feel, token_first=token_first, token_follows=token_follows,
        token_form=token_form, token_gap_shares=token_gap_shares, token_habits=token_habits, token_holds=token_holds, token_keeps=token_keeps,
        token_key=token_key, token_kinds=token_kinds, token_kit=token_kit, token_kit_channels=token_kit_channels,
        token_kit_classes=token_kit_classes, token_kit_degrees=token_kit_degrees, token_kit_echo=token_kit_echo, token_kit_holds=token_kit_holds,
        token_kit_levels=token_kit_levels, token_kit_onsets=token_kit_onsets, token_kit_pans=token_kit_pans, token_kit_pitches=token_kit_pitches,
        token_kit_rates=token_kit_rates, token_kit_seconds=token_kit_seconds, token_kit_tuned=token_kit_tuned, token_layer_onsets=token_layer_onsets,
        token_layer_ranges=token_layer_ranges, token_layer_relations=token_layer_relations, token_layer_samples=token_layer_samples,
        token_layer_shares=token_layer_shares, token_layer_stretches=token_layer_stretches, token_layer_struck=token_layer_struck,
        token_layer_words=token_layer_words, token_layers=token_layers, token_lengths=token_lengths, token_levels=token_levels,
        token_line_company=token_line_company, token_loop=token_loop, token_loops=token_loops, token_loud=token_loud, token_motions=token_motions,
        token_onsets=token_onsets, token_pans=token_pans, token_periods=token_periods, token_places=token_places, token_profiles=token_profiles,
        token_pulse=token_pulse, token_quals=token_quals, token_rides=token_rides, token_rubs=token_rubs, token_sample_ranges=token_sample_ranges,
        token_samples=token_samples, token_section_levels=token_section_levels, token_shapes=token_shapes, token_shortest=token_shortest,
        token_song=token_song, token_spans=token_spans, token_steps=token_steps, token_stretches=token_stretches,
        token_struck_places=token_struck_places, token_tempo=token_tempo, token_together=token_together, token_tone_tiers=token_tone_tiers,
        token_tones=token_tones, token_top=token_top, token_tune_together=token_tune_together, token_turn_moves=token_turn_moves,
        token_turns=token_turns, token_voice_places=token_voice_places, token_with_kit=token_with_kit, weights=weights,
    )
