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
