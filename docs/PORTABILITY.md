# Portability

**Decided 2026-09-04, revised for 1.0.0.** The generator is a plain Python
package with no runtime dependencies and writes wherever `-o`/`-d` points. The
player (`bitcomposer/player/`) is the same package with Qt (PySide6) added,
installed with `pipx install bitcomposer` on Linux and by the installer on
Windows. The KDE Plasma widget and its D-Bus daemon that came before it lived
in a `companion/` folder; the player does everything they did (the media keys
through MPRIS, start at login in the tray), and they were removed in 1.0.0rc3.

Generated music deliberately stays out of the repo, in `~/Music/Chiptune`
(override with `$BITCOMPOSER_MUSIC_DIR`). The idea of defaulting CLI output to
`<repo>/output/` was considered and dropped; the CLI writes to the working
directory unless told otherwise, and the helper scripts pass the music dir
explicitly.

A developer runs the player from the checkout (`python -m bitcomposer.player`,
or `pipx install --editable .`); generation then follows whichever branch is
checked out.
