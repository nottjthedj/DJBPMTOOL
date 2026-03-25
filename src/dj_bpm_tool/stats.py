import csv
import math
import os
from collections import Counter, defaultdict

def _to_float(s: str):
    if s is None:
        return None
    s = str(s).strip()
    if not s:
        return None
    try:
        v = float(s)
        if v <= 0:
            return None
        return v
    except Exception:
        return None

def _norm_group_value(v: str, unknown_label: str = "(blank)") -> str:
    if v is None:
        return unknown_label
    s = str(v).strip()
    return s if s else unknown_label

def _update_group(group_map: dict, key: str, bpm_value) -> None:
    g = group_map[key]
    g["rows_total"] += 1
    if bpm_value is None:
        g["bpm_blank"] += 1
    else:
        g["bpm_numeric"] += 1

def _finalize_groups(group_map: dict) -> dict:
    out = {}
    for k, v in group_map.items():
        total = v["rows_total"]
        numeric = v["bpm_numeric"]
        blank = v["bpm_blank"]
        fill_rate = (numeric / total) if total else 0.0
        out[k] = {
            "rows_total": total,
            "bpm_numeric": numeric,
            "bpm_blank": blank,
            "fill_rate": round(fill_rate, 4),
        }
    return out

def _resolve_column(fieldnames, desired_name: str):
    """
    Return the actual column name in the CSV matching desired_name,
    ignoring case and surrounding whitespace. Returns None if not found.
    """
    if not fieldnames:
        return None
    desired = desired_name.strip().lower()
    for fn in fieldnames:
        if fn is None:
            continue
        if str(fn).strip().lower() == desired:
            return fn
    return None

def bpm_stats_from_csv(csv_path: str, bucket_size: int = 10, top_n_groups: int = 15) -> dict:
    stats = {
        "rows_total": 0,
        "bpm_blank": 0,
        "bpm_numeric": 0,
        "bpm_non_numeric": 0,
        "bpm_min": None,
        "bpm_max": None,
        "bucket_size": bucket_size,
        "buckets": {},
        "top_buckets": [],
        "by_genre": {},
        "by_directory": {},
        "top_missing_directories": [],
        "top_genres_by_rows": [],
        "top_directories_by_rows": [],
        "directory_source": None,  # "Directory" or "FilePath"
    }

    buckets = Counter()

    by_genre = defaultdict(lambda: {"rows_total": 0, "bpm_numeric": 0, "bpm_blank": 0})
    by_dir = defaultdict(lambda: {"rows_total": 0, "bpm_numeric": 0, "bpm_blank": 0})
    missing_by_dir = Counter()

    with open(csv_path, newline="", encoding="utf-8", errors="replace") as f:
        r = csv.DictReader(f)
        if not r.fieldnames:
            raise ValueError("CSV has no header row")

        bpm_col = _resolve_column(r.fieldnames, "BPM")
        if not bpm_col:
            raise ValueError("CSV must contain a 'BPM' column")

        file_col = _resolve_column(r.fieldnames, "FilePath")
        genre_col = _resolve_column(r.fieldnames, "Genre")
        dir_col = _resolve_column(r.fieldnames, "Directory")

        # Directory source: prefer explicit Directory column; else derive from FilePath if available
        if dir_col:
            stats["directory_source"] = "Directory"
        elif file_col:
            stats["directory_source"] = "FilePath"
        else:
            stats["directory_source"] = None

        for row in r:
            stats["rows_total"] += 1

            raw_bpm = row.get(bpm_col)
            bpm_num = _to_float(raw_bpm) if (raw_bpm is not None and str(raw_bpm).strip() != "") else None

            # global counters
            if raw_bpm is None or str(raw_bpm).strip() == "":
                stats["bpm_blank"] += 1
            else:
                if bpm_num is None:
                    stats["bpm_non_numeric"] += 1
                else:
                    stats["bpm_numeric"] += 1
                    stats["bpm_min"] = bpm_num if stats["bpm_min"] is None else min(stats["bpm_min"], bpm_num)
                    stats["bpm_max"] = bpm_num if stats["bpm_max"] is None else max(stats["bpm_max"], bpm_num)

                    b0 = int(math.floor(bpm_num / bucket_size) * bucket_size)
                    label = f"{b0}-{b0 + bucket_size - 1}"
                    buckets[label] += 1

            # Genre breakdown (if present)
            if genre_col:
                genre = _norm_group_value(row.get(genre_col))
                _update_group(by_genre, genre, bpm_num)

            # Directory breakdown (explicit Directory OR derived from FilePath)
            directory_value = None
            if dir_col:
                directory_value = row.get(dir_col)
            elif file_col:
                fp = row.get(file_col)
                if fp:
                    directory_value = os.path.dirname(str(fp))

            if directory_value is not None:
                d = _norm_group_value(directory_value)
                _update_group(by_dir, d, bpm_num)
                if bpm_num is None:
                    missing_by_dir[d] += 1

    stats["buckets"] = dict(buckets)
    stats["top_buckets"] = buckets.most_common(10)

    by_genre_final = _finalize_groups(by_genre)
    by_dir_final = _finalize_groups(by_dir)

    stats["by_genre"] = by_genre_final
    stats["by_directory"] = by_dir_final

    stats["top_missing_directories"] = missing_by_dir.most_common(top_n_groups)

    if by_genre_final:
        stats["top_genres_by_rows"] = sorted(
            ((k, v["rows_total"], v["fill_rate"]) for k, v in by_genre_final.items()),
            key=lambda x: x[1],
            reverse=True
        )[:top_n_groups]

    if by_dir_final:
        stats["top_directories_by_rows"] = sorted(
            ((k, v["rows_total"], v["fill_rate"]) for k, v in by_dir_final.items()),
            key=lambda x: x[1],
            reverse=True
        )[:top_n_groups]

    return stats
