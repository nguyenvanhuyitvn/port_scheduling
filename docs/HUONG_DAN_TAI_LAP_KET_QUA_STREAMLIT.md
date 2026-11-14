# Hướng dẫn dùng Streamlit để có kết quả như trong báo cáo

Tài liệu này hướng dẫn tái lập các bảng và hình trong Chương 3 của báo cáo
`Bao_cao_Advanced_Algorithms_Lap_lich_tau_Streamlit_v2.docx`, chủ yếu qua ứng dụng Streamlit.

Có hai cách:

| Cách | Làm gì | Thời gian | Số liệu |
|---|---|---|---|
| **A. Mở lại kết quả đã chạy** | Mục 4 của ứng dụng đọc thư mục `results/report/` | Vài phút | Khớp đúng với báo cáo |
| **B. Chạy lại từ đầu** | Mục 3 của ứng dụng, 6 đợt chạy | Khoảng 8 giờ | Gần giống, không trùng từng chữ số |

Ở cách B, số liệu không trùng hoàn toàn vì ngân sách GA/GGA tính theo **thời gian thực**: máy nhanh hay chậm, hoặc đang bận việc khác, thì số thế hệ chạy được trong cùng số giây sẽ khác. Xu hướng và kết luận vẫn giữ nguyên.

---

## 1. Cài đặt và mở ứng dụng

Mở Terminal tại thư mục project:

```bash
cd /Users/admin/Documents/advanced_alogrimths/code/port_scheduling_streamlit
```

Lần đầu tiên, cài môi trường (máy này đã có sẵn `.venv`, có thể bỏ qua):

```bash
python3 -m venv .venv && .venv/bin/python -m pip install -e .
```

Mở ứng dụng:

```bash
.venv/bin/python -m streamlit run app.py
```

Trình duyệt mở `http://localhost:8501`. Nếu báo **Port 8501 is not available**, tức là đang có một Streamlit khác chạy; tắt nó đi hoặc dùng cổng khác:

```bash
.venv/bin/python -m streamlit run app.py --server.port 8502
```

Thanh bên trái có 7 mục. Bảng dưới cho biết mỗi phần của báo cáo lấy từ đâu:

| Nội dung báo cáo | Mục trong ứng dụng | Ghi chú |
|---|---|---|
| Bảng 3.6, Hình 3.1: kiểm chứng ví dụ 200 m / 100 m | **6. Kiểm tra (5)–(8)** | |
| Bảng 3.8, Hình 3.2–3.3: lịch GGA 12 tàu | **2. Lập lịch** | |
| Bảng 3.7, 3.9–3.14: kết quả 10 seed, 5 nhóm, ablation | **3. Thực nghiệm hàng loạt** (chạy) và **4. Biểu đồ và bảng kết quả** (xem) | Kiểm định Wilcoxon chạy bằng lệnh, xem mục 6 |
| Bảng 3.15–3.16, Hình 3.10–3.12: số liệu bài báo | **5. Đối chiếu bài báo** | Số chép từ bài báo, không phải kết quả chạy |
| Hình 3.1–3.9 (nhãn tiếng Việt) | Lệnh `make_report_figures.py` | Xem mục 6 |

---

## 2. Kiểm chứng mô hình (Bảng 3.6) — khoảng 1 phút

1. Chọn **6. Kiểm tra (5)–(8)**.
2. *Solver kiểm tra*: `highs`. *Giới hạn mỗi ví dụ*: `10`.
3. Nhấn **Chạy solver xác nhận**.

Kết quả đúng: ứng dụng báo *"Cả bốn kiểm tra PASS, solver đã xác nhận trạng thái."* Bốn trường hợp được kiểm tra là:

| Ví dụ | Mô hình | Kết quả |
|---|---|---|
| Bến 200 m | corrected | 4 giờ |
| Bến 200 m | printed_core | 6 giờ |
| Bến 100 m | corrected | 6 giờ |
| Bến 100 m | printed_core | INFEASIBLE |

## 3. Lịch GGA cho 12 tàu (Bảng 3.8, Hình 3.2–3.3) — khoảng 10 giây

1. Chọn **2. Lập lịch**.
2. *Instance có sẵn*: `data/liaoning_12.json`. Không đánh dấu ô "Dùng dữ liệu đã chỉnh tại mục 1".
3. *Thuật toán*: `greedy`, `gga`. Có thể thêm `ga` để so sánh. *Seed*: `0`.
4. *Ngân sách heuristic*: `time`; *Giây / lần heuristic*: `5`; *Population*: `40`; *pc* `0.8`, *pm* `0.2`, *beta* `0.15`.
5. Nhấn **Chạy lập lịch**.

Kết quả đúng:
- Greedy và GGA đều cho **Z = 79,114 giờ**, khả thi, thời gian chờ bằng 0.
- Bảng lịch GGA trùng Bảng 3.8: V1 bắt đầu lúc 4,000 tại vị trí 0, dùng cẩu 1–2, v.v.
- Hai hình lịch bến và lịch cẩu tương ứng Hình 3.2 và 3.3.

Nút **Tải toàn bộ kết quả ZIP** lưu lịch, `run.json` và các hình.

---

## 4. Cách A — Mở lại kết quả đã chạy (khuyến nghị)

Thư mục `results/report/` chứa toàn bộ 1.522 lượt chạy của đợt 11–12/11/2026. Mỗi thư mục con ứng với một cấu hình ngân sách:

| Thư mục trong `results/report/` | Nội dung | Ngân sách heuristic / MIP |
|---|---|---|
| `67396ef25939030e` | Nhóm 5 tàu | 2 s / 300 s |
| `26331fd6e2eeeb90` | Nhóm 10 tàu **và** bộ Liêu Ninh 12 tàu (cả hai biến thể ablation) | 5 s / 300 s |
| `16348e76a844470b` | Nhóm 15 tàu, có ablation | 10 s / – |
| `cdc022fc3ed71817` | Nhóm 20 tàu, có ablation | 20 s / – |
| `fb2963d024b6d90c` | Nhóm 40 tàu | 60 s / 60 s |

Các bước:

1. Chọn **4. Biểu đồ và bảng kết quả**.
2. Ở ô *Đợt và cấu hình*, gõ `report/` rồi chọn thư mục theo bảng trên. Dòng `{...}` bên dưới hiện cấu hình ngân sách để bạn kiểm tra đã chọn đúng.
3. Bảng tổng hợp hiện Best/Mean/Std theo instance và phương pháp.
4. Ở ô *Số tàu*, chọn nhóm để xem:
   - biểu đồ so sánh Best/Mean theo instance;
   - biểu đồ phân bố chất lượng;
   - đường hội tụ. Chọn instance và seed: ví dụ `n40_01`, `ga seed=0` và `gga seed=0` cho ra Hình 3.8 với nhãn tiếng Anh. Biểu đồ so sánh theo instance ứng với Hình 3.5–3.7.
5. Mỗi hình có nút tải PNG. Nút cuối trang tải cả thư mục dưới dạng ZIP.

Số liệu xem ở mục 4 được tính theo từng instance. Các con số tổng hợp của báo cáo (trung bình theo nhóm, Wilcoxon) lấy từ lệnh ở mục 6.

---

## 5. Cách B — Chạy lại toàn bộ trong Streamlit

### Lưu ý trước khi chạy

- Ứng dụng tạo một thư mục kết quả riêng cho mỗi tổ hợp "cấu hình + phiên bản mã nguồn". Hôm 12/11 tệp `charts.py` đã được sửa sau đợt chạy chính, nên lần chạy mới sẽ **không dùng lại** được thư mục `results/report/` và sẽ chạy từ đầu. Đặt một tên đợt mới, ví dụ `report_streamlit`, để không lẫn với kết quả cũ.
- Mỗi lần nhấn nút chỉ chạy **một** cấu hình ngân sách. Các nhóm có ngân sách khác nhau nên cần **6 lần bấm**.
- Ứng dụng lưu checkpoint. Nếu lỡ đóng trình duyệt hoặc máy ngủ, mở lại, chọn đúng tham số và nhấn lại nút: các lượt đã xong được bỏ qua.
- Đợt dài nên chạy bằng lệnh (mục 5.3) thay cho trình duyệt. Không chạy hai đợt cùng lúc, vì thời gian sẽ bị đo sai.
- Trên macOS, giữ máy không ngủ trong lúc chạy, ví dụ chạy kèm `caffeinate -i`.

### 5.1 Tham số chung cho cả 6 đợt (mục 3. Thực nghiệm hàng loạt)

| Ô trên giao diện | Giá trị |
|---|---|
| Số instance mỗi nhóm | `10` |
| Số seed heuristic / instance | `10` |
| Ngân sách heuristic | `time` |
| Số thế hệ | `100` (không dùng ở chế độ time, giữ nguyên mặc định) |
| Population | `40` |
| Crossover pc / Mutation pm / Mutation beta | `0.8` / `0.2` / `0.15` |
| MIP backend | `highs` |
| Gurobi threads | `1` |
| Tên đợt chạy | `report_streamlit` (giữ nguyên cho cả 6 đợt) |

### 5.2 Sáu đợt chạy

| Đợt | Nhóm số tàu | Ô "Thêm dữ liệu Liêu Ninh" | Phương pháp | Giây / lần heuristic | Giới hạn MIP (giây) | Thời gian ước tính |
|---|---|---|---|---|---|---|
| 1 | (để trống) | ✔ | greedy, ga, gga, ga_greedy, ga_repair, mip | 5 | 300 | ~9 phút |
| 2 | 5 | ✘ | greedy, ga, gga, mip | 2 | 300 | ~12 phút |
| 3 | 10 | ✘ | greedy, ga, gga, mip | 5 | 300 | ~1 giờ 10 phút |
| 4 | 15 | ✘ | greedy, ga, gga, ga_greedy, ga_repair | 10 | 1 | ~1 giờ 10 phút |
| 5 | 20 | ✘ | greedy, ga, gga, ga_greedy, ga_repair | 20 | 1 | ~2 giờ 15 phút |
| 6 | 40 | ✘ | greedy, ga, gga, mip | 60 | 60 | ~3 giờ 30 phút |

Mỗi đợt: điền tham số, nhấn **Chạy / tiếp tục thực nghiệm**, chờ đến khi hiện *"Hoàn thành ma trận. … kết quả đã lưu; 0 lỗi."*

Giải thích một số lựa chọn:
- Đợt 4 và 5 không chạy MIP. Ô giới hạn MIP đặt `1` chỉ để cấu hình trùng với đợt chạy bằng lệnh.
- Đợt 1 và đợt 3 dùng cùng ngân sách nên kết quả nằm chung một thư mục, giống `26331fd6e2eeeb90`.

Sau khi xong, xem kết quả ở **mục 4** như cách A, chọn các thư mục trong `results/report_streamlit/`.

### 5.3 Cách tương đương bằng lệnh (khuyến nghị cho đợt dài)

Một lệnh chạy hết 6 đợt trên, có checkpoint:

```bash
caffeinate -i .venv/bin/python run_report_plan.py --out results/report_streamlit
```

Thêm `--dry-run` để xem trước kế hoạch và thời gian ước tính mà không chạy. Kết quả mở được ở mục 4 của ứng dụng giống hệt cách bấm nút.

---

## 6. Bảng tổng hợp, kiểm định Wilcoxon và hình tiếng Việt

Streamlit không tính kiểm định thống kê. Sau khi có kết quả (cách A dùng `results/report`, cách B dùng `results/report_streamlit`), chạy:

```bash
.venv/bin/python analyze_report.py --root results/report
```

```bash
.venv/bin/python make_report_figures.py --root results/report
```

Mọi đầu ra nằm trong `<root>/report_tables/`:

| Tệp | Dùng cho báo cáo |
|---|---|
| `summary.csv` | Bảng 3.7 (dòng heuristic), Bảng 3.10 |
| `per_instance_<nhóm>.csv` | Số liệu MIP theo instance (gap, cận dưới) trong mục 3.3.3 |
| `wilcoxon.csv` | Bảng 3.12 và 3.14 |
| `ablation.csv` | Bảng 3.13 |
| `REPORT.md` | Tóm tắt tất cả các bảng trên |
| `verification_examples.png` | Hình 3.1 |
| `berth_liaoning_gga.png`, `crane_liaoning_gga.png` | Hình 3.2, 3.3 |
| `instances_n15.png`, `instances_n20.png`, `instances_n40.png` | Hình 3.5, 3.6, 3.7 |
| `conv_liaoning.png`, `conv_n40.png`, `box_n20.png` | Hình 3.4, 3.8, 3.9 |
| `boxplot_*.png`, `convergence_*.png` | Hình bổ sung, nhãn tiếng Anh |

Số thế hệ, số đánh giá và tỷ lệ cá thể khả thi trong Bảng 3.9 và 3.11 lấy từ các trường `generations`, `evaluations`, `feasible_evaluations` trong từng `run.json`. Bảng cuối trang ở mục 4 của ứng dụng có cột `generations` và `evaluations`; số cá thể khả thi chỉ có trong `run.json`.

## 7. Đối chiếu nhanh với báo cáo

Nếu chạy lại (cách B), Z trung bình nên gần các giá trị sau (giờ):

| Nhóm | Greedy | GA | GGA | MIP–HiGHS |
|---|---|---|---|---|
| Liêu Ninh 12 | 79,11 | ≈ 133 (dao động mạnh) | 79,11 | 79,11 (LIMIT) |
| 5 tàu | 21,58 | ≈ 23 | 21,43 | 21,42, OPTIMAL 10/10 |
| 10 tàu | 41,99 | ≈ 61 | 41,73 | 41,54 trên 8/10 instance |
| 15 tàu | 67,82 | ≈ 169 | 66,01 | – |
| 20 tàu | 101,17 | ≈ 385 | 95,14 | – |
| 40 tàu | 315,43 | ≈ 2.900 | 262,83 | có lời giải trên 2/10 instance |

Greedy là thuật toán xác định nên phải trùng **chính xác**; nếu khác, dữ liệu hoặc mã nguồn đã bị thay đổi. GGA thường lệch dưới 1%. GA dao động nhiều nhất. MIP phụ thuộc tốc độ máy, đặc biệt ở nhóm 10 và 40 tàu.

## 8. Lỗi thường gặp

| Hiện tượng | Cách xử lý |
|---|---|
| `Port 8501 is not available` | Tắt Streamlit đang chạy hoặc thêm `--server.port 8502` |
| Mục 4 báo "Chưa có kết quả batch" | Chưa có thư mục chứa `experiment.json` trong `results/`; chạy mục 3 hoặc lệnh trước |
| Chọn `gurobi` thì báo lỗi license | Máy này không có Gurobi; dùng `highs`. Báo cáo cũng dùng HiGHS cho mọi bảng tổng hợp |
| Đợt chạy dừng giữa chừng | Mở lại ứng dụng, nhập đúng tham số và tên đợt, nhấn nút lần nữa; phần đã xong được giữ |
| Số GA/GGA khác báo cáo một chút | Bình thường với ngân sách theo thời gian (đã nói ở đầu tài liệu) |
| Thư mục kết quả mới có mã khác `results/report` | Bình thường: mã thư mục phụ thuộc cả phiên bản mã nguồn |

---

## 9. Nguồn gốc từng hình và bảng trong báo cáo

Đã đối chiếu ngày 12/11/2026. Có ba loại nội dung, và chú thích trong báo cáo đã ghi rõ loại của từng hình.

**a) Kết quả chạy project.** Đây là số liệu thực nghiệm; mọi giá trị đều lấy từ tệp `run.json` trong `results/`.

| Trong báo cáo | Nguồn | Tái tạo bằng |
|---|---|---|
| Hình 3.1, Bảng 3.6 (cột HiGHS) | `results/report/verification/` | Mục 6 của ứng dụng; `make_report_figures.py` |
| Hình 3.2, 3.3, Bảng 3.8 | Lịch GGA của bộ 12 tàu; cả 10 seed cho cùng một lịch | Mục 2 của ứng dụng; `make_report_figures.py` |
| Hình 3.4–3.9 | `results/report/` (seed 0; 10 trường hợp × 10 seed) | Mục 4 của ứng dụng (nhãn tiếng Anh); `make_report_figures.py` |
| Bảng 3.7, 3.9–3.14 | `results/report/` (1.522 lượt chạy) | `analyze_report.py` |
| Bảng 3.6 (cột Gurobi), dòng Gurobi ở Bảng 3.7 | `results/verification_gurobi/`, `results/liaoning_gurobi_trial/` | Chỉ chạy lại được khi máy có Gurobi |
| Bảng 2.3 (số biến, số hàng) | Hàm `mip.build` | Đếm trực tiếp từ mô hình |

**b) Số liệu chép từ bài báo [1].** Đây không phải kết quả chạy: Bảng 3.15, 3.16 và Hình 3.10–3.12 (vẽ lại từ Bảng 6–8 của bài báo, số liệu nằm trong `data/paper_reference/`). Mục 5 của ứng dụng hiển thị các hình này với nhãn "PAPER TABLE DATA".

**c) Hình minh họa phương pháp.** Không phải kết quả: Hình 1.1, 2.1–2.6. Trong đó Hình 2.3 và 2.4 dùng giá trị ví dụ của bài báo; Hình 2.5 dùng số do báo cáo tự chọn để minh họa phép lai ghép và đột biến, và chú thích hình đã ghi điều này.

## 10. Kịch bản demo trong khoảng 10–15 phút

Không cần chạy lại 8 giờ. Toàn bộ kết quả trong báo cáo đã có sẵn trong `results/report/`; buổi demo kết hợp **mở kết quả đã chạy** với **chạy trực tiếp vài phép thử nhỏ** để chứng minh chương trình hoạt động thật. Thời gian dưới đây đo trên máy M1 Pro ngày 12/11/2026.

Chuẩn bị trước buổi demo: mở ứng dụng sẵn (mục 1 của tài liệu này) và chạy trước bước 5 một lần để lúc demo chỉ cần mở lại kết quả.

| Bước | Mục ứng dụng | Thao tác | Thời gian | Kết quả mong đợi |
|---|---|---|---|---|
| 1 | 6. Kiểm tra (5)–(8) | Solver `highs`, giới hạn `10`, nhấn **Chạy solver xác nhận** | dưới 1 giây | Cả bốn kiểm tra PASS (4, 6, 6 giờ, INFEASIBLE) — đúng Bảng 3.6 |
| 2 | 2. Lập lịch | `data/liaoning_12.json`; thuật toán `greedy, ga, gga, ga_greedy, ga_repair`; seed 0; `time`, 5 giây | khoảng 25 giây | Greedy, GGA, GA + khởi tạo tham lam = 79,114 giờ; GA cao hơn nhiều; lịch bến và lịch cẩu giống Hình 3.2–3.3 |
| 3 | 2. Lập lịch | `data/benchmark/n40_01.json`; `greedy, ga, gga`; seed 0; `time`, **10 giây** | khoảng 20 giây | Greedy 246,27; GGA khoảng 225; GA khoảng 3.800 giờ — cùng xu hướng Hình 3.7 và 3.8 |
| 4 | 4. Biểu đồ và bảng kết quả | Chọn `results/report/fb2963d024b6d90c` (40 tàu) hoặc `cdc022fc3ed71817` (20 tàu, có ablation) | vài giây | Bảng tổng hợp 10 trường hợp × 10 seed, biểu đồ so sánh, phân bố và hội tụ — chính là dữ liệu của báo cáo |
| 5 | 3. Thực nghiệm hàng loạt | Nhóm `20`; 3 instance; 3 seed; phương pháp `greedy, ga, gga, ga_greedy, ga_repair`; `time`, **3 giây**; tên đợt `demo` | khoảng 2 phút | 39 lượt, 0 lỗi; Z trung bình: GGA ≈ 97 < Greedy = GA + khởi tạo tham lam ≈ 103 < GA + Repair ≈ 115 ≪ GA ≈ 540 — cùng thứ tự với Bảng 3.13 |
| 6 | 5. Đối chiếu bài báo | Mở để so sánh | vài giây | Hình 5–7 của bài báo (dữ liệu tham khảo) |

Lưu ý khi trình bày:
- Ở bước 2 nếu chọn thêm `mip` với giới hạn 10 giây, HiGHS sẽ dừng ở LIMIT với lịch kém hơn (khoảng 129 giờ). Đây là minh họa tốt cho việc MIP cần nhiều thời gian; báo cáo dùng 300 giây.
- Bước 3 và 5 dùng ngân sách ngắn hơn báo cáo nên số liệu không trùng từng chữ số, nhưng thứ tự các phương pháp giữ nguyên. Nên nói rõ điều này khi demo.
- Nếu muốn bấm thật đợt đầy đủ, dùng lệnh ở mục 5.3 và để máy chạy qua đêm; ứng dụng chỉ cần mở kết quả ở mục 4.
