"""
SPC snapshots: the SNES sound subsystem at one instant, read.

An .spc file is the SPC700's 64 KB of RAM (the game's music driver, the
song in that driver's own format, and the samples), the 128 S-DSP
registers, the CPU registers to resume from, and an ID666 tag. read()
gives all of it, with the DSP registers decoded: per voice the volume,
pitch, sample and envelope; the echo; the sample directory, whose samples
decode through brr.decode.

Step 2 of the SPC import plan (docs/SPC-IMPORT.md): what a snapshot holds
outright. What it only implies (the notes) takes running the driver, the
emulator of step 3. Standard library only, like the generator. The files
are the user's: the package reads them and never ships any.

    python -m bitcomposer.spc song.spc            what a snapshot holds
    python -m bitcomposer.spc --export DIR *.spc   its samples as WAV files
"""
from dataclasses import dataclass, field
from pathlib import Path

from .brr import Sample, decode, plausible

MAGIC = b"SNES-SPC700 Sound File Data"
SIZE = 0x10200                 # header + RAM + DSP + unused + the RAM under the IPL ROM
RAM, DSP, EXTRA = 0x100, 0x10100, 0x101C0
RATE = 32000                   # the DSP's output rate; a sample plays at it at pitch 0x1000
IPL = 0xFFC0                   # the boot ROM shadows the top 64 bytes of RAM

# Global DSP registers (per-voice ones are 0x00-0x09 + 0x10 * voice)
MVOLL, MVOLR, EVOLL, EVOLR = 0x0C, 0x1C, 0x2C, 0x3C
KON, KOFF, FLG, ENDX = 0x4C, 0x5C, 0x6C, 0x7C
EFB, PMON, NON, EON, DIR, ESA, EDL = 0x0D, 0x2D, 0x3D, 0x4D, 0x5D, 0x6D, 0x7D
FIR = (0x0F, 0x1F, 0x2F, 0x3F, 0x4F, 0x5F, 0x6F, 0x7F)


class SPCError(ValueError):
    """Not an SPC snapshot this reader understands."""


def _s8(b: int) -> int:
    return b - 256 if b & 0x80 else b


@dataclass
class Voice:
    """One of the DSP's eight voices as the snapshot left it."""
    index: int
    volume: tuple[int, int]      # left, right: -128..127
    pitch: int                   # 14 bits; 0x1000 plays a sample at 32 kHz as recorded
    sample: int                  # SRCN, the directory entry it plays
    adsr: bool                   # True: the ADSR envelope; False: GAIN
    attack: int                  # ADSR rates and levels, as the registers hold them
    decay: int
    sustain_level: int
    sustain_rate: int
    gain: int                    # the GAIN register, used when adsr is False
    envelope: int                # ENVX: the envelope's level now, 0-127
    output: int                  # OUTX: the voice's output now, -128..127
    echo: bool                   # sends to the echo (EON)
    noise: bool                  # plays the noise generator instead of its sample (NON)
    pitch_mod: bool              # pitch modulated by the voice before it (PMON)

    @property
    def sounding(self) -> bool:
        """Playing something audible at the instant of the snapshot."""
        return self.pitch > 0 and self.envelope > 0 and self.volume != (0, 0)


@dataclass
class Echo:
    delay_ms: int                # EDL * 16
    feedback: float              # EFB / 128
    volume: tuple[float, float]  # EVOL left, right / 128
    fir: tuple[int, ...]         # the eight filter taps, signed
    voices: tuple[int, ...]      # the voices sending to it
    writes: bool                 # FLG bit 5 clear: the echo buffer is being written
    buffer: int                  # ESA * 256: where the buffer starts in RAM

    @property
    def on(self) -> bool:
        return self.writes and bool(self.voices) and self.volume != (0.0, 0.0)


@dataclass
class Tags:
    """ID666: what the dumper wrote about the song. Empty where absent."""
    title: str = ""
    game: str = ""
    artist: str = ""
    dumper: str = ""
    comments: str = ""
    date: str = ""
    length_s: int | None = None  # seconds to play before the fade
    fade_ms: int | None = None
    binary: bool = False         # the tag's numbers were binary, not text


@dataclass
class Snapshot:
    ram: bytes
    dsp: bytes
    extra_ram: bytes             # what the RAM holds under the IPL ROM
    pc: int
    a: int
    x: int
    y: int
    psw: int
    sp: int
    tags: Tags
    source: str = ""
    _samples: dict = field(default_factory=dict, repr=False)

    @property
    def voices(self) -> list[Voice]:
        d = self.dsp
        out = []
        for v in range(8):
            b = v * 0x10
            adsr1, adsr2 = d[b + 5], d[b + 6]
            out.append(Voice(
                index=v, volume=(_s8(d[b]), _s8(d[b + 1])),
                pitch=(d[b + 2] | d[b + 3] << 8) & 0x3FFF, sample=d[b + 4],
                adsr=bool(adsr1 & 0x80), attack=adsr1 & 0x0F, decay=(adsr1 >> 4) & 7,
                sustain_level=adsr2 >> 5, sustain_rate=adsr2 & 0x1F, gain=d[b + 7],
                envelope=d[b + 8] & 0x7F, output=_s8(d[b + 9]),
                echo=bool(d[EON] >> v & 1), noise=bool(d[NON] >> v & 1),
                pitch_mod=bool(d[PMON] >> v & 1) and v > 0))
        return out

    @property
    def echo(self) -> Echo:
        d = self.dsp
        return Echo(delay_ms=(d[EDL] & 0x0F) * 16, feedback=_s8(d[EFB]) / 128,
                    volume=(_s8(d[EVOLL]) / 128, _s8(d[EVOLR]) / 128),
                    fir=tuple(_s8(d[a]) for a in FIR),
                    voices=tuple(v for v in range(8) if d[EON] >> v & 1),
                    writes=not d[FLG] & 0x20, buffer=d[ESA] << 8)

    @property
    def main_volume(self) -> tuple[float, float]:
        return _s8(self.dsp[MVOLL]) / 128, _s8(self.dsp[MVOLR]) / 128

    @property
    def directory(self) -> int:
        return self.dsp[DIR] << 8

    def entry(self, srcn: int) -> tuple[int, int]:
        """A directory entry: (start, loop address)."""
        e = (self.directory + 4 * srcn) & 0xFFFF
        r = self.ram
        return r[e] | r[(e + 1) & 0xFFFF] << 8, r[(e + 2) & 0xFFFF] | r[(e + 3) & 0xFFFF] << 8

    def sample(self, srcn: int) -> Sample | None:
        """Directory entry srcn decoded, or None when it holds no sample
        (most of the 256 entries are unused, and hold whatever RAM had)."""
        if srcn not in self._samples:
            start, loop = self.entry(srcn)
            s = None
            if 0 < start < IPL and start <= loop < IPL:
                s = decode(self.ram, start, loop)
                if s is not None and len(s) < 16:
                    s = None
            self._samples[srcn] = s
        return self._samples[srcn]

    def samples(self, everything: bool = False) -> dict[int, Sample]:
        """The directory's samples, by entry: those that look like samples
        (brr.plausible) and those a voice is playing now, which may still
        include leftovers the song never plays (running the driver is what
        tells). everything: every entry that decodes at all."""
        playing = {v.sample for v in self.voices if v.sounding and not v.noise}
        out = {}
        for n in range(256):
            s = self.sample(n)
            if s is not None and (everything or n in playing or plausible(self.ram, s.start)):
                out[n] = s
        return out


def read(path_or_data, source: str = "") -> Snapshot:
    """An SPC snapshot from a path or its bytes."""
    if isinstance(path_or_data, (bytes, bytearray)):
        data = bytes(path_or_data)
    else:
        p = Path(path_or_data)
        source = source or str(p)
        try:
            data = p.read_bytes()
        except OSError as e:
            raise SPCError(f"{p}: cannot read it ({e.strerror or e})") from None
    where = source or "data"
    if not data.startswith(MAGIC):
        raise SPCError(f"{where}: not an SPC file (it does not start {MAGIC.decode()!r})")
    if len(data) < SIZE:
        raise SPCError(f"{where}: {len(data)} bytes; an SPC file is at least {SIZE}")
    pc = data[0x25] | data[0x26] << 8
    return Snapshot(ram=data[RAM:RAM + 0x10000], dsp=data[DSP:DSP + 0x80], extra_ram=data[EXTRA:EXTRA + 0x40],
                    pc=pc, a=data[0x27], x=data[0x28], y=data[0x29], psw=data[0x2A], sp=data[0x2B],
                    tags=_tags(data) if data[0x23] == 26 else Tags(), source=source)


def _text(b: bytes) -> str:
    return b.split(b"\0", 1)[0].decode("latin-1").strip()


def _digits(b: bytes) -> bool:
    """Text-format numbers: digits, padded with NULs or spaces."""
    return all(c in b"0123456789 \0" for c in b)


def _tags(data: bytes) -> Tags:
    """ID666 comes in a text and a binary layout that differ from 0x9E on
    and say nothing about which they are; the usual test is whether the
    length and fade fields read as digits."""
    t = Tags(title=_text(data[0x2E:0x4E]), game=_text(data[0x4E:0x6E]),
             dumper=_text(data[0x6E:0x7E]), comments=_text(data[0x7E:0x9E]))
    length, fade = data[0xA9:0xAC], data[0xAC:0xB1]
    if _digits(length) and _digits(fade) and _digits(data[0x9E:0xA9].replace(b"/", b"0").replace(b"-", b"0")):
        t.date = _text(data[0x9E:0xA9])
        t.length_s = int(_text(length)) if _text(length) else None
        t.fade_ms = int(_text(fade)) if _text(fade) else None
        t.artist = _text(data[0xB1:0xD1])
    else:
        t.binary = True
        ymd = int.from_bytes(data[0x9E:0xA2], "little")
        t.date = f"{ymd // 10000:04d}-{ymd // 100 % 100:02d}-{ymd % 100:02d}" if ymd else ""
        t.length_s = int.from_bytes(data[0xA9:0xAC], "little") or None
        t.fade_ms = int.from_bytes(data[0xAC:0xB0], "little") or None
        t.artist = _text(data[0xB0:0xD0])
    return t
