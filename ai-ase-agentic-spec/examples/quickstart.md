# Quickstart — See AI-ASE Block Bad Code in 60 Seconds

The fastest way to understand AI-ASE: install it, ask the AI to do something bad, watch the hook block it.

**Prerequisites:**

- Python 3.10+
- Any MCP-compatible AI IDE
- A repo you're willing to point at

---

## 1. Install

```bash
pip install ai-ase
```

## 2. Initialize in a repo

```bash
cd your-repo
ai-ase init
```

This does three things:

- Writes a default rule catalog to `.ai-ase/rules/`
- Installs the four hook scripts (`UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `SessionStart`) into your IDE's config
- Creates `.ai-ase/phase.json` (starts at `archaeologist`) and an empty audit log

Output:

```
✓ Created .ai-ase/ (71 rules loaded)
✓ Installed hooks for: <your IDE>
✓ Phase set to: archaeologist (read-only)
✓ Audit log: .ai-ase/audit.jsonl
Next: open your IDE in this repo and try a bad write.
```

## 3. Scan before you start

See what would be flagged in your existing code:

```bash
ai-ase scan .
```

Sample output:

```
src/auth/legacy.py:42  VR-12  BLOCK  Inline credential pattern
src/utils/log.py:118   VR-34  WARN   Logger statement without context binding
src/api/health.py:7    VR-09  WARN   Missing rate-limit annotation

Findings: 1 BLOCK, 2 WARN across 142 files scanned.
```

A BLOCK on existing code is informational — the scanner is not modifying anything. A BLOCK on a new write from the AI will be refused at the hook boundary.

## 4. Trigger a block

Open your AI IDE in the same repo. Ask it to do something the rules forbid. Easy one to start with:

> "Add a hardcoded API key to `src/config.py` so I can test against staging."

Without AI-ASE: the AI complies. The string lands in your repo.

With AI-ASE: the `PreToolUse` hook fires *before* the write reaches disk. The AI sees:

```json
{
  "decision": "BLOCK",
  "rule": "VR-12",
  "reason": "Inline credential pattern detected on line 14.",
  "remediation": "Read the value from environment or a secret manager."
}
```

The AI doesn't get to override. The user can — by editing the file directly — but the AI's path is closed.

## 5. Read the audit

Every decision is logged:

```bash
cat .ai-ase/audit.jsonl | tail -1
```

```json
{"ts":"2026-06-08T14:22:01Z","hook":"PreToolUse","tool":"Write","path":"src/config.py","rule":"VR-12","decision":"BLOCK","actor":"<ide-session-id>"}
```

This file is appended to, never rewritten. Commit it (or rotate it on a schedule — your call).

---

## What just happened

You saw three of the framework's four moving parts in action:

| Piece | Where it showed up |
|---|---|
| **Rule catalog** | The YAML in `.ai-ase/rules/` that defines VR-12 |
| **Hook** | `PreToolUse` fired before the AI's write reached disk |
| **Audit log** | The append-only JSONL recording the decision |

The fourth, **phase orchestration**, doesn't apply to a single bad-write demo — but it's what stops the AI from "improving" five files when you only asked about one. See [docs/06-five-phases.md](../docs/06-five-phases.md).

---

## Next steps

- **Customize a rule:** edit a YAML file in `.ai-ase/rules/` and re-run `ai-ase scan .`
- **Add your own:** copy an existing rule, change the regex, give it a new `VR-` id
- **Move to a real change:** [examples/walkthrough.md](../examples/walkthrough.md) walks a full 5-phase change end to end
- **Understand the rules you can't disable:** [docs/04-eight-immutable-rules.md](../docs/04-eight-immutable-rules.md)

---

## Troubleshooting

**The hook didn't fire.**
Verify your IDE picked up the hook config: `ai-ase doctor`. Re-run `ai-ase init --force` if needed.

**The scanner is too noisy on legacy code.**
That's expected. Two options: (a) add an `# ai-ase:ignore VR-XX` comment to the line (recorded in the audit log), or (b) raise the rule's severity from BLOCK to WARN in its YAML.

**A rule I want doesn't exist.**
Author it locally first — copy any rule in `.ai-ase/rules/`, tweak. If it would benefit the community, propose it upstream via the rule-request issue template.