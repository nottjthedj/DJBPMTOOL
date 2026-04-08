from pathlib import Path
import struct

SERATO_SUBCRATES_DIR = Path.home() / "Music" / "_Serato_" / "Subcrates"
DEFAULT_TEMPLATE = SERATO_SUBCRATES_DIR / "Disco.crate"


def _be_u32(n: int) -> bytes:
    return struct.pack(">I", int(n))


def _chunk(tag4: bytes, payload: bytes) -> bytes:
    if len(tag4) != 4:
        raise ValueError("Chunk tag must be 4 bytes")
    return tag4 + _be_u32(len(payload)) + payload


def _utf16be(s: str) -> bytes:
    return s.encode("utf-16be")


def _read_template_header(template_path: Path) -> bytes:
    b = template_path.read_bytes()
    j = b.find(b"otrk")
    if j == -1:
        raise ValueError(f"Template has no 'otrk' chunk: {template_path}")
    return b[:j]


def build_serato_crate_bytes(file_paths: list[str], template_path: Path | None = None) -> bytes:
    """
    Build a Serato .crate by cloning the exact header from a known-good template crate,
    then appending otrk/ptrk entries.

    This avoids needing to reverse-engineer Serato's required metadata chunks.
    """
    if template_path is None:
        template_path = DEFAULT_TEMPLATE

    header = _read_template_header(template_path)

    out = bytearray()
    out += header

    for p in file_paths:
        p = str(p).strip()
        if not p:
            continue

        # Match observed encoding in working crates
        ptrk = _chunk(b"ptrk", _utf16be(p))
        otrk = _chunk(b"otrk", ptrk)
        out += otrk

    return bytes(out)


def prompt_crate_name() -> str:
    name = input("Crate name (no .crate): ").strip()
    while not name:
        name = input("Crate name (no .crate): ").strip()
    if name.lower().endswith(".crate"):
        name = name[:-6]
    return name


def confirm_overwrite(path: Path) -> bool:
    ans = input(f'File exists: "{path.name}". Overwrite? [y/N]: ').strip().lower()
    return ans in ("y", "yes")


def write_serato_crate_interactive(
    file_paths: list[str],
    crate_name: str | None = None,
    template_path: str | None = None,
) -> Path:
    SERATO_SUBCRATES_DIR.mkdir(parents=True, exist_ok=True)

    tpl = Path(template_path).expanduser() if template_path else DEFAULT_TEMPLATE
    if not tpl.exists():
        raise FileNotFoundError(f"Template crate not found: {tpl}")

    while True:
        name = crate_name.strip() if crate_name else prompt_crate_name()
        out_path = SERATO_SUBCRATES_DIR / f"{name}.crate"

        if out_path.exists() and not confirm_overwrite(out_path):
            crate_name = None
            continue

        out_path.write_bytes(build_serato_crate_bytes(file_paths, template_path=tpl))
        return out_path
