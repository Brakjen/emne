import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.routes.finds import ai_review_checklist


class _ScalarResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


@pytest.mark.asyncio
async def test_review_checklist_returns_content_when_enabled(monkeypatch):
    find = SimpleNamespace(
        id=uuid.uuid4(),
        title="Checklist target",
        category="tree",
        description="Old trunk near a fence",
        status="watching",
        species=SimpleNamespace(name="Pinus sylvestris"),
        photos=[],
    )
    settings = SimpleNamespace(ai_review_checklist=True, region="Rogaland, Norway")

    db = AsyncMock()
    db.execute.return_value = _ScalarResult(find)

    monkeypatch.setattr("app.routes.finds.get_app_settings", AsyncMock(return_value=settings))
    monkeypatch.setattr("app.routes.finds.ai_service.find_image_urls", lambda *_args, **_kwargs: [])
    monkeypatch.setattr("app.routes.finds.ai_service.complete", AsyncMock(return_value="- Check trunk\n- Check access"))

    with patch("app.routes.finds.ai_service.is_configured", return_value=True):
        response = await ai_review_checklist(find.id, db)

    assert response.status_code == 200
    assert b"Check trunk" in response.body


@pytest.mark.asyncio
async def test_review_checklist_disabled_returns_403(monkeypatch):
    find = SimpleNamespace(
        id=uuid.uuid4(),
        title="Disabled checklist",
        category="tree",
        description=None,
        status="watching",
        species=None,
        photos=[],
    )
    settings = SimpleNamespace(ai_review_checklist=False, region="Rogaland, Norway")

    db = AsyncMock()
    db.execute.return_value = _ScalarResult(find)
    monkeypatch.setattr("app.routes.finds.get_app_settings", AsyncMock(return_value=settings))

    with patch("app.routes.finds.ai_service.is_configured", return_value=True):
        response = await ai_review_checklist(find.id, db)

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_review_checklist_unconfigured_returns_503(monkeypatch):
    settings = SimpleNamespace(ai_review_checklist=True, region="Rogaland, Norway")
    db = AsyncMock()
    monkeypatch.setattr("app.routes.finds.get_app_settings", AsyncMock(return_value=settings))

    with patch("app.routes.finds.ai_service.is_configured", return_value=False):
        response = await ai_review_checklist(uuid.uuid4(), db)

    assert response.status_code == 503


@pytest.mark.asyncio
async def test_review_checklist_missing_find_returns_404(monkeypatch):
    settings = SimpleNamespace(ai_review_checklist=True, region="Rogaland, Norway")

    db = AsyncMock()
    db.execute.return_value = _ScalarResult(None)
    monkeypatch.setattr("app.routes.finds.get_app_settings", AsyncMock(return_value=settings))

    with patch("app.routes.finds.ai_service.is_configured", return_value=True):
        response = await ai_review_checklist(uuid.uuid4(), db)

    assert response.status_code == 404
