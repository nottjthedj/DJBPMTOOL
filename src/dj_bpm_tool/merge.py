import csv

def load_bpm_map(bpm_csv_path: str) -> dict[str, str]:
    bpm_map: dict[str, str] = {}
    with open(bpm_csv_path, newline="", encoding="utf-8", errors="replace") as f:
        r = csv.DictReader(f)
        if not r.fieldnames:
            return bpm_map
        for row in r:
            fp = (row.get("FilePath") or "").strip()
            bpm = (row.get("BPM") or "").strip()
            if fp:
                bpm_map[fp] = bpm
    return bpm_map

def merge_bpm_into_master(master_csv_path: str, bpm_csv_path: str, out_csv_path: str) -> dict[str, int]:
    bpm_map = load_bpm_map(bpm_csv_path)

    stats = {
        "rows_total": 0,
        "rows_blank_bpm": 0,
        "rows_filled": 0,
        "rows_missing_filepath": 0,
    }

    with open(master_csv_path, newline="", encoding="utf-8", errors="replace") as f_in, \
         open(out_csv_path, "w", newline="", encoding="utf-8") as f_out:

        r = csv.DictReader(f_in)
        if not r.fieldnames:
            raise ValueError("Master CSV has no header row")

        if "FilePath" not in r.fieldnames or "BPM" not in r.fieldnames:
            raise ValueError("Master CSV must contain 'FilePath' and 'BPM' columns")

        w = csv.DictWriter(f_out, fieldnames=r.fieldnames)
        w.writeheader()

        for row in r:
            stats["rows_total"] += 1
            fp = (row.get("FilePath") or "").strip()
            bpm = (row.get("BPM") or "").strip()

            if not fp:
                stats["rows_missing_filepath"] += 1
                w.writerow(row)
                continue

            if not bpm:
                stats["rows_blank_bpm"] += 1
                new_bpm = (bpm_map.get(fp) or "").strip()
                if new_bpm:
                    row["BPM"] = new_bpm
                    stats["rows_filled"] += 1

            w.writerow(row)

    return stats
