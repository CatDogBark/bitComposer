"""The vocabulary's map, from the code: every table the packs keep (packtables.KEPT), who draws it, what conditions it
and what it conditions in turn; written as a Markdown page with a Mermaid graph, and a check that the hand-written
VOCABULARY.md names every table and nothing else.

    python tools/vocab_map.py --out docs/idiom/vocabulary-map.md
    python tools/vocab_map.py --check docs/idiom/VOCABULARY.md      # exit 1 on drift

The draw sites are read from the writer's source (whole.py, writer.py, harness.py): a table is "drawn by" the function
its name appears in. Which table gives a conditioning its value is a short hand-kept list below (SOURCES); a
conditioning not in it is structural (the part, the bar's meter, the chain's previous outcome)."""
import argparse
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from bitcomposer.translate import packtables  # noqa: E402

SOURCES = {                               # a conditioning -> the tables whose outcome gives it its value in a written song
    "habit": ["habits", "bass_habits", "drum_habits", "drum_group_habits", "balance"],
    "tempo": ["tempos", "balance"],
    "weight": ["weights", "balance"],
    "feel": ["feels"],
    "kit": ["kit_pieces", "balance"],
    "form": ["form", "letters"],
    "length": ["lengths", "length_habits"],
    "layer": ["layers", "balance"],
    "kind": ["counter_samples", "layers", "balance"],
    "mode": ["keys"],
    "speed": ["part_speeds"],
    "band": ["parts", "balance"],
    "phrases": ["phrase_letters"],
    "contour": ["contours"],
    "relation": ["relations"],
    "shape": ["voicing_habits"],
    "tune": ["levels", "balance"],
    "period": ["periods"],
}
CONCEPTS = {"mix_level", "lead", "loudness"}   # VOCABULARY entries that are measures, passes or ideas, not tables
STRUCTURAL = {"part", "meter", "previous", "place", "line", "onsets", "voice", "value", "index", "tone", "rank", "gap", "role"}
STAGES = [                                # where a table is drawn, by the function that draws it (the writer's source)
    ("plan", "the plan, drawn once a song"), ("writing", "the parts' writing (whole.write hands the table to a writer)"), ("drums", "the drums"), ("bass", "the bass"), ("upper", "the upper parts"),
    ("melody", "the tune"), ("counter", "the counter-line"), ("render", "the render"), ("harness", "the harness only"),
    ("unused", "counted, drawn nowhere (the measures' words)")]
FILES = ("whole.py", "writer.py", "harness.py")


def draw_sites() -> dict:
    """{table: {(file, function)}} for every place the writer's source names a table."""
    out = {}
    pat = re.compile(r'(?:_draw\(models, |_maybe\(models, |models\[|models\.get\(|in models\b|models_or_empty\(models\)\b)"?([a-z_]+)"?|"([a-z_]+)" in models')
    for f in FILES:
        path = os.path.join(os.path.dirname(HERE), "bitcomposer", "translate", f)
        func = "?"
        for line in open(path, encoding="utf-8"):
            m = re.match(r"def (\w+)\(", line)
            if m:
                func = m.group(1)
            for m in re.finditer(r'(?:_draw\(models, "|_maybe\(models, "|models\["|models\.get\("|")([a-z_]+)"(?:\] | in models|\)|,)', line):
                name = m.group(1)
                if name in packtables.KEPT:
                    out.setdefault(name, set()).add((f, func))
            if '"drums-" +' in line or 'f"drums-{' in line:   # the drum groups' tables, named by their letters at the draw
                for name in packtables.KEPT:
                    if name.startswith("drums-"):
                        out.setdefault(name, set()).add((f, func))
    return out


def stage_of(sites: set) -> str:
    funcs = {fn for f, fn in sites if f != "harness.py"}
    if not funcs:
        return "harness" if sites else "unused"
    for key, fns in (("drums", {"drums", "drum_groups", "free_drum_envelope", "_free_drum_figures", "kit_value"}),
                     ("bass", {"bass", "second_bass"}), ("upper", {"upper", "stack", "beside_pitch", "interval_weights"}),
                     ("melody", {"melody", "new_cell", "draw_move", "phrase_plan", "_figures"}), ("counter", {"counter"}),
                     ("render", {"score_of", "samples_for", "best_sample", "echo_of", "master_of", "level_of", "read_back"})):
        if funcs & fns:
            return key
    if funcs & {"write"} and not any(fn.startswith("plan") or fn in ("_plan_once", "compose", "habit_near", "drum_entrances", "entrances") for fn in funcs):
        return "writing"
    return "plan"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", help="write the map page here")
    ap.add_argument("--check", help="VOCABULARY.md: every table named, nothing else")
    a = ap.parse_args(argv)
    sites = draw_sites()
    rows = []
    for name, (module, builder, kwargs, shape, on_floor, mixture, what) in packtables.KEPT.items():
        feeds = sorted({n for n, (_, _, _, sh, *_) in packtables.KEPT.items() if n != name
                        and any(name in SOURCES.get(c, []) for c in sh)})
        rows.append({"name": name, "module": module, "builder": builder, "shape": list(shape), "what": what,
                     "stage": stage_of(sites.get(name, set())), "drawn_by": sorted({fn for _, fn in sites.get(name, ())}), "feeds": feeds})
    if a.check:
        text = open(a.check, encoding="utf-8").read()
        named = set(re.findall(r"\*\*([a-z_]+(?:-[A-Za-z]+)?)\*\*", text))
        kept = set(packtables.KEPT)
        missing, extra = sorted(kept - named), sorted(named - kept - CONCEPTS)
        if missing:
            print("tables with no VOCABULARY entry:", ", ".join(missing))
        if extra:
            print("VOCABULARY entries naming no table:", ", ".join(extra))
        if not a.out:
            return 1 if missing or extra else 0
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(page(rows))
        print(f"{a.out}: {len(rows)} tables, {sum(len(r['feeds']) for r in rows)} edges")
    return 0


def page(rows: list) -> str:
    by_stage = {k: [r for r in rows if r["stage"] == k] for k, _ in STAGES}
    out = ["# The vocabulary's map", "",
           "Generated by `python tools/vocab_map.py --out docs/idiom/vocabulary-map.md` from `packtables.KEPT` and the writer's",
           "source; do not edit by hand. The words themselves, what each counts and why it exists, are in `VOCABULARY.md`;",
           "this page is the index and the wiring: each table's shape (its conditionings), where it is drawn, and which",
           "tables its outcome conditions in turn (`SOURCES` in the tool names which table gives a conditioning its value).", "",
           "## The writing, stage by stage", "",
           "```mermaid", "flowchart LR",
           "  P[the plan: one draw a song] --> D[drums] --> B[bass] --> U[upper parts] --> M[the tune] --> C[the counter-line] --> R[render]", "```", ""]
    for key, title in STAGES:
        rs = by_stage[key]
        if not rs:
            continue
        out += [f"### {title} ({len(rs)})", "", "| table | shape | drawn in | conditions | what it counts |", "|---|---|---|---|---|"]
        for r in rs:
            out.append(f"| `{r['name']}` | {', '.join(r['shape'])} | {', '.join(r['drawn_by']) or '-'} | {', '.join(f'`{x}`' for x in r['feeds']) or '-'} | {r['what']} |")
        out.append("")
    out += ["## What conditions what", "",
            "One graph a stage: the stage's tables, and the tables whose outcome gives one of their conditionings its value",
            "(the label is the conditioning). Structural conditionings (the part, the meter, the chain's previous outcome, a",
            "place) are no edges. A word that feeds many stages (`habits`, `tempos`, the `balance` token) appears in each.", ""]
    nid = lambda n: n.replace("-", "_")   # noqa: E731
    for key, title in STAGES:
        rs = by_stage[key]
        if not rs:
            continue
        edges, srcs = [], set()
        for r in rs:
            for c in r["shape"]:
                for src in SOURCES.get(c, []):
                    if src in packtables.KEPT and src != r["name"]:
                        edges.append((src, r["name"], c))
                        srcs.add(src)
        out += [f"### {title}", "", "```mermaid", "flowchart LR"]
        mine = {r["name"] for r in rs}
        for src in sorted(srcs - mine):
            out.append(f'  {nid(src)}(["{src}"])')
        out.append(f'  subgraph {key}["{title}"]')
        out += [f'    {nid(r["name"])}["{r["name"]}"]' for r in rs]
        out.append("  end")
        for src, dst, c in sorted(set(edges)):
            out.append(f"  {nid(src)} -- {c} --> {nid(dst)}")
        out += ["```", ""]
    return "\n".join(out)


if __name__ == "__main__":
    raise SystemExit(main())
