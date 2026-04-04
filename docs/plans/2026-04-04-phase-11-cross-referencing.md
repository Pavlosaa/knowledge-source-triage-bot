# Phase 11: Cross-referencing between records

## Context

The Knowledge Source Triage Bot stores analyzed sources in a Notion "AI Sources" database. Currently each record is isolated — no links between related entries. The user wants automatic N:N cross-referencing: when a new record is created, find existing records with content/functional overlap and link them bidirectionally. Plus a one-time backfill for existing records.

**User decisions:**
- Matching: Hybrid (tags/topics filter first, then Claude semantic verification)
- Storage: Notion Relation property (self-referencing, bidirectional)
- Trigger: Automatic on every new record + backfill script

## Implementation Plan

### Step 1: Add Relation property to DB schema

**File: `bot/notion/writer.py`**

- Add `_ensure_relation_property(db_id)` method — calls `databases.update()` to add "Related Sources" relation property with `database_id` = self (same DB), `synced_property_name = "Related by"`. Idempotent (Notion ignores if property already exists).
- Call it from `_get_or_create_database()` after finding/creating DB.
- Do NOT add to `_create_database()` initial properties (self-referencing requires DB to exist first).

### Step 2: Create references module

**New file: `bot/notion/references.py`**

```
async def find_related_sources(client, db_id, new_record: AnalysisResult, new_page_id: str) -> list[str]
```

Logic:
1. **Query candidates** — fetch all records from DB (paginated, `databases.query()`), extract their tags, topics, title, core_summary, page_id
2. **Filter by overlap** — keep candidates with >= 2 shared tags OR >= 1 shared topic with new record
3. **If no candidates** → return empty list
4. **Claude verification** (Haiku) — send new record summary + candidate summaries, ask Claude to return list of genuinely related page IDs with brief reason
5. **Return** list of related page IDs

```
async def write_relations(client, new_page_id: str, related_page_ids: list[str]) -> None
```

- Update new page's "Related Sources" relation with related_page_ids
- Notion's synced relation handles back-references automatically (no manual update needed)

### Step 3: Add Claude prompt for semantic matching

**File: `bot/analyzer/prompts.py`**

Add `CROSS_REFERENCE_SYSTEM` prompt:
- Input: new record (title, summary, tags, topics) + list of candidates (id, title, summary, tags)
- Output: JSON list of `{"page_id": "...", "reason": "..."}` for genuinely related records
- Rules: only include records with real content/functional overlap, not just superficial tag matches

### Step 4: Integrate into pipeline

**File: `bot/analyzer/pipeline.py`**

After step 6 (Notion page creation), add step 7:
```python
# --- 7. Cross-reference related sources ---
try:
    related_ids = await find_related_sources(
        writer._client, writer._database_id, result, page_id
    )
    if related_ids:
        await write_relations(writer._client, page_id, related_ids)
        logger.info(f"Cross-referenced {len(related_ids)} related sources")
except Exception as exc:
    logger.warning(f"Cross-referencing failed: {exc}")
```

Need to extract `page_id` from the created page (modify `create_source_page` to return both URL and page ID).

### Step 5: Backfill script

**New file: `scripts/backfill_references.py`**

Standalone async script:
1. Load config (API keys from env)
2. Query all records from AI Sources DB
3. For each record, run `find_related_sources()` against all other records
4. Optimize: build tag/topic index once, avoid duplicate pair checks (if A→B found, skip B→A)
5. Rate-limit Notion API calls (max 3/sec → add `asyncio.sleep(0.35)` between calls)
6. Log progress: `Processing record {i}/{total}: {title} → {n} relations found`

Run: `python -m scripts.backfill_references`

### Step 6: Tests

**File: `tests/test_references.py`**

- Test candidate filtering (tag/topic overlap logic)
- Test Claude prompt construction
- Test relation writing (mocked Notion client)
- Test backfill dedup (no duplicate pairs)

## Key Files to Modify

| File | Change |
|------|--------|
| `bot/notion/writer.py` | Add `_ensure_relation_property()`, modify `create_source_page()` to return page_id |
| `bot/notion/references.py` | **NEW** — cross-referencing logic |
| `bot/analyzer/prompts.py` | Add `CROSS_REFERENCE_SYSTEM` prompt |
| `bot/analyzer/pipeline.py` | Add step 7 after Notion write |
| `scripts/backfill_references.py` | **NEW** — one-time backfill |
| `tests/test_references.py` | **NEW** — unit tests |

## Reuse Existing Patterns

- `_call_claude()` from `pipeline.py` for Claude Haiku call in references.py
- `NotionWriter._client` (AsyncClient) for all Notion API calls
- `_strip_markdown_json()` from `pipeline.py` for parsing Claude response
- Existing `_HAIKU` model constant from pipeline.py

## Verification

1. **Unit tests**: `pytest tests/test_references.py`
2. **Manual test**: Send a URL to the bot via Telegram that clearly relates to an existing record → check Notion that "Related Sources" relation appears on both records
3. **Backfill test**: Run `python -m scripts.backfill_references` on existing DB → verify relations created, no duplicates
4. **CI**: Existing CI pipeline (ruff, mypy, pytest) catches lint/type/test issues

## Open Question

Tag-based pre-filtering: je potřeba ověřit aktuální distribuci tagů v Notion DB. Pokud jsou tagy dostatečně specifické, filtr "2+ shared tags OR 1 shared topic" by měl fungovat. Pokud ne, zvážit frequency-based filtering nebo čistě sémantický přístup přes Claude.
