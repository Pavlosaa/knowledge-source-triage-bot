<!-- Generated: 2026-03-02 | Updated: 2026-10-13 | Files scanned: 33 | Token estimate: ~950 -->

# Backend Module Codemap

**Files:** 21 Python modules + 1 script | **Entry:** main.py

---

## Layer 1: Entry Point & Config

### main.py (87L)
```
main() → load_config → NotionWriter + ProjectsCache
  → partial(run_pipeline_with_discovery, config, writer, projects)
  → bot_data["pipeline_fn"/"format_fn"]  # DI for /accept
  → CommandHandler("accept") registered before the TEXT handler
  → process_queue(queue, pipeline_fn, format_results)
  → app.updater.start_polling()
```

### bot/config.py (83L)
```
@dataclass(frozen=True) Config:
  telegram_bot_token, telegram_group_id, anthropic_api_key,
  claude_fast_model, claude_analysis_model,   # env or defaults from claude.py
  notion_api_key, notion_rnd_page_id, notion_projects_page_id,
  scrapfly_api_key?, github_token?

load_config() → Config  # fail-fast on missing vars
```

---

## Layer 2: Telegram Integration

### bot/telegram/handler.py (177L)
```
extract_urls(text) → list[str]  # regex: r"https?://[^\s]+"

class MessageHandler:
  handle(update, context) → enqueue (message, placeholder, urls)

accept_command(update, context) → None  # /accept as reply to a rejection
  URL from original message entities → fetch failure? retry with Phase 1
  : credibility rejection → skip_credibility=True; is_override=True always

process_queue(queue, pipeline_fn, format_fn) → None  # runs forever
  dequeue → results = pipeline_fn(url) → format_fn(results) → reply
```

### bot/telegram/formatter.py (154L)
```
format_results(results: list[AnalysisResult], original_url) → str
  └─ single result: delegate to format_result()
  └─ multi: parent + "🔍 Nalezené repozitáře (N):" + compact summaries

format_result(result, original_url) → str
  └─ dispatch: _format_duplicate / _format_valuable / _format_rejected (with /accept hint)
```

---

## Layer 3: Content Fetching

### bot/fetcher/twitter.py (250L)
```
TweetContent: tweet_id, author_name, author_username, text, follower_count?, is_verified?, embedded_urls
ArticleContent: url, title?, author_name?, body

detect_content_type(url) → "tweet" | "article" | "unknown"
fetch_tweet(tweet_id, api_key) → TweetContent  # ScrapFly + BS4, card links, retry on timeout
fetch_article(url, api_key) → ArticleContent    # ScrapFly + BS4
```

### bot/fetcher/github.py (79L)
```
RepoContent: owner, repo, description?, stars, language?, readme?

extract_repo_coords(url) → (owner, repo) | None  # regex, strips .git
fetch_repo(owner, repo, token?) → RepoContent     # REST API
```

### bot/fetcher/article.py (84L) + playwright.py (60L)
```
ArticleContent: url, title?, body
PageContent: url, title?, body

fetch_article(url) → ArticleContent  # httpx+BS4, Playwright fallback
fetch_with_playwright(url) → PageContent
```

---

## Layer 4: Analysis Pipeline

### bot/analyzer/pipeline.py (481L)
```
@dataclass AnalysisResult:
  url, has_value, content_type?, author?, title?, core_summary?,
  key_principles[], use_cases[], discovery_score?, tags[],
  project_recommendations[], notion_url?, brief_summary?,
  rejection_reason?, topics[], real_world_example?,
  credibility_score?, credibility_reason?, duplicate_of?,
  fetch_failed, is_override, notion_page_id?, fetched_content?

run_pipeline(url, config, writer, projects, source_context?,
             *, skip_credibility=False, is_override=False) → AnalysisResult
  0. Dedup check → 1. Fetch → 2. Phase 1 credibility (fast model, skipped on override)
  → score < 2: Phase 3B rejection summary (fast model) → return
  → 3. Phase 3A full analysis (analysis model) → 4. Notion write → 5. Cross-ref

_call_claude(system, user, model, effort, api_key) → dict
  # MAX_TOKENS + request_options() + response_text(); 3 attempts, 2^n s backoff

run_pipeline_with_discovery(url, config, writer, projects,
                            *, skip_credibility, is_override) → list[AnalysisResult]
  1. run_pipeline(url) for parent
  2. extract_github_urls(fetched_content) → discovered repos
  3. For each: run_pipeline(repo, source_context=parent_context)
  4. Batch cross-reference all sibling pages
```

### bot/analyzer/extractor.py (110L)
```
async extract_github_urls(fetched, source_url) → list[str]  # resolves t.co/bit.ly via HEAD
  TweetContent: scan text + embedded_urls
  ArticleContent: scan body
  RepoContent: return [] (depth limit)
  Cap: 5 repos, dedup, filter source URL
```

### bot/analyzer/json_utils.py (38L)
```
strip_markdown_json(text) → str  # extract JSON from markdown fences
```

### bot/analyzer/claude.py (38L)
```
DEFAULT_FAST_MODEL = "claude-haiku-5-5"; DEFAULT_ANALYSIS_MODEL = "claude-sonnet-5-5"
MAX_TOKENS = 16_000  # ceiling; thinking tokens count against it

request_options(model, effort) → kwargs
  output_config={effort} (skipped for older models)
  + fallbacks="default" via extra_body/beta header (Sonnet/Opus 5.x)
response_text(response) → str  # joins text blocks, raises on stop_reason="refusal"
```

### bot/analyzer/prompts.py (101L)
```
CREDIBILITY_SYSTEM, FULL_ANALYSIS_SYSTEM, CROSS_REFERENCE_SYSTEM,
REJECTION_SUMMARY_SYSTEM, TOPICS[] (7)
```

---

## Layer 5: Notion Integration

### bot/notion/writer.py (294L)
```
class NotionWriter:
  client, database_id  # exposed properties for cross-ref
  find_existing(url) → {url, date} | None  # dedup
  create_source_page(result, url) → (page_url, page_id)
  _get_or_create_database() → db_id
  _ensure_relation_property(db_id)  # "Related Sources" (F1)
  _create_record(db_id, result, url) → page dict  # + "Manual Override" tag if is_override
  _build_body(result, url) → block list
```

### bot/notion/references.py (210L)
```
find_related_sources(client, db_id, new_record, page_id, api_key, model) → list[page_id]
  1. Query candidates (paginated)
  2. Filter by overlap (≥2 tags OR ≥1 topic), top 15 by score (tags×1 + topics×2)
  3. Claude semantic verification (fast model)
  4. Return verified page IDs

write_relations(client, page_id, related_ids) → None
  # Notion handles back-references automatically
```

### bot/notion/projects.py (87L)
```
class ProjectsCache:
  get_context() → str  # 24h TTL, async-safe with Lock
```

---

## Scripts

### scripts/backfill_references.py (237L)
```
python -m scripts.backfill_references
  Load all records → build tag/topic index → N×N matching
  → Claude verify (CLAUDE_FAST_MODEL) → write relations → rate-limited (0.35s/call)
  Dedup: canonical pairs, skip existing relations
```
