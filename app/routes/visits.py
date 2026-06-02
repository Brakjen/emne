import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Form, Request, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import get_current_user
from app.database import get_db
from app.models import Find, Photo, Visit
from app.services.photo import delete_photo_files, delete_photo_files_bulk, extract_exif_datetime, get_photo_url, upload_photo

router = APIRouter(prefix="/finds/{find_id}/visits", dependencies=[Depends(get_current_user)])

from app.templating import templates


@router.get("/new", response_class=HTMLResponse)
async def new_visit_form(request: Request, find_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    stmt = select(Find).where(Find.id == find_id)
    result = await db.execute(stmt)
    find = result.scalar_one_or_none()
    if not find:
        return HTMLResponse("Not found", status_code=404)

    return templates.TemplateResponse(request, "visits/form.html", {
        "find": find,
    })


@router.post("")
async def create_visit(
    find_id: uuid.UUID,
    request: Request,
    notes: str = Form(""),
    visited_at: str = Form(""),
    photos: list[UploadFile] = File(default=[]),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Find).where(Find.id == find_id)
    result = await db.execute(stmt)
    find = result.scalar_one_or_none()
    if not find:
        return HTMLResponse("Not found", status_code=404)

    if visited_at:
        visit_dt = datetime.fromisoformat(visited_at).replace(tzinfo=timezone.utc)
    else:
        visit_dt = datetime.now(timezone.utc)

    visit = Visit(
        find_id=find_id,
        notes=notes or None,
        visited_at=visit_dt,
    )
    db.add(visit)
    await db.flush()

    for photo_file in photos:
        if photo_file.filename and photo_file.size and photo_file.size > 0:
            image_bytes = await photo_file.read()
            if not image_bytes:
                continue
            storage_key, thumbnail_key = upload_photo(image_bytes, str(find_id))
            taken_at = extract_exif_datetime(image_bytes)
            photo = Photo(
                find_id=find_id,
                visit_id=visit.id,
                storage_key=storage_key,
                thumbnail_key=thumbnail_key,
                taken_at=taken_at,
            )
            db.add(photo)

    await db.commit()
    return RedirectResponse(url=f"/finds/{find_id}", status_code=303)


@router.get("/{visit_id}/edit", response_class=HTMLResponse)
async def edit_visit_form(request: Request, find_id: uuid.UUID, visit_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    stmt = select(Find).where(Find.id == find_id)
    result = await db.execute(stmt)
    find = result.scalar_one_or_none()
    if not find:
        return HTMLResponse("Not found", status_code=404)

    stmt = select(Visit).options(selectinload(Visit.photos)).where(Visit.id == visit_id, Visit.find_id == find_id)
    result = await db.execute(stmt)
    visit = result.scalar_one_or_none()
    if not visit:
        return HTMLResponse("Not found", status_code=404)

    photo_urls = [(p, get_photo_url(p.thumbnail_key)) for p in visit.photos]

    return templates.TemplateResponse(request, "visits/edit.html", {
        "find": find,
        "visit": visit,
        "photo_urls": photo_urls,
    })


@router.post("/{visit_id}/edit")
async def update_visit(
    find_id: uuid.UUID,
    visit_id: uuid.UUID,
    request: Request,
    notes: str = Form(""),
    visited_at: str = Form(""),
    photos: list[UploadFile] = File(default=[]),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Visit).where(Visit.id == visit_id, Visit.find_id == find_id)
    result = await db.execute(stmt)
    visit = result.scalar_one_or_none()
    if not visit:
        return HTMLResponse("Not found", status_code=404)

    if visited_at:
        visit.visited_at = datetime.fromisoformat(visited_at).replace(tzinfo=timezone.utc)
    visit.notes = notes or None

    for photo_file in photos:
        if photo_file.filename and photo_file.size and photo_file.size > 0:
            image_bytes = await photo_file.read()
            if not image_bytes:
                continue
            storage_key, thumbnail_key = upload_photo(image_bytes, str(find_id))
            taken_at = extract_exif_datetime(image_bytes)
            photo = Photo(
                find_id=find_id,
                visit_id=visit.id,
                storage_key=storage_key,
                thumbnail_key=thumbnail_key,
                taken_at=taken_at,
            )
            db.add(photo)

    await db.commit()
    return RedirectResponse(url=f"/finds/{find_id}", status_code=303)


@router.post("/{visit_id}/delete")
async def delete_visit(find_id: uuid.UUID, visit_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    stmt = select(Visit).options(selectinload(Visit.photos)).where(Visit.id == visit_id, Visit.find_id == find_id)
    result = await db.execute(stmt)
    visit = result.scalar_one_or_none()
    if not visit:
        return RedirectResponse(url=f"/finds/{find_id}", status_code=303)

    if visit.photos:
        keys = [(p.storage_key, p.thumbnail_key) for p in visit.photos]
        delete_photo_files_bulk(keys)
    for photo in visit.photos:
        await db.delete(photo)
    await db.delete(visit)
    await db.commit()
    return RedirectResponse(url=f"/finds/{find_id}", status_code=303)
