02-compaction.md# Compaction: What Survives

*Context degradation, the "lost in the middle" problem, and when to compact*

## Two Separate Problems (Most People Confuse These)

**1. Attention Degradation**
Happens *well before* the context limit.
The model technically "sees" all tokens but **can't attend equally** to everything.
Information in the middle gets less attention.
**When:** ~100K-200K+ tokens in conversation
**Fix:** `/compact` or `/clear`

**2. Hard Context Limit**
The absolute ceiling: 1M tokens (Opus 4.7).
Harness auto-compacts before hitting this.
Forces lossy compression of older messages.
**When:** ~800K-900K tokens
**Fix:** Automatic (harness handles it)

**Key insight:** You should compact at Problem 1, not wait for Problem 2. By the time auto-compaction triggers, you've already been getting degraded responses for a long time.

## The "Lost in the Middle" Problem

*Attention isn't uniform across context*

Transformer models don't attend equally to all tokens in the context. There's a well-documented U-shaped attention curve:

**Attention strength by position in context:**

- System prompt: Very High
- Early messages: High
- Middle messages: LOW
- Recent messages: Very High
- Current query: Maximum

**Practical impact:**

- A decision you made in message #3 of a 50-message conversation? May be effectively "forgotten" — it's in the low-attention middle zone
- Your system prompt (CLAUDE.md, memory, hooks)? Always strong — it's at the very beginning
- The last 3-5 messages? Always strong — recency bias
- Everything in between? Degrading proportionally to context length

> **When does this become noticeable?** Research suggests quality degradation begins around 100K-200K tokens for most tasks. For tasks requiring precise recall of earlier details (like "remember the architecture decision from message #5"), degradation starts even earlier — around 50K-80K tokens.

## When Should YOU Compact?

*Don't wait for auto — compact proactively*

| Context Size | State | Action |
|---|---|---|
| 0 - 50K tokens | Green zone — full recall, fast responses | Do nothing |
| 50K - 100K tokens | Still good — minor edges may soften | Monitor |
| 100K - 200K tokens | Yellow zone — middle-context recall degrading | Consider `/compact` if switching tasks |
| 200K - 500K tokens | Orange zone — noticeable quality loss on earlier details | **Compact now** or `/clear` if you can start fresh |
| 500K - 800K tokens | Red zone — significant degradation, responses slower | Compact immediately |
| 800K+ tokens | Auto-compaction triggers (harness intervenes) | Automatic |

> **Insight:** Rule of thumb: If you've been in the same session for 30+ messages with heavy tool use, you're likely in the 100K-200K range. If the model starts "forgetting" earlier context or giving inconsistent answers, that's your signal to compact.

**Commands available:**

- `/compact` — Summarize older messages, keep recent ones intact. Preserves session continuity.
- `/clear` — Nuclear option. Wipes all conversation history. System prompt + memory reload fresh.

## How Auto-Compaction Works Mechanically

*Haiku summarizes, Opus continues*

When the harness detects context is approaching the limit:

```
BEFORE compaction (context at ~800K tokens):
┌────────────────────────────────────────────────────────────┐
│ System prompt (25K) │ Msg 1-40 (600K) │ Msg 41-50 (175K) │
└────────────────────────────────────────────────────────────┘
                        ↑ this gets compressed

Step 1: Harness selects older messages (Msg 1-40)
Step 2: Sends them to Haiku: "Summarize this conversation"
Step 3: Haiku returns a ~5-10K token summary
Step 4: Harness replaces 600K of messages with 10K summary

AFTER compaction (context now ~210K tokens):
┌───────────────────────────────────────────────────────────────┐
│ System prompt (25K) │ [Summary] (10K) │ Msg 41-50 (175K)    │
└───────────────────────────────────────────────────────────────┘
                        ↑ lossy compression (60:1 ratio)
```

**What the summary contains:**

- High-level decisions made ("user chose approach X over Y")
- Key file paths that were discussed
- Major conclusions and outcomes
- What tasks were completed

**What the summary loses:**

- Exact code snippets (paraphrased instead)
- Specific numbers, IDs, or values mentioned in passing
- Nuanced reasoning and trade-off discussions
- The "why" behind decisions (often compressed to just the decision)
- Intermediate debugging steps
- Tool call details (exact commands run, full outputs)

> **Pain point:** The 60:1 compression ratio is extremely lossy. 600K tokens compressed to 10K means 98.3% of the original information is discarded. Haiku (the summarizer) makes judgment calls about what's "important" — and its judgment may not align with what you'll need later.

## Survival Matrix: What Lives, What Dies

*Concrete examples*

| Information Type | Survives? | Why |
|---|---|---|
| System prompt (CLAUDE.md, memory, hooks) | ALWAYS | Never compacted — it's outside conversation history |
| "We decided to use PostgreSQL not MongoDB" | Usually | High-level decisions are summary-worthy |
| File paths you edited | Sometimes | Survives if repeated/important; lost if mentioned once |
| The exact regex you debugged | Rarely | Too specific — summarized as "fixed regex issue" |
| A specific error message | Rarely | Exact text lost; gist preserved ("encountered auth error") |
| Why you rejected approach B | Rarely | Reasoning collapses to just the conclusion |
| A number you mentioned once ("port 8443") | Almost never | Isolated facts are first to be cut |
| Code you asked to be written | Partially | Summary says "wrote auth middleware" — not the actual code |
| Your preferences stated in-conversation | Sometimes | Better stored in Memory (persists regardless of compaction) |

> **Insight:** The Memory system is your defense against compaction loss. Anything important enough to survive across sessions (preferences, decisions, facts) should be saved to Memory — it lives in MEMORY.md and is reloaded into every system prompt regardless of compaction. Compaction can't touch it.

## The Silent Quality Drop

*You won't notice until it's too late*

The worst part: **the model doesn't tell you it's degrading.** It doesn't say "I'm having trouble recalling message #7." It just... gives slightly worse answers, silently.

**Symptoms of context degradation:**

- Model contradicts an earlier decision without acknowledging the change
- Model re-asks a question you already answered
- Model proposes an approach you already rejected (and explained why)
- Model loses track of variable names, file paths, or conventions you established
- Responses become more generic and less specific to your codebase
- Model starts "hallucinating" file paths or function names that are close but wrong

> **The deceptive part:** The model remains confident. It doesn't hedge or say "I might be misremembering." It states things with the same certainty whether it's recalling from the high-attention zone or the degraded middle. You have to catch the drift yourself.

**Practical defense:**

- For long sessions: use `/compact` proactively every 20-30 messages
- For critical decisions: save to Memory immediately (don't rely on conversation history)
- For ongoing work: use task lists (TodoWrite) — they're structured and resist summarization better than prose
- For architecture: keep a CLAUDE.md or plan file updated — it's re-read every turn regardless of compaction

## Your Context Window Right Now

*Where this session stands*

This session (at the time of writing) has consumed roughly:

- ~91K used (from cache write data)
- ~909K remaining

```
1,000,000 tokens total (Opus 4.7 with 1M context)

Used so far:  ~91K tokens (9.1%)
├── System prompt + tools:    ~25K
├── Hook outputs:             ~8K
├── Memory + CLAUDE.md:       ~3K
└── Conversation history:     ~55K

Remaining:    ~909K tokens (90.9%)

Estimated messages before compaction needed:
├── At current verbosity:     ~80-100 more messages
├── With heavy tool use:      ~50-60 more messages
└── With code generation:     ~30-40 more messages (code is token-dense)
```

> **Insight:** With 1M context on Opus 4.7: You're unlikely to hit the hard limit in a normal session. The real enemy is attention degradation — which starts mattering around 200K tokens. At current pace, that's roughly 20-30 more messages away. Compact proactively before then if precision matters.

## Strategies to Beat Context Loss

*Practical defenses*

| Strategy | How | Survives Compaction? |
|---|---|---|
| **Save to Memory** | "Remember that we chose PostgreSQL because of X" | YES — loaded every turn from MEMORY.md |
| **Keep CLAUDE.md updated** | Write architectural decisions to the project's CLAUDE.md | YES — re-read from disk every turn |
| **Use plan files** | Write plans to .claude/plans/ — referenced during implementation | YES — read from disk on demand |
| **Use task lists** | TaskCreate with descriptions — structured, not prose | PARTIALLY — tasks are in-session, survive compaction better than prose |
| **Proactive /compact** | Compact every 20-30 messages or when switching topics | N/A — reduces the problem preemptively |
| **Start fresh sessions** | New session for new tasks — Memory carries forward, conversation doesn't | YES — memory is cross-session by design |

> **Insight:** The hierarchy of persistence (most durable → least):
>
> 1. **CLAUDE.md** — on disk, loaded every turn, never compacted, never expires
> 2. **Memory files** — on disk, index loaded every turn, cross-session
> 3. **Plan files** — on disk, loaded during implementation
> 4. **Task lists** — in-session, structured, survive compaction better
> 5. **Recent messages** — protected during compaction (last N messages kept)
> 6. **Older messages** — FIRST to be compressed/lost
> 7. **Tool call details** — MOST vulnerable (verbose, low information density)

## Key Takeaways

*The 5 things to remember*

1. **Degradation happens before the limit.** Don't wait for auto-compaction at 800K. Quality drops noticeably around 200K tokens. Compact proactively.
2. **The middle of context is a dead zone.** Beginning (system prompt) and end (recent messages) get high attention. Everything between is on a gradient of forgetting.
3. **Compaction is 60:1 lossy compression.** Haiku makes judgment calls about what's "important." Exact values, code, reasoning, and nuance are cut. Only high-level summaries survive.
4. **The model won't tell you it's degrading.** It remains confident even when recalling from the low-attention zone. You must watch for symptoms: contradictions, re-asks, generic answers.
5. **Memory is your compaction insurance.** Anything that must survive across the full session (or across sessions) should be in Memory or CLAUDE.md — not relying on conversation history.

## ⚡ Why this matters for AI-ASE

Attention degrades around 200K tokens, well before the hard ceiling. Critical state cannot live in conversation alone — it has to live somewhere the harness reloads each turn.

- Justifies the rule that critical decisions go to **memory files**, not conversation history (V7 Files Universal Interface)
- Justifies **Layer 10** (Journey-Log Automation) — checkpoints persist past compaction
- Justifies **Layer 11** (Trust Score persistence) — the score lives in `metrics.json`, not memory