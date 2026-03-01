# ============================================================
# CORE INSTRUCTIONS (universal — synced to Notion master copy)
# ============================================================
# Master copy: https://www.notion.so/Claude-Code-300295e74c248063a68bcde2f242a10f
# Any changes to this section MUST be pushed to Notion after user approval.

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

## 5. Demand Elegance (Balanced)
- For non-trivial changes: pause and ask "is there a more elegant way?"
- If a fix feels hacky: "Knowing everything I know now, implement the elegant solution"
- Skip this for simple, obvious fixes - don't over-engineer
- Challenge your own work before presenting it

## 6. Autonomous Bug Fixing
- When given a bug report: just fix it. Don't ask for hand-holding
- Point at logs, errors, failing tests -> then resolve them
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

## 11. Git Commit Strategy
- **MANDATORY:** After completing ANY task, create a commit BEFORE marking task as complete
- **Task Completion = Implemented + Tested + Committed + Pushed**
- Never end a session with uncommitted changes without explicit user acknowledgment
- Pre-commit checklist: tests pass, TypeScript compiles, no console.errors
- Commit message format: `type(scope): description` with task number
- Post-commit: always push to remote immediately
- End-of-session protocol: check `git status`, prompt commit if changes exist, verify all pushed

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