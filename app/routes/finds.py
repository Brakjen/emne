import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Form, Request, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from geoalchemy2.shape import to_shape, from_shape
from shapely.geometry import Point
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import get_current_user
from app.database import get_db
from app.models import Find, Photo, Visit, Species
from app.services.photo import (
    extract_exif_datetime,
    extract_exif_gps,
    get_photo_url,
    resolve_cover_photo,
    upload_photo,
)
from app.routes.species import get_or_create_species
from app.services import ai as ai_service
from app.services.settings import get_app_settings

router = APIRouter(prefix="/finds", dependencies=[Depends(get_current_user)])

from app.templating import templates


@router.get("", response_class=HTMLResponse)
async def list_finds(request: Request, category: str | None = None, status: str | None = None, species: uuid.UUID | None = None, db: AsyncSession = Depends(get_db)):
    stmt = select(Find).options(selectinload(Find.photos), selectinload(Find.species)).order_by(Find.created_at.desc())
    if category:
        stmt = stmt.where(Find.category == category)
    if status:
        stmt = stmt.where(Find.status == status)
    if species:
        stmt = stmt.where(Find.species_id == species)
    result = await db.execute(stmt)
    finds = result.scalars().all()

    # Attach thumbnail URLs
    finds_data = []
    for f in finds:
        point = to_shape(f.location)
        thumb_url = None
        cover = resolve_cover_photo(f)
        if cover:
            thumb_url = get_photo_url(cover.thumbnail_key)
        finds_data.append({
            "find": f,
            "lat": point.y,
            "lon": point.x,
            "thumbnail_url": thumb_url,
        })

    # Species used for the filter dropdown
    species_result = await db.execute(select(Species).order_by(Species.name))
    all_species = species_result.scalars().all()

    return templates.TemplateResponse(request, "finds/list.html", {
        "finds_data": finds_data,
        "current_category": category,
        "current_status": status,
        "current_species": str(species) if species else None,
        "all_species": all_species,
    })


@router.get("/new", response_class=HTMLResponse)
async def new_find_form(request: Request, lat: float | None = None, lon: float | None = None):
    return templates.TemplateResponse(request, "finds/form.html", {
        "find": None,
        "lat": lat,
        "lon": lon,
    })


@router.post("")
async def create_find(
    request: Request,
    title: str = Form(...),
    category: str = Form("other"),
    description: str = Form(""),
    species_name: str = Form(""),
    latitude: float = Form(...),
    longitude: float = Form(...),
    accuracy: float | None = Form(None),
    photos: list[UploadFile] = File(default=[]),
    db: AsyncSession = Depends(get_db),
):
    point = from_shape(Point(longitude, latitude), srid=4326)
    species = await get_or_create_species(db, species_name)
    find = Find(
        title=title,
        category=category,
        description=description or None,
        species_id=species.id if species else None,
        location=point,
        location_accuracy=accuracy,
    )
    db.add(find)
    await db.flush()

    for photo_file in photos:
        if photo_file.filename and photo_file.size and photo_file.size > 0:
            image_bytes = await photo_file.read()
            if not image_bytes:
                continue
            storage_key, thumbnail_key = upload_photo(image_bytes, str(find.id))
            taken_at = extract_exif_datetime(image_bytes)
            photo = Photo(
                find_id=find.id,
                storage_key=storage_key,
                thumbnail_key=thumbnail_key,
                taken_at=taken_at,
            )
            db.add(photo)

    await db.commit()
    return RedirectResponse(url=f"/finds/{find.id}", status_code=303)


@router.post("/{find_id}/status")
async def update_status(
    find_id: uuid.UUID,
    status: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Find).where(Find.id == find_id))
    find = result.scalar_one_or_none()
    if not find:
        return HTMLResponse("Not found", status_code=404)
    if status in ("watching", "collected", "passed"):
        find.status = status
        await db.commit()
    return RedirectResponse(url=f"/finds/{find_id}", status_code=303)


@router.post("/{find_id}/cover")
async def set_cover(
    find_id: uuid.UUID,
    photo_id: str = Form(""),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Find).options(selectinload(Find.photos)).where(Find.id == find_id)
    )
    find = result.scalar_one_or_none()
    if not find:
        return HTMLResponse("Not found", status_code=404)

    if photo_id:
        # Only allow a photo that belongs to this find; toggle off if re-selected
        target = uuid.UUID(photo_id)
        if find.cover_photo_id == target:
            find.cover_photo_id = None
        elif any(p.id == target for p in find.photos):
            find.cover_photo_id = target
    else:
        find.cover_photo_id = None
    await db.commit()
    return RedirectResponse(url=f"/finds/{find_id}", status_code=303)


@router.post("/{find_id}/refine-location")
async def refine_location(
    find_id: uuid.UUID,
    latitude: float = Form(...),
    longitude: float = Form(...),
    accuracy: float | None = Form(None),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Find).where(Find.id == find_id))
    find = result.scalar_one_or_none()
    if not find:
        return HTMLResponse("Not found", status_code=404)
    find.location = from_shape(Point(longitude, latitude), srid=4326)
    find.location_accuracy = accuracy
    await db.commit()
    return RedirectResponse(url=f"/finds/{find_id}", status_code=303)


@router.get("/{find_id}", response_class=HTMLResponse)
async def find_detail(request: Request, find_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    stmt = (
        select(Find)
        .options(
            selectinload(Find.photos),
            selectinload(Find.species),
            selectinload(Find.visits).selectinload(Visit.photos),
        )
        .where(Find.id == find_id)
    )
    result = await db.execute(stmt)
    find = result.scalar_one_or_none()
    if not find:
        return HTMLResponse("Not found", status_code=404)

    point = to_shape(find.location)
    all_photo_urls = [(p, get_photo_url(p.storage_key), get_photo_url(p.thumbnail_key)) for p in find.photos]
    initial_photo_urls = [(p, url, thumb) for p, url, thumb in all_photo_urls if p.visit_id is None]

    app_settings = await get_app_settings(db)
    ai_agents = ai_service.enabled_agents(app_settings, find_scoped=True)

    return templates.TemplateResponse(request, "finds/detail.html", {
        "find": find,
        "lat": point.y,
        "lon": point.x,
        "photo_urls": all_photo_urls,
        "initial_photo_urls": initial_photo_urls,
        "get_photo_url": get_photo_url,
        "ai_configured": ai_service.is_configured(),
        "ai_agents": ai_agents,
    })


@router.post("/{find_id}/ai/review-checklist")
async def ai_review_checklist(find_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    app_settings = await get_app_settings(db)

    if not ai_service.is_configured():
        return JSONResponse(
            {"error": "AI is not configured. Set EMNE_OPENAI_API_KEY first."},
            status_code=503,
        )

    if not app_settings.ai_review_checklist:
        return JSONResponse(
            {"error": "Review checklist is disabled in Settings."},
            status_code=403,
        )

    stmt = (
        select(Find)
        .options(selectinload(Find.photos), selectinload(Find.species))
        .where(Find.id == find_id)
    )
    result = await db.execute(stmt)
    find = result.scalar_one_or_none()
    if not find:
        return JSONResponse({"error": "Find not found"}, status_code=404)

    species_name = find.species.name if find.species else "Unknown"
    user_text = (
        "Create a practical bonsai/yamadori review checklist for this find.\n"
        f"Title: {find.title}\n"
        f"Category: {find.category}\n"
        f"Status: {find.status}\n"
        f"Species: {species_name}\n"
        f"Description: {find.description or '(none)'}"
    )

    try:
        content = await ai_service.complete(
            "review_checklist",
            user_text,
            region=app_settings.region,
            image_urls=ai_service.find_image_urls(find, use_full=False, limit=4),
        )
    except ai_service.AINotConfigured:
        return JSONResponse(
            {"error": "AI is not configured. Set EMNE_OPENAI_API_KEY first."},
            status_code=503,
        )

    return JSONResponse({"content": content.strip()})


@router.post("/{find_id}/ai/species-id")
async def ai_species_id(find_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    app_settings = await get_app_settings(db)

    if not ai_service.is_configured():
        return JSONResponse(
            {"error": "AI is not configured. Set EMNE_OPENAI_API_KEY first."},
            status_code=503,
        )

    if not app_settings.ai_species_id:
        return JSONResponse(
            {"error": "Species identification is disabled in Settings."},
            status_code=403,
        )

    stmt = (
        select(Find)
        .options(selectinload(Find.photos), selectinload(Find.species))
        .where(Find.id == find_id)
    )
    result = await db.execute(stmt)
    find = result.scalar_one_or_none()
    if not find:
        return JSONResponse({"error": "Find not found"}, status_code=404)

    if not find.photos:
        return JSONResponse(
            {"error": "No photos available. Add photos first for species identification."},
            status_code=400,
        )

    user_text = "Identify the species shown in these photos."

    try:
        content = await ai_service.complete(
            "species_id",
            user_text,
            region=app_settings.region,
            image_urls=ai_service.find_image_urls(find, use_full=False, limit=4),
        )
    except ai_service.AINotConfigured:
        return JSONResponse(
            {"error": "AI is not configured. Set EMNE_OPENAI_API_KEY first."},
            status_code=503,
        )

    return JSONResponse({"content": content.strip()})


@router.patch("/{find_id}/species")
async def update_find_species(
    find_id: uuid.UUID,
    species_name: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    """Update a find's species (used by AI species ID 'Apply' button)."""
    stmt = select(Find).where(Find.id == find_id)
    result = await db.execute(stmt)
    find = result.scalar_one_or_none()
    if not find:
        return JSONResponse({"error": "Find not found"}, status_code=404)

    species = await get_or_create_species(db, species_name)
    find.species_id = species.id
    await db.commit()

    return JSONResponse({"success": True, "species": species.name})


@router.get("/{find_id}/edit", response_class=HTMLResponse)
async def edit_find_form(request: Request, find_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    stmt = select(Find).options(selectinload(Find.species)).where(Find.id == find_id)
    result = await db.execute(stmt)
    find = result.scalar_one_or_none()
    if not find:
        return HTMLResponse("Not found", status_code=404)

    point = to_shape(find.location)
    return templates.TemplateResponse(request, "finds/form.html", {
        "find": find,
        "lat": point.y,
        "lon": point.x,
    })


@router.post("/{find_id}/edit")
async def update_find(
    find_id: uuid.UUID,
    title: str = Form(...),
    category: str = Form("other"),
    description: str = Form(""),
    species_name: str = Form(""),
    latitude: float = Form(...),
    longitude: float = Form(...),
    accuracy: float | None = Form(None),
    photos: list[UploadFile] = File(default=[]),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Find).where(Find.id == find_id)
    result = await db.execute(stmt)
    find = result.scalar_one_or_none()
    if not find:
        return HTMLResponse("Not found", status_code=404)

    species = await get_or_create_species(db, species_name)
    find.title = title
    find.category = category
    find.description = description or None
    find.species_id = species.id if species else None
    find.location = from_shape(Point(longitude, latitude), srid=4326)
    find.location_accuracy = accuracy

    for photo_file in photos:
        if photo_file.filename and photo_file.size and photo_file.size > 0:
            image_bytes = await photo_file.read()
            if not image_bytes:
                continue
            storage_key, thumbnail_key = upload_photo(image_bytes, str(find_id))
            taken_at = extract_exif_datetime(image_bytes)
            photo = Photo(
                find_id=find_id,
                storage_key=storage_key,
                thumbnail_key=thumbnail_key,
                taken_at=taken_at,
            )
            db.add(photo)

    await db.commit()
    return RedirectResponse(url=f"/finds/{find.id}", status_code=303)


@router.post("/{find_id}/delete")
async def delete_find(find_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    from app.services.photo import delete_photo_files

    stmt = select(Find).options(selectinload(Find.photos)).where(Find.id == find_id)
    result = await db.execute(stmt)
    find = result.scalar_one_or_none()
    if not find:
        return HTMLResponse("Not found", status_code=404)

    for photo in find.photos:
        try:
            delete_photo_files(photo.storage_key, photo.thumbnail_key)
        except Exception:
            pass

    await db.delete(find)
    await db.commit()
    return RedirectResponse(url="/finds", status_code=303)
