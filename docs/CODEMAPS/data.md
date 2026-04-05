<!-- Generated: 2026-03-02 | Updated: 2026-04-04 | Files scanned: 29 | Token estimate: ~700 -->

# Data & Configuration Codemap

---

## Configuration (bot/config.py)

```python
@dataclass(frozen=True) Config:
  # Required (fail-fast at startup)
  telegram_bot_token: str
  telegram_group_id: int
  anthropic_api_key: str
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
credibility_score?, credibility_reason?, duplicate_of?, fetch_failed,
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

| Prompt | Model | Max Tokens | Output Schema |
|--------|-------|-----------|---------------|
| CREDIBILITY_SYSTEM | Haiku | 150 | `{credibility_score: 1-5, credibility_reason}` |
| VALUE_ASSESSMENT_SYSTEM | Haiku | 150 | `{has_value: bool, value_score: 1-5, rejection_reason?}` |
| FULL_ANALYSIS_SYSTEM | Sonnet | 2000 | `{title, topics[], core_summary, key_principles[], use_cases[], real_world_example, discovery_score, tags[], project_recommendations[]}` |
| REJECTION_SUMMARY_SYSTEM | Haiku | 200 | `{brief_summary?, rejection_reason}` |
| CROSS_REFERENCE_SYSTEM | Haiku | 500 | `{related: [{page_id, reason}]}` |

All text output in Czech except tags (English). Topics from 6 predefined categories.

---

## Notion Database: "AI Sources"

**Properties:**
| Name | Type | Values/Notes |
|------|------|-------------|
| Title | title | Czech, max 70 chars |
| Topic | multi_select | AI Tools & Libraries, Educational Content, Tips & Tricks, Best Practices, News & Updates, Interesting Findings |
| Discovery Score | number | 1-5 |
| Source URL | url | Canonicalized (no www, no trailing slash) |
| Content Type | select | Tweet (blue), X Article (green), GitHub (gray), Article (orange) |
| Author | rich_text | |
| Tags | multi_select | English keywords, max 10 |
| Date Added | date | UTC auto |
| Relevant Projects | multi_select | From recommendations (high/medium only, max 10) |
| Related Sources | relation | Self-referencing, dual property "Related by" |

**Page Body Blocks:**
📌 Shrnutí → 🔑 Klíčové poznatky → 💡 Využití → 🌍 Příklad z praxe → 🎯 Relevance pro projekty (toggles) → 🔗 Zdroj (bookmark)

---

## Cross-Reference Matching (references.py)

**Pre-filter:** ≥2 shared tags OR ≥1 shared topic
**Verification:** Claude Haiku semantic check — only genuine content/functional overlap
**Storage:** Notion Relation property — bidirectional (Notion handles back-refs)
**Sibling linking:** Discovery orchestrator links parent article ↔ discovered repos

---

## Context Caching (projects.py)

**ProjectsCache:** In-memory, 24h TTL, async Lock
- Fetches child pages from NOTION_PROJECTS_PAGE_ID
- Extracts project name + description (max 300 chars)
- Builds context string for Phase 3A prompt
