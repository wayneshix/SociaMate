"""
Embedding service for generating vector embeddings of text chunks.
"""
import os
import requests
import numpy as np
import time
from dotenv import load_dotenv
import logging
import json
from typing import List, Dict, Any

load_dotenv()

logger = logging.getLogger(__name__)

# Default embedding model
DEFAULT_EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
HF_TOKEN = os.getenv("HF_TOKEN")

class EmbeddingService:
    """Service for generating embeddings from text."""
    
    def __init__(self, model_name=None, api_key=None):
        """Initialize the embedding service."""
        self.model_name = model_name or DEFAULT_EMBEDDING_MODEL
        self.api_key = api_key or HF_TOKEN
        self.api_url = f"https://api-inference.huggingface.co/models/{self.model_name}"
        self.headers = {"Authorization": f"Bearer {self.api_key}"}
        logger.info(f"Initialized EmbeddingService with model: {self.model_name}")
        
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate an embedding for a single text.
        
        Args:
            text: The text to embed
            
        Returns:
            List of floats representing the embedding vector
        """
        if not text:
            logger.warning("Empty text provided for embedding")
            return []
            
        try:
            # Apply model-specific instruction if needed (for BGE models)
            if "bge" in self.model_name.lower() and not text.startswith("Represent this sentence"):
                instruction = "Represent this sentence for searching relevant passages: "
                text = instruction + text
            
            # HuggingFace inference API expects this format
            payload = {"inputs": text, "options": {"wait_for_model": True}}
            
            # Make the API call
            start_time = time.time()
            response = requests.post(self.api_url, headers=self.headers, json=payload)
            embedding_time = time.time() - start_time
            
            logger.debug(f"Embedding generated in {embedding_time:.2f}s")
            
            if response.status_code != 200:
                logger.error(f"Error generating embedding: {response.text}")
                return []
                
            # Parse the response based on response format
            result = response.json()
            
            # For proper debugging
            logger.debug(f"Embedding result type: {type(result)}")
            if isinstance(result, dict):
                logger.debug(f"Embedding result keys: {result.keys()}")
            
            # Handle different response formats
            embedding = []
            if isinstance(result, list) and len(result) > 0:
                if isinstance(result[0], list):
                    # Format: [[0.1, 0.2, ...]]
                    embedding = result[0]
                elif isinstance(result[0], (int, float)):
                    # Format: [0.1, 0.2, ...]
                    embedding = result
            elif isinstance(result, dict):
                if "embeddings" in result:
                    if isinstance(result["embeddings"], list) and len(result["embeddings"]) > 0:
                        embedding = result["embeddings"][0]
                elif "embedding" in result:
                    embedding = result["embedding"]
                # Check for other potential formats
                for key in result:
                    if isinstance(result[key], list) and len(result[key]) > 0 and isinstance(result[key][0], (int, float)):
                        embedding = result[key]
                        break
            
            # Log dimension info for debugging
            if embedding:
                logger.debug(f"Generated embedding with dimension: {len(embedding)}")
            else:
                # If we reach here, the response format is unexpected
                logger.error(f"Unexpected embedding response format: {result}")
                logger.error(f"Response type: {type(result)}")
                
            return embedding
                
        except Exception as e:
            logger.exception(f"Error generating embedding: {str(e)}")
            return []
            
    def batch_generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in batch.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        if not texts:
            return []
            
        results = []
        for text in texts:
            embedding = self.generate_embedding(text)
            results.append(embedding)
            
        return results

# Create a global instance with default configuration
embedding_service = EmbeddingService() 
logger.info(f"Created global embedding_service with model: {embedding_service.model_name}") 