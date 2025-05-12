import time
import requests
import statistics
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class TimeSynchronizer:
    def __init__(self, ntp_servers=None):
        self.ntp_servers = ntp_servers or [
            "pool.ntp.org",
            "time.google.com",
            "time.cloudflare.com"
        ]
        self.offset = 0
        self.drift_rate = 0
        self.last_sync = 0
        
    def sync(self) -> float:
        """Synchronize with NTP servers and return offset"""
        offsets = []
        
        for server in self.ntp_servers:
            try:
                offset = self._get_time_offset(server)
                offsets.append(offset)
            except Exception as e:
                logger.warning(f"Error getting time from {server}: {e}")
        
        if not offsets:
            logger.error("Failed to synchronize with any NTP server")
            return self.offset
        
        # Calculate median offset to filter outliers
        self.offset = statistics.median(offsets)
        self.last_sync = time.time()
        return self.offset
    
    def _get_time_offset(self, server: str) -> float:
        """Get time offset from an NTP server using HTTP"""
        t0 = time.time()
        response = requests.get(f"https://{server}", timeout=5)
        t3 = time.time()
        
        # Extract server time from response header
        server_time_str = response.headers.get("Date")
        if not server_time_str:
            raise ValueError(f"No Date header in response from {server}")
        
        # Parse server time (RFC 7231 format)
        server_time = time.mktime(time.strptime(
            server_time_str, "%a, %d %b %Y %H:%M:%S GMT"
        ))
        
        # Calculate round-trip time and offset
        rtt = t3 - t0
        t1 = server_time
        t2 = server_time  # HTTP doesn't provide separate t1/t2
        
        # Simplified offset calculation
        offset = ((t1 - t0) + (t2 - t3)) / 2
        
        logger.debug(f"Time offset from {server}: {offset:.6f}s (RTT: {rtt:.6f}s)")
        return offset
    
    def get_synchronized_time(self) -> float:
        """Get current time adjusted by offset"""
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