# Hooks Runtime

## Purpose

Hooks are the **teeth** of AI-ASE. MCP tools are probabilistic — the AI decides whether to call them. Hooks fire on every tool use regardless of what the AI decides. This is where rules go from "advisory" to "enforced".

Two files:

- `src/ai_ase/hooks.py` — installation: writes the hook config that the AI IDE loads.
- `src/ai_ase/hook_handler.py` — the runtime: invoked as a subprocess per hook event, reads JSON from stdin, returns the decision.

## The 4 hook events

The framework standardizes on the 4 events common to mainstream AI IDEs:

| Event | When | What the framework does |
|---|---|---|
| `SessionStart` | session opens | Announces governance is active; sets `AI_ASE_SESSION_ID`; injects nothing into context (just side effects + audit). |
| `UserPromptSubmit` | every user prompt | Injects the 50-line kernel + active phase via the IDE's prompt-injection mechanism. Logs prompt metadata (length, hash) to `.ai-ase/prompt-log.jsonl`. |
| `PreToolUse` | before any `Write`, `Edit`, `Bash` | The enforcement point. Scans the content. Denies BLOCK violations. Denies destructive `Bash` commands. |
| `PostToolUse` | after successful `Write`/`Edit` | Re-scans on disk (belt for suspenders). Appends to `findings.json` + audit log. |

## Hook contract (Claude Code-compatible — used as the lingua franca)

The handler is invoked as a subprocess. Communication:

- **stdin:** single line of JSON
- **stdout:** single JSON document
- **exit code:** ALWAYS 0 (exit ≠ 0 = "hook crashed" to the IDE, which silently disables further hooks)
- **stderr:** human-readable diagnostics only; the IDE may surface these to the user

### Input shape

```json
{
  "hook_event_name": "PreToolUse",
  "tool_name": "Write",
  "tool_input": {
    "file_path": "src/x.py",
    "content": "..."
  },
  "session_id": "s-9f3a"
}
```

### Output shape (PreToolUse)

```json
{
  "permissionDecision": "allow"
}
```

Or, to block:

```json
{
  "permissionDecision": "deny",
  "permissionDecisionReason": "VR-10 BLOCK: float for money. Use Decimal."
}
```

### Output shape (PostToolUse, SessionStart, UserPromptSubmit)

A short JSON `{"acknowledged": true}` or empty `{}`. These hooks don't gate, they observe.

## Reading stdin — critical

```python
import sys, json
line = sys.stdin.readline()      # NOT sys.stdin.read()
event = json.loads(line)
```

The IDE keeps the pipe open across multiple events. `read()` blocks forever. `readline()` returns one event at a time.

## `hooks.py` — installation

```python
def install(scope: str = "project") -> Path:
    """scope: 'project' (writes to .claude/settings.local.json or .vscode/settings.json) or 'global' (~/...)"""
```

Generates a settings file (per-IDE shape) that wires every hook event to `ai-ase hook handle`. Reference shape:

```json
{
  "hooks": {
    "SessionStart":      [{"hooks": [{"type": "command", "command": "ai-ase hook handle"}]}],
    "UserPromptSubmit":  [{"hooks": [{"type": "command", "command": "ai-ase hook handle"}]}],
    "PreToolUse":        [{"hooks": [{"type": "command", "command": "ai-ase hook handle"}]}],
    "PostToolUse":       [{"hooks": [{"type": "command", "command": "ai-ase hook handle"}]}]
  }
}
```

See [artifacts/example-settings.json](../artifacts/example-settings.json) for the canonical example.

The framework writes the file using `pathlib` and `json.dump(indent=2)`. If a settings file already exists, it merges (preserves user keys, adds/updates `hooks`).

## `hook_handler.py` — the dispatcher

```python
def main() -> int:
    event = json.loads(sys.stdin.readline())
    name = event["hook_event_name"]
    handler = DISPATCH.get(name, handle_unknown)
    try:
        response = handler(event)
    except Exception as e:
        audit.append("error", module="hook_handler", message=str(e))
        response = {}
    print(json.dumps(response))
    return 0    # ALWAYS 0
```

```python
DISPATCH = {
    "SessionStart":     handle_session_start,
    "UserPromptSubmit": handle_user_prompt_submit,
    "PreToolUse":       handle_pre_tool_use,
    "PostToolUse":      handle_post_tool_use,
}
```

### `handle_session_start(event)`

```
1. session_id = generate_or_resolve_session_id()
2. os.environ["AI_ASE_SESSION_ID"] = session_id   # for subsequent subprocesses
3. profile = active_profile()["id"]
4. audit.append("session_start", profile=profile)
5. stderr print: "AI-ASE active. profile={profile}, 71 rules, 17 blocking."
6. return {}
```

### `handle_user_prompt_submit(event)`

```
1. prompt = event.get("prompt", "")
2. append_jsonl(".ai-ase/prompt-log.jsonl", {
     "ts": utcnow(), "session_id": ..., "len": len(prompt),
     "hash": sha256(prompt)[:16],
   })
3. kernel = context.inject_kernel(profile=active_profile()["id"],
                                  phase=current_phase().value,
                                  budget=profile_budget())
4. return {"additionalContext": kernel}   # IDE-specific field name; check the IDE's hook spec
```

### `handle_pre_tool_use(event)`

```
1. tool = event["tool_name"]
2. if tool == "Bash":
3.   cmd = event["tool_input"].get("command", "")
4.   if policy.matches_destructive(cmd):
5.     return {"permissionDecision":"deny","permissionDecisionReason":f"Destructive command blocked: {cmd}"}
6.   return {"permissionDecision":"allow"}
7. if tool in ("Write", "Edit"):
8.   content = event["tool_input"].get("content") or event["tool_input"].get("new_string","")
9.   filepath = event["tool_input"]["file_path"]
10.  if tool == "Edit" and len(content) <= 10: return {"permissionDecision":"allow"}    # trivial edit
11.  result = engine.validate(content, filepath, active_profile()["id"])
12.  audit.append("validation", file=filepath, decision="deny" if result.blocks else "allow",
                  violations=[v.rule_id for v in result.blocks])
13.  if result.blocks:
14.    reason = "; ".join(f"{v.rule_id}: {v.description}. Fix: {v.fix_guidance}" for v in result.blocks)
15.    return {"permissionDecision":"deny","permissionDecisionReason":reason}
16.  return {"permissionDecision":"allow"}
17. return {"permissionDecision":"allow"}   # unknown tool: permissive default (IDE-controlled tools)
```

### `handle_post_tool_use(event)`

```
1. tool = event["tool_name"]
2. if tool not in ("Write","Edit"): return {}
3. filepath = event["tool_input"]["file_path"]
4. if not Path(filepath).exists(): return {}
5. result = engine.validate(Path(filepath).read_text(), filepath, active_profile()["id"])
6. findings.append(filepath, result)
7. audit.append("validation", file=filepath, decision="allow" if not result.blocks else "deny-postwrite",
                violations=[v.rule_id for v in result.blocks])
8. return {}
```

`deny-postwrite` indicates a BLOCK violation slipped through PreToolUse (shouldn't happen, but if it does, surface it).

## Timeouts

The IDE will kill the hook if it takes too long. Targets:

| Event | Soft timeout | Hard timeout |
|---|---|---|
| SessionStart | 2 s | 5 s |
| UserPromptSubmit | 2 s | 5 s |
| PreToolUse | 5 s | 10 s |
| PostToolUse | 5 s | 10 s |

To stay fast: cache loaded rules (mtime-keyed), avoid network I/O, never spawn subprocesses inside the handler.

## Tests (target ≥ 25)

- Each hook event dispatches correctly.
- Unknown event returns empty `{}` and logs.
- PreToolUse `Write` with clean content → allow.
- PreToolUse `Write` with VR-01 content → deny + reason mentions VR-01.
- PreToolUse `Bash` with `rm -rf /` → deny.
- PreToolUse `Bash` with `rm -rf /tmp/scratch` → allow (boundary).
- PostToolUse re-scans the file on disk.
- All hooks exit 0 even when handler raises.
- `install("project")` is idempotent.
- `install("global")` writes to home directory.

## Anti-patterns

| Don't | Because |
|---|---|
| Use `sys.stdin.read()` | Blocks forever. Use `readline()`. |
| Exit non-zero on validation failure | Exit 0 always. The decision is in the JSON response. |
| Print debugging to stdout | Stdout is the JSON channel. Use stderr. |
| Make network calls inside hooks | Latency budget is single-digit seconds. Stay local. |
| Modify the user's hook config silently | `install()` merges and shows a diff before writing in non-`--force` mode. |
| Block on `Read` tool | Reads are free (GP3). Hooks only intercept mutations. |

## Ground truth

- [artifacts/hooks-design.md](../artifacts/hooks-design.md) — the original design doc.
- [artifacts/example-settings.json](../artifacts/example-settings.json) — a working settings file.
- [ai-ide-research/03-hook-evasion.md](../ai-ide-research/03-hook-evasion.md) — known evasion patterns to defend against.
- [ai-ide-research/07-model-vs-hook.md](../ai-ide-research/07-model-vs-hook.md) — what the model vs the hook controls.
