"""Unit tests for the AI foundation (no network / no API key required)."""
from types import SimpleNamespace

import pytest

from app.services import ai


def test_build_system_prompt_injects_region():
    prompt = ai.build_system_prompt("species_id", "Toscana, Italia")
    assert "Toscana, Italia" in prompt
    # Task-specific instructions are appended after the base context.
    assert ai.AGENTS["species_id"].instructions in prompt


def test_build_system_prompt_defaults_blank_region():
    prompt = ai.build_system_prompt("review_checklist", "   ")
    assert ai.DEFAULT_REGION in prompt


def test_build_system_prompt_unknown_agent():
    with pytest.raises(KeyError):
        ai.build_system_prompt("does_not_exist", "Rogaland, Norway")


def test_enabled_agents_filters_by_toggle():
    app_settings = SimpleNamespace(
        ai_species_id=True,
        ai_review_checklist=False,
        ai_collect_timing=True,
        ai_suggest_metadata=False,
    )
    keys = {a.key for a in ai.enabled_agents(app_settings)}
    assert keys == {"species_id", "collect_timing"}


def test_enabled_agents_find_scoped_filter():
    app_settings = SimpleNamespace(
        ai_species_id=True,
        ai_review_checklist=True,
        ai_collect_timing=True,
        ai_suggest_metadata=True,
    )
    scoped = ai.enabled_agents(app_settings, find_scoped=True)
    assert all(a.find_scoped for a in scoped)


def test_is_configured_reflects_key(monkeypatch):
    monkeypatch.setattr(ai.settings, "openai_api_key", "")
    assert ai.is_configured() is False
    monkeypatch.setattr(ai.settings, "openai_api_key", "sk-test")
    assert ai.is_configured() is True


@pytest.mark.asyncio
async def test_complete_raises_when_unconfigured(monkeypatch):
    monkeypatch.setattr(ai.settings, "openai_api_key", "")
    with pytest.raises(ai.AINotConfigured):
        await ai.complete("species_id", "hi", region="Rogaland, Norway")
