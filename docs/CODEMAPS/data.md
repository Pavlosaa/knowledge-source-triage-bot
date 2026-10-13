<!-- Generated: 2026-03-02 | Updated: 2026-10-13 | Files scanned: 33 | Token estimate: ~700 -->

# Data & Configuration Codemap

---

## Configuration (bot/config.py)

```python
@dataclass(frozen=True) Config:
  # Required (fail-fast at startup)
  telegram_bot_token: str
  telegram_group_id: int
  anthropic_api_key: str
  claude_fast_model: str         # CLAUDE_FAST_MODEL, default claude-haiku-5-5
  claude_analysis_model: str     # CLAUDE_ANALYSIS_MODEL, default claude-sonnet-5-5
  notion_api_key: str
  notion_rnd_page_id: str
  notion_projects_page_id: str
  # Optional
  scrapfly_api_key: str | None   # X.com fetching
  github_token: str | None       # Higher rate limit
```

---

## Core Data Structures

### AnalysisResult (pipeline.py)
```
url, has_value, content_type?, author?,
title?, core_summary?, key_principles[], use_cases[],
discovery_score?, tags[], project_recommendations[], notion_url?,
brief_summary?, rejection_reason?, topics[], real_world_example?,
credibility_score?, credibility_reason?, duplicate_of?, fetch_failed, is_override,
notion_page_id?, fetched_content? (transient)
```

### Fetcher Types
```
TweetContent:   tweet_id, author_name, author_username, text, follower_count?, is_verified?, embedded_urls[]
ArticleContent: url, title?, author_name?, body  (twitter.py version)
ArticleContent: url, title?, body                (article.py version)
RepoContent:    owner, repo, description?, stars, language?, readme?
PageContent:    url, title?, body                (playwright.py)
```

---

## Claude Prompts (prompts.py)

| Prompt | Model | Effort | Output Schema |
|--------|-------|--------|---------------|
| CREDIBILITY_SYSTEM | fast (Haiku 5.5) | low | `{credibility_score: 1-5, credibility_reason}` — score < 2 rejects |
| FULL_ANALYSIS_SYSTEM | analysis (Sonnet 5.5) | medium | `{title, topics[], core_summary, key_principles[], use_cases[], real_world_example, discovery_score, tags[], project_recommendations[]}` |
| REJECTION_SUMMARY_SYSTEM | fast (Haiku 5.5) | low | `{brief_summary?, rejection_reason}` |
| CROSS_REFERENCE_SYSTEM | fast (Haiku 5.5) | low | `{related: [{page_id, reason}]}` |

`max_tokens` is 16 000 for all calls (a ceiling — thinking tokens count against it). Models are set via `CLAUDE_FAST_MODEL` / `CLAUDE_ANALYSIS_MODEL`.

All text output in Czech except tags (English). Topics from 7 predefined categories (`TOPICS` in prompts.py).

---

## Notion Database: "AI Sources"

**Properties:**
| Name | Type | Values/Notes |
|------|------|-------------|
| Title | title | Czech, max 70 chars |
| Topic | multi_select | AI Tools & Libraries, Tutorials, Educational Content, Tips & Tricks, Best Practices, News & Updates, Interesting Findings |
| Discovery Score | number | 1-5 |
| Source URL | url | Canonicalized (no www, no trailing slash) |
| Content Type | select | Tweet (blue), X Article (green), GitHub (gray), Article (orange) |
| Author | rich_text | |
| Tags | multi_select | English keywords, max 10 (+ "Manual Override" on /accept) |
| Date Added | date | UTC auto |
| Relevant Projects | multi_select | From recommendations (high/medium only, max 10) |
| Related Sources | relation | Self-referencing, dual property "Related by" |

**Page Body Blocks:**
📌 Shrnutí → 🔑 Klíčové poznatky → 💡 Využití → 🌍 Příklad z praxe → 🎯 Relevance pro projekty (toggles) → 🔗 Zdroj (bookmark)

---

## Cross-Reference Matching (references.py)

**Pre-filter:** ≥2 shared tags OR ≥1 shared topic, top 15 by overlap score (tags×1 + topics×2)
**Verification:** Claude semantic check (fast model) — only genuine content/functional overlap
**Storage:** Notion Relation property — bidirectional (Notion handles back-refs)
**Sibling linking:** Discovery orchestrator links parent article ↔ discovered repos

---

## Context Caching (projects.py)

**ProjectsCache:** In-memory, 24h TTL, async Lock
- Fetches child pages from NOTION_PROJECTS_PAGE_ID
- Extracts project name + description (max 300 chars)
- Builds context string for Phase 3A prompt
