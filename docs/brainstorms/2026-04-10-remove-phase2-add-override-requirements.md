---
date: 2026-04-10
topic: remove-phase2-add-override
---

# Remove Phase 2 Value Gate + Add Override Mechanism

## Problem Frame

The bot rejects too many links as "low value." The user shares links personally with
good reason — the bot should classify and index almost everything. Current Phase 2
(VALUE_ASSESSMENT) uses a "critical evaluator" prompt with a binary `has_value` gate
that biases Haiku toward rejection. The `value_score` (1-5) is computed but completely
ignored in code. Phase 2 failure defaults to rejection (asymmetric with Phase 1).

The bot should be an **inclusive triage/classification tool**, not a quality gate.
Rejection should only occur for: fetch failure, empty/inaccessible content, or
clearly spam/fake sources (Phase 1 credibility < 2).

## Requirements

- R1. **Remove Phase 2 (VALUE_ASSESSMENT) entirely.** No value assessment gate in the
  pipeline. After Phase 1 passes, processing goes directly to Phase 3A (full analysis).
  Phase 2 prompt, parsing logic, and the `has_value` branching are deleted.

- R2. **Absorb value scoring into Phase 3A.** Phase 3A (Sonnet, full analysis) already
  produces `discovery_score` (1-5). This becomes the sole quality/value signal. No
  additional `value_score` field is needed — `discovery_score` already captures relevance
  to the knowledge base. Verify the Phase 3A prompt does not need adjustment to also
  assess general content value (not just "discovery relevance").

- R3. **Phase 3B runs only on Phase 1 rejection.** Phase 3B (rejection summary) still
  generates `brief_summary` and `rejection_reason` for Phase 1 rejections
  (credibility < 2). It no longer runs for value-based rejections (those don't exist).

- R4. **Add `/accept` override via Telegram reply.** When the bot sends a rejection
  message (credibility rejection or fetch failure), the user can reply with `/accept`
  to force reprocessing:
  - On **credibility rejection**: skip Phase 1, go directly to Phase 3A.
  - On **fetch failure**: retry the fetch. If fetch succeeds, run Phase 3A. If fetch
    fails again, report the error.

- R5. **Mark overridden records in Notion.** Notion records created via `/accept`
  override include an indicator (e.g., tag "Manual Override" or a property) so the
  user can audit overridden items.

- R6. **Update Telegram rejection message format.** Rejection messages must include
  a hint that the user can reply with `/accept` to force processing.
  Example: `❌ Nízká věrohodnost (1/5) — odpověz /accept pro vynucené zpracování`

- R7. **Phase 1 credibility gate remains unchanged.** Threshold stays at `< 2`
  (only score = 1 rejects). Default on Phase 1 failure stays neutral (score = 3).
  This is the only automated rejection gate in the pipeline.

- R8. **Clean up Phase 2 artifacts.** Remove:
  - `VALUE_ASSESSMENT_SYSTEM` prompt from `prompts.py`
  - Phase 2 parsing and branching logic from `pipeline.py`
  - `_CREDIBILITY_REJECT_THRESHOLD` constant stays (used by Phase 1)
  - Any Phase 2-specific tests

## Success Criteria

- Links that were previously rejected as "low value" (like the DESIGN.md example)
  now produce full Notion records with topics, tags, and discovery_score.
- The only automated rejection reasons are: fetch failure, empty content, or
  credibility score = 1.
- `/accept` reply to a rejection message triggers reprocessing and creates
  a Notion record (when content is accessible).
- Existing tests pass (with Phase 2 tests removed/updated). No regression
  in Phase 1 or Phase 3A behavior.

## Scope Boundaries

- **In scope:** Phase 2 removal, Phase 3A prompt review, /accept override, Telegram
  message format updates, test updates.
- **Out of scope:** Changes to Phase 1 credibility logic, Notion schema changes
  (beyond adding override indicator), new content type fetchers, auto-learning
  thresholds.
- **Not changing:** Phase 1 credibility check, Phase 3A full analysis (beyond prompt
  review), Notion writer, dedup logic, fetcher logic.

## Key Decisions

- **Remove Phase 2 vs. recalibrate:** Remove entirely. Value scoring moves to Phase 3A
  which already produces `discovery_score` with Sonnet on full content — strictly
  superior to Haiku on 3000 chars.
- **Override mechanism:** Reply-based (`/accept`) only, no preemptive prefix. Simpler
  UX, contextual (user sees the rejection first).
- **Phase 1 preserved:** Lightweight anti-spam gate (credibility < 2) stays. Protects
  against edge cases without blocking legitimate content.

## Dependencies / Assumptions

- Phase 3A `discovery_score` is sufficient as the sole value signal — no need for
  a separate value_score field.
- `/accept` reply detection requires the bot to track which rejection message
  corresponds to which URL (message reply context in python-telegram-bot v21).
- Notion "Manual Override" indicator can be implemented as a tag without schema changes.

## Outstanding Questions

### Deferred to Planning
- [Affects R2][Needs research] Does Phase 3A's `discovery_score` prompt need adjustment
  to also assess general content value, or does "relevance to knowledge base" already
  cover that?
- [Affects R4][Technical] How to map a Telegram reply to the original URL — store
  URL in message metadata, or parse it from the original rejection message?
- [Affects R5][Technical] Best way to add "Manual Override" indicator to Notion record —
  existing Tags property, or new checkbox property?
- [Affects R8][Technical] Identify all Phase 2-specific test cases that need removal
  vs. adaptation.

## Next Steps

-> `/ce:plan` for structured implementation planning
