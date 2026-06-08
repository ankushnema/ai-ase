# Source Mapping — Spec ↔ Module Crosswalk

A spec is only useful if you can find the code that implements each piece. This file maps every section of the rebuild to the implementation module (in the Python package) and the vendored ground-truth artifact (in `artifacts/`).

If you are rebuilding from this spec, this is the file you keep open in a tab.

---

## Spec → implementation module → ground-truth source

| Spec section | Implementation module | Ground-truth source |
|---|---|---|
| [docs/05-architecture.md](../docs/05-architecture.md) — the runtime picture | `src/ai_ase/__init__.py`, [spec/01-project-structure.md](../spec/01-project-structure.md) | — |
| [docs/05-architecture.md](../docs/05-architecture.md) — 50-line kernel | `src/ai_ase/hook_handler.py::inject_kernel()` | [artifacts/context/base-prompt.md](../artifacts/context/base-prompt.md) |
| [docs/05-architecture.md](../docs/05-architecture.md) — file-pattern → guardrail map | `src/ai_ase/context.py` or assembler module | [artifacts/context/assembler.yaml](../artifacts/context/assembler.yaml) |
| [docs/04-eight-immutable-rules.md](../docs/04-eight-immutable-rules.md) | `src/ai_ase/hook_handler.py` + per-rule enforcement points | [artifacts/context/base-prompt.md](../artifacts/context/base-prompt.md) (lines 7–25) |
| [docs/06-five-phases.md](../docs/06-five-phases.md) | `src/ai_ase/phases.py`, `src/ai_ase/phase_orchestrator.py` | — |
| [catalogs/rules.md](../catalogs/rules.md) | `src/ai_ase/engine.py`, `src/ai_ase/rules/` | [artifacts/rules/](../artifacts/rules/), [artifacts/rules-registry.yaml](../artifacts/rules-registry.yaml), [artifacts/rules-groups.yaml](../artifacts/rules-groups.yaml) |
| [catalogs/tools.md](../catalogs/tools.md) | `src/ai_ase/server.py` | — (defined inline in this spec) |
| [catalogs/skills.md](../catalogs/skills.md) | `src/ai_ase/skills.py` | [artifacts/skills-registry.yaml](../artifacts/skills-registry.yaml) |

---

## Implementation file → what's in it

The package follows the layout in [spec/01-project-structure.md](../spec/01-project-structure.md). Each module owns one concern:

| Module | Concern | Spec file |
|---|---|---|
| `__init__.py` | Package init, `__version__` | [spec/02-package-config.md](../spec/02-package-config.md) |
| `__main__.py` | `python -m ai_ase` entry | [spec/02-package-config.md](../spec/02-package-config.md) |
| `engine.py` | The scanner: load YAML rules, scan a file, return violations | [spec/03-core-engine.md](../spec/03-core-engine.md) |
| `cli.py` | `ai-ase scan`, `serve`, `init`, `phase`, `dashboard` | [spec/04-cli.md](../spec/04-cli.md) |
| `server.py` | MCP server, 9 tools, stdio transport | [spec/05-mcp-server.md](../spec/05-mcp-server.md) |
| `context.py` | Kernel + file-pattern → guardrail assembly | [spec/06-context-assembler.md](../spec/06-context-assembler.md) |
| `rules/` (YAML) | The 71 rules on disk | [spec/07-rule-schema.md](../spec/07-rule-schema.md) |
| `profiles/` (YAML) | patch / feature / migration / incident definitions | [spec/08-profiles.md](../spec/08-profiles.md) |
| `phases.py` | Phase enum + per-phase metadata | [spec/09-phase-orchestrator.md](../spec/09-phase-orchestrator.md) |
| `phase_orchestrator.py` | Phase transitions, `skills_satisfied()`, gate enforcement | [spec/09-phase-orchestrator.md](../spec/09-phase-orchestrator.md) |
| `audit.py` | Append-only JSONL audit log, correlation IDs | [spec/10-audit-log.md](../spec/10-audit-log.md) |
| `trust.py` | Trust score computation + degradation policy | [spec/11-trust-score.md](../spec/11-trust-score.md) |
| `skills.py` | Skill registry + trigger engine | [spec/12-skills-system.md](../spec/12-skills-system.md) |
| `agents.py` | Generator / Verifier / Attacker / Auditor coordination | [spec/13-multi-agent.md](../spec/13-multi-agent.md) |
| `adapters.py` | `ai-ase adapter copilot/ci` generators | [spec/14-platform-adapters.md](../spec/14-platform-adapters.md) |
| `hooks.py`, `hook_handler.py` | The hook event dispatcher invoked from `ai-ase hook handle` | [spec/15-hooks-runtime.md](../spec/15-hooks-runtime.md) |
| `findings.py` | The `findings.json` schema written by `PostToolUse` | [spec/16-car-feedback.md](../spec/16-car-feedback.md), [spec/15-hooks-runtime.md](../spec/15-hooks-runtime.md) |
| `session_log.py` | Session log generation + reconciliation | [spec/17-session-log.md](../spec/17-session-log.md) |
| `rag_retriever.py` | TF-IDF retriever for rule / skill / doc lookup | [spec/18-rag-retriever.md](../spec/18-rag-retriever.md) |
| `dashboard.py` | CLI + HTML governance report | [spec/19-dashboard.md](../spec/19-dashboard.md) |
| `capabilities.py` | Implemented / specified / planned matrix | [spec/20-capabilities-matrix.md](../spec/20-capabilities-matrix.md) |
| `policy.py` | `check_policy()` — read/write/exec permission decisions | [spec/11-trust-score.md](../spec/11-trust-score.md) (consumed by trust degradation) |
| (CI workflow + action.yml) | GitHub Action wrapping `ai-ase scan` | [spec/21-ci-github-action.md](../spec/21-ci-github-action.md) |
| `.mcp.json` (generated) | How an AI IDE finds the MCP server | [spec/22-mcp-connection.md](../spec/22-mcp-connection.md) |

---

## Ground-truth artifacts in `artifacts/`

Each file in `artifacts/` is the *actual on-disk artifact* from the reference implementation. When the spec describes a schema or wire format, the canonical example lives here:

| Artifact | Used by spec section | Used by implementation module |
|---|---|---|
| [skills-registry.yaml](../artifacts/skills-registry.yaml) | [catalogs/skills.md](../catalogs/skills.md) | `skills.py` loader |
| [rules-registry.yaml](../artifacts/rules-registry.yaml) | [catalogs/rules.md](../catalogs/rules.md) | `engine.py` loader |
| [rules-groups.yaml](../artifacts/rules-groups.yaml) | [catalogs/rules.md](../catalogs/rules.md) | `engine.py` profile filter |
| [rules/](../artifacts/rules/) (16 YAML files) | [catalogs/rules.md](../catalogs/rules.md) | `engine.py` regex scan |
| [context/base-prompt.md](../artifacts/context/base-prompt.md) | [docs/04-eight-immutable-rules.md](../docs/04-eight-immutable-rules.md), [docs/05-architecture.md](../docs/05-architecture.md) | `hook_handler.py::inject_kernel()` |
| [context/assembler.yaml](../artifacts/context/assembler.yaml) | [spec/06-context-assembler.md](../spec/06-context-assembler.md) | `context.py` |
| [hooks-design.md](../artifacts/hooks-design.md) | [spec/15-hooks-runtime.md](../spec/15-hooks-runtime.md) | `hooks.py`, `hook_handler.py` |
| [platform-adapters-design.md](../artifacts/platform-adapters-design.md) | [spec/14-platform-adapters.md](../spec/14-platform-adapters.md) | `adapters.py` |
| [dashboard-design.md](../artifacts/dashboard-design.md) | [spec/19-dashboard.md](../spec/19-dashboard.md) | `dashboard.py` |
| [example-settings.json](../artifacts/example-settings.json) | [spec/15-hooks-runtime.md](../spec/15-hooks-runtime.md) | (hook registration) |
| [examples/](../artifacts/examples/) | [examples/quickstart.md](../examples/quickstart.md) | (developer-facing samples) |

---

## How to use this file as a rebuilder

1. Pick a section of the rebuild you want to implement (e.g., catalogs/rules.md).
2. Open the implementation spec (`spec/03-core-engine.md` + `spec/07-rule-schema.md`).
3. Open the ground-truth source (`artifacts/rules/...`) to see what the YAML actually looks like.
4. Write the module. Run the tests listed in the implementation spec.
5. Verify your output matches the ground-truth source.

If those three files disagree on something, the **spec** wins; the ground-truth source is illustrative, and the implementation spec calls out every deliberate divergence.