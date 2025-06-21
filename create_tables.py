import asyncio
import sys
sys.path.append('.')

from app.db.connection import engine
from app.db.models import Base

async def create_tables():
    """Create all database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Database tables created successfully!")

if __name__ == "__main__":
    asyncio.run(create_tables()) 