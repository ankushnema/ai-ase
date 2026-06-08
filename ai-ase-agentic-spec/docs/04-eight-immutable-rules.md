# The 8 Immutable Rules

**Read time:** 4 minutes.

Eight rules. Non-negotiable. Injected by the governance kernel on every turn so no conversation can drift far enough to forget them.

The values are *why*. These rules are *how*.

---

## The 8 rules

| # | Rule | One-line meaning |
|---|---|---|
| **1** | **SESSION LOG** | A session log exists before any work. Check → Create → Resume. |
| **2** | **PHASE GATES** | Never auto-advance phases. Stop and ask. Silence is not approval. |
| **3** | **CODE REVIEW GATE** | High-impact change? Show the plan, get approval, *then* edit. |
| **4** | **SCOPE DISCIPLINE** | Do only what was asked. Notice something else? Mention it; don't fix it. |
| **5** | **READ-ONLY VERBS** | "Analyze", "review", "compare", "check" mean *report*. Not act. |
| **6** | **CAR FEEDBACK LOOP** | Every human correction becomes a rule, not just a code fix. |
| **7** | **BUSINESS AUTHORITY GATE** | No code against business rules until a human approves them. |
| **8** | **POST-EDIT VALIDATION** | After each batch of edits, run the scanner. Fix violations before continuing. |

## Why each one exists

- **Rule 1** — Without a log, work is unauditable. V2 and GP5 collapse.
- **Rule 2** — Auto-advancing phases is the AI granting itself autonomy the human didn't give. V3 violation.
- **Rule 3** — The cost of confirming a one-line plan is trivial. The cost of an unwanted refactor is not.
- **Rule 4** — Drive-by changes pollute diffs and erode trust. GP2.
- **Rule 5** — Treating "review" as "review and fix" is the most common scope-bleed failure.
- **Rule 6** — If you fix the symptom only, the next agent repeats the bug. The framework must learn faster than the agents drift.
- **Rule 7** — The AI may *extract* apparent business rules from code. It is not the authority on whether they're correct.
- **Rule 8** — Per-file writes can pass individually and fail in aggregate. Catch the integration-level violations.

## Where they are enforced

A rule that isn't enforced *somewhere* is a slogan. Each has at least one enforcement point:

| Rule | Enforced by |
|---|---|
| 1 — Session log | SessionStart hook |
| 2 — Phase gates | Phase machine + PreToolUse hook |
| 3 — Code review gate | PreToolUse hook (high-impact classifier) |
| 4 — Scope discipline | PreToolUse hook + kernel prompt |
| 5 — Read-only verbs | Kernel prompt + UserPromptSubmit hook |
| 6 — CAR feedback loop | Critic phase + memory writes |
| 7 — Business authority | Guardian phase artifact policy |
| 8 — Post-edit validation | PostToolUse hook → scanner |

## What "non-negotiable" means

These are injected every turn. They are not configurable per-project, per-profile, or per-skill. A project that turns one off is no longer operating inside AI-ASE — that's allowed, it just isn't "AI-ASE with rule X disabled."

The rules can evolve through the formal proposal process, but never as a session-scope toggle.

---

**Next:** [docs/05-architecture.md](../docs/05-architecture.md) — how the kernel, phases, skills, rules, hooks, and audit fit together.