#!/usr/bin/env python3
"""
Benchmark script for testing context retrieval performance.
"""
import sys
import os
import time
import logging
import statistics
import uuid
import random
from datetime import datetime, timedelta

# Add the parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database import get_db, init_db
from app.repositories.message_repository import message_repository
from app.services.context import context_service
from app.services.cache import cache
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)

def generate_random_message():
    """Generate a random message."""
    authors = ["User1", "User2", "User3", "User4", "User5"]
    content_templates = [
        "I think we should {action} the {thing}.",
        "Has anyone seen the {thing}?",
        "Let's meet at {time} to discuss the {thing}.",
        "I disagree with {name}, because {reason}.",
        "I agree with {name}, the {thing} is important.",
        "What do you think about {thing}?",
        "I'm not sure about {thing}, maybe we should {action} it.",
        "Can someone help me with {thing}?",
        "I've been working on {thing} all day.",
        "Did you hear about {name}'s {thing}? It's amazing!"
    ]
    
    actions = ["review", "update", "delete", "check", "finalize", "discuss"]
    things = ["project", "report", "presentation", "budget", "proposal", "meeting", "email", "code", "design", "plan"]
    times = ["2pm", "tomorrow", "next week", "Friday", "Monday morning", "after lunch"]
    reasons = ["it's not feasible", "we don't have time", "it's too expensive", "it won't work", "we need more data"]
    
    template = random.choice(content_templates)
    content = template.format(
        action=random.choice(actions),
        thing=random.choice(things),
        time=random.choice(times),
        name=random.choice(authors),
        reason=random.choice(reasons)
    )
    
    return {
        "author": random.choice(authors),
        "content": content,
        "timestamp": datetime.utcnow() - timedelta(minutes=random.randint(0, 1000))
    }

def create_test_conversation(db, message_count=200):
    """Create a test conversation with random messages."""
    conversation_id = str(uuid.uuid4())
    
    # Generate messages
    messages = [generate_random_message() for _ in range(message_count)]
    
    # Sort by timestamp
    messages.sort(key=lambda x: x["timestamp"])
    
    # Create messages in the database
    created_messages = message_repository.create_messages(db, conversation_id, messages)
    
    logger.info(f"Created test conversation {conversation_id} with {len(created_messages)} messages")
    
    return conversation_id

def run_context_benchmark(db, conversation_id, iterations=10):
    """Run a benchmark for context retrieval."""
    # Ensure cache is empty
    cache.invalidate_conversation(conversation_id)
    
    # Test un-cached retrieval
    uncached_times = []
    for i in range(iterations):
        start_time = time.time()
        context = context_service.get_context(db, conversation_id, use_cache=False)
        elapsed = time.time() - start_time
        uncached_times.append(elapsed)
        logger.info(f"Iteration {i+1}: Context retrieval took {elapsed:.4f}s (uncached)")
    
    # Test cached retrieval
    cached_times = []
    for i in range(iterations):
        start_time = time.time()
        context = context_service.get_context(db, conversation_id, use_cache=True)
        elapsed = time.time() - start_time
        cached_times.append(elapsed)
        logger.info(f"Iteration {i+1}: Context retrieval took {elapsed:.4f}s (cached)")
    
    # Test semantic search retrieval
    query_times = []
    for i in range(iterations):
        query = f"meeting {i}"  # Simple query to avoid cache hits
        start_time = time.time()
        context = context_service.get_context(db, conversation_id, query_text=query)
        elapsed = time.time() - start_time
        query_times.append(elapsed)
        logger.info(f"Iteration {i+1}: Context retrieval with query took {elapsed:.4f}s")
    
    # Print summary statistics
    print("\nBenchmark Results:")
    print(f"Uncached retrieval: avg={statistics.mean(uncached_times):.4f}s, min={min(uncached_times):.4f}s, max={max(uncached_times):.4f}s")
    print(f"Cached retrieval: avg={statistics.mean(cached_times):.4f}s, min={min(cached_times):.4f}s, max={max(cached_times):.4f}s")
    print(f"Query retrieval: avg={statistics.mean(query_times):.4f}s, min={min(query_times):.4f}s, max={max(query_times):.4f}s")
    
    # Check if meeting our target of 500ms
    target_met = statistics.mean(cached_times) < 0.5
    print(f"\nTarget of <500ms for cached retrieval: {'MET' if target_met else 'NOT MET'}")
    
    return {
        "uncached_times": uncached_times,
        "cached_times": cached_times,
        "query_times": query_times,
        "target_met": target_met
    }

def main():
    """Run the benchmark."""
    logger.info("Initializing database...")
    init_db()
    
    # Get database session
    db = next(get_db())
    
    try:
        # Create test conversation
        logger.info("Creating test conversation...")
        conversation_id = create_test_conversation(db, message_count=200)
        
        # Run benchmark
        logger.info("Running benchmark...")
        results = run_context_benchmark(db, conversation_id)
        
        # Exit with success status
        sys.exit(0 if results["target_met"] else 1)
        
    except Exception as e:
        logger.exception(f"Error running benchmark: {str(e)}")
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    main() 