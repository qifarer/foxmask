# foxmask/infrastructure/kafka.py
from kafka import KafkaProducer, KafkaConsumer
import json
from foxmask.core.config import get_settings

settings = get_settings()

def get_kafka_producer():
    return KafkaProducer(
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda v: json.dumps(v).encode('utf-8'),
        acks='all',
        retries=3
    )

def get_kafka_consumer(group_id: str, auto_offset_reset: str = 'earliest'):
    return KafkaConsumer(
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        value_deserializer=lambda m: json.loads(m.decode('utf-8')),
        group_id=group_id,
        auto_offset_reset=auto_offset_reset,
        enable_auto_commit=True
    )