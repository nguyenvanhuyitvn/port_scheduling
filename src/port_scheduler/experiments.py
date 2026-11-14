"""Resumable, configuration-separated experiments; no invented solver results."""

from dataclasses import dataclass, asdict
from pathlib import Path
import hashlib
import json
import csv
import io
import zipfile
import traceback
import numpy as np
import pandas as pd
from .domain import load_instance, Instance, Vessel, write_json
from .heuristics import run
from .mip import solve
from .cli import save_run, environment


@dataclass(frozen=True)
class Config:
    mode: str = "time"
    seconds: float = 5.0
    generations: int = 100
    population: int = 40
    pc: float = 0.8
    pm: float = 0.2
    beta: float = 0.15
    solver_seconds: float = 60.0
    solver: str = "highs"
    threads: int = 1

    def check(self):
        if self.mode not in {"time", "generations"}:
            raise ValueError("Unknown budget mode")
        if self.seconds <= 0 or self.solver_seconds <= 0 or self.generations < 1:
            raise ValueError("Budget must be positive")
        if (
            self.population < 4
            or not 0 <= self.pc <= 1
            or not 0 <= self.pm <= 1
            or self.beta < 0
        ):
            raise ValueError("Invalid GA parameters")
        if self.solver not in {"highs", "gurobi"}:
            raise ValueError("Unknown solver")
        return self


def source_hash():
    return hashlib.sha256(
        b"".join(p.read_bytes() for p in sorted(Path(__file__).parent.glob("*.py")))
    ).hexdigest()


def experiment_id(config):
    # Separate all configurations AND code revisions, never mix timed and generation runs.
    payload = {"config": asdict(config), "source": source_hash()}
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:16]


def execute(instance_path, algorithm, seed, config, out):
    config.check()
    ins = load_instance(instance_path)
    if algorithm == "mip":
        result = solve(
            ins, config.solver, config.solver_seconds, False, int(seed), config.threads
        )
    else:
        if algorithm not in {"ga", "gga", "ga_greedy", "ga_repair", "greedy"}:
            raise ValueError("Unknown algorithm")
        # Greedy is a deterministic construction: do not cut it short with GA budget.
        seconds = (
            None
            if algorithm == "greedy" or config.mode == "generations"
            else config.seconds
        )
        generations = (
            1
            if algorithm == "greedy"
            else (config.generations if config.mode == "generations" else None)
        )
        result = run(
            ins,
            algorithm,
            seconds,
            generations,
            config.population,
            int(seed),
            config.pc,
            config.pm,
            config.beta,
        )
    result.update(
        algorithm=algorithm,
        seed=int(seed),
        experiment_config=asdict(config),
        experiment_id=experiment_id(config),
        data_sha256=hashlib.sha256(Path(instance_path).read_bytes()).hexdigest(),
    )
    save_run(ins, result, out, instance_path)
    return ins, result


def run_matrix(files, algorithms, seeds, config, root, progress=None):
    root = Path(root) / experiment_id(config)
    root.mkdir(parents=True, exist_ok=True)
    write_json(
        root / "experiment.json",
        {
            "config": asdict(config),
            "environment": environment(),
            "source_sha256": source_hash(),
            "provenance": "independent implementation; self-generated synthetic instances",
        },
    )
    jobs = [
        (Path(f), a, s)
        for f in files
        for a in algorithms
        for s in (seeds[:1] if a in {"greedy", "mip"} else seeds)
    ]
    for index, (file, algorithm, seed) in enumerate(jobs):
        data_hash = hashlib.sha256(file.read_bytes()).hexdigest()
        target = root / (file.stem + "_" + data_hash[:8]) / f"{algorithm}_seed{seed}"
        rp = target / "run.json"
        state = "ran"
        if rp.exists():
            r = json.loads(rp.read_text())
            if r.get("data_sha256") == data_hash and r.get(
                "experiment_id"
            ) == experiment_id(config):
                state = "resumed"
        if state != "resumed":
            try:
                execute(file, algorithm, seed, config, target)
                if (target / "error.json").exists():
                    (target / "error.json").unlink()
            except Exception as exc:
                target.mkdir(parents=True, exist_ok=True)
                write_json(
                    target / "error.json",
                    {
                        "algorithm": algorithm,
                        "seed": seed,
                        "error": str(exc),
                        "traceback": traceback.format_exc(),
                    },
                )
                state = "error"
        if progress:
            progress(
                index + 1,
                len(jobs),
                f"{file.stem} / {algorithm} / seed={seed} / {state}",
            )
    records = collect(root)
    summary = aggregate(records)
    records.to_csv(root / "runs.csv", index=False, encoding="utf-8-sig")
    summary.to_csv(root / "summary.csv", index=False, encoding="utf-8-sig")
    errors = [
        {"path": str(p.relative_to(root)), **json.loads(p.read_text())}
        for p in root.rglob("error.json")
    ]
    write_json(root / "errors.json", errors)
    return root, records, summary, errors


def collect(root):
    rows = []
    for p in sorted(Path(root).rglob("run.json")):
        r = json.loads(p.read_text())
        ins = json.loads((p.parent / "instance.json").read_text())
        if r.get("model") == "printed_core":
            continue
        rows.append(
            dict(
                instance=ins["name"],
                n=len(ins["vessels"]),
                algorithm=r["algorithm"],
                seed=r["seed"],
                data_sha256=r.get("data_sha256", "legacy"),
                experiment_id=r.get("experiment_id", "legacy"),
                feasible=bool(r.get("feasible")),
                objective=r.get("objective") if r.get("feasible") else None,
                wall_seconds=r.get("wall_seconds"),
                generations=r.get("generations"),
                evaluations=r.get("evaluations"),
                status=r.get("status"),
                proven_optimal=r.get("proven_optimal", False),
                lower_bound=r.get("lower_bound"),
                flow_relative_gap=r.get("flow_relative_gap"),
                run_path=str(p),
            )
        )
    return pd.DataFrame(rows)


def aggregate(records):
    rows = []
    if records.empty:
        return pd.DataFrame()
    for keys, g in records.groupby(
        ["experiment_id", "data_sha256", "instance", "n", "algorithm"], dropna=False
    ):
        ok = g[g.feasible]
        z = ok.objective.dropna().astype(float)
        rows.append(
            dict(
                zip(
                    ["experiment_id", "data_sha256", "instance", "n", "algorithm"], keys
                )
            )
            | dict(
                runs=len(g),
                feasible_runs=len(ok),
                feasible_rate=len(ok) / len(g),
                best=z.min() if len(z) else None,
                mean=z.mean() if len(z) else None,
                std=z.std(ddof=1) if len(z) > 1 else None,
                worst=z.max() if len(z) else None,
                mean_wall_seconds=g.wall_seconds.mean(),
                optimal_runs=int(g.proven_optimal.sum()),
            )
        )
    return pd.DataFrame(rows)


def zip_directory(root):
    root = Path(root)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(root.rglob("*")):
            if p.is_file() and "__pycache__" not in p.parts:
                z.write(p, p.relative_to(root))
    return buf.getvalue()


def from_frame(frame, name, shoreline, cranes, productivity, metadata=None):
    required = ["id", "eta", "length", "workload", "q_min", "q_max"]
    if not set(required) <= set(frame.columns):
        raise ValueError("Required columns: " + ", ".join(required))
    vessels = []
    for record in frame[required].to_dict("records"):
        for key in ["q_min", "q_max"]:
            value = float(record[key])
            if not np.isfinite(value) or not value.is_integer():
                raise ValueError(f"{key} must be integer")
            record[key] = int(value)
        if pd.isna(record["id"]):
            raise ValueError("ID must not be empty")
        record["id"] = str(record["id"]).strip()
        for key in ["eta", "length", "workload"]:
            record[key] = float(record[key])
        vessels.append(Vessel(**record))
    return Instance(
        str(name),
        float(shoreline),
        int(cranes),
        float(productivity),
        vessels,
        metadata or {},
    ).check()
