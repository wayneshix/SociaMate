#!/usr/bin/env python3
"""
Database migration script for creating tables.
"""
import sys
import os
import logging
import traceback

# Add the parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database import init_db, DATABASE_URL
from app.models import models_bases
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

def main():
    """Create database tables."""
    try:
        logging.info(f"Using DATABASE_URL: {DATABASE_URL}")
        logging.info("Creating database tables...")
        init_db()
        logging.info("Database tables created successfully.")
    except Exception as e:
        logging.error(f"Error creating database tables: {str(e)}")
        logging.error("Full traceback:")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main() 