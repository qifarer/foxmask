# -*- coding: utf-8 -*-
# foxmask/task/dead_letter_processor.py
# Dead letter queue processor for handling failed messages in Kafka

import asyncio
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from foxmask.core.kafka import kafka_manager
from foxmask.core.logger import logger

class DeadLetterProcessor:
    def __init__(self):
        self.dlq_topic = "dead_letter_queue"
        self.max_retries = 5
        self.retry_delay = timedelta(minutes=5)

    async def process_dead_letter_messages(self):
        """Process messages from dead letter queue"""
        consumer = await kafka_manager.create_consumer(self.dlq_topic, "dlq_processor_group")
        
        try:
            while True:
                messages = consumer.poll(timeout_ms=1000, max_records=10)
                
                for topic_partition, message_batch in messages.items():
                    for message in message_batch:
                        try:
                            await self.handle_dead_letter_message(message.value)
                            consumer.commit()
                            
                        except Exception as e:
                            logger.error(f"Error processing DLQ message {message.value.get('message_id')}: {e}")
                            continue
                
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"Error in DLQ processor: {e}")
        finally:
            consumer.close()

    async def handle_dead_letter_message(self, message_data: Dict[str, Any]):
        """Handle dead letter message"""
        original_message = message_data.get('original_message', {})
        failure_reason = message_data.get('failure_reason', 'Unknown')
        retry_count = message_data.get('retry_count', 0)
        
        logger.warning(
            f"Processing DLQ message {original_message.get('message_id')}, "
            f"retry count: {retry_count}, reason: {failure_reason}"
        )
        
        if retry_count >= self.max_retries:
            # Maximum retries reached, archive the message
            await self.archive_message(message_data)
            return
        
        # Check if enough time has passed for retry
        last_failure_time = datetime.fromisoformat(message_data.get('last_failure_time'))
        if datetime.utcnow() - last_failure_time < self.retry_delay:
            # Not enough time has passed, skip for now
            return
        
        # Retry the original message
        try:
            original_topic = original_message.get('topic')
            if original_topic:
                # Update retry count and retry
                message_data['retry_count'] = retry_count + 1
                message_data['last_failure_time'] = datetime.utcnow().isoformat()
                
                await kafka_manager.send_message(
                    topic=original_topic,
                    value=original_message,
                    key=original_message.get('key')
                )
                
                logger.info(f"Retried message {original_message.get('message_id')}")
                
        except Exception as e:
            logger.error(f"Failed to retry DLQ message {original_message.get('message_id')}: {e}")
            
            # Put back to DLQ with updated retry count
            message_data['retry_count'] = retry_count + 1
            message_data['last_failure_time'] = datetime.utcnow().isoformat()
            message_data['failure_reason'] = f"Retry failed: {str(e)}"
            
            await kafka_manager.send_message(
                topic=self.dlq_topic,
                value=message_data,
                key=original_message.get('message_id')
            )

    async def archive_message(self, message_data: Dict[str, Any]):
        """Archive message that has reached max retries"""
        # TODO: Implement message archiving (e.g., to database or cold storage)
        original_message_id = message_data.get('original_message', {}).get('message_id')
        
        logger.error(
            f"Archiving message {original_message_id} after {self.max_retries} failed retries"
        )
        
        # Here you would store the message in a database or other persistent storage
        # await archive_service.archive_message(message_data)

    async def send_to_dlq(
        self,
        original_message: Dict[str, Any],
        failure_reason: str,
        exception: Optional[Exception] = None
    ):
        """Send failed message to dead letter queue"""
        dlq_message = {
            'original_message': original_message,
            'failure_reason': failure_reason,
            'exception_info': str(exception) if exception else None,
            'last_failure_time': datetime.utcnow().isoformat(),
            'retry_count': 0
        }
        
        try:
            await kafka_manager.send_message(
                topic=self.dlq_topic,
                value=dlq_message,
                key=original_message.get('message_id', 'unknown')
            )
            
            logger.warning(
                f"Sent message {original_message.get('message_id')} to DLQ: {failure_reason}"
            )
            
        except Exception as e:
            logger.error(f"Failed to send message to DLQ: {e}")

# Global dead letter processor instance
dead_letter_processor = DeadLetterProcessor()