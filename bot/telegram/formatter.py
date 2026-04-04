"""Format AnalysisResult into Telegram HTML messages."""

from __future__ import annotations

import html
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bot.analyzer.pipeline import AnalysisResult

_SCORE_STARS = {1: "★☆☆☆☆", 2: "★★☆☆☆", 3: "★★★☆☆", 4: "★★★★☆", 5: "★★★★★"}


def _stars(score: int) -> str:
    return _SCORE_STARS.get(score, "?")


_TELEGRAM_MSG_LIMIT = 4096


def format_results(results: list[AnalysisResult], original_url: str) -> str:
    """Format one or more AnalysisResults for a Telegram reply."""
    if len(results) <= 1:
        return format_result(results[0], original_url)

    # Parent is first result
    parent_text = format_result(results[0], original_url)

    # Discovered repos
    repo_results = results[1:]
    valuable = [r for r in repo_results if r.has_value]
    skipped = len(repo_results) - len(valuable)

    if not valuable and skipped == 0:
        return parent_text

    lines: list[str] = [
        parent_text,
        "",
        f"🔍 <b>Nalezené repozitáře ({len(repo_results)}):</b>",
    ]

    for i, repo in enumerate(valuable, 1):
        score = repo.discovery_score or 0
        title = html.escape(repo.title or repo.url)
        line = f"{i}. {title} | {_stars(score)} ({score}/5)"
        if repo.notion_url:
            line += f'\n   📖 <a href="{repo.notion_url}">Notion →</a>'
        lines.append(line)

    if skipped > 0:
        lines.append(f"\n<i>({skipped} repozitářů přeskočeno �� duplikát nebo nízká hodnota)</i>")

    text = "\n".join(lines)
    if len(text) > _TELEGRAM_MSG_LIMIT:
        text = text[: _TELEGRAM_MSG_LIMIT - 3] + "..."
    return text


def format_result(result: AnalysisResult, original_url: str) -> str:
    """Render an AnalysisResult as an HTML-formatted Telegram message."""
    if result.duplicate_of:
        return _format_duplicate(result, original_url)
    if result.has_value:
        return _format_valuable(result, original_url)
    return _format_rejected(result, original_url)


def _format_duplicate(result: AnalysisResult, original_url: str) -> str:
    dup = result.duplicate_of
    lines: list[str] = [
        f'🔗 <a href="{original_url}">Původní zdroj</a>',
        "",
        "🔄 <b>Už zpracováno</b>",
    ]
    if dup is None:
        return "\n".join(lines)
    if dup.get("date"):
        lines.append(f"📅 Přidáno: {dup['date']}")
    if dup.get("url"):
        lines.append(f'📖 <a href="{dup["url"]}">Otevřít v Notion →</a>')
    return "\n".join(lines)


def _format_valuable(result: AnalysisResult, original_url: str) -> str:
    score = result.discovery_score or 0
    stars = _stars(score)

    lines: list[str] = [
        f'🔗 <a href="{original_url}">Původní zdroj</a>',
        "",
        f"✅ <b>Hodnotný zdroj</b> | {stars} ({score}/5)",
        "",
        f"📌 <b>Obsah:</b> {result.core_summary}",
    ]

    if result.key_principles:
        lines.append("")
        lines.append("🔑 <b>Klíčové body:</b>")
        for principle in result.key_principles:
            lines.append(f"• {principle}")

    if result.use_cases:
        lines.append("")
        lines.append("💡 <b>Use cases:</b>")
        for uc in result.use_cases:
            lines.append(f"• {uc}")

    if result.project_recommendations:
        relevant = [r for r in result.project_recommendations if r["relevance"] in ("high", "medium")]
        if relevant:
            lines.append("")
            project_names = ", ".join(r["project_name"] for r in relevant)
            lines.append(f"🎯 <b>Relevantní pro:</b> {project_names}")

    if result.notion_url:
        lines.append("")
        lines.append(f'📖 <a href="{result.notion_url}">Otevřít v Notion →</a>')
    else:
        lines.append("")
        lines.append("⚠️ <i>Notion záznam se nepodařilo vytvořit.</i>")

    return "\n".join(lines)


def _format_rejected(result: AnalysisResult, original_url: str) -> str:
    lines: list[str] = [
        f'🔗 <a href="{original_url}">Původní zdroj</a>',
        "",
    ]

    if result.fetch_failed:
        lines.append("⚠️ <b>Zdroj nedostupný</b>")
        lines.append("")
        if result.rejection_reason:
            reason = html.escape(result.rejection_reason[:300])
            lines.append(f"🚫 <b>Důvod:</b> {reason}")
        return "\n".join(lines)

    lines.append("❌ <b>Nízká hodnota</b>")

    if result.brief_summary:
        lines.append("")
        lines.append(f"💭 <b>Shrnutí:</b> {html.escape(result.brief_summary)}")

    if result.rejection_reason:
        reason = html.escape(result.rejection_reason[:300])
        lines.append(f"🚫 <b>Proč:</b> {reason}")

    return "\n".join(lines)
