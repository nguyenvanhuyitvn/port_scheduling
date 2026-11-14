"""Refresh portable tables and export representative convergence for each instance."""

from pathlib import Path
import argparse
import json
import matplotlib.pyplot as plt
from port_scheduler.experiments import collect, aggregate
from port_scheduler.charts import export_suite, convergence


def export(root):
    root = Path(root)
    records = collect(root)
    if records.empty:
        return
    records.to_csv(root / "runs.csv", index=False, encoding="utf-8-sig")
    aggregate(records).to_csv(root / "summary.csv", index=False, encoding="utf-8-sig")
    out = export_suite(root)
    for instance, g in records.groupby("instance"):
        items = []
        for algorithm, a in g.groupby("algorithm"):
            chosen = a.sort_values("seed").iloc[0]
            items.append(
                (
                    f"{algorithm} seed={chosen.seed}",
                    json.loads(Path(chosen.run_path).read_text()),
                )
            )
        fig = convergence(items)
        fig.savefig(out / f"convergence_{instance}_seed0.png", dpi=150)
        plt.close(fig)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("root")
    a = p.parse_args()
    export(a.root)
