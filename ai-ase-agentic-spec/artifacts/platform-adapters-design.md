# Platform Adapters — Design Document

## Purpose

Generate platform-specific configuration files that integrate AI-ASE governance into developer workflows. Instead of manually authoring 200-line copilot-instructions or CI workflows, teams run a single command.

## Problem

- v1.2 had a 3000-line `copilot-instructions.md` — too long, stale within days
- CI integration required manual YAML authoring per repo
- No standardized way to onboard new repos

## Solution

Two CLI commands that generate ready-to-use configs:

```
ai-ase adapter copilot [--profile PROFILE] [--output DIR]
ai-ase adapter ci [--profile PROFILE] [--output DIR]
```

## Architecture

```
ai-ase adapter copilot
         |
         v
+-------------------+
|  adapters.py      |
|  - load rules     |  <-- reuses engine.load_rules()
|  - summarize      |
|  - render template|
+-------------------+
         |
         v
.github/copilot-instructions.md (150-200 lines)
```

## Design Decisions

| Decision | Choice | Why |
|----------|--------|-----|
| Template engine | f-strings | No new dependency, simple conditionals per profile |
| Output length | 150-200 lines | v1.2 was 3000 = too much. MCP tools handle enforcement, not the instructions file |
| Governance kernel | 8 rules hardcoded | These are immutable across versions. Changing them is a major decision. |
| CI target | GitHub Actions only | Most common. Jenkins/GitLab can be added later. |
| Rule summary | Dynamic from YAML | Stays in sync as rules are added/removed |

## What the Copilot Instructions Contain

1. **Governance kernel** (8 non-negotiable rules)
2. **MCP server connection** instructions
3. **Profile description** (what changes per profile)
4. **Rule summary** (counts + BLOCK rule IDs)
5. **Multi-agent verification** note
6. **"What this means for you"** — 5 actionable items

## What the CI Workflow Does

1. Triggers on `pull_request` to main/master/develop
2. Installs ai-ase via pip
3. Runs `ai-ase scan . --profile {profile}`
4. Posts scan results as PR comment
5. Fails the check if BLOCK violations found

## Key Insight

The copilot-instructions.md is NOT the enforcement mechanism. It's context for the AI. The MCP server tools (validate_code) are the enforcement. The instructions tell the AI:
- These tools exist
- You MUST call them
- Here's what the rules look for

If the AI ignores the instructions (~5-10% of the time), the pre-commit hook (CI scan) catches it at merge time. Belt + suspenders.

## Files

- `src/ai_ase/adapters.py` — Generation logic
- `tests/test_adapters.py` — 24 tests
- `src/ai_ase/cli.py` — CLI integration (adapter subcommand)