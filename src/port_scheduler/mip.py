"""One linear formulation, two explicit solver backends; corrected model in report.

printed_core isolates the logic of equations (5)-(8), not the entire paper model.
"""

import math
import time
import numpy as np
from scipy import sparse
from scipy.optimize import Bounds, LinearConstraint, milp
from .domain import Assignment, bounds, objective
from .validation import validate


class MatrixModel:
    def __init__(self):
        self.names = []
        self.lb = []
        self.ub = []
        self.integrality = []
        self.c = []
        self.rows = []
        self.low = []
        self.high = []

    def var(self, name, low=0, high=math.inf, integer=False, cost=0):
        k = len(self.names)
        self.names.append(name)
        self.lb.append(low)
        self.ub.append(high)
        self.integrality.append(int(integer))
        self.c.append(cost)
        return k

    def row(self, terms, low=-math.inf, high=math.inf):
        self.rows.append(terms)
        self.low.append(low)
        self.high.append(high)

    def matrix(self):
        ii = []
        jj = []
        vv = []
        for r, terms in enumerate(self.rows):
            for k, v in terms.items():
                if v:
                    ii.append(r)
                    jj.append(k)
                    vv.append(v)
        return sparse.coo_matrix(
            (vv, (ii, jj)), shape=(len(self.rows), len(self.names))
        ).tocsc()


def build(ins, printed_core=False):
    model = MatrixModel()
    n = len(ins.vessels)
    m = ins.cranes
    zbar, U = bounds(ins)
    H = U
    Ms = ins.shoreline
    Mq = m
    Mt = U
    b = {}
    u = {}
    d = {}
    s = {}
    p = {}
    e = {}
    y = {}
    h = {}
    for i, v in enumerate(ins.vessels):
        b[i] = model.var(f"b[{i}]", v.eta, U)
        u[i] = model.var(f"u[{i}]", v.eta, U, cost=1)
        d[i] = model.var(f"d[{i}]", 0, H)
        s[i] = model.var(f"s[{i}]", 0, ins.shoreline - v.length)
        p[i] = model.var(f"p[{i}]", 1, m, True)
        e[i] = model.var(f"e[{i}]", 1, m, True)
        for j in range(1, m + 1):
            y[i, j] = model.var(f"y[{i},{j}]", 0, 1, True)
            h[i, j] = model.var(f"h[{i},{j}]", 0, H)
        model.row({u[i]: 1, b[i]: -1, d[i]: -1}, 0, 0)
        model.row({y[i, j]: 1 for j in range(1, m + 1)}, v.q_min, v.q_max)
        model.row({h[i, j]: ins.productivity for j in range(1, m + 1)}, v.workload)
        for j in range(1, m + 1):
            model.row({h[i, j]: 1, y[i, j]: -H}, high=0)
            model.row({h[i, j]: 1, d[i]: -1}, high=0)
            model.row({d[i]: 1, h[i, j]: -1, y[i, j]: H}, high=H)
            model.row({p[i]: 1, y[i, j]: Mq}, high=j + Mq)
            model.row({e[i]: -1, y[i, j]: Mq}, high=Mq - j)
        model.row({p[i]: 1, e[i]: -1}, high=0)
        terms = {e[i]: 1, p[i]: -1}
        terms.update({y[i, j]: -1 for j in range(1, m + 1)})
        model.row(terms, -1, -1)
    model.row({u[i]: 1 for i in range(n)}, high=zbar + sum(v.eta for v in ins.vessels))
    for i in range(n):
        for k in range(i + 1, n):
            L, R, B, A = [
                model.var(f"{a}[{i},{k}]", 0, 1, True) for a in ["L", "R", "B", "A"]
            ]
            if printed_core:
                # L=z, R=1-z; B=w, A=1-w: exactly the pairwise core (5)-(8).
                model.row({L: 1, R: 1}, 1, 1)
                model.row({B: 1, A: 1}, 1, 1)
            else:
                model.row({L: 1, R: 1, B: 1, A: 1}, low=1)
            model.row({s[i]: 1, s[k]: -1, L: Ms}, high=Ms - ins.vessels[i].length)
            model.row({s[k]: 1, s[i]: -1, R: Ms}, high=Ms - ins.vessels[k].length)
            model.row({u[i]: 1, b[k]: -1, B: Mt}, high=Mt)
            model.row({u[k]: 1, b[i]: -1, A: Mt}, high=Mt)
            for j in range(1, m + 1):
                model.row({y[i, j]: 1, y[k, j]: 1, B: -1, A: -1}, high=1)
            model.row({e[i]: 1, p[k]: -1, L: Mq, B: -Mq, A: -Mq}, high=Mq - 1)
            model.row({e[k]: 1, p[i]: -1, R: Mq, B: -Mq, A: -Mq}, high=Mq - 1)
    return model, (b, u, s, y), U


def finite_or_none(x):
    return float(x) if x is not None and math.isfinite(float(x)) else None


def solve(ins, solver="highs", seconds=10, printed_core=False, seed=0, threads=1):
    start = time.perf_counter()
    model, idx, U = build(ins, printed_core)
    mat = model.matrix()
    build_seconds = time.perf_counter() - start
    remaining = seconds - build_seconds
    if remaining <= 0:
        return dict(
            status="BUDGET_EXHAUSTED_DURING_BUILD",
            schedule=[],
            objective=None,
            feasible=False,
            wall_seconds=time.perf_counter() - start,
            build_seconds=build_seconds,
            solver=solver,
            model="printed_core" if printed_core else "corrected",
        )
    x = None
    lb = None
    gap = None
    opt_start = time.perf_counter()
    if solver == "highs":
        res = milp(
            np.asarray(model.c),
            integrality=np.asarray(model.integrality),
            bounds=Bounds(model.lb, model.ub),
            constraints=LinearConstraint(mat, model.low, model.high),
            options={"time_limit": remaining, "mip_rel_gap": 0.0, "disp": False},
        )
        status = {
            0: "OPTIMAL",
            1: "LIMIT",
            2: "INFEASIBLE",
            3: "UNBOUNDED",
            4: "SOLVER_ERROR",
        }.get(res.status, str(res.status))
        message = str(res.message)
        x = res.x
        lb = finite_or_none(getattr(res, "mip_dual_bound", None))
        gap = finite_or_none(getattr(res, "mip_gap", None))
    elif solver == "gurobi":
        try:
            import gurobipy as gp
        except ImportError as ex:
            raise RuntimeError(
                "Gurobi is not installed. Install gurobipy and activate a license, or select --solver highs."
            ) from ex
        try:
            gm = gp.Model("integrated_berth_crane")
            gm.Params.OutputFlag = 0
            gm.Params.TimeLimit = max(0.001, seconds - (time.perf_counter() - start))
            gm.Params.MIPGap = 0
            gm.Params.Seed = seed
            gm.Params.Threads = threads
            vs = [
                gm.addVar(
                    lb=a,
                    ub=b,
                    vtype=gp.GRB.INTEGER if integer else gp.GRB.CONTINUOUS,
                    name=name,
                )
                for name, a, b, integer in zip(
                    model.names, model.lb, model.ub, model.integrality
                )
            ]
            gm.setObjective(
                gp.quicksum(c * v for c, v in zip(model.c, vs) if c), gp.GRB.MINIMIZE
            )
            for terms, lo, hi in zip(model.rows, model.low, model.high):
                expr = gp.quicksum(c * vs[j] for j, c in terms.items())
                if lo == hi:
                    gm.addConstr(expr == lo)
                else:
                    if math.isfinite(lo):
                        gm.addConstr(expr >= lo)
                    if math.isfinite(hi):
                        gm.addConstr(expr <= hi)
            gm.Params.TimeLimit = max(0.001, seconds - (time.perf_counter() - start))
            gm.optimize()
            status = {
                2: "OPTIMAL",
                3: "INFEASIBLE",
                9: "LIMIT",
                4: "INF_OR_UNBD",
                5: "UNBOUNDED",
            }.get(gm.Status, f"STATUS_{gm.Status}")
            message = f"Gurobi status {gm.Status}"
            if gm.SolCount:
                x = np.array([v.X for v in vs])
                gap = finite_or_none(gm.MIPGap)
            lb = finite_or_none(gm.ObjBound)
            gm.dispose()
        except gp.GurobiError as ex:
            raise RuntimeError(f"Gurobi error (no silent fallback): {ex}") from ex
    else:
        raise ValueError("Unknown solver")
    opt_seconds = time.perf_counter() - opt_start
    rows = []
    errors = []
    violation = None
    if x is not None:
        values = mat @ x
        violation = float(
            max(
                np.max(np.maximum(np.asarray(model.low) - values, 0)),
                np.max(np.maximum(values - np.asarray(model.high), 0)),
                np.max(np.maximum(np.asarray(model.lb) - x, 0)),
                np.max(np.maximum(x - np.asarray(model.ub), 0)),
                np.max(
                    np.abs(
                        x[np.asarray(model.integrality, dtype=bool)]
                        - np.rint(x[np.asarray(model.integrality, dtype=bool)])
                    )
                ),
            )
        )
        b, u, s, y = idx
        rows = [
            Assignment(
                v.id,
                float(x[b[i]]),
                float(x[u[i]]),
                float(x[s[i]]),
                [j for j in range(1, ins.cranes + 1) if x[y[i, j]] > 0.5],
            )
            for i, v in enumerate(ins.vessels)
        ]
        errors = validate(ins, rows)
        if violation > 1e-5:
            errors.append(f"MIP residual/integrality violation {violation}")
    feasible = bool(rows) and not errors
    offset = sum(v.eta for v in ins.vessels)
    result = dict(
        status=status,
        message=message,
        solver=solver,
        model="printed_core" if printed_core else "corrected",
        schedule=rows,
        objective=objective(ins, rows) if feasible else None,
        feasible=feasible,
        validation_errors=errors,
        proven_optimal=bool(status == "OPTIMAL" and feasible),
        lower_bound=(lb - offset) if lb is not None else None,
        solver_relative_gap_on_sum_completion=gap,
        build_seconds=build_seconds,
        optimize_seconds=opt_seconds,
        wall_seconds=time.perf_counter() - start,
        budget_seconds=seconds,
        variables=len(model.names),
        constraints=len(model.rows),
        max_model_violation=violation,
    )
    if feasible and result["lower_bound"] is not None:
        result["flow_relative_gap"] = max(
            0.0,
            (result["objective"] - result["lower_bound"])
            / max(abs(result["objective"]), 1e-12),
        )
    else:
        result["flow_relative_gap"] = None
    return result
