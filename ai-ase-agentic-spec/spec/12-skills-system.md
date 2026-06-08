# Skills System

## Purpose

`skills.py` is the registry + trigger engine for the 21 skills catalogued in [../catalogs/skills.md](../catalogs/skills.md). Skills are on-demand governance knowledge: a Markdown body the AI loads when a trigger fires.

The skills system lets the kernel stay 50 lines while expert procedures (adversarial review, business rule extraction, anti-hallucination audit) live on disk and load only when needed. V5 (Context is King) made operational.

## Files

- `src/ai_ase/skills.py` — registry loader, trigger engine, completion tracking.
- `src/ai_ase/skills/_registry.yaml` — the canonical registry (bundled).
- `src/ai_ase/skills/<skill-id>/SKILL.md` — the body of each skill (bundled).

## Registry schema

```yaml
skills:
  - id: business-rule-extraction          # REQUIRED. stable identifier.
    name: "Business Rule Extraction"      # REQUIRED. human label.
    description: "Extract business rules from legacy code into GIVEN/WHEN/THEN."
    triggers:                             # REQUIRED. list, OR-logic across entries.
      - event: phase-start                # event type (see below)
        condition: phase == "archaeologist"
      - event: explicit
        command: "extract business rules"
    instructions: "skills/business-rule-extraction/SKILL.md"   # REQUIRED. path relative to package root.
    scope: read-only                      # REQUIRED. read-only | advisory | blocking | full-access
    type: phase                           # REQUIRED. enforcement | phase | gate | quality | feedback | utility
    artifact: "business-guardrails.md"    # OPTIONAL. file the skill must produce to be considered "completed".
    artifact-validator: "regex"           # OPTIONAL. how to verify the artifact: regex | exists | json-schema
    artifact-regex: "### \\[B\\d{3}\\]"   # OPTIONAL. for artifact-validator=regex
```

## Trigger event types

| Event | Source | Payload |
|---|---|---|
| `session-start` | SessionStart hook | `{}` |
| `phase-start` | `phase_orchestrator.advance()` | `{"phase": str}` |
| `phase-complete` | `phase_orchestrator.advance()` | `{"phase": str}` |
| `phase-advance-attempt` | orchestrator pre-check | `{"phase": str}` |
| `file-created` | `PostToolUse` Write | `{"path": str}` |
| `file-pattern` | `PostToolUse` Write | `{"path": str}` |
| `files-changed-count` | `PostToolUse` aggregate | `{"count": int}` |
| `post-generation` | end-of-Reflector batch | `{"files": list[str]}` |
| `explicit` | user typed a command | `{"command": str}` |
| `(scheduled)` | cron / interval | `{"interval": str}` |

## Condition language

Conditions are tiny boolean expressions. Supported operators: `==`, `!=`, `>=`, `<=`, `>`, `<`, `OR`, `AND`.

Examples:
- `phase == "archaeologist"`
- `count >= 5`
- `path matches **/*Controller.java`

Implementation: a 30-line recursive-descent parser or a regex-based dispatcher. Do NOT use `eval()`.

## Public interface

```python
@dataclass
class Skill:
    id: str
    name: str
    description: str
    triggers: list[dict]
    instructions: Path        # resolved package path
    scope: str
    type: str
    artifact: str | None
    artifact_validator: str | None
    artifact_regex: str | None

def load_registry() -> list[Skill]: ...

def get_by_id(skill_id: str) -> Skill | None: ...

def evaluate_triggers(event: str, payload: dict) -> list[Skill]: ...

def completed(skill_id: str, *, session_id: str) -> bool: ...

def mark_completed(skill_id: str, *, session_id: str, artifact_path: str | None = None) -> None: ...
```

## Algorithm: `evaluate_triggers(event, payload)`

```
1. skills = load_registry()
2. fired = []
3. for skill in skills:
4.   for trig in skill.triggers:
5.     if trig["event"] != event: continue
6.     if "condition" in trig and not eval_condition(trig["condition"], payload): continue
7.     fired.append(skill); break
8. return fired
```

## Algorithm: `completed(skill_id, session_id)`

```
1. skill = get_by_id(skill_id)
2. if not skill: raise UnknownSkill
3. if skill.artifact is None:
4.   return audit_has("skill_completed", skill_id=skill_id, session_id=session_id)
5. # Artifact required:
6. if not Path(skill.artifact).exists(): return False
7. content = Path(skill.artifact).read_text()
8. if skill.artifact_validator == "regex":
9.   return bool(re.search(skill.artifact_regex, content))
10. if skill.artifact_validator == "exists": return True
11. return False
```

## Algorithm: `mark_completed(skill_id, session_id, artifact_path)`

```
1. audit.append("skill_completed",
                skill_id=skill_id,
                session_id=session_id,
                artifact_path=artifact_path)
```

## Skill body format (`SKILL.md`)

```markdown
# {Skill Name}

## When This Skill Activates
{describe the triggers in prose for the AI's benefit}

## What You Do
1. Step one
2. Step two
3. Step three

## Rules
- Non-negotiable constraint 1
- Non-negotiable constraint 2

## Output Format
{describe the artifact the skill must produce}

## Example
{concrete walkthrough}
```

The AI reads this body verbatim when the trigger fires. Keep each skill body ≤ 100 lines (V5 — context budget).

## Tests (target ≥ 22)

- Registry loads, every skill has required fields.
- `evaluate_triggers("session-start", {})` returns the always-on skills.
- `evaluate_triggers("phase-start", {"phase":"critic"})` returns `adversarial-review`.
- `evaluate_triggers("file-created", {"path":"src/UserController.java"})` returns `code-review-gate`.
- `completed()` returns False before mark, True after.
- `completed()` for artifact-required skill returns False when artifact missing.
- `completed()` for `business-rule-extraction` returns True only when regex matches.
- Condition parser handles `==`, `>=`, `AND`, `OR`.
- Unknown skill ID raises `UnknownSkill`.

## Anti-patterns

| Don't | Because |
|---|---|
| Use `eval()` for conditions | RCE risk. Hand-rolled parser is 30 lines. |
| Load all skill bodies at startup | Defeats the point. Bodies load on trigger. |
| Allow the AI to mark its own skills completed | Audit-based completion only. Artifact-based checks for the rest. |
| Add skills without a trigger | A skill that never fires is dead code. Every skill needs at least one trigger. |

## Ground truth

[artifacts/skills-registry.yaml](../artifacts/skills-registry.yaml) is the canonical 21-skill registry. The skill body Markdown files (`SKILL.md`) **were not published** in the reference implementation — when rebuilding, write them from the catalog descriptions + the design intent in each row of [../catalogs/skills.md](../catalogs/skills.md).
