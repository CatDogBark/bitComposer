"""The echo: its per-song settings tables and the bus that turns them into
taps and darker sample variants for the pattern layer."""

from . import samples as smp
from .it_format import ITSample
from .pattern import CH_MELODY, CH_HARMONY, CH_HARMONY2, CH_HARMONY3, CH_ARP, CH_ECHO1, CH_ECHO2, CH_ECHO_HARMONY, CH_ECHO_ARP
from .instruments import (_register_releases, _sample_from_inst)


# Echo, modelled on the SNES echo unit's result rather than its wiring:
# repeats on a beat fraction (three rows is a dotted eighth at four rows to
# the beat), each one quieter by the feedback and darker through a lowpass,
# one delay for the whole song, drums and bass dry. The hardware had one
# on/off bit per voice; we send each part at its own level: the lead wet,
# the harmony and arp lighter. A tap's channel may be shared (lead taps 1
# and 3; both harmony taps) and pattern.plan_echo lets the louder win.
ECHO_TAP_CUTOFF_HZ = (4000, 2000, 1000)   # two-pole lowpass on the sample each tap plays
# Per-song echo settings, drawn from their own stream (song_salt ^ 0xEC40) so
# a seed's arrangement does not move when they change. Delay in rows is picked
# for the tempo so the repeat stays a musical fraction in a 180-450 ms band:
# fast songs favour the dotted eighth and quarter, slow songs the eighth.
# "slap" is the Mega Man X echo: 48 ms, under a row, written as a tick delay
# (SDx) on the copy's note row instead of a pan, so it takes the channel's pan.
# "row" is one row (100-150 ms at 100-150 BPM): the Secret of Mana echo sits
# at 96 and 176 ms, between the slap and the eighth; only packs draw it.
ECHO_DELAYS = {"eighth": 2, "dotted": 3, "quarter": 4, "slap": 0.5, "row": 1}
ECHO_DELAY_WEIGHTS = [        # (min bpm, {name: weight})
    (140, {"eighth": 1, "dotted": 5, "quarter": 4}),
    (100, {"eighth": 2, "dotted": 6, "quarter": 2}),
    (0,   {"eighth": 5, "dotted": 4, "quarter": 1}),
]
ECHO_FEEDBACK_RANGE = (0.3, 0.6)    # each further repeat relative to the last
ECHO_WET_WEIGHTS = {"light": 1, "normal": 2, "wet": 1}
# How the repeats sit in the stereo field. "bounce" alternates sides per tap,
# an effect the ear files as an effect. "centre" puts every repeat under its
# source, on the source's own side: the hardware's echo came back on both
# sides at once, behind the voice, and reads as a room. An earlier "spread"
# mode put every repeat hard on the far side of the part, and a copy arriving
# a quarter second late from another direction is heard as a second player
# coming in late (Sunlit Expanse, Veiled Meridian), so it is gone. Pans are
# IT Xxx values (0-255); the sources sit at melody 128, harmony 80/128/176,
# arp 160 (DEFAULT_CHANNEL_PANS, 0-64, times 4).
ECHO_STEREO_WEIGHTS = {"bounce": 3, "centre": 2}
ECHO_PANS = {
    "bounce": {"melody": (40, 215, 40), "harmony": ((200, 56), (56, 200), (56, 200)), "arp": (60, 200)},
    "centre": {"melody": (128, 128, 128), "harmony": ((80, 80), (128, 128), (176, 176)), "arp": (160, 160)},
}
# The hardware echoed at one level all song; we open it where the texture is
# thin and pull it back where the arp and harmony fill the space.
ECHO_SECTION_GAIN = {"intro": 1.3, "bridge": 1.3, "outro": 1.25, "verse": 1.0, "chorus": 0.7}
# Per sent role: first-repeat level (fraction of the part) and tap channels.
# Harmony has three source channels, one return channel each.
ECHO_SENDS = {
    "melody": (0.5, (CH_ECHO1, CH_ECHO2, CH_ECHO1)),
    "harmony": (0.3, None),                       # per voice: (ch, ch)
    "arp": (0.35, CH_ECHO_ARP),
}
# --echo-wet scales every send; "random" is "normal" until the per-song
# wetness pass (stage three) draws it.
ECHO_WETNESS = {"light": 0.6, "normal": 1.0, "wet": 1.5, "random": 1.0}
# Per-note send: the hardware echoed everything a voice played; we send held
# notes (>= 4 rows, a quarter note) and phrase endings (a rest of >= 2 rows
# follows) and leave fast runs dry, so the tail reads as a tail.
ECHO_SEND_HOLD = 4
ECHO_SEND_REST = 2
# The arp sends only its accented steps (strong and normal, not weak: arp.py
# writes them at 1.0 / 0.8 / 0.62 of the arp level), and the whole arp send
# tapers with tempo: full to ECHO_ARP_FULL_BPM, gone by ECHO_ARP_OFF_BPM. At
# 180 BPM a dotted-eighth repeat of an eighth-note pizzicato landed one row
# after every pluck and the arp turned into a stream of ticks.
ECHO_ARP_ACCENT = 0.7
ECHO_ARP_FULL_BPM = 130
ECHO_ARP_OFF_BPM = 170


def _echo_label(use_echo: bool, echo_wet: str) -> str:
    if not use_echo:
        return ""
    return " + echo" if echo_wet == "normal" else f" + echo ({echo_wet})"


class _EchoBus:
    """The song's echo: the sends, their taps and the darker samples they play.

    Each tap has its own lowpass cutoff, so each preset that passes through
    the echo gets one variant sample per distinct cutoff, made on first use
    (the alternate lead arrives mid-song). sends() yields what
    pattern.apply_echo_taps wants per source channel: (src, taps, hold, rest)
    with taps = [(channel, delay, level, {source instrument: variant})].
    """

    def __init__(self, samples: list[ITSample], wet: float = 1.0, delay: float = 3,
                 feedback: float = 0.5, stereo: str = "bounce", arp_scale: float = 1.0,
                 speed: int = 6):
        self.samples = samples
        self.wet, self.delay, self.feedback, self.stereo = wet, delay, feedback, stereo
        self.arp_scale, self.speed = arp_scale, speed
        self._variants: dict[tuple[str, float, bool], int] = {}
        self._maps: list[dict[int, int]] = [dict() for _ in ECHO_TAP_CUTOFF_HZ]

    def add_source(self, src_idx: int, preset: str, strike_rule: bool = False) -> None:
        if src_idx in self._maps[0]:
            return
        for k, cutoff in enumerate(ECHO_TAP_CUTOFF_HZ):
            key = (preset, cutoff, strike_rule)
            if key not in self._variants:
                inst = smp.echo_variant(preset, cutoff, strike_rule=strike_rule)
                self.samples.append(_sample_from_inst(f"{preset}_echo{int(cutoff) // 1000}k", inst))
                self._variants[key] = len(self.samples)
            self._maps[k][src_idx] = self._variants[key]
        _register_releases(self.samples)

    def _taps(self, level: float, channels, pans, gain: float = 1.0):
        taps = []
        for k, ch in enumerate(channels):
            lvl = min(1.0, level * self.wet * gain) * self.feedback ** k
            if lvl < 0.08:
                break                         # below this a repeat is not heard
            total = self.delay * (k + 1)
            rows = int(total)
            ticks = int(round((total - rows) * self.speed))
            if ticks >= self.speed:
                rows, ticks = rows + 1, 0
            if ticks:
                taps.append((ch, rows, lvl, self._maps[k], None, ticks))
            else:
                taps.append((ch, rows, lvl, self._maps[k], pans[k]))
        return taps

    def sends(self, sec_type: str = "verse") -> list[tuple[int, list, int, int, float]]:
        """(source channel, taps, hold, rest, accent) for every sent part in a section."""
        gain = ECHO_SECTION_GAIN.get(sec_type, 1.0)
        pans = ECHO_PANS[self.stereo]
        out = [(CH_MELODY, self._taps(*ECHO_SENDS["melody"], pans["melody"], gain),
                ECHO_SEND_HOLD, ECHO_SEND_REST, 0.0)]
        level, _ = ECHO_SENDS["harmony"]
        for v, (src, ret) in enumerate(zip((CH_HARMONY, CH_HARMONY2, CH_HARMONY3), CH_ECHO_HARMONY)):
            out.append((src, self._taps(level, (ret, ret), pans["harmony"][v], gain), 0, 0, 0.0))
        arp_level, arp_channels = ECHO_SENDS["arp"]
        out.append((CH_ARP, self._taps(arp_level * self.arp_scale, arp_channels, pans["arp"], gain),
                    0, 0, ECHO_ARP_ACCENT))
        return out

    def describe(self) -> str:
        name = next(n for n, rows in ECHO_DELAYS.items() if rows == self.delay)
        if name == "slap":
            return f"slap delay, feedback {self.feedback:.2f}, {self.stereo}"
        return f"{name} delay, feedback {self.feedback:.2f}, {self.stereo}"
