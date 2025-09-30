#!/usr/bin/env python3
"""Sweep LBA stride values for queue_depth_burst and plot IOPS."""

import argparse
import csv
import math
import re
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Tuple

try:
    import matplotlib.pyplot as plt
except ModuleNotFoundError:  # pragma: no cover
    plt = None

IOPS_TOKEN = "Simulated IOPS"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", default="./build/examples/queue_depth_burst",
                        help="Path to the queue_depth_burst executable (default: %(default)s)")
    parser.add_argument("--transport", default="trtype:PCIe",
                        help="Transport ID string passed after -r (default: %(default)s)")
    parser.add_argument("--queue", type=int, default=1,
                        help="Queue count for -q (default: %(default)s)")
    parser.add_argument("--lba-span", type=int, default=1,
                        help="LBAs per command (-l value, default: %(default)s)")
    parser.add_argument("--start", type=int, default=1,
                        help="Starting LBA stride value (inclusive)")
    parser.add_argument("--stop", type=int, default=10000,
                        help="Ending LBA stride value (inclusive)")
    parser.add_argument("--step", type=int, default=100,
                        help="Stride increment between runs (default: %(default)s)")
    parser.add_argument("--sudo", action="store_true",
                        help="Prefix the command with sudo")
    parser.add_argument("--save", type=Path,
                        help="Path to save the generated plot instead of showing it")
    parser.add_argument("--csv", type=Path,
                        help="Optional CSV output file for stride/IOPS pairs")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print commands only without executing")
    parser.add_argument("--quiet", action="store_true",
                        help="Suppress command stdout/stderr except errors")
    return parser.parse_args()


def run_once(args: argparse.Namespace, stride: int) -> Optional[float]:
    cmd = []
    if args.sudo:
        cmd.append("sudo")
    cmd.extend([
        args.binary,
        "-r", args.transport,
        "-q", str(args.queue),
        "-m", str(stride),
        "-l", str(args.lba_span),
    ])

    if args.dry_run:
        print("DRY-RUN:", " ".join(cmd))
        return math.nan

    result = subprocess.run(cmd, capture_output=True, text=True)
    output = (result.stdout or "") + (result.stderr or "")

    if not args.quiet:
        sys.stdout.write(output)
        if output and not output.endswith("\n"):
            sys.stdout.write("\n")

    if result.returncode != 0:
        sys.stderr.write(f"Command failed for stride {stride} with code {result.returncode}\n")
        return None

    for line in output.splitlines():
        if IOPS_TOKEN in line:
            try:
                _, value_str = line.split(":", 1)
                return float(value_str.strip().split()[0])
            except (ValueError, IndexError):
                match = re.search(r"([-+]?[0-9]*\.?[0-9]+)", line)
                if match:
                    try:
                        return float(match.group(1))
                    except ValueError:
                        pass
                continue

    sys.stderr.write(f"Unable to parse IOPS from stride {stride} output.\n")
    return None


def write_csv(csv_path: Path, rows: List[Tuple[int, Optional[float]]]) -> None:
    with csv_path.open("w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["stride", "iops"])
        writer.writerows(rows)


def plot(rows: List[Tuple[int, Optional[float]]], save_path: Optional[Path]) -> None:
    if plt is None:
        sys.stderr.write("matplotlib not available; skipping plot.\n")
        return

    strides = [s for s, i in rows if i is not None and not math.isnan(i)]
    iops = [i for _, i in rows if i is not None and not math.isnan(i)]

    if not strides:
        sys.stderr.write("No valid data collected; nothing to plot.\n")
        return

    plt.figure(figsize=(10, 5))
    plt.plot(strides, iops, marker="o", linestyle="-", linewidth=1)
    plt.xlabel("LBA stride (-m)")
    plt.ylabel("Simulated IOPS")
    plt.title("queue_depth_burst IOPS vs. LBA stride")
    plt.grid(True, which="both", linestyle="--", linewidth=0.5)

    if save_path:
        plt.savefig(save_path, bbox_inches="tight")
        print(f"Plot saved to {save_path}")
    else:
        plt.show()


def main() -> int:
    args = parse_args()

    if args.step <= 0:
        sys.stderr.write("--step must be positive.\n")
        return 2
    if args.start <= 0 or args.stop < args.start:
        sys.stderr.write("Invalid stride range specified.\n")
        return 2

    rows: List[Tuple[int, Optional[float]]] = []

    for stride in range(args.start, args.stop + 1, args.step):
        iops = run_once(args, stride)
        rows.append((stride, iops))

    if args.csv:
        write_csv(args.csv, rows)
        print(f"CSV written to {args.csv}")

    if not args.dry_run:
        plot(rows, args.save)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
