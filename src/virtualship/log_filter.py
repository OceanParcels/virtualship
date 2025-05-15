"""Class for suppressing duplicate log messages in Python logging."""

import logging


class DuplicateFilter(logging.Filter):
    """Logging filter for suppressing duplicate log messages."""

    def __init__(self):
        self.last_log = None

    def filter(self, record):
        current_log = record.getMessage()
        if current_log != self.last_log:
            self.last_log = current_log
            return True
        return False
