# F2: Extrakce GitHub odkazů z článků/postů

## Context

Bot zpracovává URL sdílené přes Telegram. Pokud analyzovaný článek nebo tweet obsahuje odkazy na GitHub repozitáře, chceme je automaticky extrahovat a každé repo analyzovat jako samostatný vstup. Výsledné záznamy se propojí přes F1 cross-referencing. Zdrojový článek se použije jako kontext pro analýzu repa.

## Architecture Changes

| Change | File | Description |
|--------|------|-------------|
| New | `bot/analyzer/extractor.py` | GitHub URL extraction from fetched content |
| Modified | `bot/analyzer/pipeline.py` | `run_pipeline_with_discovery()` orchestrator; `run_pipeline()` gains `source_context` + `_depth` params |
| Modified | `bot/telegram/handler.py` | `process_queue` calls new orchestrator, handles list of results |
| Modified | `bot/telegram/formatter.py` | New `format_results()` for multiple records in one reply |
| Modified | `main.py` | Rewire to `run_pipeline_with_discovery` |
| New test | `tests/test_extractor.py` | URL extraction tests |
| New test | `tests/test_pipeline_discovery.py` | Multi-record pipeline integration tests |
| New test | `tests/test_formatter.py` | Multi-result formatting tests |

## Implementation Steps

### Step 1: GitHub URL Extraction Module

**New file: `bot/analyzer/extractor.py`**

```python
def extract_github_urls(fetched: Any, source_url: str) -> list[str]
```

- TweetContent: scan `text` + `embedded_urls` for GitHub URLs
- ArticleContent: scan `body` field
- RepoContent: return empty list (depth limit — never follow README links)
- Reuse `extract_repo_coords()` regex from `bot/fetcher/github.py`
- Reconstruct canonical URL: `https://github.com/{owner}/{repo}`
- Filter out source URL itself, deduplicate, cap at `_MAX_DISCOVERED_REPOS = 5`

### Step 2: Pipeline Extension — source_context param

**File: `bot/analyzer/pipeline.py`**

Add optional params to `run_pipeline()`:

```python
async def run_pipeline(
    url: str,
    config: Config,
    writer: NotionWriter,
    projects: ProjectsCache,
    source_context: str | None = None,
    _depth: int = 0,
) -> AnalysisResult
```

- When `source_context` is provided, prepend to Phase 3A user prompt
- `_depth=0` = top-level, `_depth=1` = discovered repo (no further extraction)
- Default `None` preserves existing behavior

### Step 3: Discovery Orchestrator

**File: `bot/analyzer/pipeline.py`**

```python
async def run_pipeline_with_discovery(
    url: str,
    config: Config,
    writer: NotionWriter,
    projects: ProjectsCache,
) -> list[AnalysisResult]
```

Logic:
1. Call `run_pipeline(url, _depth=0)` for original URL
2. If fetch_failed or duplicate → return `[result]`
3. Extract GitHub URLs from fetched content via `extract_github_urls()`
4. For each discovered URL, call `run_pipeline(url, source_context=..., _depth=1)` sequentially
5. Batch cross-reference all sibling page IDs (parent ↔ repos)
6. Return `[parent_result, *repo_results]`

**Fetched content access:** Add transient `_fetched: Any = None` field to `AnalysisResult` (set after fetch step, not serialized).

### Step 4: Source Context Builder

**File: `bot/analyzer/pipeline.py`**

```python
def _build_source_context(result: AnalysisResult) -> str
```

Returns concise context (title, core_summary, URL), truncated to ~500 chars.

### Step 5: AnalysisResult Extension

**File: `bot/analyzer/pipeline.py`**

New fields on `AnalysisResult`:
- `notion_page_id: str | None = None` — for cross-ref batch linking
- `_fetched: Any = field(default=None, repr=False)` — transient fetched content

### Step 6: Batch Sibling Cross-Reference

**Within `run_pipeline_with_discovery()`**

After all pipelines complete, collect all `page_id` values from results where `has_value=True`. For each page, write relations to all sibling pages using existing `write_relations()`. Non-blocking (try/except).

### Step 7: Telegram Formatter Update

**File: `bot/telegram/formatter.py`**

```python
def format_results(results: list[AnalysisResult], original_url: str) -> str
```

- Single result → delegate to existing `format_result()`
- Multiple results → parent result + separator + compact repo summaries
- Skip rejected/duplicate repos in summary, mention count of skipped
- Respect Telegram 4096 char limit

### Step 8: Handler Update

**File: `bot/telegram/handler.py`**

- `process_queue` calls `run_pipeline_with_discovery()` instead of `run_pipeline()`
- Returns `list[AnalysisResult]`, passes to `format_results()`

### Step 9: Main.py Rewiring

**File: `main.py`**

- Change `pipeline_fn` partial: `run_pipeline` → `run_pipeline_with_discovery`
- Change `format_fn`: `format_result` → `format_results`

### Step 10-11: Tests

**`tests/test_extractor.py`:**
- Article with 2 GitHub URLs → returns 2 canonical URLs
- Tweet with GitHub URL in `embedded_urls` → 1 URL
- RepoContent → empty list (depth limit)
- Source URL filtered out, duplicates removed, cap at 5
- Non-repo GitHub URLs filtered out

**`tests/test_pipeline_discovery.py`:**
- Article with no GitHub URLs → single-element list
- Article with 2 GitHub URLs → 3-element list (parent + 2 repos)
- Fetch failure → single failed result, no discovery
- Duplicate repo → included with `duplicate_of`, excluded from cross-ref batch
- `source_context` passed to discovered repo pipelines

**`tests/test_formatter.py`:**
- Single result → same as `format_result()`
- Multiple results → parent + repo summary section
- Rejected repos skipped in summary

## Implementation Order

| Step | Depends On | Complexity |
|------|-----------|------------|
| 1 (extractor) | — | Low |
| 10 (extractor tests) | Step 1 | Low |
| 7 (formatter) | — | Low |
| 11 (formatter tests) | Step 7 | Low |
| 5 (AnalysisResult fields) | — | Low |
| 2 (source_context param) | Step 1 | Low |
| 4 (source context builder) | — | Low |
| 3 (orchestrator) | Steps 1, 2, 4, 5 | Medium |
| 6 (sibling cross-ref) | Step 3 | Medium |
| 8 (handler) | Steps 3, 7 | Low |
| 9 (main.py) | Steps 3, 8 | Low |

Steps 1+10 and 7+11 can run in parallel (no dependencies).

## Risks & Mitigations

- **API cost:** Cap at 5 repos. Sequential processing. Dedup catches already-processed repos early.
- **Slow processing:** 5 repos × ~15s = 75s. Update Telegram placeholder with progress.
- **Depth recursion:** `_depth` param. Extraction only when `_depth == 0`.
- **Breaking change:** `run_pipeline_with_discovery()` always returns list. `format_results()` handles single-element lists via delegation.
