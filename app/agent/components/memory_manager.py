from typing import List, Optional
from pydantic import BaseModel
from app.schema import Message
from loguru import logger

class MemoryManager(BaseModel):
    """Manages agent memory operations and message history.
    
    Provides functionality for storing, retrieving, and managing messages
    in the agent's memory with built-in duplicate detection.
    """
    
    messages: List[Message] = []
    duplicate_threshold: int = 2
    
    def add_message(self, message: Message) -> None:
        """Add a message to memory with logging.
        
        Args:
            message: The message to add to memory.
        """
        self.messages.append(message)
        logger.debug(f"Added {message.role} message to memory")
    
    def get_last_message(self) -> Optional[Message]:
        """Retrieve the most recent message from memory.
        
        Returns:
            The last message if memory is not empty, None otherwise.
        """
        return self.messages[-1] if self.messages else None
    
    def clear(self) -> None:
        """Clear all messages from memory."""
        self.messages.clear()
        logger.debug("Cleared memory")
    
    def is_stuck(self) -> bool:
        """Check if the agent is stuck in a loop by detecting duplicate content.
        
        Returns:
            bool: True if duplicate content threshold is reached, False otherwise.
        """
        if len(self.messages) < 2:
            return False
            
        last_message = self.get_last_message()
        if not last_message or not last_message.content:
            return False
            
        # Count identical content occurrences
        duplicate_count = sum(
            1
            for msg in reversed(self.messages[:-1])
            if msg.role == "assistant" and msg.content == last_message.content
        )
        
        return duplicate_count >= self.duplicate_threshold
    
    def get_context_window(self, window_size: int = 5) -> List[Message]:
        """Get the most recent messages within a context window.
        
        Args:
            window_size: Number of recent messages to include.
            
        Returns:
            List of most recent messages up to window_size.
        """
        return self.messages[-window_size:] if len(self.messages) > window_size else self.messages.copy()
    
    def search_messages(self, query: str) -> List[Message]:
        """Search messages containing the query string.
        
        Args:
            query: String to search for in message content.
            
        Returns:
            List of messages containing the query string.
        """
        return [msg for msg in self.messages if query.lower() in msg.content.lower()]
    
    class Config:
        arbitrary_types_allowed = True