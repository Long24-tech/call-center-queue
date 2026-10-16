from validator import Validator


class CLIMenu:
    """
    Khung giao diện CLI (Menu Skeleton) theo Mục 10.4 của tài liệu thiết kế mới.
    Chạy độc lập với dữ liệu mẫu ở Tuần 2 trước khi nối vào CallCenter ở Tuần 3.
    """
    MENU_OPTIONS = {
        1: "Thêm khách hàng / cập nhật thông tin khách hàng",
        2: "Tạo Issue mới",
        3: "Tiếp nhận cuộc gọi mới hoặc callback cho Issue đang mở",
        4: "Xem tất cả hàng đợi theo bốn mức ưu tiên (Level 4 -> Level 1)",
        5: "Cập nhật thời gian chờ và tính lại điểm (Refresh Waiting Queue)",
        6: "Xử lý cuộc gọi tiếp theo (Process Next Call)",
        7: "Cập nhật kết quả Call và trạng thái Issue (COMPLETED/ABANDONED & OPEN/RESOLVED)",
        8: "Xem lịch sử cuộc gọi của khách hàng / Issue",
        9: "Xem thống kê hệ thống",
        0: "Lưu dữ liệu và thoát chương trình",
    }

    @classmethod
    def render_menu(cls) -> str:
        lines = [
            "\n" + "=" * 68,
            "   CALL CENTER WAITING LINE SYSTEM (MULTI-LEVEL QUEUE SIMULATION)",
            "=" * 68
        ]
        for key in [1, 2, 3, 4, 5, 6, 7, 8, 9, 0]:
            lines.append(f"  [{key}] {cls.MENU_OPTIONS[key]}")
        lines.append("=" * 68)
        return "\n".join(lines)

    @classmethod
    def parse_user_option(cls, raw_input: str) -> int:
        """Xác thực lựa chọn của người dùng trên menu chính."""
        return Validator.validate_menu_choice(raw_input, 0, 9)