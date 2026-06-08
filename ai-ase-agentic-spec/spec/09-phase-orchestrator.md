# Phase Orchestrator

## Purpose

Manages the 5-phase lifecycle (Archaeologist → Guardian → Architect → Critic → Reflector). Enforces:

1. The active phase is persisted to disk (`.ai-ase/phase.json`).
2. Phase transitions require explicit human approval (Rule 2).
3. A phase cannot end until its required skills have produced their artifacts (`skills_satisfied()`).
4. Rule 7 (`business-authority-gate`) is checked before entering Reflector.

## Files

- `src/ai_ase/phases.py` — enum + per-phase metadata.
- `src/ai_ase/phase_orchestrator.py` — transitions + gate enforcement.

## `phases.py`

```python
from enum import Enum
from dataclasses import dataclass

class Phase(str, Enum):
    ARCHAEOLOGIST = "archaeologist"
    GUARDIAN = "guardian"
    ARCHITECT = "architect"
    CRITIC = "critic"
    REFLECTOR = "reflector"

@dataclass(frozen=True)
class PhaseMeta:
    purpose: str
    next_phase: Phase | None
    required_skills: tuple[str, ...]      # skill IDs that must produce artifacts
    required_artifacts: tuple[str, ...]   # filesystem markers
    advance_condition: str                # one-line human-readable

PHASE_META: dict[Phase, PhaseMeta] = {
    Phase.ARCHAEOLOGIST: PhaseMeta(
        purpose="Extract and approve business rules.",
        next_phase=Phase.GUARDIAN,
        required_skills=("challenge-me", "business-rule-extraction"),
        required_artifacts=("business-guardrails.md",),
        advance_condition="business-guardrails.md exists with at least one ### [B###] entry, and a human has approved it.",
    ),
    Phase.GUARDIAN: PhaseMeta(
        purpose="Surface relevant guardrails and compliance constraints.",
        next_phase=Phase.ARCHITECT,
        required_skills=("guardrail-compliance-check",),
        required_artifacts=(),
        advance_condition="Compliance review note recorded in session log.",
    ),
    Phase.ARCHITECT: PhaseMeta(
        purpose="Design system, decide patterns, write ADR.",
        next_phase=Phase.CRITIC,
        required_skills=("architecture-design",),
        required_artifacts=("docs/adr/",),   # any ADR file under docs/adr/
        advance_condition="At least one ADR file present in docs/adr/.",
    ),
    Phase.CRITIC: PhaseMeta(
        purpose="Adversarial review of prior phases.",
        next_phase=Phase.REFLECTOR,
        required_skills=("adversarial-review",),
        required_artifacts=(),
        advance_condition="Risk report appended to session log.",
    ),
    Phase.REFLECTOR: PhaseMeta(
        purpose="Generate and verify code.",
        next_phase=None,    # terminal
        required_skills=(
            "business-authority-gate",
            "code-generation",
            "anti-hallucination-audit",
            "mutation-testing",
            "manifest-reconciliation",
        ),
        required_artifacts=(),
        advance_condition="Session complete. Phase resets to archaeologist for next change.",
    ),
}

PHASE_SKILLS: dict[Phase, tuple[str, ...]] = {
    phase: meta.required_skills for phase, meta in PHASE_META.items()
}
```

## `phase_orchestrator.py`

### Public interface

```python
def current_phase() -> Phase: ...
def status() -> dict: ...                          # for `ai-ase phase status`
def advance(*, approve: bool = False) -> Phase: ...  # for `ai-ase phase advance`
def skills_satisfied(phase: Phase) -> tuple[bool, list[str]]: ...
def reset_for_new_change() -> None: ...
```

### Algorithm: `advance(approve)`

```
1. current = current_phase()
2. if not approve: raise GateRequiresApproval(current)
3. ok, missing = skills_satisfied(current)
4. if not ok: raise PhaseGateFailed(current, missing)
5. if current == REFLECTOR: raise PhaseSessionComplete()
6. # Check Rule 7 specifically when entering Reflector:
7. if PHASE_META[current].next_phase == REFLECTOR:
8.   if not business_guardrails_human_approved(): raise BusinessAuthorityNotApproved()
9. next_p = PHASE_META[current].next_phase
10. write_phase_file(next_p, history_append(current))
11. audit.append("phase_change", from=current, to=next_p, approver=current_user())
12. return next_p
```

### Algorithm: `skills_satisfied(phase)`

```
1. meta = PHASE_META[phase]
2. missing = []
3. for skill_id in meta.required_skills:
4.   if not skills.completed(skill_id, session_id=current_session()):
5.     missing.append(skill_id)
6. for artifact in meta.required_artifacts:
7.   if not artifact_exists(artifact): missing.append(f"artifact:{artifact}")
8. return (len(missing) == 0, missing)
```

`skills.completed()` is in [12-SKILLS-SYSTEM.md](../spec/12-skills-system.md). `artifact_exists()` is a directory walk for directory artifacts, file-exists for file artifacts.

### `business_guardrails_human_approved()`

The file `business-guardrails.md` must contain a YAML frontmatter or footer block:

```yaml
---
approved-by: <user@company>
approved-at: 2026-06-08T10:00:00Z
---
```

`approved-by` must NOT be the AI agent itself. The check parses the frontmatter and rejects any value equal to `ai`, `claude`, `copilot`, `cursor`, `assistant`, etc. (case-insensitive). The list is maintained in `phase_orchestrator.AI_USERNAMES_DENYLIST`.

### `reset_for_new_change()`

Called when a session completes (Reflector finishes). Writes `phase.json` back to `archaeologist`. History is preserved.

## Disk format: `.ai-ase/phase.json`

```json
{
  "phase": "guardian",
  "history": [
    {"from": null, "to": "archaeologist", "at": "2026-06-08T09:00:00Z", "approver": null},
    {"from": "archaeologist", "to": "guardian", "at": "2026-06-08T10:15:00Z", "approver": "dev@company"}
  ]
}
```

## Tests (target ≥ 20)

- Each phase advances to the correct next phase.
- `advance(approve=False)` raises `GateRequiresApproval`.
- `advance()` raises `PhaseGateFailed` when required skill artifact is missing.
- Entering Reflector raises `BusinessAuthorityNotApproved` when `business-guardrails.md` is missing or AI-approved.
- `skills_satisfied()` correctly enumerates missing skills.
- Phase change appends to audit log.
- Phase history grows monotonically.
- `reset_for_new_change()` returns to archaeologist without losing history.

## Anti-patterns

| Don't | Because |
|---|---|
| Auto-advance after the last skill completes | Rule 2. Silence is not approval. |
| Let the AI write to `phase.json` | Only the orchestrator (invoked via `ai-ase phase advance`) writes it. |
| Skip the business-authority check for "small" changes | The 8 rules are immutable. Profile does not relax them. |
| Allow arbitrary phase jumps | Only the orchestrator's `next_phase` link is honored. Skipping ahead = silent rule break. |

## Ground truth

No vendored file. Implementations should mirror this spec.