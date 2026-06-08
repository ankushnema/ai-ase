# Build Path

**Read time:** 5 minutes.

The rebuild order. If you're an AI agent told "build AI-ASE from this repo," follow this sequence. If you skip ahead, you will get stuck.

The full implementation blueprint is in [spec/](../spec/). This path is the *order* and the *checkpoints*.

---

## Pre-flight — what you must have read

Before writing any code:

- [docs/01-what-is-aiase.md](../docs/01-what-is-aiase.md) — what it is
- [docs/02-why-it-exists.md](../docs/02-why-it-exists.md) — why text-only governance fails
- [docs/03-core-values.md](../docs/03-core-values.md) — the constraints
- [docs/04-eight-immutable-rules.md](../docs/04-eight-immutable-rules.md) — the rules you yourself must follow
- [docs/05-architecture.md](../docs/05-architecture.md) — the shape
- [docs/06-five-phases.md](../docs/06-five-phases.md) — the state machine
- [catalogs/rules.md](../catalogs/rules.md) — the rule catalog
- [catalogs/tools.md](../catalogs/tools.md) — the MCP tool surface

If you have not read these, stop. Read first, build second.

### What this spec folder does **not** ship

Be explicit about the gap before you start:

- **Skill instruction bodies are not vendored.** [artifacts/skills-registry.yaml](../artifacts/skills-registry.yaml) defines all 21 skills (id, name, triggers, scope, artifact contract), but the actual `skills/<id>/SKILL.md` body files are *not* in this folder. When you reach Step 8 (Skills system), you must either author each skill body from its registry entry + the description row in [catalogs/skills.md](../catalogs/skills.md), or stub each body with a placeholder so the loader and `skills_satisfied()` checks have something to read.
- **No Python source.** Every `.py` module described in [spec/](../spec/) must be written from the spec; no reference implementation is bundled.
- **Rule patterns are exhaustive, rule *fixtures* are not.** Test fixtures under `tests/fixtures/` need to be authored from the pattern examples in each rule YAML.

---

## The 12 steps

Each step has one output and one checkpoint. Do not advance until the checkpoint passes.

### 1. Skeleton

Create the package structure from [spec/01-project-structure.md](../spec/01-project-structure.md). Do not improvise the layout.

- **Output:** an empty package that imports cleanly.
- **Checkpoint:** `python -c "import ai_ase"` does not raise.

### 2. Rule loader

Implement the YAML rule loader. Schema: [spec/07-rule-schema.md](../spec/07-rule-schema.md). Catalog: [catalogs/rules.md](../catalogs/rules.md).

- **Output:** `ai_ase.rules.load_catalog()` returns a list of Rule objects.
- **Checkpoint:** Loaded catalog has 71 unique rules (21 BLOCK, 50 WARN, of which 8 carry `pattern: STRUCTURAL_CHECK` and are skipped by the regex scanner). Authoritative source: [artifacts/rules-registry.yaml](../artifacts/rules-registry.yaml).

### 3. Rule scanner

For each rule, run the regex (or AST check) against incoming text. Return Findings with `rule_id`, `severity`, `line`, `message`, `fix`.

- **Output:** `ai_ase.scanner.scan(text, profile)` returns Findings.
- **Checkpoint:** A known-bad fixture returns the expected finding. A clean fixture returns empty. Fixtures live in `tests/fixtures/` — never inline credential-shaped strings in source or docs.

### 4. Policy module

`check_policy(action, profile, phase, trust)` is the central decision point. Given an action and state, return ALLOW / WARN / BLOCK with a reason.

- **Output:** `ai_ase.policy.check_policy(...)` returns a Decision.
- **Checkpoint:** Each branch (phase gate, trust gate, scanner gate, Guardian allowlist) has at least one test.

### 5. CLI

Implement `ai-ase scan <path>` and `ai-ase serve` (MCP server).

- **Output:** a working `ai-ase` entry point.
- **Checkpoint:** `ai-ase scan tests/fixtures/` produces expected output. `ai-ase serve` starts the MCP server.

### 6. MCP server

Wire the tools from [catalogs/tools.md](../catalogs/tools.md) to the policy/scanner/audit modules.

- **Output:** MCP server exposing `validate_code`, `check_policy`, `read_audit`, etc.
- **Checkpoint:** A test client can call each tool and get the expected schema back.

### 7. Hooks

Implement the four hook entry points: SessionStart, UserPromptSubmit, PreToolUse, PostToolUse.

- **Output:** hook scripts in `hooks/` that the AI IDE invokes.
- **Checkpoint:** Configure the IDE to invoke them. Open a session. Verify the kernel is injected, a known-bad write is blocked, audit entries appear.

### 8. Phase orchestrator

Implement the 5-phase state machine. Persist to `phase.json`. Wire `PHASE_SKILLS` and `skills_satisfied()`.

- **Output:** phase advancement requiring human approval and skill artifacts.
- **Checkpoint:** Advancing without the artifact is rejected. Advancing with it succeeds.

### 9. Trust score

Compute and degrade trust. Persist to `metrics.json`.

- **Output:** trust updates after each write; degrades on rule violations.
- **Checkpoint:** Injected violations drop trust. Trust < 50 puts session in read-only mode.

### 10. RAG retriever

TF-IDF rule retrieval. Score the catalog against the active prompt; return top N.

- **Output:** `ai_ase.rag.retrieve(prompt, k=5)` returns most relevant rules.
- **Checkpoint:** Auth-related prompts retrieve auth rules first; Docker-related prompts retrieve Docker rules first.

### 11. Skill registry

Load and trigger skills per `_registry.yaml`.

- **Output:** skills auto-activate on matching events.
- **Checkpoint:** A mocked event triggers the expected skill.

### 12. Integration tests

Cover end-to-end: a session, a phase advance with artifacts, a rule violation blocking a write, a trust degradation cycle, an MCP tool call from a real client.

- **Checkpoint:** All tests pass. Policy module mutation kill rate > 40%.

---

## Stop conditions

Stop and ask the human if:

- The spec is ambiguous on a behavior — don't guess.
- A new external dependency seems needed — V4 says a file usually suffices.
- A test passes locally but fails on a clean checkout — something is order-dependent.
- You're tempted to add a feature not in the spec — file an issue first.

## Done definition

You are done when:

- All 12 steps are checked off
- All tests pass
- `ai-ase scan` and `ai-ase serve` work end-to-end
- Hooks are wired and verified by a real session
- Each of the 8 immutable rules has an enforcement point you can point to in code
- A new user can `pip install` and follow [examples/quickstart.md](../examples/quickstart.md) to a working setup

If any answer is "no" or "not sure," you are not done.

## Common failure modes

- **Skipping the read.** The most common reason rebuilds diverge from intent.
- **Inventing rules.** Only use the canonical catalog. Propose new rules via issue.
- **Collapsing phases.** Tempting; wrong. Five exist for reasons in [docs/05-architecture.md](../docs/05-architecture.md).
- **Adding infrastructure.** No vector DB. No microservices. No queues. Files on disk. (V4.)
- **Failing open.** If rule load fails, the system must surface the error and refuse to operate. Never silently allow.