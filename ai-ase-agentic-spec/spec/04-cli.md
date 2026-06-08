# CLI

## Purpose

`cli.py` is the single console entry point. Every operational command (`scan`, `serve`, `init`, `phase`, `dashboard`, `adapter`, `hook`, `rules`, `version`) routes through here.

## Public interface

```bash
ai-ase scan <path> [--profile PROFILE] [--quiet] [--json]
ai-ase serve
ai-ase init [--profile PROFILE] [--force]
ai-ase phase status
ai-ase phase advance [--approve]
ai-ase dashboard [--html FILE] [--profile PROFILE]
ai-ase adapter copilot [--profile PROFILE] [--output DIR]
ai-ase adapter ci      [--profile PROFILE] [--output DIR]
ai-ase hook install [--global] [--project]
ai-ase hook handle              # invoked by hook subprocess
ai-ase rules [--profile PROFILE]
ai-ase version
```

## Entry point

```python
def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return dispatch(args)
```

`pyproject.toml` maps `ai-ase = "ai_ase.cli:main"`.

## Subcommand contracts

### `scan <path>`

```
1. Resolve path → file or directory.
2. If directory: walk; skip {.git, node_modules, __pycache__, .venv, venv, dist, build, target, .idea}.
3. For each file with a known extension: read content, call engine.validate().
4. Print per-file violations (BLOCK always, WARN unless --quiet).
5. Print summary: X BLOCK, Y WARN across N files.
6. Append validation events to audit log (see 10-AUDIT-LOG).
7. Exit code: 1 if any BLOCK, else 0.
8. --json: write a single JSON document instead of formatted output.
```

### `serve`

```
1. from .server import main as serve_main
2. serve_main()        # blocks; runs FastMCP stdio transport
```

### `init`

```
1. mkdir .ai-ase/ if missing
2. Write .ai-ase/profile.json    {"profile": "feature"}
3. Write .ai-ase/phase.json      {"phase": "archaeologist", "history": []}
4. Write .ai-ase/trust.json      {"score": 70, "band": "good", "components": {}}
5. Write .mcp.json at workspace root if missing (see 22-MCP-CONNECTION)
6. Call hook install --project (see 15-HOOKS-RUNTIME)
7. Print summary of files written.
8. --force: overwrite existing files (otherwise: skip with notice)
```

### `phase status` / `phase advance`

See [09-PHASE-ORCHESTRATOR.md](../spec/09-phase-orchestrator.md). The CLI is a thin wrapper around `phase_orchestrator.status()` and `.advance()`.

### `dashboard`

See [19-DASHBOARD.md](../spec/19-dashboard.md).

### `adapter copilot` / `adapter ci`

See [14-PLATFORM-ADAPTERS.md](../spec/14-platform-adapters.md).

### `hook install` / `hook handle`

See [15-HOOKS-RUNTIME.md](../spec/15-hooks-runtime.md). `hook handle` reads JSON from stdin and dispatches.

### `rules`

```
1. rules = load_rules(find_rules_path(cwd))
2. filter by --profile
3. Print: total, BLOCK rules table (id, name, severity), WARN rules table.
```

### `version`

Prints `ai_ase.__version__`.

## Output format (scan)

```
══════════════════════════════════════════════════════
  AI-ASE Guardrail Scanner v{version}
══════════════════════════════════════════════════════

Scanning {N} files (profile: {profile})...

  BLOCK  {rule_id}  {filepath}:{line}
         {rule_name}
         `{line_content}`
         Fix: {fix_guidance}

  WARN   {rule_id}  {filepath}:{line}
         {rule_name}
         `{line_content}`

──────────────────────────────────────────────────────
  Results: {blocks} BLOCK, {warns} WARN
  Files scanned: {count}
  Profile: {profile}

  Status: PASSED | FAILED (fix N blocking violations before commit)
══════════════════════════════════════════════════════
```

## Argparse structure

Use `argparse` with subparsers. Do NOT introduce Click or Typer (V4 — keep deps minimal).

```python
parser = argparse.ArgumentParser(prog="ai-ase")
sub = parser.add_subparsers(dest="command", required=True)
sub.add_parser("scan", ...)
sub.add_parser("serve")
sub.add_parser("init", ...)
phase = sub.add_parser("phase")
phase_sub = phase.add_subparsers(dest="phase_command", required=True)
phase_sub.add_parser("status")
phase_sub.add_parser("advance", ...)
# etc.
```

## Tests

- Each subcommand: arg parsing, dispatch, exit code.
- `scan` against a directory with clean + violating fixtures: correct exit code.
- `init` is idempotent without `--force`; overwrites with `--force`.
- `version` matches `ai_ase.__version__`.
- Skipped-directory list is honored.

## Anti-patterns

| Don't | Because |
|---|---|
| Print stack traces to stderr on user error | Use `parser.error()` or a short message. |
| Mix logging frameworks | Plain `print`. CLI output is a UI. |
| Read stdin in `scan` | `scan <path>` operates on files. `hook handle` is the only stdin consumer. |
| Hide BLOCK violations behind `--quiet` | `--quiet` only hides WARN. BLOCK is always shown. |

## Ground truth

No standalone reference file. The behavior is exercised by `artifacts/examples/01_basic_scan.py`.