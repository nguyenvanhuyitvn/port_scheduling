"""Run: python -m streamlit run app.py (after pip install -e .)."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
import io
import json
import uuid
from dataclasses import asdict
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st
from port_scheduler.domain import load_instance, write_json
from port_scheduler.experiments import (
    Config,
    execute,
    run_matrix,
    collect,
    aggregate,
    from_frame,
    zip_directory,
)
from port_scheduler.charts import (
    comparison,
    reference,
    convergence,
    distributions,
    explanatory_figures,
    export_suite,
)
from port_scheduler.validation import validate
from port_scheduler.cli import verify_examples

st.set_page_config(page_title="Port Scheduling Lab", layout="wide")
st.title("Port Scheduling Lab - Advanced Algorithms")
st.caption(
    "Continuous BAP + time-invariant specific QCAP | Independent implementation | Z = Σ(end - ETA), hours"
)
st.sidebar.markdown(
    """
    <style>
    [data-testid="stSidebarUserContent"] [data-testid="stVerticalBlock"] {
        min-height: calc(100vh - 5rem);
    }
    [data-testid="stSidebarUserContent"] [data-testid="stVerticalBlock"]
        > [data-testid="stElementContainer"]:last-child {
        margin-top: auto;
    }
    </style>
    """,
    unsafe_allow_html=True,
)
st.sidebar.markdown("**CHỨC NĂNG CHÍNH**")
page = st.sidebar.radio(
    "Chức năng",
    [
        "1. Dữ liệu đầu vào",
        "2. Lập lịch",
        "3. Thực nghiệm hàng loạt",
        "4. Biểu đồ và bảng kết quả",
        "5. Đối chiếu bài báo",
        "6. Kiểm tra (5)-(8)",
        "7. Hướng dẫn",
    ],
    label_visibility="collapsed",
)
st.sidebar.markdown(
    "**Người thực hiện**<br>Nguyễn Văn Huy<br>Tạ Quang Hưng",
    unsafe_allow_html=True,
)


def download_dir(path, label="Tải toàn bộ kết quả ZIP"):
    st.download_button(
        label,
        zip_directory(path),
        file_name=Path(path).name + ".zip",
        mime="application/zip",
    )


def fig_download(fig, name):
    st.pyplot(fig)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=180, bbox_inches="tight")
    st.download_button(
        "Tải " + name, buf.getvalue(), file_name=name, mime="image/png", key=name
    )
    plt.close(fig)


def controls(prefix):
    mode = st.selectbox(
        "Ngân sách heuristic", ["time", "generations"], key=prefix + "mode"
    )
    a, b, c = st.columns(3)
    seconds = a.number_input(
        "Giây / lần heuristic", min_value=0.01, value=5.0, key=prefix + "sec"
    )
    generations = b.number_input(
        "Số thế hệ", min_value=1, value=100, key=prefix + "gen"
    )
    population = c.number_input("Population", min_value=4, value=40, key=prefix + "pop")
    a, b, c = st.columns(3)
    pc = a.number_input("Crossover pc", 0.0, 1.0, 0.8, key=prefix + "pc")
    pm = b.number_input("Mutation pm", 0.0, 1.0, 0.2, key=prefix + "pm")
    beta = c.number_input("Mutation beta", 0.0, 1.0, 0.15, key=prefix + "beta")
    a, b, c = st.columns(3)
    solver = a.selectbox("MIP backend", ["highs", "gurobi"], key=prefix + "solver")
    ss = b.number_input(
        "Giới hạn MIP (giây)", min_value=0.1, value=60.0, key=prefix + "ss"
    )
    threads = c.number_input(
        "Gurobi threads", min_value=1, value=1, key=prefix + "threads"
    )
    if mode == "generations":
        st.info(
            "Heuristic chạy đủ số thế hệ, không giới hạn wall time. Thời gian thực tế có thể dài. Greedy chỉ xây dựng một lịch."
        )
    return Config(
        mode,
        float(seconds),
        int(generations),
        int(population),
        pc,
        pm,
        beta,
        float(ss),
        solver,
        int(threads),
    )


if page.startswith("1."):
    st.subheader("Nhập, sửa và tải dữ liệu")
    source = st.radio(
        "Nguồn", ["Dữ liệu có sẵn", "Upload JSON / CSV", "Tạo mới"], horizontal=True
    )
    try:
        metadata = {}
        if source == "Dữ liệu có sẵn":
            paths = sorted((ROOT / "data").rglob("*.json"))
            chosen = st.selectbox(
                "Instance", paths, format_func=lambda p: str(p.relative_to(ROOT))
            )
            ins = load_instance(chosen)
            d = asdict(ins)
            metadata = d["metadata"]
            frame = pd.DataFrame(d["vessels"])
        elif source == "Upload JSON / CSV":
            upload = st.file_uploader(
                "JSON cấu hình đầy đủ hoặc CSV danh sách tàu", type=["json", "csv"]
            )
            if upload is None:
                st.stop()
            if upload.name.endswith(".json"):
                d = json.loads(upload.getvalue().decode("utf-8-sig"))
                metadata = d.get("metadata", {})
                frame = pd.DataFrame(d["vessels"])
            else:
                frame = pd.read_csv(upload, dtype={"id": str})
                d = dict(
                    name=Path(upload.name).stem,
                    shoreline=1400,
                    cranes=11,
                    productivity=35,
                )
        else:
            d = dict(name="custom", shoreline=1400, cranes=11, productivity=35)
            frame = pd.DataFrame(
                [dict(id="V1", eta=0.0, length=150.0, workload=300.0, q_min=1, q_max=2)]
            )
        a, b, c, e = st.columns(4)
        name = a.text_input("Tên instance", str(d["name"]))
        L = b.number_input(
            "Chiều dài bến (m)", min_value=1.0, value=float(d["shoreline"])
        )
        m = c.number_input("Số cẩu", min_value=1, value=int(d["cranes"]))
        qe = e.number_input(
            "Năng suất mỗi cẩu (TEU/h)", min_value=0.01, value=float(d["productivity"])
        )
        st.info(
            "ETA nhập bằng giờ số thực tính từ mốc quy hoạch. Ví dụ ngày 1 lúc 04:00 → 4; ngày 2 lúc 03:00 → 27. Đây là giả định diễn giải ETA của dữ liệu bài báo."
        )
        edited = st.data_editor(
            frame, num_rows="dynamic", hide_index=True, width="stretch"
        )
        st.json(metadata, expanded=False)
        if st.button("Kiểm tra và dùng dữ liệu này", type="primary"):
            ins = from_frame(edited, name, L, m, qe, metadata | {"edited_in_app": True})
            st.session_state["input_data"] = asdict(ins)
            st.success(
                f"Hợp lệ: {len(ins.vessels)} tàu. Chuyển sang mục 2 để lập lịch."
            )
        if "input_data" in st.session_state:
            payload = st.session_state.input_data
            st.download_button(
                "Tải JSON đã kiểm tra",
                json.dumps(payload, ensure_ascii=False, indent=2),
                file_name="input_instance.json",
            )
            st.download_button(
                "Tải CSV danh sách tàu",
                pd.DataFrame(payload["vessels"])
                .to_csv(index=False)
                .encode("utf-8-sig"),
                file_name="input_vessels.csv",
            )
            st.caption(
                "CSV chỉ chứa tàu; JSON giữ thêm chiều dài bến, số cẩu, năng suất và metadata."
            )
    except Exception as exc:
        st.error(f"Dữ liệu không hợp lệ: {exc}")

elif page.startswith("2."):
    paths = sorted((ROOT / "data").rglob("*.json"))
    chosen = st.selectbox(
        "Instance có sẵn", paths, format_func=lambda p: str(p.relative_to(ROOT))
    )
    custom = st.checkbox(
        "Dùng dữ liệu đã chỉnh tại mục 1", value="input_data" in st.session_state
    )
    algorithms = st.multiselect(
        "Thuật toán",
        ["greedy", "ga", "gga", "ga_greedy", "ga_repair", "mip"],
        default=["greedy", "gga"],
    )
    seed = st.number_input("Seed", min_value=0, value=0)
    config = controls("single")
    if st.button("Chạy lập lịch", type="primary"):
        if not algorithms:
            st.error("Chọn ít nhất một thuật toán.")
            st.stop()
        work = ROOT / "results" / "interactive" / uuid.uuid4().hex[:12]
        work.mkdir(parents=True)
        if custom:
            if "input_data" not in st.session_state:
                st.error("Chưa kiểm tra dữ liệu tại mục 1.")
                st.stop()
            chosen = work / "input.json"
            write_json(chosen, st.session_state.input_data)
        results = []
        for algorithm in algorithms:
            with st.spinner("Đang chạy " + algorithm):
                try:
                    ins, r = execute(chosen, algorithm, seed, config, work / algorithm)
                    if r["feasible"]:
                        explanatory_figures(
                            ins, r["schedule"], work / algorithm / "charts"
                        )
                    results.append((algorithm, r, str(work / algorithm)))
                except Exception as exc:
                    st.error(f"{algorithm}: {exc}")
        st.session_state["single_results"] = results
        st.session_state["single_root"] = str(work)
    if "single_results" in st.session_state:
        results = st.session_state.single_results
        for algorithm, r, path in results:
            st.subheader(algorithm.upper())
            a, b, c, e = st.columns(4)
            a.metric(
                "Z (giờ)",
                (
                    f"{r['objective']:.6f}"
                    if r.get("objective") is not None
                    else "Không có incumbent"
                ),
            )
            b.metric("Wall time (giây)", f"{r['wall_seconds']:.3f}")
            c.metric("Trạng thái", r["status"])
            e.metric("Chứng minh tối ưu", "Có" if r.get("proven_optimal") else "Chưa")
            st.write(
                "Khả thi:",
                r["feasible"],
                "| Lỗi validator:",
                r.get("validation_errors", []),
            )
            st.json(
                {k: v for k, v in r.items() if k not in {"schedule", "history"}},
                expanded=False,
            )
            table = pd.read_csv(Path(path) / "schedule.csv")
            st.dataframe(table, width="stretch", hide_index=True)
            if not table.empty:
                st.write(
                    {
                        "Tổng chờ (giờ)": float(table.waiting.sum()),
                        "Tổng làm hàng (giờ)": float(table.duration.sum()),
                        "Thời điểm hoàn thành cuối (giờ)": float(table.end.max()),
                    }
                )
            for file in [
                "berth_schedule.png",
                "crane_schedule.png",
                "figure2_chromosome.png",
            ]:
                p = Path(path) / "charts" / file
                if p.exists():
                    st.image(str(p), caption=file)
        fig_download(
            convergence([(a, r) for a, r, _ in results]), "convergence_single.png"
        )
        download_dir(st.session_state.single_root)

elif page.startswith("3."):
    st.subheader("Ma trận thực nghiệm có lưu checkpoint")
    st.warning(
        "10 instance × 10 seed × 2 heuristic ở mỗi nhóm; toàn bộ 5 nhóm tạo 1.000 lần chạy heuristic. Nhóm 40 tàu với 60 giây/lần riêng đã có thể cần hơn 3 giờ cho GA/GGA. Có thể chạy CLI, tắt app và mở lại kết quả sau."
    )
    groups = st.multiselect("Nhóm số tàu", [5, 10, 15, 20, 40], default=[5])
    include_real = st.checkbox("Thêm dữ liệu Liêu Ninh 12 tàu", False)
    count = st.slider("Số instance mỗi nhóm", 1, 10, 10)
    repeats = st.slider("Số seed heuristic / instance", 1, 10, 10)
    algorithms = st.multiselect(
        "Phương pháp",
        ["greedy", "ga", "gga", "ga_greedy", "ga_repair", "mip"],
        default=["greedy", "ga", "gga"],
    )
    config = controls("batch")
    label = st.text_input("Tên đợt chạy (chữ/số/gạch dưới)", "benchmark")
    if st.button("Chạy / tiếp tục thực nghiệm", type="primary"):
        if not label or any(
            c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"
            for c in label
        ):
            st.error("Tên đợt chạy không hợp lệ")
            st.stop()
        files = [
            p
            for n in groups
            for p in sorted((ROOT / "data" / "benchmark").glob(f"n{n:02d}_*.json"))[
                :count
            ]
        ]
        if include_real:
            files.append(ROOT / "data" / "liaoning_12.json")
        if not files or not algorithms:
            st.error("Chọn dữ liệu và phương pháp.")
            st.stop()
        bar = st.progress(0.0)
        status = st.empty()

        def update(i, total, message):
            bar.progress(i / total)
            status.write(f"{i}/{total}: {message}")

        root, records, summary, errors = run_matrix(
            files,
            algorithms,
            list(range(repeats)),
            config,
            ROOT / "results" / label,
            update,
        )
        export_suite(root)
        st.session_state["last_batch"] = str(root)
        st.success(
            f"Hoàn thành ma trận. {len(records)} kết quả đã lưu; {len(errors)} lỗi."
        )
        st.dataframe(summary)
        if errors:
            st.error(
                "Có lần chạy lỗi; xem errors.json trong gói kết quả. Không thay bằng số liệu mô phỏng."
            )
    if "last_batch" in st.session_state:
        download_dir(st.session_state.last_batch)

elif page.startswith("4."):
    configs = (
        sorted((ROOT / "results").rglob("experiment.json"))
        if (ROOT / "results").exists()
        else []
    )
    if not configs:
        st.info("Chưa có kết quả batch. Chạy mục 3 hoặc CLI.")
        st.stop()
    selected = st.selectbox(
        "Đợt và cấu hình",
        configs,
        format_func=lambda p: str(p.parent.relative_to(ROOT)),
    )
    root = selected.parent
    st.json(json.loads(selected.read_text()), expanded=False)
    records = collect(root)
    summary = aggregate(records)
    if records.empty:
        st.warning("Không có lần chạy thành công. Xem errors.json.")
        st.stop()
    st.dataframe(summary, width="stretch", hide_index=True)
    st.caption(
        "Best/Mean/Std chỉ tính trên các lần khả thi. Std mẫu ddof=1; để trống nếu <2 lần. MIP best là incumbent nếu chưa proven_optimal. Seed tái lập theo số thế hệ; ngân sách thời gian có thể đổi số đánh giá."
    )
    n = st.selectbox("Số tàu", sorted(records.n.unique()))
    fig_download(comparison(summary, int(n)), f"comparison_n{n}.png")
    fig_download(distributions(records, int(n)), f"distribution_n{n}.png")
    names = records[records.n == n].instance.unique()
    instance = st.selectbox("Instance xem hội tụ", names)
    available = records[records.instance == instance]
    labels = {
        f"{r.algorithm} seed={r.seed}": r.run_path for r in available.itertuples()
    }
    chosen = st.multiselect("Đường hội tụ", list(labels), default=list(labels)[:4])
    axis = st.radio("Trục hội tụ", ["seconds", "generation"], horizontal=True)
    fig_download(
        convergence(
            [(k, json.loads(Path(labels[k]).read_text())) for k in chosen], axis
        ),
        "convergence_batch.png",
    )
    st.dataframe(records, width="stretch", hide_index=True)
    errors = root / "errors.json"
    if errors.exists() and json.loads(errors.read_text()):
        st.error(json.loads(errors.read_text()))
    download_dir(root)

elif page.startswith("5."):
    st.subheader("Số liệu công bố - chỉ dùng tham khảo")
    st.warning(
        "Các số liệu dưới đây được chép từ bảng bài báo. Đây KHÔNG phải kết quả chương trình vừa chạy. Dữ liệu synthetic gốc và mã tác giả chưa được cung cấp."
    )
    for n in [15, 20, 40]:
        data = pd.read_csv(
            ROOT / "data" / "paper_reference" / f"table_{ {15:6,20:7,40:8}[n]}.csv"
        )
        fig_download(
            reference(data, n), f"paper_figure_{ {15:5,20:6,40:7}[n]}_redrawn.png"
        )
        st.dataframe(data, hide_index=True)
    for table in [2, 4, 5]:
        st.write(f"Table {table} - số liệu công bố")
        st.dataframe(
            pd.read_csv(ROOT / "data" / "paper_reference" / f"table_{table}.csv"),
            hide_index=True,
        )
    st.markdown(
        "Figures 1–4: hình giải thích do project dựng riêng được xuất khi chạy một lịch khả thi ở mục 2. Figure 3 tương ứng hai lịch bến và cẩu thực tế. Không khẳng định Chromosome Representation năm gene của project giống nguyên bản tác giả."
    )

elif page.startswith("6."):
    st.subheader("Kiểm tra ràng buộc (5)-(8)")
    st.write(
        "Hai tàu A/B: ETA=0, dài 100 m, 70 TEU, đúng một cẩu/tàu, hai cẩu năng suất 35 TEU/h. Mỗi tàu cần 2 giờ."
    )
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Bến (m)": 200,
                    "corrected - suy luận": 4,
                    "printed_core - suy luận": "6",
                },
                {
                    "Bến (m)": 100,
                    "corrected - suy luận": 6,
                    "printed_core - suy luận": "INFEASIBLE",
                },
            ]
        )
    )
    st.caption(
        "Bến 200 m: corrected cho làm đồng thời ở hai đoạn bến và hai cẩu. printed_core buộc tách thêm thời gian. Bến 100 m: hai tàu phải dùng lại cùng đoạn bến; printed_core vẫn đòi tách không gian nên vô nghiệm. printed_core chỉ là lõi chẩn đoán."
    )
    solver = st.selectbox("Solver kiểm tra", ["highs", "gurobi"])
    seconds = st.number_input("Giới hạn mỗi ví dụ (giây)", 1.0, 120.0, 10.0)
    if st.button("Chạy solver xác nhận"):
        from argparse import Namespace

        out = ROOT / "results" / "verification" / uuid.uuid4().hex[:8]
        try:
            verify_examples(Namespace(out=str(out), solver=solver, seconds=seconds))
            st.success("Cả bốn kiểm tra PASS, solver đã xác nhận trạng thái.")
        except Exception as exc:
            st.error(str(exc))
        if (out / "verification.json").exists():
            st.dataframe(pd.read_json(out / "verification.json"))
        if out.exists():
            download_dir(out, "Tải log kiểm tra")

else:
    st.markdown((ROOT / "docs" / "STREAMLIT_GUIDE.md").read_text(encoding="utf-8"))
