import csv
import os
import re
import unicodedata
from dataclasses import dataclass
from typing import Dict, List, Tuple

from rapidfuzz import fuzz


_FEAT_RE = re.compile(r"\b(feat|ft)\.?\b", re.IGNORECASE)


def _ascii_fold(s: str) -> str:
    """Convert accented/unicode chars to closest ASCII equivalent (e.g. é→e, ñ→n)."""
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")


def _norm(s: str) -> str:
    """Core normalizer: remove bracketed edit info and punctuation, keep letters/numbers/spaces."""
    if s is None:
        return ""
    s = _ascii_fold(str(s)).strip().lower()
    s = s.replace("&", " and ")
    s = _FEAT_RE.sub(" ", s)

    # remove bracketed info for core matching
    s = re.sub(r"\([^)]*\)", " ", s)   # ( ... )
    s = re.sub(r"\[[^\]]*\]", " ", s)  # [ ... ]

    # drop punctuation-ish
    s = re.sub(r"[^a-z0-9\s]", " ", s)

    # collapse whitespace
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _norm_keep_brackets(s: str) -> str:
    """Full normalizer: keep bracketed info but normalize punctuation/whitespace."""
    if s is None:
        return ""
    s = _ascii_fold(str(s)).strip().lower()
    s = s.replace("&", " and ")
    s = _FEAT_RE.sub(" ", s)

    # keep () and [] but normalize everything else
    s = re.sub(r"[^a-z0-9\s()\[\]]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


@dataclass
class MatchResult:
    playlist_row: Dict[str, str]
    status: str  # matched|missing|ambiguous
    score: int
    file_path: str = ""
    matched_artist: str = ""
    matched_title: str = ""
    notes: str = ""


def load_csv_rows(path: str) -> List[Dict[str, str]]:
    with open(path, "r", newline="", encoding="utf-8-sig", errors="replace") as f:
        r = csv.DictReader(f)
        return list(r)
def _pick_col(fieldnames: List[str], *candidates: str) -> str:
    """
    Pick the first matching column from fieldnames using case/whitespace-insensitive compare.
    Returns "" if not found.
    """
    if not fieldnames:
        return ""
    norm_map = {str(fn).strip().lower(): fn for fn in fieldnames}
    for c in candidates:
        key = str(c).strip().lower()
        if key in norm_map:
            return norm_map[key]
    return ""


def _score_pair(
    p_artist: str,
    p_title: str,
    l_artist: str,
    l_title: str,
    p_artist_full: str,
    p_title_full: str,
    l_artist_full: str,
    l_title_full: str,
) -> int:
    a = fuzz.token_set_ratio(p_artist, l_artist)
    t = fuzz.token_set_ratio(p_title, l_title)
    c = fuzz.token_set_ratio(f"{p_artist} {p_title}", f"{l_artist} {l_title}")

    af = fuzz.token_set_ratio(p_artist_full, l_artist_full)
    tf = fuzz.token_set_ratio(p_title_full, l_title_full)
    cf = fuzz.token_set_ratio(f"{p_artist_full} {p_title_full}", f"{l_artist_full} {l_title_full}")

    score = (a * 0.18) + (t * 0.32) + (c * 0.20) + (af * 0.08) + (tf * 0.14) + (cf * 0.08)
    return int(round(score))


def match_playlist_to_library(
    library_csv: str,
    playlist_csv: str,
    library_artist_col: str = "Artist",
    library_title_col: str = "Title",
    library_path_col: str = "FilePath",
    playlist_artist_col: str = "Artist",
    playlist_title_col: str = "Title",
    min_score: int = 92,
    ambiguous_margin: int = 4,
    require_file_exists: bool = True,
    verbose: bool = False,
) -> Tuple[List[MatchResult], Dict[str, int]]:



    lib_rows = load_csv_rows(library_csv)
    pl_rows = load_csv_rows(playlist_csv)

    lib_fields = list(lib_rows[0].keys()) if lib_rows else []
    pl_fields = list(pl_rows[0].keys()) if pl_rows else []

    library_artist_col = _pick_col(lib_fields, library_artist_col, "artist")
    library_title_col = _pick_col(lib_fields, library_title_col, "title")
    library_path_col = _pick_col(
        lib_fields,
        library_path_col,
        "filepath",
        "file path",
        "sourcefile",
        "source file",
    )

    # fallback must be AFTER lib_fields exists
    if (not library_path_col) or (library_path_col not in lib_fields):
        if "SourceFile" in lib_fields:
            library_path_col = "SourceFile"

    playlist_artist_col = _pick_col(pl_fields, playlist_artist_col, "artist")
    playlist_title_col = _pick_col(pl_fields, playlist_title_col, "title")

    if not library_artist_col or not library_title_col or not library_path_col:
        raise ValueError(f"Library CSV missing required columns. Have: {lib_fields}")

    if not playlist_artist_col or not playlist_title_col:
        raise ValueError(f"Playlist CSV missing required columns. Have: {pl_fields}")

    lib = []
    for row in lib_rows:
        fp = row.get(library_path_col, "") or ""
        a = row.get(library_artist_col, "") or ""
        t = row.get(library_title_col, "") or ""
        lib.append(
            {
                "row": row,
                "fp": fp,
                "a_raw": a,
                "t_raw": t,
                "a": _norm(a),
                "t": _norm(t),
                "a_full": _norm_keep_brackets(a),
                "t_full": _norm_keep_brackets(t),
            }
        )

    results: List[MatchResult] = []
    stats = {"playlist_rows": len(pl_rows), "matched": 0, "missing": 0, "ambiguous": 0}

    for prow in pl_rows:
        pa_raw = (prow.get(playlist_artist_col, "") or "").strip()
        pt_raw = (prow.get(playlist_title_col, "") or "").strip()
        pa = _norm(pa_raw)
        pt = _norm(pt_raw)
        pa_full = _norm_keep_brackets(pa_raw)
        pt_full = _norm_keep_brackets(pt_raw)

        # Skip rows that have no usable Artist/Title after normalization
        if not (pa or pt):
            continue

        # Skip YouTube/video-title rows (usually have no Artist and are not real tracks)
        if not pa and pt:
            t = pt_raw.lower()
            bad_markers = [
                "official video", "lyrical video", "wedding video", "bts",
                "full song", "full version", "mashup", " song ",
                "x ", " vs ", " vs.",
                " ranveer ", " anushka ",
            ]
            if any(m in t for m in bad_markers):
                continue

        scored: List[Tuple[int, dict]] = []
        for l in lib:
            s = _score_pair(pa, pt, l["a"], l["t"], pa_full, pt_full, l["a_full"], l["t_full"])
            scored.append((s, l))

        scored.sort(key=lambda x: x[0], reverse=True)
        best_score, best = scored[0]
        second_score = scored[1][0] if len(scored) > 1 else -1

        if verbose:
            print(f"[match] {pa_raw} - {pt_raw} | best={best_score}, second={second_score}")

        best_fp = best["fp"]
        if require_file_exists and best_fp and not os.path.exists(os.path.expanduser(best_fp)):
            results.append(
                MatchResult(
                    prow,
                    "missing",
                    best_score,
                    file_path=best_fp,
                    matched_artist=best["a_raw"],
                    matched_title=best["t_raw"],
                    notes="Matched metadata but FilePath not found on disk",
                )
            )
            stats["missing"] += 1
            continue

        if best_score < min_score:
            results.append(MatchResult(prow, "missing", best_score, notes=f"Below min_score {min_score}"))
            stats["missing"] += 1
            continue

        # If there are multiple perfect matches, auto-pick deterministically (first after sort)
        if best_score == 100 and second_score == 100:
            results.append(
                MatchResult(
                    prow,
                    "matched",
                    best_score,
                    file_path=best_fp,
                    matched_artist=best["a_raw"],
                    matched_title=best["t_raw"],
                    notes="Perfect tie (auto-picked)",
                )
            )
            stats["matched"] += 1
            continue

        if (best_score - second_score) < ambiguous_margin:
            results.append(
                MatchResult(
                    prow,
                    "ambiguous",
                    best_score,
                    file_path=best_fp,
                    matched_artist=best["a_raw"],
                    matched_title=best["t_raw"],
                    notes=f"Top two too close (margin<{ambiguous_margin})",
                )
            )
            stats["ambiguous"] += 1
            continue

        results.append(
            MatchResult(
                prow,
                "matched",
                best_score,
                file_path=best_fp,
                matched_artist=best["a_raw"],
                matched_title=best["t_raw"],
            )
        )
        stats["matched"] += 1

    return results, stats


