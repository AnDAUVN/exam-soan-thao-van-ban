"""
Module chấm điểm tự động và Kiểm định Gian lận (Anti-Cheat Forensics) theo Nghị định 30/2020/NĐ-CP.
"""

from __future__ import annotations
import os
import zipfile
import re
import datetime
import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Tuple, Optional

NAMESPACES = {
    'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
    'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
    'cp': 'http://schemas.openxmlformats.org/package/2006/metadata/core-properties',
    'dc': 'http://purl.org/dc/elements/1.1/',
    'dcterms': 'http://purl.org/dc/terms/',
    'app': 'http://schemas.openxmlformats.org/officeDocument/2006/extended-properties'
}

DXA_PER_MM = 56.7

from grading_service import GradingService

class DocxNghiDinh30Grader:
    def __init__(self, docx_path: str, expected_student_id: str = None, expected_token: str = None, rubric_config: Dict[str, float] = None):
        self.docx_path = docx_path
        self.expected_student_id = expected_student_id
        self.expected_token = expected_token
        self.rubric = rubric_config if rubric_config else GradingService.get_rubric_map()

    def inspect_anti_cheat(self, zf: zipfile.ZipFile) -> Dict[str, Any]:
        """
        Kiểm định gian lận chuyên sâu bằng siêu dữ liệu (Metadata Forensics):
        1. Kiểm tra Chữ ký số / Token bảo mật của phiên thi
        2. Tác giả tạo file (dc:creator)
        3. Tổng thời gian gõ văn bản (Total Editing Time)
        4. Số lần chỉnh sửa lưu bài (Revision count)
        5. Ngày giờ tạo file (Created timestamp)
        """
        forensics = {
            "token_valid": False,
            "creator_matched": False,
            "total_time_mins": 0,
            "revision": 1,
            "created_time_str": "Không xác định",
            "status": "SAFE",  # SAFE, WARNING, FLAGGED
            "flags": [],
            "violations": [],
            "violation_text": "Hợp lệ"
        }

        # 1. Đọc docProps/core.xml (Tác giả, Token, Giờ tạo)
        if 'docProps/core.xml' in zf.namelist():
            try:
                core_xml = zf.read('docProps/core.xml')
                root = ET.fromstring(core_xml)
                creator = root.find('.//dc:creator', NAMESPACES)
                keywords = root.find('.//cp:keywords', NAMESPACES)
                created = root.find('.//dcterms:created', NAMESPACES)

                creator_val = creator.text.strip() if (creator is not None and creator.text) else ""
                token_val = keywords.text.strip() if (keywords is not None and keywords.text) else ""
                created_val = created.text.strip() if (created is not None and created.text) else ""

                forensics["created_time_str"] = created_val

                # Kiểm tra mã Token bảo mật
                if self.expected_token and token_val:
                    if self.expected_token in token_val:
                        forensics["token_valid"] = True
                        forensics["flags"].append("✅ Khớp mã bảo mật phôi thi chính thức")
                    else:
                        forensics["flags"].append("🔴 LỖI: Copy bài từ bạn khác (Mã bảo mật thuộc về phiên thi của thí sinh khác)")
                        forensics["violations"].append("Copy từ bạn khác")
                        forensics["status"] = "FLAGGED"
                elif self.expected_token and not token_val:
                    forensics["flags"].append("🔴 LỖI: File không đúng phôi thi (Nộp file mẫu ngoài hoặc file tạo sẵn)")
                    forensics["violations"].append("File không đúng phôi")
                    forensics["status"] = "FLAGGED"

                # Kiểm tra Tác giả file
                if self.expected_student_id and creator_val:
                    if self.expected_student_id.lower() in creator_val.lower():
                        forensics["creator_matched"] = True
                    else:
                        forensics["flags"].append(f"⚠️ CẢNH BÁO: Tác giả máy tính ({creator_val}) khác với Mã SV ({self.expected_student_id})")
                        forensics["violations"].append(f"Khác tác giả ({creator_val})")
                        if forensics["status"] != "FLAGGED":
                            forensics["status"] = "WARNING"
            except Exception as e:
                forensics["flags"].append(f"Lỗi đọc siêu dữ liệu tác giả: {str(e)}")

        # 2. Đọc docProps/app.xml (Thời gian soạn thảo, số lần lưu)
        if 'docProps/app.xml' in zf.namelist():
            try:
                app_xml = zf.read('docProps/app.xml')
                root = ET.fromstring(app_xml)
                total_time = root.find('.//app:TotalTime', NAMESPACES)
                if total_time is None:
                    # Thử tìm không có prefix nếu namespace mặc định
                    for el in root.iter():
                        if el.tag.endswith('TotalTime'):
                            total_time = el
                            break

                if total_time is not None and total_time.text:
                    mins = int(total_time.text)
                    forensics["total_time_mins"] = mins

                    # Phân tích hành vi thời gian gõ văn bản thực tế:
                    if mins < 3:
                        forensics["flags"].append(f"🔴 LỖI: Nghi vấn Copy bài làm sẵn (Thời gian gõ bài chỉ {mins} phút)")
                        forensics["violations"].append(f"Copy bài sẵn ({mins}p)")
                        forensics["status"] = "FLAGGED"
                    elif mins < 6:
                        forensics["flags"].append(f"⚠️ CẢNH BÁO: Tốc độ hoàn thành bất thường ({mins} phút cho văn bản đầy đủ)")
                        forensics["violations"].append(f"Gõ quá nhanh ({mins}p)")
                        if forensics["status"] != "FLAGGED":
                            forensics["status"] = "WARNING"
                    else:
                        forensics["flags"].append(f"✅ Thời gian thực hiện hợp lý: {mins} phút gõ văn bản thực tế")
            except Exception:
                pass

        if not forensics["flags"]:
            forensics["flags"].append("File chuẩn, không phát hiện dấu hiệu bất thường")

        if forensics["violations"]:
            forensics["violation_text"] = ", ".join(forensics["violations"])
        else:
            forensics["violation_text"] = "Hợp lệ"

        return forensics

    def parse_document(self) -> Dict[str, Any]:
        """
        Bóc tách chi tiết từng thành phần để đối chiếu từ Ô 1 đến Ô 9.
        L06 & L12:
        - Kiểm tra an toàn tệp tải lên (Dung lượng <= 15MB, chống ZIP Bomb / XML expansion).
        - Đánh giá kế thừa style và tỷ lệ phông chữ (Times New Roman >= 70%).
        - Kiểm định ngày tháng năm chuẩn lịch (chặn ngày 99/99).
        - Kiểm định bảng đầu trang định vị đúng Ô 1 & Ô 2 (không chấm điểm cho bảng dữ liệu ngẫu nhiên).
        """
        results = {
            "margins": {},
            "paper_size": {},
            "fonts": set(),
            "has_times_new_roman": False,
            "tnr_ratio": 0.0,
            "primary_font": "Unknown",
            "font_char_counts": {},
            "paragraphs": [],
            "tables_count": 0,
            "has_valid_header_table": False,
            "header_table_comment": "Chưa có bảng đầu trang định vị Cơ quan và Quốc hiệu",
            "has_valid_date": False,
            "date_comment": "Không tìm thấy ngày tháng năm hợp lệ",
            "text_full": "",
            "anti_cheat": {}
        }

        # L12: Kiểm tra dung lượng tệp và cấu trúc ZIP trước khi đọc nội dung
        try:
            if not os.path.exists(self.docx_path):
                return {"error": "Tệp không tồn tại trên máy chủ"}

            file_size = os.path.getsize(self.docx_path)
            if file_size > 15 * 1024 * 1024:
                return {"error": "Dung lượng tệp vượt quá giới hạn cho phép (15MB)"}

            if not zipfile.is_zipfile(self.docx_path):
                return {"error": "Tệp không phải định dạng ZIP/Word (.docx) hợp lệ"}

            with zipfile.ZipFile(self.docx_path, 'r') as zf:
                infolist = zf.infolist()
                if len(infolist) > 500:
                    return {"error": "Cấu trúc tệp DOCX bất thường: số lượng phần tử vượt quá giới hạn an toàn (max 500 phần tử)"}

                total_uncompressed = 0
                for info in infolist:
                    total_uncompressed += info.file_size
                    if info.file_size > 15 * 1024 * 1024:
                        return {"error": f"Phần tử '{info.filename}' trong tệp vượt quá kích thước cho phép"}
                    if info.compress_size > 0:
                        ratio = info.file_size / info.compress_size
                        if ratio > 100:
                            return {"error": "Phát hiện tệp có tỷ lệ nén bất thường (nghi vấn ZIP Bomb)"}

                if total_uncompressed > 30 * 1024 * 1024:
                    return {"error": "Tổng dung lượng giải nén vượt quá ngưỡng an toàn (30MB)"}

                if 'word/document.xml' not in zf.namelist():
                    return {"error": "Tệp DOCX không hợp lệ: thiếu word/document.xml"}

                # Kiểm tra gian lận siêu dữ liệu
                results["anti_cheat"] = self.inspect_anti_cheat(zf)

                # 0. Đọc style mặc định từ word/styles.xml để hỗ trợ style inheritance
                default_font = "Times New Roman"
                if 'word/styles.xml' in zf.namelist():
                    try:
                        styles_xml = zf.read('word/styles.xml')
                        styles_root = ET.fromstring(styles_xml)
                        doc_def_rf = styles_root.find('.//w:docDefaults/w:rPrDefault/w:rPr/w:rFonts', NAMESPACES)
                        if doc_def_rf is not None:
                            df = doc_def_rf.attrib.get(f"{{{NAMESPACES['w']}}}ascii") or doc_def_rf.attrib.get(f"{{{NAMESPACES['w']}}}hAnsi")
                            if df:
                                default_font = df
                        # Kiểm tra style Normal
                        for st in styles_root.findall('.//w:style', NAMESPACES):
                            if st.attrib.get(f"{{{NAMESPACES['w']}}}styleId") == "Normal" or st.attrib.get(f"{{{NAMESPACES['w']}}}default") == "1":
                                st_rf = st.find('.//w:rFonts', NAMESPACES)
                                if st_rf is not None:
                                    df = st_rf.attrib.get(f"{{{NAMESPACES['w']}}}ascii")
                                    if df:
                                        default_font = df
                    except Exception:
                        pass

                # Đọc word/document.xml
                doc_xml = zf.read('word/document.xml')
                root = ET.fromstring(doc_xml)

                # 1. Khổ giấy & Lề trang
                sect_pr = root.find('.//w:sectPr', NAMESPACES)
                if sect_pr is not None:
                    pg_mar = sect_pr.find('w:pgMar', NAMESPACES)
                    if pg_mar is not None:
                        top = float(pg_mar.attrib.get(f"{{{NAMESPACES['w']}}}top", 0)) / DXA_PER_MM
                        bottom = float(pg_mar.attrib.get(f"{{{NAMESPACES['w']}}}bottom", 0)) / DXA_PER_MM
                        left = float(pg_mar.attrib.get(f"{{{NAMESPACES['w']}}}left", 0)) / DXA_PER_MM
                        right = float(pg_mar.attrib.get(f"{{{NAMESPACES['w']}}}right", 0)) / DXA_PER_MM
                        results["margins"] = {
                            "top_mm": round(top, 1),
                            "bottom_mm": round(bottom, 1),
                            "left_mm": round(left, 1),
                            "right_mm": round(right, 1)
                        }

                    pg_sz = sect_pr.find('w:pgSz', NAMESPACES)
                    if pg_sz is not None:
                        width = float(pg_sz.attrib.get(f"{{{NAMESPACES['w']}}}w", 0)) / DXA_PER_MM
                        height = float(pg_sz.attrib.get(f"{{{NAMESPACES['w']}}}h", 0)) / DXA_PER_MM
                        results["paper_size"] = {
                            "width_mm": round(width, 1),
                            "height_mm": round(height, 1),
                            "is_a4": (205 <= width <= 215) and (292 <= height <= 302)
                        }

                # 2. Phông chữ: Đánh giá chi tiết từng run và tính tỷ lệ thống trị (L06)
                font_char_counts: Dict[str, int] = {}
                total_text_chars = 0
                for r in root.findall('.//w:r', NAMESPACES):
                    r_font = None
                    rf = r.find('.//w:rFonts', NAMESPACES)
                    if rf is not None:
                        r_font = rf.attrib.get(f"{{{NAMESPACES['w']}}}ascii") or rf.attrib.get(f"{{{NAMESPACES['w']}}}hAnsi")
                    if not r_font:
                        r_font = default_font

                    run_text = "".join([t.text for t in r.findall('.//w:t', NAMESPACES) if t.text])
                    c_count = len(run_text.strip())
                    if c_count > 0:
                        total_text_chars += c_count
                        norm_f = r_font.strip()
                        font_char_counts[norm_f] = font_char_counts.get(norm_f, 0) + c_count
                        results["fonts"].add(norm_f)

                results["font_char_counts"] = font_char_counts
                if font_char_counts:
                    primary_f = max(font_char_counts, key=font_char_counts.get)
                    results["primary_font"] = primary_f

                tnr_chars = sum(count for f_name, count in font_char_counts.items() if "times new roman" in f_name.lower())
                calibri_chars = sum(count for f_name, count in font_char_counts.items() if any(bad in f_name.lower() for bad in ["calibri", "arial", "tahoma"]))
                
                if total_text_chars > 0:
                    tnr_ratio = tnr_chars / total_text_chars
                else:
                    tnr_ratio = 1.0 if "times new roman" in default_font.lower() else 0.0

                results["tnr_ratio"] = round(tnr_ratio, 2)
                # Yêu cầu Times New Roman phải chiếm tối thiểu 70% tổng số ký tự (loại bỏ trường hợp chỉ có 1 run TNR trong tài liệu Calibri)
                results["has_times_new_roman"] = (tnr_ratio >= 0.70)

                # 3. Trích xuất text các đoạn
                p_list = []
                for p in root.findall('.//w:p', NAMESPACES):
                    p_text = "".join([t.text for t in p.findall('.//w:t', NAMESPACES) if t.text]).strip()
                    if p_text:
                        p_list.append(p_text)

                results["paragraphs"] = p_list
                results["text_full"] = " ".join(p_list)
                full_text = results["text_full"]

                # 4. Kiểm tra Bảng đầu trang định vị Tên cơ quan và Quốc hiệu (L06)
                tables = root.findall('.//w:tbl', NAMESPACES)
                results["tables_count"] = len(tables)
                if tables:
                    first_table = tables[0]
                    rows = first_table.findall('.//w:tr', NAMESPACES)
                    if rows:
                        first_row_cells = rows[0].findall('.//w:tc', NAMESPACES)
                        if len(first_row_cells) >= 2:
                            cell_0_txt = "".join([t.text for t in first_row_cells[0].findall('.//w:t', NAMESPACES) if t.text]).strip().upper()
                            cell_1_txt = "".join([t.text for t in first_row_cells[1].findall('.//w:t', NAMESPACES) if t.text]).strip().upper()
                            
                            agency_kws = ["BỘ", "ỦY BAN", "UBND", "TRƯỜNG", "CÔNG TY", "TỔNG CÔNG TY", "SỞ", "PHÒNG", "VIỆN", "KHOA", "BAN", "TRUNG TÂM", "TỔ CHỨC", "ĐẢNG", "HỘI ĐỒNG", "CƠ QUAN"]
                            motto_kws = ["CỘNG HÒA", "VIỆT NAM", "ĐỘC LẬP", "TỰ DO", "HẠNH PHÚC"]
                            
                            has_agency = any(kw in cell_0_txt for kw in agency_kws) or (len(cell_0_txt) >= 4 and cell_0_txt.isupper())
                            has_motto = any(kw in cell_1_txt for kw in motto_kws)
                            
                            if has_agency and has_motto:
                                results["has_valid_header_table"] = True
                                results["header_table_comment"] = "Đạt: Bảng đầu trang 2 cột định vị chuẩn xác Tên cơ quan (bên trái) và Quốc hiệu/Tiêu ngữ (bên phải)"
                            elif has_agency or has_motto:
                                results["has_valid_header_table"] = True
                                results["header_table_comment"] = "Đạt cơ bản: Bảng chia cột đầu trang có định vị cơ quan/quốc hiệu"
                            else:
                                results["has_valid_header_table"] = False
                                results["header_table_comment"] = "Bảng đầu trang không chứa Tên cơ quan và Quốc hiệu (phát hiện bảng dữ liệu thông thường chứ không phải bảng chia cột đầu trang)"
                        else:
                            results["has_valid_header_table"] = False
                            results["header_table_comment"] = "Bảng đầu trang không đủ 2 cột (cần 1 cột Tên cơ quan và 1 cột Quốc hiệu/Tiêu ngữ)"
                else:
                    results["has_valid_header_table"] = False
                    results["header_table_comment"] = "Chưa dùng bảng không viền để chia 2 cột định vị đầu trang theo Nghị định 30"

                # 5. Kiểm tra ngày tháng năm chuẩn lịch (L06: Chặn ngày 99/99)
                date_match = re.search(
                    r"(?:([\w\s]+),\s*)?ngày\s+(0?[1-9]|[12]\d|3[01])\s+tháng\s+(0?[1-9]|1[0-2])\s+năm\s+((?:19|20)\d{2})",
                    full_text,
                    re.IGNORECASE
                )
                if date_match:
                    place_str, d_str, m_str, y_str = date_match.groups()
                    day_val = int(d_str)
                    month_val = int(m_str)
                    year_val = int(y_str)
                    
                    is_valid_cal = True
                    cal_reason = ""
                    if month_val in [4, 6, 9, 11] and day_val > 30:
                        is_valid_cal = False
                        cal_reason = f"Tháng {month_val} chỉ có tối đa 30 ngày (bài làm ghi ngày {day_val})"
                    elif month_val == 2:
                        is_leap = (year_val % 4 == 0 and (year_val % 100 != 0 or year_val % 400 == 0))
                        max_feb = 29 if is_leap else 28
                        if day_val > max_feb:
                            is_valid_cal = False
                            cal_reason = f"Tháng 2 năm {year_val} chỉ có tối đa {max_feb} ngày (bài làm ghi ngày {day_val})"

                    if is_valid_cal:
                        results["has_valid_date"] = True
                        matched_str = date_match.group(0).strip()
                        results["date_comment"] = f"Đạt: Có thành phần địa danh ngày tháng năm chuẩn lịch ({matched_str})"
                    else:
                        results["has_valid_date"] = False
                        results["date_comment"] = f"Ngày tháng không hợp lệ theo lịch: {cal_reason}"
                else:
                    results["has_valid_date"] = False
                    results["date_comment"] = "Không tìm thấy ngày tháng năm hợp lệ theo Nghị định 30 (VD: '..., ngày 15 tháng 10 năm 2026')"

        except Exception as e:
            return {"error": f"Lỗi đọc file: {str(e)}"}

        return results

    def grade(self) -> Dict[str, Any]:
        """Chấm điểm và đối chiếu chi tiết từ Ô 1 đến Ô 9 theo Rubric thang điểm tùy chỉnh của Giảng viên"""
        data = self.parse_document()
        rubric = self.rubric or {}
        p_paper = float(rubric.get("paper_size", 0.5))
        p_margins = float(rubric.get("margins", 1.5))
        p_font = float(rubric.get("font_family", 1.0))
        p_quoc_hieu = float(rubric.get("quoc_hieu", 1.5))
        p_co_quan = float(rubric.get("co_quan", 1.0))
        p_so_ky_hieu = float(rubric.get("so_ky_hieu", 1.0))
        p_dia_danh = float(rubric.get("dia_danh_ngay_thang", 1.0))
        p_ten_loai = float(rubric.get("ten_loai_trich_yeu", 1.0))
        p_tham_quyen = float(rubric.get("tham_quyen_ky", 1.0))
        p_noi_nhan = float(rubric.get("noi_nhan", 0.5))
        total_rubric_max = round(p_paper + p_margins + p_font + p_quoc_hieu + p_co_quan + p_so_ky_hieu + p_dia_danh + p_ten_loai + p_tham_quyen + p_noi_nhan, 2)
        if total_rubric_max <= 0:
            total_rubric_max = 10.0

        if "error" in data:
            return {
                "score": 0.0,
                "max_score": total_rubric_max,
                "details": [{"item": "Đọc file", "score": 0.0, "max": total_rubric_max, "comment": data["error"]}],
                "anti_cheat": {
                    "status": "FLAGGED", 
                    "flags": [f"🔴 LỖI: {data['error']}"],
                    "violations": ["File không đúng"],
                    "violation_text": "File không đúng"
                }
            }

        score = 0.0
        details = []
        text = data.get("text_full", "")
        text_upper = text.upper()
        anti_cheat = data.get("anti_cheat", {})

        # [TIÊU CHUẨN TRANG & FONT]
        # 1. Khổ giấy A4
        paper = data.get("paper_size", {})
        if paper.get("is_a4"):
            score += p_paper
            details.append({"cell": "Tổng thể", "item": "Khổ giấy A4", "score": p_paper, "max": p_paper, "comment": f"Đúng khổ A4 ({paper.get('width_mm')} x {paper.get('height_mm')} mm)"})
        else:
            details.append({"cell": "Tổng thể", "item": "Khổ giấy A4", "score": 0.0, "max": p_paper, "comment": "Chưa đúng khổ A4"})

        # 2. Căn lề trang
        margins = data.get("margins", {})
        top = margins.get("top_mm", 0)
        bottom = margins.get("bottom_mm", 0)
        left = margins.get("left_mm", 0)
        right = margins.get("right_mm", 0)
        top_ok = (19.0 <= top <= 26.0)
        bottom_ok = (19.0 <= bottom <= 26.0)
        left_ok = (29.0 <= left <= 36.0)
        right_ok = (14.0 <= right <= 21.0)
        margin_score = 0.0
        if top_ok and bottom_ok: margin_score += round(p_margins * 0.5, 2)
        if left_ok and right_ok: margin_score += round(p_margins * 0.5, 2)
        score += margin_score
        details.append({
            "cell": "Tổng thể",
            "item": "Căn lề trang (Top/Bottom 20-25mm, Left 30-35mm, Right 15-20mm)",
            "score": round(margin_score, 2),
            "max": p_margins,
            "comment": f"Trên {top}mm, Dưới {bottom}mm, Trái {left}mm, Phải {right}mm"
        })

        # 3. Phông Times New Roman (L06: Yêu cầu tỷ lệ >= 70%)
        tnr_ratio = data.get("tnr_ratio", 0.0)
        primary_f = data.get("primary_font", "Unknown")
        if data.get("has_times_new_roman"):
            score += p_font
            details.append({"cell": "Tổng thể", "item": "Phông chữ chuẩn", "score": p_font, "max": p_font, "comment": f"Đạt: Sử dụng Times New Roman theo quy định ({int(tnr_ratio * 100)}% dung lượng văn bản)"})
        else:
            details.append({"cell": "Tổng thể", "item": "Phông chữ chuẩn", "score": 0.0, "max": p_font, "comment": f"Chưa đạt: Phông Times New Roman chỉ chiếm {int(tnr_ratio * 100)}% (chủ đạo là phông '{primary_f}')"})

        # [ĐỐI CHIẾU Ô 1: QUỐC HIỆU VÀ TIÊU NGỮ]
        has_quoc_hieu = "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM" in text_upper
        has_tieu_ngu = ("ĐỘC LẬP - TỰ DO - HẠNH PHÚC" in text_upper or 
                        "ĐỘC LẬP – TỰ DO – HẠNH PHÚC" in text_upper or 
                        "ĐỘC LẬP - TỰ DO - HẠNH PHÚC" in text or
                        "Độc lập - Tự do - Hạnh phúc" in text)
        if has_quoc_hieu and has_tieu_ngu:
            score += p_quoc_hieu
            details.append({"cell": "Ô 1", "item": "Quốc hiệu & Tiêu ngữ", "score": p_quoc_hieu, "max": p_quoc_hieu, "comment": "Đạt: Quốc hiệu in hoa toàn bộ, Tiêu ngữ chuẩn có gạch nối"})
        else:
            q_partial = round(p_quoc_hieu * 0.33, 2) if (has_quoc_hieu or has_tieu_ngu) else 0.0
            score += q_partial
            details.append({"cell": "Ô 1", "item": "Quốc hiệu & Tiêu ngữ", "score": q_partial, "max": p_quoc_hieu, "comment": "Thiếu hoặc sai quy cách Quốc hiệu/Tiêu ngữ"})

        # [ĐỐI CHIẾU Ô 2: TÊN CƠ QUAN BAN HÀNH & BỐ CỤC ĐẦU TRANG] (L06)
        if data.get("has_valid_header_table"):
            score += p_co_quan
            details.append({"cell": "Ô 2", "item": "Tên cơ quan & Bố cục đầu trang", "score": p_co_quan, "max": p_co_quan, "comment": data.get("header_table_comment", "Đạt")})
        else:
            cq_partial = round(p_co_quan * 0.2, 2) if data.get("tables_count", 0) >= 1 else 0.0
            score += cq_partial
            details.append({"cell": "Ô 2", "item": "Tên cơ quan & Bố cục đầu trang", "score": cq_partial, "max": p_co_quan, "comment": data.get("header_table_comment", "Chưa đạt bảng chia cột đầu trang")})

        # [ĐỐI CHIẾU Ô 3: SỐ VÀ KÝ HIỆU]
        has_so_ky_hieu = bool(re.search(r"Số\s*:\s*\d+[/][a-zA-Z0-9\-_]+", text, re.IGNORECASE))
        if has_so_ky_hieu:
            score += p_so_ky_hieu
            details.append({"cell": "Ô 3", "item": "Số và ký hiệu văn bản", "score": p_so_ky_hieu, "max": p_so_ky_hieu, "comment": "Đạt: Đúng quy cách 'Số: .../...-...' theo NĐ 30"})
        else:
            skh_partial = round(p_so_ky_hieu * 0.3, 2) if "Số" in text else 0.0
            score += skh_partial
            details.append({"cell": "Ô 3", "item": "Số và ký hiệu văn bản", "score": skh_partial, "max": p_so_ky_hieu, "comment": "Chưa đúng cấu trúc Số/Ký hiệu (VD: Số: 01/QĐ-ĐHCN)"})

        # [ĐỐI CHIẾU Ô 4: ĐỊA DANH, NGÀY THÁNG NĂM] (L06: Chặn ngày 99/99)
        if data.get("has_valid_date"):
            score += p_dia_danh
            details.append({"cell": "Ô 4", "item": "Địa danh, ngày, tháng, năm", "score": p_dia_danh, "max": p_dia_danh, "comment": data.get("date_comment", "Đạt")})
        else:
            details.append({"cell": "Ô 4", "item": "Địa danh, ngày, tháng, năm", "score": 0.0, "max": p_dia_danh, "comment": data.get("date_comment", "Thiếu hoặc sai quy cách ngày tháng")})

        # [ĐỐI CHIẾU Ô 5: TÊN LOẠI & TRÍCH YẾU]
        has_type_or_abstract = any(kw in text_upper for kw in ["QUYẾT ĐỊNH", "THÔNG BÁO", "TỜ TRÌNH", "CÔNG VĂN", "VỀ VIỆC", "V/V"])
        if has_type_or_abstract:
            score += p_ten_loai
            details.append({"cell": "Ô 5", "item": "Tên loại & Trích yếu nội dung", "score": p_ten_loai, "max": p_ten_loai, "comment": "Đạt: Có Tên loại văn bản và trích yếu nội dung"})
        else:
            details.append({"cell": "Ô 5", "item": "Tên loại & Trích yếu nội dung", "score": 0.0, "max": p_ten_loai, "comment": "Chưa nhận diện rõ Tên loại văn bản hoặc Trích yếu"})

        # [ĐỐI CHIẾU Ô 7 & Ô 8: THẨM QUYỀN KÝ & CON DẤU]
        has_signature_role = any(role in text_upper for role in ["HIỆU TRƯỞNG", "GIÁM ĐỐC", "CHỦ TỊCH", "KT.", "TL.", "TRƯỞNG PHÒNG", "TM."])
        if has_signature_role:
            score += p_tham_quyen
            details.append({"cell": "Ô 7, 8", "item": "Thẩm quyền ký & Con dấu", "score": p_tham_quyen, "max": p_tham_quyen, "comment": "Đạt: Có chức danh người có thẩm quyền ký chuẩn xác"})
        else:
            details.append({"cell": "Ô 7, 8", "item": "Thẩm quyền ký & Con dấu", "score": 0.0, "max": p_tham_quyen, "comment": "Chưa có chức vụ/thẩm quyền ký"})

        # [ĐỐI CHIẾU Ô 9: NƠI NHẬN]
        has_noi_nhan = "NƠI NHẬN" in text_upper or "KÍNH GỬI" in text_upper or "LƯU: VT" in text_upper
        if has_noi_nhan:
            score += p_noi_nhan
            details.append({"cell": "Ô 9", "item": "Nơi nhận (Ô 9a / Ô 9b)", "score": p_noi_nhan, "max": p_noi_nhan, "comment": "Đạt: Có thành phần Nơi nhận và Lưu văn thư"})
        else:
            details.append({"cell": "Ô 9", "item": "Nơi nhận (Ô 9a / Ô 9b)", "score": 0.0, "max": p_noi_nhan, "comment": "Thiếu thành phần Nơi nhận"})

        return {
            "score": round(score, 2),
            "max_score": total_rubric_max,
            "details": details,
            "anti_cheat": anti_cheat,
            "metadata": {
                "margins": margins,
                "paper_size": paper,
                "fonts": list(data.get("fonts", [])),
                "primary_font": data.get("primary_font", "Unknown"),
                "tnr_ratio": data.get("tnr_ratio", 0.0)
            }
        }
