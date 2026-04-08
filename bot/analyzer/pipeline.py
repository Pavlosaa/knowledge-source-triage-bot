"""Claude analysis pipeline. Orchestrates 3-phase analysis of fetched content."""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import anthropic
from loguru import logger

from bot.analyzer.extractor import extract_github_urls
from bot.analyzer.json_utils import strip_markdown_json
from bot.analyzer.prompts import (
    CREDIBILITY_SYSTEM,
    FULL_ANALYSIS_SYSTEM,
    REJECTION_SUMMARY_SYSTEM,
    VALUE_ASSESSMENT_SYSTEM,
)
from bot.fetcher.article import fetch_article as fetch_generic_article
from bot.fetcher.github import RepoContent, extract_repo_coords, fetch_repo
from bot.fetcher.twitter import (
    TweetContent,
    detect_content_type,
    extract_tweet_id,
    fetch_tweet,
)
from bot.fetcher.twitter import (
    fetch_article as fetch_x_article,
)
from bot.notion.references import find_related_sources, write_relations

if TYPE_CHECKING:
    from bot.config import Config
    from bot.notion.projects import ProjectsCache
    from bot.notion.writer import NotionWriter

# Content truncation limits (chars) to control token costs
_PHASE12_CONTENT_LIMIT = 3_000
_PHASE3_CONTENT_LIMIT = 6_000

# Credibility score below which we reject without further analysis
_CREDIBILITY_REJECT_THRESHOLD = 2

_HAIKU = "claude-haiku-4-5-20251001"
_SONNET = "claude-sonnet-4-6"


@dataclass
class AnalysisResult:
    url: str
    has_value: bool

    # Source metadata (from fetcher)
    content_type: str | None = None
    author: str | None = None

    # Populated when has_value = True
    title: str | None = None
    core_summary: str | None = None
    key_principles: list[str] = field(default_factory=list)
    use_cases: list[str] = field(default_factory=list)
    discovery_score: int | None = None
    tags: list[str] = field(default_factory=list)
    project_recommendations: list[dict] = field(default_factory=list)
    notion_url: str | None = None

    # Populated when has_value = False
    brief_summary: str | None = None
    rejection_reason: str | None = None

    # Topic classification (Notion categories, 1-3)
    topics: list[str] = field(default_factory=list)

    # Concrete real-world usage example
    real_world_example: str | None = None

    # Credibility
    credibility_score: int | None = None
    credibility_reason: str | None = None

    # Dedup: set when URL already exists in Notion
    duplicate_of: dict | None = None

    # True when fetcher failed completely (content unavailable)
    fetch_failed: bool = False

    # Page ID for cross-referencing (set after Notion write)
    notion_page_id: str | None = None

    # Transient: fetched content for post-fetch extraction (not persisted/displayed)
    fetched_content: Any = field(default=None, repr=False)


async def run_pipeline(
    url: str,
    config: Config,
    writer: NotionWriter,
    projects: ProjectsCache,
    source_context: str | None = None,
) -> AnalysisResult:
    """
    Full analysis pipeline:
      1. Fetch content (twitter / playwright / github / article)
      2. Phase 1: credibility check (Haiku)
      3. Phase 2: value assessment (Haiku)
      4. Phase 3A/B: full analysis or rejection summary (Sonnet / Haiku)
      5. Create Notion page if has_value
    """
    result = AnalysisResult(url=url, has_value=False)
    _started_at = time.monotonic()

    # --- 0. Dedup check ---
    existing = await writer.find_existing(url)
    if existing:
        logger.info(f"Duplicate URL skipped: {url} → {existing['url']}")
        result.duplicate_of = existing
        _log_summary(result, url, _started_at)
        return result

    # --- 1. Fetch ---
    try:
        fetched, content_type, author = await _fetch(url, config)
    except Exception as exc:
        logger.error(f"Fetch failed for {url}: {exc}")
        result.rejection_reason = f"Nepodařilo se získat data ze zdroje: {exc}"
        result.fetch_failed = True
        _log_summary(result, url, _started_at)
        return result

    result.content_type = content_type
    result.author = author
    result.fetched_content = fetched
    content_text = _build_content_text(fetched)

    # --- 2. Phase 1: Credibility (Haiku) ---
    try:
        cred = await _call_claude(
            system=CREDIBILITY_SYSTEM,
            user=_credibility_prompt(url, content_text[:_PHASE12_CONTENT_LIMIT]),
            model=_HAIKU,
            max_tokens=150,
            api_key=config.anthropic_api_key,
        )
        result.credibility_score = int(cred.get("credibility_score", 3))
        result.credibility_reason = cred.get("credibility_reason")
    except Exception as exc:
        logger.warning(f"Phase 1 failed, continuing with neutral credibility: {exc}")
        result.credibility_score = 3

    if result.credibility_score < _CREDIBILITY_REJECT_THRESHOLD:
        result.rejection_reason = f"Low credibility ({result.credibility_score}/5): {result.credibility_reason}"
        _log_summary(result, url, _started_at)
        return result

    # --- 3. Phase 2: Value assessment (Haiku) ---
    try:
        value = await _call_claude(
            system=VALUE_ASSESSMENT_SYSTEM,
            user=content_text[:_PHASE12_CONTENT_LIMIT],
            model=_HAIKU,
            max_tokens=150,
            api_key=config.anthropic_api_key,
        )
        has_value = bool(value.get("has_value", False))
        phase2_rejection = value.get("rejection_reason")
    except Exception as exc:
        logger.warning(f"Phase 2 failed, assuming no value: {exc}")
        has_value = False
        phase2_rejection = "Analysis phase failed"

    if not has_value:
        # --- 4. Phase 3B: Rejection summary (Haiku) ---
        try:
            rejection = await _call_claude(
                system=REJECTION_SUMMARY_SYSTEM,
                user=content_text[:_PHASE12_CONTENT_LIMIT],
                model=_HAIKU,
                max_tokens=200,
                api_key=config.anthropic_api_key,
            )
            result.brief_summary = rejection.get("brief_summary")
            result.rejection_reason = rejection.get("rejection_reason") or phase2_rejection
        except Exception as exc:
            logger.warning(f"Phase 3B failed: {exc}")
            result.rejection_reason = phase2_rejection

        _log_summary(result, url, _started_at)
        return result

    # --- 5. Phase 3A: Full analysis (Sonnet) ---
    project_context = await projects.get_context()
    phase3_user = f"{content_text[:_PHASE3_CONTENT_LIMIT]}\n\n{project_context}"
    if source_context:
        phase3_user += f"\n\n[DISCOVERY CONTEXT — this repo was found in the following source:]\n{source_context}"

    try:
        analysis = await _call_claude(
            system=FULL_ANALYSIS_SYSTEM,
            user=phase3_user,
            model=_SONNET,
            max_tokens=2000,
            api_key=config.anthropic_api_key,
        )
    except Exception as exc:
        logger.error(f"Phase 3A failed for {url}: {exc}")
        result.rejection_reason = f"Analysis failed: {exc}"
        _log_summary(result, url, _started_at)
        return result

    result.has_value = True
    result.title = analysis.get("title")
    # Support both "topics" (list) and legacy "topic" (string)
    raw_topics = analysis.get("topics") or []
    if not raw_topics:
        legacy = analysis.get("topic")
        raw_topics = [legacy] if legacy else []
    result.topics = raw_topics
    result.core_summary = analysis.get("core_summary")
    result.key_principles = analysis.get("key_principles") or []
    result.use_cases = analysis.get("use_cases") or []
    result.real_world_example = analysis.get("real_world_example")
    result.discovery_score = analysis.get("discovery_score")
    result.tags = analysis.get("tags") or []
    result.project_recommendations = analysis.get("project_recommendations") or []

    # --- 6. Write to Notion ---
    page_id: str | None = None
    try:
        result.notion_url, page_id = await writer.create_source_page(result, url)
        result.notion_page_id = page_id
        logger.info(f"Notion record created: {result.notion_url}")
    except Exception as exc:
        logger.error(f"Notion write failed for {url}: {exc}")

    # --- 7. Cross-reference related sources ---
    if page_id and writer.database_id:
        try:
            related_ids = await find_related_sources(
                writer.client,
                writer.database_id,
                result,
                page_id,
                config.anthropic_api_key,
            )
            if related_ids:
                await write_relations(writer.client, page_id, related_ids)
                logger.info(f"Cross-referenced {len(related_ids)} related sources")
        except Exception as exc:
            logger.warning(f"Cross-referencing failed (non-blocking): {exc}")

    _log_summary(result, url, _started_at)
    return result


# ---------------------------------------------------------------------------
# Discovery orchestrator
# ---------------------------------------------------------------------------


async def run_pipeline_with_discovery(
    url: str,
    config: Config,
    writer: NotionWriter,
    projects: ProjectsCache,
) -> list[AnalysisResult]:
    """
    Run the analysis pipeline with automatic GitHub repo discovery.

    If the fetched content contains GitHub repo URLs, each repo is analyzed
    as a separate source. All resulting records are cross-referenced.
    """
    parent_result = await run_pipeline(url, config, writer, projects)

    # No discovery if fetch failed, duplicate, or no fetched content
    if parent_result.fetch_failed or parent_result.duplicate_of or not parent_result.fetched_content:
        return [parent_result]

    # Extract GitHub URLs from fetched content
    discovered_urls = await extract_github_urls(parent_result.fetched_content, url)
    if not discovered_urls:
        return [parent_result]

    logger.info(f"Discovered {len(discovered_urls)} GitHub repo(s) in {url}")

    # Build source context from parent for enriching repo analysis
    context = _build_source_context(parent_result)

    # Process each discovered repo sequentially
    repo_results: list[AnalysisResult] = []
    for repo_url in discovered_urls:
        try:
            repo_result = await run_pipeline(repo_url, config, writer, projects, source_context=context)
            repo_results.append(repo_result)
        except Exception as exc:
            logger.warning(f"Discovery pipeline failed for {repo_url}: {exc}")

    all_results = [parent_result, *repo_results]

    # Batch cross-reference all sibling pages
    await _cross_reference_siblings(writer, all_results)

    return all_results


def _build_source_context(result: AnalysisResult) -> str:
    """Build a concise context string from a parent analysis result."""
    parts: list[str] = []
    if result.title:
        parts.append(f"Title: {result.title}")
    if result.core_summary:
        parts.append(f"Summary: {result.core_summary}")
    parts.append(f"URL: {result.url}")
    context = "\n".join(parts)
    return context[:500]


async def _cross_reference_siblings(
    writer: NotionWriter,
    results: list[AnalysisResult],
) -> None:
    """Cross-reference all sibling pages that have Notion records."""
    page_ids = [r.notion_page_id for r in results if r.has_value and r.notion_page_id]
    if len(page_ids) < 2 or not writer.database_id:
        return

    try:
        for page_id in page_ids:
            sibling_ids = [pid for pid in page_ids if pid != page_id]
            await write_relations(writer.client, page_id, sibling_ids)
        logger.info(f"Batch cross-referenced {len(page_ids)} sibling pages")
    except Exception as exc:
        logger.warning(f"Sibling cross-referencing failed (non-blocking): {exc}")


# ---------------------------------------------------------------------------
# Fetch routing
# ---------------------------------------------------------------------------


async def _fetch(
    url: str,
    config: Config,
) -> tuple[Any, str, str | None]:
    """Route URL to the right fetcher. Returns (fetched_content, content_type_label, author)."""
    # GitHub
    coords = extract_repo_coords(url)
    if coords:
        owner, repo = coords
        fetched = await fetch_repo(owner, repo, token=config.github_token)
        author = owner
        return fetched, "GitHub", author

    # X.com
    x_type = detect_content_type(url)
    if x_type in ("tweet", "article"):
        if config.scrapfly_api_key is None:
            raise RuntimeError(
                "X.com fetching requires SCRAPFLY_API_KEY. Set it in .env to enable tweet/article analysis."
            )

        if x_type == "tweet":
            tweet_id = extract_tweet_id(url)
            fetched_tweet = await fetch_tweet(
                tweet_id or "",
                api_key=config.scrapfly_api_key,
            )
            author = f"@{fetched_tweet.author_username}"
            return fetched_tweet, "Tweet", author

        fetched_article = await fetch_x_article(url, api_key=config.scrapfly_api_key)
        return fetched_article, "X Article", fetched_article.author_name

    # Generic article / web page
    fetched_generic = await fetch_generic_article(url)
    return fetched_generic, "Article", None


# ---------------------------------------------------------------------------
# Content normalization
# ---------------------------------------------------------------------------


def _build_content_text(fetched: Any) -> str:
    if isinstance(fetched, TweetContent):
        lines = [
            "[SYSTEM-PROVIDED METADATA — use ONLY these facts, do NOT invent missing fields]",
            f"Author: @{fetched.author_username} ({fetched.author_name})",
        ]
        if fetched.follower_count is not None:
            lines.append(f"Followers: {fetched.follower_count:,}")
        if fetched.is_verified is not None:
            lines.append(f"Verified: {fetched.is_verified}")
        lines += ["", fetched.text]
        if fetched.embedded_urls:
            lines += ["", "Embedded URLs:", *fetched.embedded_urls]
        return "\n".join(lines)

    if isinstance(fetched, RepoContent):
        lines = [
            f"GitHub: {fetched.owner}/{fetched.repo}",
            f"Stars: {fetched.stars:,}",
            f"Language: {fetched.language or 'unknown'}",
            f"Description: {fetched.description or 'none'}",
            "",
            "README:",
            fetched.readme or "(no README)",
        ]
        return "\n".join(lines)

    # ArticleContent or playwright PageContent
    title = getattr(fetched, "title", None) or ""
    body = getattr(fetched, "body", "")
    return f"Title: {title}\n\n{body}" if title else body


def _credibility_prompt(url: str, content_preview: str) -> str:
    return f"URL: {url}\n\nContent preview:\n{content_preview}"


# ---------------------------------------------------------------------------
# Claude call with retry
# ---------------------------------------------------------------------------


def _log_summary(result: AnalysisResult, url: str, started_at: float) -> None:
    """Emit a single structured log line per processed URL."""
    duration_ms = int((time.monotonic() - started_at) * 1000)
    logger.info(
        "pipeline_done | url={url} | type={content_type} | has_value={has_value} "
        "| score={score} | duration_ms={duration_ms}",
        url=url,
        content_type=result.content_type or "unknown",
        has_value=result.has_value,
        score=result.discovery_score,
        duration_ms=duration_ms,
    )


async def _call_claude(
    system: str,
    user: str,
    model: str,
    max_tokens: int,
    api_key: str,
    max_attempts: int = 3,
) -> dict:
    """Call Claude with exponential backoff retry. Returns parsed JSON dict."""
    client = anthropic.AsyncAnthropic(api_key=api_key)
    last_exc: Exception | None = None

    for attempt in range(max_attempts):
        try:
            response = await client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            block = response.content[0]
            raw_text = block.text if hasattr(block, "text") else ""  # type: ignore[union-attr]
            text = raw_text.strip()
            text = strip_markdown_json(text)
            return json.loads(text)  # type: ignore[no-any-return]
        except json.JSONDecodeError as exc:
            logger.warning(f"Claude returned invalid JSON (attempt {attempt + 1}): {exc}")
            last_exc = exc
        except anthropic.APIError as exc:
            logger.warning(f"Claude API error (attempt {attempt + 1}): {exc}")
            last_exc = exc

        if attempt < max_attempts - 1:
            delay = 2 ** (attempt + 1)
            await asyncio.sleep(delay)

    raise RuntimeError(f"Claude call failed after {max_attempts} attempts") from last_exc
