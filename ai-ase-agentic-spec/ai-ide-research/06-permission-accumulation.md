# Permission Accumulation

*Every "Allow always" permanently expands the attack surface — your allowlist has 49 entries*

## Your Current Permission Surface — Live Audit

- **49** Total Entries
- **4** HIGH Risk
- **8** MEDIUM Risk
- **~20** Stale / One-off

Source: `C:\Users\username\ds\.claude\settings.local.json` — accumulated over multiple sessions. Never manually reviewed or pruned.

## How Permission Accumulation Happens

*The "Allow always" trap*

```
Session 1: You're debugging, need to run tests
  Claude: "Can I run ./mvnw test?"
  You: [Allow always]  ← saves "Bash(./mvnw test:*)" permanently

Session 5: You're doing file cleanup
  Claude: "Can I delete old files?"
  You: [Allow always]  ← saves "Bash(rm:*)" permanently

Session 12: You're killing a hung process
  Claude: "Can I kill the process?"
  You: [Allow always]  ← saves "Bash(taskkill:*)" permanently

Session 30: You forgot you ever allowed these.
  Claude can now silently: delete any file, kill any process, run any test.
  No prompt. No confirmation. No audit trail.
```

**The problem:** "Allow always" is permanent, broad, and invisible. You click it once in context (debugging a specific issue) but it persists forever (across all future sessions and contexts).

> **Pain point:** There's no expiry, no review prompt, no audit log. Permissions accumulate monotonically — they only grow, never shrink, unless you manually edit settings.json.

## Your Allowlist — Risk Categorization

*4 HIGH risk entries found*

**HIGH RISK — Broad destructive capabilities:**

| Entry | Risk | What it allows |
|---|---|---|
| `Bash(rm:*)` | HIGH | Delete ANY file or directory without prompting. Model could `rm -rf` with no confirmation. |
| `Bash(taskkill:*)` | HIGH | Kill ANY Windows process. Could terminate critical services. |
| `Bash(cp:*)` | HIGH | Copy ANY file anywhere. Could overwrite important files or exfiltrate data. |
| `Read(//c/Users/username/**)` | HIGH | Read ANY file in your user directory. Includes .ssh, credentials, personal files. |

**MEDIUM RISK — Broad but contextual:**

| Entry | Risk | What it allows |
|---|---|---|
| `Read(//i/**)` | MEDIUM | Read entire I: drive without prompting |
| `Bash(pkill -f "stock-trading")` | MEDIUM | Kill specific process — narrow but destructive |
| `Bash(cosmic-ray:*)` | MEDIUM | Run mutation testing framework (mutates code files) |
| `Bash(./mvnw spring-boot:run)` | MEDIUM | Start a server — binds ports, consumes resources |

**STALE — One-off commands that no longer apply:**

| Entry | Risk | Likely context |
|---|---|---|
| `Bash(grep 'VR-' .../registry.yaml)` | STALE | One-time AI-ASE rule lookup — overly specific |
| `Bash(echo 'public class X ...')` | STALE | Testing hook detection — no longer needed |
| `Bash(cr-report session.sqlite)` | STALE | One-time mutation test report |
| `Bash(mutatest --src ...)` | STALE | Very specific command from a past session |

> **Insight:** ~20 of 49 entries are stale one-off commands that were useful in a single session and will never match again. They're harmless but clutter the allowlist and make it hard to audit the entries that DO matter.

## Security Implications

*What a compromised model could do with your allowlist*

**Scenario:** If a prompt injection or model misbehavior occurred, your current allowlist permits:

- Delete any file: `rm -rf ~/important-project` — no prompt
- Kill any process: `taskkill /f /im critical-service.exe` — no prompt
- Read any file: `Read ~/.ssh/id_rsa` — no prompt
- Copy files anywhere: `cp sensitive.db /tmp/exfil/` — no prompt
- Start services: `./mvnw spring-boot:run` — binds ports

**Mitigating factors:**

- AI-ASE PreToolUse hook — still scans all tool calls for content violations (but checks content, not command safety)
- Model training — Claude resists destructive actions even without permission checks
- Internal network — no external exfiltration path via API (stays in your organization)

> **Pain point:** The gap: AI-ASE's PreToolUse hook scans for CODE CONTENT violations (secrets, patterns). It does NOT check whether a Bash command is destructive. `rm -rf /` would sail through VR-01 through VR-67 because it doesn't contain a hardcoded credential — it's just a dangerous command. The permission system is your only defense for command safety, and it's been eroded by "Allow always" clicks.

## Best Practices for Permission Hygiene

*How to manage the allowlist properly*

| Practice | Why |
|---|---|
| **Prefer "Allow once" over "Allow always"** | One-time permission doesn't persist. Use for unusual/rare commands. |
| **Use specific patterns, not wildcards** | `Bash(rm *.pyc)` is safer than `Bash(rm:*)` |
| **Review settings.local.json monthly** | Prune stale entries, tighten broad ones. 5 minutes prevents drift. |
| **Never allow `rm:*` or `taskkill:*`** | These are nuclear — always prompt for destructive operations |
| **Separate project settings from user settings** | Project-specific allows go in project settings, not global |
| **Audit after major work sessions** | The "Allow always" impulse is strongest when you're deep in debugging — review after |

> **Why it works:** Recommended cleanup for your current allowlist:
>
> - Remove `Bash(rm:*)` — always prompt for deletions
> - Remove `Bash(taskkill:*)` — always prompt for process kills
> - Narrow `Bash(cp:*)` to specific directories if needed
> - Remove ~20 stale one-off entries (the overly-specific grep/echo commands)
> - Keep: `ai-ase` commands, `Read` permissions, `mvnw test`

## What AI-ASE Could Add: Permission Governance

*Proposed new capability*

AI-ASE currently governs CODE CONTENT. It should also govern COMMAND SAFETY:

| Feature | How | Effort |
|---|---|---|
| **Dangerous command detection** | PreToolUse hook blocks `rm -rf`, `git push --force`, `DROP TABLE` regardless of allowlist | Medium |
| **Permission audit report** | Periodic scan of settings.json, flag broad/dangerous entries, suggest tightening | Low |
| **Permission expiry** | Auto-expire "Allow always" after 7 days unless re-confirmed | Requires Claude Code changes (not hook-level) |
| **Scope limiting** | Allow `rm` only within project directory, not globally | Medium (path-aware matching in hook) |

> **Insight:** The immediate win: A PreToolUse rule that blocks obviously destructive commands (`rm -rf /`, `git push --force origin main`, `DROP DATABASE`) regardless of permission allowlist. Like VR-01 for secrets, but for dangerous shell operations. Call it VR-70: Destructive Command Without Confirmation.

## Proposed Hook: Permission Audit at Session Start

*Aspirational design — not currently shipped*

> **Pain point:** Important framing: The Claude Code permission system runs at the *harness* layer, not the hook layer. A hook cannot intercept and override an "allow always" decision in real time — by the time a hook fires, the harness has already consulted the allowlist. What a hook *can* do is read `settings.json` at session start and **surface a warning** via the governance kernel. That's the design proposed below. It's aspirational; it does not exist in AI-ASE today.

**Where:** UserPromptSubmit hook — fires on first user message of every session.
**When:** Only on the FIRST invocation per session (use a session marker file to avoid repeating every turn).
**What user sees:** A warning block injected into the governance kernel if risky permissions are found.
**What this hook cannot do:** Block a permission grant in flight, or revoke an existing one. It only reads, scores, and reports. The user still has to edit `settings.json` to remove dangerous entries.

```
# Pseudo-code for the permission audit hook addition

import json
import os
from pathlib import Path

DANGEROUS_PATTERNS = [
    ("Bash(rm:*)", "Can delete ANY file without prompting"),
    ("Bash(taskkill:*)", "Can kill ANY process without prompting"),
    ("Bash(cp:*)", "Can copy/overwrite ANY file without prompting"),
    ("Bash(git push --force:*)", "Can force-push without prompting"),
    ("Bash(DROP:*)", "Can drop database objects without prompting"),
]

BROAD_READ_PATTERN = r"Read\(//.*\*\*\)"  # Read with ** glob = entire tree

def audit_permissions(settings_path):
    """Scan settings for dangerous permission entries."""
    settings = json.loads(Path(settings_path).read_text())
    allows = settings.get("permissions", {}).get("allow", [])

    findings = []
    for entry in allows:
        for pattern, desc in DANGEROUS_PATTERNS:
            if pattern in entry or entry.endswith(":*)"):
                findings.append({"entry": entry, "risk": "HIGH", "desc": desc})

    stale_count = sum(1 for e in allows if len(e) > 80)  # very specific = likely stale
    return findings, stale_count, len(allows)

def format_warning(findings, stale_count, total):
    """Format the warning for injection into governance kernel."""
    if not findings:
        return ""

    lines = [
        f"## ⚠ Permission Audit ({total} entries, {len(findings)} HIGH risk)",
        ""
    ]
    for f in findings[:5]:  # show max 5
        lines.append(f"  - `{f['entry']}` → {f['desc']}")

    if stale_count > 10:
        lines.append(f"  - ~{stale_count} stale entries (consider pruning)")

    lines.append("")
    lines.append("  Run: `ai-ase permissions audit` or manually edit settings.local.json")
    lines.append("  Docs: claude-code-permission-accumulation.html")

    return "\n".join(lines)
```

**What the user sees in the governance kernel (session start only):**

```
## ⚠ Permission Audit (49 entries, 4 HIGH risk)

  - `Bash(rm:*)` → Can delete ANY file without prompting
  - `Bash(taskkill:*)` → Can kill ANY process without prompting
  - `Bash(cp:*)` → Can copy/overwrite ANY file without prompting
  - `Read(//c/Users/username/**)` → Can read ALL user files without prompting
  - ~20 stale entries (consider pruning)

  Run: `ai-ase permissions audit` or manually edit settings.local.json
```

**Session-once logic (don't repeat every turn):**

```
SESSION_MARKER = "/tmp/aiase-session-{session_id}.marker"

def should_audit():
    """Only audit on first message of session."""
    if os.path.exists(SESSION_MARKER):
        return False
    Path(SESSION_MARKER).touch()
    return True
```

> **Insight:** Why session start?
>
> - User is fresh, not deep in a debugging flow
> - They see it before any work — can clean up immediately
> - Only once per session — no nagging
> - Stop hook (session end) risks being missed if terminal is closed
> - Model also sees the warning — can reference it if user asks about permissions

> **Why it works:** Implementation effort: LOW. Add ~30 lines to the existing UserPromptSubmit hook. Pattern matching on settings.json is instant (<5ms). No new dependencies. Can ship in the next AI-ASE release.

## Key Takeaways

*4 things to remember*

1. **"Allow always" is permanent and invisible.** Every click expands the surface area. There's no expiry, no review prompt, no audit log. Permissions only grow unless you manually prune.
2. **Wildcard permissions are dangerous.** `Bash(rm:*)` means the model can delete anything without asking. The context where you allowed it (cleaning .pyc files) is gone — the permission remains forever.
3. **AI-ASE doesn't cover command safety.** It checks code content (secrets, patterns) but not command destructiveness. A `rm -rf` passes all 67 rules because it contains no hardcoded credential. This is a gap.
4. **Review your allowlist monthly.** 5 minutes of pruning settings.local.json prevents permission drift. Remove broad wildcards, delete stale one-offs, keep only what you actively need.

## ⚡ Why this matters for AI-ASE

AI-ASE hooks scan *code content*. The harness handles *command safety*. These are different responsibility layers, and the lesson clarifies why a permission-audit feature is **proposed but not shipped** — hooks cannot intercept permission decisions in flight.

- Justifies the architectural split: **content scanning at hook layer**, **command safety at harness layer**
- Justifies **Layer 9** (Multi-Agent Critic) — neither model nor hook alone catches legitimate-looking destructive commands; an adversarial second pass is the gap-filler
- The *proposed* session-start permission audit is aspirational and labeled as such; see the corresponding card above
