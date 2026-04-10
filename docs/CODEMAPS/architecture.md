<!-- Generated: 2026-03-02 | Updated: 2026-04-10 | Files scanned: 31 | Token estimate: ~750 -->

# Architecture Codemap

**Type:** Python 3.12 async application | **Entry:** main.py

---

## System Diagram

```
Telegram Group
    │ TEXT + URL          /accept (reply to rejection)
    ▼                     ▼
handler.py            accept_command()
  → asyncio.Queue       → extract URL from reply entities
  → process_queue()      → run_pipeline_with_discovery(skip_credibility?, is_override=True)
    │                     │
    ▼                     ▼
run_pipeline_with_discovery(url)
├─ run_pipeline(url) → AnalysisResult
│  ├─ Dedup check (Notion query)
│  ├─ _fetch() → fetcher routing
│  │  ├─ github.com → fetch_repo() (REST API)
│  │  ├─ x.com/status → fetch_tweet() (ScrapFly)
│  │  ├─ x.com/article → fetch_article() (ScrapFly)
│  │  └─ other → fetch_article() (httpx+BS4+Playwright)
│  ├─ Phase 1: Credibility (Haiku) — reject if score < 2
│  │  └─ Phase 3B: Rejection summary (Haiku) — on reject
│  ├─ Phase 3A: Full Analysis (Sonnet)
│  ├─ Notion Writer → create page (+ "Manual Override" tag if override)
│  └─ Cross-reference → find_related_sources() (Haiku)
│
├─ extract_github_urls(fetched_content)
├─ For each repo: run_pipeline(repo, source_context=...)
└─ Batch cross-reference siblings
    │
    ▼
format_results() → Telegram HTML reply (single or multi-record)
```

---

## Module Dependency Graph

```
main.py
├─ bot.config::load_config → Config
├─ bot.telegram.handler::{MessageHandler, accept_command, process_queue}
├─ bot.telegram.formatter::format_results
├─ telegram.ext::CommandHandler  (for /accept)
├─ bot.analyzer.pipeline::run_pipeline_with_discovery
│  ├─ bot.analyzer.extractor::extract_github_urls
│  ├─ bot.analyzer.json_utils::strip_markdown_json
│  ├─ bot.analyzer.prompts (4 system prompts)
│  ├─ bot.fetcher.{twitter, github, article, playwright}
│  ├─ bot.notion.writer::NotionWriter
│  ├─ bot.notion.references::{find_related_sources, write_relations}
│  └─ bot.notion.projects::ProjectsCache
└─ External: Telegram, Claude, Notion, ScrapFly, GitHub, Playwright
```

---

## Notion Database Schema: "AI Sources"

| Property | Type | Notes |
|----------|------|-------|
| Title | title | Czech, max 70 chars |
| Topic | multi_select | 1-3 from 6 categories |
| Discovery Score | number | 1-5 |
| Source URL | url | Canonicalized |
| Content Type | select | Tweet, X Article, GitHub, Article |
| Author | rich_text | |
| Tags | multi_select | English keywords, max 10; includes "Manual Override" for overrides |
| Date Added | date | UTC |
| Relevant Projects | multi_select | From project recommendations |
| Related Sources | relation | Self-referencing, bidirectional |

---

## Deployment

- **Host:** Oracle Cloud Free Forever (AMD x86, 1 OCPU, 12GB RAM)
- **Service:** systemd `triage-bot.service` (auto-restart)
- **CI/CD:** GitHub Actions → lint, typecheck, test, security → auto-deploy via SSH
- **Logs:** `logs/bot.log` (DEBUG), `logs/errors.log` (ERROR), both 10MB rotation
