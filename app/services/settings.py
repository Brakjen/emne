from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AppSettings

# Single-row settings: there is exactly one row, with id = 1.
SETTINGS_ID = 1


async def get_app_settings(db: AsyncSession) -> AppSettings:
    """Return the single application settings row, creating it if missing."""
    settings = await db.get(AppSettings, SETTINGS_ID)
    if settings is None:
        settings = AppSettings(id=SETTINGS_ID)
        db.add(settings)
        await db.flush()
    return settings
