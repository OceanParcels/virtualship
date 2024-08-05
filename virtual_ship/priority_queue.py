"""PriorityQueue class."""

import heapq
from typing import Generic, TypeVar

T = TypeVar("T")


class PriorityQueue(Generic[T]):
    """A priority queue: a queue that pops the smallest value first."""

    _queue: list[T]

    def __init__(self) -> None:
        """Initialize this object."""
        self._queue: list[T] = []

    def push(self, item: T) -> None:
        """
        Add an item to the queue.

        :param item: The item to add.
        """
        heapq.heappush(self._queue, item)

    def pop(self) -> T:
        """
        Get and remove the smallest item from the queue.

        :returns: The removed item.
        """
        return heapq.heappop(self._queue)

    def peek(self) -> T:
        """
        Look at the smallest item in the queue.

        :returns: The smallest item.
        """
        return self._queue[0]

    def is_empty(self) -> bool:
        """
        Check if the queue is empty.

        :returns: Whether the queue is empty.
        """
        return len(self._queue) == 0

    def __len__(self) -> int:
        """Get the number of items in the queue.

        :returns: The number of items in the queue.
        """
        return len(self._queue)
