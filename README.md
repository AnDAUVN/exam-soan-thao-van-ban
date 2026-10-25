# Hệ Thống Phần Mềm Thi Môn Soạn Thảo Văn Bản Hành Chính (Nghị Định 30/2020/NĐ-CP)

Dự án phần mềm thi trực tuyến chuyên biệt dành cho các trường Đại học, Cao đẳng, Trung tâm đào tạo môn **Soạn thảo văn bản hành chính & Văn thư lưu trữ**.

---

## 🎯 Cấu trúc đề thi đáp ứng yêu cầu

1. **10 Câu Trắc Nghiệm Ngẫu Nhiên:**
   - Đề thi tự động bốc ngẫu nhiên 10 câu từ ngân hàng câu hỏi chuẩn Nghị định 30.
   - Trộn ngẫu nhiên thứ tự các phương án (A, B, C, D) cho từng thí sinh (không sinh viên nào giống nhau).
   - Chấm điểm tự động và lưu bài làm tức thì.
2. **2 Văn Bản Hành Chính Thực Hành Trên MS Word:**
   - Hệ thống tự động bốc thăm ngẫu nhiên:
     - **Văn bản 1 (Từ Giỏ A):** Quyết định cá biệt, Quyết định khen thưởng, Quyết định ban hành quy chế...
     - **Văn bản 2 (Từ Giỏ B):** Công văn hành chính, Tờ trình phê duyệt kinh phí, Thông báo lịch làm việc...
   - Sinh viên mở Word trên máy để làm bài, sau đó kéo thả nộp file `.docx` lên hệ thống.
3. **Module Chấm Điểm Thể Thức Tự Động (Auto-Grader Docx):**
   - Đọc trực tiếp cấu trúc XML của file Word (`.docx`) sinh viên nộp lên.
   - Soi chi tiết theo quy chuẩn **Nghị định 30/2020/NĐ-CP**:
     - ✅ Khổ giấy A4 (210mm x 297mm).
     - ✅ Căn lề trang: Trên 20-25mm, Dưới 20-25mm, Trái 30-35mm, Phải 15-20mm.
     - ✅ Phông chữ chuẩn: Times New Roman, Unicode.
     - ✅ Bố cục Quốc hiệu & Tiêu ngữ: Đúng chữ in hoa, in thường, đậm.
     - ✅ Kỹ thuật chia bảng không viền phần đầu trang (Tên cơ quan - Quốc hiệu).
4. **Đồng hồ đếm ngược & Thu bài tự động:**
   - Đồng hồ đếm ngược đồng bộ từ server.
   - Tự động khóa và thu bài khi hết giờ làm bài.
   - Hỗ trợ chế độ Fullscreen Kiosk Mode chống gian lận.

---

## 📁 Cấu trúc thư mục dự án

```text
exam-soan-thao-van-ban/
├── backend/
│   ├── docx_grader.py       # Engine bóc tách XML và chấm thể thức Word theo NĐ 30
│   ├── questions_bank.py    # Ngân hàng 10+ câu trắc nghiệm & Giỏ đề tình huống A, B
│   ├── exam_engine.py       # Logic sinh đề ngẫu nhiên, chấm trắc nghiệm & quản lý phiên
│   ├── main.py              # API Server FastAPI (Nhận bài thi, nộp file .docx)
│   └── uploads/             # Nơi lưu trữ file bài làm Word của từng sinh viên
├── frontend/
│   ├── index.html           # Giao diện phòng thi trực quan
│   ├── app.js               # Logic điều khiển Timer, nộp bài, chuyển tab
│   └── style.css            # Tùy biến giao diện & hiệu ứng cảnh báo
├── requirements.txt         # Danh sách thư viện Python
└── README.md                # Tài liệu hướng dẫn
```

---

## 🚀 Hướng dẫn khởi chạy hệ thống

### 1. Cài đặt các thư viện cần thiết
Mở Terminal / PowerShell tại thư mục dự án và chạy lệnh:
```bash
pip install -r requirements.txt
```

### 2. Khởi chạy máy chủ Web Thi
```bash
cd backend
python main.py
```
*(Hoặc dùng lệnh: `uvicorn main:app --reload --port 8000`)*

### 3. Trải nghiệm phòng thi
- Mở trình duyệt web và truy cập: **`http://localhost:8000`**
- Nhập **Mã sinh viên** và **Họ tên** rồi nhấn **Bắt đầu làm bài thi**.
- Làm 10 câu trắc nghiệm, xem 2 tình huống soạn thảo văn bản, nộp file `.docx` và xem hệ thống chấm điểm thể thức ngay lập tức!
