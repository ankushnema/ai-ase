# Platform Adapters

## Purpose

`adapters.py` generates platform-specific configuration files (Copilot instructions, GitHub Actions workflow) so teams don't have to author them by hand. Two CLI commands:

```bash
ai-ase adapter copilot [--profile PROFILE] [--output DIR]
ai-ase adapter ci      [--profile PROFILE] [--output DIR]
```

## Why

- v1.2 of the framework had a 3000-line `copilot-instructions.md`. Stale within days.
- CI integration was manual YAML per repo.
- Teams need a one-command answer.

## Output: Copilot instructions

```
.github/copilot-instructions.md       (150–200 lines, NOT 3000)
```

Contains:

1. The 50-line governance kernel (verbatim from `context/base-prompt.md`).
2. MCP server connection note (`see .mcp.json — the validate_code tool is mandatory`).
3. Profile description (what changes per profile).
4. Rule summary (counts + BLOCK rule IDs).
5. Multi-agent verification note.
6. "What this means for you" — 5 actionable lines for the developer reading it.

**Key insight:** The instructions file is NOT the enforcement mechanism. The MCP server is. The instructions tell the AI *that the tools exist*. If the AI ignores the instructions (~5–10 % of the time), the PreToolUse hook catches it. Belt + suspenders.

## Output: GitHub Actions workflow

```
.github/workflows/ai-ase-scan.yml     (~40 lines)
```

Contains:

```yaml
name: AI-ASE Scan
on:
  pull_request:
    branches: [main, master, develop]
jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install ai-ase
      - run: ai-ase scan . --profile {{PROFILE}}
```

Posts results as a PR comment via a follow-up step (uses `actions/github-script` or `peter-evans/create-or-update-comment`).

## Public interface

```python
def generate_copilot_instructions(profile: str) -> str: ...

def generate_ci_workflow(profile: str) -> str: ...

def write_copilot(profile: str, output_dir: Path) -> Path: ...

def write_ci(profile: str, output_dir: Path) -> Path: ...
```

## Algorithm: `generate_copilot_instructions(profile)`

```
1. kernel = read packaged base-prompt.md
2. kernel = substitute placeholders (PROFILE, PHASE="archaeologist", BUDGET=profile-default)
3. rules = load_rules(bundled_path)
4. summary = build_rule_summary(rules, profile)
5. profile_block = build_profile_block(profile)
6. parts = [kernel, mcp_section(), profile_block, summary, multi_agent_note(), actionable_section()]
7. return "\n\n".join(parts)
```

`build_rule_summary` produces:

```markdown
## Active Rules (profile: feature)

**71 rules total: 17 BLOCK, 50 WARN**

### BLOCK rules (always fired, reject the write)
- VR-01 Hardcoded Password
- VR-02 Hardcoded API Key
- VR-03 AWS Access Key
- ... (15 more)

### WARN categories
- Code quality: 10 rules
- Logging: 7 rules
- Performance: 7 rules
- Resilience: 4 rules
- DevOps: 6 rules
- AI engineering: 5 rules
```

## Template engine

Use f-strings + simple conditionals. **No Jinja2.** V4 (Simplicity) — every dependency added is a maintenance liability. The templates are short and per-profile variation is small.

## Tests (target ≥ 24)

- `generate_copilot_instructions("feature")` produces 150–200 lines.
- `generate_copilot_instructions("patch")` includes patch-specific profile block.
- Output includes verbatim 50-line kernel.
- Output mentions `validate_code` tool.
- Output lists all 17 BLOCK rule IDs.
- `generate_ci_workflow(profile)` produces valid YAML (passes `yaml.safe_load`).
- `write_copilot()` creates `.github/copilot-instructions.md`.
- `write_ci()` creates `.github/workflows/ai-ase-scan.yml`.
- Re-running with same profile is idempotent (file content identical).
- Different profiles produce different output.

## Anti-patterns

| Don't | Because |
|---|---|
| Generate a 3000-line copilot file again | The whole point was to fix this. Cap at 200. |
| Embed company-specific rules in the adapter | Adapters generate from canonical rules only. House rules belong in `.ai-ase/rules/`. |
| Add Jinja2 | f-strings are enough. Adding a templating library to render five files is overkill. |
| Generate Jenkinsfile / GitLab CI in v1 | Start with GitHub Actions. The 80 % case. Others can be added later. |

## Ground truth

[artifacts/platform-adapters-design.md](../artifacts/platform-adapters-design.md) is the design doc this spec implements.