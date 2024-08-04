import heapq
from typing import TypeVar, Generic

T = TypeVar("T")


class SortedQueue(Generic[T]):
    _queue: list[T]

    def __init__(self) -> None:
        self._queue: list[T] = []

    def push(self, item: T) -> None:
        heapq.heappush(self._queue, item)

    def pop(self) -> T:
        return heapq.heappop(self._queue)

    def peek(self) -> T:
        return self._queue[0]

    def is_empty(self) -> bool:
        return len(self._queue) == 0

    def __len__(self) -> int:
        return len(self._queue)
