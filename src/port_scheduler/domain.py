"""Input validation, units, sequential reference, and serialization."""

from __future__ import annotations
import json
import math
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass(frozen=True)
class Vessel:
    id: str
    eta: float
    length: float
    workload: float
    q_min: int
    q_max: int


@dataclass
class Instance:
    name: str
    shoreline: float
    cranes: int
    productivity: float
    vessels: list[Vessel]
    metadata: dict

    def check(self):
        def finite(x):
            return (
                isinstance(x, (float, int))
                and not isinstance(x, bool)
                and math.isfinite(x)
            )

        if not finite(self.shoreline) or self.shoreline <= 0:
            raise ValueError("shoreline must be finite and positive")
        if type(self.cranes) is not int or self.cranes < 1:
            raise ValueError("cranes must be a positive integer")
        if not finite(self.productivity) or self.productivity <= 0:
            raise ValueError("productivity must be finite and positive")
        if not self.vessels or len({v.id for v in self.vessels}) != len(self.vessels):
            raise ValueError("vessel list must be nonempty; IDs must be unique")
        for v in self.vessels:
            if not isinstance(v.id, str) or not v.id:
                raise ValueError("vessel ID must be a nonempty string")
            if not finite(v.eta) or v.eta < 0:
                raise ValueError(f"{v.id}: eta must be finite and nonnegative")
            if not finite(v.length) or not 0 < v.length <= self.shoreline:
                raise ValueError(f"{v.id}: length must fit the shoreline")
            if not finite(v.workload) or v.workload <= 0:
                raise ValueError(f"{v.id}: workload must be positive")
            if (
                type(v.q_min) is not int
                or type(v.q_max) is not int
                or not 1 <= v.q_min <= v.q_max <= self.cranes
            ):
                raise ValueError(f"{v.id}: require 1 <= q_min <= q_max <= cranes")
        return self


@dataclass
class Assignment:
    vessel_id: str
    start: float
    end: float
    position: float
    cranes: list[int]


def load_instance(path):
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    return Instance(
        d["name"],
        d["shoreline"],
        d["cranes"],
        d["productivity"],
        [Vessel(**v) for v in d["vessels"]],
        d.get("metadata", {}),
    ).check()


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8",
    )


def duration(ins, v, q):
    return v.workload / (ins.productivity * q)


def sequential(ins, order=None, rng=None):
    """Always feasible for this model. No crane movement/setup time is modeled."""
    order = (
        order
        if order is not None
        else sorted(range(len(ins.vessels)), key=lambda i: (ins.vessels[i].eta, i))
    )
    t = 0.0
    rows = []
    for i in order:
        v = ins.vessels[i]
        q = v.q_min if rng is None else int(rng.integers(v.q_min, v.q_max + 1))
        p = 1 if rng is None else int(rng.integers(1, ins.cranes - q + 2))
        s = 0.0 if rng is None else float(rng.uniform(0, ins.shoreline - v.length))
        t = max(t, v.eta)
        end = t + duration(ins, v, q)
        rows.append(Assignment(v.id, t, end, s, list(range(p, p + q))))
        t = end
    return rows


def objective(ins, rows):
    eta = {v.id: v.eta for v in ins.vessels}
    return sum(r.end - eta[r.vessel_id] for r in rows)


def bounds(ins):
    zbar = objective(ins, sequential(ins))
    # Objective cap Z<=zbar preserves an optimum. All flow times are nonnegative.
    upper_time = max(v.eta for v in ins.vessels) + zbar
    return zbar, upper_time


def serialize_rows(rows):
    return [asdict(r) for r in rows]
