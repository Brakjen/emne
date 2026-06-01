from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from geoalchemy2.shape import to_shape
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import get_current_user
from app.database import get_db
from app.models import Find
from app.services.photo import get_photo_url

router = APIRouter(dependencies=[Depends(get_current_user)])
templates = Jinja2Templates(directory="app/templates")


@router.get("/map", response_class=HTMLResponse)
async def map_page(request: Request):
    return templates.TemplateResponse(request, "map.html")


@router.get("/api/finds/geojson")
async def finds_geojson(db: AsyncSession = Depends(get_db)):
    stmt = select(Find).options(selectinload(Find.photos)).order_by(Find.created_at.desc())
    result = await db.execute(stmt)
    finds = result.scalars().all()

    features = []
    for f in finds:
        point = to_shape(f.location)
        thumb_url = None
        if f.photos:
            thumb_url = get_photo_url(f.photos[0].thumbnail_key)

        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [point.x, point.y],
            },
            "properties": {
                "id": str(f.id),
                "title": f.title,
                "category": f.category,
                "thumbnail_url": thumb_url,
            },
        })

    return JSONResponse({
        "type": "FeatureCollection",
        "features": features,
    })
