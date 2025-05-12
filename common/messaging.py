import pika
import json
from typing import Dict, Any, Callable, Optional
from enum import Enum
import threading
import logging
import time

logger = logging.getLogger(__name__)

class ExchangeType(str, Enum):
    FANOUT = "fanout"
    DIRECT = "direct"
    TOPIC = "topic"
    HEADERS = "headers"

class MessageBroker:
    def __init__(self, connection_url: str, reconnect_delay: int = 5):
        self.connection_url = connection_url
        self.reconnect_delay = reconnect_delay
        self.connection = None
        self.channel = None
        self._connect()
        
    def _connect(self) -> None:
        try:
            parameters = pika.URLParameters(self.connection_url)
            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()
            logger.info("Connected to RabbitMQ")
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            self.connection = None
            self.channel = None
            
    def _ensure_connection(self) -> bool:
        if self.connection is None or self.channel is None or self.connection.is_closed:
            try:
                self._connect()
            except Exception as e:
                logger.error(f"Failed to reconnect: {e}")
                return False
        return self.connection is not None and self.channel is not None
        
    def declare_exchange(self, exchange_name: str, exchange_type: ExchangeType) -> bool:
        if not self._ensure_connection():
            return False
            
        try:
            self.channel.exchange_declare(
                exchange=exchange_name,
                exchange_type=exchange_type.value,
                durable=True
            )
            return True
        except Exception as e:
            logger.error(f"Failed to declare exchange {exchange_name}: {e}")
            return False
            
    def declare_queue(self, queue_name: str, durable: bool = True) -> bool:
        if not self._ensure_connection():
            return False
            
        try:
            self.channel.queue_declare(queue=queue_name, durable=durable)
            return True
        except Exception as e:
            logger.error(f"Failed to declare queue {queue_name}: {e}")
            return False
            
    def bind_queue(self, queue_name: str, exchange_name: str, routing_key: str = "") -> bool:
        if not self._ensure_connection():
            return False
            
        try:
            self.channel.queue_bind(
                queue=queue_name,
                exchange=exchange_name,
                routing_key=routing_key
            )
            return True
        except Exception as e:
            logger.error(f"Failed to bind queue {queue_name} to exchange {exchange_name}: {e}")
            return False
            
    def publish(self, exchange_name: str, routing_key: str, message: Dict[str, Any]) -> bool:
        if not self._ensure_connection():
            return False
            
        try:
            self.channel.basic_publish(
                exchange=exchange_name,
                routing_key=routing_key,
                body=json.dumps(message).encode(),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # make message persistent
                    content_type='application/json'
                )
            )
            return True
        except Exception as e:
            logger.error(f"Failed to publish message to {exchange_name}: {e}")
            return False
    
    def consume(self, queue_name: str, callback: Callable, auto_ack: bool = False) -> None:
        if not self._ensure_connection():
            return
            
        try:
            self.channel.basic_consume(
                queue=queue_name,
                on_message_callback=callback,
                auto_ack=auto_ack
            )
            self.channel.start_consuming()
        except Exception as e:
            logger.error(f"Error consuming from queue {queue_name}: {e}")
            
    def start_consuming_in_thread(self, queue_name: str, callback: Callable, auto_ack: bool = False) -> threading.Thread:
        def consume_wrapper():
            while True:
                try:
                    self.consume(queue_name, callback, auto_ack)
                except Exception as e:
                    logger.error(f"Error in consumer thread: {e}")
                    time.sleep(self.reconnect_delay)
                    if not self._ensure_connection():
                        logger.error("Failed to reconnect, retrying...")
                        time.sleep(self.reconnect_delay)
        
        thread = threading.Thread(target=consume_wrapper, daemon=True)
        thread.start()
        return thread
        
    def close(self) -> None:
        if self.connection and not self.connection.is_closed:
            self.connection.close()