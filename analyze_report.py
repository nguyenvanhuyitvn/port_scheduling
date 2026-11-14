"""Build report tables, Wilcoxon tests and figures from run_report_plan.py output.

  .venv/bin/python analyze_report.py --root results/report

Writes to <root>/report_tables/:
  per_instance_n*.csv   paper-style table: mean/min/std/time per algorithm, MIP Z/LB/gap
  summary.csv           one row per (group, algorithm)
  wilcoxon.csv          paired tests on per-instance mean objective
  ablation.csv          GA vs GA+greedy vs GA+repair vs GGA
  boxplot_n*.png        % above best known Z per instance
  convergence_n*.png    incumbent history (seed 0, first instance)
  REPORT.md             all of the above as Markdown tables
Only runs whose schedule passed the independent validator are counted.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))
import numpy as np
import pandas as pd
from scipy.stats import wilcoxon
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from port_scheduler.experiments import collect

ORDER = ["greedy", "ga", "ga_greedy", "ga_repair", "gga", "mip"]
LABEL = {
    "greedy": "Greedy",
    "ga": "GA",
    "ga_greedy": "GA+Greedy init",
    "ga_repair": "GA+Repair",
    "gga": "GGA",
    "mip": "MIP",
}
PAIRS = [
    ("gga", "ga"),
    ("gga", "greedy"),
    ("gga", "mip"),
    ("ga_greedy", "ga"),
    ("ga_repair", "ga"),
    ("gga", "ga_greedy"),
    ("gga", "ga_repair"),
]


def load(root):
    # Only experiment folders (with experiment.json); verification/ holds model diagnostics.
    cfg = {}
    frames = []
    for p in sorted(Path(root).rglob("experiment.json")):
        cfg[p.parent.name] = json.loads(p.read_text())["config"]
        frames.append(collect(p.parent))
    frames = [f.dropna(axis=1, how="all") for f in frames if not f.empty]
    if not frames:
        raise SystemExit(f"No experiment runs under {root}")
    r = pd.concat(frames, ignore_index=True)
    for col in ["lower_bound", "flow_relative_gap"]:
        if col not in r:
            r[col] = np.nan
    r["budget_s"] = r.experiment_id.map(lambda e: cfg.get(e, {}).get("seconds"))
    r["mip_budget_s"] = r.experiment_id.map(
        lambda e: cfg.get(e, {}).get("solver_seconds")
    )
    r["group"] = np.where(
        r.instance.str.contains("liaoning"),
        "liaoning_12",
        "n" + r.n.astype(str).str.zfill(2),
    )
    r["objective"] = pd.to_numeric(r.objective, errors="coerce")
    dup = r.groupby(["group", "algorithm"]).experiment_id.nunique()
    if (dup > 1).any():
        print(
            "WARNING: several budgets for the same group/algorithm, keeping the most recent folder:"
        )
        print(dup[dup > 1].to_string())
        r = r.assign(_mt=r.run_path.map(lambda x: Path(x).stat().st_mtime))
        newest = (
            r.groupby(["group", "algorithm", "experiment_id"])._mt.max().reset_index()
        )
        newest = newest.loc[
            newest.groupby(["group", "algorithm"])._mt.idxmax(),
            ["group", "algorithm", "experiment_id"],
        ]
        r = r.merge(newest, on=["group", "algorithm", "experiment_id"]).drop(
            columns="_mt"
        )
    return r


def per_instance(g):
    rows = []
    for inst, t in g.groupby("instance"):
        row = {"instance": inst}
        for alg in ORDER:
            a = t[t.algorithm == alg]
            if a.empty:
                continue
            z = a[a.feasible].objective.dropna()
            if alg == "mip":
                m = a.iloc[0]
                row.update(
                    {
                        "MIP Z": m.objective if m.feasible else None,
                        "MIP LB": m.lower_bound,
                        "MIP gap %": (
                            None
                            if pd.isna(m.flow_relative_gap)
                            else 100 * m.flow_relative_gap
                        ),
                        "MIP status": m.status,
                        "MIP time": m.wall_seconds,
                    }
                )
                continue
            p = LABEL[alg]
            row[f"{p} mean"] = z.mean() if len(z) else None
            if alg != "greedy":
                row[f"{p} min"] = z.min() if len(z) else None
                row[f"{p} std"] = z.std(ddof=1) if len(z) > 1 else None
            row[f"{p} time"] = a.wall_seconds.mean()
            if len(z) < len(a):
                row[f"{p} feasible"] = f"{len(z)}/{len(a)}"
        rows.append(row)
    return pd.DataFrame(rows)


def best_known(g):
    feas = g[g.feasible].dropna(subset=["objective"])
    return feas.groupby("instance").objective.min()


def summary(r):
    rows = []
    for (grp, alg), t in r.groupby(["group", "algorithm"]):
        ok = t[t.feasible].dropna(subset=["objective"])
        bk = best_known(r[r.group == grp])
        inst_mean = ok.groupby("instance").objective.mean()
        rel = 100 * (inst_mean / bk.reindex(inst_mean.index) - 1)
        rows.append(
            dict(
                group=grp,
                algorithm=LABEL.get(alg, alg),
                alg_key=alg,
                instances=t.instance.nunique(),
                runs=len(t),
                feasible_rate=len(ok) / len(t),
                mean_of_means=inst_mean.mean(),
                mean_of_best=ok.groupby("instance").objective.min().mean(),
                mean_std=(
                    ok.groupby("instance").objective.std(ddof=1).mean()
                    if alg not in {"greedy", "mip"}
                    else None
                ),
                pct_above_best_known=rel.mean(),
                mean_time_s=t.wall_seconds.mean(),
                heuristic_budget_s=t.budget_s.iloc[0] if alg != "mip" else None,
                mip_budget_s=t.mip_budget_s.iloc[0] if alg == "mip" else None,
                proven_optimal=int(t.proven_optimal.sum()) if alg == "mip" else None,
            )
        )
    s = pd.DataFrame(rows)
    s["_o"] = s.alg_key.map({a: i for i, a in enumerate(ORDER)})
    return s.sort_values(["group", "_o"]).drop(columns="_o")


def tests(r):
    rows = []
    for grp, g in r.groupby("group"):
        means = (
            g[g.feasible]
            .dropna(subset=["objective"])
            .groupby(["instance", "algorithm"])
            .objective.mean()
            .unstack()
        )
        for a, b in PAIRS:
            if a not in means or b not in means:
                continue
            d = means[[a, b]].dropna()
            diff = d[a] - d[b]
            row = dict(
                group=grp,
                A=LABEL[a],
                B=LABEL[b],
                pairs=len(d),
                A_better=int((diff < -1e-6).sum()),
                ties=int((diff.abs() <= 1e-6).sum()),
                B_better=int((diff > 1e-6).sum()),
                mean_A=d[a].mean(),
                mean_B=d[b].mean(),
                mean_improvement_pct=(
                    100 * ((d[b] - d[a]) / d[b]).mean() if len(d) else None
                ),
                median_diff=diff.median() if len(d) else None,
            )
            nz = int((diff.abs() > 1e-6).sum())
            if nz >= 5:
                row["p_value"] = float(
                    wilcoxon(
                        d[a], d[b], zero_method="wilcox", alternative="two-sided"
                    ).pvalue
                )
                row["significant_0.05"] = row["p_value"] < 0.05
            else:
                row["p_value"] = None
                row["significant_0.05"] = None
                row["note"] = f"only {nz} non-tied pairs; test not meaningful"
            rows.append(row)
    return pd.DataFrame(rows)


def figures(r, out):
    for grp, g in r.groupby("group"):
        bk = best_known(g)
        ok = g[g.feasible].dropna(subset=["objective"]).copy()
        ok["rel"] = 100 * (ok.objective / ok.instance.map(bk) - 1)
        algs = [a for a in ORDER if a in ok.algorithm.unique()]
        fig, ax = plt.subplots(figsize=(8, 4.5))
        ax.boxplot(
            [ok[ok.algorithm == a].rel.to_numpy() for a in algs],
            tick_labels=[LABEL[a] for a in algs],
        )
        ax.set(
            ylabel="% above best known Z of the instance",
            title=f"{grp}: solution quality over instances and seeds",
        )
        ax.grid(alpha=0.25, axis="y")
        fig.tight_layout()
        fig.savefig(out / f"boxplot_{grp}.png", dpi=170)
        plt.close(fig)
        first = sorted(g.instance.unique())[0]
        fig, ax = plt.subplots(figsize=(8, 4.5))
        drawn = False
        for a in [x for x in ORDER if x not in {"greedy", "mip"}]:
            t = g[(g.instance == first) & (g.algorithm == a) & (g.seed == 0)]
            if t.empty:
                continue
            res = json.loads(Path(t.iloc[0].run_path).read_text())
            h = pd.DataFrame(res.get("history", []))
            if h.empty:
                continue
            x = h.seconds.tolist() + [res["wall_seconds"]]
            y = h.objective.tolist() + [h.objective.iloc[-1]]
            ax.step(x, y, where="post", label=LABEL[a])
            drawn = True
        if drawn:
            ax.set(
                xlabel="Wall time (s)",
                ylabel="Best Z so far (h)",
                title=f"{grp}: convergence on {first}, seed 0",
            )
            ax.legend()
            ax.grid(alpha=0.25)
            fig.tight_layout()
            fig.savefig(out / f"convergence_{grp}.png", dpi=170)
        plt.close(fig)


def md(df, digits=2):
    if df is None or df.empty:
        return "_no data_\n"

    def f(v):
        if v is None or (isinstance(v, float) and np.isnan(v)):
            return "–"
        if isinstance(v, (float, np.floating)):
            return f"{v:.{digits}f}" if abs(v) >= 1e-3 or v == 0 else f"{v:.2e}"
        return str(v)

    head = (
        "| "
        + " | ".join(map(str, df.columns))
        + " |\n|"
        + "---|" * len(df.columns)
        + "\n"
    )
    return head + "".join(
        "| " + " | ".join(f(v) for v in row) + " |\n"
        for row in df.itertuples(index=False)
    )


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root", default="results/report")
    a = p.parse_args()
    root = Path(a.root)
    out = root / "report_tables"
    out.mkdir(parents=True, exist_ok=True)
    r = load(root)
    s = summary(r)
    w = tests(r)
    s.drop(columns="alg_key").to_csv(
        out / "summary.csv", index=False, encoding="utf-8-sig"
    )
    w.to_csv(out / "wilcoxon.csv", index=False, encoding="utf-8-sig")
    abl = s[s.alg_key.isin(["ga", "ga_greedy", "ga_repair", "gga"])]
    abl = abl[abl.group.isin(abl[abl.alg_key.isin(["ga_greedy", "ga_repair"])].group)]
    abl.drop(columns="alg_key").to_csv(
        out / "ablation.csv", index=False, encoding="utf-8-sig"
    )
    figures(r, out)
    lines = [
        "# Experiment results\n",
        f"Source: `{root}` — {len(r)} runs, {int(r.feasible.sum())} feasible (independent validator).\n",
        "Objective Z = total time vessels spend in port (hours). Statistics over seeds; group rows average over instances.\n",
        "Wilcoxon: two-sided signed-rank test on per-instance mean Z (pairs = instances).\n",
    ]
    for grp, g in r.groupby("group"):
        t = per_instance(g)
        t.to_csv(out / f"per_instance_{grp}.csv", index=False, encoding="utf-8-sig")
        lines += [
            f"\n## {grp}\n",
            "\n### Per instance\n",
            md(t),
            "\n### Summary\n",
            md(s[s.group == grp].drop(columns=["group", "alg_key"])),
            "\n### Wilcoxon\n",
            md(w[w.group == grp].drop(columns="group") if not w.empty else w, 4),
        ]
    if not abl.empty:
        lines += ["\n## Ablation\n", md(abl.drop(columns="alg_key"))]
    (out / "REPORT.md").write_text("".join(lines), encoding="utf-8")
    print(
        md(
            s.drop(columns="alg_key")[
                [
                    "group",
                    "algorithm",
                    "mean_of_means",
                    "mean_of_best",
                    "pct_above_best_known",
                    "mean_time_s",
                ]
            ]
        )
    )
    if not w.empty:
        print(
            md(
                w[
                    [
                        "group",
                        "A",
                        "B",
                        "pairs",
                        "A_better",
                        "ties",
                        "B_better",
                        "mean_improvement_pct",
                        "p_value",
                    ]
                ],
                4,
            )
        )
    print(f"Written: {out}")


if __name__ == "__main__":
    main()
