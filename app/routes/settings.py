from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.config import settings as app_config
from app.database import get_db
from app.services.settings import get_app_settings
from app.templating import templates

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request, db: AsyncSession = Depends(get_db)):
    settings = await get_app_settings(db)
    return templates.TemplateResponse(
        request,
        "settings.html",
        {
            "settings": settings,
            "openai_configured": bool(app_config.openai_api_key),
        },
    )


@router.post("/settings")
async def update_settings(
    request: Request,
    region: str = Form(""),
    ai_species_id: bool = Form(False),
    ai_review_checklist: bool = Form(False),
    ai_collect_timing: bool = Form(False),
    ai_suggest_metadata: bool = Form(False),
    db: AsyncSession = Depends(get_db),
):
    settings = await get_app_settings(db)
    region = (region or "").strip()
    settings.region = region or "Rogaland, Norway"
    settings.ai_species_id = ai_species_id
    settings.ai_review_checklist = ai_review_checklist
    settings.ai_collect_timing = ai_collect_timing
    settings.ai_suggest_metadata = ai_suggest_metadata
    await db.commit()
    return RedirectResponse(url="/settings", status_code=303)
