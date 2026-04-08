from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import csv


@dataclass
class MatchResult:
    status: str  # "matched" | "missing" | "ambiguous" | "skipped"
    playlist_artist: str
    playlist_title: str
    file_path: str | None = None
    matched_artist: str | None = None
    matched_title: str | None = None
    score: int | None = None
    note: str | None = None


def _read_csv_rows(path: str) -> list[dict]:
    p = Path(path)
    with p.open("r", encoding="utf-8-sig", errors="replace", newline="") as f:
        return list(csv.DictReader(f))


def _norm(s: str | None) -> str:
    return " ".join((s or "").strip().split()).lower()


def _pick_col(row: dict, candidates: list[str]) -> str | None:
    # case-insensitive key match
    keys = {k.lower(): k for k in row.keys()}
    for c in candidates:
        if c.lower() in keys:
            return keys[c.lower()]
    return None


def _detect_cols(rows: list[dict], kind: str) -> tuple[str, str, str | None]:
    # returns (artist_col, title_col, filepath_col)
    if not rows:
        raise ValueError(f"{kind} CSV has no rows")

    sample = rows[0]
    artist_col = _pick_col(sample, ["Artist", "artist", "ARTIST"])
    title_col = _pick_col(sample, ["Title", "title", "TRACK", "Track", "Song", "song", "Name", "name"])
    filepath_col = _pick_col(sample, ["FilePath", "filepath", "SourceFile", "sourcefile", "Path", "path"])

    if not artist_col or not title_col:
        raise ValueError(f"Could not detect Artist/Title columns in {kind} CSV. Columns: {list(sample.keys())}")

    return artist_col, title_col, filepath_col


def match_playlist_to_library(
    library_csv: str,
    playlist_csv: str,
    min_score: int = 92,
    ambiguous_margin: int = 4,
    require_file_exists: bool = True,
    verbose: bool = False,
):
    # NOTE: This is a minimal placeholder matcher.
    # If you already have a better matcher in your project, we can swap this out.
    # For now, exact match on normalized "artist - title".
    lib_rows = _read_csv_rows(library_csv)
    pl_rows = _read_csv_rows(playlist_csv)

    lib_artist_col, lib_title_col, lib_fp_col = _detect_cols(lib_rows, "library")
    pl_artist_col, pl_title_col, _ = _detect_cols(pl_rows, "playlist")

    index = {}
    for r in lib_rows:
        a = _norm(r.get(lib_artist_col))
        t = _norm(r.get(lib_title_col))
        fp = r.get(lib_fp_col) if lib_fp_col else None
        if not fp:
            continue
        index.setdefault((a, t), []).append(fp)

    results: list[MatchResult] = []
    stats = {"playlist_rows": 0, "matched": 0, "missing": 0, "ambiguous": 0}

    for r in pl_rows:
        stats["playlist_rows"] += 1
        pa = (r.get(pl_artist_col) or "").strip()
        pt = (r.get(pl_title_col) or "").strip()
        na, nt = _norm(pa), _norm(pt)

        if not na and not nt:
            results.append(MatchResult(status="skipped", playlist_artist=pa, playlist_title=pt, note="blank row"))
            continue

        hits = index.get((na, nt), [])
        if not hits:
            results.append(MatchResult(status="missing", playlist_artist=pa, playlist_title=pt))
            stats["missing"] += 1
            continue

        # if multiple exact hits, pick first deterministically
        fp = hits[0]
        if require_file_exists and not Path(fp).exists():
            results.append(MatchResult(status="missing", playlist_artist=pa, playlist_title=pt, note="file missing on disk"))
            stats["missing"] += 1
            continue

        results.append(
            MatchResult(
                status="matched",
                playlist_artist=pa,
                playlist_title=pt,
                file_path=fp,
                matched_artist=pa,
                matched_title=pt,
                score=100,
            )
        )
        stats["matched"] += 1

    return results, stats


def write_reports(results: list[MatchResult], out_dir: str, crate_name: str) -> dict:
    outp = Path(out_dir)
    outp.mkdir(parents=True, exist_ok=True)

    audit_path = outp / "match_audit.csv"
    missing_path = outp / "missing_tracks.csv"
    ambiguous_path = outp / "ambiguous_matches.csv"
    m3u_path = outp / f"{crate_name}.m3u"

    # audit
    with audit_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["status", "playlist_artist", "playlist_title", "file_path", "score", "note"])
        for r in results:
            w.writerow([r.status, r.playlist_artist, r.playlist_title, r.file_path or "", r.score or "", r.note or ""])

    # missing
    with missing_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["playlist_artist", "playlist_title", "note"])
        for r in results:
            if r.status == "missing":
                w.writerow([r.playlist_artist, r.playlist_title, r.note or ""])

    # ambiguous (placeholder; kept for compatibility)
    with ambiguous_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["playlist_artist", "playlist_title", "note"])

    # m3u
    with m3u_path.open("w", encoding="utf-8", newline="") as f:
        for r in results:
            if r.status == "matched" and r.file_path:
                f.write(r.file_path + "\n")

    return {
        "audit": str(audit_path),
        "missing": str(missing_path),
        "ambiguous": str(ambiguous_path),
        "m3u": str(m3u_path),
    }


def cmd_crate_from_csv(args) -> int:
    results, stats = match_playlist_to_library(
        library_csv=args.library,
        playlist_csv=args.playlist,
        min_score=args.min_score,
        ambiguous_margin=args.ambiguous_margin,
        require_file_exists=not args.allow_missing_files,
        verbose=args.verbose,
    )

    print(
        f"playlist_rows={stats['playlist_rows']} matched={stats['matched']} missing={stats['missing']} ambiguous={stats['ambiguous']}"
    )

    if args.dry_run:
        print("dry-run: not writing outputs")
        return 0

    crate_name = args.name
    out = write_reports(results, out_dir=args.output, crate_name=crate_name)

    matched_paths = [r.file_path for r in results if r.status == "matched" and r.file_path]

    from dj_bpm_tool.serato_crate import write_serato_crate_interactive

    crate_path = write_serato_crate_interactive(
        matched_paths,
        crate_name=crate_name,
        template_path=args.template_crate,
    )

    print("wrote:")
    for k, v in out.items():
        print(f"  {k}: {v}")
    print(f"  serato_crate: {crate_path}")
    print(f"  template_crate: {args.template_crate}")

    return 0
