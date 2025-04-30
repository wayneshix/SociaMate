"""
Unit tests for the chunking service.
"""
import pytest
import sys
import os
from datetime import datetime

# Add the parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.chunker import ChunkerService, ChunkerConfig
from app.models.message import Message

def test_chunk_conversation_empty():
    """Test chunking an empty conversation."""
    chunker = ChunkerService()
    chunks = chunker.chunk_conversation([], "test-conversation")
    assert len(chunks) == 0

def test_chunk_conversation_single_message():
    """Test chunking a conversation with a single message."""
    chunker = ChunkerService()
    
    message = Message(
        id=1,
        conversation_id="test-conversation",
        author="User1",
        content="This is a test message",
        timestamp=datetime.utcnow()
    )
    
    chunks = chunker.chunk_conversation([message], "test-conversation")
    
    assert len(chunks) == 1
    assert chunks[0].conversation_id == "test-conversation"
    assert chunks[0].chunk_index == 0
    assert chunks[0].message_count == 1
    assert "User1: This is a test message" in chunks[0].content
    assert chunks[0].authors == ["User1"]

def test_chunk_conversation_multiple_messages():
    """Test chunking a conversation with multiple messages."""
    chunker = ChunkerService()
    
    messages = [
        Message(
            id=i,
            conversation_id="test-conversation",
            author=f"User{i % 3 + 1}",
            content=f"This is test message {i}",
            timestamp=datetime.utcnow()
        )
        for i in range(10)
    ]
    
    chunks = chunker.chunk_conversation(messages, "test-conversation")
    
    assert len(chunks) == 1
    assert chunks[0].conversation_id == "test-conversation"
    assert chunks[0].chunk_index == 0
    assert chunks[0].message_count == 10
    
    # Check that all messages are included
    for i in range(10):
        assert f"User{i % 3 + 1}: This is test message {i}" in chunks[0].content
    
    # Check that all authors are included
    assert set(chunks[0].authors) == {"User1", "User2", "User3"}

def test_chunk_conversation_respects_max_tokens():
    """Test that chunking respects the maximum token limit."""
    # Create a chunker with a very small token limit
    config = ChunkerConfig(max_chunk_tokens=10, max_chunk_messages=100)
    chunker = ChunkerService(config)
    
    # Create messages with known token counts
    messages = [
        Message(
            id=i,
            conversation_id="test-conversation",
            author="User1",
            content="A B C D E",  # Each token is a letter plus space
            timestamp=datetime.utcnow()
        )
        for i in range(5)
    ]
    
    chunks = chunker.chunk_conversation(messages, "test-conversation")
    
    # Should create multiple chunks due to token limit
    assert len(chunks) > 1

def test_chunk_conversation_respects_max_messages():
    """Test that chunking respects the maximum message limit."""
    # Create a chunker with a small message limit
    config = ChunkerConfig(max_chunk_tokens=1000, max_chunk_messages=3)
    chunker = ChunkerService(config)
    
    # Create more messages than the limit
    messages = [
        Message(
            id=i,
            conversation_id="test-conversation",
            author="User1",
            content=f"Message {i}",
            timestamp=datetime.utcnow()
        )
        for i in range(10)
    ]
    
    chunks = chunker.chunk_conversation(messages, "test-conversation")
    
    # Should create multiple chunks due to message limit
    assert len(chunks) > 1
    
    # Each chunk should have at most 3 messages (except maybe the last one)
    for i, chunk in enumerate(chunks[:-1]):
        assert chunk.message_count <= 3

def test_chunk_conversation_with_overlap():
    """Test that chunking includes overlapping messages."""
    # Create a chunker with message limit and overlap
    config = ChunkerConfig(max_chunk_tokens=1000, max_chunk_messages=3, overlap_messages=1)
    chunker = ChunkerService(config)
    
    # Create sequential messages
    messages = [
        Message(
            id=i,
            conversation_id="test-conversation",
            author="User1",
            content=f"Message {i}",
            timestamp=datetime.utcnow()
        )
        for i in range(5)
    ]
    
    chunks = chunker.chunk_conversation(messages, "test-conversation")
    
    # Should have overlap between chunks
    assert "Message 2" in chunks[0].content  # Last message in first chunk
    assert "Message 2" in chunks[1].content  # First message in second chunk (overlap) 