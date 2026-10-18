"""
A small window for people who are not at a terminal: pick a sound (a palette
or a style pack) and how many songs, press Generate, and the .it files land in a folder.
Play them with OpenMPT (Windows), or any tracker player that reads Impulse
Tracker modules. Standard-library only (tkinter), like the generator; the
player (bitcomposer-player) is the full program.
"""
import os
import sys
import threading
import subprocess
from pathlib import Path

from . import __version__
from .composer import compose_and_save
from .composer import SOUNDS

SOUND = ["random", *SOUNDS]
ECHO = ["random", "on", "off"]
ENERGY = ["random", "chill", "normal", "intense"]
TEMPO = ["random", "slow", "medium", "fast"]


def default_folder() -> Path:
    music = Path.home() / "Music"
    return (music if music.is_dir() else Path.home()) / "bitComposer"


def open_folder(path: Path) -> None:
    if sys.platform.startswith("win"):
        os.startfile(str(path))                     # noqa: S606 - user's own folder
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])


def main() -> None:
    import tkinter as tk
    from tkinter import ttk, filedialog

    root = tk.Tk()
    root.title(f"bitComposer {__version__}")
    root.resizable(False, False)
    pad = {"padx": 8, "pady": 4}

    frame = ttk.Frame(root, padding=12)
    frame.grid(sticky="nsew")

    choices = {}
    for row, (label, name, options) in enumerate([
        ("Sound", "sound", SOUND), ("Echo", "echo", ECHO),
        ("Energy", "energy", ENERGY), ("Tempo", "tempo", TEMPO),
    ]):
        ttk.Label(frame, text=label).grid(row=row, column=0, sticky="w", **pad)
        var = tk.StringVar(value=options[0])
        ttk.Combobox(frame, textvariable=var, values=options, state="readonly", width=14).grid(row=row, column=1, sticky="w", **pad)
        choices[name] = var

    ttk.Label(frame, text="How many").grid(row=5, column=0, sticky="w", **pad)
    count = tk.IntVar(value=5)
    ttk.Spinbox(frame, from_=1, to=50, textvariable=count, width=6).grid(row=5, column=1, sticky="w", **pad)

    ttk.Label(frame, text="Save to").grid(row=6, column=0, sticky="w", **pad)
    folder = tk.StringVar(value=str(default_folder()))
    ttk.Entry(frame, textvariable=folder, width=36).grid(row=6, column=1, columnspan=2, sticky="we", **pad)

    def browse():
        chosen = filedialog.askdirectory(initialdir=folder.get() or str(Path.home()))
        if chosen:
            folder.set(chosen)
    ttk.Button(frame, text="Browse", command=browse).grid(row=6, column=3, **pad)

    log = tk.Listbox(frame, height=8, width=60)
    log.grid(row=8, column=0, columnspan=4, sticky="we", **pad)
    status = ttk.Label(frame, text="Songs are Impulse Tracker .it files; OpenMPT plays them on Windows.")
    status.grid(row=9, column=0, columnspan=4, sticky="w", **pad)

    buttons = ttk.Frame(frame)
    buttons.grid(row=7, column=0, columnspan=4, sticky="we", **pad)
    generate_btn = ttk.Button(buttons, text="Generate")
    generate_btn.pack(side="left")
    ttk.Button(buttons, text="Open folder", command=lambda: open_folder(Path(folder.get()))).pack(side="left", padx=8)

    def worker(n, out_dir, opts):
        out_dir.mkdir(parents=True, exist_ok=True)
        for i in range(n):
            try:
                path = out_dir / f"song-{i}.it"
                info = compose_and_save(str(path), sound=opts["sound"], echo=opts["echo"],
                                        energy=opts["energy"], tempo=opts["tempo"])
                final = out_dir / f"{info['title']}.it"
                if final != path:
                    if final.exists():
                        final.unlink()
                    path.rename(final)
                pack = f" ({info['pack']})" if info.get("pack") else ""
                ins = info["instruments"]
                drew = (f"{info['song_form']} form, {info.get('intro') or 'no'} intro, {info['harmony_mode']} harmony, "
                        f"{info['bass_style']} bass" + (f" ({info['bass_riff']})" if info.get('bass_riff') else "")
                        + (f", {info['echo_delay']} echo" if info.get("echo") else ", no echo"))
                root.after(0, log.insert, "end", f"{info['title']}  —  {info['style']}{pack}, {info['tempo']} BPM")
                root.after(0, log.insert, "end", f"    {ins['melody']} / {ins['harmony']} / {ins['bass']} / {ins['arp']}  ·  {drew}")
            except Exception as e:                    # keep the window alive on any failure
                root.after(0, log.insert, "end", f"failed: {e}")
            root.after(0, log.see, "end")
        root.after(0, lambda: (generate_btn.state(["!disabled"]), status.config(text=f"Done. {n} song(s) in {out_dir}")))

    def generate():
        opts = {k: v.get() for k, v in choices.items()}
        n = max(1, min(50, int(count.get() or 1)))
        out_dir = Path(folder.get()).expanduser()
        generate_btn.state(["disabled"])
        status.config(text="Generating…")
        threading.Thread(target=worker, args=(n, out_dir, opts), daemon=True).start()

    generate_btn.config(command=generate)
    root.mainloop()


if __name__ == "__main__":
    main()
