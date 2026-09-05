"""
Pattern-level utilities: note application, effects, drums, and sustain management.
"""

import copy
import random

from . import theory
from . import structure as struct
from .it_format import (
    ITPattern, ITNote, midi_to_it_note, NOTE_CUT, NOTE_OFF,
    FX_VIBRATO, FX_PORTAMENTO, FX_VOLUME_SLIDE,
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

NUM_CHANNELS = 12
ROWS_PER_PATTERN = 64

# Timing grid. IT plays 4 rows per quarter note at the speed/tempo pairing we
# write, so one bar of 4/4 is 16 rows and a 64-row pattern holds 4 bars.
# Drum templates are 16 steps of one 16th note each — one step per row.
ROWS_PER_BEAT = 4
ROWS_PER_BAR = 16
ROWS_PER_STEP = 1
BARS_PER_PATTERN = ROWS_PER_PATTERN // ROWS_PER_BAR

# Map layer keys to the channels they control
LAYER_CHANNELS = {
    "melody":  [CH_MELODY],
    "harmony": [CH_HARMONY, CH_HARMONY2, CH_HARMONY3],
    "bass":    [CH_BASS],
    "arp":     [CH_ARP],
    "drums":   [CH_KICK, CH_SNARE, CH_HIHAT, CH_TOM, CH_CRASH, CH_OPEN_HAT],
}

# Tonal channels that can ring (drums naturally stop)
TONAL_CHANNELS = [CH_MELODY, CH_HARMONY, CH_HARMONY2, CH_HARMONY3, CH_BASS, CH_ARP]


# ── Note application ──

def humanize_volume(base_volume: int, amount: int = 6) -> int:
    """Add subtle random velocity variation to a note."""
    variation = random.randint(-amount, amount)
    return max(1, min(64, base_volume + variation))


def apply_notes_to_pattern(pattern: ITPattern, channel: int,
                           note_list: list[tuple[int, int]],
                           instrument: int, volume: int = 255,
                           effect: int = 0, effect_val: int = 0,
                           humanize: bool = False):
    """Write note events into a pattern channel.

    Note-cut events are signaled by midi_note == -1.
    """
    for row, midi_note in note_list:
        if 0 <= row < pattern.rows:
            if midi_note == -1:
                # Note-cut event
                pattern.data[row][channel] = ITNote(note=NOTE_CUT)
                continue
            it_note = midi_to_it_note(midi_note)
            vol = volume
            if humanize and vol != 255:
                vol = humanize_volume(vol)
            pattern.data[row][channel] = ITNote(
                note=it_note,
                instrument=instrument,
                volume=vol,
                effect=effect,
                effect_val=effect_val,
            )


# ── Effects ──

def apply_vibrato(pattern: ITPattern, channel: int,
                  note_list: list[tuple[int, int]], speed: int = 4, depth: int = 3):
    """Add vibrato continuation to rows after note-on events."""
    vibrato_val = ((speed & 0x0F) << 4) | (depth & 0x0F)
    for i, (row, _) in enumerate(note_list):
        # Get duration until next note or end of pattern
        next_row = note_list[i + 1][0] if i + 1 < len(note_list) else pattern.rows
        # Add vibrato on rows after the note-on (note-on row already has effect from apply_notes)
        for r in range(row + 1, min(next_row, pattern.rows)):
            if pattern.data[r][channel].note == 0:  # Don't overwrite note events
                pattern.data[r][channel] = ITNote(
                    effect=FX_VIBRATO,
                    effect_val=vibrato_val,
                )


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
                       note_list: list[tuple[int, int]], fade_rate: int = 2):
    """Add volume slide down after each harmony note-on so notes decay naturally."""
    for row, midi_note in note_list:
        if midi_note == -1 or row < 0 or row >= pattern.rows:
            continue
        # Apply volume slide down on rows after the note-on until next event
        for r in range(row + 1, pattern.rows):
            cell = pattern.data[r][channel]
            # Stop if we hit another note or note-cut on this channel
            if cell.note != 0:
                break
            if cell.effect == 0:
                cell.effect = FX_VOLUME_SLIDE
                cell.effect_val = fade_rate  # 0x0y = slide down by y per tick


def apply_fade(pattern: ITPattern, channel: int, fade_in: bool = False,
               fade_out: bool = False, rows_count: int = 8):
    """Add volume fade in/out at pattern start/end."""
    if fade_in:
        # Volume slide up over first N rows
        slide_val = 0x30  # Slide up by 3 per tick
        for r in range(min(rows_count, pattern.rows)):
            existing = pattern.data[r][channel]
            if existing.effect == 0:
                existing.effect = FX_VOLUME_SLIDE
                existing.effect_val = slide_val
    if fade_out:
        # Volume slide down over last N rows
        slide_val = 0x03  # Slide down by 3 per tick
        start = max(0, pattern.rows - rows_count)
        for r in range(start, pattern.rows):
            existing = pattern.data[r][channel]
            if existing.effect == 0:
                existing.effect = FX_VOLUME_SLIDE
                existing.effect_val = slide_val


# ── Drums ──

def generate_drums(drum_pattern: dict[str, list[int]],
                   rows: int) -> dict[str, list[int]]:
    """Tile a one-bar, 16-step drum pattern across the given number of rows.

    The templates in theory.py are written as a single bar of 16th notes
    (kick on 1/2/3/4, snare on 2 and 4, hats on 8ths), so one step is one
    row and the bar repeats every ROWS_PER_BAR rows. Spreading the 16 steps
    over the whole 64-row pattern instead would play everything at quarter
    speed — one kick per bar and a snare every other bar.
    """
    expanded = {}
    for drum, pattern in drum_pattern.items():
        hits = []
        for bar_start in range(0, rows, ROWS_PER_BAR):
            for step, hit in enumerate(pattern):
                row = bar_start + step * ROWS_PER_STEP
                if hit and row < rows:
                    hits.append(row)
        expanded[drum] = hits
    return expanded


def apply_drums_to_pattern(pattern: ITPattern, drum_hits: dict[str, list[int]],
                           sample_map: dict[str, int],
                           swing: int = 0):
    """Write drum hits into pattern. swing>0 delays off-beat hats (shuffle).

    The off-beat eighth sits on row 2 of each 4-row beat, so a one-row delay
    is the largest shift that still swings — +2 would land on the next beat.
    Finer (triplet) swing needs the SDx note-delay effect for sub-row timing.
    """
    drum_channels = {
        "kick": CH_KICK, "snare": CH_SNARE, "hihat": CH_HIHAT,
        "hat": CH_HIHAT, "tom": CH_TOM, "crash": CH_CRASH,
        "open_hihat": CH_OPEN_HAT,
    }
    drum_note = midi_to_it_note(60)

    for drum, hits in drum_hits.items():
        ch = drum_channels.get(drum)
        inst_key = drum if drum != "hat" else "hihat"
        inst = sample_map.get(inst_key)
        if ch is None or inst is None:
            continue
        for row in hits:
            actual_row = row
            # Apply swing to off-beat hihat hits
            if (swing > 0 and drum in ("hihat", "hat")
                    and row % ROWS_PER_BEAT == 2 * ROWS_PER_STEP):
                actual_row = min(row + ROWS_PER_STEP, pattern.rows - 1)
            if 0 <= actual_row < pattern.rows:
                pattern.data[actual_row][ch] = ITNote(
                    note=drum_note,
                    instrument=inst,
                )


# ── Sustain management ──

def apply_sustain_safety_net(pat: ITPattern, channels: list[int] | None = None,
                             max_ring: int = 12):
    """Ensure no tonal note rings more than max_ring rows without a cut.

    Catches any generator that forgets to add note-cuts.
    """
    if channels is None:
        channels = [CH_MELODY, CH_HARMONY, CH_HARMONY2, CH_HARMONY3, CH_ARP]
    for ch in channels:
        last_note_row = None
        for row in range(pat.rows):
            cell = pat.data[row][ch]
            if cell.note != 0:  # any note event (including cuts) resets
                if cell.note == NOTE_CUT or cell.note == NOTE_OFF:
                    last_note_row = None
                else:
                    last_note_row = row
            elif last_note_row is not None and (row - last_note_row) == max_ring:
                pat.data[row][ch] = ITNote(note=NOTE_CUT)
                last_note_row = None


def _pattern_last_note_rings(pat: ITPattern, ch: int) -> bool:
    """Check if a channel's last event is a note (not a cut), meaning it rings past the pattern end."""
    last_is_note = False
    for row in range(pat.rows):
        n = pat.data[row][ch].note
        if n == NOTE_CUT or n == NOTE_OFF:
            last_is_note = False
        elif n != 0:
            last_is_note = True
    return last_is_note


def silence_inactive_channels(orders: list[int], patterns: list[ITPattern]):
    """Insert NOTE_CUT at row 0 to prevent notes ringing across pattern boundaries.

    If a channel had a ringing note in the previous pattern and the current
    pattern has no early event on that channel, insert a cut at row 0.
    """
    max_ring = 12  # match the in-pattern safety net

    for ord_idx in range(1, len(orders)):
        prev_pat = patterns[orders[ord_idx - 1]]
        cur_pat_idx = orders[ord_idx]
        cur_pat = patterns[cur_pat_idx]

        needs_cut = []
        for ch in TONAL_CHANNELS:
            if _pattern_last_note_rings(prev_pat, ch):
                has_early_event = False
                for row in range(min(max_ring, cur_pat.rows)):
                    if cur_pat.data[row][ch].note != 0:
                        has_early_event = True
                        break
                if not has_early_event:
                    needs_cut.append(ch)

        if needs_cut:
            new_pat = copy.deepcopy(cur_pat)
            for ch in needs_cut:
                new_pat.data[0][ch] = ITNote(note=NOTE_CUT)
            patterns.append(new_pat)
            orders[ord_idx] = len(patterns) - 1
