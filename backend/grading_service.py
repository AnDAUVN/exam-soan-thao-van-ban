"""
Dịch vụ Quản lý Thang Điểm & Tiêu Chí Chấm Thi (Rubric) Tự Điều Chỉnh
Cho phép Giảng viên tùy biến thang điểm từng phần thi và chi tiết 10 tiêu chí Nghị định 30.
"""

import os
import json
import copy
from typing import Dict, Any, List

BASE_DIR = os.path.dirname(__file__)
CONFIG_FILE = os.path.join(BASE_DIR, "grading_config.json")

DEFAULT_GRADING_CONFIG = {
    "sections": {
        "quiz_max": 2.0,
        "case_1_format_max": 2.0,
        "case_1_content_max": 2.0,
        "case_2_format_max": 2.0,
        "case_2_content_max": 2.0
    },
    "rubric_items": [
        {
            "id": "paper_size",
            "cell": "Tổng thể",
            "name": "Khổ giấy A4",
            "description": "Kích thước 210 x 297 mm chuẩn A4",
            "default_points": 0.5,
            "points": 0.5
        },
        {
            "id": "margins",
            "cell": "Tổng thể",
            "name": "Căn lề trang văn bản",
            "description": "Trên/Dưới 20-25mm, Trái 30-35mm, Phải 15-20mm",
            "default_points": 1.5,
            "points": 1.5
        },
        {
            "id": "font_family",
            "cell": "Tổng thể",
            "name": "Phông chữ chuẩn Times New Roman",
            "description": "Bắt buộc sử dụng phông chữ Times New Roman theo NĐ 30",
            "default_points": 1.0,
            "points": 1.0
        },
        {
            "id": "quoc_hieu",
            "cell": "Ô 1",
            "name": "Quốc hiệu & Tiêu ngữ",
            "description": "Quốc hiệu in hoa đứng đậm, Tiêu ngữ có gạch nối",
            "default_points": 1.5,
            "points": 1.5
        },
        {
            "id": "co_quan",
            "cell": "Ô 2",
            "name": "Tên cơ quan ban hành & Bố cục đầu trang",
            "description": "Bảng không viền chia cột cân xứng với Quốc hiệu",
            "default_points": 1.0,
            "points": 1.0
        },
        {
            "id": "so_ky_hieu",
            "cell": "Ô 3",
            "name": "Số và ký hiệu văn bản",
            "description": "Cấu trúc 'Số: .../...-...' theo đúng quy định",
            "default_points": 1.0,
            "points": 1.0
        },
        {
            "id": "dia_danh_ngay_thang",
            "cell": "Ô 4",
            "name": "Địa danh, ngày, tháng, năm",
            "description": "Địa danh tỉnh/thành, ngày tháng năm đầy đủ",
            "default_points": 1.0,
            "points": 1.0
        },
        {
            "id": "ten_loai_trich_yeu",
            "cell": "Ô 5",
            "name": "Tên loại & Trích yếu nội dung",
            "description": "Tên loại văn bản hoặc V/v công văn, trích yếu",
            "default_points": 1.0,
            "points": 1.0
        },
        {
            "id": "tham_quyen_ky",
            "cell": "Ô 7, 8",
            "name": "Thẩm quyền ký & Con dấu",
            "description": "Chức danh thẩm quyền ký (Hiệu trưởng, Giám đốc, TM., KT., TL.)",
            "default_points": 1.0,
            "points": 1.0
        },
        {
            "id": "noi_nhan",
            "cell": "Ô 9",
            "name": "Nơi nhận (Ô 9a / Ô 9b)",
            "description": "Thành phần nơi nhận và lưu văn thư",
            "default_points": 0.5,
            "points": 0.5
        }
    ]
}

class GradingService:
    @staticmethod
    def load_config() -> Dict[str, Any]:
        """Tải cấu hình thang điểm từ file JSON, nếu chưa có thì khởi tạo mặc định"""
        if not os.path.exists(CONFIG_FILE):
            GradingService.save_config(DEFAULT_GRADING_CONFIG)
            return copy.deepcopy(DEFAULT_GRADING_CONFIG)
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            # Kiểm tra và điền các trường còn thiếu nếu file cũ
            if "sections" not in cfg:
                cfg["sections"] = copy.deepcopy(DEFAULT_GRADING_CONFIG["sections"])
            if "rubric_items" not in cfg or not isinstance(cfg["rubric_items"], list):
                cfg["rubric_items"] = copy.deepcopy(DEFAULT_GRADING_CONFIG["rubric_items"])
            return cfg
        except Exception as e:
            print(f"Lỗi đọc {CONFIG_FILE}, dùng cấu hình mặc định: {e}")
            return copy.deepcopy(DEFAULT_GRADING_CONFIG)

    @staticmethod
    def save_config(new_config: Dict[str, Any]) -> Dict[str, Any]:
        """Lưu cấu hình thang điểm mới sau khi kiểm định dữ liệu"""
        try:
            sections = new_config.get("sections", {})
            quiz_max = float(sections.get("quiz_max", 3.0))
            c1_f_max = float(sections.get("case_1_format_max", 2.0))
            c1_c_max = float(sections.get("case_1_content_max", 1.5))
            c2_f_max = float(sections.get("case_2_format_max", 2.0))
            c2_c_max = float(sections.get("case_2_content_max", 1.5))

            if min(quiz_max, c1_f_max, c1_c_max, c2_f_max, c2_c_max) < 0:
                return {"error": "Điểm của từng mục không được là số âm!"}

            total_sections = round(quiz_max + c1_f_max + c1_c_max + c2_f_max + c2_c_max, 2)

            sanitized_rubric = []
            default_map = {item["id"]: item for item in DEFAULT_GRADING_CONFIG["rubric_items"]}

            items_input = new_config.get("rubric_items", [])
            for item in items_input:
                item_id = item.get("id")
                base = default_map.get(item_id, item)
                pts = float(item.get("points", base.get("default_points", 1.0)))
                if pts < 0:
                    pts = 0.0
                sanitized_rubric.append({
                    "id": item_id,
                    "cell": base.get("cell", "Quy cách"),
                    "name": base.get("name", item_id),
                    "description": base.get("description", ""),
                    "default_points": base.get("default_points", 1.0),
                    "points": round(pts, 2)
                })

            # Đảm bảo đủ các mục mặc định nếu bị thiếu
            existing_ids = {it["id"] for it in sanitized_rubric}
            for d_item in DEFAULT_GRADING_CONFIG["rubric_items"]:
                if d_item["id"] not in existing_ids:
                    sanitized_rubric.append(copy.deepcopy(d_item))

            final_data = {
                "sections": {
                    "quiz_max": round(quiz_max, 2),
                    "case_1_format_max": round(c1_f_max, 2),
                    "case_1_content_max": round(c1_c_max, 2),
                    "case_2_format_max": round(c2_f_max, 2),
                    "case_2_content_max": round(c2_c_max, 2),
                    "total": total_sections
                },
                "rubric_items": sanitized_rubric
            }

            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(final_data, f, ensure_ascii=False, indent=2)

            return {
                "status": "success",
                "message": f"Đã lưu thang điểm thành công! Tổng điểm cơ cấu bài thi: {total_sections}đ.",
                "config": final_data
            }
        except Exception as e:
            return {"error": f"Lỗi lưu cấu hình thang điểm: {str(e)}"}

    @staticmethod
    def reset_to_default() -> Dict[str, Any]:
        """Khôi phục lại thang điểm chuẩn ban đầu theo Nghị định 30"""
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(DEFAULT_GRADING_CONFIG, f, ensure_ascii=False, indent=2)
            return {
                "status": "success",
                "message": "Đã khôi phục thang điểm về chuẩn Nghị định 30 thành công!",
                "config": copy.deepcopy(DEFAULT_GRADING_CONFIG)
            }
        except Exception as e:
            return {"error": f"Lỗi khôi phục thang điểm: {str(e)}"}

    @staticmethod
    def get_rubric_map() -> Dict[str, float]:
        """Lấy dict ánh xạ {id: points} phục vụ chấm điểm tự động"""
        cfg = GradingService.load_config()
        return {item["id"]: float(item.get("points", 1.0)) for item in cfg.get("rubric_items", [])}

    @staticmethod
    def get_sections() -> Dict[str, float]:
        """Lấy cấu hình điểm tối đa các phần thi"""
        cfg = GradingService.load_config()
        return cfg.get("sections", DEFAULT_GRADING_CONFIG["sections"])
