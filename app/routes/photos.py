import uuid

from fastapi import APIRouter, Depends, Form, Request, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models import Photo
from app.services.photo import (
    delete_photo_files,
    extract_exif_datetime,
    get_photo_url,
    upload_photo,
)

router = APIRouter(prefix="/photos", dependencies=[Depends(get_current_user)])


@router.post("/{find_id}/upload")
async def upload_photo_route(
    find_id: uuid.UUID,
    visit_id: uuid.UUID | None = Form(None),
    caption: str = Form(""),
    photo: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    image_bytes = await photo.read()
    storage_key, thumbnail_key = upload_photo(image_bytes, str(find_id))
    taken_at = extract_exif_datetime(image_bytes)

    photo_record = Photo(
        find_id=find_id,
        visit_id=visit_id,
        storage_key=storage_key,
        thumbnail_key=thumbnail_key,
        caption=caption or None,
        taken_at=taken_at,
    )
    db.add(photo_record)
    await db.commit()
    return RedirectResponse(url=f"/finds/{find_id}", status_code=303)


@router.post("/{find_id}/upload-bulk")
async def upload_photos_bulk(
    find_id: uuid.UUID,
    visit_id: uuid.UUID | None = Form(None),
    photos: list[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
):
    for photo_file in photos:
        if not photo_file.filename or not photo_file.size or photo_file.size == 0:
            continue
        image_bytes = await photo_file.read()
        if not image_bytes:
            continue
        storage_key, thumbnail_key = upload_photo(image_bytes, str(find_id))
        taken_at = extract_exif_datetime(image_bytes)
        photo_record = Photo(
            find_id=find_id,
            visit_id=visit_id,
            storage_key=storage_key,
            thumbnail_key=thumbnail_key,
            taken_at=taken_at,
        )
        db.add(photo_record)
    await db.commit()
    return RedirectResponse(url=f"/finds/{find_id}", status_code=303)


@router.post("/{photo_id}/delete")
async def delete_photo_route(photo_id: uuid.UUID, next: str = Form(None), db: AsyncSession = Depends(get_db)):
    stmt = select(Photo).where(Photo.id == photo_id)
    result = await db.execute(stmt)
    photo = result.scalar_one_or_none()
    if not photo:
        return HTMLResponse("Not found", status_code=404)

    find_id = photo.find_id
    try:
        delete_photo_files(photo.storage_key, photo.thumbnail_key)
    except Exception:
        pass

    await db.delete(photo)
    await db.commit()
    redirect_url = next if next and next.startswith("/finds/") else f"/finds/{find_id}"
    return RedirectResponse(url=redirect_url, status_code=303)


@router.post("/{photo_id}/caption")
async def update_caption(photo_id: uuid.UUID, caption: str = Form(""), db: AsyncSession = Depends(get_db)):
    stmt = select(Photo).where(Photo.id == photo_id)
    result = await db.execute(stmt)
    photo = result.scalar_one_or_none()
    if not photo:
        return HTMLResponse("Not found", status_code=404)

    photo.caption = caption.strip() or None
    await db.commit()
    return RedirectResponse(url=f"/finds/{photo.find_id}", status_code=303)
