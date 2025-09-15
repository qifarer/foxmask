from foxmask.core.kafka import kafka_manager
from foxmask.core.logger import logger
from .schemas import MessageType
async def setup_kafka_topics():
    """设置Kafka Topic"""
    topics = [
        {
            'name': 'CREATE_KNOWLEDGE_ITEM',
            'partitions': 3,
            'replication_factor': 1,
            'config': {
                'retention.ms': '604800000',  # 7 days
                'cleanup.policy': 'delete'
            }
        },
        {
            'name': MessageType.FILE_PROCESSING.value,
            'partitions': 3,
            'replication_factor': 1,
            'config': {
                'retention.ms': '604800000',  # 7 days
                'cleanup.policy': 'delete'
            }
        }
    ]
    
    for topic_config in topics:
        try:
            await kafka_manager.create_topic(
                topic_name=topic_config['name'],
                num_partitions=topic_config.get('partitions', 3),
                replication_factor=topic_config.get('replication_factor', 1),
                config=topic_config.get('config')
            )
            logger.info(f"Topic '{topic_config['name']}' setup completed")
        except Exception as e:
            logger.error(f"Failed to setup topic '{topic_config['name']}': {e}")