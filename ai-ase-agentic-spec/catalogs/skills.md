# Catalog — The 21 Skills

A skill is on-demand governance knowledge: a markdown file the agent loads when its trigger fires. Skills exist so the kernel can stay small while expert procedures (adversarial review, business-rule extraction, etc.) live on disk and load only when needed.

The canonical registry is `_registry.yaml` in the implementation. This catalog is the human-readable companion: what each skill is for, when it fires, what (if anything) it produces.

---

## Schema

Every skill has six fields:

| Field | Meaning |
|---|---|
| **id** | stable identifier referenced from PHASE_SKILLS, hooks, other skills |
| **name** | human-readable label |
| **type** | Enforcement, Phase, Gate, Quality, Feedback, or Utility |
| **trigger** | the event or condition that activates it |
| **scope** | `read-only`, `advisory`, `blocking`, or `full-access` |
| **artifact** | the file (if any) the skill must produce; checked by `skills_satisfied()` |

A `blocking` skill that doesn't produce its artifact prevents phase advancement. An `advisory` skill surfaces a warning. A `read-only` skill produces a report — the human decides what to do with it.

---

## The 21 Skills

### Enforcement (1)

Always-on governance — fires once per session.

| ID | Trigger | Scope | Notes |
|---|---|---|---|
| **challenge-me** | session-start (always) | blocking | The mandatory alignment interview at the start of every session. |

### Phase (5) — one per phase

Each phase has exactly one phase-skill. Producing the artifact is required to advance.

| ID | Active in | Required artifact |
|---|---|---|
| **business-rule-extraction** | Archaeologist | `business-guardrails.md` (must contain `### [B###]` headings) |
| **guardrail-compliance-check** | Guardian | compliance review note |
| **architecture-design** | Architect | design doc + ADR(s) |
| **adversarial-review** | Critic | risk report |
| **code-generation** | Reflector | the change itself |

### Gate (3)

Triggered by structural events (a file being created, a phase ending). Quick blocking checks.

| ID | Trigger | Scope |
|---|---|---|
| **code-review-gate** | file created in service / controller / entity / config paths, or ≥ 5 files changed, or explicit "review gate" | blocking — requires explicit human plan-approval (Rule 3) |
| **phase-gate-enforcement** | phase complete | blocking — verifies artifacts before advance |
| **business-authority-gate** | Reflector phase start | blocking — verifies `business-guardrails.md` is human-approved (Rule 7) |

### Quality (5)

Run during or after Reflector to verify the change is correct, not just compliant.

| ID | Trigger | Notes |
|---|---|---|
| **mutation-testing** | tests passing in Reflector | targets ≥ 40 % kill rate per module |
| **architecture-testing** | post-generation | verifies layer boundaries, dependency rules |
| **manifest-reconciliation** | Reflector start + end | compares planned vs actual changes |
| **adversarial-testing** | mutation kill-rate ≥ 70 % | only fires when mutation testing earns it |
| **anti-hallucination-audit** | post-generation (always) | resolves imports / symbols against real packages and codebase |

### Feedback (1)

| ID | Trigger | Scope |
|---|---|---|
| **car-feedback-loop** | human correction detected | advisory — Rule 6: every correction becomes a framework rule |

### Utility (6)

Run on schedule or by explicit invocation. Not phase-bound.

| ID | Trigger | Notes |
|---|---|---|
| **session-log-management** | session-start, deliverable-created | satisfies Rule 1 |
| **trust-score-analysis** | phase complete | drives Layer 11 |
| **guardrail-metrics** | monthly or explicit | aggregate scanner stats over time |
| **blind-audit** | bi-weekly or explicit | independent re-evaluation |
| **ai-security-review** | AI/LLM code detected | catches hardcoded prompts, unpinned models, unrestricted agent tools |
| **concurrency-review** | async/threading code detected | catches race conditions, missing synchronization |

---

## When skills fire — by hook event

Skills don't fire by themselves; they ride hook events. Cross-reference for a hook implementer:

| Hook event | Skills that may activate |
|---|---|
| **SessionStart** | challenge-me, session-log-management |
| **UserPromptSubmit** | (none — kernel injection, not skills) |
| **PreToolUse** | code-review-gate, phase-gate-enforcement, business-authority-gate |
| **PostToolUse** | code-generation (during Reflector), session-log-management (on deliverable) |
| **PhaseAdvance** (synthetic event raised by `ai-ase phase advance`) | phase-skill for the entering phase, phase-gate-enforcement, trust-score-analysis |
| **(file watch)** | architecture-testing, anti-hallucination-audit, ai-security-review, concurrency-review |
| **(scheduled)** | guardrail-metrics, blind-audit |

---

## Adding a new skill

1. Define the skill markdown file matching the format in [spec/12-skills-system.md](../spec/12-skills-system.md).
2. Add an entry to `_registry.yaml` with id, name, description, triggers, instructions path, scope.
3. If the skill is `blocking`, add it to the relevant `PHASE_SKILLS` entry in [spec/09-phase-orchestrator.md](../spec/09-phase-orchestrator.md) so `skills_satisfied()` checks it.
4. Write a regex validator for the artifact (e.g., `### \[B\d{3}\]` for business rules).
5. File a PR with rationale, expected false-positive rate, and a test fixture.

---

## Why 21 and not more

Each skill is a context-budget cost when it fires. Adding a skill should clear a high bar: it must catch a class of failure that no existing skill covers, and the failure must be common enough to justify the budget. Most candidate skills get rejected for being too situational.