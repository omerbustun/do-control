import pika
import time
import logging
from enum import Enum

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TopicType(str, Enum):
    COMMANDS = "do-control.commands"
    STATUS = "do-control.status"
    METRICS = "do-control.metrics"

def create_exchanges():
    """Create RabbitMQ exchanges for all topic types"""
    # Wait for RabbitMQ to be ready
    for attempt in range(30):
        try:
            # Connect to RabbitMQ
            connection = pika.BlockingConnection(
                pika.URLParameters('amqp://guest:guest@rabbitmq:5672/')
            )
            channel = connection.channel()
            
            # Declare exchanges for each topic type
            for topic in TopicType:
                channel.exchange_declare(
                    exchange=topic.value,
                    exchange_type='topic',
                    durable=True
                )
                logger.info(f"Exchange {topic.value} created successfully")
            
            # Close connection
            connection.close()
            logger.info("All exchanges created successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ (attempt {attempt+1}/30): {e}")
            time.sleep(2)
    
    logger.error("Failed to initialize RabbitMQ after multiple attempts")
    return False

if __name__ == "__main__":
    create_exchanges() 