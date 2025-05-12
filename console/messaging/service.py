from typing import Dict, Any, List, Optional
from common.messaging import MessageBroker, ExchangeType
from console.config import settings
import logging

logger = logging.getLogger(__name__)

class MessagingService:
    def __init__(self, connection_url: Optional[str] = None):
        self.connection_url = connection_url or settings.RABBITMQ_URL
        self.broker = MessageBroker(self.connection_url)
        self._setup_exchanges()
        
    def _setup_exchanges(self) -> None:
        """
        Initialize required exchanges
        """
        # Commands exchange for distributing commands to agents
        self.broker.declare_exchange("do-control.commands", ExchangeType.FANOUT)
        
        # Status exchange for agent status updates
        self.broker.declare_exchange("do-control.status", ExchangeType.TOPIC)
        
        # Metrics exchange for collecting metrics
        self.broker.declare_exchange("do-control.metrics", ExchangeType.TOPIC)
        
    def setup_agent_queues(self, agent_id: str) -> None:
        """
        Set up queues for a specific agent
        """
        # Commands queue (receives from commands exchange)
        self.broker.declare_queue(f"do-control.agent.{agent_id}.commands")
        self.broker.bind_queue(
            queue_name=f"do-control.agent.{agent_id}.commands",
            exchange_name="do-control.commands",
            routing_key=""
        )
        
    def send_command(self, command: Dict[str, Any]) -> bool:
        """
        Send a command to all agents
        """
        return self.broker.publish(
            exchange_name="do-control.commands",
            routing_key="",
            message=command
        )
        
    def send_direct_command(self, agent_id: str, command: Dict[str, Any]) -> bool:
        """
        Send a command to a specific agent
        """
        return self.broker.publish(
            exchange_name="",  # Default exchange
            routing_key=f"do-control.agent.{agent_id}.commands",
            message=command
        )
        
    def register_status_handler(self, callback) -> None:
        """
        Register a handler for agent status updates
        """
        # Create and bind queue for status updates
        self.broker.declare_queue("do-control.console.status")
        self.broker.bind_queue(
            queue_name="do-control.console.status",
            exchange_name="do-control.status",
            routing_key="agent.*.#"  # Listen to all agent status updates
        )
        
        # Start consuming in a background thread
        self.broker.start_consuming_in_thread(
            queue_name="do-control.console.status",
            callback=callback,
            auto_ack=True
        )
        
    def register_metrics_handler(self, callback) -> None:
        """
        Register a handler for metrics collection
        """
        # Create and bind queue for metrics
        self.broker.declare_queue("do-control.console.metrics")
        self.broker.bind_queue(
            queue_name="do-control.console.metrics",
            exchange_name="do-control.metrics",
            routing_key="#"  # Listen to all metrics
        )
        
        # Start consuming in a background thread
        self.broker.start_consuming_in_thread(
            queue_name="do-control.console.metrics",
            callback=callback,
            auto_ack=True
        )