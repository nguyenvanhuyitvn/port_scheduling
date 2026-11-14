# Hướng dẫn ứng dụng Streamlit và thực nghiệm

## 1. Cài đặt

Yêu cầu Python 3.11 trở lên. Giải nén ZIP, mở terminal tại thư mục chứa app.py và pyproject.toml.

Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m streamlit run app.py
```

macOS / Linux:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e .
.venv/bin/python -m streamlit run app.py
```

Mở địa chỉ localhost mà Streamlit thông báo, thường là http://localhost:8501. Nhấn Ctrl+C trong terminal để dừng. Nếu dùng môi trường đã kích hoạt, có thể thay đường dẫn Python bằng `python` trong các lệnh tiếp theo.

Gurobi là tùy chọn:

```bash
python -m pip install -e ".[gurobi]"
```

Cần license Gurobi phù hợp kích thước mô hình. Restricted license có thể giải các ví dụ nhỏ nhưng từ chối nhóm lớn. Chương trình ghi lỗi riêng, không tự thay Gurobi bằng HiGHS và không gán kết quả giả.

## 2. Dữ liệu đầu vào

`data/liaoning_12.json`: 12 tàu chép từ Table 1, bến 1.400 m, 11 cẩu, 35 TEU/h/cẩu. `liaoning_12_original.csv` giữ ETA gốc. Quy ước ngày:giờ:phút là giả định cần xác nhận: ngày 1 lúc 04:00 → 4 giờ; ngày 2 lúc 03:00 → 27 giờ. Không cộng safety margin chưa được cung cấp.

`data/benchmark/`: 50 instance tự sinh, mỗi nhóm 5, 10, 15, 20 và 40 tàu có 10 instance. Cấu hình: 5/10 tàu dùng 1000 m–10 cẩu; 15/20 tàu dùng 1200 m–12 cẩu; 40 tàu dùng 1500 m–15 cẩu. Tỷ lệ tàu nhỏ/vừa/lớn là 40/40/20. Các khoảng chiều dài, khối lượng và số cẩu theo Table 3. ETA tự sinh Uniform[0,48] giờ, làm tròn 0,001 giờ; đây là lựa chọn của project, không phải dữ liệu gốc tác giả. Seed dữ liệu 2026. `prepare_data.py` tái tạo xác định bộ này.

Mỗi instance có JSON đầy đủ và CSV sáu cột: `id,eta,length,workload,q_min,q_max`. ETA là giờ số thực; length là m; workload là TEU; q là số nguyên. CSV không giữ cấu hình cảng; khi upload phải nhập thêm chiều dài bến, số cẩu và năng suất trên giao diện. `data/instances_index.csv` lưu chỉ mục cấu hình.

Mục 1 cho phép chọn mẫu, upload JSON/CSV hoặc tạo mới; chỉnh trực tiếp bằng bảng, thêm/xóa tàu, kiểm tra và tải JSON/CSV. Mục 2 chỉ dùng dữ liệu tùy chỉnh sau khi nhấn kiểm tra ở mục 1. JSON là định dạng nên dùng để tái lập đầy đủ.

## 3. Chạy một lịch

Chọn mục 2; chọn dữ liệu, các phương pháp Greedy/GA/GGA/MIP, seed, ngân sách và tham số. Mặc định Population=40, pc=0.8, pm=0.2. Mode time giới hạn wall time; mode generations chạy đủ số thế hệ, không có giới hạn wall time. Greedy chỉ xây dựng một lịch, không chạy tiến hóa.

Đầu ra hiển thị Z, wall time, trạng thái, tính khả thi và proven_optimal; bảng gồm ETA, start, end, duration, waiting, flow_time, position, length và cranes. Tổng thời gian ở cảng bằng tổng waiting cộng tổng duration. Thời điểm hoàn thành cuối là max(end), khác mục tiêu Z. Không có due date nên không tự tạo lateness.

Lịch bến thể hiện mỗi tàu bằng hình chữ nhật trên trục thời gian–vị trí bến. Lịch cẩu thể hiện từng crane ID theo thời gian. Khối cẩu cố định suốt lần làm hàng và gồm các chỉ số liên tiếp. Validator kiểm tra đủ tàu, ETA, biên bến, khối lượng, số lượng cẩu, chồng lấn và thứ tự cẩu. Nó không mô phỏng chuyển động vật lý của cẩu giữa hai tác vụ.

Download ZIP lưu toàn bộ lịch CSV, run.json, history.csv, manifest.json, hình và input. Chương trình không khẳng định heuristic là tối ưu đã chứng minh.

## 4. Toàn bộ ma trận thử nghiệm

Mục 3 hỗ trợ chọn cả năm nhóm, tối đa 10 instance/nhóm và 10 seed/instance, thêm bộ 12 tàu, chọn solver. Mỗi tổ hợp dữ liệu–phương pháp–seed được lưu riêng; mỗi cấu hình ngân sách và mã nguồn có ID riêng. Nhấn chạy lại để tiếp tục checkpoint. Một lần solver lỗi được lưu trong error.json và được thử lại ở lần tiếp tục; kết quả lỗi không được thay bằng số liệu khác.

Batch có thể mất nhiều giờ. Dùng CLI để chạy dài; ứng dụng có thể mở lại các kết quả tại mục 4. Không chạy nhiều batch đồng thời nếu cần so sánh thời gian công bằng.

Kiểm tra nhanh đầy đủ cấu trúc ma trận:

```bash
python benchmark.py --preset quick --include-real --out results/my_quick
```

Quick dùng 0,25 giây/heuristic; chỉ dùng kiểm tra đường chạy và đầu ra, không kết luận chất lượng tìm kiếm từ ngân sách này. Greedy vẫn hoàn tất xây dựng lịch. GGA có thể chưa khởi tạo đủ Population=40 trong thời gian ngắn, đặc biệt nhóm 40 tàu; xem evaluations/generations trong run.json.

So sánh cùng 100 thế hệ cho nhóm nhỏ/vừa, theo thông số thuật toán bài báo:

```bash
python benchmark.py --preset paper-generations --groups 5 10 15 20 --include-real --algorithms greedy ga gga --out results/generations_100
```

So sánh cùng thời gian 60 giây cho nhóm 40 tàu:

```bash
python benchmark.py --preset paper-time --groups 40 --algorithms greedy ga gga mip --solver gurobi --out results/large_60s
```

MIP đối chứng nhóm nhỏ (tối đa 3600 giây/instance là lựa chọn tái lập của project):

```bash
python benchmark.py --preset paper-generations --groups 5 10 --algorithms mip --solver gurobi --out results/mip_small
```

Có thể thay gurobi bằng highs, nhưng phải đổi tên phương pháp trong báo cáo cho đúng. Solver và heuristic ở các cấu hình khác nhau được giữ thành các đợt riêng; không lấy số liệu hai môi trường hoặc ngân sách khác nhau để tính chung Mean/Std. Preset paper-time mặc định 5 giây cho nhóm <=20 và 60 giây cho nhóm 40; 5 giây là ngân sách so sánh của project, không phải một giới hạn được bài báo quy định cho mọi nhóm. Muốn tái hiện mốc 100 thế hệ, dùng paper-generations.

## 5. Biểu đồ

Mục 4: đường Best/Mean theo instance (tương ứng kiểu Figure 5–7), phân bố chất lượng tương đối, thời gian trung bình và đường hội tụ incumbent theo giây hoặc thế hệ. Chất lượng tương đối là % cao hơn nghiệm khả thi tốt nhất đã ghi nhận trên cùng dữ liệu/cấu hình, KHÔNG phải optimality gap. Dữ liệu không khả thi không góp vào Best/Mean/Std; tỷ lệ khả thi và lỗi được báo riêng. Std dùng mẫu ddof=1; một lần chạy không có Std.

Mục 5: dựng lại Figure 5–7 từ số liệu Table 6–8 của bài báo; đánh dấu PAPER TABLE DATA. Tables 2/4/5 cũng có CSV đối chiếu. Các số liệu công bố không bị đưa vào kết quả chạy của project.

Figures 1–4: project vẽ minh họa tương đương về ý nghĩa, không chép nguyên hình: biến không gian–thời gian, năm gene chuẩn hóa của bản cài đặt, lịch giải mã thực tế (hai hình bến/cẩu) và ví dụ Arithmetic Crossover/Mutation. Hình toán tử dùng số minh họa công khai, không được trình bày là trace của một generation thực tế. Các khác biệt encoding/decoder so với mô tả tác giả được giữ trong METHOD.md.

Mỗi lần batch tự xuất PNG/PDF so sánh và phân bố ở charts/. Mục 4 tạo thêm hình hội tụ từ history.csv. Các hình tham khảo được xuất sẵn tại paper_figures/. Các hình kết quả của project nằm riêng trong results/.

## 6. Kiểm tra mô hình

Mục 6 chạy hai ví dụ bến 200 m và 100 m với corrected/printed_core. Kỳ vọng suy luận: 4, 6, 6 giờ và INFEASIBLE. PASS chỉ khi solver xác nhận trạng thái tương ứng, không chỉ vì incumbent gần kỳ vọng. printed_core cô lập lõi logic (5)–(8), không tái hiện toàn bộ mô hình in. Không dùng nó làm đối chứng hiệu năng chính.

## 7. Cấu trúc và luồng

app.py: bảy màn hình Streamlit. benchmark.py: batch CLI. run_report_plan.py: chạy toàn bộ kế hoạch thực nghiệm của báo cáo (kiểm chứng, Liêu Ninh, 5 nhóm, ablation). analyze_report.py: bảng theo instance, tổng hợp, Wilcoxon, ablation, boxplot và hội tụ. prepare_data.py: dữ liệu. src/port_scheduler/experiments.py: thực thi, checkpoint, thống kê và ZIP. charts.py: hình và đồ thị. domain.py: mô hình dữ liệu. heuristics.py: Greedy/GA/GGA và hai biến thể ablation ga_greedy, ga_repair. mip.py: ma trận MIP và backend. validation.py: validator độc lập. cli.py: CLI gốc, lưu kết quả và manifest. tests/: kiểm tra thuật toán, batch và giao diện. data/: input và bảng tham khảo. results/: các lần thực chạy. docs/: phương pháp và hướng dẫn.

Luồng: nhập → kiểm tra dữ liệu → chọn thuật toán → giải → validator → lưu lịch và manifest → tổng hợp → biểu đồ → download. Batch lặp luồng theo instance–algorithm–seed và có checkpoint.

## 8. Giới hạn diễn giải

Đây là cài đặt độc lập dựa trên tài liệu, không phải mã nguồn tác giả. Có thể tái hiện cấu trúc thử nghiệm nhưng chưa chứng minh tương đương decoder gốc; không hứa trùng số công bố trên synthetic tự sinh. MIP dùng mô hình nhất quán đã hiệu chỉnh. GGA gồm Greedy warm start và Repair; nếu chỉ giữ nghiệm khởi tạo thì chưa chứng minh đóng góp của tiến hóa. Đọc history.csv trước khi kết luận. Đóng góp riêng của Greedy Initialization và Repair chỉ được kết luận từ các lần chạy ablation (ga_greedy, ga_repair) cùng ngân sách; kết quả đã chạy cho nhóm 15 và 20 tàu nằm trong EXECUTION_STATUS.md.

Gurobi LIMIT không đồng nghĩa INFEASIBLE. Không có incumbent không chứng minh vô nghiệm. Lower bound và gap được báo theo flow time khi có; không nhầm gap trên sum completion của backend. Wall time bao gồm dựng mô hình, loại phần vẽ/lưu file; CPU time chưa được đo riêng. Thời gian chạy phụ thuộc máy, phần mềm và tải nền.

Nguồn: bài báo được cung cấp, DOI 10.21203/rs.3.rs-9235581/v1. Không cung cấp lại bản PDF tác giả trong gói mã nguồn. Thông tin các lần chạy được kiểm chứng của phiên bản này nằm trong EXECUTION_STATUS.md.
