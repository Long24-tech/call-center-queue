import re
from datetime import datetime
from typing import Optional
from models import Call, Issue


class Validator:
    """Kiểm tra tính hợp lệ của toàn bộ dữ liệu đầu vào từ CLI."""

    ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{2,20}$")
    PHONE_PATTERN = re.compile(r"^0\d{9,10}$")

    @classmethod
    def validate_id(cls, value: str, prefix: str = "") -> str:
        """Kiểm tra mã định danh (Customer ID, Issue ID, Call ID)."""
        if not isinstance(value, str) or not value.strip():
            raise ValueError("ID không được để trống.")
        cleaned = value.strip().upper()
        if not cls.ID_PATTERN.match(cleaned):
            raise ValueError(f"ID '{value}' chứa ký tự không hợp lệ hoặc độ dài ngoài khoảng 2-20.")
        if prefix and not cleaned.startswith(prefix.upper()):
            raise ValueError(f"ID '{cleaned}' phải bắt đầu bằng tiền tố '{prefix.upper()}'.")
        return cleaned

    @classmethod
    def validate_non_empty_text(cls, value: str, field_name: str = "Trường dữ liệu") -> str:
        """Kiểm tra chuỗi tên hoặc mô tả không được rỗng."""
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field_name} không được để trống.")
        return value.strip()

    @classmethod
    def validate_phone(cls, phone: str) -> str:
        """Kiểm tra số điện thoại Việt Nam (10-11 chữ số, bắt đầu bằng 0)."""
        if not isinstance(phone, str) or not phone.strip():
            raise ValueError("Số điện thoại không được để trống.")
        cleaned = phone.strip()
        if not cls.PHONE_PATTERN.match(cleaned):
            raise ValueError(f"Số điện thoại '{phone}' không hợp lệ (cần 10-11 chữ số, bắt đầu bằng số 0).")
        return cleaned

    @staticmethod
    def validate_vip_flag(value: str) -> bool:
        """Chuyển đổi chuỗi nhập VIP ('y/n', 'true/false', '1/0') sang boolean."""
        if isinstance(value, bool):
            return value
        if not isinstance(value, str):
            raise ValueError("Giá trị VIP không hợp lệ.")
        cleaned = value.strip().lower()
        if cleaned in {"true", "t", "yes", "y", "1", "vip"}:
            return True
        if cleaned in {"false", "f", "no", "n", "0", "regular", "normal"}:
            return False
        raise ValueError(f"Trạng thái VIP '{value}' không hợp lệ (nhập y/n hoặc true/false).")

    @staticmethod
    def validate_datetime(time_str: str, base_date: Optional[datetime] = None) -> datetime:
        """
        Hỗ trợ parse định dạng 'YYYY-MM-DD HH:MM', 'YYYY-MM-DD HH:MM:SS' hoặc 'HH:MM'.
        Phục vụ Event-driven Simulation.
        """
        if not isinstance(time_str, str) or not time_str.strip():
            raise ValueError("Thời gian không được để trống.")
        cleaned = time_str.strip()

        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
            try:
                return datetime.strptime(cleaned, fmt)
            except ValueError:
                pass

        # Nếu chỉ nhập giờ:phút (VD: "09:15")
        for fmt in ("%H:%M:%S", "%H:%M"):
            try:
                parsed_time = datetime.strptime(cleaned, fmt).time()
                ref = base_date or datetime(2026, 10, 15)
                return datetime.combine(ref.date(), parsed_time)
            except ValueError:
                pass

        raise ValueError(f"Định dạng thời gian '{time_str}' không hợp lệ (dùng 'YYYY-MM-DD HH:MM' hoặc 'HH:MM').")

    @staticmethod
    def validate_menu_choice(choice: str, min_val: int = 0, max_val: int = 9) -> int:
        """Kiểm tra lựa chọn menu từ 0 đến 9."""
        if not isinstance(choice, str) or not choice.strip().isdigit():
            raise ValueError("Lựa chọn menu phải là một số nguyên.")
        val = int(choice.strip())
        if not (min_val <= val <= max_val):
            raise ValueError(f"Lựa chọn menu phải nằm trong khoảng từ {min_val} đến {max_val}.")
        return val

    @staticmethod
    def validate_call_status(status: str) -> str:
        """Kiểm tra trạng thái Call hợp lệ."""
        cleaned = status.strip().upper() if isinstance(status, str) else ""
        if cleaned not in Call.VALID_STATUSES:
            raise ValueError(f"Trạng thái Call '{status}' không hợp lệ.")
        return cleaned

    @staticmethod
    def validate_issue_status(status: str) -> str:
        """Kiểm tra trạng thái Issue hợp lệ (OPEN / RESOLVED)."""
        cleaned = status.strip().upper() if isinstance(status, str) else ""
        if cleaned not in {Issue.STATUS_OPEN, Issue.STATUS_RESOLVED}:
            raise ValueError(f"Trạng thái Issue '{status}' không hợp lệ (chỉ nhận OPEN hoặc RESOLVED).")
        return cleaned

    @staticmethod
    def forbid_manual_priority_input(user_payload: dict) -> None:
        """
        Nguyên tắc dữ liệu Mục 3.2 & 10.2:
        Người dùng không được tự nhập Priority Score hoặc Queue Level.
        """
        forbidden_keys = {"score", "priority_score", "queue_level", "level"}
        found = forbidden_keys.intersection(set(k.lower() for k in user_payload.keys()))
        if found:
            raise PermissionError(
                f"Hệ thống tự động tính điểm ưu tiên và Level. Không cho phép nhập thủ công: {found}"
            )