"""A song as played: the notes the SNES chip decoder finds, each named (a
MIDI pitch from its sample's measured tuning), with the samples they play.

A driver plays an equal-tempered pitch table, so every note of a sample
falls the same fraction of a semitone off: that fraction is the sample's
own tuning (its measured pitch, and how the composer tuned it), and each
note is named with it taken out. FFVI's instruments do not share one: in
Locke, from 12 cents flat to 23 sharp."""
import hashlib
import math
from dataclasses import dataclass, field

from ..spc import brr, emulate, notes as notes_mod, tuning

LONGEST = 240.0                      # seconds of a song read: past its loop, for any song a player would loop


@dataclass
class Sample:
    """A sample a song plays, by the addresses the SNES chip read."""
    addr: tuple[int, int]            # start, loop
    key: str                         # its BRR data's hash: the same sample in another song, or game
    f0: float | None                 # its fundamental at its own rate (pitch 0x1000), None: no pitch found
    frames: int
    loops: bool
    offset: float = 0.0              # its notes' fraction of a semitone, as played (taken out of their midi)


@dataclass
class Played:
    """A note in musical terms."""
    voice: int
    start: float                     # seconds from the snapshot, as the SNES chip sounds it
    end: float | None                # None: still sounding when the reading ends
    sample: Sample | None            # None: noise
    midi: float | None               # its pitch at key-on, its sample's tuning taken out; None: unpitched
    level: float                     # its volume, the two sides' mean, 0-1
    pan: float                       # the right side's share, 0 (left) to 1 (right)
    note: notes_mod.Note = field(repr=False)

    @property
    def length(self) -> float | None:
        return None if self.end is None else self.end - self.start


@dataclass
class Song:
    """A song as played: its notes in order of their start, and its samples."""
    source: str
    seconds: float
    notes: list[Played]
    samples: dict                    # BRR addresses -> Sample
    tags: object = None
    writes: list = field(default_factory=list, repr=False)


def _key(ram, start: int) -> str:
    """A hash of a sample's BRR blocks, through its end block."""
    blocks = bytearray()
    a = start
    for _ in range(brr.MAX_BLOCKS):
        block = bytes(ram[(a + i) & 0xFFFF] for i in range(brr.BLOCK))
        blocks += block
        a = (a + brr.BLOCK) & 0xFFFF
        if block[0] & 1:
            break
    return hashlib.sha1(blocks).hexdigest()[:16]


def song_seconds(snap) -> float:
    """How long a song is read: its tag's length and fade, or a minute and a half without one."""
    tag = (snap.tags.length_s or 0) + (snap.tags.fade_ms or 0) / 1000
    return min(LONGEST, float(tag) if tag > 0 else 90.0)


def play(snap, seconds: float | None = None) -> Song:
    """Run the snapshot's driver and name its notes."""
    seconds = song_seconds(snap) if seconds is None else seconds
    run = emulate.run(snap, seconds)
    found = []
    for n in notes_mod.decode(snap, run.writes, until=seconds, keyons=run.keyons):
        if not n.pitch and not n.noise and n.bends:
            n.pitch = n.bends.pop(0)[1]      # keyed at pitch 0, its pitch written just after
        if n.pitch or n.noise:
            if n.brr is None and not n.noise:
                n.brr = snap.entry(n.sample)
            found.append(n)
    samples = {}
    for n in found:
        if n.noise or n.brr in samples:
            continue
        s = brr.decode(snap.ram, *n.brr) if 0 < n.brr[0] < 0xFFC0 else None
        f0 = tuning.fundamental(s) if s is not None and len(s.pcm) >= 16 else None
        samples[n.brr] = Sample(n.brr, _key(snap.ram, n.brr[0]), f0, len(s.pcm) if s else 0, bool(s and s.loops))
    raw = [(n, samples.get(n.brr) if not n.noise else None) for n in found]
    for s in samples.values():
        if s.f0:
            s.offset = _offset([tuning.midi(s.f0, n.pitch) for n, x in raw if x is s])
    played = []
    for n, s in raw:
        m = tuning.midi(s.f0, n.pitch) - s.offset if s is not None and s.f0 else None
        left, right = abs(n.volume[0]), abs(n.volume[1])
        played.append(Played(n.voice, n.start, n.end, s, m, (left + right) / 256,
                             right / (left + right) if left + right else 0.5, n))
    played.sort(key=lambda p: (p.start, p.voice))
    return Song(snap.source, seconds, played, samples, snap.tags, run.writes)


def _offset(midis: list[float]) -> float:
    """The circular mean of notes' fractions of a semitone, from -0.5 to 0.5."""
    if not midis:
        return 0.0
    ang = [2 * math.pi * (m - math.floor(m)) for m in midis]
    return math.atan2(sum(map(math.sin, ang)), sum(map(math.cos, ang))) / (2 * math.pi)
