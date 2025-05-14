import json
import pika
from typing import Dict, Any, Callable, Optional
from enum import Enum
import threading
import logging
import time
from datetime import datetime

logger = logging.getLogger(__name__)

class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

class TopicType(str, Enum):
    COMMANDS = "do-control.commands"
    STATUS = "do-control.status"
    METRICS = "do-control.metrics"

class MessageBroker:
    def __init__(self, rabbitmq_url: str):
        self.rabbitmq_url = rabbitmq_url
        self.connection = None
        self.channel = None
        self.connect()
        self.consumer_threads = {}
        
    def connect(self):
        """Connect to RabbitMQ and set up channel"""
        try:
            self.connection = pika.BlockingConnection(
                pika.URLParameters(self.rabbitmq_url)
            )
            self.channel = self.connection.channel()
            
            # Declare exchanges for each topic type
            for topic in TopicType:
                self.channel.exchange_declare(
                    exchange=topic.value,
                    exchange_type='topic',
                    durable=True
                )
                
            logger.info("Connected to RabbitMQ")
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            raise
        
    def _ensure_connection(self):
        """Ensure connection is active, reconnect if needed"""
        if not self.connection or self.connection.is_closed:
            logger.info("RabbitMQ connection is closed, reconnecting...")
            self.connect()
        elif not self.channel or self.channel.is_closed:
            logger.info("RabbitMQ channel is closed, recreating...")
            self.channel = self.connection.channel()
            
    def publish(self, topic: str, key: str, message: Dict[str, Any]) -> bool:
        """Publish a message to a topic"""
        topic_name = topic.value if hasattr(topic, 'value') else topic
        
        try:
            self._ensure_connection()
            
            self.channel.basic_publish(
                exchange=topic_name,
                routing_key=key,
                body=json.dumps(message, cls=DateTimeEncoder).encode(),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # persistent delivery
                    content_type='application/json'
                )
            )
            logger.debug(f"Published message to {topic_name} with routing key {key}")
            return True
        except Exception as e:
            logger.error(f"Failed to publish message to {topic_name}: {e}")
            return False
            
    def consume(self, topic: str, group_id: str, callback: Callable, auto_commit: bool = False) -> None:
        """Consume messages from a topic"""
        topic_name = topic.value if hasattr(topic, 'value') else topic
        
        try:
            self._ensure_connection()
            
            # Declare a queue for this consumer group
            queue_name = f"{topic_name}.{group_id}"
            self.channel.queue_declare(queue=queue_name, durable=True)
            
            # Bind the queue to the exchange with routing key '#' to receive all messages
            self.channel.queue_bind(
                exchange=topic_name,
                queue=queue_name,
                routing_key='#'
            )
            
            def message_handler(ch, method, properties, body):
                try:
                    value = json.loads(body.decode())
                    callback(method.routing_key, value)
                    
                    if auto_commit or not method.delivery_tag:
                        ch.basic_ack(delivery_tag=method.delivery_tag)
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    if not auto_commit and method.delivery_tag:
                        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
            
            self.channel.basic_consume(
                queue=queue_name,
                on_message_callback=message_handler,
                auto_ack=False
            )
            
            logger.info(f"Started consuming from {topic_name}")
            self.channel.start_consuming()
            
        except Exception as e:
            logger.error(f"Error consuming from topic {topic_name}: {e}")
            raise
            
    def start_consuming_in_thread(self, topic: str, group_id: str, callback: Callable, auto_commit: bool = False) -> threading.Thread:
        """Start consuming messages in a background thread"""
        def consume_wrapper():
            while True:
                try:
                    # Create a new connection for each consumer thread
                    connection = pika.BlockingConnection(
                        pika.URLParameters(self.rabbitmq_url)
                    )
                    channel = connection.channel()
                    
                    topic_name = topic.value if hasattr(topic, 'value') else topic
                    
                    # Declare exchange
                    channel.exchange_declare(
                        exchange=topic_name,
                        exchange_type='topic',
                        durable=True
                    )
                    
                    # Declare a queue for this consumer group
                    queue_name = f"{topic_name}.{group_id}"
                    channel.queue_declare(queue=queue_name, durable=True)
                    
                    # Bind the queue to the exchange with routing key '#' to receive all messages
                    channel.queue_bind(
                        exchange=topic_name,
                        queue=queue_name,
                        routing_key='#'
                    )
                    
                    def message_handler(ch, method, properties, body):
                        try:
                            value = json.loads(body.decode())
                            callback(method.routing_key, value)
                            
                            if auto_commit or not method.delivery_tag:
                                ch.basic_ack(delivery_tag=method.delivery_tag)
                        except Exception as e:
                            logger.error(f"Error processing message: {e}")
                            if not auto_commit and method.delivery_tag:
                                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
                    
                    channel.basic_consume(
                        queue=queue_name,
                        on_message_callback=message_handler,
                        auto_ack=False
                    )
                    
                    logger.info(f"Started consuming from {topic_name} in thread")
                    channel.start_consuming()
                    
                except Exception as e:
                    logger.error(f"Error in consumer thread: {e}")
                    time.sleep(5)  # Wait before retrying
                    
        thread_id = f"{topic}.{group_id}"
        if thread_id in self.consumer_threads and self.consumer_threads[thread_id].is_alive():
            logger.warning(f"Consumer thread for {thread_id} already running")
            return self.consumer_threads[thread_id]
            
        thread = threading.Thread(target=consume_wrapper, daemon=True)
        thread.start()
        self.consumer_threads[thread_id] = thread
        return thread
        
    def close(self) -> None:
        """Close all connections"""
        if self.connection and self.connection.is_open:
            try:
                self.connection.close()
                logger.info("Closed RabbitMQ connection")
            except Exception as e:
                logger.error(f"Error closing connection: {e}")