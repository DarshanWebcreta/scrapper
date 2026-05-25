import logging
import sys
import asyncio
from collections import deque
from typing import List, Callable

# Keep recent 200 logs in memory for fast loading on page refresh
LOG_HISTORY = deque(maxlen=200)

# Listeners for real-time log streaming
_log_listeners: List[Callable[[str], None]] = []

class SSELogHandler(logging.Handler):
    """
    Custom logging handler that intercepts log messages,
    saves them to HISTORY, and notifies active SSE listeners.
    """
    def emit(self, record):
        try:
            msg = self.format(record)
            LOG_HISTORY.append(msg)
            # Notify listeners
            for listener in _log_listeners:
                try:
                    # Run listener callback
                    listener(msg)
                except Exception:
                    pass  # Ignore listener issues to prevent log crashes
        except Exception:
            self.handleError(record)

def register_log_listener(callback: Callable[[str], None]):
    """Register a callback for new log messages."""
    if callback not in _log_listeners:
        _log_listeners.append(callback)

def unregister_log_listener(callback: Callable[[str], None]):
    """Unregister a callback."""
    if callback in _log_listeners:
        _log_listeners.remove(callback)

def get_recent_logs() -> List[str]:
    """Retrieve the in-memory log history."""
    return list(LOG_HISTORY)

def setup_logging():
    """Configure standard logging with our custom SSE broadcast handler."""
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Avoid duplicate handlers if setup multiple times
    if logger.handlers:
        logger.handlers.clear()
        
    formatter = logging.Formatter(
        '[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # SSE Broadcast Handler
    sse_handler = SSELogHandler()
    sse_handler.setFormatter(formatter)
    logger.addHandler(sse_handler)

# Setup initial logging
setup_logging()
logger = logging.getLogger("App")
