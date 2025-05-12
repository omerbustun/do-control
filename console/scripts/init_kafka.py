from confluent_kafka.admin import AdminClient, NewTopic
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_topics():
    # Wait for Kafka to be ready
    for _ in range(30):
        try:
            # Create admin client
            admin_client = AdminClient({
                'bootstrap.servers': 'kafka:29092'
            })
            
            # Define topics
            topics = [
                NewTopic('do-control.commands', num_partitions=1, replication_factor=1),
                NewTopic('do-control.status', num_partitions=1, replication_factor=1),
                NewTopic('do-control.metrics', num_partitions=1, replication_factor=1)
            ]
            
            # Create topics
            result = admin_client.create_topics(topics)
            
            # Wait for topics to be created
            for topic, future in result.items():
                try:
                    future.result()
                    logger.info(f"Topic {topic} created successfully")
                except Exception as e:
                    logger.error(f"Failed to create topic {topic}: {e}")
            
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Kafka: {e}")
            time.sleep(2)
    
    return False

if __name__ == "__main__":
    create_topics() 