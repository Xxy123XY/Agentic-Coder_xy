from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from contextlib import asynccontextmanager
from app.config import get_settings

settings = get_settings()


@asynccontextmanager
async def get_checkpointer():
    """Async context manager that yields a SQLite checkpointer.

    Use with: `async with get_checkpointer() as cp: ...`
    """
    async with AsyncSqliteSaver.from_conn_string(settings.checkpointer_db) as saver:
        yield saver