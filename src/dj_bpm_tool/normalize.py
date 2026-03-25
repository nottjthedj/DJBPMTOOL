import csv
import math

def normalize_bpm_value(value: str, mode: str) -> str:
    s = (value or "").strip()
    if not s:
        return ""

    try:
        v = float(s)
    except Exception:
        return s  # leave as-is if not numeric

    if v <= 0:
        return ""

    mode = (mode or "round").lower()

    if mode == "round":
        return str(int(round(v)))
    if mode == "floor":
        return str(int(math.floor(v)))
    if mode == "ceil":
        return str(int(math.ceil(v)))
    if mode == "keep1":
        return f"{v:.1f}"
    if mode == "keep2":
        return f"{v:.2f}"

    raise ValueError("mode must be one of: round, floor, ceil, keep1, keep2")

def normalize_bpm_csv(in_csv_path: str, out_csv_path: str, mode: str = "round") -> dict[str, int]:
    stats = {"rows_total": 0, "bpm_changed": 0, "bpm_blank": 0}

    with open(in_csv_path, newline="", encoding="utf-8", errors="replace") as f_in, \
         open(out_csv_path, "w", newline="", encoding="utf-8") as f_out:

        r = csv.DictReader(f_in)
        if not r.fieldnames:
            raise ValueError("Input CSV has no header row")

        if "BPM" not in r.fieldnames:
            raise ValueError("Input CSV must contain a 'BPM' column")

        w = csv.DictWriter(f_out, fieldnames=r.fieldnames)
        w.writeheader()

        for row in r:
            stats["rows_total"] += 1
            before = (row.get("BPM") or "").strip()
            if not before:
                stats["bpm_blank"] += 1
                w.writerow(row)
                continue

            after = normalize_bpm_value(before, mode)
            if after != before:
                row["BPM"] = after
                stats["bpm_changed"] += 1

            w.writerow(row)

    return stats
