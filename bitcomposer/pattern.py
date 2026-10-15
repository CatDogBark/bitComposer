"""
Pattern-level utilities: note application, effects, drums, and sustain management.
"""

import random

from .it_format import (
    ITPattern, ITNote, midi_to_it_note, NOTE_CUT, NOTE_OFF,
    FX_VIBRATO, FX_PORTAMENTO, FX_VOLUME_SLIDE,
    FX_ARPEGGIO, arpeggio_param,
)


# ── Channel assignments ──

CH_MELODY = 0
CH_HARMONY = 1
CH_HARMONY2 = 2
CH_HARMONY3 = 3
CH_BASS = 4
CH_ARP = 5
CH_KICK = 6
CH_SNARE = 7
CH_HIHAT = 8
CH_TOM = 9
CH_CRASH = 10
CH_OPEN_HAT = 11
# Echo returns of the lead. The SNES fed its mix through a hardware delay; a
# tracker fakes that with a delayed, quieter copy of the part on its own
# channel. Two taps give the feedback repeat.
CH_ECHO1 = 12
CH_ECHO2 = 13

NUM_CHANNELS = 14
ROWS_PER_PATTERN = 64

# Timing grid. IT plays 4 rows per quarter note at the speed/tempo pairing we
# write, so one bar of 4/4 is 16 rows and a 64-row pattern holds 4 bars.
# Drum templates are 16 steps of one 16th note each — one step per row.
ROWS_PER_BEAT = 4
ROWS_PER_BAR = 16
ROWS_PER_STEP = 1
BARS_PER_PATTERN = ROWS_PER_PATTERN // ROWS_PER_BAR

# Tonal channels that can ring (drums naturally stop)
TONAL_CHANNELS = [CH_MELODY, CH_HARMONY, CH_HARMONY2, CH_HARMONY3, CH_BASS, CH_ARP,
                  CH_ECHO1, CH_ECHO2]


# ── Note endings ──

# Sample indices (1-based) whose sample has a sustain loop and a release
# tail. Set per song by the composer. A note on one of these ends with a
# note-off, which lets the tail play; anything else still gets a hard cut.
RELEASE_INSTRUMENTS: set[int] = set()


def end_note(instrument: int) -> int:
    """The note value that ends a note on this instrument: NOTE_OFF for a
    voice with a release tail, NOTE_CUT otherwise."""
    return NOTE_OFF if instrument in RELEASE_INSTRUMENTS else NOTE_CUT


# ── Note application ──

def humanize_volume(base_volume: int, amount: int = 6,
                    rng: random.Random | None = None) -> int:
    """Add subtle random velocity variation to a note."""
    variation = (rng or random).randint(-amount, amount)
    return max(1, min(64, base_volume + variation))


def apply_notes_to_pattern(pattern: ITPattern, channel: int,
                           note_list: list[tuple[int, int]],
                           instrument: int, volume: int = 255,
                           effect: int = 0, effect_val: int = 0,
                           humanize: bool = False,
                           rng: random.Random | None = None):
    """Write note events into a pattern channel.

    Note-cut events are signaled by midi_note == -1. `rng` is the stream
    humanisation draws from; the melody passes its own so that the number of
    melody notes does not shift the global stream for every later part.
    """
    for row, midi_note in note_list:
        if 0 <= row < pattern.rows:
            if midi_note == -1:
                # End of the previous note: a release where the voice has one.
                pattern.data[row][channel] = ITNote(note=end_note(instrument))
                continue
            it_note = midi_to_it_note(midi_note)
            vol = volume
            if humanize and vol != 255:
                vol = humanize_volume(vol, rng=rng)
            pattern.data[row][channel] = ITNote(
                note=it_note,
                instrument=instrument,
                volume=vol,
                effect=effect,
                effect_val=effect_val,
            )


# ── Effects ──

def apply_vibrato(pattern: ITPattern, channel: int,
                  note_list: list[tuple[int, int]], speed: int = 4, depth: int = 3,
                  onset_delay: int = 3):
    """Add vibrato to a note once it has been held for onset_delay rows.

    Starting on the row straight after the note-on put vibrato on 62% of every
    melody row, so each note wobbled from the instant it sounded and short
    notes wobbled too. Real playing lets a note speak first and only sustained
    ones get vibrato, so delay the onset and leave short notes clean.
    """
    vibrato_val = ((speed & 0x0F) << 4) | (depth & 0x0F)
    for i, (row, midi_note) in enumerate(note_list):
        # Note-cuts silence the channel, so there is nothing to modulate after
        # one — writing vibrato there was decorating silence.
        if midi_note == -1:
            continue
        next_row = note_list[i + 1][0] if i + 1 < len(note_list) else pattern.rows
        for r in range(row + 1 + onset_delay, min(next_row, pattern.rows)):
            if pattern.data[r][channel].note == 0:  # Don't overwrite note events
                pattern.data[r][channel] = ITNote(
                    effect=FX_VIBRATO,
                    effect_val=vibrato_val,
                )


def apply_chord_arpeggio(pattern: ITPattern, channel: int,
                         note_list: list[tuple[int, int]],
                         chord_notes: list[int]):
    """Give single-voice harmony the Jxy arpeggio so it sounds like a chord.

    J is the defining tracker/chiptune effect — one channel cycling through
    chord tones fast enough to read as a chord — and the generator emitted
    none at all. Applied where the harmony is thin, so a lone voice still
    states the full harmony.
    """
    for row, midi_note in note_list:
        if midi_note == -1 or not (0 <= row < pattern.rows):
            continue
        cell = pattern.data[row][channel]
        if cell.note == 0 or cell.effect != 0:
            continue
        cell.effect = FX_ARPEGGIO
        cell.effect_val = arpeggio_param(midi_note, chord_notes)


def echo_send_rows(pattern: ITPattern, src: int, hold: int = 0, rest: int = 0) -> set[int]:
    """Rows of src's note-ons that the echo should carry.

    The SNES echoed every note a voice played; we can choose. With hold and
    rest both 0 every note is sent. Otherwise a note is sent when it is held
    for at least `hold` rows or is followed by a rest of at least `rest`
    rows, so held notes and phrase endings get a tail and fast runs stay dry.
    """
    events = [r for r in range(pattern.rows) if pattern.data[r][src].note != 0]
    sent = set()
    for i, r in enumerate(events):
        if pattern.data[r][src].note in (NOTE_CUT, NOTE_OFF):
            continue
        end = events[i + 1] if i + 1 < len(events) else pattern.rows
        if hold == 0 and rest == 0:
            sent.add(r)
            continue
        if end - r >= hold:
            sent.add(r)
            continue
        if rest and end < pattern.rows and pattern.data[end][src].note in (NOTE_CUT, NOTE_OFF):
            after = events[i + 2] if i + 2 < len(events) else pattern.rows
            if after - end >= rest:
                sent.add(r)
    return sent


def plan_echo(pattern: ITPattern, src: int, taps, hold: int = 0, rest: int = 0
              ) -> dict[int, list[tuple[int, ITNote]]]:
    """Echo events for src, on a timeline that runs past the pattern's end.

    `taps` is a list of (dst_channel, delay_rows, level, inst_map); inst_map
    maps a source instrument to the (darker) one the tap plays, or is None.
    Several taps may share a channel: where two land on one row the louder
    wins, and a copy's end (the source note's cut, note-off or next note-on,
    shifted by the delay) is written only while that copy still owns the
    channel, so a later tap never cuts an earlier one short.

    Returns {dst_channel: [(row, ITNote)]} with rows that may be >= rows;
    apply_echo keeps the in-pattern part and apply_echo_spill the rest.
    """
    events = [r for r in range(pattern.rows) if pattern.data[r][src].note != 0]
    sent = echo_send_rows(pattern, src, hold, rest)
    by_channel: dict[int, list] = {}
    for i, r in enumerate(events):
        if r not in sent:
            continue
        cell = pattern.data[r][src]
        end = events[i + 1] if i + 1 < len(events) else pattern.rows
        end_cell = pattern.data[end][src] if end < pattern.rows else None
        vol = cell.volume if cell.volume != 255 else 64
        for dst, delay, level, inst_map in taps:
            inst = (inst_map or {}).get(cell.instrument, cell.instrument)
            if end_cell is not None and end_cell.note in (NOTE_CUT, NOTE_OFF):
                end_note_value = end_cell.note
            else:
                end_note_value = end_note(inst)
            by_channel.setdefault(dst, []).append(
                (r + delay, level, ITNote(note=cell.note, instrument=inst,
                                           volume=max(1, int(vol * level))),
                 end + delay, end_note_value))
    out: dict[int, list[tuple[int, ITNote]]] = {}
    for dst, items in by_channel.items():
        items.sort(key=lambda t: (t[0], -t[1]))
        chosen = []
        for item in items:
            if chosen and chosen[-1][0] == item[0]:
                continue                      # same row: the louder tap was first
            chosen.append(item)
        evs = []
        for k, (row, _, note, end_row, end_value) in enumerate(chosen):
            evs.append((row, note))
            next_row = chosen[k + 1][0] if k + 1 < len(chosen) else None
            if next_row is None or end_row < next_row:
                evs.append((end_row, ITNote(note=end_value)))
        out[dst] = evs
    return out


def apply_echo_taps(pattern: ITPattern, src: int, taps, hold: int = 0, rest: int = 0):
    """Write the echo of src into the pattern for every tap (see plan_echo).

    Events past the pattern end are dropped: patterns are shared between
    order positions, so a tail cannot spill into whichever one happens to
    come next (apply_echo_spill_taps handles the safe cases).
    """
    for dst, evs in plan_echo(pattern, src, taps, hold, rest).items():
        for row, note in evs:
            if row < pattern.rows:
                pattern.data[row][dst] = note


def apply_echo_spill_taps(prev: ITPattern, cur: ITPattern, src: int, taps,
                          hold: int = 0, rest: int = 0):
    """Write the echo of prev's last notes into the start of cur.

    apply_echo_taps drops events that fall past the pattern end, so the echo
    went silent for the last beats of every pattern. The composer calls this
    for consecutive patterns whose second member has a single predecessor,
    where writing into it cannot be wrong for any other order position.
    cur's own events win: nothing here overwrites a cell already in use.
    """
    for dst, evs in plan_echo(prev, src, taps, hold, rest).items():
        for row, note in evs:
            target = row - prev.rows
            if 0 <= target < cur.rows and cur.data[target][dst].note == 0:
                cur.data[target][dst] = note


def apply_echo(pattern: ITPattern, src: int, dst: int,
               delay_rows: int, level: float, inst_map=None,
               hold: int = 0, rest: int = 0):
    """One tap: copy src's notes onto dst, delay_rows later, scaled to level."""
    apply_echo_taps(pattern, src, [(dst, delay_rows, level, inst_map)], hold, rest)


def apply_echo_spill(prev: ITPattern, cur: ITPattern, src: int, dst: int,
                     delay_rows: int, level: float, inst_map=None,
                     hold: int = 0, rest: int = 0):
    """One tap's spill into the next pattern (see apply_echo_spill_taps)."""
    apply_echo_spill_taps(prev, cur, src, [(dst, delay_rows, level, inst_map)], hold, rest)


def apply_portamento(pattern: ITPattern, channel: int,
                     note_list: list[tuple[int, int]],
                     instrument: int, volume: int = 255,
                     porta_speed: int = 32, humanize: bool = False):
    """Write notes with tone portamento — slides between consecutive notes."""
    for i, (row, midi_note) in enumerate(note_list):
        if 0 <= row < pattern.rows:
            it_note = midi_to_it_note(midi_note)
            vol = volume
            if humanize and vol != 255:
                vol = humanize_volume(vol)
            if i == 0:
                # First note: play normally
                pattern.data[row][channel] = ITNote(
                    note=it_note, instrument=instrument, volume=vol,
                )
            else:
                # Subsequent notes: slide to them
                pattern.data[row][channel] = ITNote(
                    note=it_note, instrument=instrument, volume=vol,
                    effect=FX_PORTAMENTO, effect_val=porta_speed,
                )


def apply_harmony_fade(pattern: ITPattern, channel: int,
                       note_list: list[tuple[int, int]], fade_rate: int = 2,
                       hold_rows: int = 0):
    """Add volume slide down after each harmony note-on so notes decay naturally.

    hold_rows delays the slide: a pad should sit at level and only come down
    just before the next hit. With a per-row slide from the first row, a
    sustain chord written at volume 20 was silent after 20 rows of a 32-row
    hold and then re-attacked out of nothing — heard as the pad cutting out.
    """
    for row, midi_note in note_list:
        if midi_note == -1 or row < 0 or row >= pattern.rows:
            continue
        # Apply volume slide down on rows after the note-on until next event
        for r in range(row + 1 + hold_rows, pattern.rows):
            cell = pattern.data[r][channel]
            # Stop if we hit another note or note-cut on this channel
            if cell.note != 0:
                break
            if cell.effect == 0:
                cell.effect = FX_VOLUME_SLIDE
                cell.effect_val = fade_rate  # 0x0y = slide down by y per tick


def apply_fade(pattern: ITPattern, channel: int, fade_in: bool = False,
               fade_out: bool = False, rows_count: int = 8):
    """Fade a channel in over the first rows_count rows or out over the last.

    The volume column of each note-on inside the window is scaled, so new
    notes come in at the faded level, and empty rows get a volume slide so
    held notes move too. The previous version only wrote slides: a slide-up
    on notes that already carried their full volume made the intro *louder*
    than the song, and a slide-down was undone by the next note's volume
    column, so fade-outs stepped back up every beat.
    """
    def scale_note(cell: ITNote, factor: float):
        if cell.note == 0 or cell.note in (NOTE_CUT, NOTE_OFF):
            return
        base = cell.volume if cell.volume != 255 else 64
        cell.volume = max(1, min(64, int(round(base * factor))))

    if fade_in:
        n = min(rows_count, pattern.rows)
        for r in range(n):
            cell = pattern.data[r][channel]
            scale_note(cell, (r + 1) / n)
            if cell.note == 0 and cell.effect == 0:
                cell.effect = FX_VOLUME_SLIDE
                cell.effect_val = 0x10  # slide up 1 per tick
    if fade_out:
        n = min(rows_count, pattern.rows)
        start = pattern.rows - n
        for r in range(start, pattern.rows):
            cell = pattern.data[r][channel]
            scale_note(cell, 1.0 - (r - start) / n)
            if cell.note == 0 and cell.effect == 0:
                cell.effect = FX_VOLUME_SLIDE
                cell.effect_val = 0xF1  # fine slide down 1 per row


# ── Sustain management ──

def apply_sustain_safety_net(pat: ITPattern, channels: list[int] | None = None,
                             max_ring: int = 12):
    """Ensure no tonal note rings more than max_ring rows without a cut.

    Catches any generator that forgets to add note-cuts.
    """
    if channels is None:
        channels = [CH_MELODY, CH_HARMONY, CH_HARMONY2, CH_HARMONY3, CH_ARP,
                    CH_ECHO1, CH_ECHO2]
    for ch in channels:
        last_note_row = None
        last_inst = 0
        for row in range(pat.rows):
            cell = pat.data[row][ch]
            if cell.note != 0:  # any note event (including cuts) resets
                if cell.note == NOTE_CUT or cell.note == NOTE_OFF:
                    last_note_row = None
                else:
                    last_note_row = row
                    last_inst = cell.instrument
            elif last_note_row is not None and (row - last_note_row) == max_ring:
                pat.data[row][ch] = ITNote(note=end_note(last_inst))
                last_note_row = None


def _pattern_last_note_rings(pat: ITPattern, ch: int) -> int:
    """If a channel's last event is a note (not a cut), return its instrument
    (so it rings past the pattern end); 0 otherwise."""
    last_inst = 0
    for row in range(pat.rows):
        cell = pat.data[row][ch]
        if cell.note == NOTE_CUT or cell.note == NOTE_OFF:
            last_inst = 0
        elif cell.note != 0:
            last_inst = cell.instrument or -1
    return last_inst


def silence_inactive_channels(orders: list[int], patterns: list[ITPattern]):
    """Insert NOTE_CUT at row 0 to prevent notes ringing across pattern boundaries.

    If a channel had a ringing note in the previous pattern and the current
    pattern has no early event on that channel, insert a cut at row 0.

    The cut is written into the pattern itself. A pattern can sit at several
    order positions, but a cut on a channel that is silent for its first
    max_ring rows is harmless wherever it plays — it either stops something
    that was ringing in or stops nothing. The old deep-copy-per-order approach
    left every song carrying orphaned, unplayed patterns and defeated the
    order-list reuse the composer works to produce.
    """
    max_ring = 12  # match the in-pattern safety net

    for ord_idx in range(1, len(orders)):
        prev_pat = patterns[orders[ord_idx - 1]]
        cur_pat = patterns[orders[ord_idx]]

        for ch in TONAL_CHANNELS:
            ringing = _pattern_last_note_rings(prev_pat, ch)
            if not ringing:
                continue
            has_early_event = any(
                cur_pat.data[row][ch].note != 0
                for row in range(min(max_ring, cur_pat.rows)))
            if not has_early_event:
                # Keep whatever effect the cell carried (a fade slide, say).
                cur_pat.data[0][ch].note = end_note(ringing)
                cur_pat.data[0][ch].instrument = 0
                cur_pat.data[0][ch].volume = 255
