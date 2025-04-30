"""
Unit tests for the vector store service.
"""
import pytest
import sys
import os
import numpy as np
import uuid
import tempfile
import shutil

# Add the parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.vector_store import VectorStore
from app.services.embedding import embedding_service

def test_vector_store_dimensions():
    """Test that the vector store is using the correct dimensions."""
    # Create a temporary directory for index files
    temp_dir = tempfile.mkdtemp()
    try:
        # Create a vector store with the default dimension (should be 384 for bge-small-en-v1.5)
        vs = VectorStore(index_dir=temp_dir)
        
        # Check that the dimension is 384
        assert vs.dimension == 384
        
        # Generate a test embedding
        test_text = "This is a test sentence for embedding"
        embedding = embedding_service.generate_embedding(test_text)
        
        # Check that the embedding dimension matches the vector store dimension
        assert len(embedding) == vs.dimension
        
        # Test adding the embedding to the store
        conversation_id = str(uuid.uuid4())
        chunk_id = 1
        
        # Add embedding to store
        idx = vs.add_embedding(embedding, conversation_id, chunk_id)
        
        # Verify it was added successfully
        assert idx is not None
        
        # Test search functionality
        results = vs.search(embedding, conversation_id, top_k=1)
        
        # Verify we get a result
        assert len(results) == 1
        assert results[0][0] == chunk_id  # First result should be the chunk we added
        assert results[0][1] > 0.9  # Similarity to itself should be very high
    
    finally:
        # Clean up the temporary directory
        shutil.rmtree(temp_dir)

def test_vector_store_handles_dimension_mismatch():
    """Test that the vector store correctly handles dimension mismatches."""
    # Create a temporary directory for index files
    temp_dir = tempfile.mkdtemp()
    try:
        # Create a vector store with the default dimension
        vs = VectorStore(index_dir=temp_dir)
        
        # Create a test embedding with wrong dimension
        wrong_embedding = [0.1] * (vs.dimension - 50)  # 50 fewer dimensions
        
        # Create a test embedding with extra dimensions
        extra_embedding = [0.1] * (vs.dimension + 50)  # 50 more dimensions
        
        conversation_id = str(uuid.uuid4())
        
        # Add the wrong dimension embedding
        result1 = vs.add_embedding(wrong_embedding, conversation_id, chunk_id=1)
        
        # Add the extra dimension embedding
        result2 = vs.add_embedding(extra_embedding, conversation_id, chunk_id=2)
        
        # Both should succeed, with internal correction
        assert result1 is not None
        assert result2 is not None
        
        # Verify search still works
        query = [0.1] * vs.dimension
        results = vs.search(query, conversation_id, top_k=2)
        
        # Should find both results
        assert len(results) == 2
    
    finally:
        # Clean up the temporary directory
        shutil.rmtree(temp_dir)

def test_vector_store_singleton():
    """Test that the global vector store instance has the correct dimension."""
    from app.services.vector_store import vector_store
    
    # Check that the global instance has the correct dimension
    assert vector_store.dimension == 384 