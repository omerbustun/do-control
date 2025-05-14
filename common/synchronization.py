import time
import logging
import ntplib
from typing import Optional, Tuple
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class TimeSynchronizer:
    def __init__(self, ntp_servers: list = None):
        self.ntp_client = ntplib.NTPClient()
        self.ntp_servers = ntp_servers or [
            'pool.ntp.org',
            'time.google.com',
            'time.windows.com',
            'time.apple.com'
        ]
        self.offset = 0
        self.last_sync = 0
        self.drift_rate = 0  # Drift rate in seconds per second
        self.last_drift_check = 0
        self.sync_status = {
            'last_sync': None,
            'offset': 0,
            'drift_rate': 0,
            'sync_error': None,
            'using_ntp': False
        }
        
    def sync(self) -> float:
        """Synchronize with NTP servers"""
        try:
            # Try each NTP server until one responds
            for server in self.ntp_servers:
                try:
                    response = self.ntp_client.request(server, version=3, timeout=2.0)
                    if response:
                        # Calculate offset in seconds
                        self.offset = response.offset
                        self.last_sync = time.time()
                        
                        # Update sync status
                        self.sync_status.update({
                            'last_sync': datetime.now(timezone.utc),
                            'offset': self.offset,
                            'drift_rate': self.drift_rate,
                            'sync_error': None,
                            'using_ntp': True
                        })
                        
                        logger.info(f"Time synchronized with {server}, offset: {self.offset:.6f}s")
                        return self.offset
                except Exception as e:
                    logger.warning(f"Failed to sync with {server}: {e}")
                    continue
            
            # If all servers fail, log error and use local time
            error_msg = "Failed to sync with any NTP server, using local time"
            logger.error(error_msg)
            self.sync_status.update({
                'sync_error': error_msg,
                'using_ntp': False,
                'last_sync': datetime.now(timezone.utc)
            })
            return 0.0  # Use local time as fallback
            
        except Exception as e:
            error_msg = f"Time synchronization error: {e}"
            logger.error(error_msg)
            self.sync_status.update({
                'sync_error': error_msg,
                'using_ntp': False,
                'last_sync': datetime.now(timezone.utc)
            })
            return 0.0  # Use local time as fallback
    
    def _check_drift(self) -> None:
        """Check for time drift and update drift rate"""
        current_time = time.time()
        
        # Only check drift every hour
        if current_time - self.last_drift_check < 3600:
            return
            
        try:
            # Get current offset
            old_offset = self.offset
            new_offset = self.sync()
            
            # Calculate drift rate (seconds per second)
            time_elapsed = current_time - self.last_drift_check
            if time_elapsed > 0:
                self.drift_rate = (new_offset - old_offset) / time_elapsed
                self.sync_status['drift_rate'] = self.drift_rate
                
                if abs(self.drift_rate) > 0.001:  # More than 1ms drift per second
                    logger.warning(f"Significant time drift detected: {self.drift_rate:.6f}s/s")
            
            self.last_drift_check = current_time
            
        except Exception as e:
            logger.error(f"Error checking time drift: {e}")
    
    def get_synchronized_time(self) -> float:
        """Get current synchronized time in UTC"""
        current_time = time.time()
        
        # Re-sync periodically
        if current_time - self.last_sync > 3600:  # Sync hourly
            self.sync()
        else:
            # Check for drift
            self._check_drift()
            
            # Apply drift compensation
            time_since_last_sync = current_time - self.last_sync
            drift_compensation = self.drift_rate * time_since_last_sync
            
        return current_time + self.offset + drift_compensation
    
    def get_sync_status(self) -> dict:
        """Get current synchronization status"""
        # Create a copy of the status dict with serializable values
        status_copy = self.sync_status.copy()
        
        # Convert datetime to timestamp if present
        if status_copy.get('last_sync') and isinstance(status_copy['last_sync'], datetime):
            status_copy['last_sync'] = status_copy['last_sync'].timestamp()
            
        return status_copy
    
    def calculate_execution_time(self, future_offset_ms: int = 5000) -> float:
        """Calculate a future execution time with margin"""
        # Ensure we have a recent sync
        if time.time() - self.last_sync > 60:  # Re-sync if older than 1 minute
            self.sync()
        
        # Calculate execution time with offset
        return self.get_synchronized_time() + (future_offset_ms / 1000.0)