"""Claude analysis pipeline. Orchestrates 3-phase analysis of fetched content."""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import anthropic
from loguru import logger

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


async def run_pipeline(
    url: str,
    config: Config,
    writer: NotionWriter,
    projects: ProjectsCache,
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
        result.rejection_reason = f"Could not fetch content: {exc}"
        _log_summary(result, url, _started_at)
        return result

    result.content_type = content_type
    result.author = author
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
    try:
        result.notion_url = await writer.create_source_page(result, url)
        logger.info(f"Notion record created: {result.notion_url}")
    except Exception as exc:
        logger.error(f"Notion write failed for {url}: {exc}")

    _log_summary(result, url, _started_at)
    return result


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
            f"Author: @{fetched.author_username} ({fetched.author_name})",
            f"Followers: {fetched.follower_count:,}",
            f"Verified: {fetched.is_verified}",
            "",
            fetched.text,
        ]
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


def _strip_markdown_json(text: str) -> str:
    """Extract JSON object from text, handling markdown code blocks and trailing content."""
    # Strip markdown code fences
    if text.startswith("```"):
        lines = text.splitlines()
        inner = lines[1:-1] if lines[-1].strip() == "```" else lines[1:]
        text = "\n".join(inner).strip()

    # Extract first complete JSON object {…} to handle trailing text
    start = text.find("{")
    if start == -1:
        return text
    depth = 0
    in_string = False
    escape = False
    for i, ch in enumerate(text[start:], start):
        if escape:
            escape = False
            continue
        if ch == "\\" and in_string:
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if not in_string:
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return text[start : i + 1]
    return text[start:]


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
            text = _strip_markdown_json(text)
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
