# Hướng dẫn thực nghiệm cho báo cáo Advanced Algorithms

## 1. Kết quả cần thu

Thực nghiệm được tổ chức để trả lời ba câu hỏi: mô hình có phản ánh đúng điều kiện phục vụ tàu không; GA/GGA trả về lịch hợp lệ với chất lượng như thế nào; và chi phí thay đổi ra sao khi tăng số tàu. Không đặt mục tiêu ép kết quả về 79,11 giờ hoặc mặc định GGA phải thắng mọi instance.

Gói bao gồm mã nguồn, 12 tàu, hai ví dụ, chín instance tổng hợp và đầu ra đã chạy để kiểm tra quy trình. Đầu ra mẫu chỉ là kiểm thử quy mô nhỏ, không thay thế thí nghiệm chính 10 lần chạy trên máy của người thực hiện.

## 2. Cài môi trường và kiểm tra đường dẫn

Làm theo README. Các lệnh PowerShell dưới đây đều chạy ở thư mục chứa `pyproject.toml`, sau khi cài `pip install -e .`. Không chạy từ bên trong `src`.

```powershell
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -m pip show port-scheduling-coursework
.\.venv\Scripts\python.exe -m port_scheduler --help
```

Phiên bản Python, NumPy, SciPy, hệ điều hành và mã băm nguồn được lưu trong `manifest.json` mỗi lần chạy. Khoảng phiên bản trong requirements cho phép cài trên Python 3.11; phiên bản thực tế đã kiểm thử có trong `docs/VERIFIED_RESULTS.md`. Sau khi cài thành công, có thể lưu môi trường của mình:

```powershell
.\.venv\Scripts\python.exe -m pip freeze > environment_local.txt
```

## 3. Kiểm chứng trước thực nghiệm chính

Chạy unittest và `verify-examples` như README. Kiểm tra bốn dòng `passed`. Mỗi thư mục ví dụ có `run.json` và `schedule.csv`; ví dụ vô nghiệm có lịch rỗng và mục tiêu null, không có giá trị giả bằng 0.

Nội dung đưa vào Chương 3 nên phân biệt:

- Kết quả phân tích: 4 giờ, 6 giờ và mâu thuẫn không gian của nhóm được in.
- Kết quả chương trình: tên backend, trạng thái OPTIMAL/INFEASIBLE, mục tiêu và validator.

Chỉ ghi “Gurobi xác nhận” nếu thực sự chạy `--solver gurobi`. Kiểm tra HiGHS đã có sẵn là bằng chứng HiGHS. `printed_core` là chẩn đoán nhóm (5)–(8); không tuyên bố đã chạy lại nguyên vẹn toàn bộ mô hình của bài báo.

## 4. Kiểm tra dữ liệu 12 tàu

Đối chiếu `data/liaoning_12_original.csv` với Bảng 1 nguồn. JSON sử dụng ETA 4, 12, 12, 16, 24, 24, 27, 45, 53, 57, 58, 60 giờ theo quy ước ngày:giờ:phút. L=1400 m, m=11 cẩu, QE=35 TEU/giờ.

Đây là cách diễn giải được công bố, chưa được xác nhận bằng mã nguồn tác giả. Nếu đổi giả định, lưu một instance có tên khác và chạy lại **tất cả** phương pháp. Không chỉnh ETA chỉ để khớp một kết quả kỳ vọng.

Chiều dài lấy trực tiếp làm chiều dài hiệu dụng. Nếu muốn thêm khoảng an toàn, tạo bộ dữ liệu mới, ghi rõ mức cộng và không gộp hai cấu hình vào cùng bảng thống kê.

## 5. Sinh và cố định dữ liệu tổng hợp

Chín instance đã được tạo với lệnh sau và lưu trong gói:

```powershell
.\.venv\Scripts\python.exe -m port_scheduler generate --counts 5 10 20 --instances 3 --seed 2026 --horizon 48 --out data/synthetic
```

Lệnh này ghi lại các tệp cùng tên nếu thư mục đã tồn tại. Giữ bản đầu vào cố định trước khi chạy so sánh. Để thử một horizon khác, dùng thư mục và tên cấu hình mới; không trộn kết quả hai horizon dưới cùng tên instance.

Quy tắc: tỷ lệ tàu 40/40/20; chiều dài và khối lượng đều rời rạc theo khoảng tham khảo; ETA đều liên tục 0–48 giờ, làm tròn 0,001 giờ. Đây không phải mô tả phân phối gốc của tác giả.

## 6. Thực nghiệm chính theo cùng thời gian

Khởi đầu 5 giây/lần cho GA và GGA:

```powershell
.\.venv\Scripts\python.exe run_experiments.py --instances data/liaoning_12.json --algorithms ga gga --seeds 0 1 2 3 4 5 6 7 8 9 --seconds 5 --out results/main_12
.\.venv\Scripts\python.exe run_experiments.py --instances data/synthetic --algorithms ga gga --seeds 0 1 2 3 4 5 6 7 8 9 --seconds 5 --out results/main_synthetic
```

Lệnh thứ hai có 9 instance × 2 thuật toán × 10 seed × 5 giây = khoảng 900 giây tính toán lõi, cộng overhead. Để chạy thử nhanh, chọn một file và ba seed trước. Có thể tăng lên 30 hoặc 60 giây, nhưng dùng thư mục kết quả riêng cho từng ngân sách.

Khởi tạo, giải mã và Repair đều nằm trong thời gian đo. Vẽ hình, lưu tệp và khởi động tiến trình nằm ngoài `wall_seconds` của thuật toán. Ngân sách là giới hạn thực thi có thể vượt nhẹ; so sánh cả thời gian đo thực tế.

Hai cấu hình có một incumbent tuần tự chung. Điều này bảo đảm đã có lời giải hợp lệ nhưng không đồng nghĩa các quần thể đầu giống nhau. GA dùng khởi tạo tuần tự khả thi ngẫu nhiên; GGA dùng khởi tạo qua decoder tham lam. Xem METHOD.md trước khi giải thích chênh lệch.

## 7. Thực nghiệm MIP

Ưu tiên các instance 5 tàu:

```powershell
.\.venv\Scripts\python.exe -m port_scheduler run --instance data/synthetic/synthetic_n5_01.json --algorithm mip --solver highs --seconds 30 --out results/exact_n5_01 --plot
.\.venv\Scripts\python.exe -m port_scheduler run --instance data/synthetic/synthetic_n5_02.json --algorithm mip --solver highs --seconds 30 --out results/exact_n5_02
.\.venv\Scripts\python.exe -m port_scheduler run --instance data/synthetic/synthetic_n5_03.json --algorithm mip --solver highs --seconds 30 --out results/exact_n5_03
```

Nếu có Gurobi, thay `--solver highs` bằng `--solver gurobi` và lưu thư mục khác. Có thể chạy đồng ngân sách 5 giây như heuristic để so sánh nguồn lực, rồi thêm thí nghiệm 30–300 giây nhằm tìm mốc tối ưu. **Không gộp hai ngân sách thành một điều kiện so sánh.**

Không phải mọi instance 5 tàu đều được chứng minh tối ưu trong 5 hay 30 giây. Khi status LIMIT và có incumbent, chỉ khẳng định có nghiệm khả thi. Khi LIMIT mà lịch rỗng, ghi chưa tìm được incumbent trong ngân sách, không kết luận mô hình vô nghiệm.

## 8. Chế độ cùng số thế hệ tùy chọn

```powershell
.\.venv\Scripts\python.exe -m port_scheduler run --instance data/liaoning_12.json --algorithm ga --generations 100 --seed 0 --out results/generation100_ga
.\.venv\Scripts\python.exe -m port_scheduler run --instance data/liaoning_12.json --algorithm gga --generations 100 --seed 0 --out results/generation100_gga
```

Không thêm `--seconds` nếu muốn chế độ chỉ theo thế hệ. Nếu đưa cả hai, dừng khi chạm điều kiện đầu tiên, Mutation dùng tiến trình thời gian; đó là một cấu hình khác. Quần thể mặc định 40; pc=0,8, pm=0,2, beta=0,15. beta, pm trên từng gene và Elitism là các lựa chọn triển khai được công bố, không phải tham số gốc đã được xác nhận.

Chế độ số thế hệ hỗ trợ kiểm tra tính lặp lại cùng seed; chế độ thời gian có thể tạo kết quả khác giữa hai lần cùng seed vì số đánh giá thay đổi theo tốc độ máy.

## 9. Đọc từng đầu ra

### run.json

| Trường | Cách hiểu |
|---|---|
| objective | Tổng flow time, giờ; null nếu chưa có lịch khả thi |
| feasible | Kết quả kiểm tra lịch độc lập |
| validation_errors | Danh sách lỗi; phải rỗng với lịch hợp lệ |
| status | FEASIBLE cho heuristic; trạng thái solver cho MIP |
| proven_optimal | Chỉ true nếu solver báo tối ưu và lịch qua kiểm tra |
| lower_bound | Cận của Z sau khi trừ hằng ETA, nếu solver cung cấp |
| flow_relative_gap | (Z-bound)/abs(Z), dạng tỷ lệ, không phải phần trăm |
| wall_seconds | Thời gian thực đo, không phải CPU time |
| build_seconds | Thời gian dựng ma trận MIP |
| optimize_seconds | Thời gian phần backend MIP |
| generations | Số thế hệ đã bắt đầu; thế hệ cuối có thể chưa đủ con khi hết thời gian |
| evaluations | Số cá thể đã đánh giá; không tính incumbent chung ban đầu |
| history | Các lần cải thiện incumbent, không phải mọi đánh giá |

Gap của solver trên tổng completion time và gap của Z có mẫu số khác nhau khi ETA không bằng 0. Đọc `flow_relative_gap` nếu báo cáo mục tiêu Z. Heuristic có `proven_optimal: false` kể cả khi tình cờ trùng nghiệm tối ưu.

### schedule.csv

Mỗi dòng là một tàu: ETA, bắt đầu, kết thúc, thời lượng, chờ, flow time, vị trí, chiều dài và danh sách cẩu. Kiểm tra `waiting=start-eta`, `flow_time=end-eta`. Danh sách cẩu được giữ cố định trong toàn bộ khoảng làm hàng.

### summary.csv

Các cột: instance, phương pháp, backend, ngân sách, số lần chạy, số lần khả thi, tỷ lệ khả thi, best, mean, std mẫu, thời gian trung bình, số lần solver chứng minh tối ưu. `std_sample` để trống nếu có ít hơn hai lần khả thi, không đặt bằng 0 giả tạo.

Trung bình chất lượng chỉ tính các lần khả thi. Nếu tỷ lệ khả thi thấp, phải trình bày cùng mean để tránh kết luận sai. Các chẩn đoán printed_core được loại khỏi bảng so sánh hiệu năng.

Lưu mỗi cấu hình trong một thư mục mới. Chạy lại cùng đường dẫn sẽ ghi đè; `summarize` quét tất cả run.json bên dưới root, nên không đặt một bản sao của cùng lần chạy trong cây rồi tính hai lần.

```powershell
.\.venv\Scripts\python.exe -m port_scheduler summarize --root results/main_12 --out results/main_12/summary.csv
```

## 10. Vẽ và kiểm tra hình

```powershell
.\.venv\Scripts\python.exe -m port_scheduler plot --instance data/liaoning_12.json --run results/liaoning12_gga_seed0/run.json --out results/liaoning12_gga_seed0
```

Hình bến dùng trục ngang thời gian và trục dọc vị trí bến. Hai hình chữ nhật có thể chung khoảng thời gian nếu tách vị trí, hoặc chung vị trí nếu tách thời gian. Hình cẩu dùng trục dọc ID cẩu; một hàng không được có hai tàu giao nhau theo thời gian. Phải xem cả hai hình vì hình bến hợp lệ chưa đủ xác nhận cẩu.

## 11. Viết kết quả vào báo cáo

1. Giữ bảng kết quả tài liệu [1] ở mục mốc tham chiếu, có dẫn nguồn.
2. Thêm bảng riêng “Kết quả thực nghiệm của nghiên cứu” từ summary.csv trên máy mình.
3. Ghi rõ dữ liệu, ETA, chiều dài hiệu dụng, tham số, ngân sách, seed, môi trường và backend.
4. Phân tích ít nhất một instance GGA tốt hơn GA và một instance không tốt hơn, nếu xuất hiện; không chọn lọc chỉ các trường hợp thuận lợi.
5. Chỉ tính gap tới tối ưu khi có chứng nhận; incumbent MIP chưa tối ưu là mốc tham chiếu.
6. Báo cáo các khác biệt decoder nêu trong METHOD.md. Không gọi đây là tái lập chính xác thuật toán gốc.

Mẫu diễn đạt sau khi có dữ liệu: “Trên instance X, trong ngân sách Y giây và R lần chạy, cấu hình GGA đạt trung bình ..., độ lệch chuẩn ..., tỷ lệ khả thi .... Kết quả so sánh phản ánh đồng thời khác biệt khởi tạo và xử lý khả thi.” Điền số thật từ đầu ra; không dùng lại số của bài báo làm kết quả của chương trình.

Kết luận phải bám theo từng bảng và từng chỉ tiêu. Nếu GA có best thấp hơn GGA hoặc hai phương pháp bằng nhau, giữ nguyên kết quả và phân tích thay vì chỉ chọn các trường hợp có lợi. Việc GGA giữ một lịch Greedy nền giúp bảo toàn lịch đó, không chứng minh tối ưu toàn cục.

## 12. Lỗi thường gặp

- `No module named port_scheduler`: chưa cài `pip install -e .` hoặc dùng sai Python.
- Không có `gurobipy`: cài extra và cấu hình license; có thể chọn HiGHS nhưng ghi đúng backend.
- Gurobi báo license/quy mô: không sửa kết quả thành HiGHS; chọn lại backend bằng lệnh khác và thư mục khác.
- `LIMIT` với objective null: tăng thời gian hoặc giảm quy mô; không gọi vô nghiệm.
- Kết quả khác kết quả mẫu: chế độ thời gian phụ thuộc tốc độ; kiểm tra seed, dữ liệu và METHOD trước.
- Không đạt 79,11 giờ: mô hình, decoder và quy ước dữ liệu chưa được xác nhận là bản gốc; không ép khớp con số.
- Thời gian thực cao hơn budget nhẹ: thuật toán/solver cần hoàn tất bước đang xử lý; đọc wall_seconds. Nếu vượt lớn, kiểm tra máy và độ phức tạp instance.

## 13. Thứ tự hoàn thành trong một đến hai tuần

Ngày 1–2: môi trường, test, ví dụ, đọc mô hình. Ngày 3–4: chạy 12 tàu và xem lịch. Ngày 5–7: chạy bộ chính 10 seed, MIP nhỏ, tổng hợp và cập nhật Chương 3. Tuần thứ hai: phân tích các kết quả khác kỳ vọng, rà soát mô tả decoder và chuẩn bị bảo vệ.

## 14. Chạy toàn bộ kế hoạch báo cáo bằng một lệnh

`run_report_plan.py` gom các mục 3–7 thành một kế hoạch cố định, có checkpoint (chạy lại sẽ bỏ qua lần chạy đã xong):

| Pha | Dữ liệu | Thuật toán | Ngân sách heuristic | MIP |
|---|---|---|---|---|
| verify | example_100/200 | MIP corrected/printed_core | – | 10 s |
| liaoning | liaoning_12 | greedy, ga, gga, ga_greedy, ga_repair, mip | 5 s | 300 s |
| main | n05 / n10 / n15 / n20 / n40 (10 instance mỗi nhóm) | greedy, ga, gga (+ mip cho 5, 10, 40) | 2 / 5 / 10 / 20 / 60 s | 300 / 300 / – / – / 60 s |
| ablation | n15, n20 (10 instance) | ga, gga, ga_greedy, ga_repair | 10 / 20 s | – |

```bash
.venv/bin/python run_report_plan.py --dry-run
.venv/bin/python run_report_plan.py
.venv/bin/python analyze_report.py --root results/report
```

Mỗi thuật toán ngẫu nhiên chạy 10 seed. `--solver gurobi` đổi backend MIP, `--scale 0.05` chạy thử nhanh với ngân sách thu nhỏ (chỉ để kiểm tra luồng, không dùng số liệu), `--phases` chọn pha. Thời gian xấu nhất khoảng 9 giờ.

`analyze_report.py` ghi vào `results/report/report_tables/`: `per_instance_<nhóm>.csv` (mean/min/std/thời gian; MIP gồm Z, cận dưới, gap, trạng thái), `summary.csv`, `ablation.csv`, `wilcoxon.csv` (kiểm định dấu-hạng hai phía trên Z trung bình theo instance), `boxplot_*.png`, `convergence_*.png` và `REPORT.md`. Wilcoxon bỏ các cặp hòa; cần ít nhất 6 cặp khác nhau thì p mới có thể nhỏ hơn 0,05.
