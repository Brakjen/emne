"""Field Guide — static articles with markdown rendering."""
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse

from app.auth import get_current_user
from app.templating import templates

router = APIRouter(prefix="/guide", dependencies=[Depends(get_current_user)])

# Articles are defined here; content lives in app/guide/*.md
ARTICLES = [
    {
        "slug": "yamadori-checklist",
        "title": "Yamadori Baseline Checklist",
        "description": "Field checklist for assessing yamadori material: trunk, nebari, health, access, legal.",
        "icon": "✅",
    },
    {
        "slug": "collection-timing",
        "title": "Collection Timing Guide",
        "description": "When to collect based on species, season and regional climate.",
        "icon": "📅",
    },
    {
        "slug": "aftercare-basics",
        "title": "Aftercare Basics",
        "description": "Post-collection care: potting, watering, protection and recovery signs.",
        "icon": "🌱",
    },
]

GUIDE_DIR = Path(__file__).parent.parent / "guide"


def get_article(slug: str) -> dict | None:
    for article in ARTICLES:
        if article["slug"] == slug:
            return article
    return None


@router.get("", response_class=HTMLResponse)
async def guide_index(request: Request):
    return templates.TemplateResponse(request, "guide/index.html", {"articles": ARTICLES})


@router.get("/{slug}", response_class=HTMLResponse)
async def guide_article(request: Request, slug: str):
    article = get_article(slug)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    md_path = GUIDE_DIR / f"{slug}.md"
    if md_path.exists():
        content = md_path.read_text()
    else:
        content = f"# {article['title']}\n\n*Content coming soon.*"

    return templates.TemplateResponse(
        request,
        "guide/article.html",
        {"article": article, "content": content},
    )
