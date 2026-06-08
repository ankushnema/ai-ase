# Project Structure

## Purpose

Defines the on-disk layout of the `ai-ase` Python package. Do not improvise. The layout is referenced by every other spec.

## Top-level layout

```
ai-ase/
├── src/
│   └── ai_ase/
│       ├── __init__.py              # __version__ = "1.3.0"
│       ├── __main__.py              # python -m ai_ase
│       ├── engine.py                # see 03-CORE-ENGINE
│       ├── cli.py                   # see 04-CLI
│       ├── server.py                # see 05-MCP-SERVER
│       ├── context.py               # see 06-CONTEXT-ASSEMBLER
│       ├── phases.py                # see 09-PHASE-ORCHESTRATOR
│       ├── phase_orchestrator.py    # see 09-PHASE-ORCHESTRATOR
│       ├── audit.py                 # see 10-AUDIT-LOG
│       ├── trust.py                 # see 11-TRUST-SCORE
│       ├── policy.py                # see 11-TRUST-SCORE (consumed by)
│       ├── skills.py                # see 12-SKILLS-SYSTEM
│       ├── agents.py                # see 13-MULTI-AGENT
│       ├── adapters.py              # see 14-PLATFORM-ADAPTERS
│       ├── hooks.py                 # see 15-HOOKS-RUNTIME
│       ├── hook_handler.py          # see 15-HOOKS-RUNTIME
│       ├── findings.py              # see 16-CAR-FEEDBACK
│       ├── session_log.py           # see 17-SESSION-LOG
│       ├── rag_retriever.py         # see 18-RAG-RETRIEVER
│       ├── dashboard.py             # see 19-DASHBOARD
│       ├── capabilities.py          # see 20-CAPABILITIES-MATRIX
│       ├── rules/                   # bundled rule YAML — see 07-RULE-SCHEMA
│       │   ├── _registry.yaml
│       │   ├── _groups.yaml
│       │   ├── security/
│       │   ├── code-quality/
│       │   ├── type-safety/
│       │   ├── sre-reliability/
│       │   ├── devops/
│       │   └── ai-engineering/
│       ├── profiles/                # bundled profile YAML — see 08-PROFILES
│       ├── skills/                  # bundled skill markdown — see 12-SKILLS-SYSTEM
│       ├── context/                 # base prompt + assembler config — see 06
│       │   ├── base-prompt.md
│       │   └── assembler.yaml
│       └── templates/               # adapter / session-log templates — see 14, 17
├── tests/
│   ├── test_engine.py
│   ├── test_policy.py
│   ├── test_trust.py
│   ├── test_audit.py
│   ├── test_skills.py
│   ├── test_phase_orchestrator.py
│   ├── test_server_tools.py
│   ├── test_hooks.py
│   ├── test_adapters.py
│   ├── test_dashboard.py
│   ├── test_mutation.py             # anti-circular-validation probes
│   ├── test_claim_integrity.py      # doc-to-runtime CI gate
│   └── fixtures/
│       ├── violations.py
│       ├── clean.py
│       ├── violations.java
│       └── violations.dockerfile
├── action/
│   └── action.yml                   # see 21-CI-GITHUB-ACTION
├── pyproject.toml                   # see 02-PACKAGE-CONFIG
├── README.md
├── LICENSE                          # Apache-2.0
├── CHANGELOG.md
└── CONTRIBUTING.md
```

## Why this layout

| Choice | Reason | Value |
|---|---|---|
| `src/`-layout | Prevents accidentally importing from the source tree before install | hygiene |
| Bundled `rules/` + `profiles/` + `skills/` inside the package | A `pip install ai-ase` is enough to scan — no extra repos to clone | V4 (Simplicity), V7 (Files are universal interface) |
| Flat module names (no deep nesting) | Every file is one concern, one responsibility | V4 |
| `tests/` at top level (not inside `src/`) | Standard pytest discovery | hygiene |
| Single Apache-2.0 LICENSE | Permissive, no CLA needed | adoption |

## Critical: bundled vs. project-local rules

`rules/` ships inside the package. A project may also place rules under `.ai-ase/rules/` or `core/rules/` to add house rules. The engine's `find_rules_path()` (see [03-CORE-ENGINE.md](../spec/03-core-engine.md)) walks upward to find a project-local path; if none, it falls back to bundled.

Bundled rules are the **floor** — every project gets them. Project-local rules **add** to (never replace) the floor.

## Ground truth

[artifacts/rules/](../artifacts/rules/), [artifacts/skills-registry.yaml](../artifacts/skills-registry.yaml), [artifacts/context/](../artifacts/context/) show what the bundled directories look like in the reference implementation.