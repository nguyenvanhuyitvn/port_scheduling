# Trạng thái thực nghiệm đã thực chạy

## Đợt chạy đầy đủ cho báo cáo — 11–12/11/2026

Lệnh: `run_report_plan.py` (mặc định), rồi `run_report_plan.py --phases ablation` sau khi mở rộng ablation lên 10 instance. Tổng hợp: `analyze_report.py --root results/report`. Toàn bộ run.json, bảng và hình nằm trong `results/report/`; log trong `results/report_full_run.log` và `results/report_ablation_run.log`.

- Máy: Apple M1 Pro, 16 GB RAM, macOS 15.6.1 arm64; Python 3.15.0, numpy 2.5.4, scipy 1.18.1 (HiGHS), matplotlib 3.11.2. Không có gurobipy trong môi trường này: **mọi MIP của đợt này là HiGHS**, một luồng.
- 1.522 lần chạy thuật toán + 4 ca kiểm chứng mô hình, 0 lỗi. Mọi lịch tính vào bảng đều qua validator độc lập. Ngân sách là wall time, các tác vụ chạy tuần tự.
- Kiểm chứng: corrected/printed_core với bến 200 m và 100 m cho 4 giờ, 6 giờ, 6 giờ, INFEASIBLE — cả bốn PASS.

Z trung bình (giờ) trên các instance; std là độ lệch chuẩn trung bình giữa 10 seed; % là mức trên Z tốt nhất đã biết của instance (không phải gap tối ưu).

| Nhóm | Ngân sách heuristic / MIP | Greedy | GA | GGA (std, %) | MIP HiGHS |
|---|---|---|---|---|---|
| Liêu Ninh 12 | 5 s / 300 s | 79,11 | 133,32 | 79,11 (0,00; 0,00%) | 79,11, LIMIT, cận dưới 50,64 |
| 5 tàu | 2 s / 300 s | 21,58 | 22,98 | 21,43 (0,04; 0,06%) | 21,42, 10/10 OPTIMAL |
| 10 tàu | 5 s / 300 s | 41,99 | 61,10 | 41,73 (0,13; 0,41%) | 41,54 trên 8/10 instance có incumbent, LIMIT, gap 9–17% |
| 15 tàu | 10 s / – | 67,82 | 169,20 | 66,01 (0,26; 0,29%) | không chạy |
| 20 tàu | 20 s / – | 101,17 | 384,91 | 95,14 (0,71; 0,45%) | không chạy |
| 40 tàu | 60 s / 60 s | 315,43 | 2937,84 | 262,83 (7,06; 4,19%) | incumbent trên 2/10 instance, gap khoảng 98% |

Ablation (10 instance × 10 seed mỗi nhóm):

| Cấu hình | 15 tàu | 20 tàu |
|---|---|---|
| GA | 169,20 | 384,91 |
| GA + Repair (`ga_repair`) | 74,65 | 114,55 |
| GA + khởi tạo tham lam (`ga_greedy`) | 67,70 | 100,68 |
| GGA | 66,01 | 95,14 |

Wilcoxon dấu-hạng hai phía trên Z trung bình theo instance (`report_tables/wilcoxon.csv`):

- GGA tốt hơn GA ở 10/10 instance của mọi nhóm, p = 0,002.
- GGA tốt hơn Greedy: 15 tàu 6 thắng/4 hòa, p = 0,031; 20 tàu và 40 tàu 10/10, p = 0,002. Ở 5 và 10 tàu phần lớn hòa; ở bộ Liêu Ninh GGA giữ đúng lịch Greedy 79,114 giờ.
- `ga_greedy` và `ga_repair` đều tốt hơn GA ở 10/10 instance, p = 0,002 cho cả hai nhóm.
- GGA tốt hơn `ga_repair` 10/10, p = 0,002 (cả hai nhóm). GGA so với `ga_greedy`: 20 tàu 10/10, p = 0,002; 15 tàu 5 thắng/5 hòa, không thua, p = 0,0625 vì Wilcoxon bỏ cặp hòa.

Giới hạn: dữ liệu tổng hợp tự sinh; MIP chỉ HiGHS (Gurobi từng chứng minh tối ưu 79,114 giờ cho bộ Liêu Ninh trong khoảng 0,6 s, xem mục Gurobi bên dưới); một seed MIP; ngân sách theo thời gian phụ thuộc tốc độ máy.

Các mục dưới đây là đợt kiểm tra nhanh ngày 07/11/2026 với phiên bản mã trước khi thêm ablation; giữ lại làm lịch sử.

## Phân biệt phạm vi cài đặt và phạm vi đã chạy

Đã cài đặt trọn luồng nhập liệu–lập lịch–validator–lưu kết quả–batch–biểu đồ cho các nhóm trong bài báo. Chưa thực chạy toàn bộ ma trận dài 100 thế hệ/60 giây × 10 instance × 10 seed. Có đầy đủ preset để tiếp tục trên máy có thời gian và license phù hợp. Không được mô tả quick-validation là tái lập đầy đủ kết quả tác giả.

## Kiểm chứng phần mềm

- 19 unittest PASS, gồm 15 test lõi, 3 test batch/thống kê/input và 1 test Streamlit navigation + chạy lịch thực tế.
- Đã kiểm tra lại cả bảy màn hình với AppTest sau khi có dữ liệu kết quả và biểu đồ. AppTest kiểm tra luồng widget/thực thi; không khẳng định đã kiểm thử mọi trình duyệt hoặc Windows.
- Bốn trường hợp corrected/printed_core PASS trên cả HiGHS và Gurobi: 4 giờ, 6 giờ, 6 giờ, INFEASIBLE.
- Validator độc lập đã kiểm tra lại 1552 lịch được lưu và báo khả thi; không phát hiện vi phạm. Mã băm engine của tất cả manifest khớp source đi kèm. AUDIT.json ghi chi tiết. Các lịch trống vì solver hết ngân sách không được tính như lịch khả thi.

## Ma trận kiểm tra nhanh

- 50 instance tự sinh: 10 instance mỗi nhóm 5/10/15/20/40 tàu, cùng bộ Liêu Ninh 12 tàu.
- 10 seed cho GA và GGA trên mỗi instance: 1.020 lần heuristic ngẫu nhiên; 51 lần Greedy; 50 lần MIP HiGHS với giới hạn 1 giây.
- Tổng 1121 kết quả trong verified_quick, 1097 kết quả có lịch khả thi. Solver không có incumbent trong 1 giây được giữ nguyên trạng thái, không thay số.
- Heuristic quick dùng 0,25 giây/lần, Population=40. Ngân sách này có thể hết ngay trong khởi tạo; xem evaluations/generations ở từng run.json. Không dùng nó để rút kết luận chất lượng thuật toán như bài báo.
- Các lượt kiểm tra phần mềm có thời điểm chạy đồng thời với hoạt động kiểm thử khác; thời gian kèm theo không được xem là benchmark phần cứng được kiểm soát.

## Gurobi thực tế

- Đã cài và chạy Gurobi với restricted size-limited license trong môi trường tạo gói.
- 20 mô hình ở các nhóm 5/10 tàu có kết quả solver; 17 lần đã chứng minh tối ưu trong ngân sách 1 giây.
- Đã chạy thêm Greedy/GA/GGA trên cùng nhóm với cấu hình quick tương ứng để vẽ so sánh trong verified_gurobi. Tổng 440 run.json trong đợt này.
- 30 mô hình thuộc các nhóm 15/20/40 bị từ chối do giới hạn kích thước license. Có error.json và log đầy đủ, không thay Gurobi bằng HiGHS ngầm.
- Bộ Liêu Ninh: Gurobi cho status OPTIMAL, Z=79.114285714286 giờ, proven_optimal=True, wall time=0.570341 giây với giới hạn 5 giây. Kết luận tối ưu chỉ áp dụng mô hình đã hiệu chỉnh, dữ liệu và giả định ETA hiện tại; không xác nhận tương đương nguyên bản tác giả.

## Thử nghiệm dài một trường hợp 40 tàu

Đã chạy n40_01, seed=0, ngân sách 60 giây cho mỗi GA/GGA và MIP HiGHS; Greedy hoàn tất xây dựng một lịch. Đây là một trường hợp, chưa phải 10 instance × 10 seed.

```csv
algorithm,objective,wall_seconds,status,proven_optimal
ga,3499.05041813792,60.00035392300015,FEASIBLE,False
gga,232.58280952380952,60.000032152999665,FEASIBLE,False
greedy,246.26557142857146,0.004917475000183913,FEASIBLE,False
mip,,60.0210855940004,LIMIT,False
```

## Bộ 12 tàu theo 100 thế hệ

results/liaoning_showcase chứa Greedy, GA/GGA 100 thế hệ, MIP HiGHS giới hạn 5 giây, các hình minh họa và hội tụ. GGA giữ lại lịch Greedy 79,114285714 giờ trong lần đã chạy; không quy kết cải thiện này cho tiến hóa. Gurobi được lưu riêng tại liaoning_gurobi_trial vì khác backend/ngân sách với đợt showcase.

## Hình và dữ liệu

- Figure 1–4: minh họa tương đương do project tự dựng, riêng encoding năm gene là lựa chọn triển khai. Figure 3 dùng hai ảnh lịch bến/cẩu thực tế.
- Figure 5–7: có hai nguồn tách biệt. paper_figures/ dựng từ Table 6–8 của tác giả; results/*/charts/ dùng kết quả chương trình. Không gộp hai nguồn.
- 51 input chính có JSON + CSV và index cấu hình. Synthetic tự sinh theo Table 3, không phải instance gốc tác giả.
- Các hình đã được mở kiểm tra chữ, chú giải và trục. Export gồm PNG/PDF cho so sánh/phân bố; có thêm hội tụ seed đầu cho mỗi instance.
- Wall time là thời gian thực trôi qua; không gọi là CPU time. Không báo lateness vì input không có hạn chót.

Môi trường, phiên bản thư viện, source/input hash và ngân sách cụ thể được lưu trong manifest.json/run.json. Khác biệt thuật toán và giả định được công bố trong METHOD.md. Ứng dụng Streamlit là bản 2.0; engine kế thừa giữ __version__ 1.0.0 và được nhận diện chính xác bằng source hash.
