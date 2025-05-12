import time
import logging

logger = logging.getLogger(__name__)

class TimeSynchronizer:
    def __init__(self):
        self.offset = 0
        self.last_sync = 0
        
    def sync(self) -> float:
        """Synchronize with host time"""
        # In Docker, we can trust the host's time
        self.offset = 0
        self.last_sync = time.time()
        return self.offset
    
    def get_synchronized_time(self) -> float:
        """Get current time"""
        # Re-sync periodically
        if time.time() - self.last_sync > 3600:  # Sync hourly
            self.sync()
        
        return time.time() + self.offset
    
    def calculate_execution_time(self, future_offset_ms: int = 5000) -> float:
        """Calculate a future execution time with margin"""
        # Ensure we have a recent sync
        if time.time() - self.last_sync > 60:  # Re-sync if older than 1 minute
            self.sync()
        
        # Calculate execution time with offset
        return self.get_synchronized_time() + (future_offset_ms / 1000.0)