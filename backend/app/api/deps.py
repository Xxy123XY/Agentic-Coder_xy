from fastapi import Header, HTTPException, status
from app.db.session import async_session
from app.config import get_settings

settings = get_settings()


async def get_db():
    """FastAPI dependency that yields a database session per request."""
    async with async_session() as session:
        yield session


def verify_api_key(x_api_key: str | None = Header(None)) -> None:
    """Simple API key check for internal endpoints (jobs list, etc.).

    For development this is optional — production should use GitHub OAuth.
    """
    if not settings.debug and x_api_key != settings.github_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )