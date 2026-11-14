import argparse
import csv
import hashlib
import importlib.metadata
import json
import platform
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
from .domain import (
    Assignment,
    Instance,
    Vessel,
    load_instance,
    serialize_rows,
    write_json,
)
from .heuristics import run as run_heuristic
from .mip import solve
from .validation import validate


def environment():
    versions = {}
    for name in ["numpy", "scipy", "matplotlib", "gurobipy"]:
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = None
    return dict(
        python=sys.version,
        platform=platform.platform(),
        machine=platform.machine(),
        processor=platform.processor(),
        packages=versions,
    )


def save_run(ins, result, out, input_path):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    rows = result["schedule"]
    payload = {**result, "schedule": serialize_rows(rows)}
    write_json(out / "run.json", payload)
    write_json(out / "instance.json", asdict(ins))
    raw = Path(input_path).read_bytes()
    write_json(
        out / "manifest.json",
        dict(
            created_utc=datetime.now(timezone.utc).isoformat(),
            input_sha256=hashlib.sha256(raw).hexdigest(),
            input_name=Path(input_path).name,
            source_code_sha256=hashlib.sha256(
                b"".join(
                    p.read_bytes() for p in sorted(Path(__file__).parent.glob("*.py"))
                )
            ).hexdigest(),
            environment=environment(),
            timing="wall clock; plotting and file writing excluded",
            note="Independent implementation, not original paper code",
        ),
    )
    with (out / "schedule.csv").open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "vessel_id",
                "eta",
                "start",
                "end",
                "duration",
                "waiting",
                "flow_time",
                "position",
                "length",
                "cranes",
            ]
        )
        vs = {v.id: v for v in ins.vessels}
        for r in sorted(rows, key=lambda x: x.vessel_id):
            v = vs[r.vessel_id]
            w.writerow(
                [
                    v.id,
                    v.eta,
                    r.start,
                    r.end,
                    r.end - r.start,
                    r.start - v.eta,
                    r.end - v.eta,
                    r.position,
                    v.length,
                    " ".join(map(str, r.cranes)),
                ]
            )
    if "history" in result:
        with (out / "history.csv").open("w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=["seconds", "generation", "objective"])
            w.writeheader()
            w.writerows(result["history"])


def run_one(args):
    ins = load_instance(args.instance)
    if args.algorithm == "mip":
        result = solve(
            ins,
            args.solver,
            args.seconds if args.seconds is not None else 10,
            args.model == "printed_core",
            args.seed,
            args.threads,
        )
    else:
        if args.model != "corrected":
            raise ValueError("printed_core is only a MIP diagnostic")
        result = run_heuristic(
            ins,
            args.algorithm,
            args.seconds,
            args.generations,
            args.population,
            args.seed,
            args.pc,
            args.pm,
            args.beta,
        )
    result["algorithm"] = args.algorithm
    result["seed"] = args.seed
    save_run(ins, result, args.out, args.instance)
    if args.plot and result["feasible"]:
        from .plotting import plot

        plot(ins, result["schedule"], args.out)
    print(
        json.dumps(
            {
                k: v
                for k, v in result.items()
                if k not in {"schedule", "history", "parameters"}
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    print(f"Saved: {Path(args.out).resolve()}")


def generate(args):
    if args.instances < 1 or args.horizon <= 0:
        raise ValueError("instances and horizon must be positive")
    rng = np.random.default_rng(args.seed)
    for n in args.counts:
        if n < 5 or n % 5:
            raise ValueError("counts must be multiples of 5 and >=5")
        L, m = (1000, 10) if n <= 10 else ((1200, 12) if n <= 20 else (1500, 15))
        for k in range(args.instances):
            vessels = []
            classes = (
                [(80, 210, 100, 300, 1, 2)] * (2 * n // 5)
                + [(210, 300, 300, 1000, 2, 4)] * (2 * n // 5)
                + [(300, 400, 1000, 1300, 4, 6)] * (n // 5)
            )
            for i, ci in enumerate(classes):
                a, b, c, d, q0, q1 = ci
                vessels.append(
                    Vessel(
                        f"V{i+1}",
                        round(float(rng.uniform(0, args.horizon)), 3),
                        int(rng.integers(a, b + 1)),
                        int(rng.integers(c, d + 1)),
                        q0,
                        q1,
                    )
                )
            ins = Instance(
                f"synthetic_n{n}_{k+1:02d}",
                L,
                m,
                35,
                vessels,
                dict(
                    source="self-generated; ranges inspired by paper Table 3",
                    seed=args.seed,
                    sample_index=k + 1,
                    eta_distribution=f"uniform continuous [0,{args.horizon}] hours rounded to 0.001",
                    length_workload_distribution="discrete uniform; inclusive endpoints",
                    safety_margin_added_m=0,
                ),
            )
            ins.check()
            write_json(Path(args.out) / f"{ins.name}.json", asdict(ins))
    print(f"Generated instances in {Path(args.out).resolve()}")


def verify_examples(args):
    summaries = []
    for L in [200, 100]:
        ins = Instance(
            f"example_{L}",
            L,
            2,
            35,
            [Vessel("A", 0, 100, 70, 1, 1), Vessel("B", 0, 100, 70, 1, 1)],
            {"source": "self-constructed analytic verification"},
        )
        ip = Path(args.out) / f"example_{L}.json"
        write_json(ip, asdict(ins))
        for printed in [False, True]:
            r = solve(ins, args.solver, args.seconds, printed)
            label = "printed_core" if printed else "corrected"
            save_run(ins, r, Path(args.out) / f"L{L}_{label}", ip)
            expected = (
                None
                if (L == 100 and printed)
                else (6.0 if printed or L == 100 else 4.0)
            )
            passed = (
                (r["status"] == "INFEASIBLE")
                if expected is None
                else (
                    r.get("proven_optimal", False)
                    and abs(r["objective"] - expected) < 1e-5
                )
            )
            summaries.append(
                dict(
                    shoreline=L,
                    model=label,
                    status=r["status"],
                    objective=r["objective"],
                    expected=expected,
                    passed=passed,
                )
            )
    write_json(Path(args.out) / "verification.json", summaries)
    for row in summaries:
        print(row)
    if not all(x["passed"] for x in summaries):
        raise RuntimeError(
            "Verification failed or solver did not prove result; inspect run.json"
        )


def summarize(args):
    groups = {}
    for path in Path(args.root).rglob("run.json"):
        r = json.loads(path.read_text(encoding="utf-8"))
        ins = json.loads((path.parent / "instance.json").read_text(encoding="utf-8"))
        # Diagnostics deliberately excluded from performance comparison.
        if r.get("model") == "printed_core":
            continue
        key = (
            ins["name"],
            r.get("algorithm", "mip"),
            r.get("solver", ""),
            r.get("budget_seconds"),
        )
        groups.setdefault(key, []).append(r)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "instance",
                "algorithm",
                "solver",
                "budget_seconds",
                "runs",
                "feasible_runs",
                "feasible_rate",
                "best",
                "mean",
                "std_sample",
                "wall_mean_seconds",
                "optimal_runs",
            ]
        )
        for key, rs in sorted(groups.items(), key=lambda x: str(x[0])):
            good = [r for r in rs if r["feasible"] and r["objective"] is not None]
            z = [r["objective"] for r in good]
            w.writerow(
                [
                    *key,
                    len(rs),
                    len(good),
                    len(good) / len(rs),
                    min(z) if z else "",
                    float(np.mean(z)) if z else "",
                    float(np.std(z, ddof=1)) if len(z) > 1 else "",
                    float(np.mean([r["wall_seconds"] for r in rs])),
                    sum(r.get("proven_optimal", False) for r in rs),
                ]
            )
    print(f"Summary: {out.resolve()}")


def main():
    parser = argparse.ArgumentParser(
        description="Integrated continuous berth and fixed specific crane scheduling"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("run")
    p.add_argument("--instance", required=True)
    p.add_argument("--out", required=True)
    p.add_argument(
        "--algorithm",
        choices=["greedy", "ga", "gga", "ga_greedy", "ga_repair", "mip"],
        default="gga",
    )
    p.add_argument("--solver", choices=["highs", "gurobi"], default="highs")
    p.add_argument(
        "--model", choices=["corrected", "printed_core"], default="corrected"
    )
    p.add_argument("--seconds", type=float)
    p.add_argument("--generations", type=int)
    p.add_argument("--population", type=int, default=40)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--pc", type=float, default=0.8)
    p.add_argument("--pm", type=float, default=0.2)
    p.add_argument("--beta", type=float, default=0.15)
    p.add_argument("--threads", type=int, default=1)
    p.add_argument("--plot", action="store_true")
    p.set_defaults(func=run_one)
    p = sub.add_parser("generate")
    p.add_argument("--counts", nargs="+", type=int, default=[5, 10, 20])
    p.add_argument("--instances", type=int, default=3)
    p.add_argument("--seed", type=int, default=2026)
    p.add_argument("--horizon", type=float, default=48)
    p.add_argument("--out", default="data/synthetic")
    p.set_defaults(func=generate)
    p = sub.add_parser("verify-examples")
    p.add_argument("--solver", choices=["highs", "gurobi"], default="highs")
    p.add_argument("--seconds", type=float, default=10)
    p.add_argument("--out", default="results/verification")
    p.set_defaults(func=verify_examples)
    p = sub.add_parser("validate")
    p.add_argument("--instance", required=True)
    p.add_argument("--run", required=True)

    def check(a):
        r = json.loads(Path(a.run).read_text(encoding="utf-8"))
        errors = validate(
            load_instance(a.instance), [Assignment(**v) for v in r["schedule"]]
        )
        print(
            json.dumps(
                {"feasible": not errors, "errors": errors}, ensure_ascii=False, indent=2
            )
        )
        if errors:
            raise ValueError("Schedule invalid")

    p.set_defaults(func=check)
    p = sub.add_parser("plot")
    p.add_argument("--instance", required=True)
    p.add_argument("--run", required=True)
    p.add_argument("--out", required=True)

    def draw(a):
        ins = load_instance(a.instance)
        r = json.loads(Path(a.run).read_text(encoding="utf-8"))
        rows = [Assignment(**v) for v in r["schedule"]]
        errors = validate(ins, rows)
        if errors:
            raise ValueError(errors)
        from .plotting import plot

        plot(ins, rows, a.out)

    p.set_defaults(func=draw)
    p = sub.add_parser("summarize")
    p.add_argument("--root", default="results")
    p.add_argument("--out", default="results/summary.csv")
    p.set_defaults(func=summarize)
    args = parser.parse_args()
    if args.command == "run" and args.seconds is None and args.generations is None:
        args.seconds = 5.0
    try:
        args.func(args)
    except (ValueError, RuntimeError, OSError) as ex:
        print(f"ERROR: {ex}", file=sys.stderr)
        raise SystemExit(2)


if __name__ == "__main__":
    main()
