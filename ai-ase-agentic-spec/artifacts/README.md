# Artifacts — Ground-Truth On-Disk Files

> **The actual YAML, markdown, JSON and example scripts that ship inside the AI-ASE Python package.** When a spec says "the engine loads YAML files with *this* schema," this folder has the YAML.

The [spec/](../spec/) specs describe these files in prose. This folder is the canonical source — if a spec and an artifact disagree, the artifact wins (and the spec is wrong; open an issue).

---

## What's here

| File / folder | What it is | Spec section |
|---|---|---|
| [skills-registry.yaml](../artifacts/skills-registry.yaml) | All 21 skills: triggers, scopes, instruction paths | [spec/12-skills-system.md](../spec/12-skills-system.md), [catalogs/skills.md](../catalogs/skills.md) |
| [rules-registry.yaml](../artifacts/rules-registry.yaml) | Master index of all rule files | [spec/07-rule-schema.md](../spec/07-rule-schema.md), [catalogs/rules.md](../catalogs/rules.md) |
| [rules-groups.yaml](../artifacts/rules-groups.yaml) | Rule grouping / category map | [catalogs/rules.md](../catalogs/rules.md) |
| [rules/](../artifacts/rules/) | 16 rule YAML files across 6 active categories — full regex, rationale, fix text | [spec/07-rule-schema.md](../spec/07-rule-schema.md) |
| [context/base-prompt.md](../artifacts/context/base-prompt.md) | The 50-line governance kernel injected via UserPromptSubmit | [docs/05-architecture.md](../docs/05-architecture.md), [spec/06-context-assembler.md](../spec/06-context-assembler.md) |
| [context/assembler.yaml](../artifacts/context/assembler.yaml) | File-pattern → guardrail map used by the context assembler | [spec/06-context-assembler.md](../spec/06-context-assembler.md) |
| [hooks-design.md](../artifacts/hooks-design.md) | Design notes for the 4 hook events | [spec/15-hooks-runtime.md](../spec/15-hooks-runtime.md) |
| [platform-adapters-design.md](../artifacts/platform-adapters-design.md) | Design notes for the AI IDE adapter layer | [spec/14-platform-adapters.md](../spec/14-platform-adapters.md) |
| [dashboard-design.md](../artifacts/dashboard-design.md) | Design notes for the trust / audit dashboard | [spec/19-dashboard.md](../spec/19-dashboard.md) |
| [example-settings.json](../artifacts/example-settings.json) | A working hook-wiring config | [spec/15-hooks-runtime.md](../spec/15-hooks-runtime.md) |
| [examples/](../artifacts/examples/) | 4 runnable examples: basic scan, MCP wiring, hook shell, trust+policy | [examples/quickstart.md](../examples/quickstart.md) |

---

## How to use this folder

**Reading the spec?** When a spec describes a schema, open the matching artifact in a second tab — you'll see the actual on-disk shape, not just prose about it.

**Rebuilding the package?** Lift these files directly into your `src/ai_ase/` tree. Don't paraphrase. The regex strings, severity values, and YAML key names are load-bearing.

**Auditing the framework?** This folder is what makes the AI-ASE claim falsifiable. Every "AI-ASE enforces rule X" in the catalogs has a corresponding YAML stanza here you can read.

---

## Note on missing SKILL bodies

The skill registry references body files at paths like `skills/business-rule-extraction/SKILL.md`. Those body files were **never published** in the reference implementation. The rebuild's [catalogs/skills.md](../catalogs/skills.md) and [spec/12-skills-system.md](../spec/12-skills-system.md) describe each skill from its registry metadata plus design intent — there is no upstream SKILL.md to vendor.
