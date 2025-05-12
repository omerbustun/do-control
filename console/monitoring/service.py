from typing import List, Dict, Any, Optional
import logging
import json
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from console.messaging.service import MessagingService

logger = logging.getLogger(__name__)

class MonitoringService:
    def __init__(self, db: Session, influxdb_client=None, messaging_service: Optional[MessagingService] = None):
        self.db = db
        self.influxdb = influxdb_client
        self.messaging_service = messaging_service or MessagingService()
        self.metrics_buffer = {}
        self._setup_metrics_handler()
    
    def _setup_metrics_handler(self):
        """Set up handler for incoming metrics"""
        self.messaging_service.register_metrics_handler(self._handle_metrics)
    
    def _handle_metrics(self, ch, method, properties, body):
        """Process incoming metrics messages"""
        try:
            metric_data = json.loads(body)
            agent_id = metric_data.get('agent_id')
            timestamp = metric_data.get('timestamp')
            metrics = metric_data.get('metrics', {})
            
            if not agent_id or not timestamp or not metrics:
                logger.warning(f"Received invalid metrics message: {metric_data}")
                return
            
            # Store in InfluxDB if available
            if self.influxdb:
                self._store_in_influxdb(agent_id, timestamp, metrics)
            
            # Add to in-memory buffer
            if agent_id not in self.metrics_buffer:
                self.metrics_buffer[agent_id] = []
            
            self.metrics_buffer[agent_id].append({
                'timestamp': timestamp,
                'metrics': metrics
            })
            
            # Keep only recent metrics in memory
            self._prune_metrics_buffer()
            
        except Exception as e:
            logger.error(f"Error handling metrics: {e}")
    
    def _store_in_influxdb(self, agent_id, timestamp, metrics):
        """Store metrics in InfluxDB"""
        if not self.influxdb:
            return
        
        # Convert timestamp to datetime
        dt = datetime.fromtimestamp(timestamp)
        
        # Flatten and store metrics
        for category, values in metrics.items():
            if isinstance(values, dict):
                for key, value in values.items():
                    self._write_influxdb_point(agent_id, category, key, value, dt)
            else:
                self._write_influxdb_point(agent_id, category, category, values, dt)
    
    def _write_influxdb_point(self, agent_id, category, field_name, value, timestamp):
        """Write a single point to InfluxDB"""
        try:
            point = {
                "measurement": "do_control_metrics",
                "tags": {
                    "agent_id": agent_id,
                    "category": category
                },
                "time": timestamp.isoformat(),
                "fields": {
                    field_name: float(value) if isinstance(value, (int, float)) else str(value)
                }
            }
            self.influxdb.write_points([point])
        except Exception as e:
            logger.error(f"Error writing to InfluxDB: {e}")
    
    def _prune_metrics_buffer(self):
        """Remove old metrics from in-memory buffer"""
        now = datetime.now()
        cutoff = now - timedelta(minutes=10)  # Keep 10 minutes of data
        
        for agent_id in list(self.metrics_buffer.keys()):
            self.metrics_buffer[agent_id] = [
                m for m in self.metrics_buffer[agent_id]
                if datetime.fromtimestamp(m['timestamp']) > cutoff
            ]
    
    def get_agent_metrics(self, agent_id, lookback_minutes=5):
        """Get recent metrics for an agent"""
        now = datetime.now()
        cutoff = now - timedelta(minutes=lookback_minutes)
        
        if agent_id not in self.metrics_buffer:
            return []
        
        return [
            m for m in self.metrics_buffer[agent_id]
            if datetime.fromtimestamp(m['timestamp']) > cutoff
        ]
    
    def get_execution_metrics(self, execution_id):
        """Get metrics for a specific test execution"""
        # Implementation depends on how we tag test-specific metrics
        # This is a placeholder
        return []