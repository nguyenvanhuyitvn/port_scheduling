"""Explicit normalized genes and feasibility-oriented decoder.

Independent implementation choices (see docs/METHOD.md), not exact paper code.
"""

import time
import numpy as np
from .domain import Assignment, bounds, duration, objective, sequential
from .validation import validate


class BudgetExpired(Exception):
    pass


def encode(ins, rows, priorities=None):
    _, U = bounds(ins)
    lookup = {r.vessel_id: r for r in rows}
    g = np.zeros((len(ins.vessels), 5))
    order = sorted(
        range(len(ins.vessels)), key=lambda i: (lookup[ins.vessels[i].id].start, i)
    )
    ranks = {i: k / max(1, len(order) - 1) for k, i in enumerate(order)}
    for i, v in enumerate(ins.vessels):
        r = lookup[v.id]
        q = len(r.cranes)
        g[i] = [
            ranks[i],
            (r.start - v.eta) / max(U - v.eta, 1e-12),
            r.position / max(ins.shoreline - v.length, 1e-12),
            (q - v.q_min) / max(v.q_max - v.q_min, 1),
            (min(r.cranes) - 1) / max(ins.cranes - q, 1),
        ]
    if priorities is not None:
        g[:, 0] = priorities
    return np.clip(g, 0, 1)


def gene_values(ins, v, g, U):
    q = int(np.floor(v.q_min + g[3] * (v.q_max - v.q_min) + 0.5))
    p = 1 + int(np.floor(g[4] * (ins.cranes - q) + 0.5))
    return v.eta + g[1] * (U - v.eta), g[2] * (ins.shoreline - v.length), q, p


def raw_decode(ins, g):
    _, U = bounds(ins)
    rows = []
    for v, gi in zip(ins.vessels, g):
        t, s, q, p = gene_values(ins, v, gi, U)
        rows.append(
            Assignment(
                v.id,
                float(t),
                float(t + duration(ins, v, q)),
                float(s),
                list(range(p, p + q)),
            )
        )
    return rows


def repair_decode(ins, g, deadline=float("inf")):
    """Fixed rounded crane quantity; earliest feasible event time; soft s/p preferences.

    For a fixed block, the feasible s intervals change only at vessel edges.
    Candidate positions include these edges and both shoreline bounds.
    """
    _, U = bounds(ins)
    lookup = {v.id: v for v in ins.vessels}
    rows = []
    for i in np.argsort(g[:, 0], kind="stable"):
        if time.perf_counter() >= deadline:
            raise BudgetExpired
        v = ins.vessels[int(i)]
        _, desired_s, q, desired_p = gene_values(ins, v, g[i], U)
        dt = duration(ins, v, q)
        # A later start inside a fixed overlap pattern cannot create feasibility.
        # New free resource becomes available at an existing completion event.
        events = sorted({v.eta} | {r.end for r in rows if r.end >= v.eta})
        found = None
        for t in events:
            if time.perf_counter() >= deadline:
                raise BudgetExpired
            active = [r for r in rows if min(t + dt, r.end) > max(t, r.start) + 1e-8]
            positions = {0.0, ins.shoreline - v.length, float(desired_s)}
            for r in active:
                positions.add(r.position - v.length)
                positions.add(r.position + lookup[r.vessel_id].length)
            positions = sorted(
                (s for s in positions if -1e-8 <= s <= ins.shoreline - v.length + 1e-8),
                key=lambda s: (abs(s - desired_s), s),
            )
            blocks = sorted(
                range(1, ins.cranes - q + 2), key=lambda p: (abs(p - desired_p), p)
            )
            for s in positions:
                s = max(0.0, min(float(s), ins.shoreline - v.length))
                for p in blocks:
                    ok = True
                    for r in active:
                        vl = lookup[r.vessel_id].length
                        if s + v.length <= r.position + 1e-8:
                            if p + q - 1 >= min(r.cranes):
                                ok = False
                                break
                        elif r.position + vl <= s + 1e-8:
                            if max(r.cranes) >= p:
                                ok = False
                                break
                        else:
                            ok = False
                            break
                    if ok:
                        found = Assignment(
                            v.id, float(t), float(t + dt), s, list(range(p, p + q))
                        )
                        break
                if found:
                    break
            if found:
                break
        if not found:
            raise RuntimeError(
                "Decoder failed despite validated unbounded-horizon input"
            )
        rows.append(found)
    return rows


# Ablation variants: (initialization, decoder).
#   ga        : randomized feasible sequential schedules, raw decode (no repair)
#   gga       : greedy ETA individual + greedy-decoded random keys, repair decode
#   ga_greedy : greedy initialization as in GGA, raw decode (no repair)
#   ga_repair : GA initialization, repair decode
# Selection, crossover, mutation, elitism and budgets are identical for all four.
VARIANTS = {
    "ga": ("sequential", "raw"),
    "gga": ("greedy", "repair"),
    "ga_greedy": ("greedy", "raw"),
    "ga_repair": ("sequential", "repair"),
}
ALGORITHMS = ("greedy",) + tuple(VARIANTS)


def run(
    ins,
    algorithm="gga",
    seconds=5,
    generations=None,
    population=40,
    seed=0,
    pc=0.8,
    pm=0.2,
    beta=0.15,
):
    if algorithm not in ALGORITHMS:
        raise ValueError("Unknown algorithm")
    init_mode, decode_mode = VARIANTS.get(algorithm, ("greedy", "repair"))
    if seconds is None and generations is None:
        raise ValueError("Specify seconds or generations")
    if seconds is not None and seconds <= 0:
        raise ValueError("seconds must be positive")
    if generations is not None and generations < 1:
        raise ValueError("generations must be positive")
    if population < 4:
        raise ValueError("population must be >=4")
    if not (0 <= pc <= 1 and 0 <= pm <= 1 and beta >= 0):
        raise ValueError("Invalid genetic parameters")
    start = time.perf_counter()
    deadline = start + seconds if seconds is not None else float("inf")
    rng = np.random.default_rng(seed)
    zbar, _ = bounds(ins)
    best = sequential(ins)
    best_z = objective(ins, best)
    best_g = encode(ins, best)
    errors = validate(ins, best)
    if errors:
        raise RuntimeError(errors)
    history = [
        dict(seconds=time.perf_counter() - start, generation=0, objective=best_z)
    ]
    evaluated = 0
    feasible_evaluations = 0

    def evaluate(g):
        nonlocal best, best_z, best_g, evaluated, feasible_evaluations
        if time.perf_counter() >= deadline:
            raise BudgetExpired
        rows = (
            repair_decode(ins, g, deadline)
            if decode_mode == "repair"
            else raw_decode(ins, g)
        )
        bad = validate(ins, rows)
        evaluated += 1
        if bad:
            return g, 1e-12 / (1 + len(bad)), None
        feasible_evaluations += 1
        z = objective(ins, rows)
        # Lamarckian repair writes physical genes back; order keys are retained.
        repaired = encode(ins, rows, g[:, 0]) if decode_mode == "repair" else g.copy()
        if z < best_z - 1e-8:
            best_z = z
            best = rows
            best_g = repaired.copy()
            history.append(
                dict(seconds=time.perf_counter() - start, generation=gen, objective=z)
            )
        return repaired, 1 / (z + 1e-9), z

    gen = 0
    pop = [(best_g.copy(), 1 / (best_z + 1e-9), best_z)]
    try:
        if algorithm == "greedy":
            g = np.zeros_like(best_g)
            order = sorted(
                range(len(ins.vessels)), key=lambda i: (ins.vessels[i].eta, i)
            )
            for rank, i in enumerate(order):
                g[i, 0] = rank / max(1, len(order) - 1)
            g[:, 3] = 1.0
            evaluate(g)
        else:

            def greedy_seed(g):
                # With the raw decoder, greedy construction happens once here and the
                # resulting physical schedule is written into the genes; with the repair
                # decoder the same construction happens inside evaluate().
                if decode_mode == "repair":
                    return g
                return encode(ins, repair_decode(ins, g, deadline), g[:, 0])

            if init_mode == "greedy":
                # Include the deterministic greedy baseline; preserve it through elitism.
                g = np.zeros_like(best_g)
                order = sorted(
                    range(len(ins.vessels)), key=lambda i: (ins.vessels[i].eta, i)
                )
                for rank, i in enumerate(order):
                    g[i, 0] = rank / max(1, len(order) - 1)
                g[:, 3] = 1.0
                pop.append(evaluate(greedy_seed(g)))
            while len(pop) < population:
                if init_mode == "greedy":
                    g = rng.random(best_g.shape)
                    g[:, 1] = 0
                    g = greedy_seed(g)
                else:
                    order = list(rng.permutation(len(ins.vessels)))
                    g = encode(ins, sequential(ins, order, rng))
                pop.append(evaluate(g))
            while (
                generations is None or gen < generations
            ) and time.perf_counter() < deadline:
                gen += 1
                progress = (
                    (time.perf_counter() - start) / seconds
                    if seconds is not None
                    else (gen - 1) / max(1, generations)
                )
                step = beta * max(0, 1 - progress)
                pop.sort(key=lambda x: x[1], reverse=True)
                new = [(x[0].copy(), x[1], x[2]) for x in pop[:2]]
                weights = np.array([x[1] for x in pop])
                weights /= weights.sum()
                while len(new) < population:
                    a, b = rng.choice(len(pop), 2, replace=True, p=weights)
                    x, y = pop[a][0].copy(), pop[b][0].copy()
                    if rng.random() < pc:
                        alpha = float(rng.random())
                        x, y = alpha * x + (1 - alpha) * y, (1 - alpha) * x + alpha * y
                    for child in (x, y):
                        mask = rng.random(child.shape) < pm
                        direction = np.where(rng.random(child.shape) < 0.5, -1, 1)
                        child = np.clip(child + mask * direction * step, 0, 1)
                        new.append(evaluate(child))
                        if len(new) >= population:
                            break
                pop = new
    except BudgetExpired:
        pass
    wall = time.perf_counter() - start
    final_errors = validate(ins, best)
    return dict(
        algorithm=algorithm,
        status="FEASIBLE",
        schedule=best,
        objective=best_z,
        feasible=not final_errors,
        validation_errors=final_errors,
        wall_seconds=wall,
        budget_seconds=seconds,
        generations=gen,
        evaluations=evaluated,
        feasible_evaluations=feasible_evaluations,
        seed=seed,
        proven_optimal=False,
        history=history,
        parameters=dict(
            population=population,
            pc=pc,
            pm=pm,
            beta=beta,
            mutation_progress="elapsed_time" if seconds is not None else "generation",
            elitism=2,
            initialization=init_mode,
            decoder=decode_mode,
            ga_initialization="randomized_feasible_sequential",
            gga_decoder="event_time_fixed_q_soft_position_block_preferences",
        ),
    )
