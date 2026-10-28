"""
Module Quản lý Xác thực Giảng viên (Teacher Authentication Service)
L10: Lưu trữ và kiểm tra mật khẩu an toàn:
- Băm mật khẩu bằng PBKDF2-HMAC-SHA256 với Salt ngẫu nhiên và 100.000 vòng lặp.
- So sánh mật khẩu phân biệt chữ hoa/thường, chống Timing Attack với secrets.compare_digest.
- Giới hạn số lần đăng nhập sai (Rate Limiting).
- Thu hồi toàn bộ phiên đăng nhập (active_tokens) khi đổi mật khẩu.
"""

from __future__ import annotations
import os
import json
import uuid
import time
import hashlib
import secrets
import threading
from typing import Tuple, Dict, Any, List

BASE_DIR = os.path.dirname(__file__)
TEACHER_AUTH_FILE = os.path.join(BASE_DIR, "teacher_auth.json")
DEFAULT_TEACHER_PASSWORD = os.environ.get("TEACHER_PASSWORD", "GiaoVien@2026")
_AUTH_LOCK = threading.RLock()

# Bộ nhớ tạm ghi nhận các lần đăng nhập sai để Rate Limiting chống Brute-force
_FAILED_LOGINS: Dict[str, List[float]] = {}
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION_SECONDS = 300  # 5 phút

def hash_password(password: str, salt: bytes = None) -> str:
    """Băm mật khẩu bằng PBKDF2-HMAC-SHA256 với Salt ngẫu nhiên 16 bytes."""
    if salt is None:
        salt = os.urandom(16)
    kdf = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100_000)
    return f"{salt.hex()}${kdf.hex()}"

def verify_password_hash(password: str, stored_hash: str) -> bool:
    """So sánh mật khẩu dạng băm với thời gian không đổi (Constant-time comparison)."""
    try:
        parts = stored_hash.split("$", 1)
        if len(parts) != 2:
            return False
        salt = bytes.fromhex(parts[0])
        expected_kdf = bytes.fromhex(parts[1])
        calc_kdf = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100_000)
        return secrets.compare_digest(calc_kdf, expected_kdf)
    except Exception:
        return False

def load_teacher_auth() -> Dict[str, Any]:
    with _AUTH_LOCK:
        if os.path.exists(TEACHER_AUTH_FILE):
            try:
                with open(TEACHER_AUTH_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        # Tự động di chuyển từ mật khẩu dạng rõ sang băm an toàn (Migration)
                        if "password" in data and "password_hash" not in data:
                            plain = data.pop("password")
                            data["password_hash"] = hash_password(plain)
                            save_teacher_auth(data)
                        elif "password_hash" not in data:
                            data["password_hash"] = hash_password(DEFAULT_TEACHER_PASSWORD)
                            save_teacher_auth(data)
                        data.setdefault("active_tokens", {})
                        return data
            except Exception as e:
                print("Lỗi đọc teacher_auth.json:", e)

        # Mặc định ban đầu nếu chưa có file
        initial_data = {
            "password_hash": hash_password(DEFAULT_TEACHER_PASSWORD),
            "active_tokens": {}
        }
        save_teacher_auth(initial_data)
        return initial_data

def save_teacher_auth(data: Dict[str, Any]):
    with _AUTH_LOCK:
        try:
            tmp_path = TEACHER_AUTH_FILE + ".tmp"
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            if os.path.exists(tmp_path):
                try:
                    os.replace(tmp_path, TEACHER_AUTH_FILE)
                except Exception:
                    # Dự phòng trên hệ điều hành Windows khi file đích bị khóa
                    with open(TEACHER_AUTH_FILE, "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                    try:
                        os.remove(tmp_path)
                    except Exception:
                        pass
        except Exception as e:
            print("Lỗi lưu teacher_auth.json:", e)

class TeacherAuthService:
    @staticmethod
    def is_rate_limited(client_key: str = "default") -> Tuple[bool, int]:
        """Kiểm tra xem client có đang bị tạm khóa do nhập sai mật khẩu nhiều lần không."""
        now = time.time()
        attempts = _FAILED_LOGINS.get(client_key, [])
        # Lọc các lần vi phạm trong vòng 5 phút qua
        recent = [t for t in attempts if (now - t) < LOCKOUT_DURATION_SECONDS]
        _FAILED_LOGINS[client_key] = recent
        if len(recent) >= MAX_FAILED_ATTEMPTS:
            remaining_lock = int(LOCKOUT_DURATION_SECONDS - (now - recent[0]))
            return True, max(1, remaining_lock)
        return False, 0

    @staticmethod
    def record_failed_attempt(client_key: str = "default"):
        now = time.time()
        _FAILED_LOGINS.setdefault(client_key, []).append(now)

    @staticmethod
    def clear_failed_attempts(client_key: str = "default"):
        _FAILED_LOGINS.pop(client_key, None)

    @staticmethod
    def verify_password(password: str) -> bool:
        """
        L10: So sánh mật khẩu phân biệt chữ hoa/thường (Case-sensitive)
        và sử dụng thuật toán băm bảo mật.
        """
        data = load_teacher_auth()
        stored_hash = data.get("password_hash")
        if not stored_hash:
            return False
        return verify_password_hash(password, stored_hash)

    @staticmethod
    def login(password: str, client_ip: str = "default") -> Tuple[bool, str]:
        # Kiểm tra rate limit chống brute-force
        limited, rem_sec = TeacherAuthService.is_rate_limited(client_ip)
        if limited:
            return False, f"Bạn đã nhập sai mật khẩu quá {MAX_FAILED_ATTEMPTS} lần! Vui lòng chờ {rem_sec} giây trước khi thử lại."

        if not TeacherAuthService.verify_password(password):
            TeacherAuthService.record_failed_attempt(client_ip)
            _, rem = TeacherAuthService.is_rate_limited(client_ip)
            rem_tries = MAX_FAILED_ATTEMPTS - len(_FAILED_LOGINS.get(client_ip, []))
            if rem_tries > 0:
                return False, f"Mật khẩu Giảng viên không chính xác! (Còn {rem_tries} lần thử trước khi bị tạm khóa)"
            return False, "Mật khẩu không chính xác! Bạn đã bị tạm khóa 5 phút."

        # Đăng nhập thành công -> xóa lịch sử vi phạm
        TeacherAuthService.clear_failed_attempts(client_ip)

        token = f"TEACHER_TOKEN_{secrets.token_hex(24)}_{int(time.time())}"
        data = load_teacher_auth()
        data.setdefault("active_tokens", {})[token] = {
            "created_at": time.time(),
            "expires_at": time.time() + (86400 * 7),  # 7 ngày
            "ip": client_ip
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
        """
        L10: Đổi mật khẩu:
        - Kiểm tra mật khẩu cũ nghiêm ngặt.
        - Băm mật khẩu mới bằng PBKDF2-HMAC-SHA256.
        - Thu hồi TOÀN BỘ phiên đăng nhập cũ (Revoke all active tokens).
        """
        if not TeacherAuthService.verify_password(old_pwd):
            return False, "Mật khẩu cũ không chính xác!"
        new_clean = str(new_pwd).strip()
        if len(new_clean) < 6:
            return False, "Mật khẩu mới phải có ít nhất 6 ký tự!"

        data = load_teacher_auth()
        data["password_hash"] = hash_password(new_clean)
        # Xóa bỏ mật khẩu dạng rõ nếu còn
        data.pop("password", None)
        # L10: Thu hồi toàn bộ active token đang hoạt động, buộc đăng nhập lại
        data["active_tokens"] = {}
        save_teacher_auth(data)
        return True, "Đổi mật khẩu thành công! Tất cả phiên làm việc cũ đã được thu hồi an toàn."
