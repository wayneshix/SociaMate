# SociaMate Architecture

## Overview

SociaMate's backend is designed to efficiently handle large conversation histories, process them into meaningful chunks, and provide relevant context for summarization and reply generation. The architecture follows clean code principles with a separation of concerns, dependency injection, and a repository pattern.

## Components

### 1. Database Layer

#### Models
- `Message`: Stores individual chat messages with author, content, timestamp, and metadata
- `MessageChunk`: Stores conversation chunks with embeddings for semantic search
- `Summary`: Stores generated summaries to avoid redundant processing

#### Database Connection
- Uses SQLAlchemy as an ORM
- PostgreSQL for reliable data storage
- Connection pooling for efficient resource usage

### 2. Repository Layer

#### Message Repository
- Handles CRUD operations for messages
- Manages conversation chunking and embedding generation
- Implements caching invalidation

### 3. Service Layer

#### Chunker Service
- Breaks conversations into manageable chunks
- Balances token count and message count
- Provides overlap between chunks for context continuity

#### Embedding Service
- Generates vector embeddings for text chunks
- Uses Hugging Face models for semantic embeddings
- Includes error handling and metrics

#### Vector Store
- FAISS-based vector index for semantic search
- Stores and retrieves embeddings efficiently
- Persists indices to disk

#### Cache Service
- Redis-based caching for frequent operations
- Caches context and summaries
- Implements TTL and invalidation strategies

#### Context Service
- Retrieves relevant context for queries
- Combines vector search with chronological fallback
- Optimized for under 500ms response time

#### Summarizer Service
- Generates summaries from context
- Uses Hugging Face summarization models
- Supports query-focused summarization

### 4. API Layer

#### FastAPI Endpoints
- RESTful API for conversation management
- Context and summary endpoints
- Proper validation and error handling

## Data Flow

1. **Message Ingestion**:
   - Messages are added to a conversation
   - Messages are stored in the database
   - The conversation is chunked
   - Chunks are embedded and indexed

2. **Context Retrieval**:
   - Client requests context for a conversation
   - If a query is provided, semantic search is performed
   - Otherwise, recent chunks are retrieved
   - Cached context is returned if available

3. **Summarization**:
   - Client requests a summary
   - Relevant context is retrieved
   - Context is sent to the summarization model
   - Summary is cached and returned

## Scalability Considerations

### Database
- Indexes on frequently queried fields
- Partitioning for large conversations
- Connection pooling

### Vector Search
- FAISS supports distributed indices
- Sharding by conversation ID
- Batch processing for embeddings

### Caching
- Redis for in-memory caching
- Distributed cache with proper invalidation
- Metrics for hit rate optimization

## Performance Metrics

- Context retrieval: Target under 500ms
- Embedding generation: Monitored per chunk
- Database queries: Optimized with indexes
- Cache hit rate: Target above 80%

## Configuration

The system is configurable through environment variables and supports the following configurable parameters:

- Chunk size (tokens): Default 1000
- Chunk overlap (messages): Default 2
- Cache TTL (seconds): Default 3600
- Top-K retrieved chunks: Default 5

## Monitoring

- Logging at appropriate levels
- Performance metrics collection
- Benchmark scripts for performance validation 