"""
Máy chủ phiên bản Lite: Hỗ trợ Quản lý theo Khóa - Lớp, Phòng thi Sinh viên, Bàn chấm Giảng viên và Engine Chống Gian Lận.
Tương thích 100% Python 3.10 - 3.13+, không cần cài đặt pip packages.
"""

import http.server
import socketserver
import json
import os
import re
import io
import socket
import time
import urllib.parse
from urllib.parse import urlparse, parse_qs
from exam_engine import ExamEngine, ACTIVE_SESSIONS, COHORTS_AND_CLASSES
from gdrive_service import GDriveService
from grading_service import GradingService

PORT = int(os.environ.get("PORT", 8000))
BASE_DIR = os.path.dirname(__file__)
FRONTEND_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "frontend"))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

def get_all_lan_ips():
    """Lấy danh sách tất cả IPv4 của máy chủ, ưu tiên IP Wi-Fi/LAN thật và xếp card ảo WSL/Hyper-V xuống cuối"""
    ips = []
    try:
        hostname = socket.gethostname()
        for ip in socket.gethostbyname_ex(hostname)[2]:
            if not ip.startswith("127.") and ip not in ips:
                ips.append(ip)
    except Exception:
        pass

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        sock_ip = s.getsockname()[0]
        s.close()
        if sock_ip and not sock_ip.startswith("127.") and sock_ip not in ips:
            ips.append(sock_ip)
    except Exception:
        pass

    if not ips:
        return ["127.0.0.1"]

    def ip_priority(ip):
        if ip.startswith("192.168."):
            return 1
        if ip.startswith("10."):
            return 2
        if ip.startswith("172."):
            try:
                second = int(ip.split('.')[1])
                if 16 <= second <= 31:
                    return 10  # Dải WSL/Hyper-V ảo xếp cuối cùng
            except Exception:
                pass
            return 3
        return 5

    ips.sort(key=ip_priority)
    return ips

def get_primary_lan_ip():
    ips = get_all_lan_ips()
    return ips[0] if ips else "127.0.0.1"

class ExamHandler(http.server.SimpleHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        # 1. GIAO DIỆN WEB
        if path == "/" or path == "/index.html":
            self.serve_file(os.path.join(FRONTEND_DIR, "index.html"), "text/html; charset=utf-8")
        elif path == "/teacher" or path == "/teacher.html":
            self.serve_file(os.path.join(FRONTEND_DIR, "teacher.html"), "text/html; charset=utf-8")
        elif path.startswith("/static/"):
            rel_file = path[len("/static/"):]
            file_path = os.path.join(FRONTEND_DIR, rel_file)
            content_type = "text/plain"
            if rel_file.endswith(".css"): content_type = "text/css"
            elif rel_file.endswith(".js"): content_type = "application/javascript"
            self.serve_file(file_path, content_type)

        # 2. DANH MỤC KHÓA & LỚP
        elif path == "/api/classes":
            self.send_json({"status": "success", "catalog": ExamEngine.get_classes_catalog()})

        # 3. TẢI PHÔI THI CHÍNH THỨC CÓ NHÚNG TOKEN BẢO MẬT & KHÓA LỚP
        elif path.startswith("/api/exam/download-template/"):
            parts = path.split("/")
            if len(parts) >= 6:
                student_id = parts[4]
                case_index = int(parts[5])
                docx_path = ExamEngine.create_official_docx_template(student_id, case_index)
                if os.path.exists(docx_path):
                    self.serve_file(
                        docx_path,
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        filename=f"Phoi_Thi_VB{case_index}_{student_id}.docx"
                    )
                    return
            self.send_error(404, "Không tìm thấy phôi thi")

        # 3b. ĐỒNG BỘ PHIÊN THI SINH VIÊN (GIA HẠN / ĐÌNH CHỈ)
        elif path.startswith("/api/exam/session/"):
            parts = parsed.path.split("/")
            student_id = parts[-1]
            session = ACTIVE_SESSIONS.get(student_id)
            if not session:
                self.send_json({"error": "Không tìm thấy sinh viên"}, 404)
                return
            remaining = max(0, int(session.get("end_time", time.time()) - time.time()))
            if remaining <= 0 and not session.get("is_submitted", False):
                session["is_submitted"] = True

            req_device_id = query_params.get("device_id", [None])[0]
            is_device_mismatch = False
            bound_dev = session.get("device_id")
            if bound_dev and req_device_id and bound_dev != req_device_id.strip():
                is_device_mismatch = True

            self.send_json({
                "student_id": session["student_id"],
                "student_name": session["student_name"],
                "sbd": session.get("sbd", session["student_id"]),
                "cohort": session.get("cohort", "Khóa 1"),
                "class_name": session.get("class_name", "Lớp 01"),
                "remaining_seconds": remaining,
                "is_submitted": session.get("is_submitted", False),
                "is_terminated": session.get("is_terminated", False),
                "termination_reason": session.get("termination_reason", ""),
                "is_device_mismatch": is_device_mismatch,
                "device_info": session.get("device_info", ""),
                "current_phase": session.get("current_phase", "QUIZ"),
                "extra_minutes_added": session.get("extra_minutes_added", 0),
                "duration_minutes": session.get("duration_minutes", 60),
                "quiz_score": session.get("quiz_score", 0.0),
                "word_scores": session.get("word_scores", {})
            })

        # 4. BÁO CÁO KẾT QUẢ SINH VIÊN
        elif path.startswith("/api/exam/final-report/"):
            student_id = path.split("/")[-1]
            session = ACTIVE_SESSIONS.get(student_id)
            if not session:
                self.send_json({"error": "Không tìm thấy sinh viên"}, 404)
                return
            session["is_submitted"] = True
            quiz = session.get("quiz_results", {})
            words = session.get("word_scores", {})
            quiz_pt = quiz.get("score", 0.0)
            w1_pt = words.get("case_1", {}).get("format_score", 0.0)
            w2_pt = words.get("case_2", {}).get("format_score", 0.0)
            sec_cfg = GradingService.get_sections()
            self.send_json({
                "student_id": session["student_id"],
                "student_name": session["student_name"],
                "sbd": session.get("sbd", session["student_id"]),
                "cohort": session.get("cohort", "Khóa 1"),
                "class_name": session.get("class_name", "Lớp 01"),
                "quiz_score": quiz_pt,
                "quiz_correct": f"{quiz.get('correct_count', 0)}/{quiz.get('total_questions', 0)}",
                "word_case_1_format_score": w1_pt,
                "word_case_2_format_score": w2_pt,
                "total_format_score": round(quiz_pt + w1_pt + w2_pt, 2),
                "sections_config": sec_cfg,
                "anti_cheat_overall": session.get("anti_cheat_overall", "SAFE"),
                "anti_cheat_violations": session.get("anti_cheat_violations", []),
                "anti_cheat_summary": session.get("anti_cheat_summary", "Hợp lệ"),
                "is_terminated": session.get("is_terminated", False),
                "termination_reason": session.get("termination_reason", "")
            })
        elif path == "/api/exam/download-spec":
            spec_file = os.path.abspath(os.path.join(BASE_DIR, "..", "SO_TAY_THE_THUC_NGHI_DINH_30_O_1_DEN_O_9.md"))
            self.serve_file(spec_file, "text/markdown; charset=utf-8")

        # 5. API GIẢNG VIÊN (TEACHER DASHBOARD) - CÓ LỌC THEO KHÓA & LỚP
        elif path == "/api/teacher/students":
            filter_cohort = query.get("cohort", [""])[0].strip()
            filter_class = query.get("class_name", [""])[0].strip()

            links_store = GDriveService.load_links()
            student_list = []
            for s_id, s_data in ACTIVE_SESSIONS.items():
                s_cohort = s_data.get("cohort", "Khóa 1")
                s_class = s_data.get("class_name", "Lớp 01")

                if filter_cohort and filter_cohort != "ALL" and s_cohort != filter_cohort:
                    continue
                if filter_class and filter_class != "ALL" and s_class != filter_class:
                    continue

                quiz = s_data.get("quiz_results", {})
                words = s_data.get("word_scores", {})
                
                quiz_score = quiz.get("score", 0.0)
                w1_format = words.get("case_1", {}).get("format_score", 0.0)
                w1_content = words.get("case_1", {}).get("content_score", 0.0)
                w2_format = words.get("case_2", {}).get("format_score", 0.0)
                w2_content = words.get("case_2", {}).get("content_score", 0.0)

                total_score = round(quiz_score + w1_format + w1_content + w2_format + w2_content, 2)
                is_graded = ("content_score" in words.get("case_1", {})) and ("content_score" in words.get("case_2", {}))
                rem_sec = max(0, int(s_data.get("end_time", time.time()) - time.time()))

                s_glinks = links_store.get(s_id, {})
                c1_drive = s_data.get("gdrive_links", {}).get("case_1", {}) or s_glinks.get("case_1", {})
                c2_drive = s_data.get("gdrive_links", {}).get("case_2", {}) or s_glinks.get("case_2", {})

                p_cases = s_data.get("practice_cases") or []
                c1_meta = p_cases[0] if len(p_cases) > 0 else {}
                c2_meta = p_cases[1] if len(p_cases) > 1 else {}

                student_list.append({
                    "student_id": s_id,
                    "student_name": s_data.get("student_name", ""),
                    "sbd": s_data.get("sbd", s_id),
                    "cohort": s_cohort,
                    "class_name": s_class,
                    "is_submitted": s_data.get("is_submitted", False),
                    "is_terminated": s_data.get("is_terminated", False),
                    "termination_reason": s_data.get("termination_reason", ""),
                    "remaining_seconds": rem_sec,
                    "extra_minutes_added": s_data.get("extra_minutes_added", 0),
                    "duration_minutes": s_data.get("duration_minutes", 60),
                    "quiz_score": quiz_score,
                    "quiz_correct": f"{quiz.get('correct_count', 0)}/{quiz.get('total_questions', 0)}",
                    "anti_cheat_overall": s_data.get("anti_cheat_overall", "SAFE"),
                    "anti_cheat_violations": s_data.get("anti_cheat_violations", []),
                    "anti_cheat_summary": s_data.get("anti_cheat_summary", "Hợp lệ"),
                    "device_info": s_data.get("device_info", "Chưa xác định"),
                    "device_first_login": s_data.get("device_first_login", ""),
                    "current_phase": s_data.get("current_phase", "QUIZ"),
                    "exam_token": s_data.get("exam_token", ""),
                    "case_1": {
                        "title": c1_meta.get("title", "Văn bản 1"),
                        "doc_type": c1_meta.get("doc_type", ""),
                        "format_score": w1_format,
                        "content_score": w1_content,
                        "details": words.get("case_1", {}).get("details", []),
                        "anti_cheat": words.get("case_1", {}).get("anti_cheat", {}),
                        "gdrive_url": c1_drive.get("file_url", ""),
                        "gdrive_folder": c1_drive.get("folder_url", "")
                    },
                    "case_2": {
                        "title": c2_meta.get("title", "Văn bản 2"),
                        "doc_type": c2_meta.get("doc_type", ""),
                        "format_score": w2_format,
                        "content_score": w2_content,
                        "details": words.get("case_2", {}).get("details", []),
                        "anti_cheat": words.get("case_2", {}).get("anti_cheat", {}),
                        "gdrive_url": c2_drive.get("file_url", ""),
                        "gdrive_folder": c2_drive.get("folder_url", "")
                    },
                    "total_score": total_score,
                    "teacher_comment": s_data.get("teacher_comment", ""),
                    "is_graded": is_graded
                })
            self.send_json({
                "status": "success", 
                "students": student_list,
                "catalog": ExamEngine.get_classes_catalog(),
                "gdrive_config": GDriveService.load_config(),
                "grading_config": GradingService.load_config()
            })

        # 6. NGÂN HÀNG CÂU HỎI & BÀI THI (GET)
        elif path == "/api/teacher/questions-bank":
            self.send_json({
                "status": "success",
                "data": ExamEngine.get_questions_bank()
            })

        # 6b. TẢI FILE WORD MẪU CÂU HỎI TRẮC NGHIỆM (GET)
        elif path == "/api/teacher/questions/sample-docx":
            sample_file = ExamEngine.get_sample_mcq_docx_path()
            if os.path.exists(sample_file):
                self.serve_file(
                    sample_file,
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    filename="Mau_De_Thi_Trac_Nghiem_Nghi_Dinh_30.docx"
                )
                return
            self.send_error(404, "Không tìm thấy file mẫu")

        # 7. CẤU HÌNH & MÃ NGUỒN GOOGLE DRIVE APPS SCRIPT (GET)
        elif path == "/api/teacher/gdrive-config":
            self.send_json({
                "status": "success",
                "config": GDriveService.load_config(),
                "apps_script_code": GDriveService.get_apps_script_code()
            })

        # 8. CẤU HÌNH THANG ĐIỂM & RUBRIC (GET)
        elif path == "/api/grading-config" or path == "/api/teacher/grading-config":
            self.send_json({
                "status": "success",
                "config": GradingService.load_config()
            })

        elif path.startswith("/api/teacher/download-file/"):
            parts = path.split("/")
            if len(parts) >= 6:
                student_id = parts[4]
                case_index = parts[5]
                student_dir = os.path.join(UPLOAD_DIR, student_id)
                found_file = None
                if os.path.exists(student_dir):
                    for fname in os.listdir(student_dir):
                        if fname.startswith(f"Case_{case_index}_"):
                            found_file = os.path.join(student_dir, fname)
                            break
                if found_file and os.path.exists(found_file):
                    self.serve_file(found_file, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
                    return
            self.send_error(404, "Chưa tìm thấy file bài làm")

        elif path == "/api/teacher/export-excel":
            filter_cohort = query.get("cohort", [""])[0].strip()
            filter_class = query.get("class_name", [""])[0].strip()

            links_store = GDriveService.load_links()
            sec_cfg = GradingService.get_sections()
            q_m = sec_cfg.get("quiz_max", 3.0)
            c1_f_m = sec_cfg.get("case_1_format_max", 2.0)
            c1_c_m = sec_cfg.get("case_1_content_max", 1.5)
            c2_f_m = sec_cfg.get("case_2_format_max", 2.0)
            c2_c_m = sec_cfg.get("case_2_content_max", 1.5)
            tot_m = round(q_m + c1_f_m + c1_c_m + c2_f_m + c2_c_m, 2)
            csv_lines = [
                f"STT,Khóa,Lớp,SBD,Mã sinh viên,Họ và tên,Điểm Trắc nghiệm ({q_m}đ),Thể thức VB1 - Công văn ({c1_f_m}đ),Nội dung VB1 ({c1_c_m}đ),Thể thức VB2 - Tờ trình/TB ({c2_f_m}đ),Nội dung VB2 ({c2_c_m}đ),Tổng điểm ({tot_m}đ),Chống Gian Lận,Link Drive VB1 (cttrung@ntt.edu.vn),Link Drive VB2 (cttrung@ntt.edu.vn),Trạng thái,Nhận xét giảng viên"
            ]
            stt = 1
            for s_id, s_data in ACTIVE_SESSIONS.items():
                s_cohort = s_data.get("cohort", "Khóa 1")
                s_class = s_data.get("class_name", "Lớp 01")

                if filter_cohort and filter_cohort != "ALL" and s_cohort != filter_cohort:
                    continue
                if filter_class and filter_class != "ALL" and s_class != filter_class:
                    continue

                quiz = s_data.get("quiz_results", {})
                words = s_data.get("word_scores", {})
                q_score = quiz.get("score", 0.0)
                w1_f = words.get("case_1", {}).get("format_score", 0.0)
                w1_c = words.get("case_1", {}).get("content_score", 0.0)
                w2_f = words.get("case_2", {}).get("format_score", 0.0)
                w2_c = words.get("case_2", {}).get("content_score", 0.0)
                total = round(q_score + w1_f + w1_c + w2_f + w2_c, 2)
                if s_data.get("is_terminated", False):
                    status = f"ĐÌNH CHỈ THI ({s_data.get('termination_reason', 'Vi phạm')})"
                elif w1_c > 0 or w2_c > 0:
                    status = "Đã chấm xong"
                elif not s_data.get("is_submitted", False) and (s_data.get("end_time", 0) > time.time()):
                    rem_m = max(1, int((s_data.get("end_time", 0) - time.time()) / 60))
                    status = f"Đang làm bài (còn {rem_m}p)"
                else:
                    status = "Chờ GV chấm"
                comment = (s_data.get("teacher_comment", "") or "").replace('"', '""')
                name = s_data.get("student_name", "").replace('"', '""')
                cheat = s_data.get("anti_cheat_overall", "SAFE")
                cheat_summary = s_data.get("anti_cheat_summary", "")
                if cheat_summary and cheat_summary != "Hợp lệ":
                    cheat_text = cheat_summary.replace('"', '""')
                else:
                    cheat_text = "Hợp lệ" if cheat == "SAFE" else ("Cảnh báo" if cheat == "WARNING" else "NGHI VẤN GIAN LẬN")

                s_glinks = links_store.get(s_id, {})
                c1_link = s_data.get("gdrive_links", {}).get("case_1", {}).get("file_url") or s_glinks.get("case_1", {}).get("file_url", "")
                c2_link = s_data.get("gdrive_links", {}).get("case_2", {}).get("file_url") or s_glinks.get("case_2", {}).get("file_url", "")

                s_sbd = s_data.get("sbd", s_id)
                line = f'{stt},"{s_cohort}","{s_class}","{s_sbd}","{s_id}","{name}",{q_score},{w1_f},{w1_c},{w2_f},{w2_c},{total},"{cheat_text}","{c1_link}","{c2_link}","{status}","{comment}"'
                csv_lines.append(line)
                stt += 1

            csv_content = "\ufeff" + "\n".join(csv_lines)
            data_bytes = csv_content.encode("utf-8")

            safe_c_name = "Tat_Ca_Cac_Lop"
            if filter_class and filter_class != "ALL":
                safe_c_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', filter_class)
            elif filter_cohort and filter_cohort != "ALL":
                safe_c_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', filter_cohort)

            self.send_response(200)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Type", "text/csv; charset=utf-8")
            self.send_header("Content-Disposition", f'attachment; filename="Bang_Diem_{safe_c_name}.csv"')
            self.send_header("Content-Length", str(len(data_bytes)))
            self.end_headers()
            self.wfile.write(data_bytes)
        else:
            self.send_error(404, "Not Found")

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        content_type = self.headers.get('Content-Type', '')

        # 1. BẮT ĐẦU THI CÓ LƯU KHÓA VÀ LỚP
        if path == "/api/exam/start":
            length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(length).decode('utf-8'))
            s_id = str(body.get("student_id") or "").strip()
            s_sbd = str(body.get("sbd") or "").strip() or s_id
            exam_data = ExamEngine.generate_exam_for_student(
                student_id=s_id,
                student_name=body.get("student_name"),
                cohort=body.get("cohort", "Khóa 1"),
                class_name=body.get("class_name", "Lớp 01 - Văn thư lưu trữ"),
                duration_minutes=int(body.get("duration_minutes", 60)),
                sbd=s_sbd,
                device_id=str(body.get("device_id") or "").strip(),
                device_info=str(body.get("device_info") or "").strip()
            )
            if "error" in exam_data:
                self.send_json({"status": "error", "detail": exam_data["error"]}, 400)
            else:
                self.send_json({"status": "success", "data": exam_data})

        # 2. QUẢN LÝ KHÓA / LỚP (THÊM, SỬA, XÓA)
        elif path == "/api/teacher/classes":
            length = int(self.headers.get('Content-Length', 0))
            raw_body = self.rfile.read(length).decode('utf-8') if length > 0 else "{}"
            body = json.loads(raw_body)
            action = body.get("action", "add")
            cohort = body.get("cohort", "").strip()

            if action == "add":
                class_name = body.get("class_name", "").strip()
                res = ExamEngine.add_cohort_or_class(cohort, class_name)
                print(f"👉 [QUẢN LÝ LỚP] THÊM: Khóa='{cohort}', Lớp='{class_name}' -> {res.get('status', res.get('error'))}")
            elif action == "edit_class":
                old_name = body.get("old_name", "").strip()
                new_name = body.get("new_name", "").strip()
                res = ExamEngine.edit_class(cohort, old_name, new_name)
                print(f"👉 [QUẢN LÝ LỚP] SỬA: Khóa='{cohort}', Lớp cũ='{old_name}' -> Lớp mới='{new_name}' -> {res.get('status', res.get('error'))}")
            elif action == "delete_class":
                class_name = body.get("class_name", "").strip()
                res = ExamEngine.delete_class(cohort, class_name)
                print(f"👉 [QUẢN LÝ LỚP] XÓA LỚP: Khóa='{cohort}', Lớp='{class_name}' -> {res.get('status', res.get('error'))}")
            elif action == "delete_cohort":
                res = ExamEngine.delete_cohort(cohort)
                print(f"👉 [QUẢN LÝ LỚP] XÓA TOÀN BỘ KHÓA: Khóa='{cohort}' -> {res.get('status', res.get('error'))}")
            else:
                res = {"error": "Hành động không hợp lệ"}

            self.send_json(res)

        elif path == "/api/exam/submit-quiz":
            length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(length).decode('utf-8'))
            res = ExamEngine.submit_quiz(body.get("student_id"), body.get("answers", {}))
            self.send_json({"status": "success", "results": res})

        elif path == "/api/exam/upload-docx":
            boundary = content_type.split("boundary=")[-1].encode('utf-8')
            length = int(self.headers.get('Content-Length', 0))
            raw_data = self.rfile.read(length)

            parts = raw_data.split(b"--" + boundary)
            fields = {}
            file_bytes = None
            filename = "submitted.docx"

            for part in parts:
                if b'name="student_id"' in part:
                    fields["student_id"] = part.split(b"\r\n\r\n")[1].split(b"\r\n")[0].decode('utf-8')
                elif b'name="case_index"' in part:
                    fields["case_index"] = int(part.split(b"\r\n\r\n")[1].split(b"\r\n")[0].decode('utf-8'))
                elif b'name="file"' in part:
                    header, file_content = part.split(b"\r\n\r\n", 1)
                    file_bytes = file_content.rstrip(b"\r\n")

            student_id = fields.get("student_id", "unknown")
            case_index = fields.get("case_index", 1)
            target_dir = os.path.join(UPLOAD_DIR, student_id)
            os.makedirs(target_dir, exist_ok=True)
            save_path = os.path.join(target_dir, f"Case_{case_index}_{filename}")

            if file_bytes:
                with open(save_path, "wb") as f:
                    f.write(file_bytes)

            grade_res = ExamEngine.grade_practice_file(student_id, save_path, case_index)

            # TỰ ĐỘNG ĐỒNG BỘ LÊN GOOGLE DRIVE THEO LỚP (cttrung@ntt.edu.vn)
            session = ACTIVE_SESSIONS.get(student_id, {})
            s_name = session.get("student_name", "SinhVien")
            cohort = session.get("cohort", "Khóa 1")
            class_name = session.get("class_name", "Lớp 01")
            GDriveService.upload_file_async(
                student_id=student_id,
                student_name=s_name,
                cohort=cohort,
                class_name=class_name,
                case_index=case_index,
                docx_path=save_path,
                active_sessions_dict=ACTIVE_SESSIONS
            )

            self.send_json({"status": "success", "grade": grade_res})

        # BÁO CÁO VI PHẠM RỜI MÀN HÌNH (GIAI ĐOẠN TRẮC NGHIỆM)
        elif path == "/api/exam/report-violation":
            length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(length).decode('utf-8'))
            student_id = str(body.get("student_id") or "").strip()
            session = ACTIVE_SESSIONS.get(student_id)
            if not session:
                self.send_json({"error": "Không tìm thấy sinh viên"}, 404)
                return

            violations = session.setdefault("anti_cheat_violations", [])
            violations.append({
                "time": time.strftime("%H:%M:%S"),
                "type": body.get("violation_type", "TAB_SWITCH"),
                "detail": body.get("detail", "Rời màn hình khi làm trắc nghiệm")
            })

            tab_v = [v for v in violations if v.get("type") == "TAB_SWITCH"]
            if len(tab_v) >= 3:
                session["anti_cheat_overall"] = "CHEATING"
                session["anti_cheat_summary"] = f"CẢNH BÁO: Rời màn hình {len(tab_v)} lần khi làm trắc nghiệm!"
            elif len(tab_v) >= 1:
                if session.get("anti_cheat_overall") != "CHEATING":
                    session["anti_cheat_overall"] = "WARNING"
                    session["anti_cheat_summary"] = f"Cảnh báo: Rời màn hình {len(tab_v)} lần"

            self.send_json({"status": "success", "violations_count": len(violations)})

        # CHUYỂN ĐỔI GIAI ĐOẠN THI (TRẮC NGHIỆM SANG WORD)
        elif path == "/api/exam/set-phase":
            length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(length).decode('utf-8'))
            student_id = str(body.get("student_id") or "").strip()
            phase = str(body.get("phase") or "WORD").strip()
            session = ACTIVE_SESSIONS.get(student_id)
            if not session:
                self.send_json({"error": "Không tìm thấy sinh viên"}, 404)
                return

            session["current_phase"] = phase
            if phase == "WORD":
                session["word_started_at"] = time.strftime("%H:%M:%S")

            self.send_json({"status": "success", "phase": phase})

        elif path == "/api/teacher/grade-content":
            length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(length).decode('utf-8'))
            student_id = body.get("student_id")
            session = ACTIVE_SESSIONS.get(student_id)
            if not session:
                self.send_json({"error": "Không tìm thấy sinh viên"}, 404)
                return

            sec_cfg = GradingService.get_sections()
            c1_c_max = float(sec_cfg.get("case_1_content_max", 1.5))
            c2_c_max = float(sec_cfg.get("case_2_content_max", 1.5))
            c1_f_max = float(sec_cfg.get("case_1_format_max", 2.0))
            c2_f_max = float(sec_cfg.get("case_2_format_max", 2.0))

            words = session.setdefault("word_scores", {})
            c1_score = float(body.get("case_1_content_score", 0.0))
            c2_score = float(body.get("case_2_content_score", 0.0))

            words.setdefault("case_1", {})["content_score"] = min(c1_c_max, max(0.0, c1_score))
            words.setdefault("case_2", {})["content_score"] = min(c2_c_max, max(0.0, c2_score))

            if "case_1_format_score" in body and body["case_1_format_score"] is not None:
                words.setdefault("case_1", {})["format_score"] = min(c1_f_max, max(0.0, float(body["case_1_format_score"])))
            if "case_2_format_score" in body and body["case_2_format_score"] is not None:
                words.setdefault("case_2", {})["format_score"] = min(c2_f_max, max(0.0, float(body["case_2_format_score"])))

            session["teacher_comment"] = body.get("teacher_comment", "")

            self.send_json({
                "status": "success",
                "message": "Đã lưu điểm và nhận xét thành công!",
                "student_id": student_id
            })

        # 4. GIÁO VIÊN GIA HẠN THỜI GIAN LÀM BÀI CHO SINH VIÊN
        elif path == "/api/teacher/extend-time":
            length = int(self.headers.get('Content-Length', 0))
            raw_body = self.rfile.read(length).decode('utf-8') if length > 0 else "{}"
            body = json.loads(raw_body)
            student_id = body.get("student_id", "").strip()
            extra_minutes = int(body.get("extra_minutes", 10))
            res = ExamEngine.extend_student_time(student_id, extra_minutes)
            print(f"👉 [GIẢNG VIÊN GIA HẠN] MSSV='{student_id}', Thêm +{extra_minutes} phút -> {res.get('status', res.get('error'))}")
            self.send_json(res)

        # 5. GIÁO VIÊN ĐÌNH CHỈ / THU BÀI BẮT BUỘC KHI ĐANG THI
        elif path == "/api/teacher/terminate-exam":
            length = int(self.headers.get('Content-Length', 0))
            raw_body = self.rfile.read(length).decode('utf-8') if length > 0 else "{}"
            body = json.loads(raw_body)
            student_id = body.get("student_id", "").strip()
            reason = body.get("reason", "").strip()
            res = ExamEngine.terminate_student_exam(student_id, reason)
            print(f"👉 [GIẢNG VIÊN ĐÌNH CHỈ THI] MSSV='{student_id}', Lý do='{reason}' -> {res.get('status', res.get('error'))}")
            self.send_json(res)

        # 5b. GIÁO VIÊN CHO SINH VIÊN LÀM LẠI / MỞ LẠI BÀI THI (DO LỠ BẤM NỘP NHẦM HOẶC LÀM LẠI)
        elif path == "/api/teacher/retake-exam":
            length = int(self.headers.get('Content-Length', 0))
            raw_body = self.rfile.read(length).decode('utf-8') if length > 0 else "{}"
            body = json.loads(raw_body)
            student_id = body.get("student_id", "").strip()
            mode = body.get("mode", "resume")
            extra_minutes = int(body.get("extra_minutes", 15))
            res = ExamEngine.reopen_or_retake_exam(student_id, mode=mode, extra_minutes=extra_minutes)
            print(f"👉 [CHO LÀM LẠI BÀI THI] MSSV='{student_id}', Hình thức='{mode}', Thêm={extra_minutes}p -> {res.get('status', res.get('error'))}")
            self.send_json(res)

        # 5c. GIÁO VIÊN MỞ KHÓA RÀNG BUỘC THIẾT BỊ (CHO PHÉP CHUYỂN MÁY)
        elif path == "/api/teacher/unlock-device":
            length = int(self.headers.get('Content-Length', 0))
            raw_body = self.rfile.read(length).decode('utf-8') if length > 0 else "{}"
            body = json.loads(raw_body)
            student_id = body.get("student_id", "").strip()
            res = ExamEngine.unlock_student_device(student_id)
            print(f"👉 [MỞ KHÓA THIẾT BỊ] MSSV='{student_id}' -> {res.get('status', res.get('error'))}")
            self.send_json(res)

        # 6. CẤU HÌNH SỐ CÂU TRẮC NGHIỆM ĐỀ THI (5 hoặc 10 câu)
        elif path == "/api/teacher/exam-config":
            length = int(self.headers.get('Content-Length', 0))
            raw_body = self.rfile.read(length).decode('utf-8') if length > 0 else "{}"
            body = json.loads(raw_body)
            mcq_count = int(body.get("mcq_count", 10))
            res = ExamEngine.update_exam_config(mcq_count)
            print(f"👉 [CẤU HÌNH ĐỀ] Số câu trắc nghiệm: {mcq_count} -> {res.get('status', res.get('error'))}")
            self.send_json(res)

        # 7. THÊM CÂU HỎI TRẮC NGHIỆM VÀO NGÂN HÀNG (THỦ CÔNG)
        elif path == "/api/teacher/questions/add-mcq":
            length = int(self.headers.get('Content-Length', 0))
            raw_body = self.rfile.read(length).decode('utf-8') if length > 0 else "{}"
            body = json.loads(raw_body)
            res = ExamEngine.add_mcq(
                question=body.get("question", ""),
                options=body.get("options", []),
                correct_index=int(body.get("correct_index", 0)),
                explanation=body.get("explanation", ""),
                group=body.get("group", "Nghị định 30/2020/NĐ-CP")
            )
            print(f"👉 [NGÂN HÀNG TRẮC NGHIỆM] THÊM CÂU HỎI -> {res.get('status', res.get('error'))}")
            self.send_json(res)

        # 7b. PHÂN TÍCH CÂU HỎI TRẮC NGHIỆM TỪ FILE WORD (.DOCX)
        elif path == "/api/teacher/questions/parse-docx":
            file_bytes = None
            length = int(self.headers.get('Content-Length', 0))
            raw_data = self.rfile.read(length) if length > 0 else b""

            if "multipart/form-data" in content_type and raw_data:
                # Trích xuất boundary chuẩn xác (loại bỏ dấu ngoặc kép hoặc tham số phụ)
                boundary = None
                for param in content_type.split(';'):
                    param = param.strip()
                    if param.lower().startswith('boundary='):
                        boundary = param[len('boundary='):].strip().strip('"').encode('utf-8')
                        break
                if not boundary:
                    boundary = content_type.split("boundary=")[-1].strip().strip('"').encode('utf-8')

                parts = raw_data.split(b"--" + boundary)
                for part in parts:
                    if b'name="file"' in part and b"\r\n\r\n" in part:
                        header, file_content = part.split(b"\r\n\r\n", 1)
                        if file_content.endswith(b"\r\n"):
                            file_bytes = file_content[:-2]
                        elif file_content.endswith(b"\n"):
                            file_bytes = file_content[:-1]
                        else:
                            file_bytes = file_content
                        break
            else:
                file_bytes = raw_data

            if not file_bytes:
                self.send_json({"error": "Chưa nhận được file Word tải lên hoặc file bị rỗng!"}, 400)
                return

            res = ExamEngine.parse_mcq_docx(file_bytes)
            print(f"👉 [NHẬP CÂU HỎI WORD] Bóc tách file Word -> {res.get('status', res.get('error'))} ({res.get('count', 0)} câu)")
            self.send_json(res)

        # 7c. PHÂN TÍCH CÂU HỎI TRẮC NGHIỆM TỪ VĂN BẢN DÁN
        elif path == "/api/teacher/questions/parse-text":
            length = int(self.headers.get('Content-Length', 0))
            raw_body = self.rfile.read(length).decode('utf-8') if length > 0 else "{}"
            body = json.loads(raw_body)
            raw_text = body.get("text", "")
            res = ExamEngine.parse_mcq_text(raw_text)
            print(f"👉 [NHẬP CÂU HỎI DÁN TEXT] Bóc tách văn bản -> {res.get('status', res.get('error'))} ({res.get('count', 0)} câu)")
            self.send_json(res)

        # 7d. LƯU HÀNG LOẠT CÂU HỎI VÀO NGÂN HÀNG (IMPORT BATCH)
        elif path == "/api/teacher/questions/import-batch":
            length = int(self.headers.get('Content-Length', 0))
            raw_body = self.rfile.read(length).decode('utf-8') if length > 0 else "{}"
            body = json.loads(raw_body)
            questions = body.get("questions", [])
            res = ExamEngine.add_mcq_batch(questions)
            print(f"👉 [NHẬP CÂU HỎI HÀNG LOẠT] Thêm {len(questions)} câu -> {res.get('status', res.get('error'))}")
            self.send_json(res)

        # 8. XÓA CÂU HỎI TRẮC NGHIỆM KHỎI NGÂN HÀNG
        elif path == "/api/teacher/questions/delete-mcq":
            length = int(self.headers.get('Content-Length', 0))
            raw_body = self.rfile.read(length).decode('utf-8') if length > 0 else "{}"
            body = json.loads(raw_body)
            question_id = body.get("question_id", "")
            try:
                if isinstance(question_id, str) and question_id.isdigit():
                    question_id = int(question_id)
            except Exception:
                pass
            res = ExamEngine.delete_mcq(question_id)
            print(f"👉 [NGÂN HÀNG TRẮC NGHIỆM] XÓA CÂU HỎI {question_id} -> {res.get('status', res.get('error'))}")
            self.send_json(res)

        # 9. THÊM ĐỀ BÀI TỰ LUẬN (GÓI A HOẶC GÓI B)
        elif path == "/api/teacher/questions/add-case":
            length = int(self.headers.get('Content-Length', 0))
            raw_body = self.rfile.read(length).decode('utf-8') if length > 0 else "{}"
            body = json.loads(raw_body)
            res = ExamEngine.add_practice_case(
                bucket=body.get("bucket", "A"),
                doc_type=body.get("doc_type", "CÔNG VĂN ĐỀ NGHỊ"),
                title=body.get("title", ""),
                context=body.get("context", ""),
                requirements=body.get("requirements", [])
            )
            print(f"👉 [NGÂN HÀNG TỰ LUẬN] THÊM ĐỀ GÓI {body.get('bucket')} -> {res.get('status', res.get('error'))}")
            self.send_json(res)

        # 10. XÓA ĐỀ BÀI TỰ LUẬN
        elif path == "/api/teacher/questions/delete-case":
            length = int(self.headers.get('Content-Length', 0))
            raw_body = self.rfile.read(length).decode('utf-8') if length > 0 else "{}"
            body = json.loads(raw_body)
            bucket = body.get("bucket", "A")
            case_id = body.get("case_id", "")
            res = ExamEngine.delete_practice_case(bucket, case_id)
            print(f"👉 [NGÂN HÀNG TỰ LUẬN] XÓA ĐỀ {bucket}/{case_id} -> {res.get('status', res.get('error'))}")
            self.send_json(res)

        # 10b. LÀM SẠCH KHO DỮ LIỆU CÂU HỎI TRẮC NGHIỆM / ĐỀ TỰ LUẬN
        elif path == "/api/teacher/questions/clear-all":
            length = int(self.headers.get('Content-Length', 0))
            raw_body = self.rfile.read(length).decode('utf-8') if length > 0 else "{}"
            body = json.loads(raw_body) if raw_body else {}
            target = body.get("target", "all")
            res = ExamEngine.clear_questions_bank(target)
            print(f"👉 [LÀM SẠCH NGÂN HÀNG] Target='{target}' -> {res.get('status', res.get('error'))}")
            self.send_json(res)

        # 10c. KHÔI PHỤC NGÂN HÀNG CÂU HỎI & ĐỀ THI MẪU NGHỊ ĐỊNH 30
        elif path == "/api/teacher/questions/restore-samples":
            res = ExamEngine.restore_sample_questions_bank()
            print(f"👉 [KHÔI PHỤC NGÂN HÀNG MẪU] -> {res.get('status', res.get('error'))}")
            self.send_json(res)

        # 11. CẬP NHẬT CẤU HÌNH GOOGLE DRIVE
        elif path == "/api/teacher/gdrive-config":
            length = int(self.headers.get('Content-Length', 0))
            raw_body = self.rfile.read(length).decode('utf-8') if length > 0 else "{}"
            body = json.loads(raw_body)
            cfg = GDriveService.load_config()
            if "webhook_url" in body:
                cfg["webhook_url"] = body["webhook_url"].strip()
            if "auto_upload" in body:
                cfg["auto_upload"] = bool(body["auto_upload"])
            GDriveService.save_config(cfg)
            print(f"👉 [GDRIVE CONFIG] Cập nhật: Webhook={cfg['webhook_url'][:30]}..., AutoUpload={cfg['auto_upload']}")
            self.send_json({"status": "success", "message": "Đã lưu cấu hình Google Drive thành công", "config": cfg})

        # 12. KIỂM TRA KẾT NỐI GOOGLE DRIVE (cttrung@ntt.edu.vn)
        elif path == "/api/teacher/gdrive-test":
            length = int(self.headers.get('Content-Length', 0))
            raw_body = self.rfile.read(length).decode('utf-8') if length > 0 else "{}"
            body = json.loads(raw_body)
            test_url = body.get("webhook_url", "")
            res = GDriveService.test_connection(test_url)
            self.send_json(res)

        # 13. ĐỒNG BỘ TOÀN BỘ BÀI THI LÊN GOOGLE DRIVE
        elif path == "/api/teacher/gdrive-sync-all":
            count = 0
            for s_id, s_data in ACTIVE_SESSIONS.items():
                s_dir = os.path.join(UPLOAD_DIR, s_id)
                if not os.path.exists(s_dir):
                    continue
                s_name = s_data.get("student_name", "SinhVien")
                cohort = s_data.get("cohort", "Khóa 1")
                class_name = s_data.get("class_name", "Lớp 01")
                for c_idx in [1, 2]:
                    f_name = f"Case_{c_idx}_submitted.docx"
                    f_path = os.path.join(s_dir, f_name)
                    if os.path.exists(f_path):
                        GDriveService.upload_file_async(
                            student_id=s_id,
                            student_name=s_name,
                            cohort=cohort,
                            class_name=class_name,
                            case_index=c_idx,
                            docx_path=f_path,
                            active_sessions_dict=ACTIVE_SESSIONS
                        )
                        count += 1
            self.send_json({
                "status": "success",
                "message": f"Đã bắt đầu đồng bộ nền {count} bài thi lên Google Drive (cttrung@ntt.edu.vn)"
            })

        # 14. GIÁO VIÊN TÙY CHỈNH THANG ĐIỂM & RUBRIC
        elif path == "/api/teacher/grading-config":
            length = int(self.headers.get('Content-Length', 0))
            raw_body = self.rfile.read(length).decode('utf-8') if length > 0 else "{}"
            body = json.loads(raw_body)
            action = body.get("action", "save")
            if action == "reset":
                res = GradingService.reset_to_default()
            else:
                config_data = body.get("config", body)
                res = GradingService.save_config(config_data)
            print(f"👉 [CẤU HÌNH THANG ĐIỂM] Action={action} -> {res.get('status', res.get('error'))}")
            self.send_json(res)
        else:
            self.send_json({"error": "Endpoint không tồn tại"}, 404)

    def serve_file(self, file_path, content_type, filename=None):
        if not os.path.exists(file_path):
            self.send_error(404, "File Not Found")
            return
        with open(file_path, "rb") as f:
            data = f.read()
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Type", content_type)
        if filename:
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def send_json(self, data, status_code=200):
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(status_code)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

if __name__ == "__main__":
    all_ips = get_all_lan_ips()
    primary_ip = all_ips[0]
    print("==================================================================")
    print("       HE THONG THI SOAN THAO VAN BAN (NGHI DINH 30/2020)         ")
    print("       QUAN LY THEO KHOA - LOP (COHORTS & CLASSES ACTIVE)        ")
    print("==================================================================")
    print(" [1] LINK GUI CHO SINH VIEN THI:")
    print(f"     👉 LINK CHÍNH (Wi-Fi/LAN): http://{primary_ip}:{PORT}")
    if len(all_ips) > 1:
        print("     👉 CAC LINK DU PHONG KHAC (Neu dung nhieu mang):")
        for other_ip in all_ips[1:]:
            is_wsl = False
            try:
                if other_ip.startswith("172.") and 16 <= int(other_ip.split('.')[1]) <= 31:
                    is_wsl = True
            except Exception:
                pass
            tag = " <-- [LƯU Ý: Card ao WSL/Hyper-V, sinh vien KHONG vao duoc link nay!]" if is_wsl else ""
            print(f"        * http://{other_ip}:{PORT}{tag}")
    print("------------------------------------------------------------------")
    print(f" [2] LINK BAN CHAM & QUAN LY LOP CUA GIANG VIEN:")
    print(f"     👉  http://localhost:{PORT}/teacher")
    print("==================================================================")
    print(" (!) KHAC PHUC KHI SINH VIEN BI DANG TAI / WAIT:")
    print("  1. Mo Tuong lua Windows: Chay file 'Mo_Tuong_Lua_Port_8000.bat'")
    print("  2. Neu Wi-Fi truong chan ket noi: Bat 'Mobile Hotspot' tren Laptop")
    print("     va cho sinh vien ket noi vao Hotspot cua Thay.")
    print("==================================================================")
    print(" May chu dang hoat dong san sang tiep nhan ca thi...")
    with socketserver.TCPServer(("", PORT), ExamHandler) as httpd:
        httpd.serve_forever()
