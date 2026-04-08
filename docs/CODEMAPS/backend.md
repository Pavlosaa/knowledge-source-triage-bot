<!-- Generated: 2026-03-02 | Updated: 2026-04-08 | Files scanned: 29 | Token estimate: ~900 -->

# Backend Module Codemap

**Files:** 20 Python modules + 1 script | **Entry:** main.py

---

## Layer 1: Entry Point & Config

### main.py (79L)
```
main() → load_config → NotionWriter + ProjectsCache
  → partial(run_pipeline_with_discovery, config, writer, projects)
  → process_queue(queue, pipeline_fn, format_results)
  → app.updater.start_polling()
```

### bot/config.py (75L)
```
@dataclass(frozen=True) Config:
  telegram_bot_token, telegram_group_id, anthropic_api_key,
  notion_api_key, notion_rnd_page_id, notion_projects_page_id,
  scrapfly_api_key?, github_token?

load_config() → Config  # fail-fast on missing vars
```

---

## Layer 2: Telegram Integration

### bot/telegram/handler.py (98L)
```
extract_urls(text) → list[str]  # regex: r"https?://[^\s]+"

class MessageHandler:
  handle(update, context) → enqueue (message, placeholder, urls)

process_queue(queue, pipeline_fn, format_fn) → None  # runs forever
  dequeue → results = pipeline_fn(url) → format_fn(results) → reply
```

### bot/telegram/formatter.py (150L)
```
format_results(results: list[AnalysisResult], original_url) → str
  └─ single result: delegate to format_result()
  └─ multi: parent + "🔍 Nalezené repozitáře (N):" + compact summaries

format_result(result, original_url) → str
  └─ dispatch: _format_duplicate / _format_valuable / _format_rejected
```

---

## Layer 3: Content Fetching

### bot/fetcher/twitter.py (~210L)
```
TweetContent: tweet_id, author_name, author_username, text, follower_count?, is_verified?, embedded_urls
ArticleContent: url, title?, author_name?, body

detect_content_type(url) → "tweet" | "article" | "unknown"
fetch_tweet(tweet_id, api_key) → TweetContent  # ScrapFly + BS4
fetch_article(url, api_key) → ArticleContent    # ScrapFly + BS4

_scrapfly_fetch(url, api_key) → str  # retry 2x on timeout/network errors
_extract_hrefs(element) → list[str]  # extract <a> href from BS4 element
_parse_tweet_html: extracts from tweetText + card.wrapper (link preview cards)
```

### bot/fetcher/github.py (79L)
```
RepoContent: owner, repo, description?, stars, language?, readme?

extract_repo_coords(url) → (owner, repo) | None  # regex
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

### bot/analyzer/pipeline.py (478L)
```
@dataclass AnalysisResult:
  url, has_value, content_type?, author?, title?, core_summary?,
  key_principles[], use_cases[], discovery_score?, tags[],
  project_recommendations[], notion_url?, brief_summary?,
  rejection_reason?, topics[], real_world_example?,
  credibility_score?, credibility_reason?, duplicate_of?,
  fetch_failed, notion_page_id?, fetched_content?

run_pipeline(url, config, writer, projects, source_context?) → AnalysisResult
  0. Dedup check → 1. Fetch → 2. Phase 1 (Haiku) → 3. Phase 2 (Haiku)
  → 4. Phase 3A (Sonnet, fetch_failed on API error) or 3B (Haiku) → 5. Notion write → 6. Cross-ref

run_pipeline_with_discovery(url, config, writer, projects) → list[AnalysisResult]
  1. run_pipeline(url) for parent
  2. extract_github_urls(fetched_content) → discovered repos
  3. For each: run_pipeline(repo, source_context=parent_context)
  4. Batch cross-reference all sibling pages
```

### bot/analyzer/extractor.py (~95L)
```
async extract_github_urls(fetched, source_url) → list[str]
  TweetContent: scan text + embedded_urls
  ArticleContent: scan body
  RepoContent: return [] (depth limit)
  Resolves t.co/bit.ly shortlinks via HTTP HEAD
  Cap: 5 repos, dedup, filter source URL, strip .git suffix
```

### bot/analyzer/json_utils.py (38L)
```
strip_markdown_json(text) → str  # extract JSON from markdown fences
```

### bot/analyzer/prompts.py (114L)
```
CREDIBILITY_SYSTEM, VALUE_ASSESSMENT_SYSTEM, FULL_ANALYSIS_SYSTEM,
CROSS_REFERENCE_SYSTEM, REJECTION_SUMMARY_SYSTEM, TOPICS[]
```

---

## Layer 5: Notion Integration

### bot/notion/writer.py (290L)
```
class NotionWriter:
  client, database_id  # exposed properties for cross-ref
  find_existing(url) → {url, date} | None  # dedup
  create_source_page(result, url) → (page_url, page_id)
  _get_or_create_database() → db_id
  _ensure_relation_property(db_id)  # "Related Sources" (F1)
  _create_record(db_id, result, url) → page dict
  _build_body(result, url) → block list
```

### bot/notion/references.py (198L)
```
find_related_sources(client, db_id, new_record, page_id, api_key) → list[page_id]
  1. Query candidates (paginated)
  2. Filter by overlap (≥2 tags OR ≥1 topic)
  3. Claude Haiku semantic verification
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

### scripts/backfill_references.py (233L)
```
python -m scripts.backfill_references
  Load all records → build tag/topic index → N×N matching
  → Claude verify → write relations → rate-limited (0.35s/call)
  Dedup: canonical pairs, skip existing relations
```
