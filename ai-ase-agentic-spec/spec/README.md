# Implementation Specs

The 22 numbered specs in this folder are the **rebuild blueprint** for AI-ASE. Each spec covers one module of the Python package, with:

- **Purpose** — what the module is responsible for, in one paragraph.
- **Public interface** — the functions / classes the rest of the package may call.
- **Algorithm** — pseudocode at the level needed to rebuild from scratch.
- **File layout** — what lives in the module file (or directory).
- **Tests** — the minimum verification surface for "done."
- **Ground truth** — link to the matching artifact in `artifacts/` when one exists.

A capable AI coding agent (or a human), given only this folder + a Python toolchain, should be able to rebuild the package so it passes the tests in [02-package-config.md](../spec/02-package-config.md).

---

## Read order

You don't have to read these top-to-bottom. The graph of dependencies is:

```
01-PROJECT-STRUCTURE       (layout — read first)
02-PACKAGE-CONFIG          (pyproject.toml, test setup — read second)
07-RULE-SCHEMA             ← foundation for engine
03-CORE-ENGINE             ← uses RULE-SCHEMA
04-CLI                     ← uses ENGINE
06-CONTEXT-ASSEMBLER       ← foundation for hooks + MCP
05-MCP-SERVER              ← uses ENGINE + CONTEXT-ASSEMBLER + TRUST + AUDIT
08-PROFILES                ← consumed by ENGINE
09-PHASE-ORCHESTRATOR      ← uses PROFILES, SKILLS
10-AUDIT-LOG               ← used by everything
11-TRUST-SCORE             ← uses AUDIT
12-SKILLS-SYSTEM           ← uses CONTEXT-ASSEMBLER
13-MULTI-AGENT             ← uses SKILLS
14-PLATFORM-ADAPTERS       ← uses RULE-SCHEMA, CONTEXT-ASSEMBLER
15-HOOKS-RUNTIME           ← uses ENGINE, AUDIT, CONTEXT-ASSEMBLER (the teeth)
16-CAR-FEEDBACK            ← uses RULE-SCHEMA
17-SESSION-LOG             ← uses AUDIT
18-RAG-RETRIEVER           ← used by MCP-SERVER, SKILLS
19-DASHBOARD               ← uses AUDIT
20-CAPABILITIES-MATRIX     ← introspection
21-CI-GITHUB-ACTION        ← wraps CLI
22-MCP-CONNECTION          ← client-side wiring, not a Python module
```

If you're rebuilding, the suggested order is the order in [../spec/00-build-path.md](../spec/00-build-path.md).

---

## Spec index

| # | Spec | Module | Lines (target) |
|---|---|---|---|
| 01 | [PROJECT-STRUCTURE](../spec/01-project-structure.md) | (layout) | — |
| 02 | [PACKAGE-CONFIG](../spec/02-package-config.md) | `pyproject.toml`, `tests/` | — |
| 03 | [CORE-ENGINE](../spec/03-core-engine.md) | `engine.py` | ~400 |
| 04 | [CLI](../spec/04-cli.md) | `cli.py` | ~350 |
| 05 | [MCP-SERVER](../spec/05-mcp-server.md) | `server.py` | ~500 |
| 06 | [CONTEXT-ASSEMBLER](../spec/06-context-assembler.md) | `context.py` | ~250 |
| 07 | [RULE-SCHEMA](../spec/07-rule-schema.md) | `rules/` (YAML) | — |
| 08 | [PROFILES](../spec/08-profiles.md) | `profiles/` (YAML) | — |
| 09 | [PHASE-ORCHESTRATOR](../spec/09-phase-orchestrator.md) | `phases.py`, `phase_orchestrator.py` | ~350 |
| 10 | [AUDIT-LOG](../spec/10-audit-log.md) | `audit.py` | ~150 |
| 11 | [TRUST-SCORE](../spec/11-trust-score.md) | `trust.py`, `policy.py` | ~250 |
| 12 | [SKILLS-SYSTEM](../spec/12-skills-system.md) | `skills.py` | ~300 |
| 13 | [MULTI-AGENT](../spec/13-multi-agent.md) | `agents.py` | ~250 |
| 14 | [PLATFORM-ADAPTERS](../spec/14-platform-adapters.md) | `adapters.py` | ~300 |
| 15 | [HOOKS-RUNTIME](../spec/15-hooks-runtime.md) | `hooks.py`, `hook_handler.py` | ~400 |
| 16 | [CAR-FEEDBACK](../spec/16-car-feedback.md) | `findings.py` + CLI cmd | ~200 |
| 17 | [SESSION-LOG](../spec/17-session-log.md) | `session_log.py` | ~250 |
| 18 | [RAG-RETRIEVER](../spec/18-rag-retriever.md) | `rag_retriever.py` | ~200 |
| 19 | [DASHBOARD](../spec/19-dashboard.md) | `dashboard.py` | ~400 |
| 20 | [CAPABILITIES-MATRIX](../spec/20-capabilities-matrix.md) | `capabilities.py` | ~100 |
| 21 | [CI-GITHUB-ACTION](../spec/21-ci-github-action.md) | `action/action.yml` | — |
| 22 | [MCP-CONNECTION](../spec/22-mcp-connection.md) | `.mcp.json` (generated) | — |