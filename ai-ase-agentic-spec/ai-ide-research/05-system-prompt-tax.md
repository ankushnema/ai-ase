# The System Prompt Tax

*~25K tokens consumed before you type a single character*

## Your Context Budget — Where It Goes

Total context window: **1,000,000 tokens** (Opus 4.7). Here's what's consumed before you say anything:

- Base prompt ~14K
- Tools ~7K
- CLAUDE.md ~1.6K
- Memory ~400
- AI-ASE ~1K
- Other ~700

**Total system prompt tax: ~24.6K tokens (2.5% of your context window)**
This is paid on every API call — but cached after the first time (see [Token Economics](01-token-economics.html)).

## Detailed Breakdown by Layer

*What each component costs*

| Layer | Tokens (est.) | % of Tax | Source | Can You Reduce? |
|---|---|---|---|---|
| **Base system prompt** | ~14,000 | 57% | Hardcoded by Anthropic (Claude Code binary) | No |
| **Tool definitions** | ~7,000 | 28% | JSON schemas for all tools (Read, Write, Bash, Agent, etc.) | No |
| **CLAUDE.md** | ~1,600 | 6.5% | Your project file: `ds/aiase1.3/CLAUDE.md` (6,263 bytes) | Yes — trim it |
| **AI-ASE governance kernel** | ~1,000 | 4% | UserPromptSubmit hook output (8 rules, phase, scoring) | Yes — reduce hook output |
| **Skills list** | ~500 | 2% | Available slash commands (9 skills listed) | Partially — unregister unused skills |
| **MEMORY.md index** | ~400 | 1.6% | Auto-memory index (1,622 bytes, 10 entries) | Yes — prune stale memories |
| **Environment info** | ~200 | 0.8% | Platform, shell, model name, date, CWD | No |

> **Insight:** The 85% you can't control: Base system prompt (57%) + tool definitions (28%) = 85% of the tax. These are fixed by Anthropic. The remaining 15% is yours to optimize (CLAUDE.md, memory, hooks).

## What's in the Base System Prompt (~14K tokens)

*The instructions that define Claude Code's behavior*

The base system prompt is hardcoded into Claude Code. It contains:

| Section | Est. Tokens | Purpose |
|---|---|---|
| Identity + role | ~200 | "You are Claude Code, Anthropic's official CLI..." |
| Tool usage instructions | ~3,000 | How to use each tool, when to prefer which, error handling |
| Git commit rules | ~1,500 | How to stage, commit, format messages, avoid destructive ops |
| PR creation rules | ~1,000 | How to create pull requests with gh CLI |
| Tone and style | ~800 | Terse responses, no emojis, markdown formatting, updates |
| Safety / security | ~1,000 | OWASP, no hardcoded secrets, careful with destructive actions |
| Doing tasks guidelines | ~1,500 | How to approach software engineering, scope discipline |
| Permission / risky actions | ~1,500 | When to confirm with user, reversibility considerations |
| Memory system instructions | ~2,000 | How to read/write memories, what to save, what not to save |
| Session-specific guidance | ~500 | Agents, skills, cron, environment details |
| Code style rules | ~1,000 | No comments, no abstractions, no drive-by changes |

You can't see or modify this — it's compiled into the Claude Code binary. But you can observe its effects in how I behave.

## Tool Definitions (~7K tokens)

*JSON schemas for every tool*

Every tool I can call has a full JSON schema sent with every API call:

| Tool | Params | Description Length |
|---|---|---|
| Bash | command, timeout, description, run_in_background | Long (safety rules included) |
| Read | file_path, offset, limit, pages | Medium |
| Write | file_path, content | Medium (usage rules) |
| Edit | file_path, old_string, new_string, replace_all | Medium (matching rules) |
| Glob | pattern, path | Short |
| Grep | pattern, path, output_mode, context, type, glob, +more | Long (many options) |
| Agent | prompt, description, subagent_type, isolation, +more | Very long (full agent docs) |
| TaskCreate/Update/List/Get | subject, description, status, blocks, etc. | Long (workflow docs) |
| AskUserQuestion | questions (complex nested schema) | Long |
| EnterPlanMode/ExitPlanMode | minimal | Long (workflow docs) |
| Skill | skill, args | Short |
| CronCreate/Delete/List | cron, prompt, recurring, durable | Long (scheduling rules) |
| NotebookEdit | notebook_path, new_source, cell_type, etc. | Medium |
| Worktree tools | name, path, action | Long |

Each tool includes: name, description (with usage guidelines), and a full JSON schema with parameter types, descriptions, and constraints. This is the second-largest chunk after the base prompt.

> **Pain point:** Every tool costs tokens even if you never use it. NotebookEdit, CronCreate, Worktree tools — they're always present in the schema regardless of whether your workflow uses them. You pay ~7K tokens for tools you may never call.

## The Growing Tax: System Prompt + Conversation

*Cache write grew from 24.6K to 91.4K during our session*

The "tax" isn't just the system prompt — it's everything that gets re-sent on each API call. This grows with conversation:

```
API call #1 (first message):
  System prompt:  24.6K tokens
  Your message:   ~50 tokens
  Total sent:     ~24.7K tokens

API call #5 (after some tool calls):
  System prompt:  24.6K tokens (cached)
  Conversation:   ~15K tokens (growing)
  Total sent:     ~40K tokens

API call #23 (current session):
  System prompt:  24.6K tokens (cached)
  Conversation:   ~67K tokens (messages + tool results)
  Total sent:     ~91.4K tokens
```

**The compound effect:**

- Call #1: 24.6K sent (system prompt dominates)
- Call #10: ~50K sent (conversation catching up)
- Call #23: ~91K sent (conversation now 2.7x the system prompt)

> **Insight:** At ~91K per call × 23 calls = 2.1M total tokens transmitted. That's why our session shows 2.1M cache read — it's the system prompt + conversation being re-sent (from cache) on every round-trip. The conversation growth IS the real cost driver over time, not the fixed system prompt.

## AI-ASE Hook Tax: ~1K Tokens Per Turn

*The governance kernel injection*

Your UserPromptSubmit hook injects the governance kernel on every user message. Here's what it costs:

```
# AI-ASE 1.3 — Governance Kernel                           (~50 tokens)
Core constraint + values reference                          (~30 tokens)
The 8 Immutable Rules (full text of all 8)                  (~400 tokens)
Active Profile / Phase / Context Budget                     (~20 tokens)
Multi-Agent Verification block                              (~50 tokens)
Rules Most Relevant to This Task (scored list)              (~100 tokens)
PreToolUse enforcement note                                 (~30 tokens)
Phase enforcement block (reflector-specific)                (~50 tokens)

Total per user message: ~730-1000 tokens
```

| Metric | Value |
|---|---|
| Hook output size per turn | ~1,000 tokens |
| Turns in this session | ~12 |
| Total AI-ASE tokens injected | ~12,000 tokens |
| % of total session tokens | ~0.6% (negligible) |

> **Insight:** The governance tax is tiny. ~1K tokens per turn is less than 1% of the per-call context. You're paying more for a single verbose tool result than for the entire governance kernel. The 8 immutable rules + phase + scoring costs less than 2 sentences of output.

## How to Reduce Your Controllable Tax

*The 15% you can optimize*

| Action | Savings | Trade-off |
|---|---|---|
| Trim CLAUDE.md to essentials | ~500-1000 tokens | Less guidance per turn (acceptable if well-trained memory) |
| Prune stale memory entries | ~100-200 tokens | Lose recall of old context (acceptable if truly stale) |
| Reduce AI-ASE hook verbosity | ~300-500 tokens/turn | Less advisory context (keep enforcement, trim commentary) |
| Unregister unused skills | ~200-400 tokens | Can't use those skills until re-registered |
| Use /compact more frequently | ~50-80% conversation reduction | Lossy compression of older context (see Page 2) |
| Shorter responses (ask for terse) | Reduces conversation growth rate | Less explanation, more implementation |

> **Pain point:** The uncomfortable truth: 85% of the tax (base prompt + tools) is untouchable. The 15% you control saves ~1-2K tokens — meaningful for long sessions but not transformative. The real optimization is managing CONVERSATION GROWTH (compact early, batch questions, be terse).

## Minimal vs Fully Loaded: What's the Difference?

*If you stripped everything optional*

| Configuration | System Prompt Size | Difference |
|---|---|---|
| **Bare minimum** (no CLAUDE.md, no memory, no hooks, no skills) | ~21K tokens | Baseline |
| + CLAUDE.md | ~22.6K tokens | +1.6K |
| + MEMORY.md | ~23K tokens | +400 |
| + Skills list | ~23.5K tokens | +500 |
| + AI-ASE hook | ~24.5K tokens | +1K |
| **Your current setup (fully loaded)** | **~24.6K tokens** | +3.6K over bare minimum |

> **Insight:** Your extras cost 3.6K tokens (17% overhead over bare minimum). In exchange you get: governance enforcement, memory recall, project context, and quick skills. That's an excellent trade — 3.6K tokens buys significant capability at negligible cost relative to the 1M window.

## Key Takeaways

*5 things to remember*

1. **The system prompt tax is ~24.6K tokens (~2.5% of 1M context).** It's paid on every API call but cached after the first. The real cost is amortized via prompt caching.
2. **85% is fixed (base prompt + tools), 15% is yours.** You can't reduce the base, but your additions (CLAUDE.md, memory, hooks) add only ~3.6K tokens — an excellent value trade.
3. **The AI-ASE governance kernel costs ~1K tokens per turn.** That's less than a single line of output. Governance is effectively free in token terms.
4. **Conversation growth is the real tax.** The system prompt stays fixed at 24.6K, but conversation grows from 0 to 67K+ over 23 API calls. Managing conversation size matters more than trimming the system prompt.
5. **Every sub-agent pays the full 24.6K tax independently.** Spawning 3 agents = 3 x 24.6K minimum. This is why agent overhead is high and shouldn't be used for trivial tasks.

## ⚡ Why this matters for AI-ASE

The real cost is conversation growth, not the system prompt. AI-ASE's governance kernel adds ~1K tokens per turn — a rounding error against the 25K base prompt and the multi-K conversation drift.

- Justifies the **50-line kernel** decision (V5: Context is King) — the governance overhead is genuinely cheap
- Justifies **on-demand skill loading** — skills only enter context when their triggers fire
- Underwrites the operational guidance in `docs/06-build-runbook.md` on when to `/clear` vs `/compact`