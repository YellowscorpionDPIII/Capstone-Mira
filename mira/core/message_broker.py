"""Message broker for event-driven architecture."""
from typing import Dict, Any, Callable, List
from collections import defaultdict
import logging
from datetime import datetime
import queue
import threading


class MessageBroker:
    """
    Central message broker for routing messages between agents.
    
    Implements publish-subscribe pattern for event-driven communication.
    """
    
    def __init__(self):
        """Initialize the message broker."""
        self.subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self.message_queue = queue.Queue()
        self.logger = logging.getLogger("mira.broker")
        self.running = False
        self.worker_thread = None
        
    def subscribe(self, message_type: str, handler: Callable[[Dict[str, Any]], None]):
        """
        Subscribe to a message type.
        
        Args:
            message_type: Type of message to subscribe to
            handler: Callback function to handle messages
        """
        self.subscribers[message_type].append(handler)
        self.logger.info(f"Subscriber added for message type: {message_type}")
        
    def unsubscribe(self, message_type: str, handler: Callable):
        """
        Unsubscribe from a message type.
        
        Args:
            message_type: Type of message to unsubscribe from
            handler: Handler to remove
        """
        if message_type in self.subscribers:
            self.subscribers[message_type].remove(handler)
            self.logger.info(f"Subscriber removed for message type: {message_type}")
            
    def publish(self, message_type: str, data: Dict[str, Any]):
        """
        Publish a message to all subscribers.
        
        Args:
            message_type: Type of message being published
            data: Message data
        """
        message = {
            'type': message_type,
            'data': data,
            'timestamp': datetime.utcnow().isoformat()
        }
        self.message_queue.put(message)
        self.logger.info(f"Message published: {message_type}")
        
    def _process_messages(self):
        """Process messages from the queue (runs in separate thread)."""
        while self.running:
            try:
                message = self.message_queue.get(timeout=1)
                message_type = message['type']
                
                if message_type in self.subscribers:
                    for handler in self.subscribers[message_type]:
                        try:
                            handler(message)
                        except Exception as e:
                            self.logger.error(f"Error in handler for {message_type}: {e}")
                            
                self.message_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.error(f"Error processing message: {e}")
                
    def start(self):
        """Start the message broker."""
        if not self.running:
            self.running = True
            self.worker_thread = threading.Thread(target=self._process_messages, daemon=True)
            self.worker_thread.start()
            self.logger.info("Message broker started")
            
    def stop(self):
        """Stop the message broker."""
        if self.running:
            self.running = False
            if self.worker_thread:
                self.worker_thread.join(timeout=5)
            self.logger.info("Message broker stopped")


# Singleton instance
_broker_instance = None


def get_broker() -> MessageBroker:
    """Get the singleton message broker instance."""
    global _broker_instance
    if _broker_instance is None:
        _broker_instance = MessageBroker()
    return _broker_instance
