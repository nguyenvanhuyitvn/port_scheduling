# Lập lịch tàu tại cảng container

Mã nguồn thực nghiệm cho báo cáo kết thúc môn **Advanced Algorithms**. Chương trình phối hợp vị trí cập bến liên tục, thời gian phục vụ và khối cần trục cụ thể không thay đổi trong quá trình làm hàng.

**Đây là bản cài đặt độc lập dựa trên báo cáo và tài liệu tham khảo, không phải mã nguồn gốc của tác giả.** Các chi tiết còn thiếu trong tài liệu được đặc tả trong `docs/METHOD.md`. Chương trình không cam kết tái tạo giá trị 79,11 giờ của tài liệu.

## 1. Cài đặt nhanh trên Windows

Giải nén ZIP, mở PowerShell tại thư mục chứa `pyproject.toml`. Sử dụng Python 3.11 trở lên:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e .
```

Không cần kích hoạt môi trường hoặc thay đổi ExecutionPolicy. Các lệnh sau gọi trực tiếp Python của môi trường.

### Bước 1 — Chạy kiểm tra

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m port_scheduler verify-examples --solver highs --seconds 10 --out results/verification
```

Đọc `results/verification/verification.json`. Cả bốn dòng phải có `passed: true`:

| Đường bờ | Mô hình | Kết quả |
|---|---|---|
| 200 m | corrected | OPTIMAL, Z = 4 giờ |
| 200 m | printed_core | OPTIMAL, Z = 6 giờ |
| 100 m | corrected | OPTIMAL, Z = 6 giờ |
| 100 m | printed_core | INFEASIBLE |

`printed_core` chỉ kiểm tra logic (5)–(8), không tái hiện toàn bộ mô hình gốc.

### Bước 2 — Chạy một lịch GGA cho 12 tàu

```powershell
.\.venv\Scripts\python.exe -m port_scheduler run --instance data/liaoning_12.json --algorithm gga --seconds 5 --seed 0 --out results/liaoning12_gga_seed0 --plot
```

Mở `run.json`, `schedule.csv`, `berth_schedule.png`, `crane_schedule.png`. Lịch phải có `feasible: true`, `validation_errors: []`. Giá trị `objective` là **tổng** thời gian các tàu ở cảng, tính bằng giờ.

### Bước 3 — Kiểm tra lịch độc lập

```powershell
.\.venv\Scripts\python.exe -m port_scheduler validate --instance data/liaoning_12.json --run results/liaoning12_gga_seed0/run.json
```

### Bước 4 — So sánh GA và GGA trên 12 tàu

```powershell
.\.venv\Scripts\python.exe run_experiments.py --instances data/liaoning_12.json --algorithms ga gga --seeds 0 1 2 3 4 5 6 7 8 9 --seconds 5 --out results/main_12
```

Thời gian lõi dự kiến khoảng 2 × 10 × 5 = 100 giây, cộng thời gian khởi động và ghi tệp; thời gian thực tế tùy máy.

### Bước 5 — Chạy mô hình chính xác không cần Gurobi

```powershell
.\.venv\Scripts\python.exe -m port_scheduler run --instance data/synthetic/synthetic_n5_01.json --algorithm mip --solver highs --seconds 30 --out results/mip_n5_highs --plot
```

HiGHS qua SciPy là một backend riêng. Không gọi các kết quả này là kết quả Gurobi.

### Bước 6 — Dùng Gurobi nếu đã có môi trường và license

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[gurobi]"
.\.venv\Scripts\python.exe -m port_scheduler verify-examples --solver gurobi --seconds 10 --out results/verification_gurobi
.\.venv\Scripts\python.exe -m port_scheduler run --instance data/liaoning_12.json --algorithm mip --solver gurobi --seconds 30 --threads 1 --out results/mip_12_gurobi --plot
```

Cài `gurobipy` không tự bảo đảm license dùng được cho mọi quy mô. Nếu Gurobi báo lỗi cài đặt, license hoặc kích thước mô hình, chương trình dừng và ghi lỗi, không âm thầm chuyển sang HiGHS. Nhánh Gurobi được cung cấp nhưng chưa chạy trong môi trường tạo gói này.

## 2. Linux và macOS

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/python -m port_scheduler verify-examples --solver highs
.venv/bin/python -m port_scheduler run --instance data/liaoning_12.json --algorithm gga --seconds 5 --seed 0 --out results/demo --plot
```

## 3. Tài liệu hướng dẫn

- `docs/HUONG_DAN_THUC_NGHIEM.md`: quy trình đầy đủ và cách viết kết quả vào Chương 3.
- `docs/METHOD.md`: mô hình toán học, decoder, GA/GGA và các khác biệt so với nguồn tham khảo.
- `docs/VERIFIED_RESULTS.md`: phạm vi đã kiểm chứng thực tế, tạo từ các lần chạy đi kèm.
- `data/liaoning_12_original.csv`: số liệu chép từ Bảng 1, giữ nguyên ETA.
- `data/liaoning_12.json`: ETA quy đổi ngày:giờ:phút; ghi rõ giả định trong metadata.
- `results_verified/`: đầu ra thực sự đã chạy tại môi trường tạo gói, không phải số liệu bài báo.

## 4. Cấu trúc

```text
port_scheduling/
  README.md
  pyproject.toml
  requirements.txt
  run_experiments.py
  data/                   dữ liệu đầu vào và metadata
  docs/                   hướng dẫn và đặc tả
  src/port_scheduler/
    domain.py             dữ liệu, cận và lịch tuần tự
    validation.py         bộ kiểm tra lịch độc lập
    mip.py                một ma trận mô hình, backend HiGHS/Gurobi
    heuristics.py         Greedy, GA, GGA và decoder
    plotting.py           vẽ lịch thực tế
    cli.py                dòng lệnh và tổng hợp
  tests/                  unittest không cần pytest
  results_verified/       kết quả mẫu đã chạy thật
```

Không có Streamlit trong phiên bản này. Trọng tâm là thực nghiệm CLI tái lập được và xuất kết quả phục vụ báo cáo.
