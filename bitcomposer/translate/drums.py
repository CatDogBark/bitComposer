"""A drum sample named by its sound (stage 4 of docs/TRANSLATOR.md): kick,
snare, hat or another sound, from the sample itself, not from where the
game hits it. rhythm.py's drum figures and against.py's drum rows take the
names from here when the game's SPC files are at hand.

    python -m bitcomposer.translate.drums --score
    python -m bitcomposer.translate.drums --db PATH --spc DIR [--game NAME]

The measure. Four numbers from the sample as played (its pitch the one the
game plays it at most, from its notes; a looped sample repeated as long as
the game holds it): how much of its power sits under LOW Hz (a kick's or a
tom's body), how much under HIGH Hz (a snare's shell and rattle; a hat has
next to none), how periodic its first 64 ms are (its best normalised
autocorrelation past the first zero crossing, over the periods of 40 to
2000 Hz: a tone near one, noise near nought), and how long it rings
(seconds to 40 dB under its peak). The spectrum is of its first 128 ms
(FFT, the standard library's complex numbers); brightness is the centroid.

The rule. Power mostly under LOW: a low drum; a kick when its centroid
sits under KICK_HZ, a tom or another pitched drum when it is periodic
(PITCHED) or sits above TOM_HZ and holds its pitch, a deep snare (a noisy
thud above the kick's range: Seiken Densetsu 3's, Top Gear's) when it does
not. Else noise (periodicity under TONE, or a hiss centred over HISS Hz
that is not plainly pitched: a looped hat repeats, and reads periodic):
ringing LONG seconds or more, a cymbal; over within CLICK seconds, a click
(a rim); with a body under HIGH, a snare; with nearly none and over within
BURST, a closed hat. Else a tone off the floor: with a body under LOW, a
snare (a drum shell with its rattle: Final Fantasy VI's snare is one);
without, another sound (a rim, a block, an orchestra hit, a pitched
instrument played as percussion).

Four cases the sound alone cannot settle, and how the game plays the sample
settles each (profile: the shares of its hits on the bar's first beat, on
its other beats, off the beat), the sound deciding everything else: a low
drum between KICK_HZ and TOM_HZ that holds no pitch (a short kick reads
high; Donkey Kong Country 2's), a kick when it lands on the beats more
than between them, else another drum; a hiss over HISS with a little body
(a hat loop over a rumble, or a bright snare), a hat when it plays off the
beat more than on, else a snare; a bodiless noise burst ringing between
BURST and RING (the built-in packs' snares are gated noise, as are open hats
and cymbals cut short), a cymbal when it lands on the first beat most, a
snare on the other beats, else a hat; and noise ringing between RING and
LONG (a cymbal, or a snare with its room: Seiken Densetsu 3's), a snare
when it lands on the backbeats more than on the first. Without the play
(the generator's samples scored alone) a low drum in the margin is the tom,
a bright bodied hiss the snare, a bodiless burst the snare under OPEN
seconds and the hat over, and long noise the cymbal.

Why these. The pack's kit (pack.py) ranked by brightness and length, which
tells a kick from a hat but not a snare from an open hat or a cymbal from a
hat loop held long; FFVI's open hat read as its snare by where it hit, and
its looped cymbal as a kick. Brightness and periodicity carry the kick, the
hat and the pitched sounds; the body under the hiss carries the snare;
length the cymbal. Checked against the generator's named drums (score())
and by ear on FFVI."""
import argparse
import cmath
import math
import os
import statistics
import sys
from collections import Counter
from dataclasses import dataclass

LOW = 200                            # Hz: a kick's body sits under this
HIGH = 1000                          # Hz: a snare's body sits under this, a hat's hiss over it
KICK_HZ = 93                         # a low drum whose centroid is under this is a kick
TOM_HZ = 200                         # and over this, holding its pitch, a tom
HISS = 5000                          # Hz: a centroid over this is a hat's or a cymbal's, nothing pitched
TONE = 0.5                           # periodicity under this is noise
PITCHED = 0.7                        # and over this plainly a pitch
RING = 0.4                           # seconds: a bodiless noise burst ringing this long is a cymbal, or a snare in a room
LONG = 0.6                           # and this long a cymbal
CLICK = 0.05                         # seconds: noise with a body over within this is a click, not a snare
BODY = 0.2                           # the share of the power under LOW (a tone) or under HIGH (noise) that is a body
RUMBLE = 0.3                         # a hiss over HISS with a body under this may be a hat over a rumble
BURST = 0.1                          # seconds: a bodiless noise burst ringing longer is an open hat, a snare or a short cymbal
OPEN = 0.24                          # seconds: and without the play, one ringing longer is the open hat
RATE = 32000                         # a sample plays at its own rate at pitch 0x1000
FRAMES = 4096                        # the spectrum's window, 128 ms at RATE
PIECES = ("kick", "snare", "hat", "other")


@dataclass
class Sound:
    """A drum sample measured: its power's shares under LOW and under HIGH,
    its centroid (Hz), its periodicity, its ring (seconds), and whether it loops."""
    low: float
    body: float
    bright: float
    tone: float
    ring: float
    loops: bool = False


def _fft(x: list) -> list:
    n = len(x)
    if n == 1:
        return x
    even, odd = _fft(x[0::2]), _fft(x[1::2])
    out = [0j] * n
    for k in range(n // 2):
        t = cmath.exp(-2j * math.pi * k / n) * odd[k]
        out[k], out[k + n // 2] = even[k] + t, even[k] - t
    return out


def _ring(pcm, rate: float) -> float:
    """Seconds until the sound has fallen 40 dB under its peak for good."""
    peak = max((abs(x) for x in pcm), default=0) or 1
    floor = peak / 100
    for i in range(len(pcm) - 1, -1, -1):
        if abs(pcm[i]) > floor:
            return (i + 1) / rate
    return 0.0


def measure(pcm, rate: float = RATE, loop: tuple | None = None, held: float | None = None) -> Sound:
    """A sample's Sound. rate: the rate it plays at (its own times the pitch
    ratio); loop: its loop (start, end) or None; held: seconds the game holds
    a looped one (it rings that long), a second if unknown."""
    pcm = list(pcm)
    if loop and loop[1] > loop[0] and loop[1] <= len(pcm):
        frames = int(rate * (held if held is not None else 1.0))
        tail = pcm[loop[0]:loop[1]]
        while len(pcm) < frames:
            pcm += tail
        pcm = pcm[:max(frames, loop[1])]
    seg = pcm[:FRAMES] + [0] * max(0, FRAMES - len(pcm))
    spec = _fft([complex(v * (0.5 - 0.5 * math.cos(2 * math.pi * i / FRAMES))) for i, v in enumerate(seg)])
    power = [abs(c) ** 2 for c in spec[:FRAMES // 2]]
    total = sum(power) or 1e-9
    hz = rate / FRAMES
    low = sum(p for i, p in enumerate(power) if i * hz < LOW) / total
    body = sum(p for i, p in enumerate(power) if i * hz < HIGH) / total
    bright = sum(i * hz * p for i, p in enumerate(power)) / total
    # periodicity: the autocorrelation of the first 64 ms, through the FFT of it zero-padded, its best
    # value past its first zero crossing (a tone's comes back up at the period; noise's stays down)
    n = FRAMES // 2
    auto = _fft([abs(c) ** 2 for c in _fft([complex(v) for v in seg[:n]] + [0j] * n)])   # the inverse, up to scale
    r0 = auto[0].real or 1e-9
    lo, hi = max(2, int(rate / 2000)), min(n // 2, int(rate / 40))
    dip = next((k for k in range(1, hi) if auto[k].real < 0), hi)
    tone = max((auto[k].real / r0 / (1 - k / n) for k in range(max(lo, dip), hi)), default=0.0)
    return Sound(low, body, bright, min(1.0, max(0.0, tone)), _ring(pcm, rate), bool(loop))


def _play(profile: dict | None) -> tuple | None:
    """How a sample is played: its hits' shares on the bar's first beat, on
    its other beats, off the beat; None without a profile."""
    if not profile or not profile.get("hits"):
        return None
    one, back = profile["one"] / profile["hits"], (profile["back"] + profile.get("three", 0)) / profile["hits"]
    return one, back, 1 - one - back


def name(s: Sound, profile: dict | None = None) -> str:
    """The piece a Sound is (PIECES; the module's rule). profile: how the
    game plays it (rhythm.sounds's: hits, one, three, back), which settles
    the four cases the sound leaves open."""
    play = _play(profile)
    if s.low >= 0.5:
        if s.bright < KICK_HZ:
            return "kick"
        if s.tone >= PITCHED or (s.bright >= TOM_HZ and s.tone >= TONE):
            return "other"
        if s.bright >= TOM_HZ:
            return "snare"
        return "kick" if play and play[0] + play[1] > play[2] else "other"
    if s.tone < TONE or (s.bright >= HISS and s.tone < PITCHED):
        if s.ring >= LONG:
            return "other"
        if s.ring >= RING and s.body < BODY:
            return "snare" if play and play[1] > play[0] else "other"
        if s.body >= BODY:
            if s.ring < CLICK:
                return "other"
            if s.bright >= HISS and s.body < RUMBLE and play and play[2] > play[0] + play[1]:
                return "hat"
            return "snare"
        if s.ring < BURST:
            return "hat"
        if play:
            return ("other", "snare", "hat")[play.index(max(play))]
        return "snare" if s.ring < OPEN else "hat"
    return "snare" if s.low >= BODY else "other"


def generator() -> dict:
    """The generator's named drums: preset -> the piece it is, from the
    built-in packs' kits and the palettes' names (open hats are hats; toms,
    crashes and rims other sounds)."""
    from .. import packs
    from ..samples import INSTRUMENT_PRESETS, is_percussion
    piece = {"kick": "kick", "bassdrum": "kick", "snare": "snare", "hat": "hat", "hihat": "hat", "open_hihat": "hat",
             "tom": "other", "crash": "other", "cymbal": "other", "rim": "other"}
    out = {}
    for pack in packs.PACKS.values():
        for slot, preset in pack.get("voices", {}).get("drums", {}).items():
            out[preset] = piece[slot]
    for preset in INSTRUMENT_PRESETS:
        if preset not in out and is_percussion(preset):
            found = [piece[w] for w in preset.split("_") if w in piece]
            if found:
                out[preset] = found[0]
    return out


def of_preset(preset: str) -> Sound:
    """A generator preset measured, as it comes (its own rate, its loop)."""
    import struct
    from ..samples import generate_instrument
    inst = generate_instrument(preset)
    pcm = struct.unpack(f"<{inst['length']}h", inst["data"])
    return measure(pcm, inst["rate"], (inst["loop_start"], inst["loop_end"]) if inst["loop"] else None)


def score() -> tuple[int, int, list]:
    """How many of the generator's named drums the rule names right without
    being told: (right, all, [(preset, its name, the rule's)] for the rest)."""
    missed = []
    truth = generator()
    for preset, piece in sorted(truth.items()):
        got = name(of_preset(preset))
        if got != piece:
            missed.append((preset, piece, got))
    return len(truth) - len(missed), len(truth), missed


class Bank:
    """A database's drum samples decoded from the game's SPC files under
    `root` (the folders the songs table names under it, or one game's own
    folder), each read once; a file missing leaves its samples unnamed."""

    def __init__(self, db, root: str):
        self.root = os.path.expanduser(root)
        self.where = {}
        for sid, folder, file in db.execute("SELECT id, folder, file FROM songs"):
            for key, start, loop, f0 in db.execute("SELECT key, start, loop, f0 FROM samples WHERE song = ?", (sid,)):
                self.where.setdefault(key, (folder, file, start, loop, f0))
        self.snaps, self.sounds = {}, {}

    def _path(self, folder: str, file: str) -> str | None:
        for p in (os.path.join(self.root, folder, file), os.path.join(self.root, file)):
            if os.path.exists(p):
                return p
        return None

    def pcm(self, key: str):
        """A sample's (pcm, loop) as the SNES chip's interpolation colours it, or None."""
        from .. import spc
        from ..spc import brr, snes_chip
        if key not in self.where:
            return None
        folder, file, start, loop, _ = self.where[key]
        path = self._path(folder, file)
        if path is None:
            return None
        if path not in self.snaps:
            try:
                self.snaps[path] = spc.read(path)
            except Exception:
                self.snaps[path] = None
        snap = self.snaps[path]
        s = brr.decode(snap.ram, start, loop) if snap and 0 < start < 0xFFC0 else None
        if s is None or len(s) < 16:
            return None
        lp = (s.loop_start, s.loop_end) if s.loops and s.loop_end > s.loop_start else None
        return snes_chip.snes_interpolated(s.pcm, lp), lp

    def sound(self, key: str, midi: float | None = None, held: float | None = None) -> Sound | None:
        """A sample's Sound as the game plays it (midi: the pitch it plays it
        at most; held: seconds it holds a looped one), measured once."""
        if key not in self.sounds:
            got = self.pcm(key)
            if got is None:
                self.sounds[key] = None
            else:
                pcm, loop = got
                if not any(pcm):
                    self.sounds[key] = None               # silent: the voice plays the noise generator over it
                    return None
                f0 = self.where[key][4]
                ratio = 440 * 2 ** ((midi - 69) / 12) / f0 if midi is not None and f0 else 1.0
                self.sounds[key] = measure(pcm, RATE * ratio, loop, held)
        return self.sounds[key]


class Kit:
    """The generator's kit as a bank: a composed song's drum keys are its
    presets' names (against.py), measured as they come."""

    def __init__(self):
        self.sounds = {}

    def sound(self, key: str, midi: float | None = None, held: float | None = None) -> Sound | None:
        from ..samples import INSTRUMENT_PRESETS
        if key not in self.sounds:
            self.sounds[key] = of_preset(key) if key in INSTRUMENT_PRESETS else None
        return self.sounds[key]


def names(bank, sounds: dict) -> dict:
    """Each drum sample named by its sound where the bank (a Bank or a Kit)
    has it: {key: name}, sounds being rhythm.sounds's profiles (their midi
    and held seconds set the measure, their hits settle a bodiless burst)."""
    out = {}
    for key, p in sounds.items():
        s = bank.sound(key, p.get("midi"), p.get("held")) if bank else None
        if s is not None:
            out[key] = name(s, p)
    return out


def report(db, root: str, game: str | None = None) -> str:
    """Each drum sample's measures, its name by sound and by how it is played."""
    from . import rhythm
    songs, _ = rhythm.load(db, game)
    sounds = rhythm.sounds(songs)
    bank = Bank(db, root)
    out = [f"drum sounds of {game or 'the database'}: {len(sounds)} samples in {sum(1 for s in songs if 'drums' in s.notes)} songs",
           f"  {'sample':10s} {'songs':>5s} {'hits':>6s} {'a bar':>5s} {'low':>5s} {'body':>5s} {'bright':>6s} {'tone':>5s}"
           f" {'ring':>5s} loop  by sound  by play"]
    tally = Counter()
    for key, p in sorted(sounds.items(), key=lambda kv: -kv[1]["hits"]):
        s = bank.sound(key, p.get("midi"), p.get("held"))
        by_sound = name(s, p) if s else "?"
        tally[by_sound] += 1
        cells = (f"{s.low:5.2f} {s.body:5.2f} {s.bright:6.0f} {s.tone:5.2f} {s.ring:5.2f} {'loop' if s.loops else '    '}"
                 if s else f"{'(no file)':>35s}")
        out.append(f"  {key[:10]:10s} {p['songs']:5d} {p['hits']:6d} {p['a_bar']:5.1f} {cells}  {by_sound:8s}  {rhythm._name(p)}")
    out.append("  by sound: " + ", ".join(f"{k} {tally[k]}" for k in PIECES + ("?",) if tally[k]))
    return "\n".join(out)


def main(argv=None) -> int:
    from . import store
    ap = argparse.ArgumentParser(prog="python -m bitcomposer.translate.drums", description=__doc__.split("\n\n")[0])
    ap.add_argument("--score", action="store_true", help="name the generator's own drums and say how many come out right")
    ap.add_argument("--db", help="the readings database (default: ~/.local/share/bitcomposer/readings.db)")
    ap.add_argument("--spc", metavar="DIR", help="the game folders' root, or one game's folder")
    ap.add_argument("--game", help="only this game's songs (the songs table's game)")
    args = ap.parse_args(argv)
    if args.score:
        right, total, missed = score()
        print(f"the generator's named drums: {right} of {total} named as they are"
              + ("; missed: " + ", ".join(f"{p} ({piece}) named {got}" for p, piece, got in missed) if missed else ""))
        return 0
    if not args.spc:
        ap.error("--spc DIR (the SPC files) or --score")
    print(report(store.connect(args.db), args.spc, args.game))
    return 0


if __name__ == "__main__":
    sys.exit(main())
