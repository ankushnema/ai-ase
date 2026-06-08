# Audit Log

## Purpose

`audit.py` writes an immutable, append-only JSONL trail of every governance-relevant event. The dashboard reads it. The trust score consumes it. Post-incident forensics rely on it.

V2 (Transparency) + V7 (Files Are Universal Interface): a grep-able file on disk, not a database.

## File location

`.ai-ase/audit-log.jsonl` (per-project).

## Event schema

Every line is a single JSON object. The fields:

| Field | Type | Required | Notes |
|---|---|---|---|
| `ts` | ISO 8601 string | yes | UTC. `2026-06-08T10:14:02.123Z` |
| `event` | string | yes | enum below |
| `session_id` | string | yes | Correlation ID (random per session) |
| `correlation_id` | string | no | When this event was caused by another event |
| `actor` | string | no | `ai`, `human:user@company`, `system` |
| `tool` | string | no | MCP tool name if applicable |
| ... | any | no | Event-specific fields |

## Event types

| Event | Required fields | When |
|---|---|---|
| `session_start` | `profile` | `SessionStart` hook |
| `session_end` | `duration_ms` | `SessionEnd` (synthetic) |
| `phase_change` | `from`, `to`, `approver` | `phase_orchestrator.advance()` |
| `profile_change` | `from`, `to`, `approver` | `ai-ase init --force` |
| `validation` | `file`, `decision` (`allow`\|`deny`), `violations` (list of rule IDs) | every `PreToolUse` write/edit + every `validate_code` MCP call |
| `policy_check` | `subject`, `action`, `decision` | `policy.decide()` |
| `tool_call` | `tool`, `args_hash`, `result_summary` | every MCP tool invocation |
| `trust_score` | `score`, `band`, `components` | `trust.compute()` |
| `car_rule_added` | `rule_id`, `source` | `car-feedback-loop` skill |
| `skill_completed` | `skill_id`, `artifact_path` | skill produces artifact |
| `gate_blocked` | `gate`, `reason` | any gate skill blocks |
| `hook_event` | `hook`, `tool_name`, `decision` | every hook invocation |
| `error` | `module`, `message` | uncaught exception in any module |

The enum is extensible; new events must be added to `audit.EventType` and documented here.

## Public interface

```python
def append(event: str, **fields) -> None: ...

def session_id() -> str: ...           # current session, cached for process lifetime

def correlation() -> contextmanager: ...   # context manager: generates a correlation_id

def read(limit: int | None = None) -> Iterator[dict]: ...

def filter(event: str | None = None, since: datetime | None = None) -> Iterator[dict]: ...
```

## Algorithm: `append(event, **fields)`

```
1. record = {
     "ts": utcnow().isoformat() + "Z",
     "event": event,
     "session_id": session_id(),
     **fields,
   }
2. line = json.dumps(record, separators=(",",":"), default=str)
3. with open(".ai-ase/audit-log.jsonl", "a", encoding="utf-8") as f:
     f.write(line + "\n")
4. fsync optional (skip — performance).
```

**Idempotency:** The same logical event called twice writes two lines. Audit is a trail, not a set.

**Atomicity:** A single `write()` call of a single line is atomic on POSIX & NTFS for typical line lengths (<4 KB). For longer events, write to a `.tmp` and rename.

## Algorithm: `session_id()`

```
1. If env var AI_ASE_SESSION_ID set → return it.
2. Else: generate `s-<8 hex>` once per process, cache it.
3. Persist to `.ai-ase/current-session.txt` (overwritten on each new process).
```

The SessionStart hook is responsible for setting `AI_ASE_SESSION_ID` so all subprocesses share a session.

## Algorithm: `correlation()` (context manager)

```
@contextmanager
def correlation():
    cid = "c-" + token_hex(4)
    token = _ctx_var.set(cid)
    try:
        yield cid
    finally:
        _ctx_var.reset(token)
```

Then `append()` reads `_ctx_var` if set and includes `correlation_id` in the record. Lets a chain of tool calls share a correlation ID without explicit threading.

## Rotation

Not in MVP. Audit log grows forever. Add `ai-ase audit rotate` (post-MVP) to compress files older than N days.

## Tests (target ≥ 22)

- `append()` writes a valid JSON line.
- Each line ends with `\n`.
- File is created if missing.
- Concurrent writes from two processes both land (POSIX guarantee within ≤ PIPE_BUF).
- `read()` returns parsed dicts.
- `filter(event="validation")` returns only validation events.
- `correlation()` propagates the correlation ID.
- Schema: every required field present per event type.

## Anti-patterns

| Don't | Because |
|---|---|
| Buffer writes | Audit must be durable. A crash should not lose the last 5 entries. |
| Truncate or rewrite the file | Append-only. Period. |
| Include credentials / file contents in events | Audit is checked into git in some repos. Treat it as visible. |
| Use a database | V7 + V4. A file is enough. Grep is enough. |

## Ground truth

No vendored file (audit logs are per-project, generated at runtime). The dashboard spec ([19-DASHBOARD.md](../spec/19-dashboard.md)) documents which events the dashboard expects to read.