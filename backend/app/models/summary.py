from sqlalchemy import Column, String, Integer, DateTime, Text, Boolean
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class Summary(Base):
    """Model for storing conversation summaries."""
    __tablename__ = "summaries"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(String, index=True, nullable=False)
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    chunk_ids = Column(ARRAY(Integer), nullable=True)  # Which chunks were used
    is_full_summary = Column(Boolean, default=False)  # Whether it's a full chronological summary
    token_count = Column(Integer, nullable=False)
    
    def to_dict(self):
        """Convert summary to dictionary."""
        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "chunk_ids": self.chunk_ids or [],
            "is_full_summary": self.is_full_summary,
            "token_count": self.token_count
        } 