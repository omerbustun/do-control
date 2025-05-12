import json
from typing import Dict, Any, Callable, Optional
from enum import Enum
import threading
import logging
import time
from confluent_kafka import Producer, Consumer, KafkaError, KafkaException

logger = logging.getLogger(__name__)

class TopicType(str, Enum):
    COMMANDS = "do-control.commands"
    STATUS = "do-control.status"
    METRICS = "do-control.metrics"

class MessageBroker:
    def __init__(self, bootstrap_servers: str, security_protocol: str = "PLAINTEXT",
                 sasl_mechanism: str = "PLAIN", sasl_username: str = "", sasl_password: str = ""):
        self.bootstrap_servers = bootstrap_servers
        self.security_protocol = security_protocol
        self.sasl_mechanism = sasl_mechanism
        self.sasl_username = sasl_username
        self.sasl_password = sasl_password
        
        # Initialize producer
        self.producer = self._create_producer()
        
        # Initialize consumer (will be created per topic)
        self.consumers = {}
        
    def _create_producer(self) -> Producer:
        """Create a Kafka producer"""
        config = {
            'bootstrap.servers': self.bootstrap_servers,
            'security.protocol': self.security_protocol,
        }
        
        if self.security_protocol != "PLAINTEXT":
            config.update({
                'sasl.mechanism': self.sasl_mechanism,
                'sasl.username': self.sasl_username,
                'sasl.password': self.sasl_password
            })
            
        return Producer(config)
        
    def _create_consumer(self, group_id: str) -> Consumer:
        """Create a Kafka consumer"""
        config = {
            'bootstrap.servers': self.bootstrap_servers,
            'group.id': group_id,
            'auto.offset.reset': 'earliest',
            'enable.auto.commit': False,
            'security.protocol': self.security_protocol,
        }
        
        if self.security_protocol != "PLAINTEXT":
            config.update({
                'sasl.mechanism': self.sasl_mechanism,
                'sasl.username': self.sasl_username,
                'sasl.password': self.sasl_password
            })
            
        return Consumer(config)
        
    def publish(self, topic: str, key: str, message: Dict[str, Any]) -> bool:
        """Publish a message to a topic"""
        try:
            self.producer.produce(
                topic=topic,
                key=key,
                value=json.dumps(message).encode(),
                callback=self._delivery_report
            )
            self.producer.poll(0)  # Trigger delivery report callbacks
            return True
        except Exception as e:
            logger.error(f"Failed to publish message to {topic}: {e}")
            return False
            
    def _delivery_report(self, err, msg):
        """Delivery report callback"""
        if err is not None:
            logger.error(f"Message delivery failed: {err}")
        else:
            logger.debug(f"Message delivered to {msg.topic()} [{msg.partition()}]")
            
    def consume(self, topic: str, group_id: str, callback: Callable, auto_commit: bool = False) -> None:
        """Consume messages from a topic"""
        topic_name = topic.value if hasattr(topic, 'value') else topic

        if topic_name not in self.consumers:
            self.consumers[topic_name] = self._create_consumer(group_id)
            self.consumers[topic_name].subscribe([topic_name])
            
        try:
            while True:
                msg = self.consumers[topic].poll(1.0)
                if msg is None:
                    continue
                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        continue
                    else:
                        logger.error(f"Consumer error: {msg.error()}")
                        break
                        
                try:
                    value = json.loads(msg.value().decode())
                    callback(msg.key().decode(), value)
                    
                    if auto_commit:
                        self.consumers[topic].commit(msg)
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    
        except Exception as e:
            logger.error(f"Error consuming from topic {topic}: {e}")
            
    def start_consuming_in_thread(self, topic: str, group_id: str, callback: Callable, auto_commit: bool = False) -> threading.Thread:
        """Start consuming messages in a background thread"""
        def consume_wrapper():
            while True:
                try:
                    self.consume(topic, group_id, callback, auto_commit)
                except Exception as e:
                    logger.error(f"Error in consumer thread: {e}")
                    time.sleep(5)  # Wait before retrying
                    
        thread = threading.Thread(target=consume_wrapper, daemon=True)
        thread.start()
        return thread
        
    def close(self) -> None:
        """Close all connections"""
        if self.producer:
            self.producer.flush()
            
        for consumer in self.consumers.values():
            consumer.close()