from typing import Dict, Any, List, Optional
from common.messaging import MessageBroker, TopicType
from console.config import settings
import logging

logger = logging.getLogger(__name__)

class MessagingService:
    def __init__(self):
        self.broker = MessageBroker(
            rabbitmq_url=settings.RABBITMQ_URL
        )
        
    def send_command(self, command: Dict[str, Any]) -> bool:
        """
        Send a command to all agents
        """
        return self.broker.publish(
            topic=TopicType.COMMANDS,
            key="broadcast",
            message=command
        )
        
    def send_direct_command(self, agent_id: str, command: Dict[str, Any]) -> bool:
        """
        Send a command to a specific agent
        """
        return self.broker.publish(
            topic=TopicType.COMMANDS,
            key=agent_id,
            message=command
        )
        
    def register_status_handler(self, callback) -> None:
        """
        Register a handler for agent status updates
        """
        self.broker.start_consuming_in_thread(
            topic=TopicType.STATUS,
            group_id="console-status",
            callback=callback,
            auto_commit=True
        )
        
    def register_metrics_handler(self, callback) -> None:
        """
        Register a handler for metrics collection
        """
        self.broker.start_consuming_in_thread(
            topic=TopicType.METRICS,
            group_id="console-metrics",
            callback=callback,
            auto_commit=True
        )