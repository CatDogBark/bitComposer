"""Classic is frozen. Every song it writes for a fixed seed and fixed options is, byte for byte, the file it wrote
when it was locked (classic_lock.json: each case's options and the sha256 of its file).

One line of a Classic song follows the release: its message ends "bitcomposer <version>". The lock sets that line
aside by composing with VERSION in the version's place, so a release moves no checksum.

The cases are written through the command line's own path (cli.compose_from_args, which is also how the player
composes), on Classic's own sounds: every sound over five seeds, the random pick, and every choice of every option
Classic takes. A second test holds the cases to the parser, so an option or a choice added later cannot go
unlocked.

The lock is not regenerated to make a failing change pass: a Classic song that changes is a fault in the change.
`python tests/test_classic_lock.py --write` writes the file, and is for the day Classic is changed on purpose."""
import hashlib
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from bitcomposer import cli, composer  # noqa: E402

LOCK = os.path.join(HERE, "classic_lock.json")
VERSION = "locked"
SOUNDS = ("chip", "snes", "genesis", "bit", "ffvi", "mana", "evermore", "megamanx")
SEEDS = (1, 2, 3, 4, 5)
# The options that are not Classic's (the writer's, the file's name and place) or are fixed by the lock itself.
NOT_LOCKED = {"--help", "--output", "--output-dir", "--name", "--prefix", "--suffix", "--seed", "--count", "--verbose",
              "--pack-file", "--score", "--classic", "--vocabulary", "--carry-theme", "--no-carry-theme", "--band-returns",
              "--no-band-returns", "--bare", "--version"}
ONE_OFF = {"--no-fills": [["--no-fills"]], "--lead-shift": [["--lead-shift", "-3"], ["--lead-shift", "4"]]}


def cases() -> dict:
    """Every locked case: its name -> the command line's options (the seed among them)."""
    out = {}
    for sound in SOUNDS:
        for seed in SEEDS:
            out[f"{sound} {seed}"] = ["--sound", sound, "-s", str(seed)]
    for seed in range(11, 17):
        out[f"random {seed}"] = ["-s", str(seed)]
    seed = 20
    for action in cli.build_parser()._actions:
        flag = action.option_strings[-1] if action.option_strings else None
        if flag is None or flag in NOT_LOCKED:
            continue
        for extra in ONE_OFF.get(flag) or [[flag, c] for c in action.choices if c not in ("random", "moving")]:
            seed += 1
            out[" ".join(extra).lstrip("-")] = [*extra, "-s", str(seed)]
    return out


def write(options: list, path: str) -> None:
    """One Classic song as the command line writes it, the release's version set aside."""
    args = cli.build_parser().parse_args(["--classic", *options, "-o", path])
    with mock.patch.object(composer, "__version__", VERSION):
        cli.compose_from_args(args, 0)


def checksums() -> dict:
    out = {}
    with tempfile.TemporaryDirectory() as d:
        for name, options in cases().items():
            path = os.path.join(d, "song.it")
            write(options, path)
            out[name] = {"options": options, "sha256": hashlib.sha256(open(path, "rb").read()).hexdigest()}
    return out


class ClassicLock(unittest.TestCase):
    def test_every_locked_song_is_the_file_it_was(self):
        locked = json.load(open(LOCK, encoding="utf-8"))["songs"]
        now = checksums()
        self.assertEqual(sorted(now), sorted(locked))
        self.assertEqual({n: c["options"] for n, c in now.items()}, {n: c["options"] for n, c in locked.items()})
        changed = sorted(n for n in locked if now[n]["sha256"] != locked[n]["sha256"])
        self.assertEqual(changed, [], f"{len(changed)} of {len(locked)} Classic songs are no longer the files they were")

    def test_the_lock_holds_every_sound_and_every_choice_classic_takes(self):
        locked = json.load(open(LOCK, encoding="utf-8"))["songs"]
        self.assertGreaterEqual(len(locked), 100)
        said = [c["options"] for c in locked.values()]
        for action in cli.build_parser()._actions:
            flag = action.option_strings[-1] if action.option_strings else None
            if flag is None or flag in NOT_LOCKED:
                continue
            if not action.choices:
                self.assertTrue(any(flag in o for o in said), flag)
                continue
            for choice in action.choices:
                if choice in ("random", "moving"):       # the defaults: every case without the flag
                    continue
                self.assertTrue(any(flag in o and o[o.index(flag) + 1] == choice for o in said), f"{flag} {choice}")
        for sound in SOUNDS:
            self.assertEqual(sum(1 for o in said if o[:2] == ["--sound", sound]), len(SEEDS) + 1, sound)
        self.assertEqual(sum(1 for o in said if o[0] == "-s"), 6)                    # the random pick


if __name__ == "__main__":
    if sys.argv[1:] == ["--write"]:
        with open(LOCK, "w", encoding="utf-8") as fh:
            json.dump({"what": "Classic's songs as they were locked: each case's options (after --classic) and the sha256 of its "
                               "file, composed with the version in its message set to " + repr(VERSION),
                       "songs": checksums()}, fh, indent=1)
            fh.write("\n")
        print("wrote", LOCK)
    else:
        unittest.main()
