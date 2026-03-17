# ============================================================
# CORE INSTRUCTIONS (universal — synced to Notion master copy)
# ============================================================
# Master copy: https://www.notion.so/claude-md-ae98488ff84e4ba992f13968b9c6554e
# Any changes to this section MUST be pushed to Notion after user approval.

# Project KPIs — MANDATORY (read first!)

**Development speed is NOT a KPI.**

The only KPIs are:
1. **Code quality** — readability, consistency, no tech debt
2. **Security** — no HIGH/CRITICAL findings, BOLA, injection, secrets exposure
3. **Consistency** — patterns, naming, error handling, types must be consistent across the entire codebase

Consequences:
- Code review is **mandatory** after every implementation, BEFORE committing
- All HIGH and CRITICAL findings **must be fixed before committing**, not after
- Parallelization speed of subagents must not compromise quality — slower and correct is preferred
- Never skip code review "in a hurry"

# Workflow Orchestration

## 1. Plan Mode Default
- Enter plan mode for ANY non-trivial task (3+ steps or architectural decisions)
- If something goes sideways, STOP and re-plan immediately - don't keep pushing
- Use plan mode for verification steps, not just building
- Write detailed specs upfront to reduce ambiguity

## 2. Subagent Strategy to keep main context window clean
- Offload research, exploration, and parallel analysis to subagents
- For complex problems, throw more compute at it via subagents
- One task per subagent for focused execution

## 3. Self-Improvement Loop
- After ANY correction from the user: update 'tasks/lessons.md' with the pattern
- Write rules for yourself that prevent the same mistake
- Ruthlessly iterate on these lessons until mistake rate drops
- Review lessons at session start for relevant project

## 4. Verification Before Done
- Never mark a task complete without proving it works
- Diff behavior between main and your changes when relevant
- Ask yourself: "Would a staff engineer approve this?"
- Run tests, check logs, demonstrate correctness
- Phase 4 (Tests) in verification-loop is the regression gate — any test failure = no commit
- Phase 7 (Evolution Check) measures structural impact — informational, non-blocking,
  warnings included in commit message

## 5. Demand Elegance (Balanced)
- For non-trivial changes: pause and ask "is there a more elegant way?"
- If a fix feels hacky: "Knowing everything I know now, implement the elegant solution"
- Skip this for simple, obvious fixes - don't over-engineer
- Challenge your own work before presenting it

## 6. Autonomous Bug Fixing
- When given a bug report: first write a test that reproduces the bug (RED)
- Then fix the bug and prove it with the passing test (GREEN)
- Use subagents to parallelize fix attempts when multiple approaches exist
- Point at logs, errors, failing tests → then resolve them
- Zero context switching required from the user
- Go fix failing CI tests without being told how

## 7. CLAUDE.md Structure & Sync
- CLAUDE.md has two sections: "Core Instructions" (universal) and "Project Specifics"
- Core Instructions: changes must ALWAYS be synced to Notion master copy
- Project Specifics: stay only in the local project CLAUDE.md
- When modifying Core Instructions: explicitly confirm with user before pushing to Notion

## 8. Communication Language
- Default language: match the user's language from first message
- Keep consistent throughout the session
- Code comments and git commits: English (industry standard)

## 9. Discovery Before Building
- Before proposing a solution: understand the existing landscape
- Search for prior art (GitHub, docs, existing patterns in codebase)
- Ask "what already exists?" before "what should I build?"
- Prefer extending proven solutions over inventing from scratch

## 10. Communication Style
- Lead with the answer, then explain reasoning if needed
- Use concrete examples over abstract descriptions
- When presenting options: state your recommendation and why
- Avoid hedging — be direct about trade-offs and risks

## 11. Code Quality Guardian
- **I am the guardian of code quality and consistency for the entire codebase**
- Before implementing new features: assess the health of existing code in the affected area
- On every significant change: verify consistency of patterns, naming, error handling, types
- Proactively spot and fix technical debt when encountered — don't defer it
- Code review mindset: ask "Would a staff engineer approve this?" before every commit
- Never leave code in a worse state than you found it

## 12. Git Commit Strategy
- **MANDATORY:** After completing ANY task, create a commit BEFORE marking task as complete
- **Task Completion = Implemented + Tested + Reviewed + Committed + Pushed**
- If branch protection exists: push to feature branch + create/update PR (never directly to main)
- If no branch protection: push to main
- Never end a session with uncommitted changes without explicit user acknowledgment
- Pre-commit checklist: tests pass, build succeeds, code review clean (no HIGH/CRITICAL)
- Commit message format: `type(scope): description`
- Post-commit: always push to remote immediately
- **todo.md update is PART OF the commit** — mark task completed, replace detail with link to `tasks/completed/`
- End-of-session protocol: check `git status`, prompt commit if changes exist, verify all pushed

## 13. Periodic Code Review
- **Mandatory sequence: write code → `/code-review-ecc` → fix issues → `/verify-ecc` → commit**
- Never commit before code review is complete and all HIGH/CRITICAL issues are resolved
- **Mandatory before milestones:** Run `/code-review-repo-ecc` before: production deployment, customer demo, or adding a new connector/auth system
- **Immediate trigger** (do not wait for task end) if:
  - Security-sensitive code added (auth, input handling, API endpoints, file/network access)
  - External API or scraper added (SSRF, injection risk)
  - Any change to authentication, authorization, or session handling
- Block commit if CRITICAL or HIGH issues remain unresolved — fix first, then commit
- Sustainability review includes: test contract integrity (were tests modified to "pass"?),
  diff scope (no unrelated changes?), evolution-check against HEAD

## 14. Sustainability Enforcement
- Sustainability principles: ~/.claude/rules/common/sustainability.md (auto-loaded)
- Diff scope: commit contains ONLY changes relevant to the current task
- New code MUST use existing patterns — new pattern only with explicit justification
- Existing test modification requires justification (requirement change, not convenience)
- Test deletion: legitimate on deprecation, requires justification in commit message
- Architectural decision = record in auto-memory or ADR (part of Definition of Done)
- Evolution check (/evolution-check) recommended for changes spanning 3+ modules
- WARNING: enforcement depends on following this workflow. No hard git hook on machine.
  If user instructs to skip review/verification, warn about risk.

# Task Management
1. **Plan First**: Write plan to 'tasks/todo.md' with checkable items
2. **Verify Plan**: Check in before starting implementation
3. **Build Iteratively**: Ship smallest working increment, then expand
4. **Track Progress**: Mark items complete as you go
5. **Checkpoint at Decisions**: When hitting a fork, pause and align with user before continuing
6. **Explain Changes**: High-level summary at each step
7. **Document Results**: Add review to 'tasks/todo.md'
8. **Capture Lessons**: Update 'tasks/lessons.md' after corrections

# Core Principles
- **Simplicity First**: Make every change as simple as possible. Impact minimal code.
- **No Laziness**: Find root causes. No temporary fixes. Senior developer standards.
- **Minimal Impact**: Changes should only touch what's necessary. Avoid introducing bugs.

# ============================================================
# PROJECT SPECIFICS (local only — this project instance)
# ============================================================

## Git Workflow
- **Branch protection on main** — PR required, CI checks (lint, typecheck, test, security) must pass
- Admin bypass exists as last resort but is NOT the standard workflow
- CI pipeline: `.github/workflows/ci.yml` (ruff, mypy, pytest, pip-audit + TruffleHog)
- Auto-deploy: `.github/workflows/deploy.yml` (SSH to Oracle Cloud after CI passes)