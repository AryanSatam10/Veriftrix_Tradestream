from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

# 1. Import your strictly typed settings
from core.config import settings

# 2. Strictly read the URL from Pydantic settings
DATABASE_URL = settings.DATABASE_URL

# Create Async Engine for non-blocking DB operations
engine = create_async_engine(
    DATABASE_URL,
    echo=False,              
    pool_size=20,            
    max_overflow=10,         
    pool_timeout=30          
)

# Async Session factory for dependency injection in FastAPI
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False   
)

class Base(DeclarativeBase):
    """Abstract declarative base class for SQLAlchemy 2.0 Unified Mapping"""
    pass

# Dependency to yield database sessions per request
async def get_db_session():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise