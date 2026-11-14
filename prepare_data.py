"""Deterministic input bundle and transcribed reference table data."""

from pathlib import Path
from argparse import Namespace
import sys
import json
import csv
from dataclasses import asdict

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT / "src"))
from port_scheduler.cli import generate
from port_scheduler.domain import load_instance


def main():
    target = ROOT / "data" / "benchmark"
    target.mkdir(parents=True, exist_ok=True)
    generate(
        Namespace(
            instances=10,
            horizon=48.0,
            seed=2026,
            counts=[5, 10, 15, 20, 40],
            out=str(target),
        )
    )
    for p in target.glob("synthetic*.json"):
        d = json.loads(p.read_text())
        n = len(d["vessels"])
        k = d["metadata"]["sample_index"]
        d["name"] = f"n{n:02d}_{k:02d}"
        q = target / (d["name"] + ".json")
        q.write_text(json.dumps(d, indent=2), encoding="utf-8")
        p.unlink()
    files = [ROOT / "data" / "liaoning_12.json", *sorted(target.glob("*.json"))]
    index = []
    for p in files:
        ins = load_instance(p)
        csvpath = p.with_suffix(".csv")
        with csvpath.open("w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(
                f, fieldnames=["id", "eta", "length", "workload", "q_min", "q_max"]
            )
            w.writeheader()
            w.writerows([asdict(v) for v in ins.vessels])
        index.append(
            dict(
                name=ins.name,
                n=len(ins.vessels),
                shoreline=ins.shoreline,
                cranes=ins.cranes,
                productivity=ins.productivity,
                json=str(p.relative_to(ROOT)),
                csv=str(csvpath.relative_to(ROOT)),
                source=(
                    "paper Table 1; ETA interpretation assumption"
                    if len(ins.vessels) == 12
                    else "self-generated, NOT original author instances"
                ),
            )
        )
    with (ROOT / "data" / "instances_index.csv").open(
        "w", newline="", encoding="utf-8-sig"
    ) as f:
        w = csv.DictWriter(f, fieldnames=list(index[0]))
        w.writeheader()
        w.writerows(index)
    ref = ROOT / "data" / "paper_reference"
    ref.mkdir(exist_ok=True)
    tables = {
        2: (
            "method,best,mean,mean_time_seconds_or_bound",
            [
                ["Gurobi", 79.11, 79.11, ">3600"],
                ["GA", 79.11, 80.70, 4.65],
                ["GGA", 79.11, 79.11, 4.72],
            ],
        ),
        4: (
            "instance,Gurobi,GA,GGA,Gurobi_time_s,GA_time_s,GGA_time_s",
            [
                [1, 16, 17, 16, 1.32, 0.91, 0.29],
                [2, 22, 24, 22, 1.72, 0.72, 1.52],
                [3, 19, 21, 19, 0.82, 0.80, 0.64],
                [4, 23, 27, 23, 1.41, 0.99, 1.47],
                [5, 27, 28, 27, 0.96, 0.90, 1.19],
                [6, 30, 32, 30, 0.65, 0.96, 0.21],
                [7, 31, 35, 33, 1.46, 1.16, 1.78],
                [8, 23, 23, 23, 1.17, 0.76, 0.28],
                [9, 33, 37, 34, 2.03, 1.00, 1.27],
                [10, 19, 19, 19, 0.29, 0.72, 0.01],
            ],
        ),
        5: (
            "instance,Gurobi,GA,GGA,Gurobi_time_s,GA_time_s,GGA_time_s",
            [
                [1, 44, 58, 47, 252, 10, 4],
                [2, 47, 60, 47, 47, 5, 5],
                [3, 45, 48, 45, 122, 2, 3],
                [4, 49, 54, 51, 81, 3, 4],
                [5, 36, 36, 36, 648, 2, 3],
                [6, 43, 46, 44, 112, 3, 4],
                [7, 46, 51, 46, 291, 3, 3],
                [8, 35, 37, 35, 266, 3, 4],
                [9, 48, 55, 50, 200, 3, 4],
                [10, 35, 38, 36, ">3600", 3, 3],
            ],
        ),
        6: (
            "instance,GA_avg,GA_min,GGA_avg,GGA_min",
            [
                [1, 107, 100, 83, 81],
                [2, 121, 114, 102, 99],
                [3, 82, 77, 60, 59],
                [4, 102, 93, 86, 82],
                [5, 139, 129, 126, 115],
                [6, 78, 71, 68, 67],
                [7, 96, 92, 71, 68],
                [8, 121, 115, 99, 98],
                [9, 106, 101, 77, 75],
                [10, 107, 98, 93, 92],
            ],
        ),
        7: (
            "instance,GA_avg,GA_min,GGA_avg,GGA_min",
            [
                [1, 145, 137, 113, 109],
                [2, 186, 166, 157, 149],
                [3, 143, 134, 120, 118],
                [4, 208, 189, 173, 164],
                [5, 165, 159, 149, 141],
                [6, 244, 233, 193, 188],
                [7, 238, 222, 185, 180],
                [8, 207, 182, 153, 144],
                [9, 146, 134, 111, 108],
                [10, 97, 93, 86, 84],
            ],
        ),
        8: (
            "instance,Gurobi,GA_avg,GA_min,GGA_avg,GGA_min",
            [
                [1, 474.99, 396.93, 379.54, 280.45, 266.62],
                [2, 373.14, 298.35, 273.83, 223.28, 220.98],
                [3, 475.98, 447.43, 393.83, 323.29, 309.11],
                [4, 220.96, 268.50, 254.66, 189.85, 186.80],
                [5, 328.66, 328.35, 314.61, 236.64, 228.81],
                [6, 258.87, 271.48, 243.88, 201.47, 193.43],
                [7, 587.34, 559.74, 504.39, 335.16, 335.16],
                [8, 236.90, 306.28, 280.10, 232.05, 225.41],
                [9, 378.26, 350.17, 308.24, 255.74, 250.10],
                [10, 325.72, 413.76, 380.93, 270.24, 259.54],
            ],
        ),
    }
    for number, (header, rows) in tables.items():
        with (ref / f"table_{number}.csv").open(
            "w", newline="", encoding="utf-8-sig"
        ) as f:
            w = csv.writer(f)
            w.writerow(header.split(","))
            w.writerows(rows)
    (ref / "README.md").write_text(
        "REFERENCE ONLY: transcribed from Tables 2, 4–8 of the provided paper. Not project-run results. Tables 6–8 retain objective columns for redrawing Figures 5–7; runtime columns for these tables are not transcribed. >3600 is a bound, not a measured number. No published averages were copied into recomputed statistics. DOI: 10.21203/rs.3.rs-9235581/v1.\n",
        encoding="utf-8",
    )
    print("Prepared 51 main instances, JSON + CSV, and reference tables.")


if __name__ == "__main__":
    main()
