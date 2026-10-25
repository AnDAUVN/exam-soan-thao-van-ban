"""
Module trích xuất và phân tích cú pháp câu hỏi trắc nghiệm từ file Word (.docx) hoặc văn bản thô.
Hỗ trợ đầy đủ các định dạng đề thi thông dụng của Giảng viên Việt Nam.
"""

import io
import re
import os
import zipfile
import datetime
import xml.etree.ElementTree as ET
from typing import List, Dict, Any

def extract_docx_paragraphs(file_bytes_or_path) -> List[Dict[str, Any]]:
    """
    Đọc tất cả các đoạn văn bản (paragraphs) trong file Word .docx bằng zipfile & XML chuẩn.
    Nhận diện các đoạn văn có in đậm hoặc gạch chân để xác định đáp án đúng.
    Hỗ trợ cả bảng biểu, text tab, break, và non-breaking spaces.
    """
    if isinstance(file_bytes_or_path, (bytes, bytearray)):
        if file_bytes_or_path.startswith(b'\xd0\xcf\x11\xe0'):
            raise ValueError("File bạn tải lên là định dạng Word cũ (.doc). Thầy/Cô vui lòng mở file bằng Word và chọn 'Save As' sang định dạng mới (.docx) trước khi tải lên.")
        f = io.BytesIO(file_bytes_or_path)
    else:
        f = file_bytes_or_path

    paragraphs = []
    try:
        with zipfile.ZipFile(f, 'r') as z:
            if "word/document.xml" not in z.namelist():
                return []
            xml_content = z.read("word/document.xml")
            root = ET.fromstring(xml_content)
            ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}

            for p in root.findall('.//w:p', ns):
                p_text_parts = []
                bold_parts = []
                underline_parts = []
                has_bold = False
                has_underline = False

                for r in p.findall('.//w:r', ns):
                    r_pr = r.find('w:rPr', ns)
                    is_b = False
                    is_u = False
                    if r_pr is not None:
                        b_elem = r_pr.find('w:b', ns)
                        if b_elem is not None:
                            val = b_elem.attrib.get('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val', 'true')
                            if val not in ['0', 'false', 'none']:
                                is_b = True
                                has_bold = True
                        u_elem = r_pr.find('w:u', ns)
                        if u_elem is not None:
                            val = u_elem.attrib.get('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val', 'single')
                            if val not in ['0', 'false', 'none']:
                                is_u = True
                                has_underline = True

                    # Quét toàn bộ thẻ con theo thứ tự: văn bản, tab, dấu xuống dòng
                    for child in r:
                        tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
                        if tag == 't':
                            txt = child.text or ""
                            p_text_parts.append(txt)
                            if is_b:
                                bold_parts.append(txt)
                            if is_u:
                                underline_parts.append(txt)
                        elif tag == 'tab':
                            p_text_parts.append("    ")
                        elif tag == 'br':
                            p_text_parts.append(" ")
                        elif tag == 'noBreakHyphen':
                            p_text_parts.append("-")

                # Chuẩn hóa khoảng trắng và non-breaking spaces (\u00A0)
                raw_full = "".join(p_text_parts).replace('\u00a0', ' ')
                full_p = re.sub(r'[ \t]+', ' ', raw_full).strip()
                if full_p:
                    paragraphs.append({
                        "text": full_p,
                        "has_bold": has_bold,
                        "has_underline": has_underline,
                        "bold_text": re.sub(r'[ \t]+', ' ', "".join(bold_parts).replace('\u00a0', ' ')).strip(),
                        "underline_text": re.sub(r'[ \t]+', ' ', "".join(underline_parts).replace('\u00a0', ' ')).strip()
                    })
    except ValueError:
        raise
    except Exception as e:
        print("[word_mcq_parser] Lỗi đọc file docx:", e)

    return paragraphs

def parse_raw_text_to_paragraphs(raw_text: str) -> List[Dict[str, Any]]:
    """
    Chuyển văn bản thô (dán từ Clipboard) thành danh sách đoạn văn.
    """
    lines = raw_text.splitlines()
    paragraphs = []
    for line in lines:
        cleaned = line.strip()
        if cleaned:
            paragraphs.append({
                "text": cleaned,
                "has_bold": False,
                "has_underline": False,
                "bold_text": "",
                "underline_text": ""
            })
    return paragraphs

def parse_mcqs_from_paragraphs(paragraphs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Bóc tách các đoạn văn thành danh sách câu hỏi trắc nghiệm hoàn chỉnh.
    Tự động nhận diện:
      - Mã câu hỏi (Câu 1, 1., Câu 01, Bài 1...)
      - Nội dung câu hỏi
      - Các phương án A, B, C, D (dù chung dòng hay khác dòng, tab hoặc space)
      - Đáp án đúng (*A., gạch chân, in đậm, Đáp án: A, Bảng đáp án cuối)
      - Căn cứ / Giải thích
    """
    if not paragraphs:
        return []

    # 1. Quét tìm bảng đáp án ở cuối văn bản (nếu có)
    # Ví dụ: "BẢNG ĐÁP ÁN: 1.A, 2.B, 3.C" hoặc "1-A 2-B 3-C"
    answer_keys_map = {}
    found_key_header = False
    for p in paragraphs:
        txt = p["text"].strip()
        if re.search(r'(?:BẢNG|DANH SÁCH)?\s*(?:ĐÁP ÁN|KEY|ANSWER)\b', txt, re.IGNORECASE):
            found_key_header = True
        if found_key_header:
            matches = re.findall(r'(\d+)[\s.:\-_]*([A-Da-d])\b', txt)
            for q_num, ans_let in matches:
                answer_keys_map[int(q_num)] = ans_let.upper()

    questions = []
    current_q = None
    q_index_counter = 0

    # Pattern nhận diện bắt đầu một câu hỏi
    # Ví dụ: "Câu 1:", "Câu 1.", "Câu 1 -", "1.", "1:", "Câu 10)", "**Câu 1:**"
    q_start_re = re.compile(
        r'^(?:[*#_~]*\s*)?(?:(?:Câu\s*(?:hỏi\s*)?(\d+)|Bài\s*(\d+))[\s.:\-_/)]*|(\d+)[.:/)][ \t]+)(.*)', 
        re.IGNORECASE
    )

    # Pattern nhận diện phương án đơn lẻ: "A. ...", "*B. ...", "A) ...", "C - ...", "[A] ...", "(A) ..."
    opt_start_re = re.compile(
        r'^(?:[*#_~]*\s*)?(?:\[([A-Da-d])\]|\(([A-Da-d])\)|([A-Da-d])[.:\-_/)])[ \t]*(.*)'
    )

    # Pattern tách nhiều phương án trên cùng 1 dòng: "A. A4   B. A3   C. Letter   D. B5"
    multi_opt_re = re.compile(
        r'(?:^|[ \t]{2,}|\t)(?:[*#_~]*\s*)?(?:\[([A-Da-d])\]|\(([A-Da-d])\)|([A-Da-d]))[.:\-_/)]+[ \t]*'
    )

    for p in paragraphs:
        txt = p["text"].strip()
        if not txt:
            continue

        # Kiểm tra nếu là tiêu đề bảng đáp án cuối bài thì dừng
        if re.match(r'^(?:BẢNG|DANH SÁCH)\s*(?:ĐÁP ÁN|KEY)\b', txt, re.IGNORECASE):
            break

        # Kiểm tra nếu là bắt đầu câu hỏi mới
        q_match = q_start_re.match(txt)
        if q_match:
            # Lưu câu hỏi trước đó nếu có
            if current_q and current_q["question"] and len(current_q["options"]) >= 2:
                questions.append(finalize_question(current_q, q_index_counter, answer_keys_map))

            q_num_str = q_match.group(1) or q_match.group(2) or q_match.group(3)
            q_num = int(q_num_str) if q_num_str and q_num_str.isdigit() else (q_index_counter + 1)
            q_index_counter = q_num
            q_content = (q_match.group(4) or "").strip()

            current_q = {
                "num": q_num,
                "question": q_content,
                "options": [],
                "correct_index": None,
                "explanation": "",
                "group": "Nghị định 30/2020/NĐ-CP",
                "has_bold_opt": None
            }
            continue

        # Nếu chưa có câu hỏi nào thì bỏ qua phần lời tựa
        if not current_q:
            continue

        # Kiểm tra dòng đáp án riêng: "Đáp án: A", "Đ/a: B", "Key: C", "Đáp án đúng: D"
        ans_match = re.search(r'(?:Đáp\s*án(?:\s*đúng)?(?:\s*là)?|Đ/a|Key|ĐA|Answer)[\s.:\-]+([A-Da-d])\b', txt, re.IGNORECASE)
        if ans_match:
            ans_letter = ans_match.group(1).upper()
            idx = ord(ans_letter) - ord('A')
            current_q["correct_index"] = idx
            continue

        # Kiểm tra dòng căn cứ / giải thích: "Căn cứ: Điều 8", "Giải thích: ..."
        exp_match = re.search(r'^(?:Căn cứ|Giải thích|Ghi chú|Lưu ý)[\s.:\-]+(.*)', txt, re.IGNORECASE)
        if exp_match:
            current_q["explanation"] = exp_match.group(1).strip()
            continue

        # Kiểm tra phương án trả lời trên dòng này
        # Trường hợp 1: Có nhiều phương án trên 1 dòng (ví dụ "A. Khổ A4    B. Khổ A3    C. Letter    D. B5")
        multi_matches = list(multi_opt_re.finditer(txt))
        if len(multi_matches) >= 2:
            for i, m in enumerate(multi_matches):
                prefix = m.group(0).strip()
                start_val = m.end()
                end_val = multi_matches[i+1].start() if i + 1 < len(multi_matches) else len(txt)
                opt_body = txt[start_val:end_val].strip()
                process_option_item(current_q, prefix, opt_body, p)
            continue

        # Trường hợp 2: Dòng là một phương án đơn lẻ ("A. Khổ A4")
        opt_match = opt_start_re.match(txt)
        if opt_match:
            prefix = txt[:opt_match.end(1) if opt_match.group(1) else (opt_match.end(2) if opt_match.group(2) else opt_match.end(3))].strip()
            opt_body = opt_match.group(4).strip()
            process_option_item(current_q, prefix, opt_body, p)
            continue

        # Trường hợp 3: Nội dung câu hỏi kéo dài nhiều dòng (nối tiếp question)
        if len(current_q["options"]) == 0:
            if current_q["question"]:
                current_q["question"] += " " + txt
            else:
                current_q["question"] = txt
        else:
            # Hoặc là nội dung kéo dài của phương án trước đó
            if current_q["options"]:
                current_q["options"][-1] += " " + txt

    # Lưu câu hỏi cuối cùng
    if current_q and current_q["question"] and len(current_q["options"]) >= 2:
        questions.append(finalize_question(current_q, q_index_counter, answer_keys_map))

    return questions

def process_option_item(current_q: Dict[str, Any], prefix: str, opt_body: str, p: Dict[str, Any]):
    """Xử lý một phương án và phát hiện dấu hiệu đáp án đúng."""
    clean_body = opt_body.strip()
    is_correct = False

    # 1. Phát hiện dấu hoa thị * hoặc # hoặc [x]
    if "*" in prefix or "#" in prefix or clean_body.startswith("*") or "[x]" in prefix.lower():
        is_correct = True
        clean_body = re.sub(r'^[*#\s]+', '', clean_body).strip()

    # 2. Phát hiện dấu gạch chân trong file Word (gạch chân luôn là chỉ dấu đáp án đúng)
    if p.get("has_underline"):
        is_correct = True

    current_idx = len(current_q["options"])
    current_q["options"].append(clean_body)

    if is_correct and current_q["correct_index"] is None:
        current_q["correct_index"] = current_idx

def finalize_question(q: Dict[str, Any], counter: int, answer_keys: Dict[int, str]) -> Dict[str, Any]:
    """Hoàn thiện cấu trúc câu hỏi trước khi trả về."""
    # Nếu chưa có đáp án đúng, tra cứu trong bảng đáp án cuối (nếu có)
    c_idx = q.get("correct_index")
    if c_idx is None:
        q_num = q.get("num", counter)
        if q_num in answer_keys:
            let = answer_keys[q_num]
            calculated_idx = ord(let) - ord('A')
            if 0 <= calculated_idx < len(q["options"]):
                c_idx = calculated_idx

    # Nếu vẫn chưa tìm thấy đáp án, mặc định là 0 (A)
    if c_idx is None or c_idx < 0 or c_idx >= len(q["options"]):
        c_idx = 0

    return {
        "question": q["question"].strip(),
        "options": q["options"],
        "correct_index": c_idx,
        "explanation": q.get("explanation", "").strip(),
        "group": q.get("group", "Nghị định 30/2020/NĐ-CP").strip()
    }

def create_mcq_sample_docx(save_path: str):
    """Tạo file Word mẫu chuẩn (.docx) hướng dẫn giảng viên soạn câu hỏi."""
    os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)
    iso_now = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")

    content_types_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
</Types>"""

    rels_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
</Relationships>"""

    core_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:title>Mau_De_Thi_Trac_Nghiem_Nghi_Dinh_30</dc:title>
  <dc:creator>HeThongThiNghiDinh30</dc:creator>
  <dcterms:created xsi:type="dcterms:W3CDTF">{iso_now}</dcterms:created>
</cp:coreProperties>"""

    document_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p>
      <w:pPr><w:jc w:val="center"/></w:pPr>
      <w:r><w:rPr><w:b/><w:sz w:val="32"/><w:color w:val="1E3A8A"/></w:rPr><w:t>BỘ CÂU HỎI TRẮC NGHIỆM MẪU (NGHỊ ĐỊNH 30/2020/NĐ-CP)</w:t></w:r>
    </w:p>
    <w:p>
      <w:pPr><w:jc w:val="center"/></w:pPr>
      <w:r><w:rPr><w:i/><w:sz w:val="22"/><w:color w:val="64748B"/></w:rPr><w:t>(Giảng viên có thể đánh dấu đáp án đúng bằng: Dấu * trước phương án, Dòng "Đáp án: X", hoặc in đậm/gạch chân)</w:t></w:r>
    </w:p>
    <w:p><w:r><w:t></w:t></w:r></w:p>

    <!-- Câu 1 -->
    <w:p><w:r><w:rPr><w:b/><w:sz w:val="26"/></w:rPr><w:t>Câu 1: Theo Nghị định 30/2020/NĐ-CP, khổ giấy chuẩn áp dụng cho văn bản hành chính là:</w:t></w:r></w:p>
    <w:p><w:r><w:rPr><w:b/><w:color w:val="059669"/></w:rPr><w:t>*A. Khổ A4 (210 mm x 297 mm)</w:t></w:r></w:p>
    <w:p><w:r><w:t>B. Khổ A3 (297 mm x 420 mm)</w:t></w:r></w:p>
    <w:p><w:r><w:t>C. Khổ Letter (215.9 mm x 279.4 mm)</w:t></w:r></w:p>
    <w:p><w:r><w:t>D. Tùy chọn khổ A4 hoặc A5</w:t></w:r></w:p>
    <w:p><w:r><w:rPr><w:i/><w:color w:val="64748B"/></w:rPr><w:t>Căn cứ: Theo Điều 8 Nghị định 30/2020/NĐ-CP</w:t></w:r></w:p>
    <w:p><w:r><w:t></w:t></w:r></w:p>

    <!-- Câu 2 -->
    <w:p><w:r><w:rPr><w:b/><w:sz w:val="26"/></w:rPr><w:t>Câu 2: Phông chữ chuẩn bắt buộc sử dụng khi soạn thảo văn bản hành chính là:</w:t></w:r></w:p>
    <w:p><w:r><w:t>A. Phông chữ Arial</w:t></w:r></w:p>
    <w:p><w:r><w:t>B. Phông chữ Times New Roman, bộ mã Unicode tiêu chuẩn</w:t></w:r></w:p>
    <w:p><w:r><w:t>C. Phông chữ .VnTime thuộc bảng mã TCVN3</w:t></w:r></w:p>
    <w:p><w:r><w:t>D. Bất kỳ phông chữ Unicode nào</w:t></w:r></w:p>
    <w:p><w:r><w:rPr><w:b/><w:color w:val="059669"/></w:rPr><w:t>Đáp án: B</w:t></w:r></w:p>
    <w:p><w:r><w:rPr><w:i/><w:color w:val="64748B"/></w:rPr><w:t>Căn cứ: Phụ lục I Nghị định 30/2020/NĐ-CP</w:t></w:r></w:p>
    <w:p><w:r><w:t></w:t></w:r></w:p>

    <!-- Câu 3 -->
    <w:p><w:r><w:rPr><w:b/><w:sz w:val="26"/></w:rPr><w:t>Câu 3: Văn bản hành chính gồm bao nhiêu thành phần thể thức chính?</w:t></w:r></w:p>
    <w:p><w:r><w:t>A. 7 thành phần thể thức chính</w:t></w:r></w:p>
    <w:p><w:r><w:t>B. 8 thành phần thể thức chính</w:t></w:r></w:p>
    <w:p><w:r><w:rPr><w:b/><w:u w:val="single"/><w:color w:val="059669"/></w:rPr><w:t>C. 9 thành phần thể thức chính</w:t></w:r></w:p>
    <w:p><w:r><w:t>D. 12 thành phần thể thức chính</w:t></w:r></w:p>
    <w:p><w:r><w:rPr><w:i/><w:color w:val="64748B"/></w:rPr><w:t>Căn cứ: Điều 8 và Phụ lục I Nghị định 30/2020/NĐ-CP</w:t></w:r></w:p>

    <w:sectPr/>
  </w:body>
</w:document>"""

    with zipfile.ZipFile(save_path, 'w', zipfile.ZIP_DEFLATED) as docx_zip:
        docx_zip.writestr('[Content_Types].xml', content_types_xml)
        docx_zip.writestr('_rels/.rels', rels_xml)
        docx_zip.writestr('docProps/core.xml', core_xml)
        docx_zip.writestr('word/document.xml', document_xml)
