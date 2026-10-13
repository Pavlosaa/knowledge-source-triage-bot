<!-- Generated: 2026-03-02 | Updated: 2026-10-13 | Files scanned: 33 | Token estimate: ~750 -->

# Architecture Codemap

**Type:** Python 3.12 async application | **Entry:** main.py

---

## System Diagram

```
Telegram Group
    │ TEXT + URL
    ▼
handler.py → asyncio.Queue → process_queue()
(/accept reply → accept_command() → pipeline with skip_credibility / is_override)
    │
    ▼
run_pipeline_with_discovery(url)          ← F2
├─ run_pipeline(url) → AnalysisResult
│  ├─ Dedup check (Notion query)
│  ├─ _fetch() → fetcher routing
│  │  ├─ github.com → fetch_repo() (REST API)
│  │  ├─ x.com/status → fetch_tweet() (ScrapFly)
│  │  ├─ x.com/article → fetch_article() (ScrapFly)
│  │  └─ other → fetch_article() (httpx+BS4+Playwright)
│  ├─ Phase 1: Credibility (fast model) — skipped on /accept override
│  ├─ score < 2 → Phase 3B: Rejection summary (fast model) → return
│  ├─ Phase 3A: Full Analysis (analysis model)
│  ├─ Notion Writer → create page
│  └─ Cross-reference → find_related_sources() (fast model)  ← F1
│
├─ extract_github_urls(fetched_content)   ← F2
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
├─ bot.telegram.handler::{MessageHandler, process_queue}
├─ bot.telegram.formatter::format_results
├─ bot.analyzer.pipeline::run_pipeline_with_discovery
│  ├─ bot.analyzer.extractor::extract_github_urls
│  ├─ bot.analyzer.json_utils::strip_markdown_json
│  ├─ bot.analyzer.claude::{request_options, response_text, MAX_TOKENS}
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
| Topic | multi_select | 1-3 from 7 categories |
| Discovery Score | number | 1-5 |
| Source URL | url | Canonicalized |
| Content Type | select | Tweet, X Article, GitHub, Article |
| Author | rich_text | |
| Tags | multi_select | English keywords, max 10 (+ "Manual Override" on /accept) |
| Date Added | date | UTC |
| Relevant Projects | multi_select | From project recommendations |
| Related Sources | relation | Self-referencing, bidirectional (F1) |

---

## Deployment

- **Host:** Oracle Cloud VM `reti-apps-rebuild` (VM.Standard.E5.Flex, 1 OCPU / 12 GB, eu-frankfurt-1), reserved public IP `89.168.123.102` (since 2026-06-20 rebuild). Shared with other apps; VM infra is managed in the `Pavlosaa/oracle-vm-devops` repo.
- **Service:** systemd `triage-bot.service` (auto-restart)
- **CI/CD:** GitHub Actions → lint, typecheck, test, security → auto-deploy via SSH (`DEPLOY_HOST` = the reserved IP), manual deploy via `workflow_dispatch`
- **Logs:** `logs/bot.log` (DEBUG), `logs/errors.log` (ERROR), both 10MB rotation
