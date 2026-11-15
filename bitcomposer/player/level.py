"""A song's level as the player hears it, and the gain that brings every song
to one common level.

The songs in a folder do not sit at one level: a written song's parts take
their levels from its token's game song, and the game's own songs span some
fifteen decibels from the quietest to the loudest. In a game that is the
score; in a player that runs one song after another it is a volume knob that
moves by itself. So the player levels what it plays, as it sets the GAIN and
the WIDTH: at playback, on the audio it is about to play, with the writer, the
vocabulary and the files left as they are. A file opened in another player
plays at the level it was written at.

The measure is the song's own audio through libopenmpt, the first minute, in
blocks of 0.4 s: the mean square over both channels, the blocks under an
absolute floor left out, then the blocks more than ten decibels under the mean
of the rest (the loudness standard's two gates, ITU-R BS.1770, without its
frequency weighting, which needs a filter a sample and the standard library
has none fast enough). A rest or a thin intro does not pull a song up.
"""
import array
import ctypes
import json
import math
import os
from pathlib import Path

from .openmpt import Module, SAMPLE_RATE

TARGET_DB = -24.5                     # dBFS: the common level, the middle of Final Fantasy VI's own songs on this measure (-24.4 over its 74)
MEASURE_SECONDS = 60.0                # how much of a song is measured
BLOCK_SECONDS = 0.4
ABSOLUTE_GATE_DB = -70.0              # a block under this is silence
RELATIVE_GATE_DB = -10.0              # and one this far under the mean of the rest is a rest or a tail
MAX_TRIM_DB = 12.0                    # the most a song is turned up or down: a file of near silence is not made a song
FULL_SCALE = 32768.0 ** 2
CHANNELS = 2

_sumprod = getattr(math, "sumprod", None)                    # Python 3.12 on


def _square_sum(samples) -> float:
    return float(_sumprod(samples, samples)) if _sumprod else float(sum(v * v for v in samples))


def _db(mean_square: float) -> float:
    return 10.0 * math.log10(mean_square / FULL_SCALE)


def gated(blocks: list[float]) -> float | None:
    """The level in dBFS of a song's blocks (each a mean square), by the two
    gates; None where nothing sounds."""
    floor = FULL_SCALE * 10 ** (ABSOLUTE_GATE_DB / 10.0)
    heard = [b for b in blocks if b > floor]
    if not heard:
        return None
    gate = sum(heard) / len(heard) * 10 ** (RELATIVE_GATE_DB / 10.0)
    kept = [b for b in heard if b > gate]
    return _db(sum(kept) / len(kept))


def measure(path: str, seconds: float = MEASURE_SECONDS) -> float | None:
    """The level of the module at `path` in dBFS, or None where it cannot be
    read or is silent. Decodes on a module of its own, so it may run beside
    the one playing."""
    try:
        module = Module(path)
    except Exception:                                        # an unreadable file has no level: it plays as it is
        return None
    try:
        frames = int(BLOCK_SECONDS * SAMPLE_RATE)
        buf = (ctypes.c_int16 * (frames * CHANNELS))()
        blocks, left = [], int(seconds * SAMPLE_RATE)
        while left > 0:
            got = module.read_stereo(min(frames, left), buf)
            if got <= 0:
                break
            left -= got
            if got * 2 < frames:                             # a last scrap under half a block is not a block
                break
            samples = array.array("h")
            samples.frombytes(bytes(buf)[:got * CHANNELS * 2])
            blocks.append(_square_sum(samples) / (got * CHANNELS))
        return gated(blocks)
    finally:
        module.destroy()


def gain_for(level_db: float | None, target_db: float = TARGET_DB) -> float:
    """The gain that brings a song measured at `level_db` to the common level:
    1.0 for a song with no level, and never more than MAX_TRIM_DB either way."""
    if level_db is None:
        return 1.0
    trim = max(-MAX_TRIM_DB, min(MAX_TRIM_DB, target_db - level_db))
    return 10 ** (trim / 20.0)


class Levels:
    """The levels measured so far, kept beside the player's settings so a song
    is measured once: {path: (modification time in ns, size, level or None)}.
    A file changed since it was measured is measured again."""

    def __init__(self, file: Path):
        self.file = Path(file)
        self.known: dict[str, tuple[int, int, float | None]] = {}
        try:
            with open(self.file) as fh:
                for path, row in json.load(fh).items():
                    self.known[path] = (int(row[0]), int(row[1]), None if row[2] is None else float(row[2]))
        except (OSError, ValueError, TypeError, IndexError, AttributeError):
            self.known = {}

    @staticmethod
    def _stamp(path: str) -> tuple[int, int] | None:
        try:
            st = os.stat(path)
        except OSError:
            return None
        return st.st_mtime_ns, st.st_size

    def cached(self, path: str) -> tuple[bool, float | None]:
        """(known, level): whether this file as it is now has been measured."""
        stamp, row = self._stamp(path), self.known.get(path)
        if stamp is None or row is None or (row[0], row[1]) != stamp:
            return False, None
        return True, row[2]

    def put(self, path: str, level: float | None) -> None:
        """What was just measured for the file as it is now."""
        stamp = self._stamp(path)
        if stamp is not None:
            self.known[path] = (stamp[0], stamp[1], level)

    def level(self, path: str) -> float | None:
        """The file's level, measured now where it is not known."""
        known, level = self.cached(path)
        if not known:
            level = measure(path)
            self.put(path, level)
        return level

    def forget(self, path: str) -> None:
        self.known.pop(path, None)

    def moved(self, old: str, new: str) -> None:
        if old in self.known:
            self.known[new] = self.known.pop(old)

    def save(self) -> None:
        """Written whole, files that are gone left out. A failure to save
        costs a measurement next time and nothing else."""
        rows = {p: list(r) for p, r in self.known.items() if os.path.exists(p)}
        try:
            self.file.parent.mkdir(parents=True, exist_ok=True)
            tmp = str(self.file) + ".tmp"
            with open(tmp, "w") as fh:
                json.dump(rows, fh)
            os.replace(tmp, self.file)
        except OSError:
            pass
