"""
Ngân hàng đề thi môn Soạn thảo văn bản hành chính (Theo Nghị định 30/2020/NĐ-CP).
Gồm:
1. Ngân hàng câu hỏi trắc nghiệm (phân nhóm ma trận)
2. Ngân hàng tình huống thực hành soạn thảo văn bản Word:
   - Gói A: Công văn đề nghị (4 điểm)
   - Gói B: Tờ trình & Thông báo (4 điểm)
"""

# Ngân hàng trắc nghiệm chuẩn NĐ 30/2020/NĐ-CP
MULTIPLE_CHOICE_POOL = [
    {
        "id": 1,
        "group": "format",
        "question": "Theo Nghị định 30/2020/NĐ-CP, khổ giấy chuẩn áp dụng cho văn bản hành chính là khổ giấy nào?",
        "options": [
            "Khổ A4 (210 mm x 297 mm)",
            "Khổ A3 (297 mm x 420 mm)",
            "Khổ Letter (215.9 mm x 279.4 mm)",
            "Tùy chọn khổ A4 hoặc A5 theo loại văn bản"
        ],
        "correct_index": 0,
        "explanation": "Theo Điều 8 Nghị định 30/2020/NĐ-CP, văn bản hành chính được trình bày trên khổ giấy A4 (210 mm x 297 mm)."
    },
    {
        "id": 2,
        "group": "format",
        "question": "Quy định về căn lề trang văn bản (đối với khổ A4 định hướng đứng) theo Nghị định 30/2020/NĐ-CP là:",
        "options": [
            "Trên: 20-25 mm; Dưới: 20-25 mm; Trái: 30-35 mm; Phải: 15-20 mm",
            "Trên: 20 mm; Dưới: 20 mm; Trái: 20 mm; Phải: 20 mm",
            "Trên: 15-20 mm; Dưới: 15-20 mm; Trái: 25-30 mm; Phải: 10-15 mm",
            "Trên: 25-30 mm; Dưới: 20-25 mm; Trái: 35-40 mm; Phải: 20-25 mm"
        ],
        "correct_index": 0,
        "explanation": "Phụ lục I NĐ 30 quy định: Lề trên/dưới: 20-25mm; Lề trái: 30-35mm; Lề phải: 15-20mm."
    },
    {
        "id": 3,
        "group": "format",
        "question": "Phông chữ chuẩn bắt buộc sử dụng khi soạn thảo văn bản hành chính theo Nghị định 30/2020/NĐ-CP là:",
        "options": [
            "Phông chữ tiếng Việt Times New Roman, bộ mã Unicode tiêu chuẩn",
            "Phông chữ Arial hoặc Calibri",
            "Phông chữ .VnTime thuộc bảng mã TCVN3",
            "Bất kỳ phông chữ Unicode nào dễ nhìn"
        ],
        "correct_index": 0,
        "explanation": "Phụ lục I NĐ 30 quy định phông chữ sử dụng trình bày văn bản là phông chữ tiếng Việt Times New Roman, bộ mã ký tự Unicode."
    },
    {
        "id": 4,
        "group": "elements",
        "question": "Quốc hiệu 'CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM' được trình bày theo quy cách nào?",
        "options": [
            "Chữ in hoa, cỡ chữ từ 12 đến 13, kiểu chữ đứng, đậm",
            "Chữ in hoa, cỡ chữ từ 13 đến 14, kiểu chữ nghiêng, đậm",
            "Chữ in thường, cỡ chữ từ 12 đến 13, kiểu chữ đứng, đậm",
            "Chữ in hoa, cỡ chữ 14, gạch chân toàn bộ"
        ],
        "correct_index": 0,
        "explanation": "Quốc hiệu được in hoa, cỡ 12-13, đứng, đậm, đặt phía trên cùng bên phải trang đầu tiên."
    },
    {
        "id": 5,
        "group": "elements",
        "question": "Tiêu ngữ 'Độc lập - Tự do - Hạnh phúc' được trình bày như thế nào?",
        "options": [
            "Chữ in thường, cỡ chữ từ 13 đến 14, kiểu chữ đứng, đậm; chữ cái đầu của các từ được viết hoa, có gạch nối giữa các từ, phía dưới có đường kẻ ngang",
            "Chữ in hoa toàn bộ, cỡ chữ 12, đứng, đậm",
            "Chữ in thường, kiểu chữ nghiêng, không có đường kẻ ngang",
            "Chữ in hoa, cỡ 14, kiểu chữ đứng, gạch chân nét đôi"
        ],
        "correct_index": 0,
        "explanation": "Tiêu ngữ cỡ 13-14, đứng, đậm, có gạch nối giữa các cụm từ và có đường kẻ ngang bằng độ dài của dòng chữ ở dưới."
    },
    {
        "id": 6,
        "group": "elements",
        "question": "Thành phần 'Số và ký hiệu của văn bản' đối với Công văn của Trường Đại học Sư phạm Hà Nội (viết tắt là ĐHSPHN) do Phòng Hành chính tham mưu có dạng nào đúng?",
        "options": [
            "Số: .../ĐHSPHN-HC",
            "Số: .../CV-ĐHSPHN",
            "Số: .../HC-ĐHSPHN",
            "Số: .../ĐHSPHN/HC"
        ],
        "correct_index": 0,
        "explanation": "Theo NĐ 30, số ký hiệu công văn: Số: [Số thứ tự]/[Chữ viết tắt tên cơ quan]-[Chữ viết tắt đơn vị soạn thảo]."
    },
    {
        "id": 7,
        "group": "authority",
        "question": "Trường hợp ký thay mặt tập thể lãnh đạo (ví dụ Ủy ban nhân dân), người có thẩm quyền ký ghi chức danh nào?",
        "options": [
            "TM. ỦY BAN NHÂN DÂN",
            "KT. CHỦ TỊCH",
            "TL. ỦY BAN NHÂN DÂN",
            "TUQ. CHỦ TỊCH"
        ],
        "correct_index": 0,
        "explanation": "Ký thay mặt cơ quan, tổ chức hoạt động theo chế độ tập thể ghi: TM. [Tên tập thể] (Ví dụ: TM. ỦY BAN NHÂN DÂN)."
    },
    {
        "id": 8,
        "group": "authority",
        "question": "Trường hợp cấp phó ký thay cấp trưởng, chức danh ký được ghi như thế nào?",
        "options": [
            "KT. [CHỨC DANH CẤP TRƯỞNG] (Ví dụ: KT. HIỆU TRƯỞNG / PHÓ HIỆU TRƯỞNG)",
            "TM. [CHỨC DANH CẤP TRƯỞNG]",
            "TL. [CHỨC DANH CẤP TRƯỞNG]",
            "KÝ HỘ"
        ],
        "correct_index": 0,
        "explanation": "Trường hợp cấp phó được giao ký thay cấp trưởng ghi: KT. (Ký thay) trước chức danh cấp trưởng."
    },
    {
        "id": 9,
        "group": "elements",
        "question": "Thành phần 'Nơi nhận' của văn bản hành chính có đặc điểm trình bày nào sau đây là ĐÚNG?",
        "options": [
            "Từ 'Nơi nhận' cỡ chữ 12, nghiêng, đậm; phần liệt kê nơi nhận cỡ chữ 11, đứng, thường",
            "Từ 'Nơi nhận' cỡ chữ 14, in hoa đậm; phần liệt kê cỡ chữ 13",
            "Toàn bộ nơi nhận dùng chữ in hoa, in nghiêng, cỡ 12",
            "Từ 'Nơi nhận' đóng khung viền xung quanh"
        ],
        "correct_index": 0,
        "explanation": "Từ 'Nơi nhận:' cỡ 12, nghiêng, đậm. Tên cơ quan, cá nhân nhận văn bản: cỡ 11, thường, đứng."
    },
    {
        "id": 10,
        "group": "format",
        "question": "Khoảng cách giữa các đoạn văn (Paragraph Spacing) trong văn bản hành chính được quy định đặt tối thiểu là:",
        "options": [
            "Tối thiểu 6pt",
            "Tối thiểu 12pt",
            "0pt (không giãn cách đoạn)",
            "Tối thiểu 18pt"
        ],
        "correct_index": 0,
        "explanation": "Khoảng cách giữa các đoạn văn đặt tối thiểu 6 pt để tạo độ thoáng rõ ràng giữa các phần nội dung."
    },
    {
        "id": 11,
        "group": "elements",
        "question": "Trích yếu nội dung văn bản đối với Quyết định được trình bày như thế nào?",
        "options": [
            "Cỡ chữ từ 13 đến 14, chữ in thường, kiểu chữ đứng, đậm, đặt dưới tên loại văn bản",
            "Cỡ chữ 12, chữ in hoa toàn bộ, đặt trong ngoặc đơn",
            "Cỡ chữ 11, chữ nghiêng, đặt ở cuối văn bản",
            "Không cần trích yếu nội dung đối với quyết định"
        ],
        "correct_index": 0,
        "explanation": "Tên loại văn bản in hoa đậm, trích yếu đặt canh giữa ngay dưới tên loại, in thường, đứng, đậm."
    },
    {
        "id": 12,
        "group": "general",
        "question": "Theo Nghị định 30/2020/NĐ-CP, văn bản hành chính gồm bao nhiêu thành phần thể thức chính?",
        "options": [
            "9 thành phần thể thức chính",
            "7 thành phần thể thức chính",
            "12 thành phần thể thức chính",
            "5 thành phần thể thức chính"
        ],
        "correct_index": 0,
        "explanation": "Nghị định 30 quy định 9 thành phần thể thức chính (Quốc hiệu tiêu ngữ, Tên cơ quan, Số ký hiệu, Địa danh ngày tháng, Tên loại trích yếu, Nội dung, Chức vụ chữ ký, Dấu, Nơi nhận)."
    }
]

# ================= GÓI A: CÔNG VĂN ĐỀ NGHỊ (4 ĐIỂM) =================
PRACTICE_CASES_POOL_A = [
    {
        "case_id": "A1",
        "doc_type": "CÔNG VĂN ĐỀ NGHỊ",
        "title": "Đề nghị khắc phục tình trạng gián đoạn cấp nước",
        "context": "Công ty Anh/Chị đang tập trung sản xuất để giao hàng cho khách hàng. Trong hai tuần gần đây, nguồn nước tại công ty nhiều lần bị gián đoạn hoặc có áp lực yếu, ảnh hưởng đến hoạt động sản xuất và vệ sinh nhà xưởng.\n\nAnh/chị hãy soạn thảo văn bản gửi đơn vị trực tiếp cung cấp nước để đề nghị kiểm tra nguyên nhân, có biện pháp khắc phục và phối hợp thông tin khi có kế hoạch gián đoạn cấp nước.",
        "requirements": [
            "Được giả định tên công ty, đơn vị nhận, thời gian và người có thẩm quyền ký;",
            "Các thông tin phải hợp lý, nhất quán;",
            "Văn bản có đầy đủ thành phần thể thức đã học theo Nghị định 30/2020/NĐ-CP."
        ]
    },
    {
        "case_id": "A2",
        "doc_type": "CÔNG VĂN ĐỀ NGHỊ",
        "title": "Đề nghị sửa chữa đường truyền Internet",
        "context": "Công ty Anh/Chị đang triển khai tiếp nhận và xử lý đơn hàng trực tuyến. Tuy nhiên, đường truyền Internet thường xuyên mất kết nối, làm gián đoạn giao dịch và chậm phản hồi khách hàng. Công ty đã liên hệ bộ phận hỗ trợ nhưng tình trạng chưa được khắc phục ổn định.\n\nAnh/chị hãy soạn thảo văn bản gửi doanh nghiệp cung cấp dịch vụ Internet để đề nghị kiểm tra, khắc phục sự cố và thông tin thời gian hoàn thành.",
        "requirements": [
            "Được giả định tên công ty, đơn vị nhận, thời gian và người có thẩm quyền ký;",
            "Các thông tin phải hợp lý, nhất quán;",
            "Văn bản có đầy đủ thành phần thể thức đã học theo Nghị định 30/2020/NĐ-CP."
        ]
    },
    {
        "case_id": "A3",
        "doc_type": "CÔNG VĂN ĐỀ NGHỊ",
        "title": "Đề nghị nhà cung cấp giao hàng đúng tiến độ",
        "context": "Công ty Anh/Chị đã ký hợp đồng mua nguyên phụ liệu của Công ty (anh chị tự giả định). Theo hợp đồng, hàng phải được giao đầy đủ trước ngày .... tháng ...... Đến ngày .... tháng ...., công ty mới nhận được khoảng 60% số lượng, ảnh hưởng đến tiến độ sản xuất.\nAnh/chị hãy soạn thảo văn bản gửi Công ty ........ để đề nghị giao phần hàng còn thiếu và xác nhận lịch giao cụ thể.",
        "requirements": [
            "Được giả định tên công ty, đơn vị nhận, thời gian và người có thẩm quyền ký;",
            "Các thông tin phải hợp lý, nhất quán;",
            "Văn bản có đầy đủ thành phần thể thức đã học theo Nghị định 30/2020/NĐ-CP."
        ]
    }
]

# ================= GÓI B: TỜ TRÌNH & THÔNG BÁO (4 ĐIỂM) =================
PRACTICE_CASES_POOL_B = [
    {
        "case_id": "B1",
        "doc_type": "TỜ TRÌNH",
        "title": "Tờ trình về việc xin phê duyệt bổ sung nhân sự",
        "context": "Công ty/Đơn vị của Anh/Chị đang triển khai mở rộng hoạt động và tiếp nhận các dự án mới. Hiện nay, khối lượng công việc tại bộ phận chuyên môn tăng đột biến dẫn đến tình trạng quá tải, nhân sự hiện tại không đảm bảo tiến độ và chất lượng công việc.\n\nAnh/chị hãy soạn thảo văn bản phù hợp gửi Ban Giám đốc (hoặc Lãnh đạo cấp trên) đề xuất phê duyệt chủ trương tuyển dụng bổ sung nhân sự cho bộ phận.",
        "requirements": [
            "Được giả định tên cơ quan/công ty, bộ phận công tác, người nhận văn bản và người ký;",
            "Nêu rõ lý do, sự cần thiết và đề xuất cụ thể số lượng, vị trí chức danh cần bổ sung;",
            "Đầy đủ các thành phần thể thức văn bản theo chuẩn Nghị định 30/2020/NĐ-CP."
        ]
    },
    {
        "case_id": "B2",
        "doc_type": "TỜ TRÌNH",
        "title": "Tờ trình về việc xin trang bị, mua sắm máy móc thiết bị làm việc",
        "context": "Hệ thống máy móc, thiết bị văn phòng (máy tính, máy in, thiết bị chuyên dụng...) tại phòng ban của Anh/Chị đã qua nhiều năm sử dụng, hiện thường xuyên bị hỏng hóc, cấu hình lạc hậu gây ảnh hưởng lớn đến hiệu suất công việc hàng ngày.\n\nAnh/chị hãy soạn thảo văn bản phù hợp gửi Ban Giám đốc (hoặc Lãnh đạo cơ quan) để báo cáo hiện trạng và đề xuất kinh phí mua sắm, thay thế trang thiết bị làm việc mới.",
        "requirements": [
            "Được giả định tên đơn vị, cấp có thẩm quyền phê duyệt, thời gian và dự trù kinh phí;",
            "Trình bày rõ sự cần thiết, danh mục thiết bị dự kiến mua sắm và hiệu quả mang lại;",
            "Đúng thể thức và kỹ thuật trình bày văn bản theo Nghị định 30/2020/NĐ-CP."
        ]
    },
    {
        "case_id": "B3",
        "doc_type": "THÔNG BÁO",
        "title": "Thông báo về việc phân công nhiệm vụ và triển khai kế hoạch công tác",
        "context": "Thực hiện kế hoạch hoạt động của cơ quan/doanh nghiệp, Lãnh đạo đơn vị đã phê duyệt kế hoạch triển khai nhiệm vụ mới và yêu cầu các phòng ban, cán bộ nhân viên phối hợp thực hiện theo đúng tiến độ được giao.\n\nAnh/chị hãy thừa lệnh (hoặc thừa ủy quyền/ký văn bản) soạn thảo văn bản gửi các đơn vị trực thuộc và toàn thể nhân viên về việc phân công nhiệm vụ được giao.",
        "requirements": [
            "Được giả định tên cơ quan ban hành, căn cứ kế hoạch, đối tượng tiếp nhận văn bản;",
            "Nêu rõ các nội dung nhiệm vụ phân công, thời hạn hoàn thành và trách nhiệm phối hợp;",
            "Văn bản có đầy đủ thành phần thể thức theo Nghị định 30/2020/NĐ-CP."
        ]
    },
    {
        "case_id": "B4",
        "doc_type": "THÔNG BÁO",
        "title": "Thông báo thông tin hoạt động chung của cơ quan, doanh nghiệp",
        "context": "Nhân dịp kỷ niệm ngày thành lập (hoặc tổ chức sự kiện chuyên môn/hoạt động định kỳ), cơ quan/công ty của Anh/Chị sẽ tổ chức chuỗi hoạt động chung nhằm tổng kết hoạt động và giao lưu nâng cao tinh thần đoàn kết.\n\nAnh/chị hãy soạn thảo văn bản gửi toàn thể cán bộ, nhân viên thông tin chi tiết về kế hoạch tổ chức hoạt động để các bộ phận chủ động sắp xếp công việc và tham gia.",
        "requirements": [
            "Được giả định tên công ty/cơ quan, thời gian, địa điểm tổ chức và thành phần tham gia;",
            "Nội dung văn bản rõ ràng, lịch trình cụ thể và phân công chuẩn bị chu đáo;",
            "Đúng chuẩn thể thức văn bản theo quy định của Nghị định 30/2020/NĐ-CP."
        ]
    }
]
