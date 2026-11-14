# Đọc dữ liệu trước khi chạy

Input chính: liaoning_12.json / .csv và benchmark/n05_01 ... n40_10.json / .csv. Mỗi nhóm có 10 instance. instances_index.csv ghi cấu hình cảng cho từng CSV. JSON giữ toàn bộ cấu hình nên ưu tiên khi chia sẻ hoặc tái lập.

CSV tàu có sáu cột: id,eta,length,workload,q_min,q_max. ETA là giờ số thực; length là mét; workload là TEU; q_min/q_max là số nguyên. Cấu hình productivity là TEU/h/cẩu. Không nhập ETA dạng ngày:giờ:phút trực tiếp vào cột eta. Nếu dùng dữ liệu Liêu Ninh, chuyển đổi theo giả định mô tả trong metadata: ngày 1 lúc 04:00 → 4, ngày 2 lúc 03:00 → 27. liaoning_12_original.csv giữ chuỗi gốc để đối chiếu.

benchmark/: dữ liệu tự sinh theo khoảng Table 3, seed 2026, ETA Uniform[0,48] giờ. Không phải bộ synthetic gốc tác giả. Cấu hình 5/10 tàu: 1000 m, 10 cẩu; 15/20: 1200 m, 12 cẩu; 40: 1500 m, 15 cẩu; năng suất 35. Tỷ lệ ba nhóm tàu là 40/40/20.

example_100.json / example_200.json: kiểm tra mô hình, không đưa vào bảng đánh giá hiệu năng chính.

synthetic/: dữ liệu nhỏ của bản CLI cũ, được giữ để tương thích. Bộ thử nghiệm mới dùng benchmark/.

paper_reference/: số liệu công bố để vẽ hình tham khảo. Đây KHÔNG phải input tàu và KHÔNG phải kết quả chương trình thực chạy; không upload các CSV này làm danh sách tàu.

Gói Data đầu vào riêng không bao gồm paper_reference/, giúp tránh nhầm số liệu công bố với input.
