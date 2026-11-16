"""The wall around Classic (bitcomposer/classic/), held.

Classic is the 1.x generator behind `--classic`. It does a different thing from the writer and is frozen: it keeps
the sounds and the code it had on the day it was walled off, and nothing done for the writer may reach it. These
tests hold what that means:

- every file in the folder is the file it was (classic_wall.json: its path and the sha256 of its text), and the
  folder holds those files and no others;
- nothing in the folder imports from outside it, the standard library and the package's version apart;
- code outside the folder takes Classic through its front door (the names in bitcomposer/classic/__init__.py's
  __all__) and reaches no deeper; Classic's own tests (tests/test_classic_*.py) are Classic's and do reach in;
- a written song loads none of Classic;
- Classic reads no pack file: a pack loaded for the writer is not among Classic's sounds.

tests/test_classic_lock.py holds Classic's songs themselves. Neither file's checksums are written again to make a
change pass. `python tests/test_classic_wall.py --write` writes classic_wall.json, for the day Classic is changed on
purpose."""
import ast
import hashlib
import json
import os
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
PACKAGE = os.path.join(ROOT, "bitcomposer")
WALL = os.path.join(PACKAGE, "classic")
MANIFEST = os.path.join(HERE, "classic_wall.json")
OUTSIDE = (PACKAGE, os.path.join(ROOT, "tools"))            # the code held to the front door


def python_files(top: str) -> list:
    out = []
    for folder, dirs, files in os.walk(top):
        dirs[:] = sorted(d for d in dirs if d != "__pycache__")
        out += [os.path.join(folder, f) for f in sorted(files) if f.endswith(".py")]
    return out


def checksums() -> dict:
    """Each file of the wall by its path from the folder: the sha256 of its text, line ends as "\\n" (a checkout that
    turns them into "\\r\\n" holds the same files)."""
    out = {}
    for path in python_files(WALL):
        text = open(path, "rb").read().replace(b"\r\n", b"\n")
        out[os.path.relpath(path, WALL).replace(os.sep, "/")] = hashlib.sha256(text).hexdigest()
    return out


def module_of(path: str) -> str:
    """A file's module name: bitcomposer/classic/packs/bit.py -> bitcomposer.classic.packs.bit."""
    name = os.path.relpath(path, ROOT)[:-3].replace(os.sep, ".")
    return name[:-len(".__init__")] if name.endswith(".__init__") else name


def imports(path: str) -> list:
    """Every import in a file, anywhere in it: (the module it names, resolved from the file's own package where it is
    relative; the names taken from it, None for a plain `import x`; the line)."""
    module = module_of(path)
    package = module if path.endswith("__init__.py") else module.rpartition(".")[0]
    out = []
    for node in ast.walk(ast.parse(open(path, encoding="utf-8").read(), path)):
        if isinstance(node, ast.Import):
            out += [(a.name, None, node.lineno) for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            if node.level:
                parts = package.split(".")
                parts = parts[:len(parts) - (node.level - 1)]
                base = ".".join(parts + ([node.module] if node.module else []))
            out.append((base, [a.name for a in node.names], node.lineno))
    return out


class ClassicWall(unittest.TestCase):
    def test_every_file_behind_the_wall_is_the_file_it_was(self):
        held = json.load(open(MANIFEST, encoding="utf-8"))["files"]
        now = checksums()
        self.assertEqual(sorted(now), sorted(held), "the folder holds other files than it did")
        changed = sorted(p for p in held if now[p] != held[p])
        self.assertEqual(changed, [], "Classic is frozen: these files changed")
        self.assertEqual(len(held), 27 + 1)                                  # its 27 modules and the front door
        others = [f for folder, _, files in os.walk(WALL) for f in files if not f.endswith((".py", ".pyc"))]
        self.assertEqual(others, [])

    def test_nothing_behind_the_wall_imports_from_outside_it(self):
        standard = set(sys.stdlib_module_names)
        for path in python_files(WALL):
            where = os.path.relpath(path, ROOT)
            for name, names, line in imports(path):
                if name == "bitcomposer.classic" or name.startswith("bitcomposer.classic."):
                    continue
                if name == "bitcomposer" and names == ["__version__"] and where == os.path.join("bitcomposer", "classic", "__init__.py"):
                    continue                                                 # the one thing taken: a song's message records it
                self.assertIn(name.split(".")[0], standard, f"{where}:{line} imports {name}")
                self.assertNotEqual(name.split(".")[0], "bitcomposer", f"{where}:{line} imports {name}")

    def test_outside_code_takes_classic_through_its_front_door(self):
        import bitcomposer.classic as classic
        door = set(classic.__all__)
        self.assertEqual(door, {"SOUNDS", "STYLES", "compose_and_save", "compose_song", "resolve_sound", "save_song", "theory"})
        took = 0
        for top in OUTSIDE:
            for path in python_files(top):
                if path.startswith(WALL + os.sep):
                    continue
                where = os.path.relpath(path, ROOT)
                for name, names, line in imports(path):
                    if name == "bitcomposer.classic":
                        self.assertIsNotNone(names, f"{where}:{line}: take names from the front door, not the module")
                        self.assertLessEqual(set(names), door, f"{where}:{line} takes {sorted(set(names) - door)} past the front door")
                        took += 1
                    else:
                        self.assertFalse(name.startswith("bitcomposer.classic."), f"{where}:{line} reaches into {name}")
                        if name == "bitcomposer" and names:
                            self.assertNotIn("classic", names, f"{where}:{line}: take names from bitcomposer.classic")
        self.assertGreaterEqual(took, 3)                                     # the command line and the readers' tools do take it

    def test_a_written_song_loads_none_of_classic(self):
        program = ("import os, sys, tempfile\n"
                   "from bitcomposer import cli\n"
                   "import bitcomposer.player.engine\n"
                   "with tempfile.TemporaryDirectory() as d:\n"
                   "    cli.compose_from_args(cli.build_parser().parse_args(['-s', '3', '-o', os.path.join(d, 'song.it')]), 0)\n"
                   "print(sorted(m for m in sys.modules if m.startswith('bitcomposer.classic')))\n")
        r = subprocess.run([sys.executable, "-c", program], cwd=ROOT, capture_output=True, text=True, timeout=600,
                           env=dict(os.environ, PYTHONPATH=ROOT, QT_QPA_PLATFORM="offscreen"))
        if r.returncode != 0 and "PySide6" in r.stderr:                      # the player's window is not installed here: without it
            r = subprocess.run([sys.executable, "-c", program.replace("import bitcomposer.player.engine\n", "")], cwd=ROOT,
                               capture_output=True, text=True, timeout=600, env=dict(os.environ, PYTHONPATH=ROOT))
        self.assertEqual(r.returncode, 0, r.stderr[-2000:])
        self.assertEqual(r.stdout.strip().splitlines()[-1], "[]")

    def test_classic_reads_no_pack_file_and_has_its_own_sounds(self):
        import tempfile
        import wave
        import bitcomposer.classic as classic
        from bitcomposer import packs, samples
        from bitcomposer.packs import packfile
        self.assertFalse(os.path.exists(os.path.join(WALL, "packs", "packfile.py")))
        self.assertIsNot(classic.packs.PACKS, packs.PACKS)
        self.assertIsNot(classic.samples.INSTRUMENT_PRESETS, samples.INSTRUMENT_PRESETS)
        self.assertEqual(sorted(classic.packs.PACKS), ["bit", "evermore", "ffvi", "mana", "megamanx"])
        self.assertEqual(classic.SOUNDS, ["chip", "snes", "genesis", "bit", "ffvi", "mana", "evermore", "megamanx"])
        before = set(classic.samples.INSTRUMENT_PRESETS)
        with tempfile.TemporaryDirectory() as d:
            with wave.open(os.path.join(d, "tone.wav"), "wb") as w:
                w.setnchannels(1); w.setsampwidth(2); w.setframerate(22050)
                w.writeframes(b"".join(int(12000 * ((i % 50) / 25.0 - 1.0)).to_bytes(2, "little", signed=True) for i in range(11025)))
            path = os.path.join(d, "pack.json")
            json.dump({"bitcomposer_pack": 1, "name": "wallpack", "label": "Wall pack", "palette": "snes", "voices": {"lead": ["tone"]},
                       "samples": {"tone": {"file": "tone.wav", "hz": 441, "loop": [5000, 11025], "release": "flute"}}}, open(path, "w"))
            name = packfile.load_pack_file(path)
            self.addCleanup(packfile.unload, name)
            self.assertIn(name, packs.PACKS)                                 # the writer's
            self.assertIn("wallpack_tone", samples.INSTRUMENT_PRESETS)
            self.assertNotIn(name, classic.packs.PACKS)                      # and not Classic's
            self.assertEqual(set(classic.samples.INSTRUMENT_PRESETS), before)
            with self.assertRaises(Exception):
                classic.compose_song(seed=1, pack=name)


if __name__ == "__main__":
    if sys.argv[1:] == ["--write"]:
        with open(MANIFEST, "w", encoding="utf-8") as fh:
            json.dump({"what": "bitcomposer/classic/ as it was walled off: each file's path from the folder and the sha256 of its "
                               "text with line ends as \\n", "files": checksums()}, fh, indent=1)
            fh.write("\n")
        print("wrote", MANIFEST)
    else:
        unittest.main()
