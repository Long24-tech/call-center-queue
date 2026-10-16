import os
import sys
# Tự động trỏ đường dẫn vào thư mục src/
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

import unittest
from models import Customer, Issue, Call, CallEvent
from queue import Queue
from priority_manager import PriorityManager
from validator import Validator
from menu import CLIMenu

import unittest
from datetime import datetime, timedelta

from models import Customer, Issue, Call, CallEvent
from queue import Queue
from priority_manager import PriorityManager
from validator import Validator
from menu import CLIMenu

#----------------------------------------------------------------------------------

class TestKyQueue(unittest.TestCase):
    """[Nguyễn Cao Kỳ] Unit test cho Queue FIFO độc lập."""

    def test_empty_queue(self):
        q = Queue("Level 1")
        self.assertTrue(q.is_empty())
        self.assertEqual(q.size(), 0)
        self.assertIsNone(q.peek())
        self.assertIsNone(q.dequeue())

    def test_fifo_order_and_size(self):
        q = Queue("Level 1")
        t0 = datetime(2026, 10, 15, 9, 0)
        c1 = Call("CALL001", "C001", "I001", t0)
        c2 = Call("CALL002", "C002", "I002", t0 + timedelta(minutes=1))
        c3 = Call("CALL003", "C003", "I003", t0 + timedelta(minutes=2))

        q.enqueue(c1)
        q.enqueue(c2)
        q.enqueue(c3)

        self.assertEqual(q.size(), 3)
        self.assertEqual(q.peek().call_id, "CALL001")
        self.assertEqual(q.dequeue().call_id, "CALL001")
        self.assertEqual(q.dequeue().call_id, "CALL002")
        self.assertEqual(q.dequeue().call_id, "CALL003")
        self.assertTrue(q.is_empty())

    def test_remove_middle_and_boundaries(self):
        q = Queue("Level 2")
        t0 = datetime(2026, 10, 15, 9, 0)
        c1 = Call("CALL001", "C001", "I001", t0)
        c2 = Call("CALL002", "C002", "I002", t0)
        c3 = Call("CALL003", "C003", "I003", t0)

        q.enqueue(c1)
        q.enqueue(c2)
        q.enqueue(c3)

        # Xóa phần tử ở giữa (hỗ trợ chuyển Level hoặc ABANDONED)
        removed = q.remove("CALL002")
        self.assertIsNotNone(removed)
        self.assertEqual(removed.call_id, "CALL002")
        self.assertEqual(q.size(), 2)
        self.assertEqual([c.call_id for c in q.to_list()], ["CALL001", "CALL003"])


class TestAnModels(unittest.TestCase):
    """[Trần Bảo An] Unit test cho Customer, Issue, Call, chống gọi trùng và thời gian chờ."""

    def test_duplicate_window_60_seconds(self):
        t0 = datetime(2026, 10, 15, 9, 0, 0)
        issue = Issue("I001", "C001", "Internet", t0)

        # Lần gọi đầu tiên hợp lệ (không phải callback)
        is_cb_1 = issue.register_valid_call(t0)
        self.assertFalse(is_cb_1)
        self.assertEqual(issue.valid_callback_count, 0)

        # Gọi lại sau 45 giây -> nằm trong cửa sổ chống trùng 60s (T06)
        self.assertTrue(issue.is_duplicate_contact(t0 + timedelta(seconds=45)))

        # Gọi lại sau 61 giây -> ngoài cửa sổ chống trùng, tính là callback hợp lệ thứ 1 (T03)
        t1 = t0 + timedelta(seconds=61)
        self.assertFalse(issue.is_duplicate_contact(t1))
        is_cb_2 = issue.register_valid_call(t1)
        self.assertTrue(is_cb_2)
        self.assertEqual(issue.valid_callback_count, 1)

    def test_min_eligible_waiting_segment_2_minutes(self):
        t0 = datetime(2026, 10, 15, 9, 0, 0)
        issue = Issue("I001", "C001", "Billing", t0)

        # Phiên chờ 90 giây (< 2 phút) -> không được tính (T05 / Mục 5.5)
        added_min = issue.add_waiting_segment(t0, t0 + timedelta(seconds=90))
        self.assertEqual(added_min, 0)
        self.assertEqual(issue.get_total_eligible_waiting_minutes(), 0)

        # Phiên chờ 4 phút + phiên chờ 6 phút -> tổng 10 phút hợp lệ (T11)
        issue.add_waiting_segment(t0, t0 + timedelta(minutes=4))
        issue.add_waiting_segment(t0 + timedelta(minutes=10), t0 + timedelta(minutes=16))
        self.assertEqual(issue.get_total_eligible_waiting_minutes(), 10)

    def test_resolved_issue_blocks_callbacks(self):
        t0 = datetime(2026, 10, 15, 9, 0, 0)
        issue = Issue("I001", "C001", "Account", t0)
        issue.register_valid_call(t0)
        issue.resolve(t0 + timedelta(minutes=15))

        self.assertEqual(issue.status, Issue.STATUS_RESOLVED)
        with self.assertRaises(ValueError):
            issue.register_valid_call(t0 + timedelta(minutes=30))


class TestLongPriorityManager(unittest.TestCase):
    """[Hồ Văn Long] Unit test cho công thức điểm, 4 Level, chuyển Queue và chọn Next Call."""

    def setUp(self):
        self.pm = PriorityManager()
        self.t0 = datetime(2026, 10, 15, 9, 0, 0)
        self.cust_reg = Customer("C001", "Nguyen Van A", "0901234567", is_vip=False)
        self.cust_vip = Customer("C002", "Tran Thi VIP", "0909999999", is_vip=True)

    def test_scoring_matrix_cases_T01_to_T13(self):
        # T01: Khách thường gọi lần đầu -> Điểm 1, Level 1
        issue1 = Issue("I001", "C001", "Wifi", self.t0)
        issue1.register_valid_call(self.t0)
        score_t01 = self.pm.calculate_priority(self.cust_reg, issue1, self.t0, self.t0)
        self.assertEqual(score_t01, 1)
        self.assertEqual(self.pm.get_level(score_t01), 1)

        # T02: VIP gọi lần đầu -> Điểm 7, Level 3
        issue_vip = Issue("I002", "C002", "Fiber", self.t0)
        issue_vip.register_valid_call(self.t0)
        score_t02 = self.pm.calculate_priority(self.cust_vip, issue_vip, self.t0, self.t0)
        self.assertEqual(score_t02, 7)
        self.assertEqual(self.pm.get_level(score_t02), 3)

        # T12: Khách thường có 2 callback (+4) và chờ 25 phút (+5) -> 1 + 4 + 5 = 10 điểm, Level 4
        issue1.register_valid_call(self.t0 + timedelta(minutes=2))   # callback 1
        issue1.register_valid_call(self.t0 + timedelta(minutes=5))   # callback 2
        issue1.register_valid_call(self.t0 + timedelta(minutes=8))   # callback 3 (vẫn trần +4)
        t_after_25m = self.t0 + timedelta(minutes=25)
        score_t12 = self.pm.calculate_priority(self.cust_reg, issue1, self.t0, t_after_25m)
        self.assertEqual(score_t12, 10)
        self.assertEqual(self.pm.get_level(score_t12), 4)

        # T13: VIP chờ 15 phút (+3) -> 7 + 3 = 10 điểm, Level 4
        score_t13 = self.pm.calculate_priority(
            self.cust_vip, issue_vip, self.t0, self.t0 + timedelta(minutes=15)
        )
        self.assertEqual(score_t13, 10)
        self.assertEqual(self.pm.get_level(score_t13), 4)

    def test_level_promotion_and_select_next_call_T14_T15(self):
        customers = {"C001": self.cust_reg, "C002": self.cust_vip}
        issue_reg = Issue("I001", "C001", "Support", self.t0)
        issue_reg.register_valid_call(self.t0)
        issue_reg.register_valid_call(self.t0 + timedelta(minutes=2))  # 1 callback -> Base 1 + 2 = 3 (L2)

        call_reg = Call("CALL001", "C001", "I001", self.t0)
        self.pm.enqueue_call(call_reg, self.cust_reg, issue_reg, self.t0)
        self.assertEqual(call_reg.queue_level, 2)
        self.assertEqual(self.pm.queues[2].size(), 1)

        # Sau 15 phút chờ (+3 điểm): Điểm tăng từ 3 lên 6 -> chuyển từ Level 2 sang Level 3 (T15)
        t_15m = self.t0 + timedelta(minutes=15)
        issues = {"I001": issue_reg}
        moved = self.pm.refresh_queues(customers, issues, t_15m)

        self.assertEqual(moved, [("CALL001", 2, 3)])
        self.assertEqual(self.pm.queues[2].size(), 0)
        self.assertEqual(self.pm.queues[3].size(), 1)
        self.assertEqual(call_reg.score, 6)

        # Chọn cuộc gọi tiếp theo
        next_call = self.pm.select_next_call(customers, issues, t_15m)
        self.assertIsNotNone(next_call)
        self.assertEqual(next_call.call_id, "CALL001")
        self.assertEqual(next_call.status, Call.STATUS_IN_SERVICE)
        self.assertEqual(self.pm.queues[3].size(), 0)


class TestKhangCLIValidator(unittest.TestCase):
    """[Phan Duy Khang] Unit test cho Validator và CLI Menu."""

    def test_valid_and_invalid_inputs(self):
        self.assertEqual(Validator.validate_id("c001", prefix="C"), "C001")
        self.assertEqual(Validator.validate_phone("0901234567"), "0901234567")
        self.assertTrue(Validator.validate_vip_flag("VIP"))
        self.assertFalse(Validator.validate_vip_flag("no"))

        with self.assertRaises(ValueError):
            Validator.validate_id("", prefix="C")
        with self.assertRaises(ValueError):
            Validator.validate_phone("12345")
        with self.assertRaises(ValueError):
            CLIMenu.parse_user_option("12")

    def test_forbid_manual_priority_score(self):
        with self.assertRaises(PermissionError):
            Validator.forbid_manual_priority_input({"customer_id": "C001", "score": 10})


if __name__ == "__main__":
    unittest.main()