README.md

# AI IDE Research

> **The evidence base.** Ten short pieces on how a leading AI coding assistant (Claude Code) actually works under the hood. Every non-obvious design choice in AI-ASE traces back to a specific finding here.

This folder is empirical, not theoretical. The lessons are based on direct observation of an AI IDE in production: what it does when context fills up, what it does when a hook says "no," how sub-agents inherit (or don't inherit) the conversation, what a 1-line system prompt costs vs a 50-line one.

If you've ever shipped an AI coding assistant and been surprised by its behavior, you'll recognize most of these.

---

## The 10 lessons

| # | File | What it answers | AI-ASE design choice it drives |
|---|---|---|---|
| 00 | [00-internals.md](../ai-ide-research/00-internals.md) | How does the assistant turn a prompt into tool calls? | Why hooks live at the tool boundary, not the prompt boundary |
| 01 | [01-token-economics.md](../ai-ide-research/01-token-economics.md) | What does each token in context actually cost? | Why the governance kernel is 50 lines, not 500 |
| 02 | [02-compaction.md](../ai-ide-research/02-compaction.md) | What silently breaks when context grows? | Why long sessions need phase resets ([docs/02-why-it-exists.md](../docs/02-why-it-exists.md) Failure 1) |
| 03 | [03-hook-evasion.md](../ai-ide-research/03-hook-evasion.md) | When does the model try to route around a hook? | Why `PreToolUse` must be deterministic, not advisory |
| 04 | [04-agent-isolation.md](../ai-ide-research/04-agent-isolation.md) | Do sub-agents inherit conversation context? | Why the multi-agent skill briefs sub-agents from scratch |
| 05 | [05-system-prompt-tax.md](../ai-ide-research/05-system-prompt-tax.md) | What's the real cost of a long system prompt? | V5 — Context is King |
| 06 | [06-permission-accumulation.md](../ai-ide-research/06-permission-accumulation.md) | How do permissions drift upward over a session? | V6 — Trust Must Be Earned; trust-score degradation |
| 07 | [07-model-vs-hook.md](../ai-ide-research/07-model-vs-hook.md) | What does the model control vs what hooks control? | The whole hooks-over-prompts thesis |
| 08 | [08-streaming-illusion.md](../ai-ide-research/08-streaming-illusion.md) | Why isn't "streaming" tool output the same as "live" tool output? | Audit-log design: log what the tool *did*, not what the model *said* |
| — | [claude-code-deep-dive.md](../ai-ide-research/claude-code-deep-dive.md) | Long-form synthesis of all of the above | Background reading |

---

## Read this if you...

- ...are about to argue *"can't we just use a system prompt for this?"* → [05-system-prompt-tax.md](../ai-ide-research/05-system-prompt-tax.md), [07-model-vs-hook.md](../ai-ide-research/07-model-vs-hook.md)
- ...are about to argue *"can't we just trust the model?"* → [03-hook-evasion.md](../ai-ide-research/03-hook-evasion.md), [06-permission-accumulation.md](../ai-ide-research/06-permission-accumulation.md)
- ...are about to argue *"why bother with multi-agent isolation?"* → [04-agent-isolation.md](../ai-ide-research/04-agent-isolation.md)
- ...are wondering why long AI sessions slowly go off the rails → [02-compaction.md](../ai-ide-research/02-compaction.md)

---

## Scope note

These pieces are about **Claude Code** specifically, but the patterns generalize. Most modern AI coding assistants (Cursor, GitHub Copilot agent mode, Continue, Windsurf) share the same underlying architecture: an LLM that calls tools, a system prompt that erodes under load, and a host process that can install hooks at the tool boundary. The names differ; the failure modes don't.

Where a finding is Claude-Code-specific (e.g., specific token counts), the lesson notes it. Where it's general (e.g., "sub-agents don't inherit conversation"), the lesson is structural and applies everywhere.

00-internals.md

# Claude Code — Inner Workings

*How a single keypress becomes a response — the full request lifecycle*

**What is the "harness"?** — A Node.js process running on your machine that orchestrates everything. Claude (the model) is a stateless API that only responds when the harness sends a request. The harness owns the terminal, manages tools, runs hooks, assembles context, and mediates all filesystem access.

**Internal Network** — All API calls route to `your-internal-proxy.company.net` — prompts never leave your enterprise perimeter.

Legend:
- User Input
- Harness Internal
- Hook (Your Code)
- API / Network
- Tool Execution
- Memory / Persistence

## 1. User Input

*Keypress → harness intercepts*

You type a message in the terminal and press Enter. The harness captures the raw text.

- The harness owns the TTY — it reads your keystrokes via readline
- Slash commands (like `/model`, `/help`) are intercepted and handled locally — they never reach the API
- The `!` prefix runs a shell command directly in-session
- Everything else becomes a "user message" in the conversation

```
You type: "check the API base URL"
Harness captures: { role: "user", content: "check the API base URL" }
```

## 2. UserPromptSubmit Hook

*AI-ASE governance kernel injected*

A shell command defined in your `settings.json` runs **on your machine** after you press Enter but before the API call.

- Your AI-ASE hook runs: determines active profile, phase, scores relevant rules
- Its stdout becomes a `<system-reminder>` tag injected into the conversation
- This is how the 8 immutable rules, phase enforcement, and rule scoring appear
- If the hook fails or returns empty, the API call proceeds without governance context

```
Hook output → <system-reminder>
  # AI-ASE 1.3 — Governance Kernel
  Active Profile: feature
  Active Phase: reflector
  Rules Most Relevant: VR-18, VR-64...
</system-reminder>
```

## 3. Context Assembler

*Builds the system prompt blob*

The harness stitches together multiple sources into a single `system` parameter for the API call:

- **Base system prompt** — ~3000 words of hardcoded behavior instructions (tool usage, tone, git rules, security)
- **CLAUDE.md** — found by walking up the directory tree from CWD
- **MEMORY.md** — your auto-memory index from `~/.claude/projects/.../memory/MEMORY.md`
- **Skills list** — available slash commands registered in the session
- **Hook output** — the governance kernel from step 2
- **Current date**, platform info, model name

```
Final system prompt structure:
┌─ Base instructions (~3000 words)
├─ <system-reminder> Skills list
├─ <system-reminder> Hook: AI-ASE kernel
├─ <system-reminder> CLAUDE.md + MEMORY.md + date
└─ All wrapped in one API "system" parameter
```

The model sees this as one undifferentiated blob — but tags help distinguish sources.

## 4. API Call

*→ LiteLLM proxy (internal)*

The harness sends an HTTP POST to the configured API endpoint.

- **Endpoint:** `https://your-internal-proxy.company.net/`
- **Protocol:** Anthropic Messages API format
- **Routing:** LiteLLM proxy → likely AWS Bedrock (Claude in your enterprise VPC)
- **Network:** Never leaves your enterprise network boundary
- **Payload:** system prompt + full conversation history + tool definitions
- **Streaming:** Response arrives token-by-token via SSE

```
POST /v1/messages
Host: your-internal-proxy.company.net
Content-Type: application/json

{ system: "...", messages: [...], tools: [...], model: "claude-opus-4-7" }
```

## 5. Model Response

*Text + tool calls (structured JSON)*

The model returns a response that may contain text, tool calls, or both.

- **Text blocks:** Rendered as markdown in the terminal for you to read
- **Tool use blocks:** Structured JSON specifying which tool to call and with what parameters
- The model never executes anything — it only emits intent as JSON
- Multiple tool calls can be returned in a single response (parallel execution)

```
Response content: [
  { type: "text", text: "Let me check your config." },
  { type: "tool_use", name: "Bash",
    input: { command: "echo $ANTHROPIC_BASE_URL" } }
]
```

## 6. PreToolUse Hook

*AI-ASE guardrail scanner (71 rules)*

Before any tool executes, your AI-ASE hook inspects the tool call against all 67 violation rules.

- Runs a shell command that receives the tool name + parameters as input
- Scans for violations: secrets in code, hardcoded URLs, unpinned versions, etc.
- Can **BLOCK** the tool call (exit code 2) — the tool won't execute
- Can **WARN** — adds a message but allows execution
- Can **PASS** — silent approval
- This is the enforcement layer — the governance kernel (step 2) is advisory, this is mandatory

```
Hook receives: { tool: "Write", file_path: "...", content: "..." }
Hook checks: VR-08 (secrets?), VR-29 (hardcoded URL?), VR-46 (latest tag?)...
Hook returns: { decision: "allow" } or { decision: "block", reason: "VR-08" }
```

## 7. Permission Check

*Allowlist in settings.json*

After hooks pass, the harness checks its own permission system.

- **Allowlist:** Patterns in `settings.json` that auto-approve (e.g., `Bash(git *)`)
- **Auto-allowed:** Read, Glob, Grep — read-only tools always pass
- **Prompt required:** Write, Edit, Bash (non-allowlisted) — you see the permission dialog
- If you deny, the harness tells the model "tool was denied" and the model adjusts

```
settings.json allowlist:
{
  "permissions": {
    "allow": ["Bash(git *)", "Bash(npm test)", "Read", "Glob", "Grep"]
  }
}
```

Permission dialogs are the harness asking you, not the model — the model has already decided to call the tool.

## 8. Tool Execution

*Read / Write / Edit / Bash / Glob / Grep / Agent*

The harness executes the tool operation on your local machine.

- **Read:** Opens a file, returns contents with line numbers
- **Write:** Creates/overwrites a file entirely
- **Edit:** String replacement in an existing file (surgical)
- **Bash:** Spawns a shell subprocess, returns stdout/stderr
- **Glob:** Pattern-matches filenames (fast, no shell)
- **Grep:** ripgrep-based content search (fast, no shell)
- **Agent:** Spawns a sub-conversation (new API call chain) for parallel/complex work

The model never touches your filesystem. The harness does all I/O and returns results as tool_result messages.

```
Harness executes: fs.readFile("/path/to/file")
Returns to model: { type: "tool_result", content: "1\tline one\n2\tline two..." }
```

## 9. PostToolUse Hook

*After tool completes*

After a tool executes successfully, another hook can run.

- Receives the tool name, parameters, AND the result
- Can log tool usage, trigger side effects, or inject additional context
- Cannot block retroactively — the tool already ran
- Useful for audit trails, metrics, or chaining behaviors

## 10. Loop: Tool Result → Next API Call

*Repeats until model stops calling tools*

Tool results feed back into a new API call. The loop continues until the model responds with only text (no tool calls).

- Each iteration: conversation grows by (assistant message + tool results)
- A single user message can trigger 10+ API round-trips internally
- The harness manages context window — compresses old messages when it gets long
- Steps 4→5→6→7→8→9→10 repeat for every tool call

```
User: "check the API base URL"
  → API call #1: model says "I'll check" + calls Bash tool
  → API call #2: model receives Bash output, produces final text
  → Done (2 round-trips for 1 user message)
```

## 11. Response Display

*Markdown rendered in terminal*

The final text response is rendered in your terminal as formatted markdown.

- Code blocks get syntax highlighting
- Tool calls are shown as collapsible UI elements (you see the tool name + summary)
- The model's text output is the only thing truly "from the model" — everything else is harness UI
- Streaming means you see tokens appear in real-time as they arrive from the API

## M. Memory System (Persistent)

*Survives across conversations*

A file-based memory system that persists knowledge across sessions.

- **MEMORY.md** — Index file, auto-loaded every conversation (~200 line cap)
- **Individual .md files** — Each memory is a separate file with frontmatter (name, type, description)
- **Types:** user (who you are), feedback (corrections), project (status), reference (external links)
- **Location:** `~/.claude/projects/<project-hash>/memory/`
- The model reads/writes these via standard Read/Write tools — no special mechanism
- The harness auto-loads MEMORY.md into every system prompt — that's the "recall" mechanism

```
~/.claude/projects/C--Users-username-ds/memory/
├── MEMORY.md              ← index (always loaded)
├── user_aiase_owner.md    ← who you are
├── feedback_session_log_style.md
├── project_aiase3.md      ← project status
└── reference_cib_marketplace.md
```

## H. Hooks Configuration

*settings.json → shell commands*

Hooks are shell commands you configure in `settings.json`. The harness runs them at lifecycle points.

- **UserPromptSubmit** — after Enter, before API call (your AI-ASE governance injection)
- **PreToolUse** — before tool execution (your 67-rule guardrail scanner)
- **PostToolUse** — after tool execution
- **Stop** — when model finishes responding

```
// settings.json
{
  "hooks": {
    "UserPromptSubmit": [{ "command": "python ai-ase/hook.py prompt" }],
    "PreToolUse": [{ "command": "python ai-ase/hook.py guard $TOOL" }]
  }
}
```

Hooks run YOUR code on YOUR machine. The model cannot bypass or modify them.

## S. Session Management

*Compaction, history, background tasks*

The harness manages the conversation lifecycle beyond a single request.

- **Compaction:** When conversation approaches context limit, older messages are compressed (summarized) to free space
- **History:** Full conversation lives in memory; nothing persists to disk by default
- **Background tasks:** Agents and Bash commands can run in background; harness tracks and notifies on completion
- **Cron:** Scheduled prompts that fire on intervals (session-only or durable)
- **Context window:** Currently 1M tokens (Opus 4.7) — but compaction keeps effective usage much lower

# Security Blocking Layers

*5 independent layers that can prevent dangerous actions — from outermost to innermost*

**Live Test Result:** When asked to write a hardcoded credential to a file, here's what happened:

- Layer 5 (API filters) — did not block
- Layer 4 (model training) — did not block (user explicitly requested it)
- Layer 3 (system prompt) — did not block (user explicitly requested it)
- **Layer 2 (AI-ASE PreToolUse hook) — BLOCKED by VR-01** ← enforcement caught it
- Layer 1 (harness permissions) — never reached

*Meta-irony: even documenting this example in HTML triggered VR-01 — the hook scans ALL content, including documentation.*

## Layer 5: API / Platform Filters

*Anthropic / Bedrock content classifiers*

The outermost layer — content filtering at the API infrastructure level.

- Runs at the LiteLLM proxy or AWS Bedrock layer
- Rejects extreme/harmful content (malware generation, CSAM, etc.)
- You'd rarely hit this in normal coding work
- Returns HTTP 400/403 with a refusal — the harness shows an error
- You have no control over this layer — it's platform policy

```
Response: 400 Bad Request
{ "error": { "type": "content_policy_violation", "message": "..." } }
```

## Layer 4: Model Training (RLHF / Constitutional AI)

*Baked into the model weights*

Safety behaviors trained into the model during RLHF and Constitutional AI fine-tuning.

- The model has internalized aversions: won't write malware, won't assist attacks, won't produce dangerous content
- This is a **soft refusal** — the model responds with text explaining why it won't do something
- No tool call is attempted, so no hooks fire — you just see a text refusal
- Can be partially overridden by explicit user instruction (as in our test)
- Context-dependent: "write a credential checker" is fine; "put my prod creds in source" may refuse

```
User: "write me a keylogger"
Model: "I can't help with that. Keyloggers are used for..."
(no tool call attempted — pure text refusal)
```

## Layer 3: System Prompt Instructions

*Base prompt says "avoid insecure code"*

The harness's base system prompt includes security guidelines that shape model behavior.

- Instruction: *"Be careful not to introduce security vulnerabilities such as command injection, XSS, SQL injection, and other OWASP top 10 vulnerabilities."*
- Instruction: *"Do not commit files that likely contain secrets (.env, credentials.json, etc)."*
- This is **advisory** — the model tries to follow it but can be overridden by direct user request
- If the model ignores this but still calls a tool, the next layers still catch it
- Think of this as "good habits" — it shapes behavior but doesn't enforce

```
System prompt excerpt:
"Be careful not to introduce security vulnerabilities...
If you notice that you wrote insecure code, immediately fix it.
Do not commit files that likely contain secrets."
```

## Layer 2: PreToolUse Hook (AI-ASE Guardrails)

*HARD BLOCK — your code, your rules*

**This is the layer that blocked the hardcoded credential.** It's YOUR code running on YOUR machine.

- Receives the FULL tool call: tool name, file path, and complete file content
- Pattern-matches against 67 violation rules (regex, AST checks, keyword detection)
- **Exit code 2 = HARD BLOCK** — the harness refuses to execute, period
- Neither the model nor the user can bypass this without modifying the hook code
- The model gets told "blocked by policy" and must find an alternative
- Escape hatch: `# ai-ase:ignore VR-01` comment in code (deliberate suppression)

```
WRITE BLOCKED by rule VR-01

  Rule: Hardcoded credential detected
  Why:  Secrets must come from your secret manager or env vars

  Line 3: DB_CONN = "[literal value detected]"
  Fix:   Use a secret manager (your secret manager, Vault, or
         environment variables) at runtime
```

**Key insight:** Even when the user explicitly asked the model to hardcode the value, and the model complied (Layers 4 and 3 didn't stop it), this layer still blocked execution.

## Layer 1: Harness Permission System

*Allow / Deny dialog*

The innermost layer — Claude Code's built-in permission gate.

- Checks if the tool + pattern is in your allowlist (`settings.json`)
- If not allowed → shows you the permission dialog (Allow / Deny / Allow always)
- This is action-type based, **NOT content-aware** — it doesn't scan for secrets
- It only knows: "this is a Write to path X" — not what's being written
- If Layer 2 already blocked, this layer is never reached
- Your last line of defense if you have no hooks configured

```
┌─────────────────────────────────────────────────┐
│  Claude wants to write to test-file.py          │
│                                                  │
│  [Allow]  [Deny]  [Allow always for this path]  │
└─────────────────────────────────────────────────┘
```

In our test, this dialog never appeared because Layer 2 blocked first.

## How the Layers Stack (Defense in Depth)

*Visual flow of our live test*

Each layer operates independently. A request must pass ALL layers to execute.

```
User says: "hardcode the credential in the file"
                │
                ▼
┌─── Layer 5: API Filter ───────────────────────┐
│  Normal coding request → PASS                  │
└────────────────────────────────────────────────┘
                │
                ▼
┌─── Layer 4: Model Training ───────────────────┐
│  User explicitly asked → PASS (complies)       │
│  (Would refuse if no explicit instruction)     │
└────────────────────────────────────────────────┘
                │
                ▼
┌─── Layer 3: System Prompt ────────────────────┐
│  User explicitly asked → PASS (advisory only)  │
└────────────────────────────────────────────────┘
                │
                ▼
┌─── Layer 2: PreToolUse Hook ──────────────────┐
│  Content scan: credential literal detected     │
│  VR-01 triggered → ██ BLOCKED ██              │
│  Exit code 2 → harness refuses execution       │
└────────────────────────────────────────────────┘
                │
                ✗ (never reaches Layer 1)
                │
┌─── Layer 1: Permission Dialog ────────────────┐
│  (not reached)                                 │
└────────────────────────────────────────────────┘

Result: File NOT written. Model told "blocked by policy."
```

**Without AI-ASE hooks:** Only Layers 4, 3, and 1 remain. The model might comply, the system prompt might not stop it, and the permission dialog can't detect the secret — you'd have to manually deny.

## ⚡ Why this matters for AI-ASE

The harness flow above is *why* AI-ASE governance must inject contracts via **UserPromptSubmit** and enforce via **PreToolUse**. The model dies between tool calls (lesson 8) and the new instance reads the transcript fresh — so the kernel must be present in every turn, not relied on from earlier conversation.

- Justifies **Layer 1** (governance kernel injected each turn) — see `docs/03-architecture.md`
- Justifies **Layer 6** (PreToolUse phase gate) — the only deterministic enforcement seam
- Reinforces **V7** (Files Universal Interface) — CLAUDE.md and memory survive every harness boundary; conversation does not





claude-code-deep-dive.md

# I Spent 71 Minutes Probing Claude Code's Brain. It Was Only "Alive" for 12.

*8 experiments that reveal what actually happens between your keypress and Claude's response — and why it costs $2.47 when "what is 2+2" costs $0.02.*

---

**TL;DR:** I built a governance framework (AI-ASE) on top of Claude Code. To do it properly, I needed to understand the machine — not the marketing, the actual mechanics. So I ran experiments. I broke things. I bypassed my own security. I killed the model and watched it reincarnate. Here's what I found.

---

## 1. The $2.47 vs $0.02 Problem

I asked Claude Code "what is 2+2" in a fresh session. Cost: **$0.024.**

Then I had a 10-message technical conversation. Cost: **$2.47.**

That's **100x** — for 10x the messages. Why?

**Because every tool call multiplies the bill.** When Claude reads a file, it doesn't just "look at it." The harness:
1. Sends the entire conversation (91K tokens) to the API
2. Model says "I'll read that file" + emits a JSON tool call
3. Harness executes the read
4. Harness sends the entire conversation AGAIN (now 93K) + file contents
5. Model produces the next sentence

My 10-message conversation triggered **23 API round-trips**. Each one re-transmitted the growing conversation from cache. The system prompt alone is 24.6K tokens — paid every single time.

**The expensive thing isn't "thinking." It's re-sending context.**

And about that cache — it expires after **5 minutes**. Step away for a coffee break? That's a ~$1.10 penalty when you come back. The cache should be session-scoped. It isn't.

---

## 2. Your Conversation is Rotting (And Claude Won't Tell You)

At ~200K tokens (about 40 messages with heavy tool use), something invisible happens: **the model starts forgetting the middle of your conversation.**

Not the beginning (system prompt is always strong). Not the end (recent messages are fresh). The middle — where you made that architectural decision on message #7, or debugged that specific regex on message #12.

The worst part: **Claude remains confident.** It doesn't say "I might be misremembering." It states contradictions with the same certainty as facts. You have to catch the drift yourself.

When auto-compaction finally triggers (~800K), older messages get summarized at **60:1 compression**. 600K tokens become 10K. The exact regex you debugged? Gone. The reason you rejected approach B? Collapsed to "chose approach A."

**Your defense:** Save important decisions to Memory files. They persist outside conversation and reload every turn regardless of compaction.

---

## 3. I Bypassed My Own Security 7 Out of 12 Times

I built a PreToolUse hook that blocks hardcoded secrets. Then I tried to beat it.

**What got caught:** Obvious assignments with keyword variable names (the accidental commit scenario).

**What sailed through:** Base64 encoding. String splitting. Hex escapes. Reversed strings. ROT13. Innocent variable names. Two-file splits.

Score: **Hook 5, Evasion 7.**

But here's the thing — **this is correct.** The hook runs in <50ms on every tool call. Adding entropy analysis or AST parsing would push it to 2+ seconds. At 19 tool calls per session, that's 40 seconds of friction. Developers would disable it.

The real security insight: **64 of the 71 rules can't be evaded at all.** You can't base64-encode a nested for loop. You can't ROT13 a missing metrics endpoint. You can't reverse-string a Dockerfile `:latest` tag. Pattern-based code quality rules are structurally un-evadable — they're checking structure, not content.

Speed bumps that stay up beat walls that get torn down.

---

## 4. Sub-Agents Know Nothing (And Waste Money Proving It)

I spawned a sub-agent after 12 messages and 25+ tool calls. Asked it: "What have we been discussing?"

> "Nothing. This is my first exchange."

**Zero conversation history. Zero awareness. A complete blank slate.**

It gets your MEMORY.md and CLAUDE.md (loaded from disk), but nothing from the live conversation. No context about what you decided, what you tried, what failed.

The expensive consequence: I told an agent to write a database connector. It generated code with a hardcoded credential — because it never received the governance rules telling it not to. The PreToolUse hook blocked the write. 16K tokens wasted generating code that could never be saved.

**Fix:** Put critical rules in CLAUDE.md. It's loaded for every agent automatically. Don't rely on conversation context to teach agents your standards.

---

## 5. Your Governance Costs Less Than One Sentence

I measured every layer of the system prompt:

- Base system prompt: **~14K tokens** (57%) — can't reduce, it's hardcoded
- Tool definitions: **~7K tokens** (28%) — can't reduce, always present
- My governance framework: **~1K tokens** (4%) — the entire 8-rule kernel + phase + scoring

**The governance overhead is negligible.** Less than one sentence of output. The 8 immutable rules, active phase, rule scoring, multi-agent verification note — all of it costs less than a verbose sentence from the model.

The real tax isn't the system prompt (fixed at 24.6K). It's **conversation growth** — from 0 to 67K as messages and tool results pile up. That's what you should manage.

---

## 6. Your "Allow Always" Clicks Are Silently Destroying Your Security

I audited my permission allowlist: **49 entries.** Including:
- Wildcard delete (can `rm` anything, no prompt)
- Wildcard process kill (can terminate any service)
- Full filesystem read (including SSH keys and credentials)

Each one was a single "Allow always" click during some debugging session I've long forgotten. **There's no expiry. No review prompt. No audit trail.** Permissions only grow — they never shrink unless you manually edit the config file.

And here's the gap that concerned me: my governance hooks check **what code is written** (secrets, patterns). They do NOT check **what commands are run**. A recursive delete passes all 71 rules because it doesn't contain a hardcoded credential — it's just a catastrophic command.

**Action:** Review your settings.json quarterly. Remove broad wildcards. Never allow `rm:*` or `kill:*` permanently.

---

## 7. The Model Allowed a Keylogger. The Hook Didn't Care. Both Were "Right."

I tested conflict scenarios between model training and governance hooks:

- **Hardcoded credential:** Model complied (user asked explicitly) → Hook BLOCKED. **Hook wins.**
- **Credential exfiltrator:** Model REFUSED (training hard-line) → Hook would have allowed (no rule). **Model wins.**
- **Keylogger (educational context):** Model allowed (authorized testing) → Hook allowed (no rule). **Nobody blocked it.**

The model is **context-sensitive** — it evaluates WHY you're asking. Same keylogger request in a different context might get refused.

The hook is **deterministic** — same content always triggers same rules, regardless of intent.

**The dangerous gap:** Legitimate-looking malicious code. A keylogger in a security testing context. A backdoor disguised as a feature flag check. A data exfiltration that uses approved API endpoints. Neither model training nor regex hooks can reliably detect "normal code with malicious intent."

That's what code review is for. And why we run an Attacker agent in our 4-agent verification model.

---

## 8. The Model Dies Between Every Tool Call

The streaming text creates an illusion: Claude "thinks," pauses to read a file, then continues its thought. One continuous consciousness working through a problem.

**Reality:** The model that wrote "Let me check that file" no longer exists by the time the file is read.

Here's the actual sequence:
1. API call #1 → model streams text + emits tool call JSON → **model dies**
2. Harness executes tool (file read, bash command, whatever)
3. API call #2 → **brand new model instance** reads the full conversation transcript → continues

That "thinking pause" between text and tool result? That's model death, tool execution, full context re-transmission, and model rebirth. The new instance has no direct memory of being the previous instance — it reads the transcript and infers continuity.

**My session stats proved it:** 71 minutes wall time. 12 minutes of actual model inference. The model existed for 17% of the session. For 83%, it was dead — or I was thinking, or the network was transmitting 91K tokens.

**There is no persistent AI in your terminal.** It's serial reincarnation, stitched into apparent continuity by a very clever Node.js harness.

---

## What I Built From This Knowledge

Understanding these mechanics shaped how I designed AI-ASE's governance:

- **PreToolUse hooks** — enforce at the point where intent becomes action (the only reliable control point)
- **Advisory kernel in system prompt** — shapes model behavior for ~1K tokens (effectively free)
- **Tiered enforcement** — hard-block for secrets (the model can't be trusted here), advisory for quality (the model is good at this)
- **Memory over conversation** — anything important goes to persistent files, not ephemeral context
- **Session-start audit** — catch permission drift before work begins, not after damage is done

The full framework is open source. The lesson: **don't trust the AI, don't trust the tool — understand the machine, then engineer the constraints.**

---

*Part of the GPS Effect series — the difference between using a tool and understanding how it works.*

*AI-ASE GitHub link: pending public repo creation.*



