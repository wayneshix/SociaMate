from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
import sys
from dotenv import load_dotenv

load_dotenv()

# Get database URL from environment variables with a default for local development
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost/sociamate")

# Set encoding environment variables in the current process
os.environ["PGCLIENTENCODING"] = "UTF8"

# Create SQLAlchemy engine with explicit connect_args
try:
    engine = create_engine(
        DATABASE_URL,
        connect_args={
            "client_encoding": "utf8",  # Force UTF-8 encoding for connections
        }
    )
    # Test connection
    with engine.connect() as conn:
        print("Database connection successful!")
except Exception as e:
    print(f"Error connecting to database: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Dependency for getting a database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Function to initialize the database (create tables)
def init_db():
    from app.models import models_bases
    try:
        for base in models_bases:
            base.metadata.create_all(bind=engine)
        print("Database tables created successfully!")
    except Exception as e:
        print(f"Error creating tables: {e}")
        import traceback
        traceback.print_exc()
        raise 