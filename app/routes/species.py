import uuid

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models import Find, Species
from app.templating import templates

router = APIRouter(dependencies=[Depends(get_current_user)])


async def get_or_create_species(db: AsyncSession, name: str) -> Species | None:
    """Resolve a species by name, creating it if it doesn't exist.

    Matching is case-insensitive and whitespace-normalized so that
    "Bjørk", "bjørk" and " Bjørk " all resolve to a single row.
    """
    name = (name or "").strip()
    if not name:
        return None
    normalized = Species.normalize(name)
    result = await db.execute(
        select(Species).where(Species.name_normalized == normalized)
    )
    species = result.scalar_one_or_none()
    if species:
        return species
    species = Species(name=name, name_normalized=normalized)
    db.add(species)
    await db.flush()
    return species


@router.get("/api/species")
async def search_species(q: str = "", db: AsyncSession = Depends(get_db)):
    stmt = select(Species).order_by(Species.name)
    q = (q or "").strip()
    if q:
        stmt = stmt.where(Species.name_normalized.contains(Species.normalize(q)))
    stmt = stmt.limit(20)
    result = await db.execute(stmt)
    species = result.scalars().all()
    return JSONResponse([{"id": str(s.id), "name": s.name} for s in species])


@router.post("/api/species")
async def create_species(name: str = Form(...), db: AsyncSession = Depends(get_db)):
    species = await get_or_create_species(db, name)
    if not species:
        return JSONResponse({"error": "Name required"}, status_code=400)
    await db.commit()
    return JSONResponse({"id": str(species.id), "name": species.name})


@router.get("/species", response_class=HTMLResponse)
async def manage_species(request: Request, db: AsyncSession = Depends(get_db)):
    stmt = (
        select(Species, func.count(Find.id))
        .outerjoin(Find, Find.species_id == Species.id)
        .group_by(Species.id)
        .order_by(Species.name)
    )
    result = await db.execute(stmt)
    species_data = [{"species": s, "count": c} for s, c in result.all()]
    return templates.TemplateResponse(request, "species/list.html", {
        "species_data": species_data,
    })


@router.post("/species/{species_id}/delete")
async def delete_species(species_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Species).where(Species.id == species_id))
    species = result.scalar_one_or_none()
    if species:
        await db.delete(species)
        await db.commit()
    return RedirectResponse(url="/species", status_code=303)
