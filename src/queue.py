from typing import Optional, List, Any


class _QueueNode:
    """Node nội bộ của Doubly Linked List phục vụ Queue FIFO."""
    def __init__(self, item: Any):
        self.item = item
        self.prev: Optional['_QueueNode'] = None
        self.next: Optional['_QueueNode'] = None


class Queue:
    """
    Cấu trúc dữ liệu hàng đợi FIFO tự cài đặt bằng Doubly Linked List.
    - enqueue(item): O(1)
    - dequeue(): O(1)
    - peek(): O(1)
    - is_empty(): O(1)
    - size(): O(1)
    - remove(call_id): O(n) hỗ trợ rút Call khi chuyển Level hoặc ABANDONED.
    """
    def __init__(self, level_name: str = ""):
        self.level_name = level_name
        self._front: Optional[_QueueNode] = None
        self._rear: Optional[_QueueNode] = None
        self._count: int = 0

    def is_empty(self) -> bool:
        """Kiểm tra hàng đợi có rỗng không - O(1)."""
        return self._count == 0

    def size(self) -> int:
        """Trả về số lượng phần tử hiện tại trong hàng đợi - O(1)."""
        return self._count

    def enqueue(self, item: Any) -> None:
        """Thêm phần tử vào cuối hàng đợi theo chuẩn FIFO - O(1)."""
        if item is None:
            raise ValueError("Không thể enqueue phần tử None.")

        new_node = _QueueNode(item)
        if self.is_empty():
            self._front = self._rear = new_node
        else:
            assert self._rear is not None
            self._rear.next = new_node
            new_node.prev = self._rear
            self._rear = new_node
        self._count += 1

    def dequeue(self) -> Optional[Any]:
        """Lấy và xóa phần tử ở đầu hàng đợi - O(1). Trả về None nếu rỗng."""
        if self.is_empty() or self._front is None:
            return None

        removed_node = self._front
        self._front = removed_node.next
        if self._front is None:
            self._rear = None
        else:
            self._front.prev = None

        self._count -= 1
        return removed_node.item

    def peek(self) -> Optional[Any]:
        """Xem phần tử đầu hàng đợi mà không xóa - O(1)."""
        if self.is_empty() or self._front is None:
            return None
        return self._front.item

    def remove(self, call_id: str) -> Optional[Any]:
        """
        Tìm và xóa một Call khỏi hàng đợi dựa trên call_id (hoặc thuộc tính tương đương) - O(n).
        Dùng khi Call tăng Level hoặc chuyển sang trạng thái ABANDONED.
        """
        current = self._front
        while current is not None:
            current_id = getattr(current.item, "call_id", current.item)
            if current_id == call_id:
                if current.prev is not None:
                    current.prev.next = current.next
                else:
                    self._front = current.next

                if current.next is not None:
                    current.next.prev = current.prev
                else:
                    self._rear = current.prev

                self._count -= 1
                return current.item
            current = current.next
        return None

    def contains(self, call_id: str) -> bool:
        """Kiểm tra xem call_id có đang nằm trong Queue hay không - O(n)."""
        current = self._front
        while current is not None:
            current_id = getattr(current.item, "call_id", current.item)
            if current_id == call_id:
                return True
            current = current.next
        return False

    def to_list(self) -> List[Any]:
        """Trả về danh sách các phần tử theo đúng thứ tự FIFO để hiển thị - O(n)."""
        result = []
        current = self._front
        while current is not None:
            result.append(current.item)
            current = current.next
        return result