"""
Vector store for semantic search of conversation chunks.
"""
import numpy as np
import faiss
import uuid
import os
import pickle
from typing import List, Dict, Any, Optional, Tuple
import logging
from app.services.embedding import embedding_service

logger = logging.getLogger(__name__)

class VectorStore:
    """FAISS-based vector store for semantic search."""
    
    def __init__(self, dimension=384, index_dir="./data/vector_indices"):
        """
        Initialize the vector store.
        
        Args:
            dimension: Dimensionality of the embedding vectors
            index_dir: Directory to store FAISS indices
        """
        self.dimension = dimension
        self.index_dir = index_dir
        self.indices = {}  # Map of conversation_id -> FAISS index
        self.id_maps = {}  # Map of conversation_id -> {id_in_index: chunk_id}
        
        # Create index directory if it doesn't exist
        os.makedirs(index_dir, exist_ok=True)
        
    def _get_or_create_index(self, conversation_id: str) -> Tuple[faiss.Index, Dict[int, str]]:
        """Get an existing index or create a new one for the conversation."""
        if conversation_id in self.indices:
            return self.indices[conversation_id], self.id_maps[conversation_id]
            
        # Check if index exists on disk
        index_path = os.path.join(self.index_dir, f"{conversation_id}_index.faiss")
        map_path = os.path.join(self.index_dir, f"{conversation_id}_map.pkl")
        
        if os.path.exists(index_path) and os.path.exists(map_path):
            try:
                logger.info(f"Loading existing index for conversation {conversation_id}")
                index = faiss.read_index(index_path)
                with open(map_path, "rb") as f:
                    id_map = pickle.load(f)
                    
                self.indices[conversation_id] = index
                self.id_maps[conversation_id] = id_map
                return index, id_map
            except Exception as e:
                logger.exception(f"Error loading index: {str(e)}")
                
        # Create a new index
        logger.info(f"Creating new index for conversation {conversation_id}")
        index = faiss.IndexFlatL2(self.dimension)
        id_map = {}
        
        self.indices[conversation_id] = index
        self.id_maps[conversation_id] = id_map
        
        return index, id_map
        
    def add_embedding(
        self, 
        embedding: List[float], 
        conversation_id: str, 
        chunk_id: int
    ) -> str:
        """
        Add an embedding vector to the store.
        
        Args:
            embedding: The embedding vector
            conversation_id: ID of the conversation
            chunk_id: ID of the chunk in the database
            
        Returns:
            ID of the embedding in the store
        """
        if not embedding:
            return None
        
        try:
            # Check if embedding is a float instead of a list/array
            if isinstance(embedding, float):
                logger.warning(f"Received a float instead of a list for embedding, creating a default vector")
                embedding = [embedding] + [0.0] * (self.dimension - 1)
                
            # Ensure embedding is the right dimensionality
            if len(embedding) != self.dimension:
                logger.warning(f"Embedding dimension mismatch. Expected {self.dimension}, got {len(embedding)}")
                # Pad or truncate as needed
                if len(embedding) < self.dimension:
                    # Pad with zeros
                    embedding = embedding + [0.0] * (self.dimension - len(embedding))
                else:
                    # Truncate
                    embedding = embedding[:self.dimension]
            
            # Convert to properly shaped numpy array (2D)
            vector = np.array([embedding], dtype=np.float32)
            
            # Get or create the index
            index, id_map = self._get_or_create_index(conversation_id)
            
            # Add to index
            idx = index.ntotal
            index.add(vector)
            
            # Update id map
            id_map[idx] = chunk_id
            
            # Save updated index
            self._save_index(conversation_id)
            
            return str(idx)
        except Exception as e:
            logger.exception(f"Error adding embedding: {str(e)}")
            return None
        
    def search(
        self, 
        query_embedding: List[float], 
        conversation_id: str, 
        top_k: int = 5
    ) -> List[Tuple[int, float]]:
        """
        Search for similar vectors.
        
        Args:
            query_embedding: The query embedding vector
            conversation_id: ID of the conversation to search in
            top_k: Number of results to return
            
        Returns:
            List of (chunk_id, similarity score) tuples
        """
        if not query_embedding or not conversation_id:
            return []
            
        # Convert to numpy array
        query_vector = np.array([query_embedding]).astype('float32')
        
        # Get the index
        try:
            index, id_map = self._get_or_create_index(conversation_id)
        except Exception as e:
            logger.exception(f"Error accessing index: {str(e)}")
            return []
            
        # Search
        if index.ntotal == 0:
            logger.warning(f"Empty index for conversation {conversation_id}")
            return []
            
        # Limit top_k to the number of vectors in the index
        top_k = min(top_k, index.ntotal)
        
        # Perform search
        distances, indices = index.search(query_vector, top_k)
        
        # Map index IDs to chunk IDs
        results = []
        for i, idx in enumerate(indices[0]):
            chunk_id = id_map.get(int(idx))
            if chunk_id is not None:
                # Convert distance to similarity score (1 - normalized distance)
                # FAISS L2 distance: lower is better
                # We want similarity: higher is better
                similarity = 1.0 - (distances[0][i] / (distances[0][-1] + 1e-5))
                results.append((chunk_id, similarity))
            
        return results
        
    def search_by_text(
        self, 
        query_text: str, 
        conversation_id: str, 
        top_k: int = 5
    ) -> List[Tuple[int, float]]:
        """
        Search for chunks similar to the query text.
        
        Args:
            query_text: The query text
            conversation_id: ID of the conversation to search in
            top_k: Number of results to return
            
        Returns:
            List of (chunk_id, similarity score) tuples
        """
        # Generate embedding for the query text
        query_embedding = embedding_service.generate_embedding(query_text)
        
        # Search with the generated embedding
        return self.search(query_embedding, conversation_id, top_k)
        
    def _save_index(self, conversation_id: str) -> None:
        """Save the index and id map to disk"""
        index, id_map = self._get_or_create_index(conversation_id)
        
        index_path = os.path.join(self.index_dir, f"{conversation_id}_index.faiss")
        map_path = os.path.join(self.index_dir, f"{conversation_id}_map.pkl")
        
        # Save the index
        faiss.write_index(index, index_path)
        
        # Save the id map
        with open(map_path, 'wb') as f:
            pickle.dump(id_map, f)
            
    def delete_conversation_embeddings(self, conversation_id: str) -> bool:
        """
        Delete all embeddings associated with a conversation
        
        Args:
            conversation_id: ID of the conversation to delete
            
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            index_path = os.path.join(self.index_dir, f"{conversation_id}_index.faiss")
            map_path = os.path.join(self.index_dir, f"{conversation_id}_map.pkl")
            
            # Check if files exist
            if os.path.exists(index_path):
                os.remove(index_path)
                logger.info(f"Deleted FAISS index for conversation {conversation_id}")
                
            if os.path.exists(map_path):
                os.remove(map_path)
                logger.info(f"Deleted ID map for conversation {conversation_id}")
                
            # Also remove from cache if present
            if conversation_id in self.indices:
                del self.indices[conversation_id]
                logger.info(f"Removed conversation {conversation_id} from index cache")
                
            if conversation_id in self.id_maps:
                del self.id_maps[conversation_id]
                logger.info(f"Removed conversation {conversation_id} from id_maps")
                
            return True
        except Exception as e:
            logger.exception(f"Error deleting conversation embeddings: {str(e)}")
            return False

# Create a global instance
vector_store = VectorStore(dimension=384) 