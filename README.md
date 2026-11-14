# Port Scheduling Lab 2.0

Ứng dụng Advanced Algorithms: continuous BAP + time-invariant specific QCAP.

## Bắt đầu

1. Cài Python 3.11+; giải nén, mở terminal tại thư mục này.
2. Tạo môi trường: `python -m venv .venv`.
3. Windows: dùng `.venv\Scripts\python.exe`; macOS/Linux: `.venv/bin/python` trong các lệnh dưới.
4. `python -m pip install -e .`
5. `python -m streamlit run app.py`

Đọc hướng dẫn đầy đủ tại **docs/STREAMLIT_GUIDE.md**, cũng hiển thị tại mục 7 trong ứng dụng. README.md và tài liệu METHOD.md được giữ từ bản CLI để giải thích mô hình; thông tin kiểm chứng hiện tại xem **docs/EXECUTION_STATUS.md**.

## Có gì trong gói

- Nhập/sửa tàu, upload JSON/CSV, tải input đã kiểm tra.
- Greedy/GA/GGA, hai biến thể ablation (GA + khởi tạo tham lam, GA + Repair), MIP với HiGHS hoặc Gurobi tùy license.
- 51 input chính: bộ Liêu Ninh 12 tàu và 10 instance cho mỗi nhóm 5/10/15/20/40 tàu; JSON + CSV + chỉ mục cấu hình.
- Batch 10 seed, checkpoint, cấu hình time/generations tách riêng, lỗi solver được báo rõ.
- Lịch bến/cẩu, gene, minh họa toán tử, hội tụ, Best/Mean, phân bố chất lượng, wall time; PNG/PDF.
- Figure 5–7 dựng từ bảng bài báo được lưu riêng tại paper_figures/ và hiển thị tại mục 5, gắn nhãn nguồn tham khảo.
- Kiểm tra hai ví dụ corrected/printed_core bằng solver.
- Các kết quả đã thực chạy nằm trong results/; không đồng nhất kiểm tra nhanh với ngân sách thực nghiệm bài báo.

## Thực nghiệm cho báo cáo (khuyến nghị)

```bash
.venv/bin/python run_report_plan.py --dry-run     # xem kế hoạch và thời gian ước tính
.venv/bin/python run_report_plan.py               # chạy tất cả, có checkpoint, tối đa khoảng 9 giờ
.venv/bin/python analyze_report.py --root results/report
```

Kế hoạch gồm kiểm chứng mô hình, bộ Liêu Ninh, 5 nhóm 5/10/15/20/40 tàu × 10 instance × 10 seed, MIP HiGHS và ablation (`ga_greedy`, `ga_repair`) trên nhóm 15/20 tàu. Bảng, kiểm định Wilcoxon và hình nằm trong `results/report/report_tables/`. Chi tiết: docs/HUONG_DAN_THUC_NGHIEM.md mục 14; kết quả đã chạy: docs/EXECUTION_STATUS.md. Từng bước tái lập bằng giao diện Streamlit: **docs/HUONG_DAN_TAI_LAP_KET_QUA_STREAMLIT.md**.

## Chạy toàn bộ thiết kế (preset cũ)

```bash
python benchmark.py --preset paper-generations --groups 5 10 15 20 --include-real --algorithms greedy ga gga --out results/full_100gen
python benchmark.py --preset paper-time --groups 40 --algorithms greedy ga gga mip --solver gurobi --out results/full_40_60s
python benchmark.py --preset paper-generations --groups 5 10 --algorithms mip --solver gurobi --out results/full_small_mip
```

Đây là các lệnh chạy dài; cần máy và license phù hợp. Không có synthetic instance gốc tác giả nên dữ liệu tổng hợp là tự sinh theo Table 3. Cài đặt decoder có các lựa chọn riêng được công bố trong METHOD.md. Các hình 1–4 là minh họa do project dựng lại theo bản cài đặt, không sao chép hình của tác giả.

Kiểm tra:

```bash
python -m unittest discover -s tests -v
```
