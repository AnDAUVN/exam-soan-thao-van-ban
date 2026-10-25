"""
Dịch vụ Tự động đồng bộ file tự luận Word lên Google Drive theo Lớp
Dành cho Giảng viên: cttrung@ntt.edu.vn (Trường Đại học Nguyễn Tất Thành - NTTU)
Sử dụng Google Apps Script Webhook độc lập, không yêu cầu thư viện bên thứ ba.
"""

import os
import json
import time
import base64
import threading
import urllib.request
import urllib.error
import re
from typing import Dict, Any, Optional

BASE_DIR = os.path.dirname(__file__)
CONFIG_FILE = os.path.join(BASE_DIR, "gdrive_config.json")
LINKS_FILE = os.path.join(BASE_DIR, "gdrive_links.json")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")

DEFAULT_CONFIG = {
    "teacher_email": "cttrung@ntt.edu.vn",
    "webhook_url": "",
    "auto_upload": True,
    "folder_prefix": "BÀI THI SOẠN THẢO VĂN BẢN (NĐ 30) - NTTU",
    "last_tested": None,
    "last_status": "Chưa kết nối Web App"
}

APPS_SCRIPT_TEMPLATE = """/**
 * GOOGLE APPS SCRIPT - TỰ ĐỘNG LƯU BÀI THI THEO LỚP CHO GIẢNG VIÊN
 * Giảng viên: cttrung@ntt.edu.vn
 * Trường Đại học Nguyễn Tất Thành (NTTU)
 * Môn học: Soạn thảo văn bản hành chính (Nghị định 30/2020/NĐ-CP)
 */

function doPost(e) {
  try {
    var data = JSON.parse(e.postData.contents);
    
    // 1. Nhận thông tin bài thi
    var fileName = data.file_name || ("Bai_Thi_" + (data.student_id || "SV") + ".docx");
    var fileBase64 = data.file_base64;
    var cohort = data.cohort || "Khoa_1";
    var className = data.class_name || "Lop_Chung";
    var studentId = data.student_id || "";
    var studentName = data.student_name || "";
    var caseIndex = data.case_index || 1;
    
    if (!fileBase64) {
      return ContentService.createTextOutput(JSON.stringify({
        status: "error",
        error: "Không có dữ liệu file (file_base64 trống)"
      })).setMimeType(ContentService.MimeType.JSON);
    }
    
    // 2. Thư mục gốc trên Google Drive của cttrung@ntt.edu.vn
    var rootFolderName = "BÀI THI SOẠN THẢO VĂN BẢN (NĐ 30) - cttrung@ntt.edu.vn";
    var rootFolder = getOrCreateFolder(DriveApp.getRootFolder(), rootFolderName);
    
    // 3. Thư mục Khóa (Ví dụ: Khóa 1, K156)
    var cohortFolder = getOrCreateFolder(rootFolder, cohort);
    
    // 4. Thư mục Lớp (Ví dụ: Lớp 01 - Văn thư lưu trữ, HC01)
    var classFolder = getOrCreateFolder(cohortFolder, className);
    
    // 5. Giải mã Base64 và Lưu file Word vào Thư mục Lớp
    var decodedBytes = Utilities.base64Decode(fileBase64);
    var blob = Utilities.newBlob(decodedBytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document", fileName);
    
    // Xóa bản cũ nếu sinh viên nộp đè bài mới
    var existingFiles = classFolder.getFilesByName(fileName);
    while (existingFiles.hasNext()) {
      existingFiles.next().setTrashed(true);
    }
    
    var file = classFolder.createFile(blob);
    file.setDescription("BÀI THI MÔN SOẠN THẢO VĂN BẢN (NGHỊ ĐỊNH 30)\\n" +
                        "Thí sinh: " + studentName + " (MSSV: " + studentId + ")\\n" +
                        "Khóa: " + cohort + " | Lớp: " + className + "\\n" +
                        "Văn bản thực hành số: " + caseIndex + "\\n" +
                        "Thời gian nộp: " + Utilities.formatDate(new Date(), "GMT+7", "dd/MM/yyyy HH:mm:ss") + "\\n" +
                        "Giảng viên phụ trách: cttrung@ntt.edu.vn");
    
    // Đặt quyền xem file qua liên kết
    try {
      file.setSharing(DriveApp.Access.ANYONE_WITH_LINK, DriveApp.Permission.VIEW);
    } catch(errShare) {}
    
    return ContentService.createTextOutput(JSON.stringify({
      status: "success",
      message: "Đã lưu bài thi lên Google Drive thành công",
      file_name: fileName,
      file_url: file.getUrl(),
      folder_url: classFolder.getUrl(),
      class_name: className,
      cohort: cohort,
      teacher_email: "cttrung@ntt.edu.vn"
    })).setMimeType(ContentService.MimeType.JSON);
    
  } catch (error) {
    return ContentService.createTextOutput(JSON.stringify({
      status: "error",
      error: error.toString()
    })).setMimeType(ContentService.MimeType.JSON);
  }
}

function doGet(e) {
  return ContentService.createTextOutput(JSON.stringify({
    status: "online",
    service: "NTTU Exam Drive Backup",
    teacher_email: "cttrung@ntt.edu.vn"
  })).setMimeType(ContentService.MimeType.JSON);
}

function getOrCreateFolder(parent, name) {
  var folders = parent.getFoldersByName(name);
  if (folders.hasNext()) {
    return folders.next();
  } else {
    return parent.createFolder(name);
  }
}
"""


class GDriveService:
    @staticmethod
    def load_config() -> Dict[str, Any]:
        """Tải cấu hình Google Drive từ file json"""
        if not os.path.exists(CONFIG_FILE):
            GDriveService.save_config(DEFAULT_CONFIG)
            return DEFAULT_CONFIG.copy()
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                # Đảm bảo các trường mặc định
                for k, v in DEFAULT_CONFIG.items():
                    if k not in cfg:
                        cfg[k] = v
                return cfg
        except Exception as e:
            print(f"⚠️ Lỗi đọc file gdrive_config.json: {e}")
            return DEFAULT_CONFIG.copy()

    @staticmethod
    def save_config(config: Dict[str, Any]):
        """Lưu cấu hình Google Drive"""
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️ Lỗi lưu file gdrive_config.json: {e}")

    @staticmethod
    def load_links() -> Dict[str, Any]:
        """Tải danh sách liên kết Google Drive đã lưu"""
        if not os.path.exists(LINKS_FILE):
            return {}
        try:
            with open(LINKS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ Lỗi đọc file gdrive_links.json: {e}")
            return {}

    @staticmethod
    def save_links(links: Dict[str, Any]):
        """Lưu danh sách liên kết Google Drive"""
        try:
            with open(LINKS_FILE, "w", encoding="utf-8") as f:
                json.dump(links, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️ Lỗi lưu file gdrive_links.json: {e}")

    @staticmethod
    def get_apps_script_code() -> str:
        """Trả về toàn bộ mã Apps Script để giảng viên dán vào script.google.com"""
        return APPS_SCRIPT_TEMPLATE

    @staticmethod
    def sanitize_filename(name: str) -> str:
        """Chuyển đổi chuỗi thành tên file an toàn"""
        clean = re.sub(r'[\\/*?:"<>|]', "", name)
        clean = clean.replace(" ", "_")
        return clean[:60]

    @staticmethod
    def upload_file(
        student_id: str,
        student_name: str,
        cohort: str,
        class_name: str,
        case_index: int,
        docx_path: str,
        active_sessions_dict: Optional[dict] = None
    ) -> Dict[str, Any]:
        """
        Gửi file tự luận lên Google Drive của cttrung@ntt.edu.vn thông qua Webhook Apps Script
        """
        config = GDriveService.load_config()
        webhook_url = (config.get("webhook_url") or "").strip()

        if not webhook_url:
            print(f"ℹ️ [GDRIVE] Chưa cấu hình webhook_url. Bỏ qua tải lên Drive cho sinh viên {student_id}")
            return {"status": "skipped", "message": "Chưa cấu hình URL Google Apps Script Web App"}

        if not os.path.exists(docx_path):
            print(f"⚠️ [GDRIVE] Không tìm thấy file {docx_path}")
            return {"status": "error", "error": f"Không tìm thấy file {docx_path}"}

        try:
            with open(docx_path, "rb") as f:
                file_bytes = f.read()

            base64_data = base64.b64encode(file_bytes).decode('utf-8')
            safe_name = GDriveService.sanitize_filename(student_name)
            file_name = f"VB{case_index}_{student_id}_{safe_name}.docx"

            payload = {
                "teacher_email": config.get("teacher_email", "cttrung@ntt.edu.vn"),
                "file_name": file_name,
                "file_base64": base64_data,
                "cohort": cohort or "Khóa 1",
                "class_name": class_name or "Lớp Chung",
                "student_id": student_id,
                "student_name": student_name,
                "case_index": case_index
            }

            post_data = json.dumps(payload, ensure_ascii=False).encode('utf-8')
            req = urllib.request.Request(
                webhook_url,
                data=post_data,
                headers={
                    "Content-Type": "application/json; charset=utf-8",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) NTTU-Exam-Server/1.0"
                }
            )

            print(f"🚀 [GDRIVE] Đang gửi bài VB{case_index} của SV {student_name} ({student_id}) lên Google Drive...")
            with urllib.request.urlopen(req, timeout=45) as resp:
                resp_bytes = resp.read()
                resp_text = resp_bytes.decode('utf-8', errors='ignore')
                result = json.loads(resp_text)

            if result.get("status") == "success":
                file_url = result.get("file_url", "")
                folder_url = result.get("folder_url", "")
                print(f"✅ [GDRIVE] Tải lên Drive thành công!\n   👉 File Link: {file_url}\n   👉 Thư mục Lớp: {folder_url}")

                # Lưu vào file gdrive_links.json để lưu trữ lâu dài
                links = GDriveService.load_links()
                s_links = links.setdefault(student_id, {})
                s_links[f"case_{case_index}"] = {
                    "file_name": file_name,
                    "file_url": file_url,
                    "folder_url": folder_url,
                    "cohort": cohort,
                    "class_name": class_name,
                    "uploaded_at": time.strftime("%Y-%m-%d %H:%M:%S")
                }
                GDriveService.save_links(links)

                # Đồng bộ vào session in-memory nếu có
                if active_sessions_dict and student_id in active_sessions_dict:
                    session = active_sessions_dict[student_id]
                    session.setdefault("gdrive_links", {})[f"case_{case_index}"] = {
                        "file_name": file_name,
                        "file_url": file_url,
                        "folder_url": folder_url
                    }

                return {
                    "status": "success",
                    "file_url": file_url,
                    "folder_url": folder_url,
                    "file_name": file_name
                }
            else:
                err_msg = result.get("error", "Lỗi phản hồi từ Google Apps Script")
                print(f"❌ [GDRIVE] Google Apps Script báo lỗi: {err_msg}")
                return {"status": "error", "error": err_msg}

        except urllib.error.HTTPError as e:
            err_msg = f"HTTP {e.code}: {e.reason}"
            print(f"❌ [GDRIVE] Lỗi kết nối Webhook: {err_msg}")
            return {"status": "error", "error": err_msg}
        except Exception as e:
            err_msg = str(e)
            print(f"❌ [GDRIVE] Ngoại lệ khi tải lên Drive: {err_msg}")
            return {"status": "error", "error": err_msg}

    @staticmethod
    def upload_file_async(
        student_id: str,
        student_name: str,
        cohort: str,
        class_name: str,
        case_index: int,
        docx_path: str,
        active_sessions_dict: Optional[dict] = None
    ):
        """Chạy upload trong luồng nền (background thread) để không làm nghẽn bài thi của thí sinh"""
        thread = threading.Thread(
            target=GDriveService.upload_file,
            args=(student_id, student_name, cohort, class_name, case_index, docx_path, active_sessions_dict),
            daemon=True
        )
        thread.start()

    @staticmethod
    def test_connection(webhook_url: Optional[str] = None) -> Dict[str, Any]:
        """Gửi kiểm tra kết nối với Google Apps Script Web App của cttrung@ntt.edu.vn"""
        config = GDriveService.load_config()
        url = (webhook_url or config.get("webhook_url") or "").strip()

        if not url:
            return {"status": "error", "error": "Vui lòng nhập URL Google Apps Script Web App trước khi kiểm tra"}

        test_payload = {
            "teacher_email": config.get("teacher_email", "cttrung@ntt.edu.vn"),
            "file_name": "TEST_KET_NOI_GOOGLE_DRIVE.docx",
            "file_base64": base64.b64encode(b"NTTU Test Connection File Content").decode('utf-8'),
            "cohort": "Kiem_Tra_Ket_Noi",
            "class_name": "Lop_Test",
            "student_id": "TEST_001",
            "student_name": "Kiem Tra He Thong",
            "case_index": 1
        }

        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(test_payload).encode('utf-8'),
                headers={
                    "Content-Type": "application/json; charset=utf-8",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) NTTU-Exam-Server/1.0"
                }
            )

            with urllib.request.urlopen(req, timeout=30) as resp:
                resp_text = resp.read().decode('utf-8', errors='ignore')
                result = json.loads(resp_text)

            if result.get("status") == "success":
                config["last_tested"] = time.strftime("%Y-%m-%d %H:%M:%S")
                config["last_status"] = "Kết nối thành công"
                if webhook_url:
                    config["webhook_url"] = webhook_url
                GDriveService.save_config(config)
                return {
                    "status": "success",
                    "message": "Kết nối thành công với Google Drive của cttrung@ntt.edu.vn!",
                    "folder_url": result.get("folder_url", ""),
                    "file_url": result.get("file_url", "")
                }
            else:
                return {"status": "error", "error": result.get("error", "Lỗi không xác định từ Apps Script")}

        except urllib.error.HTTPError as e:
            return {"status": "error", "error": f"Lỗi HTTP {e.code}: {e.reason}. Hãy đảm bảo Web App được cấp quyền 'Bất kỳ ai' (Anyone)."}
        except Exception as e:
            return {"status": "error", "error": f"Lỗi kết nối: {str(e)}"}
