"""Every SPC under a root through VGMTrans's shell, its sequences exported as MIDI (phase 1 of
docs/IDIOM.md). A developer tool for the machine that holds the games and a VGMTrans build.

    python tools/vgmtrans_batch.py SHELL SPC_ROOT OUT_DIR [--workers N]

SHELL is the vgmtrans-shell executable. Each song is loaded through a symlink without spaces (the
shell splits its line on them), every sequence it parses is exported as OUT_DIR/<game>/<song>.mid
(a second and later sequence as <song>#2.mid and on), and OUT_DIR/survey.json records, per song,
the reader VGMTrans used and how many sequences it found, or that it found none.
"""
import argparse
import glob
import json
import os
import re
import subprocess
import sys
import tempfile
from multiprocessing import Pool

ANSI = re.compile(r"\x1b\[[0-9;]*m")
SEQ = re.compile(r"^\[#(\d+)\] \[0x[0-9a-f]+:0x[0-9a-f]+\] (.*) \((\w+)\)$")


def one(args) -> dict:
    shell, path, out_dir = args
    game = os.path.basename(os.path.dirname(path))
    name = os.path.basename(path)[:-4]
    out = {"game": game, "song": name, "sequences": 0, "reader": None, "exported": []}
    with tempfile.TemporaryDirectory() as tmp:
        link = os.path.join(tmp, "in.spc")
        os.symlink(os.path.abspath(path), link)
        script = f"load {link}\nsequence list\nexit\n"
        try:
            r = subprocess.run([shell], input=script, capture_output=True, text=True, timeout=120)
        except subprocess.TimeoutExpired:
            out["error"] = "timeout"
            return out
        text = ANSI.sub("", r.stdout + r.stderr)
        seqs = []
        for line in text.splitlines():
            m = SEQ.match(line.strip())
            if m:
                seqs.append((int(m.group(1)), m.group(2), m.group(3)))
        if "Failed to load" in text:
            out["error"] = "failed to load"
        out["sequences"] = len(seqs)
        if seqs:
            out["reader"] = seqs[0][2]
            out["titles"] = [s[1] for s in seqs]
            os.makedirs(os.path.join(out_dir, game), exist_ok=True)
            cmds = [f"load {link}"]
            targets = []
            for i, (idx, title, reader) in enumerate(seqs):
                target = os.path.join(out_dir, game, name + (f"#{i + 1}" if i else "") + ".mid")
                tmp_target = os.path.join(tmp, f"out{i}.mid")
                cmds.append(f"sequence export {idx} {tmp_target}")
                targets.append((tmp_target, target))
            cmds.append("exit")
            try:
                subprocess.run([shell], input="\n".join(cmds) + "\n", capture_output=True, text=True, timeout=300)
            except subprocess.TimeoutExpired:
                out["error"] = "export timeout"
            for tmp_target, target in targets:
                if os.path.exists(tmp_target):
                    os.replace(tmp_target, target)
                    out["exported"].append(os.path.basename(target))
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python tools/vgmtrans_batch.py", description=__doc__.split("\n\n")[0])
    ap.add_argument("shell")
    ap.add_argument("spc_root")
    ap.add_argument("out_dir")
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 2))
    a = ap.parse_args(argv)
    paths = sorted(glob.glob(os.path.join(a.spc_root, "*", "*.spc")))
    os.makedirs(a.out_dir, exist_ok=True)
    print(f"{len(paths)} songs")
    results = []
    with Pool(a.workers) as pool:
        for i, r in enumerate(pool.imap_unordered(one, [(a.shell, p, a.out_dir) for p in paths]), 1):
            results.append(r)
            if i % 100 == 0:
                print(f"  {i} done", flush=True)
    results.sort(key=lambda r: (r["game"], r["song"]))
    with open(os.path.join(a.out_dir, "survey.json"), "w") as f:
        json.dump(results, f, indent=0)
    by_game = {}
    for r in results:
        g = by_game.setdefault(r["game"], {"songs": 0, "read": 0, "readers": set()})
        g["songs"] += 1
        if r["sequences"]:
            g["read"] += 1
            g["readers"].add(r["reader"])
    print(f"\n{'game':24s} {'songs':>5s} {'read':>5s}  reader")
    for game, g in sorted(by_game.items()):
        print(f"{game[:24]:24s} {g['songs']:5d} {g['read']:5d}  {', '.join(sorted(g['readers'])) or '-'}")
    print(f"\n{sum(g['read'] for g in by_game.values())} of {len(results)} songs read by VGMTrans")
    return 0


if __name__ == "__main__":
    sys.exit(main())
