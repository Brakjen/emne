from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from app.auth import get_current_user
from app.templating import templates

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/resources", response_class=HTMLResponse)
async def resources_page(request: Request):
    return templates.TemplateResponse(request, "resources.html", {})
