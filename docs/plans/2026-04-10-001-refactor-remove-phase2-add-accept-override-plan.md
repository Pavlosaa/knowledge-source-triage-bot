---
title: "refactor: Remove Phase 2 value gate, add /accept override"
type: refactor
status: completed
date: 2026-04-10
origin: docs/brainstorms/2026-04-10-remove-phase2-add-override-requirements.md
---

# refactor: Remove Phase 2 Value Gate + Add /accept Override

## Overview

Remove the Phase 2 (VALUE_ASSESSMENT) rejection gate from the 3-phase Claude analysis
pipeline and add a `/accept` Telegram reply command for overriding remaining rejections.
The bot becomes an inclusive triage/classification tool — rejection only for fetch failures
or credibility score = 1.

## Problem Statement / Motivation

The bot rejects too many links as "low value" due to Phase 2's adversarial prompt framing
("critical evaluator... ignore marketing hype"), binary `has_value` gate (ignoring the
already-computed `value_score`), and rejection-default error handling. The user sends links
personally with intent to catalog them — the bot should classify, not gatekeep.
(see origin: docs/brainstorms/2026-04-10-remove-phase2-add-override-requirements.md)

## Proposed Solution

1. **Delete Phase 2 entirely** — Phase 1 pass flows directly to Phase 3A
2. **Wire Phase 3B to Phase 1 rejections** — credibility rejections get a summary
3. **Add `/accept` command** — reply-based override for remaining rejections
4. **Mark overrides in Notion** — "Manual Override" tag for audit

### New Pipeline Flow

```
Telegram → dedup → fetch → Phase 1 (credibility, Haiku)
                              │
                    ┌─────────┴──────────┐
                    │ score >= 2         │ score < 2
                    ▼                    ▼
               Phase 3A            Phase 3B (summary)
            (Sonnet, full)              │
                    │                   ▼
                    ▼            Rejection message
               Notion write      (with /accept hint)
                    │                   │
                    ▼            /accept reply?
            Telegram reply              │
                                       ▼
                                Phase 3A (override)
                                       │
                                       ▼
                                Notion write
                                ("Manual Override" tag)
```

## Technical Considerations

### Architecture Impacts

- Phase 2 removal simplifies pipeline from 4 Claude calls (happy path: 3) to 2 Claude
  calls. Cost per link increases slightly (every link hits Sonnet) but volume is low.
- `/accept` handler introduces the first `CommandHandler` in the bot — currently only
  a `MessageHandler` with `filters.TEXT` exists in `main.py`.
- `run_pipeline` gains two optional parameters: `skip_credibility` and `is_override`.
  `run_pipeline_with_discovery` threads these through for the parent URL only.

### Critical Implementation Detail: Phase 3B Wiring

**Current behavior (bug):** Phase 1 rejection at `pipeline.py:153-156` returns early
WITHOUT calling Phase 3B. Phase 3B currently only runs for Phase 2 rejections.

**Required change:** After Phase 2 removal, Phase 3B must run on Phase 1 rejections to
produce `brief_summary` and `rejection_reason` for the Telegram rejection message.
Without this, credibility rejections show no context.

### URL Extraction for /accept

The bot sends rejection messages with `parse_mode="HTML"` containing
`<a href="{url}">Původní zdroj</a>`. When reading back via `reply_to_message`:
- Use `reply_to_message.entities` — find entity with `type == "text_link"`
- Read `entity.url` for the original URL
- Do NOT parse plain text — HTML tags are stripped from `message.text`

### Override Pipeline Calls

| Override type | `skip_credibility` | `is_override` | Phase 1 | Discovery |
|---------------|--------------------|---------------|---------|-----------|
| Credibility rejection | `True` | `True` | Skipped | Yes |
| Fetch failure | `False` | `True` | Runs | Yes |

Both use `run_pipeline_with_discovery` for consistent behavior with normal submissions.

## System-Wide Impact

- **Interaction graph:** `/accept` command → extract URL from reply → call
  `run_pipeline_with_discovery(url, skip_credibility=..., is_override=True)` →
  Phase 3A → Notion write (with "Manual Override" tag) → Telegram reply
- **Error propagation:** Phase 3A failure on override follows existing pattern
  (`fetch_failed=True` + clear error message, per Issue #5 fix at `pipeline.py:208-211`).
  User sees error, can retry again.
- **State lifecycle risks:** Dedup check inside `run_pipeline` prevents duplicate Notion
  records if user sends /accept on an already-processed URL. Race condition with concurrent
  submissions is mitigated by dedup.
- **API surface parity:** `run_pipeline_with_discovery` passes override params for parent
  URL only — discovered repos use default (no skip, no override tag).

## Acceptance Criteria

- [ ] Links previously rejected as "low value" now produce full Notion records (R1)
- [ ] Phase 3A `discovery_score` is the sole quality signal in Notion (R2)
- [ ] Credibility rejections (score < 2) show `brief_summary` from Phase 3B (R3)
- [ ] `/accept` reply on credibility rejection creates Notion record (R4)
- [ ] `/accept` reply on fetch failure retries fetch and processes if successful (R4)
- [ ] Overridden Notion records have "Manual Override" tag (R5)
- [ ] Rejection messages include `/accept` hint text (R6)
- [ ] Phase 1 credibility gate unchanged — threshold < 2, neutral on failure (R7)
- [ ] `VALUE_ASSESSMENT_SYSTEM` prompt deleted, Phase 2 code removed (R8)
- [ ] `_PHASE12_CONTENT_LIMIT` renamed to `_PHASE1_CONTENT_LIMIT` (R8)
- [ ] All existing tests pass, new tests for pipeline flow and /accept handler
- [ ] Issue #2 (F2 discovery broken by low-value rejection) resolved as side effect

## Implementation Phases

### Phase 1: Pipeline Surgery — Remove Phase 2, Wire Phase 3B

**Files:** `bot/analyzer/pipeline.py`, `bot/analyzer/prompts.py`

**Tasks:**

1. **Delete `VALUE_ASSESSMENT_SYSTEM`** from `prompts.py:29-42`
2. **Remove Phase 2 import** from `pipeline.py:16-21` (remove `VALUE_ASSESSMENT_SYSTEM`)
3. **Delete Phase 2 block** at `pipeline.py:158-173`:
   - Remove the `_call_claude` call with `VALUE_ASSESSMENT_SYSTEM`
   - Remove `has_value` / `value_score` / `phase2_rejection` variable assignments
   - Remove `if not has_value:` branching at line 174
4. **Move Phase 3B to run after Phase 1 rejection** — currently `pipeline.py:153-156`
   returns early without Phase 3B. Change to: on credibility < threshold, run Phase 3B
   to populate `brief_summary` and `rejection_reason`, THEN return.
5. **Rename constant** `_PHASE12_CONTENT_LIMIT` → `_PHASE1_CONTENT_LIMIT` at line 41
6. **Verify Phase 3A prompt** — read `FULL_ANALYSIS_SYSTEM` (`prompts.py:44-84`).
   Check if `discovery_score` description needs adjustment to also capture general
   content value. Current description focuses on "relevance to knowledge base" — may
   need broadening to "value and relevance."

**Resulting flow:**
```
Phase 1 pass (score >= 2) → Phase 3A → Notion
Phase 1 fail (score < 2)  → Phase 3B → return rejection
Phase 1 error             → default score 3 → Phase 3A → Notion
```

### Phase 2: Override Infrastructure

**Files:** `bot/analyzer/pipeline.py`, `bot/notion/writer.py`

**Tasks:**

1. **Add `is_override` field** to `AnalysisResult` dataclass:
   ```python
   is_override: bool = False  # True when created via /accept override
   ```

2. **Add parameters to `run_pipeline`**:
   ```python
   async def run_pipeline(
       url: str, ...,
       skip_credibility: bool = False,
       is_override: bool = False,
   ) -> AnalysisResult:
   ```
   - When `skip_credibility=True`: skip Phase 1 check entirely (go to Phase 3A)
   - When `is_override=True`: set `result.is_override = True` after creating result

3. **Thread params through `run_pipeline_with_discovery`**:
   ```python
   async def run_pipeline_with_discovery(
       url: str, ...,
       skip_credibility: bool = False,
       is_override: bool = False,
   ) -> list[AnalysisResult]:
   ```
   Pass `skip_credibility` and `is_override` only to the parent `run_pipeline` call.
   Discovered repos use defaults.

4. **Update Notion writer** in `writer.py:_create_record` (~line 209):
   - If `result.is_override` and tags exist, append `"Manual Override"` to the tags list
   - If `result.is_override` and no tags, set `tags = ["Manual Override"]`

### Phase 3: /accept Command Handler

**Files:** `bot/telegram/handler.py`, `main.py`

**Tasks:**

1. **Add `accept_command` handler** to `handler.py`:
   - Check `update.message.reply_to_message` exists
   - Verify replied-to message is from the bot (`from_user.is_bot`)
   - Extract URL from `reply_to_message.entities` (find `text_link` entity, read `.url`)
   - If no URL found, reply with error message
   - Determine override type from rejection message text:
     - Contains "nedostupný" or "Chyba" → fetch failure → `skip_credibility=False`
     - Contains "věrohodnost" or "Nízká hodnota" → credibility → `skip_credibility=True`
   - Send placeholder message ("Přehodnocuji...")
   - Call `run_pipeline_with_discovery(url, skip_credibility=..., is_override=True)`
   - Format results and send reply (delete placeholder)

2. **Register handler in `main.py`**:
   - Add `CommandHandler("accept", handler.accept_command)` BEFORE the TEXT handler
   - The handler needs access to: `config`, `writer`, `projects`, `format_fn`
   - Follow the existing pattern for dependency injection (the accept handler receives
     these as a closure or class attributes)

3. **Error handling in /accept**:
   - No `reply_to_message` → "Odpověz na zprávu s odmítnutým zdrojem."
   - No URL found in reply → "Nepodařilo se najít URL v původní zprávě."
   - Pipeline failure → standard error formatting (fetch_failed pattern)
   - Dedup hit (already processed) → "Tento zdroj už byl zpracován." + Notion link

### Phase 4: Formatter Updates

**Files:** `bot/telegram/formatter.py`

**Tasks:**

1. **Add `/accept` hint** to `_format_rejected()` at lines 126-150:
   - After rejection reason, add:
     `"\n\n💡 <i>Odpověz /accept pro vynucené zpracování</i>"`
   - Add to BOTH branches: fetch failure (line 132-138) and credibility rejection (140-149)

2. **Update rejection label** (optional): Currently says "Nízká hodnota" for all
   rejections. After Phase 2 removal, only credibility rejections remain — consider
   changing to "Nízká věrohodnost" for clarity.

### Phase 5: Tests

**Files:** `tests/`

**No existing Phase 2 tests to remove** — Phase 2 was untested.

**New tests needed:**

1. **`tests/test_pipeline.py`** (NEW) — pipeline integration tests:
   - Phase 1 pass → Phase 3A → Notion write (happy path)
   - Phase 1 fail (credibility < 2) → Phase 3B → rejection with `brief_summary`
   - Phase 1 error → default score 3 → Phase 3A (graceful degradation)
   - Phase 3A error → `fetch_failed=True` (existing Issue #5 behavior preserved)
   - Override: `skip_credibility=True` → skips Phase 1, runs Phase 3A
   - Override: `is_override=True` → result has `is_override=True`
   - Mock `_call_claude` and `writer` — test pipeline logic, not API calls

2. **`tests/test_formatter.py`** — update existing:
   - Rejection messages include `/accept` hint text
   - Both fetch failure and credibility rejection branches show the hint

3. **`tests/test_accept_handler.py`** (NEW) — /accept command tests:
   - Reply to bot's rejection message → extract URL → pipeline called
   - Reply to non-bot message → error response
   - No reply_to_message → error response
   - No URL in reply message → error response
   - Fetch failure override → `skip_credibility=False, is_override=True`
   - Credibility override → `skip_credibility=True, is_override=True`
   - Mock pipeline — test handler logic

4. **`tests/test_writer.py`** (NEW or extend existing) — verify:
   - `is_override=True` → "Manual Override" appended to tags

### Phase 6: Verify & Cleanup

1. Run full test suite: `pytest tests/ -v`
2. Run linter + typecheck: `ruff check . && mypy .`
3. Verify Issue #2 (F2 discovery broken by low-value rejection) is resolved
4. Manual smoke test: send a link that was previously rejected as "low value"
5. Manual smoke test: trigger Phase 1 rejection, reply /accept, verify Notion record

## Dependencies & Risks

- **python-telegram-bot v21 `CommandHandler`** — well-documented, no risk
- **Notion `multi_select` tags** — "Manual Override" auto-creates on first use, no schema
  change needed (see origin: Dependencies / Assumptions)
- **Phase 3A cost increase** — every link now hits Sonnet. At personal volume (~tens/day),
  cost difference is negligible (~$0.01-0.05 per link)
- **Phase 3B wiring is the hidden critical path** — without this change, credibility
  rejections show no context. Easy to miss because Phase 3B "already exists."

## Success Metrics

- Zero false "low value" rejections (only credibility and fetch failure rejections remain)
- /accept override produces Notion records with correct tags
- Pipeline processes faster (one fewer LLM call per link)

## Sources & References

### Origin

- **Origin document:** [docs/brainstorms/2026-04-10-remove-phase2-add-override-requirements.md](docs/brainstorms/2026-04-10-remove-phase2-add-override-requirements.md) — Key decisions carried forward: (1) Remove Phase 2 entirely, not recalibrate; (2) Reply-based /accept only, no preemptive prefix; (3) Phase 1 preserved as anti-spam gate.

### Internal References

- Pipeline: `bot/analyzer/pipeline.py` — Phase 2 block at lines 158-191
- Prompts: `bot/analyzer/prompts.py` — `VALUE_ASSESSMENT_SYSTEM` at lines 29-42
- Handler: `bot/telegram/handler.py` — message handling, queue architecture
- Formatter: `bot/telegram/formatter.py` — `_format_rejected()` at lines 126-150
- Writer: `bot/notion/writer.py` — `_create_record()` tags at line 209-210
- Main: `main.py` — handler registration at lines 46-51
- Issue #5 fix: `pipeline.py:208-211` — Phase 3A error → `fetch_failed=True`
- Issue #2: `tasks/ISSUES.md:90-92` — F2 discovery broken by low-value rejection

### Ideation

- [docs/ideation/2026-04-10-reduce-false-rejections-ideation.md](docs/ideation/2026-04-10-reduce-false-rejections-ideation.md) — 38 ideas generated, 5 survived, #1 + #4 selected
