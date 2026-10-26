import os
import json
import uuid
import time
from typing import Tuple, Dict, Any

BASE_DIR = os.path.dirname(__file__)
TEACHER_AUTH_FILE = os.path.join(BASE_DIR, "teacher_auth.json")
DEFAULT_TEACHER_PASSWORD = os.environ.get("TEACHER_PASSWORD", "GiaoVien@2026")

def load_teacher_auth() -> Dict[str, Any]:
    if os.path.exists(TEACHER_AUTH_FILE):
        try:
            with open(TEACHER_AUTH_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    data.setdefault("password", DEFAULT_TEACHER_PASSWORD)
                    data.setdefault("active_tokens", {})
                    return data
        except Exception as e:
            print("Lỗi đọc teacher_auth.json:", e)
    
    # Mặc định ban đầu
    initial_data = {
        "password": DEFAULT_TEACHER_PASSWORD,
        "active_tokens": {}
    }
    save_teacher_auth(initial_data)
    return initial_data

def save_teacher_auth(data: Dict[str, Any]):
    try:
        with open(TEACHER_AUTH_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("Lỗi lưu teacher_auth.json:", e)

class TeacherAuthService:
    @staticmethod
    def verify_password(password: str) -> bool:
        data = load_teacher_auth()
        stored_pwd = str(data.get("password", DEFAULT_TEACHER_PASSWORD)).strip()
        input_pwd = str(password).strip()
        if input_pwd == stored_pwd:
            return True
        # Chấp nhận không phân biệt chữ hoa/chữ thường (ví dụ: Giaovien@2026 và GiaoVien@2026)
        if input_pwd.lower() == stored_pwd.lower():
            return True
        return False

    @staticmethod
    def login(password: str) -> Tuple[bool, str]:
        if not TeacherAuthService.verify_password(password):
            return False, "Mật khẩu Giảng viên không chính xác!"
        
        token = f"TEACHER_TOKEN_{uuid.uuid4().hex}_{int(time.time())}"
        data = load_teacher_auth()
        data.setdefault("active_tokens", {})[token] = {
            "created_at": time.time(),
            "expires_at": time.time() + (86400 * 7) # 7 ngày
        }
        save_teacher_auth(data)
        return True, token

    @staticmethod
    def is_valid_token(token: str) -> bool:
        if not token:
            return False
        clean_token = token.strip()
        data = load_teacher_auth()
        tokens = data.get("active_tokens", {})
        if clean_token in tokens:
            info = tokens[clean_token]
            if time.time() < info.get("expires_at", 0):
                return True
            else:
                # Token hết hạn
                del tokens[clean_token]
                save_teacher_auth(data)
                return False
        return False

    @staticmethod
    def logout(token: str) -> bool:
        if not token:
            return True
        data = load_teacher_auth()
        tokens = data.get("active_tokens", {})
        if token in tokens:
            del tokens[token]
            save_teacher_auth(data)
        return True

    @staticmethod
    def change_password(old_pwd: str, new_pwd: str) -> Tuple[bool, str]:
        if not TeacherAuthService.verify_password(old_pwd):
            return False, "Mật khẩu cũ không chính xác!"
        new_clean = str(new_pwd).strip()
        if len(new_clean) < 6:
            return False, "Mật khẩu mới phải có ít nhất 6 ký tự!"
        
        data = load_teacher_auth()
        data["password"] = new_clean
        # Giữ lại các tokens hiện tại hoặc xóa tùy ý
        save_teacher_auth(data)
        return True, "Đổi mật khẩu Giảng viên thành công!"
