# SociaMate Backend

Backend service for the SociaMate application, providing conversation processing, chunking, embedding, and summarization.

## Setup

### Prerequisites

- Python 3.10+
- PostgreSQL
- Redis (optional, for caching)

### Installation

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file:
```
# Hugging Face API Token
HF_TOKEN=your_huggingface_token_here

# Database Connection
DATABASE_URL=postgresql://postgres:postgres@localhost/sociamate

# Redis Cache (optional)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0

# Application Settings
LOG_LEVEL=INFO
DEBUG=True
MAX_CHUNK_TOKENS=1000
MAX_CHUNK_MESSAGES=50
OVERLAP_MESSAGES=2
CACHE_TTL=3600
TOP_K_CHUNKS=5
```

### Database Setup

1. Create a PostgreSQL database:
```bash
createdb sociamate
```

2. Initialize the database:
```bash
python scripts/create_tables.py
```

## Running the Application

Start the FastAPI server:
```bash
uvicorn app.main:app --reload --port 8000
```

## API Documentation

Once the server is running, you can access the API documentation at:
```
http://localhost:8000/docs
```

For detailed API documentation, see the [API Documentation](docs/API.md).

## Architecture

For details about the system architecture, see the [Architecture Documentation](docs/ARCHITECTURE.md).

## Benchmarks

Run the context retrieval benchmark:
```bash
python benchmarks/context_benchmark.py
```

## Tests

Run the test suite:
```bash
pytest
``` 