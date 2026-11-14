"""All charts are redrawn: paper tables and own experiments stay separate."""

from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle


def comparison(summary, n, provenance="PROJECT RUNS"):
    f, ax = plt.subplots(figsize=(10, 5))
    g = summary[summary.n == n].copy() if not summary.empty else pd.DataFrame()
    if g.empty:
        ax.text(0.5, 0.5, f"No results for n={n}", ha="center", transform=ax.transAxes)
    else:
        names = sorted(g.instance.unique())
        xs = np.arange(1, len(names) + 1)
        for algorithm, color in [
            ("ga", "#2676ad"),
            ("gga", "#d14b42"),
            ("mip", "#75469b"),
            ("greedy", "#3f8a50"),
            ("ga_greedy", "#e2a733"),
            ("ga_repair", "#5bb8c4"),
        ]:
            a = g[g.algorithm == algorithm].set_index("instance").reindex(names)
            if a["best"].notna().any():
                if algorithm not in {"greedy", "mip"}:
                    ax.plot(
                        xs,
                        a["mean"],
                        "o--",
                        color=color,
                        label=algorithm.upper() + " mean",
                    )
                ax.plot(
                    xs,
                    a["best"],
                    "s-",
                    color=color,
                    label=algorithm.upper() + " best / incumbent",
                )
        ax.set_xticks(xs)
        ax.legend(fontsize=8, ncol=2)
    ax.set(
        xlabel="Instance index (sorted by name)",
        ylabel="Total time in port Z (hours)",
        title=f"{provenance} | n={n}",
    )
    ax.grid(alpha=0.25)
    f.tight_layout()
    return f


def reference(frame, n):
    fig, ax = plt.subplots(figsize=(10, 5))
    colors = ["#2676ad", "#e2a733", "#48a55a", "#d14b42", "#75469b"]
    for col, color in zip([c for c in frame if c != "instance"], colors):
        ax.plot(
            frame.instance,
            frame[col],
            marker="o",
            linestyle="--" if "avg" in col else "-",
            label=col,
            color=color,
        )
    ax.set(
        xlabel="Instance",
        ylabel="Objective value (hours)",
        title=f"PAPER TABLE DATA — redrawn Figure { {15:5,20:6,40:7}[n]} (n={n})",
    )
    ax.set_xticks(frame.instance)
    ax.legend()
    ax.grid(alpha=0.25)
    fig.tight_layout()
    return fig


def convergence(results, axis="seconds"):
    fig, ax = plt.subplots(figsize=(10, 5))
    for label, r in results:
        h = pd.DataFrame(r.get("history", []))
        if not h.empty:
            x = h[axis].tolist()
            y = h.objective.tolist()
            endpoint = (
                r.get("wall_seconds") if axis == "seconds" else r.get("generations")
            )
            if endpoint is not None and endpoint > x[-1]:
                x.append(endpoint)
                y.append(y[-1])
            ax.step(x, y, where="post", label=label)
    ax.set(
        xlabel="Wall time (s)" if axis == "seconds" else "Generation started",
        ylabel="Incumbent Z (hours)",
        title="Actual incumbent improvement history",
    )
    if ax.lines:
        ax.legend()
    ax.grid(alpha=0.25)
    fig.tight_layout()
    return fig


def distributions(records, n):
    fig, axs = plt.subplots(1, 2, figsize=(11, 4.5))
    g = records[records.n == n] if not records.empty else pd.DataFrame()
    if not g.empty:
        # Relative to best feasible recorded result for same data+configuration, NOT optimality gap.
        g = g.copy()
        base = g.groupby(["experiment_id", "data_sha256"]).objective.transform("min")
        g["relative_best"] = 100 * (g.objective / base - 1)
        labels = []
        vals = []
        for a, t in g[g.feasible].groupby("algorithm"):
            labels.append(a.upper())
            vals.append(t.relative_best.dropna().to_numpy())
        if vals:
            axs[0].boxplot(vals, tick_labels=labels)
        t = g.groupby("algorithm").wall_seconds.mean()
        axs[1].bar(t.index.str.upper(), t.values)
    axs[0].set(
        title="Across-instance relative quality",
        ylabel="% above best recorded feasible Z (not optimality gap)",
    )
    axs[1].set(title="Mean wall time", ylabel="Seconds (includes model construction)")
    fig.tight_layout()
    return fig


def explanatory_figures(ins, rows, out):
    """Original educational equivalents of Figures 1–4, not copied paper images."""
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.add_patch(Rectangle((2, 100), 4, 150, fc="#b4d7ef", ec="black"))
    ax.annotate("start b_i", (2, 100), (0.3, 40), arrowprops={"arrowstyle": "->"})
    ax.annotate("end u_i", (6, 100), (6.8, 40), arrowprops={"arrowstyle": "->"})
    ax.text(4, 175, "Vessel i\nlength l_i; duration d_i", ha="center")
    ax.set(
        xlim=(0, 9),
        ylim=(0, 350),
        xlabel="Time (illustrative units)",
        ylabel="Berth position (illustrative units)",
        title="Figure 1 equivalent: spatial-temporal variables",
    )
    fig.tight_layout()
    fig.savefig(out / "figure1_variables.png", dpi=160)
    plt.close(fig)
    from .heuristics import encode

    genes = encode(ins, rows)[: min(6, len(ins.vessels))]
    fig, ax = plt.subplots(figsize=(9, 4))
    im = ax.imshow(genes, vmin=0, vmax=1, cmap="Blues", aspect="auto")
    ax.set_xticks(
        range(5),
        [
            "priority key",
            "desired time",
            "desired position",
            "crane quantity",
            "first crane",
        ],
    )
    ax.set_yticks(range(len(genes)), [v.id for v in ins.vessels[: len(genes)]])
    for i in range(len(genes)):
        for j in range(5):
            ax.text(
                j,
                i,
                f"{genes[i,j]:.2f}",
                ha="center",
                va="center",
                color="white" if genes[i, j] > 0.6 else "black",
            )
    ax.set_title("Figure 2 equivalent: implementation-specific five-gene encoding")
    fig.colorbar(im, ax=ax)
    fig.tight_layout()
    fig.savefig(out / "figure2_chromosome.png", dpi=160)
    plt.close(fig)
    from .plotting import plot

    plot(ins, rows, out)
    # Figure 3 equivalent IS the actual berth_schedule.png plus crane_schedule.png.
    fig, axs = plt.subplots(1, 2, figsize=(10, 4))
    a = np.array([0.2, 0.1, 0.7, 0.8, 0.3])
    b = np.array([0.8, 0.6, 0.2, 0.4, 0.9])
    alpha = 0.4
    child = alpha * a + (1 - alpha) * b
    mut = child.copy()
    mut[2] = np.clip(mut[2] - 0.1, 0, 1)
    for values, label in [(a, "Parent A"), (b, "Parent B"), (child, "Child alpha=0.4")]:
        axs[0].plot(range(5), values, "o-", label=label)
    axs[1].plot(range(5), child, "o-", label="Before")
    axs[1].plot(range(5), mut, "s--", label="After mutation: gene 2 - 0.1")
    for ax in axs:
        ax.set(xlabel="Gene index", ylabel="Normalized value", ylim=(0, 1))
        ax.legend(fontsize=8)
        ax.grid(alpha=0.2)
    fig.suptitle("Figure 4 equivalent: illustrative arithmetic crossover and mutation")
    fig.tight_layout()
    fig.savefig(out / "figure4_operators.png", dpi=160)
    plt.close(fig)


def export_suite(root):
    from .experiments import collect, aggregate

    root = Path(root)
    records = collect(root)
    summary = aggregate(records)
    out = root / "charts"
    out.mkdir(exist_ok=True)
    for n in sorted(records.n.unique()) if not records.empty else []:
        for name, fig in [
            ("comparison", comparison(summary, int(n))),
            ("distribution", distributions(records, int(n))),
        ]:
            fig.savefig(out / f"{name}_n{n}.png", dpi=170)
            fig.savefig(out / f"{name}_n{n}.pdf")
            plt.close(fig)
    return out
