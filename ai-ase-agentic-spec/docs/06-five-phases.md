# The Five Phases

**Read time:** 5 minutes.

---

## Why phases at all?

The reasonable first reaction: *"Five phases for a code change? That sounds like waterfall in a hoodie. Aren't we overcomplicating this?"*

Fair. So the question to answer first is: **is this new ceremony, or is it your existing SDLC made mandatory for the AI?**

It's the second.

Look at how a serious change moves through a healthy human team today:

| What humans already do | AI-ASE phase |
|---|---|
| Read the code before changing it | Archaeologist |
| Check what the business / security / compliance rules require | Guardian |
| Write a design doc, get alignment | Architect |
| Threat-model, review for what could break | Critic |
| Implement, test, ship | Reflector |

Nothing in that list is new. **Every team that's been burned by a junior dev shipping a "quick fix" already does some version of these five steps for important changes.** The reason it doesn't feel like ceremony when humans do it is that good engineers do it implicitly — they read before they write, they think before they design, they review before they merge.

The AI doesn't do those steps implicitly. It's a strong implementer with no instinct for *which* of those steps to skip for *this* change. So the framework makes the steps explicit and gates them.

### What the phases actually buy you

| Without phases | With phases |
|---|---|
| AI writes after a 30-second skim | AI writes after a recorded, human-confirmed understanding (Archaeologist) |
| AI invents the rules it then "complies" with | AI works against rules a human approved up front (Guardian) |
| Design lives in the AI's head; you see it in the PR | Design exists as a reviewable doc before any code (Architect) |
| Critique = the human code review | Critique = a phase, separate from the implementer, before code (Critic) |
| Bug fix turns into a five-file refactor | Implementer phase is scoped to the approved design (Reflector) |

The complexity isn't added — it was always there, paid in code review hours, post-incident reviews, and "why does this code exist?" archaeology. The phases just front-load it where it's cheap.

### Where the line is

This is not for every change. The framework has **profiles** (`patch`, `feature`, `migration`, `incident`) that scale ceremony to the change:

- A typo fix in `patch` profile may compress Archaeologist + Guardian + Architect into a single agent turn.
- A new payment integration in `migration` profile gets the full ceremony.
- An incident response in `incident` profile uses a fast-path with a mandatory post-hoc audit.

The five phases always exist. How much time each gets is matched to the risk of the change.

---

## What the phases are

Every non-trivial change moves through five phases. Each has one purpose, one read/write policy, one required output, and a human-approved gate to the next.

The phases are not a methodology suggestion. They are an enforced state machine. `phase.json` holds the current phase. The PreToolUse hook blocks tool calls that violate the active phase's policy.

## Quick view

| # | Phase | Purpose | Reads | Writes | Required output |
|---|---|---|---|---|---|
| 1 | **Archaeologist** | Understand the code as it is | All | Nothing | A model of what exists |
| 2 | **Guardian** | Scope the rules that apply | All | `business-guardrails.md`, `COMPLIANCE.md` only | Human-approved guardrails doc |
| 3 | **Architect** | Design the change | All | Design docs + ADRs | An approved design |
| 4 | **Critic** | Attack the design | All | Nothing | A risk report |
| 5 | **Reflector** | Implement | All | Anything | The change |

---

## Phase 1 — Archaeologist

**Purpose.** Map the territory. The AI explores the codebase, names what's there, and surfaces what surprises it.

**Why first.** An AI that writes before it understands is the most common failure mode. Forcing read-only first eliminates the class.

**Required skill / artifact.** `business-rule-extraction` produces `business-guardrails.md` containing `### [B###]` headings (one per extracted rule).

**Advances when:** the human reviews the extracted business rules and confirms the AI has the right mental model.

## Phase 2 — Guardian

**Purpose.** Identify which rules — business, security, compliance, architectural — apply to the change. Get them approved by a human before any design starts.

**Why second.** Without this, the AI silently invents the rules it will later "comply" with. Rule 7 (Business Authority Gate) lives here.

**Writes are clamped.** Only `business-guardrails.md` and `COMPLIANCE.md`. No code. No design. The Guardian Governance Allowlist (Layer 8) enforces this.

**Required artifact.** Compliance review note explaining which rules apply and which the human has approved.

**Advances when:** the human signs off that the rules are correct and complete.

## Phase 3 — Architect

**Purpose.** Design the change against the approved rules. Surface the design before code exists.

**Why third.** Designing in the AI's head and "showing" via a PR is too late. The design must be reviewable before any code is written.

**Required artifact.** A design doc + ADR(s) — what's being built, why, and which decisions were closed.

**Advances when:** the human approves the design.

## Phase 4 — Critic

**Purpose.** Attack the approved design. Find what breaks before code does.

**Why a separate phase.** Asking the implementer to also be the critic is asking the AI to argue against its own work — a known weak point in current models. A dedicated Critic phase, read-only by policy, prevents the conflict of interest.

**Required artifact.** A risk report — failure modes, edge cases, missing tests, contracts that could break.

**Advances when:** the human reviews the risks and either accepts them, mitigates them in the design, or cancels the change.

## Phase 5 — Reflector

**Purpose.** Implement. This is the *only* phase where production code is written.

**Why last.** By the time Reflector starts, the AI knows what exists (Archaeologist), which rules apply (Guardian), what to build (Architect), and where it can break (Critic). Implementation is the smallest remaining step.

**Required artifact.** The change itself — passing the scanner clean (Rule 8: Post-Edit Validation).

**Advances when:** the change is committed. Session moves to the next change, which restarts at Archaeologist.

---

## The advancement gate

Advancing requires two things, in order:

1. **Mechanical:** `skills_satisfied(phase)` returns true — the required artifact exists and matches its validator.
2. **Human:** the user explicitly says "proceed." Silence is not approval (Rule 2).

The phase orchestrator refuses to write a new value to `phase.json` if either is missing.

## What a phase violation looks like

If during Architect the agent tries to call `Write` against a `.py` file:

```json
{
  "decision": "BLOCK",
  "reason": "Phase=architect. Write to production code requires Reflector phase.",
  "remediation": "Complete the design doc, get human approval, advance to Reflector."
}
```

The agent does not get to argue. The hook returned BLOCK before the tool ran.

## Why not skip phases for small changes

Profiles (`patch` / `feature` / `migration` / `incident`) scale the *ceremony* of each phase, not the *existence* of them. A typo fix in patch profile may complete Archaeologist + Guardian + Architect in a single agent turn — but the gates still fire, and the human still approves the advance to Reflector. Skipping is not the same as compressing.

---

**Next:** [docs/07-glossary.md](../docs/07-glossary.md) — the vocabulary used across all the other docs.
