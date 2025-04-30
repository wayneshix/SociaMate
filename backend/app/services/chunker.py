"""
Chunking service for breaking conversations into manageable pieces.
"""
from datetime import datetime
from app.models.message import Message
from app.models.chunk import MessageChunk
from app.services.tokenizer import tokenizer
import logging

logger = logging.getLogger(__name__)

class ChunkerConfig:
    """Configuration for chunking parameters."""
    def __init__(
        self,
        max_chunk_tokens=1000,
        max_chunk_messages=50,
        overlap_messages=2
    ):
        self.max_chunk_tokens = max_chunk_tokens
        self.max_chunk_messages = max_chunk_messages
        self.overlap_messages = overlap_messages

class ChunkerService:
    """Service for chunking conversations."""
    
    def __init__(self, config=None):
        """Initialize the chunker with the given configuration."""
        self.config = config or ChunkerConfig()
    
    def chunk_conversation(self, messages, conversation_id):
        """
        Split a list of messages into chunks based on token count and message count.
        
        Args:
            messages: List of Message objects, sorted by timestamp
            conversation_id: ID of the conversation
            
        Returns:
            List of MessageChunk objects
        """
        if not messages:
            return []
            
        chunks = []
        current_chunk_messages = []
        current_chunk_token_count = 0
        current_authors = set()
        chunk_index = 0
        
        for message in messages:
            message_token_count = tokenizer.count_tokens(message.content)
            
            # Check if adding this message would exceed limits
            if (current_chunk_token_count + message_token_count > self.config.max_chunk_tokens or
                len(current_chunk_messages) >= self.config.max_chunk_messages) and current_chunk_messages:
                
                # Create a chunk from the current messages
                chunk = self._create_chunk(
                    current_chunk_messages, 
                    conversation_id, 
                    chunk_index,
                    current_chunk_token_count,
                    list(current_authors)
                )
                chunks.append(chunk)
                
                # Start a new chunk with overlap
                overlap_start = max(0, len(current_chunk_messages) - self.config.overlap_messages)
                current_chunk_messages = current_chunk_messages[overlap_start:]
                current_chunk_token_count = sum(tokenizer.count_tokens(m.content) for m in current_chunk_messages)
                current_authors = set(m.author for m in current_chunk_messages)
                chunk_index += 1
            
            # Add the message to the current chunk
            current_chunk_messages.append(message)
            current_chunk_token_count += message_token_count
            current_authors.add(message.author)
        
        # Create a final chunk if there are remaining messages
        if current_chunk_messages:
            chunk = self._create_chunk(
                current_chunk_messages, 
                conversation_id, 
                chunk_index,
                current_chunk_token_count,
                list(current_authors)
            )
            chunks.append(chunk)
        
        return chunks
    
    def _create_chunk(self, messages, conversation_id, chunk_index, token_count, authors):
        """Create a MessageChunk from a list of messages."""
        if not messages:
            return None
            
        # Concatenate all messages into a single string
        content = "\n\n".join([
            f"{message.author}: {message.content}" 
            for message in messages
        ])
        
        # Get start and end times
        start_time = min(message.timestamp for message in messages)
        end_time = max(message.timestamp for message in messages)
        
        return MessageChunk(
            conversation_id=conversation_id,
            chunk_index=chunk_index,
            content=content,
            start_time=start_time,
            end_time=end_time,
            token_count=token_count,
            message_count=len(messages),
            authors=authors
        )

# Create a global instance with default configuration
chunker = ChunkerService() 