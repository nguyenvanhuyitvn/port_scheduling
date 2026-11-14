"""CLI matrix: paper-like presets are explicit; quick validation is not the paper budget."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))
import argparse
from port_scheduler.experiments import Config, run_matrix
from port_scheduler.charts import export_suite


def main():
    p = argparse.ArgumentParser()
    p.add_argument(
        "--preset",
        choices=["quick", "paper-time", "paper-generations"],
        default="quick",
    )
    p.add_argument(
        "--groups",
        nargs="+",
        type=int,
        choices=[5, 10, 15, 20, 40],
        default=[5, 10, 15, 20, 40],
    )
    p.add_argument("--instances", type=int, default=10)
    p.add_argument("--repeats", type=int, default=10)
    p.add_argument(
        "--algorithms",
        nargs="+",
        choices=["greedy", "ga", "gga", "ga_greedy", "ga_repair", "mip"],
        default=["greedy", "ga", "gga"],
    )
    p.add_argument("--solver", choices=["highs", "gurobi"], default="highs")
    p.add_argument("--seconds", type=float, default=None)
    p.add_argument("--solver-seconds", type=float, default=None)
    p.add_argument("--generations", type=int, default=100)
    p.add_argument("--include-real", action="store_true")
    p.add_argument("--out", default="results/benchmark")
    a = p.parse_args()
    if not 1 <= a.instances <= 10 or not 1 <= a.repeats <= 10:
        p.error("instances/repeats must be in 1..10")
    root = Path(__file__).parent
    for n in a.groups:
        # One signature per budget: a 60s n40 run is not grouped with a 5s run.
        seconds = (
            a.seconds
            if a.seconds is not None
            else (0.25 if a.preset == "quick" else (60.0 if n == 40 else 5.0))
        )
        mode = "generations" if a.preset == "paper-generations" and n != 40 else "time"
        cfg = Config(
            mode=mode,
            seconds=seconds,
            generations=a.generations,
            solver=a.solver,
            solver_seconds=(
                a.solver_seconds
                if a.solver_seconds is not None
                else (1.0 if a.preset == "quick" else (60.0 if n == 40 else 3600.0))
            ),
        )
        files = sorted((root / "data" / "benchmark").glob(f"n{n:02d}_*.json"))[
            : a.instances
        ]
        if a.include_real and n == a.groups[0]:
            files.append(root / "data" / "liaoning_12.json")

        def progress(i, total, msg):
            print(f"{n} vessels | {i}/{total} | {msg}", flush=True)

        out, records, summary, errors = run_matrix(
            files, a.algorithms, list(range(a.repeats)), cfg, root / a.out, progress
        )
        export_suite(out)
        print(
            f"SAVED {out} | {len(records)} records | {len(errors)} errors", flush=True
        )


if __name__ == "__main__":
    main()
