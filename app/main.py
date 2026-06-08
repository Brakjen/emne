from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.auth import verify_session_token, SESSION_COOKIE
from app.routes import ai as ai_routes
from app.routes import auth as auth_routes
from app.routes import finds as finds_routes
from app.routes import map as map_routes
from app.routes import photos as photos_routes
from app.routes import guide as guide_routes
from app.routes import settings as settings_routes
from app.routes import species as species_routes
from app.routes import visits as visits_routes

app = FastAPI(title="Emne", docs_url=None, redoc_url=None)

app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    public_paths = ("/login", "/static/", "/health")
    path = request.url.path

    if any(path.startswith(p) for p in public_paths):
        return await call_next(request)

    token = request.cookies.get(SESSION_COOKIE)
    if not token or not verify_session_token(token):
        return RedirectResponse(url="/login", status_code=303)

    return await call_next(request)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/")
async def root():
    return RedirectResponse(url="/finds", status_code=303)


app.include_router(auth_routes.router)
app.include_router(finds_routes.router)
app.include_router(visits_routes.router)
app.include_router(photos_routes.router)
app.include_router(map_routes.router)
app.include_router(species_routes.router)
app.include_router(settings_routes.router)
app.include_router(ai_routes.router)
app.include_router(guide_routes.router)
