from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.services import ai as ai_service
from app.services.settings import get_app_settings
from app.templating import templates

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/ai", response_class=HTMLResponse)
async def ai_page(request: Request, db: AsyncSession = Depends(get_db)):
    app_settings = await get_app_settings(db)
    return templates.TemplateResponse(
        request,
        "ai.html",
        {
            "configured": ai_service.is_configured(),
            "region": app_settings.region,
            "enabled": ai_service.enabled_agents(app_settings),
            "all_agents": list(ai_service.AGENTS.values()),
        },
    )
