"""
Integration tests for the backend services.
"""
import pytest
import sys
import os
import uuid
from datetime import datetime

# Add the parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.models.message import Message
from app.services.chunker import ChunkerService
from app.services.embedding import embedding_service
from app.services.vector_store import vector_store

def test_chunking_and_embedding_pipeline():
    """Test the entire chunking and embedding pipeline."""
    # Create a test conversation
    conversation_id = str(uuid.uuid4())
    
    # Create test messages
    messages = [
        Message(
            id=i,
            conversation_id=conversation_id,
            author="User1" if i % 2 == 0 else "User2",
            content=f"This is test message number {i} with some content to embed.",
            timestamp=datetime.now()
        )
        for i in range(5)
    ]
    
    # Create chunks from the messages
    chunker = ChunkerService()
    chunks = chunker.chunk_conversation(messages, conversation_id)
    
    # Verify chunks were created
    assert len(chunks) > 0
    
    # Embed each chunk and add to vector store
    chunk_ids = []
    for i, chunk in enumerate(chunks):
        # Generate embedding
        embedding = embedding_service.generate_embedding(chunk.content)
        
        # Verify embedding has the correct dimension
        assert len(embedding) == vector_store.dimension
        
        # Add to vector store
        idx = vector_store.add_embedding(embedding, conversation_id, chunk.id or i)
        
        # Verify it was added successfully
        assert idx is not None
        
        # Store chunk id for later search
        chunk_ids.append(chunk.id or i)
    
    # Test search functionality
    test_query = "test message with content"
    results = vector_store.search_by_text(test_query, conversation_id, top_k=3)
    
    # Verify we get results
    assert len(results) > 0
    
    # Cleanup
    vector_store.delete_conversation_embeddings(conversation_id) 