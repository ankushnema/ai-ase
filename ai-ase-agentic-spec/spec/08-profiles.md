
# Profiles

## Purpose

Profiles tune the framework's *ceremony* to the *risk* of the change. A typo fix should not pay the cost of an architecture review. A new payments service should.

Four profiles ship: `patch`, `feature`, `migration`, `incident`. The engine + orchestrator + scanner all consult the active profile.

## File location

```
src/ai_ase/profiles/
├── patch.yaml
├── feature.yaml
├── migration.yaml
└── incident.yaml
```

## Profile schema

```yaml
id: feature                                 # REQUIRED. patch | feature | migration | incident.
name: "Feature Development"                 # REQUIRED. Human label.
description: "Standard development work"
detection-keywords:                         # OPTIONAL. detect_profile() consumes these.
  - feature
  - add
  - implement
scanner-mode: standard                      # REQUIRED. block-only | standard | strict.
rules-active: all                           # REQUIRED. all | block-only.
phase-gates: true                           # REQUIRED. true | false.
context-budget-lines: 300                   # REQUIRED. Cap on assembled context.
multi-agent-depth: standard                 # REQUIRED. minimal | standard | maximum | post-hoc.
trust-threshold: 50                         # REQUIRED. Minimum trust score to proceed.
active-phases:                              # REQUIRED. Subset of [archaeologist, guardian, architect, critic, reflector].
  - archaeologist
  - guardian
  - architect
  - critic
  - reflector
```

## The 4 ship profiles

| Property | Patch | Feature | Migration | Incident |
|---|---|---|---|---|
| Scanner mode | `block-only` | `standard` | `strict` (WARN treated as BLOCK) | `block-only` |
| Phase gates | false | true | true (mandatory) | false |
| Context budget | 100 lines | 300 lines | 500 lines | 100 lines |
| Multi-agent depth | minimal (1 edge case) | standard (5–10 tests) | maximum (full battery) | post-hoc (48 h) |
| Trust threshold | 30 | 50 | 70 | 30 |
| Active phases | reflector only | all 5 | all 5 + audit | reflector only |
| Detection keywords | `fix, typo, hotfix, bug` | (default) | `migrate, rewrite, modernize, legacy` | `incident, p1, p2, outage, sev1` |

## Profile detection

See `engine.detect_profile()` in [03-CORE-ENGINE.md](../spec/03-core-engine.md). Priority order:

1. **Incident** (highest — emergency keywords override everything).
2. **Migration** (large-scale work).
3. **Patch** (small fixes).
4. **Feature** (default, no keywords matched).

The CLI's `ai-ase init` writes the chosen profile to `.ai-ase/profile.json`. The MCP `governance_profile` tool calls `detect_profile()` for ad-hoc detection from a task description.

## Profile changes mid-session

Profile is sticky once `init` writes it. To change:

```bash
ai-ase init --profile migration --force
```

A profile change is logged to the audit log as `event: profile_change`.

## Loader

```python
def load_profile(profile_id: str) -> dict:
    path = packaged_path() / "profiles" / f"{profile_id}.yaml"
    return yaml.safe_load(path.read_text())

def active_profile() -> dict:
    raw = Path(".ai-ase/profile.json").read_text()
    pid = json.loads(raw)["profile"]
    return load_profile(pid)
```

## Tests

- All 4 profile YAMLs load and parse.
- Schema validation: every required field present, every value in the allowed enum.
- `detect_profile()` returns expected profile for keyword-loaded task descriptions.
- `incident` beats `migration` beats `patch` when keywords overlap.
- Default fallback is `feature`.
- Profile change is logged to audit.

## Anti-patterns

| Don't | Because |
|---|---|
| Allow a profile that disables BLOCK rules | All four ship profiles enable all BLOCK rules. Disabling is not a profile concern. |
| Let `patch` skip the kernel | The 8 immutable rules apply to every profile. |
| Add a 5th profile in v1 | The four were chosen because they cover ~95 % of real changes. Adding a 5th invites overfit. |
| Allow per-file profile overrides | Profile is per-session, per-`init`. Per-file overrides re-introduce the "is this rule active here?" confusion the framework exists to remove. |

## Ground truth

The reference implementation does not include per-profile YAML files; profile definitions were hardcoded in `engine.detect_profile()`. This spec is the authoritative format going forward. Implementations may choose to keep them inline initially but should externalize within a release.