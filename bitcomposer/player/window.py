"""The player window: tkinter over engine.Player, laid out like the Plasma
widget (now playing, transport, gain, auto-generate, settings, mixer with
the ECHO and KIT buses, playlist with KEEP and AUTO marks, generate).

Standard library only, so the Windows build is one executable with
libopenmpt.dll beside it. Run with `bitcomposer-player` or
`python -m bitcomposer.player`; `--install-desktop` writes the app-menu
entry on Linux, `--check` reports whether the library and an audio output
are found and exits.
"""
import argparse
import os
import shlex
import sys
import threading
import urllib.request
import json
from pathlib import Path

from .. import __version__
from ..composer import SOUNDS
from .engine import Player, VOLUME_MAX, AUTOGEN_MAX, KIT_ROLES, default_music_dir
from .openmpt import LibraryMissing, lib as openmpt_lib
from .audio import make_output, OutputUnavailable

OPTIONS = [
    # (label, flag, choices); "random" first is the CLI default for each
    ("SOUND", "--sound", ["random", *SOUNDS]),
    ("TEMPO", "--tempo", ["random", "slow", "medium", "fast"]),
    ("ENERGY", "--energy", ["random", "chill", "normal", "intense"]),
    ("SCALE", "--scale", ["random", "minor", "major", "pentatonic"]),
    ("FORM", "--form", ["random", "standard", "aaba", "rondo", "short", "linear"]),
    ("ECHO", "--echo", ["random", "on", "off"]),
    ("WET", "--echo-wet", ["random", "light", "normal", "wet"]),
    ("BASS", "--bass-weight", ["random", "heavy", "medium", "light"]),
    ("DENSITY", "--drum-density", ["random", "sparse", "normal", "busy"]),
    ("SWING", "--swing", ["random", "off", "light", "heavy"]),
    ("VOICING", "--harmony-voicing", ["random", "thin", "full"]),
    ("MODE", "--harmony-mode", ["random", "stabs", "sustain", "rhythmic"]),
    ("KEYS", "--keys", ["moving", "home"]),
]
PRESETS = {
    "any": {},
    "overworld": {"--sound": "snes", "--scale": "major", "--tempo": "medium", "--form": "standard"},
    "boss": {"--sound": "genesis", "--tempo": "fast", "--energy": "intense", "--scale": "minor", "--drum-density": "busy"},
    "game boy": {"--sound": "chip", "--echo": "off", "--harmony-voicing": "thin", "--bass-weight": "light"},
    "credits": {"--sound": "snes", "--tempo": "slow", "--energy": "chill", "--scale": "major", "--drum-density": "sparse"},
    "mega man x": {"--sound": "megamanx"}, "ffvi": {"--sound": "ffvi"}, "mana": {"--sound": "mana"}, "evermore": {"--sound": "evermore"},
}
RELEASES_URL = "https://api.github.com/repos/CatDogBark/bitComposer/releases/latest"


def flags_from(choices: dict) -> str:
    parts = []
    for label, flag, options in OPTIONS:
        v = choices.get(flag, options[0])
        if v != options[0]:
            parts += [flag, v]
    return " ".join(parts)


def choices_from(flags: str) -> dict:
    out = {}
    toks = shlex.split(flags)
    for i, t in enumerate(toks[:-1]):
        if t.startswith("--"):
            out[t] = toks[i + 1]
    return out


def check() -> int:
    """Report what the player needs and exit: libopenmpt, an audio output, the music folder."""
    ok = True
    try:
        openmpt_lib()
        print("libopenmpt: ok")
    except LibraryMissing as e:
        print(f"libopenmpt: MISSING ({e})"); ok = False
    try:
        out = make_output(48000)
        print(f"audio output: ok ({type(out).__name__}{' via ' + out.command if hasattr(out, 'command') else ''})")
    except OutputUnavailable as e:
        print(f"audio output: MISSING ({e})"); ok = False
    print(f"music folder: {default_music_dir()}")
    print(f"bitcomposer {__version__}")
    return 0 if ok else 1


def install_desktop() -> int:
    """Write the app-menu entry (Linux)."""
    if not sys.platform.startswith("linux"):
        print("desktop entries are a Linux thing; on Windows the installer makes the Start menu entry")
        return 1
    apps = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / "applications"
    apps.mkdir(parents=True, exist_ok=True)
    exe = Path(sys.argv[0]).resolve()
    cmd = str(exe) if exe.name == "bitcomposer-player" else f"{sys.executable} -m bitcomposer.player"
    (apps / "bitcomposer-player.desktop").write_text(
        "[Desktop Entry]\nType=Application\nName=bitComposer\nComment=Procedural 16-bit game music: plays and generates\n"
        f"Exec={cmd}\nIcon=audio-x-generic\nTerminal=false\nCategories=AudioVideo;Audio;Music;\n")
    print(f"wrote {apps / 'bitcomposer-player.desktop'}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="bitcomposer-player", description="bitComposer: the player")
    ap.add_argument("--check", action="store_true", help="report libopenmpt, the audio output and the music folder, then exit")
    ap.add_argument("--install-desktop", action="store_true", help="write the app-menu entry (Linux) and exit")
    ap.add_argument("--music-dir", help="folder of songs (default: $BITCOMPOSER_MUSIC_DIR, ~/Music/Chiptune if it exists, else ~/Music/bitComposer)")
    ap.add_argument("--version", action="version", version=f"bitcomposer {__version__}")
    args = ap.parse_args(argv)
    if args.check:
        return check()
    if args.install_desktop:
        return install_desktop()
    return run_window(args.music_dir)


def run_window(music_dir=None) -> int:
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox

    root = tk.Tk()
    root.title(f"bitComposer {__version__}")
    root.minsize(520, 640)
    player = Player(music_dir=music_dir, schedule=lambda fn: root.after(0, fn))
    log_lines = []

    def log(msg):
        log_lines.append(msg)
        del log_lines[:-200]
        try:
            status_var.set(msg)
        except Exception:
            pass
    player.on_log = log

    try:
        openmpt_lib()
    except LibraryMissing as e:
        messagebox.showerror("bitComposer", str(e))
        return 1

    # ── layout ──
    pad = {"padx": 6, "pady": 3}
    main = ttk.Frame(root, padding=8)
    main.pack(fill="both", expand=True)
    main.columnconfigure(0, weight=1)

    # Now playing
    now = ttk.LabelFrame(main, text="NOW PLAYING", padding=6)
    now.grid(row=0, column=0, sticky="we", **pad)
    now.columnconfigure(0, weight=1)
    title_var = tk.StringVar(value="nothing loaded")
    sub_var = tk.StringVar(value="")
    drew_var = tk.StringVar(value="")
    ttk.Label(now, textvariable=title_var, font=("TkDefaultFont", 13, "bold")).grid(row=0, column=0, sticky="w")
    ttk.Label(now, textvariable=sub_var).grid(row=1, column=0, sticky="w")
    ttk.Label(now, textvariable=drew_var, wraplength=480, foreground="#666").grid(row=2, column=0, sticky="w")
    pos_var = tk.DoubleVar(value=0.0)
    time_var = tk.StringVar(value="0:00 / 0:00")
    seeking = {"drag": False}
    seek = ttk.Scale(now, from_=0, to=100, variable=pos_var, orient="horizontal")
    seek.grid(row=3, column=0, sticky="we", pady=(4, 0))
    ttk.Label(now, textvariable=time_var).grid(row=3, column=1, padx=6)

    def seek_press(_e): seeking["drag"] = True
    def seek_release(_e):
        seeking["drag"] = False
        m = player.metadata()
        if m:
            player.seek(pos_var.get() / 100.0 * m["duration"])
    seek.bind("<ButtonPress-1>", seek_press)
    seek.bind("<ButtonRelease-1>", seek_release)

    # Transport + gain
    bar = ttk.Frame(main)
    bar.grid(row=1, column=0, sticky="we", **pad)
    ttk.Button(bar, text="|◀", width=4, command=player.previous).pack(side="left")
    play_btn = ttk.Button(bar, text="▶", width=4, command=player.play_pause)
    play_btn.pack(side="left", padx=2)
    ttk.Button(bar, text="■", width=4, command=player.stop).pack(side="left")
    ttk.Button(bar, text="▶|", width=4, command=player.next).pack(side="left", padx=2)
    shuffle_var = tk.BooleanVar(value=player.shuffle)
    ttk.Checkbutton(bar, text="shuffle", variable=shuffle_var, command=lambda: player.set_shuffle(shuffle_var.get())).pack(side="left", padx=8)
    ttk.Label(bar, text="GAIN").pack(side="left", padx=(12, 2))
    gain_var = tk.DoubleVar(value=player.volume)
    gain_lbl = ttk.Label(bar, text=f"{int(player.volume * 100)}%", width=5)

    def on_gain(_v):
        player.set_volume(gain_var.get())
        gain_lbl.config(text=f"{int(player.volume * 100)}%")
    ttk.Scale(bar, from_=0.0, to=VOLUME_MAX, variable=gain_var, orient="horizontal", length=120, command=on_gain).pack(side="left")
    gain_lbl.pack(side="left")

    # Generate + auto
    gen = ttk.LabelFrame(main, text="GENERATE", padding=6)
    gen.grid(row=2, column=0, sticky="we", **pad)
    gen.columnconfigure(1, weight=1)
    saved = choices_from(player.auto_generate_settings)
    choice_vars = {}
    preset_var = tk.StringVar(value="any")

    def apply_preset(*_):
        p = PRESETS.get(preset_var.get(), {})
        for label, flag, options in OPTIONS:
            choice_vars[flag].set(p.get(flag, options[0]))
        on_choices()
    ttk.Label(gen, text="PRESET").grid(row=0, column=0, sticky="w")
    ttk.Combobox(gen, textvariable=preset_var, values=list(PRESETS), state="readonly", width=12).grid(row=0, column=1, sticky="w")
    preset_var.trace_add("write", apply_preset)
    grid = ttk.Frame(gen)
    grid.grid(row=1, column=0, columnspan=3, sticky="we")

    def on_choices(*_):
        player.set_auto_generate(player.auto_generate, flags_from({f: v.get() for f, v in choice_vars.items()}))
    for i, (label, flag, options) in enumerate(OPTIONS):
        r, c = divmod(i, 3)
        ttk.Label(grid, text=label, width=8).grid(row=r, column=c * 2, sticky="e", padx=(6, 2), pady=1)
        var = tk.StringVar(value=saved.get(flag, options[0]))
        cb = ttk.Combobox(grid, textvariable=var, values=options, state="readonly", width=9)
        cb.grid(row=r, column=c * 2 + 1, sticky="w", pady=1)
        var.trace_add("write", on_choices)
        choice_vars[flag] = var
    gen_row = ttk.Frame(gen)
    gen_row.grid(row=2, column=0, columnspan=3, sticky="we", pady=(4, 0))
    gen_btn = ttk.Button(gen_row, text="GENERATE AND PLAY")
    gen_btn.pack(side="left")
    auto_var = tk.BooleanVar(value=player.auto_generate)
    ttk.Checkbutton(gen_row, text="∞ auto-generate when a track ends", variable=auto_var,
                    command=lambda: player.set_auto_generate(auto_var.get())).pack(side="left", padx=10)

    def generate():
        gen_btn.state(["disabled"])
        log("composing…")
        player.generate(player.auto_generate_settings, play=True,
                        on_done=lambda path: (gen_btn.state(["!disabled"]), log(f"composed {os.path.basename(path)}" if path else player.last_error)))
    gen_btn.config(command=generate)

    # Mixer
    mix = ttk.LabelFrame(main, text="CHANNEL MIX", padding=6)
    mix.grid(row=3, column=0, sticky="we", **pad)
    mix.columnconfigure(1, weight=1)
    mixer = {"rows": [], "layout": [], "base": [], "file": None, "echo_bus": 1.0, "kit_bus": 1.0,
             "expanded": {"echo_bus": False, "kit_bus": False}}

    def rebuild_mixer():
        for w in mix.winfo_children():
            w.destroy()
        m = player.metadata()
        mixer["rows"] = []
        if not m:
            ttk.Label(mix, text="no track loaded").grid(row=0, column=0, sticky="w")
            return
        layout = m["layout"]
        vols = player.channel_volumes()
        mixer["layout"], mixer["base"], mixer["file"] = layout, list(vols), m["file"]
        mixer["echo_bus"], mixer["kit_bus"] = 1.0, 1.0
        voices = m["voices"]
        echo_ch = [i for i, r in enumerate(layout) if r.startswith("echo.")]
        kit_ch = [i for i, r in enumerate(layout) if r in KIT_ROLES]
        part_ch = [i for i, r in enumerate(layout) if not r.startswith("echo.") and r not in KIT_ROLES]
        row = [0]

        def label_for(i):
            r = layout[i]
            if r == "harmony":
                return f"HARM {sum(1 for k in range(i + 1) if layout[k] == 'harmony')}"
            if r.startswith("echo."):
                return f"ECHO {r[5:]}"
            return {"melody": "LEAD", "bass": "BASS", "arp": "ARP", "hihat": "HAT", "openhat": "OPEN HAT"}.get(r, r.upper())

        def fader(text, sub, value, to, on_move, fmt):
            ttk.Label(mix, text=text, width=9, anchor="e").grid(row=row[0], column=0, sticky="e")
            var = tk.DoubleVar(value=value)
            val_lbl = ttk.Label(mix, text=fmt(value), width=5)
            sc = ttk.Scale(mix, from_=0, to=to, variable=var, orient="horizontal", command=lambda _v: (on_move(var.get()), val_lbl.config(text=fmt(var.get()))))
            sc.grid(row=row[0], column=1, sticky="we", padx=4)
            val_lbl.grid(row=row[0], column=2)
            if sub:
                ttk.Label(mix, text=sub, foreground="#888", width=18, anchor="w").grid(row=row[0], column=3, sticky="w")
            row[0] += 1
            return var

        for i in part_ch:
            fader(label_for(i), voices.get(layout[i], ""), vols[i], 64, lambda v, ch=i: player.set_channel_volume(ch, int(round(v))), lambda v: str(int(round(v))))

        def bus(name, chans, key):
            def move(r):
                mixer[key] = r
                for ch in chans:
                    player.set_channel_volume(ch, int(round(mixer["base"][ch] * r)))
            btn = ttk.Button(mix, text=("▾ " if mixer["expanded"][key] else "▸ ") + name, width=9,
                             command=lambda: (mixer["expanded"].__setitem__(key, not mixer["expanded"][key]), rebuild_mixer()))
            btn.grid(row=row[0], column=0, sticky="e")
            var = tk.DoubleVar(value=mixer[key])
            lbl = ttk.Label(mix, text=f"{int(mixer[key] * 100)}%", width=5)
            ttk.Scale(mix, from_=0, to=2.0, variable=var, orient="horizontal",
                      command=lambda _v: (move(var.get()), lbl.config(text=f"{int(var.get() * 100)}%"))).grid(row=row[0], column=1, sticky="we", padx=4)
            lbl.grid(row=row[0], column=2)
            ttk.Label(mix, text=f"{len(chans)} channels, 100% = the file's mix", foreground="#888").grid(row=row[0], column=3, sticky="w")
            row[0] += 1
            if mixer["expanded"][key]:
                for ch in chans:
                    fader("  " + label_for(ch), voices.get(layout[ch], ""), vols[ch], 64,
                          lambda v, c=ch: player.set_channel_volume(c, int(round(v))), lambda v: str(int(round(v))))
        if kit_ch:
            bus("KIT", kit_ch, "kit_bus")
        if echo_ch:
            bus("ECHO", echo_ch, "echo_bus")
        ttk.Button(mix, text="APPLY TO TRACK", command=lambda: log("mix written into the file" if player.apply_mix_to_file() else "could not write the mix")).grid(row=row[0], column=0, columnspan=2, sticky="w", pady=(4, 0))

    # Playlist
    pl = ttk.LabelFrame(main, text="PLAYLIST", padding=6)
    pl.grid(row=4, column=0, sticky="nsew", **pad)
    main.rowconfigure(4, weight=1)
    pl.columnconfigure(0, weight=1)
    pl.rowconfigure(1, weight=1)
    top = ttk.Frame(pl)
    top.grid(row=0, column=0, columnspan=2, sticky="we")
    folder_var = tk.StringVar(value=str(player.music_dir))
    ttk.Label(top, textvariable=folder_var, foreground="#666").pack(side="left")

    def choose_folder():
        chosen = filedialog.askdirectory(initialdir=str(player.music_dir))
        if chosen:
            player.set_music_dir(Path(chosen))
            folder_var.set(chosen)
    ttk.Button(top, text="folder…", command=choose_folder).pack(side="right")
    ttk.Button(top, text="↻ refresh", command=player.scan).pack(side="right", padx=4)
    ttk.Button(top, text="KEEP", command=lambda: keep_selected()).pack(side="right", padx=4)
    ttk.Label(top, text=f"AUTO = pruned after {AUTOGEN_MAX}", foreground="#888").pack(side="right", padx=8)
    listbox = tk.Listbox(pl, activestyle="none", height=10)
    listbox.grid(row=1, column=0, sticky="nsew")
    sb = ttk.Scrollbar(pl, orient="vertical", command=listbox.yview)
    sb.grid(row=1, column=1, sticky="ns")
    listbox.config(yscrollcommand=sb.set)

    def keep_selected():
        sel = listbox.curselection()
        if sel:
            new = player.keep_track(sel[0])
            log(f"kept as {new}" if new else "nothing to keep")
    listbox.bind("<Double-Button-1>", lambda e: player.play(listbox.nearest(e.y)))

    status_var = tk.StringVar(value="")
    ttk.Label(main, textvariable=status_var, foreground="#666").grid(row=5, column=0, sticky="w", **pad)

    # ── refresh from the engine ──
    def fmt_t(s):
        s = int(max(0, s)); return f"{s // 60}:{s % 60:02d}"

    def refresh():
        m = player.metadata()
        play_btn.config(text="❚❚" if player.status == "Playing" else "▶")
        if m:
            title_var.set(m["title"] + ("   [AUTO]" if m["autogen"] else ""))
            sub_var.set(f"by {m['artist']}  ·  {m['type'].upper()}  ·  {m['channels']} ch  ·  {m['patterns']} pat  ·  {m['file']}")
            drew = m["drew"]
            drew_var.set("  ".join(f"{k}={v}" for k, v in drew.items()) if drew else m["blurb"])
        else:
            title_var.set("nothing loaded"); sub_var.set(""); drew_var.set("")
        if listbox.size() != len(player.playlist) or mixer.get("playlist_sig") != tuple(player.playlist):
            listbox.delete(0, "end")
            for i, path in enumerate(player.playlist):
                listbox.insert("end", ("AUTO  " if player.is_autogen(path) else "      ") + player.track_title(path))
            mixer["playlist_sig"] = tuple(player.playlist)
        for i in range(listbox.size()):
            listbox.itemconfig(i, background="#dbe9ff" if i == player.current_index else "")
        if (m or {}).get("file") != mixer.get("file"):
            rebuild_mixer()
        auto_var.set(player.auto_generate)
    player.on_change = refresh

    def tick():
        m = player.metadata()
        if m and not seeking["drag"]:
            pos = player.position()
            pos_var.set(100.0 * pos / m["duration"] if m["duration"] else 0)
            time_var.set(f"{fmt_t(pos)} / {fmt_t(m['duration'])}")
        root.after(250, tick)

    def update_check():
        try:
            with urllib.request.urlopen(RELEASES_URL, timeout=5) as r:
                tag = json.load(r).get("tag_name", "")
            latest = tag.lstrip("v")
            if latest and latest != __version__ and not latest.endswith(("rc1", "rc2", "rc3")):
                root.after(0, lambda: log(f"version {latest} is out: github.com/CatDogBark/bitComposer/releases"))
        except Exception:
            pass
    threading.Thread(target=update_check, daemon=True).start()

    player.scan()
    refresh()
    tick()
    root.protocol("WM_DELETE_WINDOW", lambda: (player.shutdown(), root.destroy()))
    root.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
