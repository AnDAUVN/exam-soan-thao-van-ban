"""
Engine quản lý phiên thi, danh mục Khóa - Lớp lưu trữ vĩnh viễn (hỗ trợ Thêm, Sửa, Xóa), sinh phôi Word và chấm điểm.
"""

import random
import copy
import time
import uuid
import os
import json
import zipfile
import datetime
from typing import Dict, Any, List
from questions_bank import MULTIPLE_CHOICE_POOL, PRACTICE_CASES_POOL_A, PRACTICE_CASES_POOL_B
from docx_grader import DocxNghiDinh30Grader
from grading_service import GradingService
from word_mcq_parser import (
    extract_docx_paragraphs, 
    parse_raw_text_to_paragraphs, 
    parse_mcqs_from_paragraphs, 
    create_mcq_sample_docx
)

ACTIVE_SESSIONS: Dict[str, Dict[str, Any]] = {}
BASE_DIR = os.path.dirname(__file__)
TEMPLATE_STORAGE = os.path.join(BASE_DIR, "templates_generated")
CATALOG_FILE = os.path.join(BASE_DIR, "classes_catalog.json")
QUESTIONS_BANK_FILE = os.path.join(BASE_DIR, "questions_bank.json")
os.makedirs(TEMPLATE_STORAGE, exist_ok=True)

def load_classes_catalog() -> Dict[str, List[str]]:
    if os.path.exists(CATALOG_FILE):
        try:
            with open(CATALOG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "Khóa 1": ["Lớp 01 - Văn thư lưu trữ", "Lớp 02 - Quản trị văn phòng", "Lớp 03 - Luật kinh tế"],
        "Khóa 2": ["Lớp 01 - Hành chính công", "Lớp 02 - Tin học văn phòng"]
    }

def save_classes_catalog(catalog: Dict[str, List[str]]):
    try:
        with open(CATALOG_FILE, "w", encoding="utf-8") as f:
            json.dump(catalog, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("Lỗi lưu danh mục lớp:", e)

def load_questions_bank_data() -> Dict[str, Any]:
    if os.path.exists(QUESTIONS_BANK_FILE):
        try:
            with open(QUESTIONS_BANK_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if not isinstance(data, dict):
                    data = {}
                data.setdefault("config", {"mcq_count": 10})
                data.setdefault("multiple_choice", [])
                data.setdefault("practice_cases_a", [])
                data.setdefault("practice_cases_b", [])
                return data
        except Exception as e:
            print("Lỗi đọc ngân hàng câu hỏi:", e)
    return {
        "config": {"mcq_count": 10},
        "multiple_choice": [],
        "practice_cases_a": [],
        "practice_cases_b": []
    }

def save_questions_bank_data(data: Dict[str, Any]):
    try:
        with open(QUESTIONS_BANK_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("Lỗi lưu ngân hàng câu hỏi:", e)

COHORTS_AND_CLASSES = load_classes_catalog()

class ExamEngine:
    @staticmethod
    def get_classes_catalog() -> Dict[str, List[str]]:
        global COHORTS_AND_CLASSES
        COHORTS_AND_CLASSES = load_classes_catalog()
        return COHORTS_AND_CLASSES

    @staticmethod
    def add_cohort_or_class(cohort: str, class_name: str) -> Dict[str, Any]:
        global COHORTS_AND_CLASSES
        cohort = cohort.strip()
        class_name = class_name.strip()
        if not cohort:
            return {"error": "Tên Khóa không được để trống"}
        
        COHORTS_AND_CLASSES = load_classes_catalog()
        
        # Tìm target cohort nếu đã có (không phân biệt hoa/thường)
        target_cohort = None
        for k in COHORTS_AND_CLASSES.keys():
            if k.strip().lower() == cohort.lower() or k == cohort:
                target_cohort = k
                break
        
        if not target_cohort:
            target_cohort = cohort
            COHORTS_AND_CLASSES[target_cohort] = []
        
        if class_name:
            # Kiểm tra xem lớp đã tồn tại chưa
            exists = any(c.strip().lower() == class_name.lower() for c in COHORTS_AND_CLASSES[target_cohort])
            if not exists:
                COHORTS_AND_CLASSES[target_cohort].append(class_name)

        save_classes_catalog(COHORTS_AND_CLASSES)
        return {"status": "success", "catalog": COHORTS_AND_CLASSES}

    @staticmethod
    def edit_class(cohort: str, old_class_name: str, new_class_name: str) -> Dict[str, Any]:
        """Sửa tên một Lớp trong Khóa"""
        global COHORTS_AND_CLASSES
        cohort = cohort.strip()
        old_class_name = old_class_name.strip()
        new_class_name = new_class_name.strip()

        if not new_class_name:
            return {"error": "Tên lớp mới không được để trống"}

        COHORTS_AND_CLASSES = load_classes_catalog()
        target_cohort = None
        for k in list(COHORTS_AND_CLASSES.keys()):
            if k.strip().lower() == cohort.lower() or k == cohort:
                target_cohort = k
                break

        if target_cohort:
            classes = COHORTS_AND_CLASSES[target_cohort]
            for idx, c in enumerate(classes):
                if c.strip().lower() == old_class_name.lower() or c == old_class_name:
                    classes[idx] = new_class_name
                    save_classes_catalog(COHORTS_AND_CLASSES)
                    return {"status": "success", "catalog": COHORTS_AND_CLASSES}
        return {"error": f"Không tìm thấy lớp '{old_class_name}' để sửa"}

    @staticmethod
    def delete_class(cohort: str, class_name: str) -> Dict[str, Any]:
        """Xóa một Lớp khỏi Khóa"""
        global COHORTS_AND_CLASSES
        cohort = cohort.strip()
        class_name = class_name.strip()

        COHORTS_AND_CLASSES = load_classes_catalog()
        target_cohort = None
        for k in list(COHORTS_AND_CLASSES.keys()):
            if k.strip().lower() == cohort.lower() or k == cohort:
                target_cohort = k
                break

        if target_cohort:
            classes = COHORTS_AND_CLASSES[target_cohort]
            to_remove = [c for c in classes if c.strip().lower() == class_name.lower() or c == class_name]
            if to_remove:
                for c in to_remove:
                    classes.remove(c)
                save_classes_catalog(COHORTS_AND_CLASSES)
                return {"status": "success", "catalog": COHORTS_AND_CLASSES}
        return {"error": f"Không tìm thấy lớp '{class_name}' trong '{cohort}' để xóa"}

    @staticmethod
    def delete_cohort(cohort: str) -> Dict[str, Any]:
        """Xóa toàn bộ một Khóa học"""
        global COHORTS_AND_CLASSES
        cohort = cohort.strip()

        COHORTS_AND_CLASSES = load_classes_catalog()
        target_cohort = None
        for k in list(COHORTS_AND_CLASSES.keys()):
            if k.strip().lower() == cohort.lower() or k == cohort:
                target_cohort = k
                break

        if target_cohort:
            del COHORTS_AND_CLASSES[target_cohort]
            save_classes_catalog(COHORTS_AND_CLASSES)
            return {"status": "success", "catalog": COHORTS_AND_CLASSES}
        return {"error": f"Không tìm thấy khóa '{cohort}' để xóa"}

    # ================= QUẢN LÝ THANG ĐIỂM & RUBRIC CHẤM =================
    @staticmethod
    def get_grading_config() -> Dict[str, Any]:
        """Lấy cấu hình thang điểm và tiêu chí rubric hiện tại"""
        return GradingService.load_config()

    @staticmethod
    def save_grading_config(new_config: Dict[str, Any]) -> Dict[str, Any]:
        """Cập nhật cấu hình thang điểm theo yêu cầu của Giảng viên"""
        return GradingService.save_config(new_config)

    @staticmethod
    def reset_grading_config() -> Dict[str, Any]:
        """Khôi phục thang điểm chuẩn theo Nghị định 30"""
        return GradingService.reset_to_default()

    # ================= QUẢN LÝ NGÂN HÀNG CÂU HỎI & CẤU HÌNH ĐỀ =================
    @staticmethod
    def get_questions_bank() -> Dict[str, Any]:
        """Lấy toàn bộ ngân hàng câu hỏi trắc nghiệm, tự luận và cấu hình số câu"""
        return load_questions_bank_data()

    @staticmethod
    def update_exam_config(mcq_count: int) -> Dict[str, Any]:
        """Cấu hình số câu hỏi trắc nghiệm trong đề thi (5 hoặc 10 câu)"""
        if mcq_count not in [5, 10]:
            return {"error": "Số lượng câu hỏi trắc nghiệm chỉ được chọn 5 hoặc 10 câu!"}
        
        data = load_questions_bank_data()
        data.setdefault("config", {})["mcq_count"] = mcq_count
        save_questions_bank_data(data)
        sec = GradingService.get_sections()
        q_max = float(sec.get("quiz_max", 3.0))
        pts_per_q = round(q_max / mcq_count, 2)
        return {
            "status": "success", 
            "message": f"Đã cấu hình thành công: Đề thi sẽ gồm {mcq_count} câu hỏi trắc nghiệm (mỗi câu {pts_per_q}đ / tổng {q_max}đ).",
            "config": data["config"]
        }

    @staticmethod
    def add_mcq(question: str, options: List[str], correct_index: int, explanation: str = "", group: str = "general") -> Dict[str, Any]:
        """Thêm câu hỏi trắc nghiệm mới vào ngân hàng"""
        q_clean = question.strip()
        if not q_clean:
            return {"error": "Nội dung câu hỏi không được để trống!"}
        
        opts_clean = [o.strip() for o in options if o and o.strip()]
        if len(opts_clean) < 2:
            return {"error": "Phải có ít nhất 2 phương án trả lời!"}
        if correct_index < 0 or correct_index >= len(opts_clean):
            return {"error": "Vị trí đáp án đúng không hợp lệ!"}

        data = load_questions_bank_data()
        mcq_list = data.setdefault("multiple_choice", [])
        
        # Tạo ID mới tự tăng
        existing_ids = [q.get("id", 0) for q in mcq_list if isinstance(q.get("id"), int)]
        new_id = max(existing_ids, default=0) + 1

        new_q = {
            "id": new_id,
            "group": group.strip() or "general",
            "question": q_clean,
            "options": opts_clean,
            "correct_index": correct_index,
            "explanation": explanation.strip()
        }
        mcq_list.append(new_q)
        save_questions_bank_data(data)
        return {"status": "success", "message": f"Đã thêm câu hỏi trắc nghiệm #{new_id} thành công!", "question": new_q}

    @staticmethod
    def delete_mcq(question_id: Any) -> Dict[str, Any]:
        """Xóa câu hỏi trắc nghiệm khỏi ngân hàng"""
        data = load_questions_bank_data()
        mcq_list = data.setdefault("multiple_choice", [])

        found = False
        target_id_str = str(question_id).strip()
        for idx, q in enumerate(mcq_list):
            q_id_str = str(q.get("id", "")).strip()
            # Khớp theo ID lưu trong DB hoặc số thứ tự hiển thị (idx + 1)
            if q_id_str == target_id_str or str(idx + 1) == target_id_str:
                mcq_list.pop(idx)
                found = True
                break
        
        if not found:
            return {"error": f"Không tìm thấy câu hỏi #{question_id} để xóa!"}
        
        save_questions_bank_data(data)
        return {"status": "success", "message": f"Đã xóa câu hỏi #{question_id} thành công!"}

    @staticmethod
    def parse_mcq_docx(file_bytes_or_path) -> Dict[str, Any]:
        """Phân tích các câu hỏi trắc nghiệm từ file Word .docx"""
        try:
            paragraphs = extract_docx_paragraphs(file_bytes_or_path)
        except ValueError as ve:
            return {"error": str(ve)}
        except Exception as e:
            return {"error": f"Lỗi đọc file Word: {str(e)}"}

        if not paragraphs:
            return {"error": "Không thể đọc nội dung file Word hoặc file bị trống!"}
        questions = parse_mcqs_from_paragraphs(paragraphs)
        if not questions:
            return {"error": "Không tìm thấy câu hỏi trắc nghiệm hợp lệ nào trong file Word. Thầy/Cô vui lòng tải 'File Word Mẫu' bên trên để đối chiếu định dạng (Câu 1:, A., B., C., D., Đáp án: A)."}
        return {"status": "success", "count": len(questions), "questions": questions}

    @staticmethod
    def parse_mcq_text(raw_text: str) -> Dict[str, Any]:
        """Phân tích các câu hỏi trắc nghiệm từ văn bản thô (dán từ Word/Clipboard)"""
        paragraphs = parse_raw_text_to_paragraphs(raw_text)
        if not paragraphs:
            return {"error": "Văn bản dán vào bị trống!"}
        questions = parse_mcqs_from_paragraphs(paragraphs)
        if not questions:
            return {"error": "Không tìm thấy câu hỏi trắc nghiệm hợp lệ nào trong văn bản dán. Vui lòng kiểm tra lại định dạng."}
        return {"status": "success", "count": len(questions), "questions": questions}

    @staticmethod
    def add_mcq_batch(questions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Thêm hàng loạt câu hỏi trắc nghiệm vào ngân hàng (nhập từ Word hoặc dán)"""
        if not questions or not isinstance(questions, list):
            return {"error": "Danh sách câu hỏi không hợp lệ!"}
        data = load_questions_bank_data()
        mcq_list = data.setdefault("multiple_choice", [])
        existing_ids = [q.get("id", 0) for q in mcq_list if isinstance(q.get("id"), int)]
        next_id = max(existing_ids, default=0) + 1

        added_count = 0
        added_items = []
        for item in questions:
            q_text = str(item.get("question", "")).strip()
            if not q_text:
                continue
            opts = item.get("options", [])
            opts_clean = [str(o).strip() for o in opts if str(o).strip()]
            if len(opts_clean) < 2:
                continue
            try:
                c_idx = int(item.get("correct_index", 0))
            except Exception:
                c_idx = 0
            if c_idx < 0 or c_idx >= len(opts_clean):
                c_idx = 0

            new_q = {
                "id": next_id,
                "group": str(item.get("group", "")).strip() or "Nghị định 30/2020/NĐ-CP",
                "question": q_text,
                "options": opts_clean,
                "correct_index": c_idx,
                "explanation": str(item.get("explanation", "")).strip()
            }
            mcq_list.append(new_q)
            added_items.append(new_q)
            next_id += 1
            added_count += 1

        if added_count == 0:
            return {"error": "Không có câu hỏi hợp lệ nào được thêm!"}

        save_questions_bank_data(data)
        return {
            "status": "success",
            "message": f"Đã nhập thành công {added_count} câu hỏi trắc nghiệm vào ngân hàng!",
            "added_count": added_count,
            "total_mcqs": len(mcq_list)
        }

    @staticmethod
    def get_sample_mcq_docx_path() -> str:
        """Lấy đường dẫn file Word mẫu trắc nghiệm (tự sinh nếu chưa có)"""
        sample_path = os.path.join(TEMPLATE_STORAGE, "Mau_Cau_Hoi_Trac_Nghiem.docx")
        if not os.path.exists(sample_path):
            create_mcq_sample_docx(sample_path)
        return sample_path

    @staticmethod
    def add_practice_case(bucket: str = "A", doc_type: str = "CÔNG VĂN ĐỀ NGHỊ", title: str = "", context: str = "", requirements: List[str] = None) -> Dict[str, Any]:
        """Thêm tình huống thực hành vào Gói A (Công văn đề nghị) hoặc Gói B (Tờ trình / Thông báo)"""
        b_clean = str(bucket or "A").strip().upper()
        if b_clean not in ["A", "B"]:
            b_clean = "A"

        if not title.strip():
            return {"error": "Tiêu đề đề bài không được để trống!"}
        if not context.strip():
            return {"error": "Bối cảnh đề bài không được để trống!"}

        reqs_clean = [r.strip() for r in (requirements or []) if r and r.strip()]
        if not reqs_clean:
            reqs_clean = ["Trình bày đúng quy cách theo Nghị định 30/2020/NĐ-CP."]

        data = load_questions_bank_data()
        key = "practice_cases_a" if b_clean == "A" else "practice_cases_b"
        cases_list = data.setdefault(key, [])

        new_case_id = f"{b_clean}{len(cases_list) + 1}"
        new_case = {
            "case_id": new_case_id,
            "doc_type": doc_type.strip() or ("CÔNG VĂN ĐỀ NGHỊ" if b_clean == "A" else "TỜ TRÌNH"),
            "title": title.strip(),
            "context": context.strip(),
            "requirements": reqs_clean
        }
        cases_list.append(new_case)
        save_questions_bank_data(data)
        b_label = "Gói A (Công văn đề nghị - 4 điểm)" if b_clean == "A" else "Gói B (Tờ trình / Thông báo - 4 điểm)"
        return {"status": "success", "message": f"Đã thêm đề bài [{new_case_id}] vào {b_label} thành công!", "case": new_case}

    @staticmethod
    def delete_practice_case(bucket: str, case_id: str) -> Dict[str, Any]:
        """Xóa đề bài tự luận khỏi Gói A hoặc Gói B"""
        b_clean = str(bucket or "").strip().upper()
        data = load_questions_bank_data()
        target_case_id_str = str(case_id).strip().lower()

        keys_to_search = []
        if b_clean == "A":
            keys_to_search = ["practice_cases_a"]
        elif b_clean == "B":
            keys_to_search = ["practice_cases_b"]
        else:
            keys_to_search = ["practice_cases_a", "practice_cases_b"]

        found = False
        for key in keys_to_search:
            cases_list = data.setdefault(key, [])
            for idx, c in enumerate(cases_list):
                c_id = str(c.get("case_id") or c.get("id") or "").strip().lower()
                if c_id == target_case_id_str:
                    cases_list.pop(idx)
                    found = True
                    break
            if found:
                break

        if not found:
            return {"error": f"Không tìm thấy đề bài {case_id} để xóa!"}

        save_questions_bank_data(data)
        return {"status": "success", "message": f"Đã xóa đề bài {case_id} thành công!"}

    @staticmethod
    def clear_questions_bank(target: str = "all") -> Dict[str, Any]:
        """Làm sạch kho dữ liệu câu hỏi trắc nghiệm hoặc đề tự luận"""
        data = load_questions_bank_data()
        msg_parts = []
        if target in ["all", "mcq"]:
            old_mcq_count = len(data.get("multiple_choice", []))
            data["multiple_choice"] = []
            msg_parts.append(f"{old_mcq_count} câu hỏi trắc nghiệm")
        if target in ["all", "cases", "cases_a"]:
            old_a = len(data.get("practice_cases_a", []))
            data["practice_cases_a"] = []
            msg_parts.append(f"{old_a} đề Gói A (Công văn đề nghị)")
        if target in ["all", "cases", "cases_b"]:
            old_b = len(data.get("practice_cases_b", []))
            data["practice_cases_b"] = []
            msg_parts.append(f"{old_b} đề Gói B (Tờ trình / Thông báo)")

        save_questions_bank_data(data)
        detail_msg = ", ".join(msg_parts) if msg_parts else "dữ liệu"
        return {
            "status": "success",
            "message": f"Đã làm sạch kho dữ liệu ({detail_msg}) thành công! Thầy/Cô có thể chủ động thêm mới đề thi.",
            "data": data
        }

    @staticmethod
    def restore_sample_questions_bank() -> Dict[str, Any]:
        """Khôi phục lại kho câu hỏi và đề thi mẫu ban đầu chuẩn Nghị định 30 theo cấu trúc mới: Gói A (Công văn đề nghị) và Gói B (Tờ trình / Thông báo)"""
        sample_a = [
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
        sample_b = [
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
        data = load_questions_bank_data()
        data["practice_cases_a"] = sample_a
        data["practice_cases_b"] = sample_b
        save_questions_bank_data(data)
        return {
            "status": "success",
            "message": "Đã khôi phục toàn bộ câu hỏi trắc nghiệm và đề tự luận chuẩn cấu trúc mới: Gói A (Công văn đề nghị) và Gói B (Tờ trình & Thông báo) thành công!",
            "data": data
        }

    # ================= SINH ĐỀ THI CHO THÍ SINH =================
    @staticmethod
    def generate_exam_for_student(
        student_id: str, 
        student_name: str, 
        cohort: str = "Khóa 1",
        class_name: str = "Lớp 01 - Văn thư lưu trữ",
        duration_minutes: int = 60,
        force_new: bool = False,
        sbd: str = ""
    ) -> Dict[str, Any]:
        now = time.time()
        sbd_val = str(sbd).strip() if sbd else student_id
        existing = ACTIVE_SESSIONS.get(student_id)
        if existing and not force_new:
            # 1. Nếu sinh viên đã nộp bài và chưa được Giảng viên cho phép làm lại
            if existing.get("is_submitted", False):
                return {
                    "error": "Bạn đã nộp bài thi rồi! Nếu lỡ tay bấm nộp nhầm và muốn làm tiếp, vui lòng báo Giảng viên mở lại bài thi cho bạn."
                }
            # 2. Nếu phiên thi đang mở (hoặc vừa được Giảng viên mở lại), khôi phục bài làm dở
            rem_sec = max(0, int(existing.get("end_time", now) - now))
            if rem_sec > 0:
                return {
                    "student_id": student_id,
                    "student_name": existing.get("student_name", student_name),
                    "sbd": existing.get("sbd", sbd_val),
                    "cohort": existing.get("cohort", cohort),
                    "class_name": existing.get("class_name", class_name),
                    "duration_minutes": existing.get("duration_minutes", duration_minutes),
                    "remaining_seconds": rem_sec,
                    "quiz_questions": existing.get("quiz_questions", []),
                    "practice_cases": [
                        {
                            "case_index": idx + 1,
                            "context": c.get("context", ""),
                            "requirements": c.get("requirements", [])
                        }
                        for idx, c in enumerate(existing.get("practice_cases", []))
                    ],
                    "exam_token": existing.get("exam_token", ""),
                    "is_resumed": True
                }

        qbank_data = load_questions_bank_data()
        mcq_count = int(qbank_data.get("config", {}).get("mcq_count", 10))
        if mcq_count not in [5, 10]:
            mcq_count = 10

        pool = copy.deepcopy(qbank_data.get("multiple_choice", []))
        if not pool:
            return {
                "error": "Ngân hàng trắc nghiệm hiện đang trống! Giảng viên vui lòng vào bảng điều khiển Giảng viên để thêm câu hỏi trắc nghiệm trước khi cho sinh viên bắt đầu thi."
            }

        pool_a = qbank_data.get("practice_cases_a", [])
        if not pool_a:
            return {
                "error": "Ngân hàng đề tự luận Gói A (Công văn đề nghị) hiện đang trống! Giảng viên vui lòng thêm đề Gói A trước khi cho sinh viên thi."
            }

        pool_b = qbank_data.get("practice_cases_b", [])
        if not pool_b:
            return {
                "error": "Ngân hàng đề tự luận Gói B (Tờ trình / Thông báo) hiện đang trống! Giảng viên vui lòng thêm đề Gói B trước khi cho sinh viên thi."
            }

        selected_count = min(mcq_count, len(pool))
        selected_raw_questions = random.sample(pool, selected_count)
        
        exam_questions = []
        answer_keys = {}

        for idx, q in enumerate(selected_raw_questions, 1):
            q_id = q["id"]
            correct_text = q["options"][q["correct_index"]]
            answer_keys[str(q_id)] = correct_text

            options = copy.deepcopy(q["options"])
            random.shuffle(options)

            exam_questions.append({
                "index": idx,
                "question_id": q_id,
                "group": q.get("group", ""),
                "question": q["question"],
                "options": options
            })

        case_a = copy.deepcopy(random.choice(pool_a))
        case_b = copy.deepcopy(random.choice(pool_b))

        start_time = time.time()
        end_time = start_time + (duration_minutes * 60)
        exam_token = f"TOKEN_EXAM_{uuid.uuid4().hex[:12].upper()}"

        session_data = {
            "student_id": student_id,
            "student_name": student_name,
            "sbd": sbd_val,
            "cohort": cohort,
            "class_name": class_name,
            "duration_minutes": duration_minutes,
            "start_time": start_time,
            "end_time": end_time,
            "exam_token": exam_token,
            "is_submitted": False,
            "is_terminated": False,
            "termination_reason": "",
            "extra_minutes_added": 0,
            "quiz_questions": exam_questions,
            "quiz_keys": answer_keys,
            "practice_cases": [case_a, case_b],
            "quiz_score": 0.0,
            "word_scores": {},
            "final_score": 0.0,
            "anti_cheat_overall": "SAFE"
        }

        ACTIVE_SESSIONS[student_id] = session_data

        return {
            "student_id": student_id,
            "student_name": student_name,
            "sbd": sbd_val,
            "cohort": cohort,
            "class_name": class_name,
            "duration_minutes": duration_minutes,
            "remaining_seconds": int(end_time - start_time),
            "quiz_questions": exam_questions,
            "practice_cases": [
                {
                    "case_index": 1,
                    "context": case_a.get("context", ""),
                    "requirements": case_a.get("requirements", [])
                },
                {
                    "case_index": 2,
                    "context": case_b.get("context", ""),
                    "requirements": case_b.get("requirements", [])
                }
            ],
            "exam_token": exam_token
        }

    @staticmethod
    def extend_student_time(student_id: str, extra_minutes: int) -> Dict[str, Any]:
        """Giáo viên gia hạn thêm thời gian nộp bài cho sinh viên cụ thể"""
        session = ACTIVE_SESSIONS.get(student_id)
        if not session:
            return {"error": "Không tìm thấy phiên thi của sinh viên này"}
        if extra_minutes <= 0:
            return {"error": "Số phút gia hạn phải lớn hơn 0"}

        now = time.time()
        # Nếu đã hết giờ thì tính thêm từ thời điểm hiện tại, nếu còn giờ thì cộng nối tiếp
        base_time = max(now, session.get("end_time", now))
        new_end_time = base_time + (extra_minutes * 60)
        session["end_time"] = new_end_time
        session["duration_minutes"] = session.get("duration_minutes", 60) + extra_minutes
        session["extra_minutes_added"] = session.get("extra_minutes_added", 0) + extra_minutes
        session["is_submitted"] = False
        session["is_terminated"] = False
        session["termination_reason"] = ""

        remaining_sec = max(0, int(new_end_time - now))
        return {
            "status": "success",
            "student_id": student_id,
            "student_name": session.get("student_name", ""),
            "remaining_seconds": remaining_sec,
            "extra_minutes_added": session["extra_minutes_added"],
            "message": f"Đã gia hạn thành công thêm {extra_minutes} phút cho thí sinh {session.get('student_name', student_id)}"
        }

    @staticmethod
    def terminate_student_exam(student_id: str, reason: str = "Giáo viên đình chỉ thi") -> Dict[str, Any]:
        """Giáo viên cho ngừng / đình chỉ thi bất cứ sinh viên nào khi đang thi"""
        session = ACTIVE_SESSIONS.get(student_id)
        if not session:
            return {"error": "Không tìm thấy phiên thi của sinh viên này"}

        reason_clean = reason.strip() if reason else "Giáo viên đình chỉ / thu bài bắt buộc"
        session["is_terminated"] = True
        session["termination_reason"] = reason_clean
        session["end_time"] = time.time()
        session["is_submitted"] = True

        return {
            "status": "success",
            "student_id": student_id,
            "student_name": session.get("student_name", ""),
            "termination_reason": reason_clean,
            "message": f"Đã đình chỉ / thu bài ngay lập tức đối với thí sinh {session.get('student_name', student_id)}"
        }

    @staticmethod
    def reopen_or_retake_exam(student_id: str, mode: str = "resume", extra_minutes: int = 15) -> Dict[str, Any]:
        """Giáo viên cho phép sinh viên làm lại bài thi khi lỡ bấm nộp nhầm hoặc cần thi lại"""
        session = ACTIVE_SESSIONS.get(student_id)
        if not session:
            return {"error": "Không tìm thấy phiên thi của sinh viên này"}

        student_name = session.get("student_name", student_id)
        now = time.time()

        if mode == "restart":
            # 1. CHO LÀM LẠI TỪ ĐẦU (CẤP ĐỀ MỚI TINH)
            cohort = session.get("cohort", "Khóa 1")
            class_name = session.get("class_name", "Lớp 01")
            duration = int(session.get("duration_minutes", 60))
            if extra_minutes and extra_minutes > 0:
                duration = max(duration, extra_minutes)

            new_exam = ExamEngine.generate_exam_for_student(
                student_id=student_id,
                student_name=student_name,
                cohort=cohort,
                class_name=class_name,
                duration_minutes=duration,
                force_new=True
            )
            new_session = ACTIVE_SESSIONS[student_id]
            new_session["is_reopened"] = True
            new_session["reopened_mode"] = "restart"
            new_session["reopened_at"] = now
            return {
                "status": "success",
                "mode": "restart",
                "student_id": student_id,
                "student_name": student_name,
                "duration_minutes": duration,
                "remaining_seconds": int(new_session["end_time"] - now),
                "message": f"Đã cấp đề thi mới hoàn toàn và mở lại phiên thi từ đầu cho thí sinh {student_name} ({duration} phút)."
            }
        else:
            # 2. MỞ LẠI BÀI ĐANG LÀM DỞ ĐỂ LÀM TIẾP (LỠ BẤM NỘP NHẦM)
            base_time = max(now, session.get("end_time", now))
            extra = max(0, extra_minutes)
            cur_rem = max(0, int(session.get("end_time", 0) - now))
            if cur_rem < 300 and extra == 0:
                extra = 15

            new_end_time = base_time + (extra * 60)
            session["end_time"] = new_end_time
            if extra > 0:
                session["extra_minutes_added"] = session.get("extra_minutes_added", 0) + extra
                session["duration_minutes"] = session.get("duration_minutes", 60) + extra

            session["is_submitted"] = False
            session["is_terminated"] = False
            session["termination_reason"] = ""
            session["is_reopened"] = True
            session["reopened_mode"] = "resume"
            session["reopened_at"] = now

            remaining_sec = max(0, int(new_end_time - now))
            rem_m = max(1, int(remaining_sec / 60))
            return {
                "status": "success",
                "mode": "resume",
                "student_id": student_id,
                "student_name": student_name,
                "remaining_seconds": remaining_sec,
                "extra_minutes_added": session.get("extra_minutes_added", 0),
                "message": f"Đã mở lại bài thi thành công! Thí sinh {student_name} có thể tiếp tục làm bài (còn ~{rem_m} phút)."
            }

    @staticmethod
    def create_official_docx_template(student_id: str, case_index: int) -> str:
        session = ACTIVE_SESSIONS.get(student_id)
        token = session.get("exam_token", "DEFAULT_TOKEN") if session else "DEFAULT_TOKEN"
        s_name = session.get("student_name", "ThiSinh") if session else "ThiSinh"
        sbd = session.get("sbd", student_id) if session else student_id
        cohort = session.get("cohort", "Khóa 1") if session else "Khóa 1"
        c_name = session.get("class_name", "Lớp 01") if session else "Lớp 01"

        out_path = os.path.join(TEMPLATE_STORAGE, f"Phoi_Thi_VB{case_index}_{student_id}.docx")
        iso_now = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")

        content_types_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
</Types>"""

        rels_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>"""

        core_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:dcmitype="http://purl.org/dc/dcmitype/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:title>Bài Thi Soạn Thảo Văn Bản - {cohort} - {c_name}</dc:title>
  <dc:creator>SBD: {sbd} - MSSV: {student_id} - {s_name}</dc:creator>
  <cp:keywords>{token}</cp:keywords>
  <cp:lastModifiedBy>{student_id}</cp:lastModifiedBy>
  <dcterms:created xsi:type="dcterms:W3CDTF">{iso_now}</dcterms:created>
  <dcterms:modified xsi:type="dcterms:W3CDTF">{iso_now}</dcterms:modified>
</cp:coreProperties>"""

        app_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
  <Template>Normal.dotm</Template>
  <TotalTime>1</TotalTime>
  <Pages>1</Pages>
  <Words>50</Words>
  <Characters>300</Characters>
  <Application>Microsoft Office Word</Application>
  <Company>HeThongThiNghiDinh30</Company>
</Properties>"""

        document_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:tbl>
      <w:tblPr>
        <w:tblW w:w="0" w:type="auto"/>
        <w:tblBorders>
          <w:top w:val="none"/><w:left w:val="none"/><w:bottom w:val="none"/><w:right w:val="none"/>
          <w:insideH w:val="none"/><w:insideV w:val="none"/>
        </w:tblBorders>
      </w:tblPr>
      <w:tr>
        <w:tc>
          <w:tcPr><w:tcW w:w="4500" w:type="dxa"/></w:tcPr>
          <w:p>
            <w:pPr><w:jc w:val="center"/><w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"/><w:sz w:val="24"/></w:rPr></w:pPr>
            <w:r><w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"/><w:sz w:val="24"/></w:rPr><w:t>CƠ QUAN CHỦ QUẢN</w:t></w:r>
          </w:p>
          <w:p>
            <w:pPr><w:jc w:val="center"/><w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"/><w:b/><w:sz w:val="24"/></w:rPr></w:pPr>
            <w:r><w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"/><w:b/><w:sz w:val="24"/></w:rPr><w:t>TÊN CƠ QUAN BAN HÀNH</w:t></w:r>
          </w:p>
          <w:p>
            <w:pPr><w:jc w:val="center"/><w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"/><w:sz w:val="26"/></w:rPr></w:pPr>
            <w:r><w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"/><w:sz w:val="26"/></w:rPr><w:t>Số: ...../......-......</w:t></w:r>
          </w:p>
        </w:tc>
        <w:tc>
          <w:tcPr><w:tcW w:w="5000" w:type="dxa"/></w:tcPr>
          <w:p>
            <w:pPr><w:jc w:val="center"/><w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"/><w:b/><w:sz w:val="24"/></w:rPr></w:pPr>
            <w:r><w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"/><w:b/><w:sz w:val="24"/></w:rPr><w:t>CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM</w:t></w:r>
          </w:p>
          <w:p>
            <w:pPr><w:jc w:val="center"/><w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"/><w:b/><w:sz w:val="26"/></w:rPr></w:pPr>
            <w:r><w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"/><w:b/><w:sz w:val="26"/></w:rPr><w:t>Độc lập - Tự do - Hạnh phúc</w:t></w:r>
          </w:p>
          <w:p>
            <w:pPr><w:jc w:val="center"/><w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"/><w:i/><w:sz w:val="26"/></w:rPr></w:pPr>
            <w:r><w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"/><w:i/><w:sz w:val="26"/></w:rPr><w:t>Hà Nội, ngày ... tháng ... năm 2026</w:t></w:r>
          </w:p>
        </w:tc>
      </w:tr>
    </w:tbl>
    <w:p>
      <w:pPr><w:spacing w:before="240"/><w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"/><w:sz w:val="28"/><w:b/></w:rPr></w:pPr>
      <w:r><w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"/><w:sz w:val="28"/><w:b/></w:rPr><w:t>[BÀI THI - SBD: {sbd} | MSSV: {student_id} - {s_name} ({cohort} - {c_name})]</w:t></w:r>
    </w:p>
    <w:sectPr>
      <w:pgSz w:w="11906" w:h="16838"/>
      <w:pgMar w:top="1134" w:right="850" w:bottom="1134" w:left="1701" w:header="708" w:footer="708" w:gutter="0"/>
    </w:sectPr>
  </w:body>
</w:document>"""

        with zipfile.ZipFile(out_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.writestr('[Content_Types].xml', content_types_xml)
            zf.writestr('_rels/.rels', rels_xml)
            zf.writestr('docProps/core.xml', core_xml)
            zf.writestr('docProps/app.xml', app_xml)
            zf.writestr('word/document.xml', document_xml)

        return out_path

    @staticmethod
    def submit_quiz(student_id: str, student_answers: Dict[str, str]) -> Dict[str, Any]:
        session = ACTIVE_SESSIONS.get(student_id)
        if not session:
            return {"error": "Không tìm thấy phiên thi của sinh viên này!"}

        sec_cfg = GradingService.get_sections()
        quiz_max = float(sec_cfg.get("quiz_max", 3.0))

        keys = session["quiz_keys"]
        total_questions = len(keys)
        correct_count = 0
        details = []

        for q_id, correct_text in keys.items():
            user_ans = student_answers.get(str(q_id), "")
            is_correct = (user_ans.strip() == correct_text.strip())
            if is_correct:
                correct_count += 1
            details.append({
                "question_id": q_id,
                "user_answer": user_ans,
                "is_correct": is_correct
            })

        quiz_score = round((correct_count / total_questions) * quiz_max, 2)
        session["quiz_score"] = quiz_score
        session["quiz_results"] = {
            "correct_count": correct_count,
            "total_questions": total_questions,
            "score": quiz_score,
            "max_score": quiz_max,
            "details": details
        }
        return session["quiz_results"]

    @staticmethod
    def grade_practice_file(student_id: str, docx_path: str, case_index: int) -> Dict[str, Any]:
        session = ACTIVE_SESSIONS.get(student_id)
        if not session:
            return {"error": "Không tìm thấy phiên thi!"}

        token = session.get("exam_token")
        grader = DocxNghiDinh30Grader(docx_path, expected_student_id=student_id, expected_token=token)
        grade_result = grader.grade()

        sec_cfg = GradingService.get_sections()
        fmt_key = f"case_{case_index}_format_max"
        format_max = float(sec_cfg.get(fmt_key, 2.0))
        raw_max = float(grade_result.get("max_score", 10.0))
        if raw_max <= 0:
            raw_max = 10.0

        format_score_scaled = round((grade_result["score"] / raw_max) * format_max, 2)
        anti_cheat = grade_result.get("anti_cheat", {})

        session["word_scores"][f"case_{case_index}"] = {
            "format_score": format_score_scaled,
            "format_max": format_max,
            "content_score_pending": True,
            "details": grade_result["details"],
            "anti_cheat": anti_cheat,
            "metadata": grade_result.get("metadata", {})
        }

        # Tổng hợp chi tiết các lỗi gian lận từ cả 2 văn bản
        c1_ac = session["word_scores"].get("case_1", {}).get("anti_cheat", {})
        c2_ac = session["word_scores"].get("case_2", {}).get("anti_cheat", {})

        all_violations = []
        for ac_item in [c1_ac, c2_ac]:
            for v in ac_item.get("violations", []):
                if v not in all_violations:
                    all_violations.append(v)

        session["anti_cheat_violations"] = all_violations
        session["anti_cheat_summary"] = ", ".join(all_violations) if all_violations else "Hợp lệ"

        if c1_ac.get("status") == "FLAGGED" or c2_ac.get("status") == "FLAGGED":
            session["anti_cheat_overall"] = "FLAGGED"
        elif c1_ac.get("status") == "WARNING" or c2_ac.get("status") == "WARNING":
            session["anti_cheat_overall"] = "WARNING"
        else:
            session["anti_cheat_overall"] = "SAFE"

        return {
            "case_index": case_index,
            "format_score": format_score_scaled,
            "format_max": format_max,
            "details": grade_result["details"],
            "anti_cheat": anti_cheat
        }
