"""
An IT song on a row grid: the half of SPC to IT that knows IT and not the
SNES. Patterns to the song's last row exactly, IT's limits, and each note
written as IT cells: the note, its pan or surround, its volume and pitch row
by row (the volume column, fine slides), its cut; the global volume on a
channel of its own; the file.

convert.py decides what to write (which samples and instruments, which
notes on which channels, their volumes and pitches row by row); this writes
it. A `Line` is plain data, so the writer is tested without the emulator,
and a second source (a console after the SNES) can write through it.
"""
import math
from dataclasses import dataclass

from .. import it_format as itf

ROWS_PER_PATTERN = 200
MAX_PATTERNS = 200
MAX_TICK_RATE = 102.0                 # IT tempo 255 is 102 ticks a second
MAX_INSTRUMENTS = 99
MAX_SAMPLES = 255                     # what an instrument's keyboard can name
MAX_CHANNELS = 64                     # an IT module's channels
KEYS = 119                            # recordings one instrument's keyboard holds: notes 1-119 (0 reads as none)
ENV_TOP = 64                          # an IT envelope's levels: 0-64
ENV_NODES = 25                        # an IT envelope's nodes
FX_SET_GLOBAL_VOLUME = 22             # Vxx
FX_SAMPLE_OFFSET = 15                 # Oxx: start xx * 256 samples in
SURROUND_ON, SURROUND_OFF = 0x91, 0x90   # S91 / S90: one side phase-inverted, centred


def tempo_for(row_hz: float) -> tuple[int, float]:
    """(IT tempo, rows a second) for rows as near `row_hz` as IT's tempo
    allows, at one tick a row."""
    tempo = max(32, min(255, round(2.5 * row_hz)))
    return tempo, tempo / 2.5


def envelope_nodes(levels: list[int]) -> list[tuple[int, int]]:
    """At most ENV_NODES nodes (tick, level) tracing per-tick levels, the
    error kept smallest."""
    points = list(enumerate(levels))
    if len(points) <= 2:
        return points or [(0, 0)]
    tol = 0.5
    while True:
        keep = _rdp(points, tol)
        if len(keep) <= ENV_NODES:
            return keep
        tol *= 1.5


def _rdp(points, tol):
    if len(points) < 3:
        return points
    (x0, y0), (x1, y1) = points[0], points[-1]
    worst, at = 0.0, 0
    for i in range(1, len(points) - 1):
        x, y = points[i]
        line = y0 + (y1 - y0) * (x - x0) / (x1 - x0) if x1 != x0 else y0
        if abs(y - line) > worst:
            worst, at = abs(y - line), i
    if worst <= tol:
        return [points[0], points[-1]]
    return _rdp(points[:at + 1], tol)[:-1] + _rdp(points[at:], tol)


@dataclass
class Line:
    """A note as one channel's cells carry it, from row `row` until it is cut
    on row `end`. `volumes` and `pitch` run row by row from `row` (as far as
    the song goes): the first volume is the note's own, each later one goes
    in the volume column where it changes and the cell is free; a pitch is
    in 64ths of a semitone from `note` (None: none to reach), reached by fine
    slides where the effect column is free."""
    row: int
    end: int
    note: int                         # IT note 1-119 (a cell's 0, C-0, reads as none)
    instrument: int
    volumes: list[int]                # 0-64
    pan: int | None = None            # 0-255 (Xxx), set where it changes; None leaves the channel's
    surround: bool = False            # S91: plays centred, one side inverted
    pitch: list[int | None] | None = None
    offset: int | None = None         # Oxx on the first row, where the effect column is free


class Grid:
    """The song's patterns, `channels` wide, `seconds` long at `row_hz` rows a
    second: to its last row exactly (the last pattern short), since notes
    still held at a rounded-up end rang on past it."""

    def __init__(self, seconds: float, row_hz: float, channels: int):
        total = max(1, round(seconds * row_hz))
        n = min(MAX_PATTERNS, math.ceil(total / ROWS_PER_PATTERN))
        self.patterns = [itf.ITPattern(rows=min(ROWS_PER_PATTERN, total - i * ROWS_PER_PATTERN), channels=channels)
                         for i in range(n)]
        self.last_row = min(total, n * ROWS_PER_PATTERN) - 1
        self.channels = channels
        self._pans, self._surround = {}, {}

    def has(self, row: int) -> bool:
        return 0 <= row <= self.last_row

    def cell(self, row: int, ch: int):
        return self.patterns[row // ROWS_PER_PATTERN].data[row % ROWS_PER_PATTERN][ch] if self.has(row) else None

    def write(self, ch: int, line: Line) -> None:
        """Write a note into channel ch (its first row in the song). A pan or
        surround is written only where the channel's changes."""
        c = self.cell(line.row, ch)
        c.note, c.instrument, c.volume = line.note, line.instrument, line.volumes[0]
        if line.surround != self._surround.get(ch, False):
            c.effect, c.effect_val = itf.FX_SPECIAL, SURROUND_ON if line.surround else SURROUND_OFF
            self._surround[ch] = line.surround
            self._pans.pop(ch, None)
        elif not line.surround and line.pan is not None and line.pan != self._pans.get(ch):
            c.effect, c.effect_val = itf.FX_SET_PAN, line.pan
            self._pans[ch] = line.pan
        if line.offset is not None and c.effect == 0:
            c.effect, c.effect_val = FX_SAMPLE_OFFSET, line.offset
        cur, last_vol = 0, c.volume
        for i, r in enumerate(range(line.row, min(line.end, self.last_row + 1))):
            cc = self.cell(r, ch)
            v = line.volumes[i]
            if i and v != last_vol and cc.volume == 255 and cc.note == 0:
                cc.volume, last_vol = v, v
            target = line.pitch[i] if line.pitch else None
            if target is None:
                continue
            delta = target - cur
            if delta and cc.effect == 0:
                d = abs(delta)
                if d <= 15:
                    val, moved = 0xE0 | d, d
                else:
                    x = min(15, round(d / 4))
                    val, moved = 0xF0 | x, 4 * x
                cc.effect = itf.FX_PORTA_UP if delta > 0 else itf.FX_PORTA_DOWN
                cc.effect_val = val
                cur += moved if delta > 0 else -moved
        if line.end <= self.last_row:
            cc = self.cell(line.end, ch)
            if cc.note == 0:
                cc.note = itf.NOTE_CUT

    def global_volume(self, ch: int, level: int, changes) -> None:
        """The global volume's changes [(row, 0-128)] on channel ch, from
        `level` (the header's): each written where it differs from the last,
        rows past the song left out."""
        for r, gv in changes:
            c = self.cell(r, ch)
            if c is None:
                continue
            if gv != level:
                c.effect, c.effect_val = FX_SET_GLOBAL_VOLUME, gv
                level = gv


def write(path: str, song: dict) -> None:
    """The song dict (as convert returns it) as an IT file."""
    n = song["info"]["channels"]
    itf.write_it_file(path, song["name"], song["samples"], song["patterns"], song["orders"], tempo=song["tempo"],
                      speed=song["speed"], global_volume=song["global_volume"], mix_volume=128, num_channels=n,
                      channel_pans=[32] * n, message=song["message"], instruments=song["instruments"])
