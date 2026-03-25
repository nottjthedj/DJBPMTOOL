import argparse
import csv
import os
import sys
import json

from .core import extract_bpm_from_mp3
from .merge import merge_bpm_into_master
from .normalize import normalize_bpm_csv
from .stats import bpm_stats_from_csv

def cmd_scan(args: argparse.Namespace) -> int:
    root = os.path.expanduser(args.music)
    out = os.path.expanduser(args.out)

    rows = 0
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["FilePath", "BPM"])
        w.writeheader()

        for dirpath, _, filenames in os.walk(root):
            for fn in filenames:
                if not fn.lower().endswith(".mp3"):
                    continue
                p = os.path.join(dirpath, fn)
                bpm = extract_bpm_from_mp3(p)
                w.writerow({"FilePath": p, "BPM": bpm})
                rows += 1
                if args.progress and rows % 1000 == 0:
                    print(f"Processed {rows} mp3...", file=sys.stderr)

    print(f"Wrote {rows} rows -> {out}")
    return 0

def cmd_merge(args: argparse.Namespace) -> int:
    master = os.path.expanduser(args.master)
    bpmcsv = os.path.expanduser(args.bpm_csv)
    out = os.path.expanduser(args.out)

    stats = merge_bpm_into_master(master, bpmcsv, out)
    print(f"Wrote merged CSV -> {out}")
    print("Stats:", stats)
    return 0

def cmd_normalize(args: argparse.Namespace) -> int:
    inp = os.path.expanduser(args.input)
    out = os.path.expanduser(args.out)
    mode = args.mode

    stats = normalize_bpm_csv(inp, out, mode=mode)
    print(f"Wrote normalized CSV -> {out}")
    print("Stats:", stats)
    return 0

def cmd_stats(args: argparse.Namespace) -> int:
    inp = os.path.expanduser(args.input)
    bucket_size = args.bucket_size

    stats = bpm_stats_from_csv(inp, bucket_size=bucket_size)

    if args.json:
        print(json.dumps(stats, indent=2))
    else:
        filled = stats["bpm_numeric"]
        blank = stats["bpm_blank"]
        nonnum = stats["bpm_non_numeric"]
        total = stats["rows_total"]

        print(f"Rows total: {total}")
        print(f"BPM numeric: {filled}")
        print(f"BPM blank: {blank}")
        print(f"BPM non-numeric: {nonnum}")
        print(f"BPM min/max: {stats['bpm_min']} / {stats['bpm_max']}")
        print(f"Top buckets (size={bucket_size}):")
        for label, count in stats["top_buckets"]:
            print(f"  {label}: {count}")

        if stats.get("directory_source"):
            print(f"\nDirectory source: {stats['directory_source']}")

        if stats.get("top_genres_by_rows"):
            print("\nTop Genres by rows (rows, fill_rate):")
            for g, rows, fill in stats["top_genres_by_rows"]:
                print(f"  {g}: {rows}, {fill}")

        if stats.get("top_directories_by_rows"):
            print("\nTop Directories by rows (rows, fill_rate):")
            for d, rows, fill in stats["top_directories_by_rows"]:
                print(f"  {d}: {rows}, {fill}")

        if stats.get("top_missing_directories"):
            print("\nTop Directories missing BPM (blank rows):")
            for d, miss in stats["top_missing_directories"]:
                print(f"  {d}: {miss}")

    return 0

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="dj-bpm", description="DJ BPM extractor + CSV tools (MP3 only)")
    sub = p.add_subparsers(dest="command", required=True)

    scan = sub.add_parser("scan", help="Scan a folder of MP3s and export BPM CSV")
    scan.add_argument("--music", required=True, help="Root folder to scan (e.g., ~/Music)")
    scan.add_argument("--out", required=True, help="Output CSV path (e.g., ~/bpm_export.csv)")
    scan.add_argument("--progress", action="store_true", help="Print progress every 1000 files")
    scan.set_defaults(func=cmd_scan)

    merge = sub.add_parser("merge", help="Merge BPM CSV into a master CSV by full FilePath (fill blank BPM only)")
    merge.add_argument("--master", required=True, help="Master CSV path (must have FilePath and BPM columns)")
    merge.add_argument("--bpm-csv", dest="bpm_csv", required=True, help="BPM export CSV path (FilePath,BPM)")
    merge.add_argument("--out", required=True, help="Output merged CSV path")
    merge.set_defaults(func=cmd_merge)

    norm = sub.add_parser("normalize", help="Normalize BPM values in a CSV (round/floor/ceil/keep1/keep2)")
    norm.add_argument("--input", required=True, help="Input CSV path (must have BPM column)")
    norm.add_argument("--out", required=True, help="Output CSV path")
    norm.add_argument("--mode", default="round", help="round|floor|ceil|keep1|keep2 (default: round)")
    norm.set_defaults(func=cmd_normalize)

    st = sub.add_parser("stats", help="Summarize BPM coverage and distribution for a CSV")
    st.add_argument("--input", required=True, help="Input CSV path (must have BPM column)")
    st.add_argument("--bucket-size", type=int, default=10, help="Histogram bucket size (default: 10)")
    st.add_argument("--json", action="store_true", help="Print raw JSON stats")
    st.set_defaults(func=cmd_stats)

    return p

def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    raise SystemExit(args.func(args))
