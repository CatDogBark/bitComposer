"""
Running a snapshot's own music driver, and what it wrote to the SNES chip.

The emulator is the Rust module `bitcomposer_emu` (emu/ in the repository,
the package bitcomposer-emu): the SNES sound CPU running the driver, the
SNES chip running beside it so the driver reads live state back. This
module calls it and hands back the writes; notes.py turns them into notes.
"""
import struct
from dataclasses import dataclass

CLOCK = 1_024_000            # SNES sound CPU cycles per second
RATE = 32000                 # the SNES chip's output rate


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


def available() -> bool:
    try:
        import bitcomposer_emu  # noqa: F401
    except ImportError:
        return False
    return True


def run(snapshot, seconds: float, audio: bool = False) -> Run:
    """Run `snapshot` (a bitcomposer.spc Snapshot) for `seconds` of song."""
    try:
        import bitcomposer_emu as emu
    except ImportError:
        raise EmulatorMissing("running an SPC file's driver needs the emulator, the bitcomposer-emu package "
                              "(emu/ in the repository; CONTRIBUTING.md says how to build it)") from None
    raw, kons, pcm, cycles, n = emu.run(snapshot.raw, float(seconds), audio)
    writes = [Write(c, r, v) for c, r, v in struct.iter_unpack("<QBB", raw)]
    keyons = [KeyOn(s / RATE, v, srcn, a, b) for s, v, srcn, a, b in struct.iter_unpack("<QBBHH", kons)]
    return Run(writes=writes, keyons=keyons, seconds=cycles / CLOCK, instructions=n, audio=pcm)
