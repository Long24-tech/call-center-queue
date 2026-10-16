from datetime import datetime
from typing import Dict, Optional, Tuple, List
from models import Customer, Issue, Call
from queue import Queue


class PriorityManager:
    """
    Quản lý công thức tính điểm ưu tiên và điều phối 4 hàng đợi (Multi-Level Queue).
    Thay thế cấu trúc Max Heap cũ theo thiết kế mới đã chốt.
    """
    # Cấu hình điểm theo Mục 5 & Phụ lục A
    BASE_SCORE_REGULAR = 1
    BASE_SCORE_VIP = 7
    CALLBACK_POINTS_PER_CALL = 2
    MAX_CALLBACK_POINTS = 4
    WAITING_MINUTES_PER_POINT = 5
    MAX_WAITING_POINTS = 6

    def __init__(self):
        # Khởi tạo 4 hàng đợi FIFO tương ứng Level 1 -> Level 4
        self.queues: Dict[int, Queue] = {
            1: Queue("Level 1 - Regular (1-2 pts)"),
            2: Queue("Level 2 - Important (3-5 pts)"),
            3: Queue("Level 3 - High Priority (6-9 pts)"),
            4: Queue("Level 4 - Immediate Service (10+ pts)"),
        }

    @staticmethod
    def get_level(score: int) -> int:
        """Xác định Queue Level (1..4) dựa trên Priority Score - O(1)."""
        if score >= 10:
            return 4
        elif score >= 6:
            return 3
        elif score >= 3:
            return 2
        else:
            return 1

    @classmethod
    def calculate_score_components(cls, customer: Customer, issue: Issue,
                                   active_wait_start: Optional[datetime] = None,
                                   current_time: Optional[datetime] = None) -> Tuple[int, int, int, int]:
        """
        Tính điểm chi tiết: (base_score, callback_points, waiting_points, total_score).
        Công thức: Priority Score = Base Score + Callback Points + Waiting Points.
        """
        base = cls.BASE_SCORE_VIP if customer.is_vip else cls.BASE_SCORE_REGULAR
        callback_pts = min(issue.valid_callback_count * cls.CALLBACK_POINTS_PER_CALL,
                           cls.MAX_CALLBACK_POINTS)

        eligible_minutes = issue.get_total_eligible_waiting_minutes(
            active_call_Wait_start=active_wait_start,
            current_time=current_time
        )
        waiting_pts = min(eligible_minutes // cls.WAITING_MINUTES_PER_POINT,
                          cls.MAX_WAITING_POINTS)

        total = base + callback_pts + waiting_pts
        return base, callback_pts, waiting_pts, total

    @classmethod
    def calculate_priority(cls, customer: Customer, issue: Issue,
                           active_wait_start: Optional[datetime] = None,
                           current_time: Optional[datetime] = None) -> int:
        """Trả về tổng Priority Score."""
        _, _, _, total = cls.calculate_score_components(
            customer, issue, active_wait_start, current_time
        )
        return total

    def enqueue_call(self, call: Call, customer: Customer, issue: Issue,
                     current_time: datetime) -> int:
        """
        Tính điểm lần đầu, gán Level và đưa Call đang WAITING vào đúng Queue.
        Đảm bảo mỗi Call chỉ nằm ở đúng một Queue.
        """
        if call.status != Call.STATUS_WAITING:
            raise ValueError("Chỉ được đưa các Call ở trạng thái WAITING vào hàng đợi.")

        # Xóa khỏi bất kỳ queue nào nếu đã tồn tại để chống trùng
        self.remove_call(call.call_id)

        if call.queue_entered_at is None:
            call.queue_entered_at = current_time

        score = self.calculate_priority(customer, issue, call.queue_entered_at, current_time)
        level = self.get_level(score)

        call.score = score
        call.queue_level = level
        call.level_entered_at = current_time

        self.queues[level].enqueue(call)
        return level

    def remove_call(self, call_id: str) -> Optional[Call]:
        """Tìm và xóa Call khỏi 4 Queue (dùng khi ABANDONED hoặc chuyển Queue) - O(n)."""
        for level in [4, 3, 2, 1]:
            removed = self.queues[level].remove(call_id)
            if removed is not None:
                return removed
        return None

    def collect_all_waiting_calls(self) -> List[Call]:
        """Thu thập danh sách tất cả các Call đang chờ từ Level 4 xuống Level 1 - O(n)."""
        all_calls: List[Call] = []
        for level in [4, 3, 2, 1]:
            all_calls.extend(self.queues[level].to_list())
        return all_calls

    def refresh_queues(self, customers: Dict[str, Customer],
                       issues: Dict[str, Issue],
                       current_time: datetime) -> List[Tuple[str, int, int]]:
        """
        Duyệt toàn bộ Call đang WAITING, tính lại điểm theo current_time.
        Nếu Level thay đổi: xóa khỏi Queue cũ, cập nhật level_entered_at và đưa vào cuối Queue mới.
        Trả về danh sách các Call đã đổi Level: [(call_id, old_level, new_level), ...]
        """
        moved_calls: List[Tuple[str, int, int]] = []
        # Duyệt từ Level 1 lên Level 4 theo danh sách snapshot để tránh lỗi khi dịch chuyển
        for level in [1, 2, 3, 4]:
            current_level_calls = self.queues[level].to_list()
            for call in current_level_calls:
                customer = customers.get(call.customer_id)
                issue = issues.get(call.issue_id)
                if not customer or not issue:
                    continue

                new_score = self.calculate_priority(
                    customer, issue, call.queue_entered_at, current_time
                )
                new_level = self.get_level(new_score)
                old_level = call.queue_level

                call.score = new_score
                if new_level != old_level:
                    self.queues[old_level].remove(call.call_id)
                    call.queue_level = new_level
                    call.level_entered_at = current_time
                    self.queues[new_level].enqueue(call)
                    moved_calls.append((call.call_id, old_level, new_level))

        return moved_calls

    def select_next_call(self, customers: Dict[str, Customer],
                         issues: Dict[str, Issue],
                         current_time: datetime) -> Optional[Call]:
        """
        Cập nhật điểm (refresh) trước khi chọn, sau đó lấy Call đầu tiên (FIFO)
        từ Queue không rỗng có mức ưu tiên cao nhất (Level 4 -> 3 -> 2 -> 1).
        """
        self.refresh_queues(customers, issues, current_time)

        for level in [4, 3, 2, 1]:
            if not self.queues[level].is_empty():
                call = self.queues[level].dequeue()
                if call is not None:
                    # Chốt phiên chờ vào lịch sử của Issue
                    issue = issues.get(call.issue_id)
                    if issue and call.queue_entered_at:
                        issue.add_waiting_segment(call.queue_entered_at, current_time)
                    call.status = Call.STATUS_IN_SERVICE
                    call.service_start_time = current_time
                    return call
        return None