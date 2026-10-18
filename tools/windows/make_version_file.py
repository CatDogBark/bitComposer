"""Write a PyInstaller version resource (--version-file) for one of the
Windows executables, so Explorer's Properties > Details names the product,
its publisher and the copyright holder. The version comes from the package.

    python tools/windows/make_version_file.py build/version-player.txt bitComposer.exe "bitComposer"
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from bitcomposer import __version__  # noqa: E402

PUBLISHER = "Enlightened Solutions LLC"
COPYRIGHT = "Copyright (c) 2026 Enlightened Solutions LLC"


def main(out: str, filename: str, description: str) -> int:
    nums = [int(n) for n in re.match(r"(\d+)\.(\d+)\.(\d+)", __version__).groups()] + [0]
    v = tuple(nums)
    strings = {
        "CompanyName": PUBLISHER,
        "FileDescription": description,
        "FileVersion": __version__,
        "InternalName": Path(filename).stem,
        "LegalCopyright": COPYRIGHT,
        "OriginalFilename": filename,
        "ProductName": "bitComposer",
        "ProductVersion": __version__,
    }
    table = ",\n        ".join(f"StringStruct({k!r}, {val!r})" for k, val in strings.items())
    text = f"""VSVersionInfo(
  ffi=FixedFileInfo(filevers={v}, prodvers={v}, mask=0x3f, flags=0x0, OS=0x40004,
                    fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('040904B0', [
        {table}])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"""
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(text, encoding="utf-8")
    print(f"wrote {out} ({filename} {__version__})")
    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:4]))
