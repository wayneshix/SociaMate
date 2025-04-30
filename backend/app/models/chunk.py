from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, Float
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class MessageChunk(Base):
    """Model for storing chunked conversations with embeddings."""
    __tablename__ = "message_chunks"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(String, index=True, nullable=False)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    embedding_id = Column(String, nullable=True)  # ID for vector store lookup
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    token_count = Column(Integer, nullable=False)
    message_count = Column(Integer, nullable=False)
    authors = Column(ARRAY(String), nullable=False)
    
    def to_dict(self):
        """Convert chunk to dictionary."""
        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "chunk_index": self.chunk_index,
            "content": self.content,
            "embedding_id": self.embedding_id,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "token_count": self.token_count,
            "message_count": self.message_count,
            "authors": self.authors
        } 