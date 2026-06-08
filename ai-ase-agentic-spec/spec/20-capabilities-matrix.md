# Capabilities Matrix

## Purpose

`capabilities.py` is the single source of truth for what's actually shipped vs. what's specified-but-not-yet vs. what's planned. It is read by:

- The CLI's `ai-ase capabilities` subcommand.
- The dashboard ("framework status" card).
- The `test_claim_integrity.py` CI gate that prevents drift between docs and code.

Without this, the docs slowly diverge from reality. Every version of the framework I've watched grow had this problem; the matrix is the fix.

## The matrix

```python
CAPABILITIES: dict[str, str] = {
    # Engine
    "engine.scan":                    "implemented",
    "engine.detect_profile":          "implemented",
    "engine.detect_language":         "implemented",

    # CLI
    "cli.scan":                       "implemented",
    "cli.serve":                      "implemented",
    "cli.init":                       "implemented",
    "cli.phase.status":               "implemented",
    "cli.phase.advance":              "implemented",
    "cli.dashboard":                  "implemented",
    "cli.dashboard.html":             "implemented",
    "cli.adapter.copilot":            "implemented",
    "cli.adapter.ci":                 "implemented",
    "cli.hook.install":               "implemented",
    "cli.hook.handle":                "implemented",
    "cli.car.suggest":                "specified",       # 16-car-feedback.md, not yet code
    "cli.audit.rotate":               "planned",         # post-MVP

    # MCP server tools
    "mcp.validate_code":              "implemented",
    "mcp.get_active_rules":           "implemented",
    "mcp.governance_profile":         "implemented",
    "mcp.check_business_rule":        "implemented",
    "mcp.compute_trust_score":        "implemented",
    "mcp.get_skill":                  "implemented",
    "mcp.report_generation":          "implemented",
    "mcp.check_policy":               "implemented",
    "mcp.dry_run_preview":            "implemented",

    # Phase orchestrator
    "phase.archaeologist":            "implemented",
    "phase.guardian":                 "implemented",
    "phase.architect":                "implemented",
    "phase.critic":                   "implemented",
    "phase.reflector":                "implemented",
    "phase.skills_satisfied":         "implemented",
    "phase.business_authority_gate":  "implemented",

    # Hooks
    "hook.SessionStart":              "implemented",
    "hook.UserPromptSubmit":          "implemented",
    "hook.PreToolUse.Write":          "implemented",
    "hook.PreToolUse.Edit":           "implemented",
    "hook.PreToolUse.Bash":           "implemented",
    "hook.PostToolUse":               "implemented",

    # Skills
    "skill.challenge-me":             "implemented",
    "skill.business-rule-extraction": "implemented",
    "skill.guardrail-compliance-check": "implemented",
    "skill.architecture-design":      "implemented",
    "skill.adversarial-review":       "implemented",
    "skill.code-generation":          "implemented",
    "skill.code-review-gate":         "implemented",
    "skill.phase-gate-enforcement":   "implemented",
    "skill.business-authority-gate":  "implemented",
    "skill.mutation-testing":         "specified",       # registry present, runtime stub
    "skill.architecture-testing":     "specified",
    "skill.manifest-reconciliation":  "specified",
    "skill.adversarial-testing":      "specified",
    "skill.anti-hallucination-audit": "implemented",
    "skill.car-feedback-loop":        "specified",
    "skill.session-log-management":   "implemented",
    "skill.trust-score-analysis":     "implemented",
    "skill.guardrail-metrics":        "planned",
    "skill.blind-audit":              "planned",
    "skill.ai-security-review":       "implemented",
    "skill.concurrency-review":       "specified",

    # Other
    "trust.compute":                  "implemented",
    "policy.decide":                  "implemented",
    "audit.append":                   "implemented",
    "context.assemble":               "implemented",
    "session_log.export":             "implemented",
    "rag.search":                     "implemented",
    "agents.run_chain":               "specified",       # MVP single-agent; chain is post-MVP
}
```

Three states only:

| State | Meaning |
|---|---|
| `implemented` | Code exists, tests pass. Safe to advertise. |
| `specified` | Spec exists in `spec/`, no code or stub-only. Documented but not safe to call. |
| `planned` | Listed in roadmap. No spec yet. |

## Public interface

```python
def status(name: str) -> str: ...               # one of the three states

def list_by_status(state: str) -> list[str]: ...

def implementation_completeness() -> float: ...   # implemented / total

def render() -> str: ...                          # human-readable table
```

## The CI gate (`test_claim_integrity.py`)

This test is the **enforcement** for the matrix. It prevents the "the docs say it does X" / "the code does Y" drift that kills frameworks.

```python
def test_all_implemented_capabilities_have_executable_path():
    for name, state in CAPABILITIES.items():
        if state != "implemented": continue
        assert capability_is_callable(name), f"{name} marked 'implemented' but not callable"

def test_no_doc_promises_unimplemented_capability_without_marker():
    # Grep publish/ for capability names.
    # If a capability appears in docs as a feature claim without a 'specified' or 'planned' marker, fail.
    ...

def test_capabilities_keys_are_unique_and_sorted():
    ...
```

`capability_is_callable(name)` checks:

- For `mcp.X`: tool is registered in the FastMCP server's tool list.
- For `cli.X`: argparse parser includes that subcommand.
- For `hook.X`: dispatcher handles that event.
- For `skill.X`: registry contains it AND artifact validator works.

When a contributor adds a feature, they must update CAPABILITIES. The CI gate fails otherwise. The docs cannot drift.

## CLI subcommand

```bash
$ ai-ase capabilities
==================================================
  AI-ASE Capabilities  (v1.3.0)
==================================================
  implemented: 47 / 62  (76 %)
  specified:    8 / 62
  planned:      7 / 62
==================================================

  IMPLEMENTED (47)
    engine.scan
    engine.detect_profile
    ...

  SPECIFIED — present in docs, not yet code (8)
    cli.car.suggest        → spec/16-car-feedback.md
    skill.mutation-testing → spec/12-skills-system.md
    ...

  PLANNED — roadmap (7)
    cli.audit.rotate
    skill.guardrail-metrics
    ...
```

## Anti-patterns

| Don't | Because |
|---|---|
| Skip the matrix and trust docs | The drift always happens. Audit it programmatically. |
| Mark something `implemented` without tests | The matrix is a *truth* claim, not an *aspiration*. |
| Hide `specified` entries from users | Honest documentation is a feature. Don't pretend stubs are real. |
| Use 5 states (`partial`, `experimental`, etc.) | Three is enough. More states = more lies. |

## Ground truth

No vendored file. The matrix is canonical here.