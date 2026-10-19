"""
The SNES chip decoder: what a driver wrote to the SNES chip, as notes.

Step 4 of docs/SPC-IMPORT.md, the chip-specific half of "a chip decoder
per sound chip". It replays the writes against a copy of the SNES chip's
registers (as the snapshot left them): a key-on (KON) on a voice starts a
note with the voice's sample, pitch, volume and envelope at that moment;
a key-off (KOFF), the voice's next key-on, or the soft reset (FLG bit 7)
ends it; pitch and volume writes while it sounds are kept as bends and
volume changes (vibrato, slides, swells). What the notes mean musically
(tempo, roles, habits) is the translator's job, shared by every chip.

Times are seconds from the snapshot, at the moment the SNES chip acts:
the hardware polls KON every other sample and starts a voice 5 samples
later, so a note sounds about 6 samples (0.19 ms) after its write.
"""
from dataclasses import dataclass, field

from .emulate import CLOCK, RATE

KON, KOFF, FLG, EON, NON = 0x4C, 0x5C, 0x6C, 0x4D, 0x3D
MVOLL, MVOLR, EVOLL, EVOLR, EFB, EDL = 0x0C, 0x1C, 0x2C, 0x3C, 0x0D, 0x7D
FIR = (0x0F, 0x1F, 0x2F, 0x3F, 0x4F, 0x5F, 0x6F, 0x7F)
KEY_ON_DELAY = 6 / RATE


@dataclass
class Note:
    voice: int
    start: float
    sample: int                      # SRCN: the directory entry it plays
    pitch: int                       # the pitch register at key-on; 0x1000 plays the sample at 32 kHz
    volume: tuple[int, int]          # left, right: -128..127
    adsr: tuple[int, int]            # ADSR1, ADSR2 at key-on
    gain: int
    echo: bool
    noise: bool
    noise_rate: int = 0              # FLG's noise clock (5-bit rate) at key-on, for noise notes
    brr: tuple[int, int] | None = None   # the (start, loop) addresses it played, as the SNES chip read them
    # the echo as it stood at key-on (it sends when `echo` and echo writes are on)
    echo_delay: float = 0.0          # seconds: EDL * 16 ms
    echo_volume: tuple[float, float] = (0.0, 0.0)    # EVOL left, right, -1..1
    echo_feedback: float = 0.0       # EFB, -1..1
    echo_fir: float = 1.0            # the FIR filter's gain at DC: its taps' sum / 128
    echo_writes: bool = True         # FLG bit 5 clear
    end: float | None = None         # None: still sounding when the run ended
    bends: list[tuple[float, int]] = field(default_factory=list)       # (time, pitch) while it sounds
    swells: list[tuple[float, int, int]] = field(default_factory=list)  # (time, left, right)

    @property
    def length(self) -> float | None:
        return None if self.end is None else self.end - self.start


def _s8(b: int) -> int:
    return b - 256 if b & 0x80 else b


def decode(snapshot, writes, until: float | None = None, keyons=None) -> list[Note]:
    """The notes in a run's writes, in order of their start. `keyons` (from
    emulate.Run) gives each note the sample addresses the SNES chip read as
    it keyed the voice on; many drivers write a voice's directory entry just
    before keying it, so the snapshot's entry may not be what plays."""
    regs = bytearray(snapshot.dsp)
    sounding: dict[int, Note] = {}
    notes: list[Note] = []

    def close(v: int, t: float):
        n = sounding.pop(v, None)
        if n is not None:
            n.end = max(t, n.start)

    for w in writes:
        t = w.cycle / CLOCK
        reg, val = w.reg, w.value
        if reg == KON:
            for v in range(8):
                if val >> v & 1:
                    close(v, t)
                    if regs[KOFF] >> v & 1 or regs[FLG] & 0x80:
                        continue                 # keyed on while held off: no sound
                    b = v * 0x10
                    n = Note(voice=v, start=t + KEY_ON_DELAY, sample=regs[b + 4],
                             pitch=(regs[b + 2] | regs[b + 3] << 8) & 0x3FFF,
                             volume=(_s8(regs[b]), _s8(regs[b + 1])), adsr=(regs[b + 5], regs[b + 6]),
                             gain=regs[b + 7], echo=bool(regs[EON] >> v & 1), noise=bool(regs[NON] >> v & 1),
                             noise_rate=regs[FLG] & 0x1F, echo_delay=(regs[EDL] & 0x0F) * 0.016,
                             echo_volume=(_s8(regs[EVOLL]) / 128, _s8(regs[EVOLR]) / 128),
                             echo_feedback=_s8(regs[EFB]) / 128, echo_fir=sum(_s8(regs[a]) for a in FIR) / 128,
                             echo_writes=not regs[FLG] & 0x20)
                    sounding[v] = n
                    notes.append(n)
            continue
        if reg == 0x7C:                          # ENDX: a write acknowledges, nothing is kept
            continue
        regs[reg] = val
        if reg == KOFF:
            for v in range(8):
                if val >> v & 1:
                    close(v, t)
        elif reg == FLG and val & 0x80:
            for v in list(sounding):
                close(v, t)
        elif reg < 0x80 and reg & 0x0F in (2, 3):
            n = sounding.get(reg >> 4)
            if n is not None:
                b = n.voice * 0x10
                p = (regs[b + 2] | regs[b + 3] << 8) & 0x3FFF
                if p != (n.bends[-1][1] if n.bends else n.pitch):
                    n.bends.append((t, p))
        elif reg < 0x80 and reg & 0x0F in (0, 1):
            n = sounding.get(reg >> 4)
            if n is not None:
                b = n.voice * 0x10
                vol = (_s8(regs[b]), _s8(regs[b + 1]))
                if vol != (n.swells[-1][1:] if n.swells else n.volume):
                    n.swells.append((t, *vol))
    if until is not None:
        for n in sounding.values():
            n.end = None
    if keyons:
        by_voice: dict[int, list] = {}
        for k in keyons:
            by_voice.setdefault(k.voice, []).append(k)
        for n in notes:
            ks = by_voice.get(n.voice, [])
            while ks and ks[0].time < n.start - 0.0005:
                ks.pop(0)
            if ks and ks[0].time <= n.start + 0.0005:
                k = ks.pop(0)
                n.brr = (k.start, k.loop)
    return notes


def master_volume(snapshot, writes) -> list[tuple[float, int, int]]:
    """The SNES chip's master volume over the run: (time, left, right), the
    snapshot's first, then each change (a driver fades a song out here)."""
    left, right = _s8(snapshot.dsp[MVOLL]), _s8(snapshot.dsp[MVOLR])
    out = [(0.0, left, right)]
    for w in writes:
        if w.reg in (MVOLL, MVOLR):
            if w.reg == MVOLL:
                left = _s8(w.value)
            else:
                right = _s8(w.value)
            if (left, right) != out[-1][1:]:
                out.append((w.cycle / CLOCK, left, right))
    return out
