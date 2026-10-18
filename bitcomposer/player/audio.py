"""Audio output for the player: raw 16-bit stereo PCM to the platform's
device, through nothing but the standard library.

Linux: a pipe into paplay (PulseAudio or PipeWire's compatibility layer),
or pw-cat, or aplay. Windows: waveOut through winmm by ctypes. Each backend
has open(), write(bytes) that blocks while the device is full, and close().
"""
import ctypes
import shutil
import subprocess
import sys
import time

CHANNELS = 2
LATENCY_MS = 150


class OutputUnavailable(RuntimeError):
    pass


class PipeOutput:
    """A command that reads s16le stereo PCM on stdin."""

    COMMANDS = {
        "paplay": lambda rate: ["paplay", "--format=s16le", f"--rate={rate}", f"--channels={CHANNELS}", "--raw",
                                f"--latency-msec={LATENCY_MS}", "--stream-name=bitComposer"],
        "pw-cat": lambda rate: ["pw-cat", "--playback", "--format=s16", f"--rate={rate}", f"--channels={CHANNELS}",
                                "--raw", "-"],
        "aplay": lambda rate: ["aplay", "-q", "-t", "raw", "-f", "S16_LE", "-r", str(rate), "-c", str(CHANNELS)],
    }

    def __init__(self, rate: int):
        self.rate = rate
        self.proc = None
        self.command = next((c for c in self.COMMANDS if shutil.which(c)), None)
        if not self.command:
            raise OutputUnavailable("no audio player found: install pulseaudio-utils (paplay), pipewire-bin (pw-cat) or alsa-utils (aplay)")

    def open(self):
        self.proc = subprocess.Popen(self.COMMANDS[self.command](self.rate), stdin=subprocess.PIPE,
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def write(self, data: bytes) -> bool:
        try:
            self.proc.stdin.write(data)
            self.proc.stdin.flush()
            return True
        except (BrokenPipeError, OSError):
            return False

    def close(self):
        if self.proc:
            try:
                self.proc.kill()
                self.proc.wait(timeout=0.5)
            except Exception:
                pass
            self.proc = None


class WaveOutOutput:
    """winmm waveOut with a ring of prepared buffers."""

    WAVE_FORMAT_PCM = 1
    WAVE_MAPPER = 0xFFFFFFFF
    WHDR_DONE = 0x1
    CALLBACK_NULL = 0
    BUFFERS = 6

    class WAVEFORMATEX(ctypes.Structure):
        _fields_ = [("wFormatTag", ctypes.c_ushort), ("nChannels", ctypes.c_ushort), ("nSamplesPerSec", ctypes.c_uint),
                    ("nAvgBytesPerSec", ctypes.c_uint), ("nBlockAlign", ctypes.c_ushort), ("wBitsPerSample", ctypes.c_ushort),
                    ("cbSize", ctypes.c_ushort)]

    class WAVEHDR(ctypes.Structure):
        pass

    WAVEHDR._fields_ = [("lpData", ctypes.c_void_p), ("dwBufferLength", ctypes.c_uint), ("dwBytesRecorded", ctypes.c_uint),
                        ("dwUser", ctypes.c_void_p), ("dwFlags", ctypes.c_uint), ("dwLoops", ctypes.c_uint),
                        ("lpNext", ctypes.POINTER(WAVEHDR)), ("reserved", ctypes.c_void_p)]

    def __init__(self, rate: int):
        self.rate = rate
        try:
            self.winmm = ctypes.windll.winmm
        except AttributeError as e:
            raise OutputUnavailable("winmm is not available") from e
        self.hwo = ctypes.c_void_p()
        self.headers = []
        self.buffers = []
        self.next = 0

    def open(self):
        fmt = self.WAVEFORMATEX(self.WAVE_FORMAT_PCM, CHANNELS, self.rate, self.rate * CHANNELS * 2, CHANNELS * 2, 16, 0)
        rc = self.winmm.waveOutOpen(ctypes.byref(self.hwo), self.WAVE_MAPPER, ctypes.byref(fmt), 0, 0, self.CALLBACK_NULL)
        if rc != 0:
            raise OutputUnavailable(f"waveOutOpen failed ({rc})")
        self.headers, self.buffers, self.next = [], [], 0

    def write(self, data: bytes) -> bool:
        if len(self.headers) < self.BUFFERS:
            buf = ctypes.create_string_buffer(data, len(data))
            hdr = self.WAVEHDR()
            hdr.lpData = ctypes.cast(buf, ctypes.c_void_p)
            hdr.dwBufferLength = len(data)
            hdr.dwFlags = 0
            self.buffers.append(buf)
            self.headers.append(hdr)
            idx = len(self.headers) - 1
        else:
            idx = self.next
            self.next = (self.next + 1) % self.BUFFERS
            hdr = self.headers[idx]
            while not (hdr.dwFlags & self.WHDR_DONE):
                time.sleep(0.002)
            self.winmm.waveOutUnprepareHeader(self.hwo, ctypes.byref(hdr), ctypes.sizeof(hdr))
            buf = ctypes.create_string_buffer(data, len(data))
            self.buffers[idx] = buf
            hdr.lpData = ctypes.cast(buf, ctypes.c_void_p)
            hdr.dwBufferLength = len(data)
            hdr.dwFlags = 0
        if self.winmm.waveOutPrepareHeader(self.hwo, ctypes.byref(hdr), ctypes.sizeof(hdr)) != 0:
            return False
        return self.winmm.waveOutWrite(self.hwo, ctypes.byref(hdr), ctypes.sizeof(hdr)) == 0

    def close(self):
        if self.hwo:
            try:
                self.winmm.waveOutReset(self.hwo)
                for hdr in self.headers:
                    self.winmm.waveOutUnprepareHeader(self.hwo, ctypes.byref(hdr), ctypes.sizeof(hdr))
                self.winmm.waveOutClose(self.hwo)
            except Exception:
                pass
            self.hwo = ctypes.c_void_p()
        self.headers, self.buffers = [], []


class NullOutput:
    """Paces like a device, plays nothing (tests, a machine with no audio)."""

    def __init__(self, rate: int):
        self.rate = rate

    def open(self):
        pass

    def write(self, data: bytes) -> bool:
        time.sleep(len(data) / (self.rate * CHANNELS * 2))
        return True

    def close(self):
        pass


def make_output(rate: int, kind: str | None = None):
    if kind == "null":
        return NullOutput(rate)
    if sys.platform.startswith("win"):
        return WaveOutOutput(rate)
    return PipeOutput(rate)
