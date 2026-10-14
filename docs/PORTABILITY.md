# Portability

**Decided 2026-09-04.** The generator is a plain Python package with no
runtime dependencies and writes wherever `-o`/`-d` points. The player stack
around it — a D-Bus daemon, a KDE Plasma 6 widget and two helper scripts — is
vendored under `companion/` with an idempotent `install.sh`, so a fresh Linux
desktop can be set up from a clone. It is optional: nothing in `bitcomposer/`
knows it exists.

Generated music deliberately stays out of the repo, in `~/Music/Chiptune`
(override with `$BITCOMPOSER_MUSIC_DIR`). The idea of defaulting CLI output to
`<repo>/output/` was considered and dropped; the CLI writes to the working
directory unless told otherwise, and the helper scripts pass the music dir
explicitly.

The import path for the daemon and widget is a `.pth` file pointing at the
checkout rather than a pip install, so generation follows whichever branch is
checked out. The cost of that choice, and how to recover from a Python minor
version bump, is in `INSTALL.md`.
