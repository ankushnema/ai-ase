# CAR Feedback Loop

## Purpose

CAR = **Correct And Record**. Rule 6: every human correction becomes a *framework rule*, not just a code fix. This is the mechanism that prevents the same mistake from being made 51 times.

`findings.py` owns the persistent findings file. The CLI subcommand `ai-ase car suggest` reads recent corrections and proposes new rule YAML.

## The loop

1. Developer corrects the AI ("no, audit events have to start with `audit.`").
2. The framework detects the correction (heuristic: a `Write` whose content materially differs from a recent AI proposal).
3. `car-feedback-loop` skill fires.
4. The skill proposes a draft rule YAML.
5. Developer reviews. If accepted, the rule lands in `.ai-ase/rules/` (project-local).
6. Scanner immediately picks it up via the mtime cache.

## `findings.py`

### Public interface

```python
@dataclass
class Finding:
    file: str
    rule_id: str
    line: int
    line_content: str
    action: str
    timestamp: str

def append(file: str, result: ScanResult) -> None: ...

def read_all() -> list[Finding]: ...

def unresolved() -> list[Finding]: ...

def mark_resolved(file: str, rule_id: str, line: int) -> None: ...
```

### Disk format

`.ai-ase/findings.json`:

```json
{
  "version": 1,
  "findings": [
    {
      "id": "f-9f3a",
      "file": "src/charges/refund_service.py",
      "rule_id": "VR-10",
      "line": 42,
      "line_content": "refund.amount = float(charge.amount)",
      "action": "BLOCK",
      "first_seen": "2026-06-08T10:14:02Z",
      "last_seen": "2026-06-08T10:14:09Z",
      "resolved": false,
      "resolved_at": null
    }
  ]
}
```

`append()` updates `last_seen` when a finding repeats; doesn't create duplicates. The pre-commit hook reads this file and refuses to commit if any `resolved=false` BLOCK findings exist.

## Correction detection

A correction is detected when (heuristic):

1. The AI proposed content X in the last N minutes (recorded as a `validation` audit event).
2. The developer wrote content Y for the same file.
3. `levenshtein_ratio(X, Y) < 0.85` (substantial change).

When detected, fire a `human-correction` synthetic event. The `car-feedback-loop` skill subscribes to it.

```python
def detect_correction(filepath: str, new_content: str, window_minutes: int = 30) -> dict | None: ...
```

Returns `{"original": X, "corrected": Y, "diff": ...}` or `None`.

## `ai-ase car suggest`

```
1. corrections = recent_corrections(window=last_session)
2. for c in corrections:
3.   draft = propose_rule(c)        # heuristic — extract a pattern from the diff
4.   print(draft as YAML)
5.   ask: "Add to .ai-ase/rules/code-quality/local-corrections.rules.yaml? (y/N)"
6.   if y: append to file with next-available VR-ID
7.   if y: audit.append("car_rule_added", rule_id=..., source="human-correction")
```

`propose_rule()` is intentionally simple in MVP: it identifies tokens present in the *original* but not the *corrected* version and offers them as a regex. The developer is expected to refine before accepting. The point is to lower the activation energy for codifying a rule, not to be perfectly precise.

## Worked example

The AI writes `publish("refund.created", payload)`. Developer corrects to `publish("audit.refund.created", payload)`.

`detect_correction()` fires. The `car-feedback-loop` skill proposes:

```yaml
- id: VR-89
  name: "Audit events must be prefixed with 'audit.'"
  action: WARN
  file-types: [PYTHON, JAVA]
  pattern: |
    publish\(["'](?!audit\.)[a-z]+\.[a-z]+["']
  description: "Event names must start with 'audit.' per house convention."
  severity: medium
  profiles: [patch, feature, migration, incident]
  rationale: "Standardized event prefix simplifies subscription, monitoring, and audit aggregation."
  fix-guidance: "Prefix the event name with 'audit.' — e.g., 'audit.refund.created'."
```

Developer reviews, types `y`, the rule lands.

## Tests

- `findings.append()` is idempotent on repeat scan.
- `findings.unresolved()` skips resolved findings.
- `detect_correction()` returns a diff when content differs substantially.
- `detect_correction()` returns None when content is similar (trivial typo).
- `propose_rule()` produces a parseable YAML draft.
- CAR rule addition writes a `car_rule_added` audit event.

## Anti-patterns

| Don't | Because |
|---|---|
| Auto-commit the proposed rule without human review | The proposer is heuristic. The accepter is human. |
| Block on a CAR check | CAR is post-hoc. It does not gate the current change. |
| Treat every diff as a correction | The detection threshold matters. A 5-char edit is not a "correction" worth a rule. |
| Skip the audit event | Without it, you can't measure how often the framework learns from corrections. |

## Ground truth

No vendored file. The behavior is described in [../docs/04-eight-immutable-rules.md](../docs/04-eight-immutable-rules.md) Rule 6 and [../docs/03-core-values.md](../docs/03-core-values.md) GP7.