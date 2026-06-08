"""AI assistant foundation.

A small, declarative agent registry plus a single execution engine that all
AI features (#11 species ID, #12 review checklist, #13 collect timing, and
metadata suggestions) call through. Keeping the configuration as data means
adding or tuning a feature is a registry edit, not new branching code.

The OpenAI API key is read from ``settings.openai_api_key`` (env
``EMNE_OPENAI_API_KEY``) and is never stored in the database. When the key is
missing, :func:`is_configured` returns ``False`` and callers should degrade
gracefully instead of crashing; :func:`complete` raises :class:`AINotConfigured`.

The ``region`` injected into every system prompt comes from the single-row
app settings (default ``"Rogaland, Norway"``), so the assistant has local
context and can be pointed elsewhere when travelling.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.config import settings

DEFAULT_MODEL = "gpt-4o"
DEFAULT_REGION = "Rogaland, Norway"

# Base context prepended to every agent's task-specific instructions. ``{region}``
# is interpolated from app settings so model and app never drift on locale.
BASE_CONTEXT = (
    "You are a knowledgeable field naturalist assistant for someone who keeps a "
    "geotagged journal of natural finds — trees, saplings, burls, deadwood, "
    "rocks, mushrooms and viewpoints — often while looking for bonsai and "
    "yamadori material. The user is based in {region}, so assume that local "
    "climate, flora, seasons and regulations unless a find clearly indicates "
    "otherwise. Use the metric system and, where helpful, give Norwegian common "
    "names alongside scientific ones. Be concise, practical and honest about "
    "uncertainty; never invent observations that are not supported by the "
    "photos or notes. For anything involving foraging or collecting, include "
    "relevant safety and legal caveats (e.g. landowner permission, protected "
    "species, mushroom edibility)."
)


class AINotConfigured(RuntimeError):
    """Raised when an AI call is attempted but no OpenAI API key is configured."""


@dataclass(frozen=True)
class AgentConfig:
    """Declarative configuration for one AI feature."""

    key: str
    settings_flag: str  # attribute on AppSettings that enables this feature
    label: str
    description: str
    instructions: str  # task-specific guidance, appended after BASE_CONTEXT
    model: str = DEFAULT_MODEL
    temperature: float = 0.3
    max_tokens: int = 1024
    find_scoped: bool = True  # surfaced from the Find detail page


AGENTS: dict[str, AgentConfig] = {
    "species_id": AgentConfig(
        key="species_id",
        settings_flag="ai_species_id",
        label="Species identification",
        description="Suggest a likely species from a find's photos.",
        instructions=(
            "Identify the most likely species shown in the photos. Give your top "
            "candidate with a confidence level (high/medium/low) and one or two "
            "alternatives, citing the visual features (bark, leaves, buds, habit) "
            "that drove your guess. State clearly when the photos are insufficient "
            "for a confident call."
        ),
        temperature=0.2,
    ),
    "review_checklist": AgentConfig(
        key="review_checklist",
        settings_flag="ai_review_checklist",
        label="Find-specific review",
        description="Highlight this find's concrete strengths, risks and next checks.",
        instructions=(
            "Assume the user already knows the baseline yamadori checklist. Focus "
            "only on observations specific to this find from the provided notes and "
            "photos: concrete strengths, concrete concerns, and 3-6 next checks to "
            "confirm in the field. Avoid generic checklist boilerplate unless it is "
            "directly justified by this find's details. Keep it concise and scannable."
        ),
        temperature=0.4,
    ),
    "collect_timing": AgentConfig(
        key="collect_timing",
        settings_flag="ai_collect_timing",
        label="Collection timing",
        description="Advise on the best season/time to collect.",
        instructions=(
            "Advise on the best time of year to collect or work on this find given "
            "the species and the region's climate. Explain the reasoning briefly "
            "(dormancy, sap flow, frost risk) and note any aftercare implications."
        ),
        temperature=0.3,
    ),
    "suggest_metadata": AgentConfig(
        key="suggest_metadata",
        settings_flag="ai_suggest_metadata",
        label="Suggest metadata",
        description="Propose a title, category and notes from photos.",
        instructions=(
            "Suggest a concise title, the most fitting category (tree, sapling, "
            "burl, rock, mushroom, viewpoint, deadwood or other), and a short "
            "descriptive note for this find based on the photos and any existing "
            "details. Keep suggestions ready to drop straight into the form."
        ),
        temperature=0.5,
    ),
}


def is_configured() -> bool:
    """Whether an OpenAI API key is available for live calls."""
    return bool(settings.openai_api_key)


def get_agent(agent_key: str) -> AgentConfig:
    try:
        return AGENTS[agent_key]
    except KeyError as exc:
        raise KeyError(f"Unknown AI agent: {agent_key!r}") from exc


def build_system_prompt(agent_key: str, region: str | None) -> str:
    """Build an agent's full system prompt with region context injected."""
    agent = get_agent(agent_key)
    region = (region or "").strip() or DEFAULT_REGION
    return f"{BASE_CONTEXT.format(region=region)}\n\n{agent.instructions}"


def enabled_agents(app_settings, *, find_scoped: bool | None = None) -> list[AgentConfig]:
    """Return the agents whose settings toggle is on.

    Pass ``find_scoped=True`` to limit to features surfaced from a Find page.
    """
    result = []
    for agent in AGENTS.values():
        if not getattr(app_settings, agent.settings_flag, False):
            continue
        if find_scoped is not None and agent.find_scoped != find_scoped:
            continue
        result.append(agent)
    return result


def find_image_urls(find, *, use_full: bool = True, limit: int = 4) -> list[str]:
    """Build a list of (presigned) image URLs for a Find's photos.

    Centralizes image-attachment handling so feature code just passes the
    result to :func:`complete`. Requires ``find.photos`` to be loaded.
    """
    from app.services.photo import get_photo_url

    urls: list[str] = []
    for photo in (find.photos or [])[:limit]:
        key = photo.storage_key if use_full else photo.thumbnail_key
        urls.append(get_photo_url(key))
    return urls


async def complete(
    agent_key: str,
    user_text: str,
    *,
    region: str | None,
    image_urls: list[str] | None = None,
    system_override: str | None = None,
) -> str:
    """Run a one-shot (optionally vision) completion for the given agent.

    Raises :class:`AINotConfigured` if no API key is set so callers can show a
    friendly notice instead of crashing.
    """
    if not is_configured():
        raise AINotConfigured("EMNE_OPENAI_API_KEY is not set")

    agent = get_agent(agent_key)
    system_prompt = system_override or build_system_prompt(agent_key, region)

    content: list[dict] = [{"type": "text", "text": user_text}]
    for url in image_urls or []:
        content.append({"type": "image_url", "image_url": {"url": url}})

    # Imported lazily so the module (and its unit tests) don't require the
    # openai package or a key just to build prompts.
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    response = await client.chat.completions.create(
        model=agent.model,
        temperature=agent.temperature,
        max_tokens=agent.max_tokens,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": content},
        ],
        user="emne",
    )
    return response.choices[0].message.content or ""
