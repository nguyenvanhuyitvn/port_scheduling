"""Run an explicitly selected experiment matrix. Paths with spaces are supported."""

import argparse
import subprocess
import sys
from pathlib import Path


def main():
    p = argparse.ArgumentParser()
    p.add_argument(
        "--instances",
        nargs="+",
        required=True,
        help="JSON files or directories (recursive)",
    )
    p.add_argument(
        "--algorithms",
        nargs="+",
        choices=["greedy", "ga", "gga", "ga_greedy", "ga_repair", "mip"],
        default=["ga", "gga"],
    )
    p.add_argument("--seeds", nargs="+", type=int, default=list(range(10)))
    p.add_argument("--seconds", type=float, default=5)
    p.add_argument("--solver", choices=["highs", "gurobi"], default="highs")
    p.add_argument("--out", default="results/experiment")
    p.add_argument("--plot", action="store_true")
    args = p.parse_args()
    files = []
    for item in args.instances:
        path = Path(item)
        files.extend(sorted(path.rglob("*.json")) if path.is_dir() else [path])
    files = list(dict.fromkeys(files))
    if not files:
        p.error("No JSON instances")
    for file in files:
        for algorithm in args.algorithms:
            for seed in (
                args.seeds[:1] if algorithm in ["mip", "greedy"] else args.seeds
            ):
                label = (
                    f"{algorithm}_{args.solver}" if algorithm == "mip" else algorithm
                )
                out = Path(args.out) / file.stem / f"{label}_seed{seed}"
                out.mkdir(parents=True, exist_ok=True)
                cmd = [
                    sys.executable,
                    "-m",
                    "port_scheduler",
                    "run",
                    "--instance",
                    str(file),
                    "--algorithm",
                    algorithm,
                    "--solver",
                    args.solver,
                    "--seconds",
                    str(args.seconds),
                    "--seed",
                    str(seed),
                    "--out",
                    str(out),
                ]
                if args.plot:
                    cmd.append("--plot")
                print(f"{file.name} | {label} | seed {seed}", flush=True)
                with (out / "console.log").open("w", encoding="utf-8") as log:
                    subprocess.run(
                        cmd, stdout=log, stderr=subprocess.STDOUT, check=True
                    )
    subprocess.run(
        [
            sys.executable,
            "-m",
            "port_scheduler",
            "summarize",
            "--root",
            args.out,
            "--out",
            str(Path(args.out) / "summary.csv"),
        ],
        check=True,
    )


if __name__ == "__main__":
    main()
