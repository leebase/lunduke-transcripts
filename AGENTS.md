# Agent Guide: lunduke-transcripts

> **For AI agents working on the lunduke-transcripts project.**
>
> This project uses **AgentFlow** — a documentation-driven methodology for human-AI collaboration.
> Read this file first, then read `context.md` for current state.

---

## Why This System Exists

AI agents are stateless. Every new session starts from zero. These project files act as **shared memory** between you, the human, and any other AI that works on this project.

When you update `context.md` at session end, you're writing a handoff note that lets **any LLM** — Claude, ChatGPT, Gemini, Copilot — pick up exactly where you left off. Treat these updates as critical, not clerical.

---

## Your Role

You are assisting with **lunduke-transcripts**, a Python Package project.

### Key Responsibilities

- Implement features according to the product definition
- Follow the Development Loop (see below)
- Maintain documentation and context files
- Follow the guardrails and constraints defined below
- Update `context.md` and `WHERE_AM_I.md` at the end of each session

---

## Document Protocol (READ THIS FIRST)

### Start of Every Session

1. **Read this file** (`AGENTS.md`) — conventions and guardrails
2. **Read `context.md`** — current state, what's happening now, next actions
3. **Check `result-review.md`** — what was recently completed
4. **Read `sprint-plan.md`** — current sprint tasks and priorities

### End of Every Session

1. **Update `context.md`**:
   - Move completed items to "Recently Completed"
   - Update "Next Actions Queue"
   - Add new "Decisions Locked"
   - Update "Last Updated" timestamp
   - Keep "Open Questions" ≤ 5

2. **Update `WHERE_AM_I.md`** (if milestones reached):
   - Update progress against product goals
   - Update phase/sprint position
   - Note any shifts in project direction

3. **Update `result-review.md`**:
   - Add new entry at the TOP (newest first)
   - Document what was built, why it matters, how to verify

4. **Update `sprint-plan.md`**:
   - Mark completed tasks
   - Update task statuses

---

## The Development Loop

Every piece of work follows this loop. **Do not skip steps.**

```
┌──────────────────────────────────────────────────────────┐
│                   THE DEVELOPMENT LOOP                    │
│                                                          │
│   1. CODE        Write the implementation                │
│        ↓                                                 │
│   2. TEST        Run automated tests (unit, lint, build) │
│        ↓                                                 │
│   3. TEST AS LEE Run the app as the human would use it   │
│        ↓                                                 │
│   4. FIX         Fix anything that broke                 │
│        ↓                                                 │
│   5. LOOP        Repeat 2-4 until everything passes      │
│        ↓                                                 │
│   6. DOCUMENT    Update docs (see list below)            │
│        ↓                                                 │
│   7. COMMIT      Stage, commit, and push                 │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### What "Test As Lee" Means

**Test As Lee** means: run the application the way the human would actually use it, and fix every problem you find.

The goal is that when Lee sits down to test, he can **focus on functionality and product decisions** — not debugging crashes, missing imports, or broken layouts.

Specifically:

1. **Start the app** the way a user would (e.g., `npm run dev`, `python main.py`, `zig build run`)
2. **Use every feature you touched** — click buttons, submit forms, navigate pages, run commands
3. **Try the unhappy paths** — bad input, empty fields, missing data, rapid actions
4. **Check for runtime errors** — console errors, stack traces, unhandled exceptions
5. **Verify the UI looks right** (if applicable) — layout, responsiveness, readable text
6. **Test the full flow end-to-end** — not just the function you wrote, but the feature it belongs to

If anything fails, **go back to step 1 (CODE) and fix it.** Do not move on to DOCUMENT until testing is clean.

### What "Document" Means

After all tests pass, update these files as needed:

- **`context.md`** — current state and next actions
- **`WHERE_AM_I.md`** — session summary
- **`result-review.md`** — what was built and how to verify
- **`sprint-plan.md`** — task completion status
- **`architecture.md`** — if you made technical decisions
- **`README.md`** — if public-facing usage changed

### What "Commit" Means

```bash
git add -A
git commit -m "descriptive message of what changed"
git push
```

Use clear, descriptive commit messages. One commit per logical unit of work.

---

## Working Style

### Build Incrementally

Do the smallest thing that works first. Verify it. Then build the next piece on top. Do not implement large features in one shot — break them into steps and validate each one.

### Definition of Done

### Definition of Done

A task is only "done" when ALL of these are true. Copy this checklist to your final `context.md` update or PR description:

```markdown
## Done Checklist
- [ ] Mode acknowledged: worked within autonomy boundaries
- [ ] Tests pass clean (run profile-specific tests)
- [ ] Tested As Lee: ran the app as a user, fixed all issues
- [ ] Updated: context.md, WHERE_AM_I.md, result-review.md, sprint-plan.md
- [ ] Committed and pushed with descriptive message
```

---

## Document Reference

| File | When to Read | When to Update |
|------|--------------|----------------|
| `AGENTS.md` | Every session start | When conventions change |
| `context.md` | Every session start | Every session end |
| `WHERE_AM_I.md` | Every session start | When milestones reached or direction changes |
| `result-review.md` | Every session start | When work completed |
| `sprint-plan.md` | Every session start | When tasks complete |
| `sprint-review.md` | After sprints | External AI fills in review |
| `project-plan.md` | When direction unclear | Strategic changes only |
| `product-definition.md` | When scope unclear | Product changes only |
| `architecture.md` | When making tech decisions | When decisions are made |
| `feedback.md` | When given feedback | Human adds feedback |
| `backlog/schema.md` | Creating backlog items | Never (reference) |
| `backlog/template.md` | Creating backlog items | Never (copy-paste) |

### Backlog System

The `backlog/` folder uses this workflow:

```
candidates/  →  AI writes here (read-only after write)
approved/    →  Human moves items here when approved
parked/      →  Human moves items here (deferred)
implemented/ →  Builder moves items here when complete
```

**To create a backlog item**: Copy `backlog/template.md` to `backlog/candidates/BI-NNN-{kebab-title}.md` and fill in all fields.

---

## Autonomy Modes

The `Mode` field in `context.md` controls how independently you work:

| Mode | Name | Behavior |
|------|------|----------|
| **1** | Supervised | Ask before every significant action. Explain your plan, wait for approval. |
| **2** | Collaborative | Plan approach, implement with check-ins. Ask for approval on decisions, not on routine code. |
| **3** | Autonomous | Execute independently within guardrails. Report results. Only ask if blocked or if a decision has major consequences. |

**Default is Mode 2.** The human may change the mode in `context.md` at any time.

---

## Guardrails

### ✅ Allowed

- Write and modify code for lunduke-transcripts
- Create and update documentation
- Add tests for new functionality
- Research solutions to technical problems
- Update context and decision logs
- Create backlog items in `backlog/candidates/`

### ❌ Not Allowed (Without Explicit Permission)

- Add external runtime dependencies
- Make breaking changes to existing APIs
- Delete files without confirming necessity
- Skip tests or documentation updates
- Commit directly to protected branches
- Move files out of `backlog/candidates/` (human curates)

---

## Communication Style

- **Concise**: Get to the point quickly
- **Specific**: Include file paths, line numbers, exact commands
- **Actionable**: Provide clear next steps
- **Honest**: Flag concerns or blockers immediately

---

*Generated by init-agent on 2026-02-17*
