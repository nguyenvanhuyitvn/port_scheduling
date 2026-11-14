"""Vẽ Hình 3.1–3.6 của báo cáo (nhãn tiếng Việt) từ kết quả đã chạy.

    .venv/bin/python make_report_figures.py                       # đọc results/report
    .venv/bin/python make_report_figures.py --root results/abc    # đợt chạy khác

Ghi ra <root>/report_tables/: verification_examples.png (Hình 3.1), berth_liaoning_gga.png và
crane_liaoning_gga.png (Hình 3.2, 3.3), conv_liaoning.png (Hình 3.4), conv_n40.png (Hình 3.5),
box_n20.png (Hình 3.6). Cần đủ GA/GGA seed 0 cho liaoning_12 và n40_01, và đủ năm cấu hình
(greedy, ga, ga_greedy, ga_repair, gga) cho nhóm 20 tàu.
"""

import argparse
import collections
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

NAMES = {
    "greedy": "Greedy",
    "ga": "GA",
    "ga_greedy": "GA + khởi tạo tham lam",
    "ga_repair": "GA + Repair",
    "gga": "GGA",
}
COLORS = {"ga": "#1f77b4", "gga": "#d62728"}


def load(root):
    runs = collections.defaultdict(dict)
    for f in Path(root).glob("*/*/*/run.json"):
        d = json.loads(f.read_text())
        if d.get("algorithm") and d.get("feasible"):
            instance = f.parent.parent.name.rsplit("_", 1)[0]
            runs[instance][(d["algorithm"], d.get("seed", 0))] = d
    return runs


def convergence(runs, instance, title, path, log=False):
    fig, ax = plt.subplots(figsize=(9, 4.6))
    for alg in ("ga", "gga"):
        d = runs[instance][(alg, 0)]
        xs = [p["seconds"] for p in d["history"]] + [d["wall_seconds"]]
        ys = [p["objective"] for p in d["history"]]
        ys.append(ys[-1])
        ax.step(xs, ys, where="post", label=NAMES[alg], color=COLORS[alg], lw=1.8)
    if log:
        ax.set_yscale("log")
    ax.set_xlabel("Thời gian thực (giây)")
    ax.set_ylabel("Z tốt nhất đã tìm được (giờ)")
    ax.set_title(title)
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def boxplot(runs, prefix, path):
    algs = ["greedy", "ga", "ga_greedy", "ga_repair", "gga"]
    data = {a: [] for a in algs}
    for instance, r in runs.items():
        if not instance.startswith(prefix):
            continue
        best = min(d["objective"] for d in r.values())
        for (a, _), d in r.items():
            if a in data:
                data[a].append((d["objective"] / best - 1) * 100)
    fig, (ax1, ax2) = plt.subplots(
        1, 2, figsize=(10, 4.6), gridspec_kw={"width_ratios": [1, 4]}
    )
    ax1.boxplot([data["ga"]], tick_labels=["GA"])
    ax1.set_ylabel("% cao hơn Z tốt nhất đã biết của trường hợp")
    rest = [a for a in algs if a != "ga"]
    ax2.boxplot([data[a] for a in rest], tick_labels=[NAMES[a] for a in rest])
    for ax in (ax1, ax2):
        ax.grid(axis="y", alpha=0.3)
    fig.suptitle("Nhóm 20 tàu: 10 trường hợp × 10 seed (Greedy: 1 lượt/trường hợp)")
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def per_instance(runs, prefix, path, log=False):
    """Kiểu Hình 5–7 của bài báo, nhưng từ dữ liệu của project: avg/min qua 10 seed theo từng trường hợp."""
    names = sorted(i for i in runs if i.startswith(prefix))
    xs = list(range(1, len(names) + 1))
    fig, ax = plt.subplots(figsize=(9, 4.8))
    for alg, col in (("ga", "#1f77b4"), ("gga", "#d62728")):
        vals = [
            [d["objective"] for (a, _), d in runs[n].items() if a == alg] for n in names
        ]
        ax.plot(
            xs,
            [sum(v) / len(v) for v in vals],
            "o--",
            color=col,
            label=f"{NAMES[alg]} trung bình (avg)",
        )
        ax.plot(
            xs,
            [min(v) for v in vals],
            "s-",
            color=col,
            label=f"{NAMES[alg]} nhỏ nhất (min)",
        )
    greedy = [runs[n][("greedy", 0)]["objective"] for n in names]
    ax.plot(xs, greedy, "^:", color="#2ca02c", label="Greedy")
    mip = [
        (x, runs[n][("mip", 0)]["objective"])
        for x, n in zip(xs, names)
        if ("mip", 0) in runs[n]
    ]
    if mip:
        ax.plot(
            *zip(*mip),
            "D",
            color="#9467bd",
            markersize=8,
            label="MIP–HiGHS 60 giây (có nghiệm)",
        )
    if log:
        ax.set_yscale("log")
    ax.set_xticks(xs)
    ax.set_xlabel("Trường hợp")
    ax.set_ylabel("Tổng thời gian ở cảng Z (giờ)")
    n = prefix[1:].lstrip("0")
    ax.set_title(
        f"Nhóm {n} tàu: 10 trường hợp × 10 seed" + (" (trục tung log)" if log else "")
    )
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8, ncol=2)
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def berth_crane(runs, data_path, out_berth, out_crane):
    """Hình 3.2 và 3.3: lịch GGA seed 0 trên bộ 12 tàu."""
    d = runs["liaoning_12"][("gga", 0)]
    length = {
        v["id"]: v["length"] for v in json.loads(Path(data_path).read_text())["vessels"]
    }
    cmap = plt.get_cmap("tab20")
    rows = sorted(d["schedule"], key=lambda r: int(r["vessel_id"][1:]))
    fig, ax = plt.subplots(figsize=(9.5, 5.7))
    for k, r in enumerate(rows):
        ax.add_patch(
            plt.Rectangle(
                (r["start"], r["position"]),
                r["end"] - r["start"],
                length[r["vessel_id"]],
                facecolor=cmap(k),
                edgecolor="black",
                alpha=0.85,
            )
        )
        ax.text(
            (r["start"] + r["end"]) / 2,
            r["position"] + length[r["vessel_id"]] / 2,
            r["vessel_id"],
            ha="center",
            va="center",
            fontsize=9,
        )
    ax.set_xlim(0, max(r["end"] for r in rows) + 2)
    ax.set_ylim(0, 1400)
    ax.set_xlabel("Thời gian (giờ)")
    ax.set_ylabel("Vị trí bến (m)")
    ax.set_title("Lịch bố trí bến cho 12 tàu")
    fig.tight_layout()
    fig.savefig(out_berth, dpi=200)
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(9.5, 4.75))
    for k, r in enumerate(rows):
        for c in r["cranes"]:
            ax.add_patch(
                plt.Rectangle(
                    (r["start"], c - 0.35),
                    r["end"] - r["start"],
                    0.7,
                    facecolor=cmap(k),
                    edgecolor="black",
                )
            )
            ax.text(
                (r["start"] + r["end"]) / 2,
                c,
                r["vessel_id"],
                ha="center",
                va="center",
                fontsize=8,
            )
    ax.set_xlim(min(r["start"] for r in rows) - 2, max(r["end"] for r in rows) + 2)
    ax.set_ylim(0.3, 11.7)
    ax.set_yticks(range(1, 12))
    ax.set_xlabel("Thời gian (giờ)")
    ax.set_ylabel("Chỉ số cần trục")
    ax.set_title("Phân công cần trục cho 12 tàu")
    fig.tight_layout()
    fig.savefig(out_crane, dpi=200)
    plt.close(fig)


def verification(root, path):
    """Hình 3.1: lịch tối ưu của hai ví dụ kiểm chứng (mô hình đã hiệu chỉnh)."""
    import csv

    fig, axes = plt.subplots(2, 1, figsize=(8.5, 5.5))
    for ax, L in zip(axes, (200, 100)):
        rows = list(
            csv.DictReader(
                open(
                    Path(root) / "verification" / f"L{L}_corrected" / "schedule.csv",
                    encoding="utf-8-sig",
                )
            )
        )
        z = sum(float(r["flow_time"]) for r in rows)
        for r, col in zip(rows, ("#bcd4e6", "#e6d0b8")):
            s, e, p, l = (
                float(r["start"]),
                float(r["end"]),
                float(r["position"]),
                float(r["length"]),
            )
            ax.add_patch(
                plt.Rectangle((s, p), e - s, l, facecolor=col, edgecolor="#333")
            )
            ax.text(
                (s + e) / 2,
                p + l / 2,
                r["vessel_id"],
                ha="center",
                va="center",
                fontsize=12,
            )
        ax.set_xlim(-0.1, 4.5)
        ax.set_ylim(0, L * 1.05)
        ax.grid(alpha=0.3)
        ax.set_xlabel("Thời gian (giờ)")
        ax.set_ylabel("Vị trí bến (m)")
        ax.set_title(f"Bến {L} m và tổng thời gian ở cảng {z:g} giờ")
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--root", default="results/report")
    a = ap.parse_args()
    out = Path(a.root) / "report_tables"
    out.mkdir(parents=True, exist_ok=True)
    runs = load(a.root)
    convergence(
        runs,
        "liaoning_12",
        "Bộ 12 tàu Liêu Ninh, seed 0, ngân sách 5 giây",
        out / "conv_liaoning.png",
    )
    convergence(
        runs,
        "n40_01",
        "Trường hợp n40_01, seed 0, ngân sách 60 giây (trục tung log)",
        out / "conv_n40.png",
        log=True,
    )
    boxplot(runs, "n20", out / "box_n20.png")
    berth_crane(
        runs,
        "data/liaoning_12.json",
        out / "berth_liaoning_gga.png",
        out / "crane_liaoning_gga.png",
    )
    verification(a.root, out / "verification_examples.png")
    per_instance(runs, "n15", out / "instances_n15.png")
    per_instance(runs, "n20", out / "instances_n20.png")
    per_instance(runs, "n40", out / "instances_n40.png", log=True)
    names = (
        "verification_examples.png",
        "berth_liaoning_gga.png",
        "crane_liaoning_gga.png",
        "conv_liaoning.png",
        "conv_n40.png",
        "box_n20.png",
        "instances_n15.png",
        "instances_n20.png",
        "instances_n40.png",
    )
    print("Đã ghi", ", ".join(str(out / n) for n in names))
