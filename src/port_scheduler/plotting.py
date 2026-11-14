"""Visualize the actual saved schedule, not a paper figure."""

from pathlib import Path
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle


def plot(ins, rows, out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    vessels = {v.id: v for v in ins.vessels}
    colors = plt.get_cmap("tab20")
    color = {v.id: colors(i % 20) for i, v in enumerate(ins.vessels)}
    fig, ax = plt.subplots(figsize=(11, 7))
    for r in rows:
        v = vessels[r.vessel_id]
        ax.add_patch(
            Rectangle(
                (r.start, r.position),
                r.end - r.start,
                v.length,
                facecolor=color[v.id],
                edgecolor="black",
                alpha=0.8,
            )
        )
        ax.text(
            (r.start + r.end) / 2,
            r.position + v.length / 2,
            v.id,
            ha="center",
            va="center",
            fontsize=8,
        )
    ax.set(
        xlim=(min(v.eta for v in ins.vessels), max(r.end for r in rows) + 1),
        ylim=(0, ins.shoreline),
        xlabel="Time (hours)",
        ylabel="Shoreline position (m)",
        title=f"{ins.name}: berth-time schedule",
    )
    fig.tight_layout()
    fig.savefig(out / "berth_schedule.png", dpi=160)
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(11, 5))
    for r in rows:
        for c in r.cranes:
            ax.broken_barh(
                [(r.start, r.end - r.start)],
                (c - 0.35, 0.7),
                facecolors=[color[r.vessel_id]],
                edgecolors="black",
            )
            ax.text(
                (r.start + r.end) / 2,
                c,
                r.vessel_id,
                ha="center",
                va="center",
                fontsize=7,
            )
    ax.set(
        yticks=list(range(1, ins.cranes + 1)),
        ylim=(0.3, ins.cranes + 0.7),
        xlabel="Time (hours)",
        ylabel="Crane ID",
        title=f"{ins.name}: crane usage",
    )
    fig.tight_layout()
    fig.savefig(out / "crane_schedule.png", dpi=160)
    plt.close(fig)
