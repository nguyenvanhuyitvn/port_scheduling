"""Independent physical validator: does not call decoder or the MIP model."""

import math
from .domain import Assignment


def validate(ins, rows, tol=1e-6):
    errors = []
    ids = [r.vessel_id for r in rows]
    expected = {v.id for v in ins.vessels}
    if len(ids) != len(set(ids)) or set(ids) != expected:
        return ["Missing, duplicate, or unknown vessel IDs"]
    vessels = {v.id: v for v in ins.vessels}
    for r in rows:
        v = vessels[r.vessel_id]
        if not all(math.isfinite(x) for x in [r.start, r.end, r.position]):
            errors.append(f"{v.id}: non-finite field")
            continue
        if r.start < v.eta - tol or r.end <= r.start:
            errors.append(f"{v.id}: arrival or duration violation")
        if r.position < -tol or r.position + v.length > ins.shoreline + tol:
            errors.append(f"{v.id}: shoreline boundary")
        cs = r.cranes
        valid_cs = len(cs) == len(set(cs)) and all(
            type(c) is int and 1 <= c <= ins.cranes for c in cs
        )
        if not valid_cs:
            errors.append(f"{v.id}: invalid crane IDs")
        if not v.q_min <= len(cs) <= v.q_max:
            errors.append(f"{v.id}: crane count")
        if cs and sorted(cs) != list(range(min(cs), max(cs) + 1)):
            errors.append(f"{v.id}: noncontiguous cranes")
        if (r.end - r.start) * ins.productivity * len(cs) < v.workload - tol * max(
            1.0, v.workload
        ):
            errors.append(f"{v.id}: insufficient handling capacity")
    # No ordering variables are used here; check time intervals directly.
    for i, a in enumerate(rows):
        for b in rows[i + 1 :]:
            if min(a.end, b.end) <= max(a.start, b.start) + tol:
                continue
            va, vb = vessels[a.vessel_id], vessels[b.vessel_id]
            a_left = a.position + va.length <= b.position + tol
            b_left = b.position + vb.length <= a.position + tol
            if not (a_left or b_left):
                errors.append(f"{a.vessel_id}/{b.vessel_id}: berth-time overlap")
            if set(a.cranes) & set(b.cranes):
                errors.append(f"{a.vessel_id}/{b.vessel_id}: shared crane")
            if a.cranes and b.cranes:
                if a_left and max(a.cranes) >= min(b.cranes):
                    errors.append(f"{a.vessel_id}/{b.vessel_id}: crossing crane order")
                if b_left and max(b.cranes) >= min(a.cranes):
                    errors.append(f"{a.vessel_id}/{b.vessel_id}: crossing crane order")
    return errors
