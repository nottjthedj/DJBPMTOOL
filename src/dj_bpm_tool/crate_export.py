import csv
import os
from typing import List

from .crate_match import MatchResult


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def write_reports(results: List[MatchResult], out_dir: str, crate_name: str) -> dict:
    _ensure_dir(out_dir)

    audit_path = os.path.join(out_dir, "match_audit.csv")
    missing_path = os.path.join(out_dir, "missing_tracks.csv")
    ambig_path = os.path.join(out_dir, "ambiguous_matches.csv")
    m3u_path = os.path.join(out_dir, f"{crate_name}.m3u")

    audit_fields = [
        "status",
        "score",
        "playlist_artist",
        "playlist_title",
        "matched_artist",
        "matched_title",
        "file_path",
        "notes",
    ]

    def prow_get(r: MatchResult, k: str) -> str:
        return (r.playlist_row.get(k, "") or "").strip()

    with open(audit_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=audit_fields)
        w.writeheader()
        for r in results:
            w.writerow(
                {
                    "status": r.status,
                    "score": r.score,
                    "playlist_artist": prow_get(r, "Artist"),
                    "playlist_title": prow_get(r, "Title"),
                    "matched_artist": r.matched_artist,
                    "matched_title": r.matched_title,
                    "file_path": r.file_path,
                    "notes": r.notes,
                }
            )

    with open(missing_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=audit_fields)
        w.writeheader()
        for r in results:
            if r.status == "missing":
                w.writerow(
                    {
                        "status": r.status,
                        "score": r.score,
                        "playlist_artist": prow_get(r, "Artist"),
                        "playlist_title": prow_get(r, "Title"),
                        "matched_artist": r.matched_artist,
                        "matched_title": r.matched_title,
                        "file_path": r.file_path,
                        "notes": r.notes,
                    }
                )

    with open(ambig_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=audit_fields)
        w.writeheader()
        for r in results:
            if r.status == "ambiguous":
                w.writerow(
                    {
                        "status": r.status,
                        "score": r.score,
                        "playlist_artist": prow_get(r, "Artist"),
                        "playlist_title": prow_get(r, "Title"),
                        "matched_artist": r.matched_artist,
                        "matched_title": r.matched_title,
                        "file_path": r.file_path,
                        "notes": r.notes,
                    }
                )

    with open(m3u_path, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for r in results:
            if r.status == "matched" and r.file_path:
                f.write(r.file_path + "\n")

    return {
        "audit": audit_path,
        "missing": missing_path,
        "ambiguous": ambig_path,
        "m3u": m3u_path,
    }
