# MCP Server

## Purpose

`server.py` exposes the 9 governance tools over the Model Context Protocol so any MCP-aware AI IDE can call them. Stdio transport, JSON-RPC 2.0.

## Library

```python
from mcp.server.fastmcp import FastMCP
mcp = FastMCP("ai-ase-governance")

@mcp.tool()
def tool_name(...) -> str:
    ...
    return "markdown report string"

def main() -> None:
    mcp.run(transport="stdio")
```

**Important.** `FastMCP()` constructor takes only a name string — no `version`, no `description` kwargs in v1.0+.

## The 9 tools

The contracts are catalogued in [../catalogs/tools.md](../catalogs/tools.md). The server-side implementation is a thin wrapper around other modules:

| Tool | Backing module |
|---|---|
| `validate_code` | `engine.validate()` |
| `get_active_rules` | `engine.load_rules()` + filter |
| `governance_profile` | `engine.detect_profile()` |
| `check_business_rule` | YAML lookup in `business-guardrails.md` + rule registry |
| `compute_trust_score` | `trust.compute()` |
| `get_skill` | `skills.get_by_id()` |
| `report_generation` | `findings.summarize()` |
| `check_policy` | `policy.decide()` |
| `dry_run_preview` | calls `validate_code` + simulates write without I/O |

## Tool descriptions matter

The text in `@mcp.tool()` decorators (and the docstring) **steers the AI's decision to call the tool**. The reference rate is ~90–95 % when the description is action-oriented and tells the AI *when* to call. Bad descriptions drop this to ~60 %.

Good:
```python
@mcp.tool()
def validate_code(code: str, filename: str, profile: str = "feature") -> str:
    """Check code against AI-ASE guardrail rules BEFORE writing it to a file.
    Call this before every file edit. Returns ALLOWED or a list of violations
    with rule IDs, line numbers, and fix guidance."""
```

Bad:
```python
@mcp.tool()
def validate_code(code: str, filename: str) -> str:
    """Validates code."""
```

## Output format

Every tool returns a markdown string. Markdown is the lingua franca of AI context. Use:

- `## Heading` for sections
- Tables for tabular data
- Backticks for code
- Bold for emphasis
- Bullet lists for findings

Example `validate_code` output:

```markdown
## Scan Result: src/charges/refund_service.py
**Profile:** feature  **Status:** BLOCKED (1 BLOCK, 2 WARN)

### BLOCK Violations
| Rule | Line | Issue |
|---|---|---|
| VR-10 | 42 | Float for money. Use Decimal. |

### Warnings
| Rule | Line | Issue |
|---|---|---|
| VR-22 | 18 | Hardcoded timeout. Externalize to config. |
| VR-31 | 67 | Magic number. Extract a constant. |

### Fix Guidance
**VR-10:** Replace `float(amount)` with `Decimal(str(amount))`. Import from `decimal`.
```

## Side-effects

Every tool call MUST append an `audit.py` event with the tool name, arguments hash, result decision, and correlation ID. See [10-AUDIT-LOG.md](../spec/10-audit-log.md).

## Tests (target ≥ 49)

- Each tool: argument validation, expected output shape.
- `validate_code` returns ALLOWED for clean fixture, BLOCKED for violating fixture.
- `dry_run_preview` does NOT write to disk (use `monkeypatch` on `open` / `Path.write_text`).
- Tool registration: enumerate `mcp._tools` and assert all 9 are present.
- Audit log: each tool call produces exactly one audit event.

## Tests — anti-circular-validation

The MCP server must not be the only thing validating its own output. `test_mutation.py` mutates a tool's return value and asserts that *some* external test (an integration test, a hook test) catches the mutation. This is V2 (Transparency) — the server cannot be trusted to judge itself.

## Anti-patterns

| Don't | Because |
|---|---|
| Use HTTP transport | The spec is stdio. HTTP introduces auth, networking, lifecycle complexity. |
| Cache the rules at import time | The CLI may modify rules between calls. Load on each invocation. |
| Return free-form prose | The AI consumes structured markdown better. |
| Swallow exceptions inside tools | Return a markdown error block. Crashing the server kills the AI session. |
| Accept arbitrary file paths | `validate_code` takes a string `code` argument, not a filepath. Avoids file-read security issues. |

## Ground truth

[catalogs/tools.md](../catalogs/tools.md) is the canonical tool surface this server exposes. [artifacts/examples/02_mcp_integration.json](../artifacts/examples/02_mcp_integration.json) shows how an IDE connects.