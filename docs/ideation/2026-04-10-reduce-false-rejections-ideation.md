---
date: 2026-04-10
topic: reduce-false-rejections
focus: Bot rejects too many links as "low value" — should be triage tool, not quality gate
---

# Ideation: Reduce False Rejections in Triage Pipeline

## Codebase Context

**Project:** Python Telegram bot — triages links shared in Telegram, runs 3-phase Claude
analysis, creates structured Notion records.

**Root Causes Identified:**
1. Phase 2 VALUE_ASSESSMENT prompt says "critical evaluator... ignore marketing hype...
   reward concrete insights" — biases Haiku toward rejection
2. Phase 2 uses binary `has_value` boolean — `value_score` (1-5) exists in prompt output
   but is COMPLETELY IGNORED in code
3. Phase 2 failure defaults to `has_value=False` (reject) — asymmetric with Phase 1
   which defaults to neutral (score 3)
4. Content truncation: Phases 1-2 see first 3000 chars only — long articles judged on
   intro alone
5. Phase 1 credibility (score < 2 rejects) is reasonable; Phase 2 is the main bottleneck

**Pipeline:** Telegram -> fetch -> Phase 1 (credibility, Haiku) -> Phase 2 (value, Haiku,
MAIN REJECTION GATE) -> Phase 3A (full analysis, Sonnet) or Phase 3B (rejection, Haiku)
-> Notion

## Ranked Ideas

### 1. Remove Phase 2 Entirely
**Description:** Delete the value assessment gate. Phase 1 (credibility >= 2) -> Phase 3A
(Sonnet, full analysis) directly. discovery_score from Phase 3A serves as sole quality signal.
**Rationale:** Phase 2 is architectural mismatch for inclusive triage tool. Eliminates root
cause, reduces latency and API costs. Simplifies codebase.
**Downsides:** Every link hits Sonnet (higher per-call cost). Negligible at personal volume.
**Confidence:** 90%
**Complexity:** Low
**Status:** Explored -> brainstormed as docs/brainstorms/2026-04-10-remove-phase2-add-override-requirements.md

### 2. Surgical Phase 2 Recalibration (4-change bundle)
**Description:** Keep Phase 2 but: (a) rewrite prompt to "librarian/classifier", (b) wire
value_score with threshold <= 1, (c) flip failure default to True, (d) expand content to 6000 chars.
**Rationale:** Incremental approach — preserves safety net while dramatically reducing
false rejections. value_score infrastructure already exists.
**Downsides:** 4 changes vs 1. Phase 2 remains potential source of problems even after tuning.
**Confidence:** 75%
**Complexity:** Medium
**Status:** Unexplored

### 3. Merge Phase 1+2 into Single Minimal Safety Check
**Description:** One Haiku call that rejects ONLY for: empty/inaccessible content, spam,
dangerous content. No value/quality assessment. Reduces API calls from 3 to 2.
**Rationale:** Two sequential gates multiply false rejection probability. Single gate with
explicit rejection conditions enforces "classify almost everything" at prompt level.
**Downsides:** Requires redesigning two phases into one. Loss of credibility_score as
standalone metadata.
**Confidence:** 70%
**Complexity:** Medium
**Status:** Unexplored

### 4. User Override via Telegram Reply
**Description:** User replies /accept to rejection message -> bot skips gates and runs
Phase 3A. Notion record gets "Manual Override" tag.
**Rationale:** Safety net for edge cases. Creates feedback loop for prompt improvement.
**Downsides:** Treats symptom, not cause. Adds user friction per false rejection.
**Confidence:** 65%
**Complexity:** Low
**Status:** Explored -> brainstormed as docs/brainstorms/2026-04-10-remove-phase2-add-override-requirements.md

### 5. Rejection-as-Metadata (Notion "Low Signal" Tag)
**Description:** Never stop processing. Low-confidence items get "Low Signal" tag + low
discovery_score. Everything indexed. User filters in Notion.
**Rationale:** Rejection is lossy. Tagged record is auditable, searchable, correctable.
**Downsides:** Notion database grows faster. Requires schema awareness.
**Confidence:** 80%
**Complexity:** Medium
**Status:** Unexplored

## Rejection Summary

| # | Idea | Reason Rejected |
|---|------|-----------------|
| 1 | Auto-learn thresholds from overrides | Over-engineered for personal bot |
| 2 | Content-type routing (bypass Phase 2 for GitHub) | Subsumed by removing Phase 2 |
| 3 | Smart truncation (intro + conclusion) | Over-engineering when real fix is gate removal |
| 4 | Log value_score for calibration | Subsumed by removing Phase 2 |
| 5 | Surface rejection reasoning in Telegram | Minor, subsumed by root cause fix |
| 6 | Detect "bare link" pattern | Subsumed by removing Phase 2 |
| 7 | Propagate value_score to Phase 3B | Subsumed by removing Phase 2 |
| 8 | Phase 3A as sole decision point | Duplicate of #1 with extra steps |

## Session Log
- 2026-04-10: Initial ideation — 38 ideas generated across 5 agents, 5 survived
- 2026-04-10: Ideas #1 + #4 selected for brainstorming -> requirements doc created
