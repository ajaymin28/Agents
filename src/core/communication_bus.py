"""
Communication Bus Module

This module implements the central communication mechanism that facilitates
inter-agent and component communication in the Ollama agent framework.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Callable, Set

logger = logging.getLogger(__name__)

class CommunicationBus:
    """
    Communication Bus for the Ollama agent framework.
    
    Responsible for:
    - Asynchronous message passing between components
    - Event subscription and publication
    - Priority-based message handling
    - Message serialization/deserialization
    """
    
    def __init__(self):
        """Initialize the Communication Bus."""
        self.subscribers = {}
        self.message_queues = {}
        self.running = False
        self.processing_tasks = set()
        logger.info("Communication Bus initialized")
        
    async def start(self):
        """Start the Communication Bus."""
        logger.info("Starting Communication Bus")
        self.running = True
        logger.info("Communication Bus started")
        
    async def stop(self):
        """Stop the Communication Bus and cleanup resources."""
        logger.info("Stopping Communication Bus")
        self.running = False
        
        # Wait for all processing tasks to complete
        if self.processing_tasks:
            logger.info(f"Waiting for {len(self.processing_tasks)} message processing tasks to complete")
            await asyncio.gather(*self.processing_tasks, return_exceptions=True)
            
        logger.info("Communication Bus stopped")
        
    async def subscribe(self, topic: str, callback: Callable, priority: int = 5):
        """
        Subscribe to a topic.
        
        Args:
            topic: Topic to subscribe to
            callback: Function to call when a message is published to the topic
            priority: Priority level (0-10, higher is more important)
        """
        if topic not in self.subscribers:
            self.subscribers[topic] = []
            
        self.subscribers[topic].append({
            "callback": callback,
            "priority": priority
        })
        
        # Sort subscribers by priority (highest first)
        self.subscribers[topic].sort(key=lambda x: x["priority"], reverse=True)
        
        logger.debug(f"Subscribed to topic: {topic} with priority: {priority}")
        
    async def unsubscribe(self, topic: str, callback: Callable):
        """
        Unsubscribe from a topic.
        
        Args:
            topic: Topic to unsubscribe from
            callback: Callback function to remove
        """
        if topic not in self.subscribers:
            return
            
        self.subscribers[topic] = [
            s for s in self.subscribers[topic] if s["callback"] != callback
        ]
        
        if not self.subscribers[topic]:
            del self.subscribers[topic]
            
        logger.debug(f"Unsubscribed from topic: {topic}")
        
    async def publish(self, topic: str, message: Dict[str, Any], priority: int = 5):
        """
        Publish a message to a topic.
        
        Args:
            topic: Topic to publish to
            message: Message to publish
            priority: Priority level (0-10, higher is more important)
        """
        if not self.running:
            logger.warning("Attempted to publish message while Communication Bus is stopped")
            return
            
        if topic not in self.subscribers:
            logger.debug(f"No subscribers for topic: {topic}")
            return
            
        # Add metadata to message
        enriched_message = {
            **message,
            "_metadata": {
                "topic": topic,
                "priority": priority,
                "timestamp": asyncio.get_event_loop().time()
            }
        }
        
        # Create task for processing message
        task = asyncio.create_task(self._process_message(topic, enriched_message))
        self.processing_tasks.add(task)
        task.add_done_callback(self.processing_tasks.remove)
        
        logger.debug(f"Published message to topic: {topic} with priority: {priority}")
        
    async def _process_message(self, topic: str, message: Dict[str, Any]):
        """
        Process a message by delivering it to all subscribers.
        
        Args:
            topic: Topic the message was published to
            message: Message to process
        """
        if topic not in self.subscribers:
            return
            
        for subscriber in self.subscribers[topic]:
            try:
                await subscriber["callback"](message)
            except Exception as e:
                logger.exception(f"Error in subscriber callback for topic {topic}: {e}")
                
    async def create_queue(self, queue_name: str, max_size: int = 100):
        """
        Create a new message queue.
        
        Args:
            queue_name: Name of the queue to create
            max_size: Maximum number of messages the queue can hold
        """
        if queue_name in self.message_queues:
            logger.warning(f"Queue already exists: {queue_name}")
            return
            
        self.message_queues[queue_name] = asyncio.Queue(maxsize=max_size)
        logger.debug(f"Created message queue: {queue_name} with max size: {max_size}")
        
    async def delete_queue(self, queue_name: str):
        """
        Delete a message queue.
        
        Args:
            queue_name: Name of the queue to delete
        """
        if queue_name not in self.message_queues:
            logger.warning(f"Queue does not exist: {queue_name}")
            return
            
        del self.message_queues[queue_name]
        logger.debug(f"Deleted message queue: {queue_name}")
        
    async def send_to_queue(self, queue_name: str, message: Dict[str, Any], timeout: Optional[float] = None):
        """
        Send a message to a queue.
        
        Args:
            queue_name: Name of the queue to send to
            message: Message to send
            timeout: Maximum time to wait if queue is full (None = wait forever)
            
        Returns:
            True if message was sent, False if timeout occurred
        """
        if queue_name not in self.message_queues:
            logger.warning(f"Queue does not exist: {queue_name}")
            return False
            
        try:
            # Add metadata to message
            enriched_message = {
                **message,
                "_metadata": {
                    "queue": queue_name,
                    "timestamp": asyncio.get_event_loop().time()
                }
            }
            
            # Put message in queue with timeout
            await asyncio.wait_for(
                self.message_queues[queue_name].put(enriched_message),
                timeout=timeout
            )
            logger.debug(f"Sent message to queue: {queue_name}")
            return True
        except asyncio.TimeoutError:
            logger.warning(f"Timeout sending message to queue: {queue_name}")
            return False
            
    async def receive_from_queue(self, queue_name: str, timeout: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """
        Receive a message from a queue.
        
        Args:
            queue_name: Name of the queue to receive from
            timeout: Maximum time to wait if queue is empty (None = wait forever)
            
        Returns:
            Message if one was received, None if timeout occurred
        """
        if queue_name not in self.message_queues:
            logger.warning(f"Queue does not exist: {queue_name}")
            return None
            
        try:
            # Get message from queue with timeout
            message = await asyncio.wait_for(
                self.message_queues[queue_name].get(),
                timeout=timeout
            )
            
            # Mark task as done
            self.message_queues[queue_name].task_done()
            
            logger.debug(f"Received message from queue: {queue_name}")
            return message
        except asyncio.TimeoutError:
            logger.debug(f"Timeout receiving message from queue: {queue_name}")
            return None
            
    async def broadcast(self, message: Dict[str, Any], topics: Optional[List[str]] = None):
        """
        Broadcast a message to multiple topics.
        
        Args:
            message: Message to broadcast
            topics: List of topics to broadcast to (None = all topics)
        """
        if topics is None:
            topics = list(self.subscribers.keys())
            
        for topic in topics:
            await self.publish(topic, message)
            
        logger.debug(f"Broadcast message to {len(topics)} topics")
        
    async def create_stream(self, stream_name: str) -> asyncio.Queue:
        """
        Create a new message stream.
        
        Args:
            stream_name: Name of the stream to create
            
        Returns:
            Queue object for the stream
        """
        # Create a queue for the stream
        await self.create_queue(f"stream:{stream_name}", max_size=1000)
        return self.message_queues[f"stream:{stream_name}"]
        
    async def publish_to_stream(self, stream_name: str, data: Any):
        """
        Publish data to a stream.
        
        Args:
            stream_name: Name of the stream to publish to
            data: Data to publish
        """
        queue_name = f"stream:{stream_name}"
        
        if queue_name not in self.message_queues:
            logger.warning(f"Stream does not exist: {stream_name}")
            return
            
        # Create message
        message = {
            "data": data,
            "_metadata": {
                "stream": stream_name,
                "timestamp": asyncio.get_event_loop().time()
            }
        }
        
        # Try to put in queue, but don't block if full (drop message)
        try:
            self.message_queues[queue_name].put_nowait(message)
            logger.debug(f"Published data to stream: {stream_name}")
        except asyncio.QueueFull:
            logger.warning(f"Stream queue full, dropping message: {stream_name}")
            
    async def subscribe_to_stream(self, stream_name: str) -> asyncio.Queue:
        """
        Subscribe to a stream.
        
        Args:
            stream_name: Name of the stream to subscribe to
            
        Returns:
            Queue to receive stream data
        """
        queue_name = f"stream:{stream_name}"
        
        if queue_name not in self.message_queues:
            await self.create_queue(queue_name, max_size=1000)
            
        return self.message_queues[queue_name]
