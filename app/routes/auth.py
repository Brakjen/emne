from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.auth import (
    login_user,
    logout_user,
    verify_password,
)
from app.config import settings

router = APIRouter()

from app.templating import templates


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html")


@router.post("/login")
async def login(request: Request):
    form = await request.form()
    password = form.get("password", "")

    if not settings.auth_password_hash or not verify_password(password, settings.auth_password_hash):
        return templates.TemplateResponse(
            request, "login.html", {"error": "Invalid password"}, status_code=401
        )

    response = RedirectResponse(url="/", status_code=303)
    login_user(response)
    return response


@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=303)
    logout_user(response)
    return response
