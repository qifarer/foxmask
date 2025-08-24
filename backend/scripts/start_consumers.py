# scripts/start_consumers.py
#!/usr/bin/env python3
import asyncio
import signal
import sys
from foxmask.task.consumers import DocumentConsumer

async def main():
    consumer = DocumentConsumer()
    
    # Handle graceful shutdown
    def signal_handler(sig, frame):
        print("Shutting down consumers...")
        # Add cleanup logic here
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print("Starting Kafka consumers...")
    await consumer.start_consuming()

if __name__ == "__main__":
    asyncio.run(main())