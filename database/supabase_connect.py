import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DB_URL = os.getenv("SUPABASE_DB")
if DB_URL is None:
    DB_URL = os.getenv("SUPABASE_DB_URL")
if not DB_URL:
    raise ValueError("SUPABASE_DB or SUPABASE_DB_URL environment variable is not set.")

engine = create_engine(DB_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
