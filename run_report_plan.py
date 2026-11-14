"""Run the full experiment plan for the course report.

Phases (each phase is resumable: finished runs are skipped on re-run):
  verify    Model check: corrected vs printed_core MIP on example_100/200.
  liaoning  Real data, 12 vessels: greedy, GA, GGA, both ablation variants, MIP.
  main      Synthetic groups 5/10/15/20/40 vessels: greedy, GA, GGA (+ MIP for 5, 10, 40).
  ablation  GA + greedy init, GA + repair on groups 15 and 20 (all 10 instances).

Examples:
  .venv/bin/python run_report_plan.py --dry-run
  .venv/bin/python run_report_plan.py --phases verify liaoning
  .venv/bin/python run_report_plan.py --scale 0.05 --repeats 2 --instances 2 --out results/report_smoke
  .venv/bin/python run_report_plan.py              # everything, several hours

Afterwards: .venv/bin/python analyze_report.py --root results/report
"""

import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))
from port_scheduler.experiments import Config, run_matrix

ROOT = Path(__file__).parent
# Heuristic seconds per run and MIP seconds per instance for each vessel group.
BUDGET = {
    5: dict(seconds=2.0, mip=300.0),
    10: dict(seconds=5.0, mip=300.0),
    15: dict(seconds=10.0, mip=None),
    20: dict(seconds=20.0, mip=None),
    40: dict(seconds=60.0, mip=60.0),
    12: dict(seconds=5.0, mip=300.0),
}
ABLATION_GROUPS = (15, 20)
ABLATION_INSTANCES = 10  # >=6 pairs needed for a two-sided Wilcoxon p<0.05


def jobs(a):
    """Yield (phase, n, files, algorithms, config)."""
    s = a.scale

    def cfg(n):
        b = BUDGET[n]
        return Config(
            mode="time",
            seconds=b["seconds"] * s,
            solver=a.solver,
            solver_seconds=(b["mip"] or 1.0) * s,
            population=a.population,
        )

    def bench(n, k):
        return sorted((ROOT / "data" / "benchmark").glob(f"n{n:02d}_*.json"))[:k]

    if "liaoning" in a.phases:
        algs = ["greedy", "ga", "gga", "ga_greedy", "ga_repair"] + (
            [] if a.no_mip else ["mip"]
        )
        yield "liaoning", 12, [ROOT / "data" / "liaoning_12.json"], algs, cfg(12)
    if "main" in a.phases:
        for n in a.groups:
            algs = ["greedy", "ga", "gga"] + (
                ["mip"] if BUDGET[n]["mip"] and not a.no_mip else []
            )
            yield "main", n, bench(n, a.instances), algs, cfg(n)
    if "ablation" in a.phases:
        for n in ABLATION_GROUPS:
            if n in a.groups:
                # Same Config as 'main' -> same experiment folder; GA/GGA runs are reused.
                yield "ablation", n, bench(n, min(a.instances, ABLATION_INSTANCES)), [
                    "ga",
                    "gga",
                    "ga_greedy",
                    "ga_repair",
                ], cfg(n)


def estimate(n_files, algs, config, repeats):
    total = 0.0
    for alg in algs:
        if alg == "greedy":
            total += 0.5 * n_files
        elif alg == "mip":
            total += config.solver_seconds * n_files
        else:
            total += config.seconds * repeats * n_files
    return total


def main():
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument(
        "--phases",
        nargs="+",
        choices=["verify", "liaoning", "main", "ablation"],
        default=["verify", "liaoning", "main", "ablation"],
    )
    p.add_argument(
        "--groups",
        nargs="+",
        type=int,
        choices=[5, 10, 15, 20, 40],
        default=[5, 10, 15, 20, 40],
    )
    p.add_argument(
        "--instances", type=int, default=10, help="instances per group (1..10)"
    )
    p.add_argument(
        "--repeats", type=int, default=10, help="seeds per stochastic algorithm"
    )
    p.add_argument("--solver", choices=["highs", "gurobi"], default="highs")
    p.add_argument("--no-mip", action="store_true", help="skip MIP runs")
    p.add_argument("--population", type=int, default=40)
    p.add_argument(
        "--scale",
        type=float,
        default=1.0,
        help="multiply every time budget (e.g. 0.05 for a smoke test)",
    )
    p.add_argument("--out", default="results/report")
    p.add_argument(
        "--dry-run", action="store_true", help="print the plan and estimated time only"
    )
    a = p.parse_args()
    if not 1 <= a.instances <= 10 or a.repeats < 1 or a.scale <= 0:
        p.error("invalid instances/repeats/scale")
    out = ROOT / a.out
    plan = list(jobs(a))
    grand = 0.0
    print(f"Output: {out} | solver: {a.solver} | seeds: {a.repeats} | scale: {a.scale}")
    for phase, n, files, algs, config in plan:
        est = estimate(len(files), algs, config, a.repeats)
        grand += est
        print(
            f'  [{phase:8}] n={n:>2} | {len(files):>2} instance(s) | {",".join(algs):38} | '
            f"heuristic {config.seconds:g}s, MIP {config.solver_seconds:g}s | worst case ~{est/3600:.2f} h"
        )
    print(
        f"Worst-case total (MIP runs to its limit; re-runs skip finished jobs): ~{grand/3600:.2f} h"
    )
    if a.dry_run:
        return
    if "verify" in a.phases:
        print("== verify: corrected vs printed_core", flush=True)
        subprocess.run(
            [
                sys.executable,
                "-m",
                "port_scheduler",
                "verify-examples",
                "--solver",
                a.solver,
                "--seconds",
                "10",
                "--out",
                str(out / "verification"),
            ],
            check=True,
            env={**__import__("os").environ, "PYTHONPATH": str(ROOT / "src")},
        )
    for phase, n, files, algs, config in plan:

        def progress(i, total, msg):
            print(f"[{phase}] n={n} | {i}/{total} | {msg}", flush=True)

        root, records, _, errors = run_matrix(
            files, algs, list(range(a.repeats)), config, out, progress
        )
        print(
            f"[{phase}] n={n} saved in {root} | {len(records)} runs in folder | {len(errors)} errors",
            flush=True,
        )
    print(f"Done. Next: {sys.executable} analyze_report.py --root {a.out}")


if __name__ == "__main__":
    main()
