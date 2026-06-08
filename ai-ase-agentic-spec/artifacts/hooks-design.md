# Hooks — Design Document

## Purpose

100% deterministic governance enforcement for Claude Code. Hooks fire on EVERY tool use — the AI doesn't decide whether to call them. They just happen.

## The Problem MCP Tools Couldn't Solve

MCP tools are probabilistic (~90-95%). The AI decides whether to call `validate_code`. In testing:
- Claude sometimes caught violations itself (didn't need the tool)
- Claude sometimes ignored the tools entirely
- Claude sometimes wrote violations and the user approved blind (no visibility)

Hooks solve all three: they fire regardless of what the AI decides.

## Architecture

```
User types prompt
  → [UserPromptSubmit hook: log prompt to .ai-ase/prompt-log.jsonl]
  → (tips only if AI_ASE_PROMPT_TIPS=1)

Claude generates code, calls Write tool
  → [PreToolUse hook: scan content against 71 rules]
    → BLOCK violation found → permissionDecision: deny → WRITE REJECTED
    → User sees: "VR-05: Double for money. Fix: use BigDecimal"
    → Claude told: "write was denied because..."
    → Clean → permissionDecision: allow → write proceeds

File written successfully
  → [PostToolUse hook: re-scan on disk, record to findings.json + write-log.jsonl]

User runs git commit
  → [pre-commit hook: reads findings.json, blocks if unresolved BLOCK violations]
```

## Protocol (Claude Code Hook Spec)

- **stdin**: Single JSON line: `{"hook_event_name": "...", "tool_name": "...", "tool_input": {...}}`
- **stdout**: JSON with `permissionDecision` (for PreToolUse) or plain text (for others)
- **Exit code**: ALWAYS 0 (exit 1 = "hook crashed" to Claude Code)
- **Key**: Use `sys.stdin.readline()` not `read()` — Claude Code keeps pipe open

## Hook Events (8 total)

### SessionStart
- **When:** Session opens
- **Does:** Prints governance announcement ("71 rules, 17 blocking, profile: X")
- **Why:** Claude and user both know enforcement is active

### UserPromptSubmit
- **When:** Every prompt submission
- **Does:** Logs prompt to `.ai-ase/prompt-log.jsonl` (timestamp, text, word count)
- **Tips:** Only shown if `AI_ASE_PROMPT_TIPS=1` (disabled by default — respects experienced devs)
- **Exit:** Always 0

### PreToolUse — Write
- **When:** Before any file write
- **Does:** Scans full file content against all rules for active profile
- **Why:** THIS IS THE ENFORCEMENT. Catches violations BEFORE they reach disk.
- **Output:** `permissionDecision: deny` + reason = write rejected. User sees why.
- **Timeout:** 10s

### PreToolUse — Edit
- **When:** Before any file edit (new_string > 10 chars)
- **Does:** Scans the new_string being inserted
- **Why:** Same enforcement as Write, for partial edits
- **Timeout:** 10s

### PreToolUse — Bash
- **When:** Before any shell command
- **Does:** Blocks dangerous commands via regex with word boundaries:
  - `rm -rf /` (root), `rm -rf ~` (home), `rm -rf .` (cwd)
  - `git push --force`, `git push -f`
  - `git reset --hard`
- **Why:** Prevents destructive operations
- **Note:** `rm -rf /some/path` is NOT blocked (only root/home/dot)
- **Timeout:** 5s

### PostToolUse — Write/Edit
- **When:** After successful write/edit
- **Does:** Re-scans file on disk. Records to findings.json + write-log.jsonl
- **Why:** Belt for the suspenders. Catches anything that slipped through PreToolUse.
- **Timeout:** 10s

### PostToolUseFailure
- **When:** Any tool call fails
- **Does:** Logs to .ai-ase/error-log.jsonl
- **Why:** Debugging, session forensics
- **Timeout:** 5s

### Notification
- **When:** Claude sends a notification
- **Does:** Logs to .ai-ase/notification-log.jsonl
- **Why:** Session tracking
- **Timeout:** 3s

## Installation

```bash
# One command — sets up everything
ai-ase init

# Or just hooks (global = all sessions)
ai-ase hook install --global

# Project-level only
ai-ase hook install
```

## Hook Command

All hooks call the same entry point: `ai-ase hook handle`

This reads JSON from stdin (Claude Code sends event data), dispatches by `hook_event_name`, returns appropriate response.

Portable: works on any machine after `pip install ai-ase`. No absolute paths.

## Field Normalization

Claude Code sends snake_case fields (`hook_event_name`, `tool_name`, `tool_input`). The handler normalizes to camelCase internally (`toolName`, `parameters`).

## Profile Detection

Order of precedence:
1. `AI_ASE_PROFILE` env var (patch/feature/migration/incident)
2. Git branch name: `hotfix/*` or `fix/*` → patch, `migrate/*` → migration
3. Default: feature

## Self-Exclusion

The hook handler doesn't scan:
- Its own source files (hook_handler.py, hooks.py, cli.py, findings.py) — prevents VR-27 bootstrapping loop
- Test files (test_*) — contain violation patterns as test data

## Inline Suppression

Developers can suppress false positives per-line:
```java
private Double price; // ai-ase:ignore VR-05
private Double total; // ai-ase:ignore-all
```

## Findings Store

- **Location:** `.ai-ase/findings.json`
- **Lifecycle:** Record on violation → persist across user approvals → clear only when code is fixed
- **Pre-commit:** `ai-ase hook pre-commit` rescans all files with findings, blocks if BLOCK violations remain
- **Key insight:** User approval ≠ resolution. Only fixing the code resolves a finding.

## Mutation Testing Results (2026-05-09)

| Module | Mutants | Kill Rate |
|--------|---------|-----------|
| findings.py | 156 | 91.7% |
| hooks.py | 334 | 80.8% |
| hook_handler.py | 380 | 72.1% |

Total: 870 mutants tested, ~80% effective kill rate. Residual survivors are equivalent mutants (string constants ±1, cosmetic).

## Key Insight

The enforcement stack has three layers, all 100% deterministic:
1. **PreToolUse hook** — catches at write-time (developer sees violation immediately)
2. **Pre-commit hook** — catches at commit-time (blocks git commit)
3. **CI workflow** — catches at PR-time (blocks merge)

MCP tools are ADVISORY (help AI write better code). Hooks are ENFORCEMENT (prevent bad code from reaching disk/repo).