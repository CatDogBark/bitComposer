"""
Running a snapshot's own music driver, and what it wrote to the SNES chip.

The emulator is the Rust module `bitcomposer_emu` (emu/ in the repository,
the package bitcomposer-emu): the SNES sound CPU running the driver, the
SNES chip running beside it so the driver reads live state back. This
module calls it and hands back the writes; notes.py turns them into notes.
"""
import struct
from array import array
from dataclasses import dataclass, field

CLOCK = 1_024_000            # SNES sound CPU cycles per second
RATE = 32000                 # the SNES chip's output rate
NEEDS = (0, 2)               # the emulator version this module calls (voice taps and mute)


class EmulatorMissing(RuntimeError):
    """The compiled emulator is not installed."""


@dataclass
class Write:
    cycle: int
    reg: int
    value: int

    @property
    def time(self) -> float:
        return self.cycle / CLOCK


@dataclass
class KeyOn:
    """A key-on as the SNES chip acted on it, with the directory entry it read
    then (drivers often write it just before: the snapshot's need not hold it)."""
    time: float
    voice: int
    srcn: int
    start: int
    loop: int


@dataclass
class Run:
    writes: list[Write]
    keyons: list[KeyOn]
    seconds: float               # the song time run
    instructions: int
    audio: bytes | None          # 32 kHz stereo 16-bit little-endian, when asked for
    # for each tapped voice, its own output (after its envelope, before its
    # volumes), one 16-bit sample per SNES chip sample from the snapshot on
    tapped: dict[int, array] = field(default_factory=dict)


def _module():
    try:
        import bitcomposer_emu as emu
    except ImportError:
        return None
    version = tuple(int(p) for p in emu.__version__.split(".")[:2] if p.isdigit())
    return emu if version >= NEEDS else None


def available() -> bool:
    return _module() is not None


def run(snapshot, seconds: float, audio: bool = False, mute: int = 0, taps: int = 0) -> Run:
    """Run `snapshot` (a bitcomposer.spc Snapshot) for `seconds` of song.
    `mute` leaves voices out of `audio` (bit n, voice n), still running;
    `taps` keeps those voices' own output in `tapped`."""
    emu = _module()
    if emu is None:
        raise EmulatorMissing(f"running an SPC file's driver needs the emulator, the bitcomposer-emu package, "
                              f"version {'.'.join(map(str, NEEDS))} or later "
                              "(emu/ in the repository; CONTRIBUTING.md says how to build it)")
    raw, kons, pcm, tap, cycles, n = emu.run(snapshot.raw, float(seconds), audio, mute, taps)
    writes = [Write(c, r, v) for c, r, v in struct.iter_unpack("<QBB", raw)]
    keyons = [KeyOn(s / RATE, v, srcn, a, b) for s, v, srcn, a, b in struct.iter_unpack("<QBBHH", kons)]
    tapped = {}
    if tap:
        voices = [v for v in range(8) if taps >> v & 1]
        both = array("h", tap)
        for i, v in enumerate(voices):
            tapped[v] = both[i::len(voices)]
    return Run(writes=writes, keyons=keyons, seconds=cycles / CLOCK, instructions=n, audio=pcm, tapped=tapped)


def solos(snapshot, seconds: float) -> dict[int, array]:
    """Each voice alone for `seconds` of song, as run(audio=True, mute=...)
    with the other seven muted gives it, but from one run (each voice's echo
    kept apart): {voice: 32 kHz stereo 16-bit}. Needs emulator 0.3."""
    emu = _module()
    if emu is None or not hasattr(emu, "solos"):
        raise EmulatorMissing("each voice alone from one run needs the emulator, bitcomposer-emu, version 0.3 or later")
    raw, frames = emu.solos(snapshot.raw, float(seconds))
    every = array("h", raw)
    return {v: every[2 * frames * v:2 * frames * (v + 1)] for v in range(8)}
