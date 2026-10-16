from datetime import datetime
from typing import List, Optional, Tuple


class Customer:
    """Đại diện thông tin khách hàng và trạng thái VIP."""
    def __init__(self, customer_id: str, name: str, phone_number: str, is_vip: bool = False):
        self.customer_id = customer_id.strip()
        self.name = name.strip()
        self.phone_number = phone_number.strip()
        self.is_vip = bool(is_vip)

    def __repr__(self):
        vip_tag = "VIP" if self.is_vip else "Regular"
        return f"<Customer {self.customer_id}: {self.name} ({vip_tag})>"


class Issue:
    """
    Theo dõi một vấn đề dịch vụ xuyên suốt nhiều lần gọi (Call).
    Trạng thái hợp lệ: OPEN, RESOLVED.
    """
    STATUS_OPEN = "OPEN"
    STATUS_RESOLVED = "RESOLVED"

    # Hằng số cấu hình theo Phụ lục A
    DUPLICATE_WINDOW_SECONDS = 60
    MIN_ELIGIBLE_WAIT_SECONDS = 120  # 2 phút

    def __init__(self, issue_id: str, customer_id: str, issue_type: str,
                 created_at: datetime, description: str = ""):
        self.issue_id = issue_id.strip()
        self.customer_id = customer_id.strip()
        self.issue_type = issue_type.strip()
        self.description = description.strip()
        self.created_at = created_at
        self.status = self.STATUS_OPEN
        self.resolved_at: Optional[datetime] = None

        # Lịch sử phục vụ tính điểm
        self.valid_callback_count: int = 0
        self.waiting_segments: List[Tuple[datetime, datetime]] = []  # Các phiên chờ đã đóng
        self.last_contact_time: Optional[datetime] = None
        self.has_had_first_valid_call: bool = False

    def is_duplicate_contact(self, arrival_time: datetime) -> bool:
        """Kiểm tra cuộc gọi lặp trong cửa sổ 60 giây của cùng Issue."""
        if self.last_contact_time is None:
            return False
        delta = (arrival_time - self.last_contact_time).total_seconds()
        return 0 <= delta <= self.DUPLICATE_WINDOW_SECONDS

    def register_valid_call(self, arrival_time: datetime) -> bool:
        """
        Ghi nhận một lần gọi hợp lệ vào Issue đang OPEN.
        Trả về True nếu đây là một Callback hợp lệ (+ điểm), False nếu là lần gọi đầu.
        """
        if self.status != self.STATUS_OPEN:
            raise ValueError("Không thể ghi nhận callback cho Issue đã RESOLVED.")

        is_callback = False
        if not self.has_had_first_valid_call:
            self.has_had_first_valid_call = True
        else:
            self.valid_callback_count += 1
            is_callback = True

        self.last_contact_time = arrival_time
        return is_callback

    def add_waiting_segment(self, start_time: datetime, end_time: datetime) -> int:
        """
        Lưu một phiên chờ khi Call rời hàng đợi (sang IN_SERVICE hoặc ABANDONED).
        Chỉ cộng phiên chờ đạt tối thiểu 2 phút (120 giây).
        """
        duration_sec = (end_time - start_time).total_seconds()
        if duration_sec >= self.MIN_ELIGIBLE_WAIT_SECONDS:
            self.waiting_segments.append((start_time, end_time))
            return int(duration_sec // 60)
        return 0

    def get_total_eligible_waiting_minutes(self, active_call_Wait_start: Optional[datetime] = None,
                                           current_time: Optional[datetime] = None) -> int:
        """
        Tính tổng số phút chờ hợp lệ tích lũy của Issue (không cộng trùng).
        Bao gồm các phiên chờ đã đóng + phiên đang WAITING hiện tại (nếu đủ >= 2 phút).
        """
        total_seconds = 0.0
        for start, end in self.waiting_segments:
            sec = (end - start).total_seconds()
            if sec >= self.MIN_ELIGIBLE_WAIT_SECONDS:
                total_seconds += sec

        if active_call_Wait_start and current_time:
            current_sec = (current_time - active_call_Wait_start).total_seconds()
            if current_sec >= self.MIN_ELIGIBLE_WAIT_SECONDS:
                total_seconds += current_sec

        return int(total_seconds // 60)

    def resolve(self, resolved_time: datetime):
        """Đóng Issue khi vấn đề đã được giải quyết hoàn toàn."""
        self.status = self.STATUS_RESOLVED
        self.resolved_at = resolved_time


class Call:
    """
    Đại diện một lần khách gọi đến.
    Chỉ các Call ở trạng thái WAITING mới nằm trong Multi-Level Queue.
    """
    STATUS_WAITING = "WAITING"
    STATUS_IN_SERVICE = "IN_SERVICE"
    STATUS_COMPLETED = "COMPLETED"
    STATUS_ABANDONED = "ABANDONED"
    STATUS_MISSED = "MISSED"
    STATUS_DISCONNECTED = "DISCONNECTED"

    VALID_STATUSES = {
        STATUS_WAITING, STATUS_IN_SERVICE, STATUS_COMPLETED,
        STATUS_ABANDONED, STATUS_MISSED, STATUS_DISCONNECTED
    }

    def __init__(self, call_id: str, customer_id: str, issue_id: str,
                 arrival_time: datetime, sequence_number: int = 0,
                 status: str = STATUS_WAITING):
        if status not in self.VALID_STATUSES:
            raise ValueError(f"Trạng thái Call không hợp lệ: {status}")

        self.call_id = call_id.strip()
        self.customer_id = customer_id.strip()
        self.issue_id = issue_id.strip()
        self.arrival_time = arrival_time
        self.queue_entered_at: Optional[datetime] = arrival_time if status == self.STATUS_WAITING else None
        self.level_entered_at: Optional[datetime] = arrival_time if status == self.STATUS_WAITING else None
        self.service_start_time: Optional[datetime] = None
        self.ended_at: Optional[datetime] = None

        self.status = status
        self.score: int = 1
        self.queue_level: int = 1
        self.sequence_number: int = sequence_number

    def __repr__(self):
        return (f"<Call {self.call_id} | Cust:{self.customer_id} | Issue:{self.issue_id} | "
                f"Score:{self.score} (L{self.queue_level}) | Status:{self.status}>")


class CallEvent:
    """Lưu lịch sử sự kiện của từng Call để tra cứu và kiểm tra cách tính điểm."""
    def __init__(self, event_id: str, call_id: str, event_type: str,
                 event_time: datetime, note: str = ""):
        self.event_id = event_id.strip()
        self.call_id = call_id.strip()
        self.event_type = event_type.strip()
        self.event_time = event_time
        self.note = note.strip()

    def __repr__(self):
        time_str = self.event_time.strftime("%Y-%m-%d %H:%M:%S")
        return f"[{time_str}] Event {self.event_id} (Call {self.call_id}): {self.event_type} - {self.note}"