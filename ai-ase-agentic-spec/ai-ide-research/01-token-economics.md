# Token Economics

*What a single conversation actually costs — and why*

**Live experiment data** from a real session on 2026-05-13. Two sessions compared: a 10-message deep-dive conversation vs. a single "what is 2+2" baseline. All costs at your organization internal rates via LiteLLM proxy → AWS Bedrock.

## The Cache Expiration Problem

Anthropic's prompt cache has a **5-minute TTL**. If you don't send another message within 5 minutes, the cache expires and your next interaction pays full re-processing cost.

**Real-world scenario:**
You read Claude's output (3 min)
Think about it (3 min)
Get pulled into Slack (10 min)
Come back and type...
**→ Cache MISS. Pay full price again.**
For a 91K context: ~$0.50-1.00 penalty

**What should happen:**
Cache should persist for at least **15-30 minutes** — or ideally be session-scoped (alive while the Claude Code process runs).

Interactive coding isn't chat — pauses of 15-30 min between responses are *normal*.

**Can you fix this?** No — the TTL is set server-side on Anthropic's API infrastructure. It's not configurable by users or the LiteLLM proxy. A workaround would require your organization's platform team to implement a local caching layer on top, or Anthropic to offer configurable TTL (which they currently don't).

**Timeline of cost impact:**

```
0-5 min between messages → Cache HIT → ~$0.003 per cached token read
5+ min gap             → Cache MISS → ~$0.015 per token (full reprocess)

91K context × $0.015/1K = $1.37 penalty per cache miss
91K context × $0.003/1K = $0.27 if cache hits

Difference per gap: $1.10 wasted every time you pause > 5 minutes
```

## The 100x Cost Difference

*$2.47 vs $0.024 — same model, same harness*

| Metric | Deep Dive (10 msgs) | Baseline (1 msg) | Ratio |
|---|---|---|---|
| Total cost | $2.47 | $0.024 | 100x |
| Your messages | 10 | 1 | 10x |
| API round-trips | ~23 | 2 | 12x |
| Cache read | 2.1M tokens | 24.6K tokens | 85x |
| Cache write | 91.4K tokens | 1.7K tokens | 54x |
| Output tokens | 30.9K | 26 | 1,188x |
| Wall time | 1h 11m | 59s | 72x |
| API compute time | 12 minutes | 5 seconds | 144x |

> **Insight:** Why 10x messages = 100x cost: Cost isn't linear because (1) each round-trip re-sends the growing conversation, (2) verbose output tokens are expensive at Opus pricing, and (3) tool calls multiply the round-trips — 19 tool calls created ~23 API calls.

## Where the Money Goes

*Output tokens dominate*

Breakdown of the $2.47 deep-dive session:

- Output tokens (30.9K @ Opus rate): ~$2.00 (81%)
- Cache read (2.1M tokens @ 1/10th rate): ~$0.25 (10%)
- Cache write (91.4K first-time tokens): ~$0.13 (5%)
- Haiku background tasks: $0.09 (4%)

> **Insight:** The expensive thing is my verbosity. Output tokens at Opus rates dominate cost. If you want cheaper sessions: ask for terse answers, use Sonnet for simple tasks, or switch to `/fast` mode. The system prompt (via cache) is relatively cheap.

## How Prompt Caching Works

*Server-side, 5-min TTL, prefix-matched*

**It's NOT Redis. NOT local. NOT on your machine.**

The cache lives on Anthropic's API servers (AWS Bedrock in your organization's VPC). It's a server-side optimization built into the Messages API.

| Property | Value |
|---|---|
| Location | Anthropic/Bedrock API servers (inside your organization network) |
| Type | Prefix-match cache (not key-value) |
| TTL | 5 minutes from last use |
| Keep-alive | Each cache HIT resets the 5-min timer |
| Scope | Per-organization, cross-session if prefix matches |
| Invalidation | Any change to cached prefix, or 5-min timeout |
| Write cost | Same as regular input (full price, first time) |
| Read cost | 1/10th of input price (90% discount) |

**How prefix matching works:**

```
API Call #1 (first message):
┌──────────────────────────────────────────────────────────┐
│ System prompt (20K) │ Tools (5K) │ Message (50) │ NEW    │
└──────────────────────────────────────────────────────────┘
  ← CACHE WRITE (25K tokens written) →    ← processed →

API Call #2 (after tool result):
┌──────────────────────────────────────────────────────────────────┐
│ System prompt (20K) │ Tools (5K) │ Msg + Result (2K) │ NEW (50) │
└──────────────────────────────────────────────────────────────────┘
  ← CACHE READ (25K served from cache) →   ← processed →

API Call #15 (conversation grown):
┌───────────────────────────────────────────────────────────────────────────┐
│ System prompt (20K) │ Tools (5K) │ Full history (60K) │ Latest (500) │ N │
└───────────────────────────────────────────────────────────────────────────┘
  ← CACHE READ (grows each call — 85K from cache) →     ← new →
```

The PREFIX keeps growing as conversation grows. Each call caches more. The "new" part (what's processed fresh) stays small.

> **Pain point:** The 5-minute TTL problem: If you step away for 6+ minutes between messages, the cache expires. Your next message pays full price again (cache WRITE instead of READ). For a 91K-token conversation, that's a ~$1+ penalty per cache miss. If you routinely pause 30+ minutes between responses, every resumption is effectively a cold start.

> **Insight:** Cross-session cache hit: In our baseline test, the "2+2" session showed 24.6K cache READ immediately — because it started within 5 minutes of our active session. The system prompt prefix was identical, so it hit the existing cache entry. Start a session after 6+ minutes of inactivity? You'd see 0 cache read and ~24.6K cache write instead.

## The API Call Multiplication Effect

*1 user message = many API calls*

You sent 10 messages. The harness made ~23 API calls. Here's why:

```
You type: "create an HTML file showing inner workings"

  API call #1: Model produces → EnterPlanMode tool call
  API call #2: Model produces → AskUserQuestion tool call
                [you answer]
  API call #3: Model produces → Write (plan file) tool call
  API call #4: Model produces → ExitPlanMode tool call
                [you approve]
  API call #5: Model produces → Write (HTML) + Bash (open) tool calls
  API call #6: Model produces → final text response

  = 6 API calls for 1 user message
```

Each tool call requires a minimum of 2 API calls:

1. Model generates the tool call (API call N)
2. Harness executes tool, feeds result back → Model processes result (API call N+1)

Parallel tool calls (e.g., 8 TaskCreate calls in one response) are more efficient — they batch into fewer round-trips.

> **Insight:** The math: 2.1M cache read / ~91K average context ≈ 23 API calls. Each one re-sends the full conversation from cache + adds new content. This is why long conversations with many tool calls get expensive — it's not the tool execution, it's the repeated context transmission.

## The Invisible Haiku

*Cheaper model running silently*

Both sessions showed Haiku usage you never directly see:

| | Deep Dive | Baseline |
|---|---|---|
| Haiku input | 3.1K | 201 |
| Haiku output | 16.5K | 16 |
| Haiku cost | $0.09 | $0.0003 |

What's Haiku doing?

- **Session initialization:** Quick classification/routing on startup
- **Compaction:** When context gets long, Haiku summarizes older messages (cheap summarization)
- **Internal tasks:** The harness may use Haiku for lightweight processing that doesn't need Opus-level reasoning

> **Insight:** Cost efficiency: Haiku at $0.09 for 16.5K output vs Opus at $2.38 for 30.9K output. If Claude Code used Opus for these background tasks, the session would cost significantly more. The multi-model architecture keeps costs down for routine work.

## How to Reduce Costs

*Practical levers you can pull*

| Lever | Impact | How |
|---|---|---|
| Use Sonnet for simple tasks | ~5x cheaper output | `/model sonnet` for straightforward work |
| Ask for terse answers | Reduces output tokens | "Be brief" or "one-liner" in your prompt |
| Batch related questions | Fewer round-trips | Ask 3 things in 1 message, not 3 separate messages |
| Keep sessions active | Avoid cache misses | Don't pause 5+ min between messages (cache expires) |
| Shorter CLAUDE.md + memory | Smaller system prompt | Trim unnecessary context from MEMORY.md |
| Use `/clear` for fresh starts | Resets context size | When conversation history is no longer needed |

> **Pain point:** The 5-minute cache problem (real-world impact): If your workflow involves reading model output, thinking for 6+ minutes, then responding — you pay a cache miss penalty every time. A 91K context session loses ~$1 per cache miss. For users who routinely pause 15-30 minutes between messages, this adds up significantly. The cache TTL should arguably be session-scoped or at least 15 minutes for interactive coding workflows.

## Key Takeaways

*The 5 things to remember*

1. **Output tokens are the #1 cost driver** — not your system prompt, not the cache. Opus output at $75/MTok means verbose explanations are expensive. My 30.9K output cost more than the 2.1M cached input.
2. **Tool calls multiply API calls** — each tool use is at minimum 1 extra round-trip. A 19-tool-call session triggered ~23 API calls from just 10 user messages.
3. **The cache saves you 90%** — but only if you keep it warm. The 5-minute TTL means pausing > 5 min between messages resets the savings. Active conversation is cheap per-call; interrupted conversation is expensive.
4. **The minimum cost of "hello" is ~$0.02** — even the simplest interaction loads ~25K tokens of system prompt. You can't go below this floor.
5. **Haiku runs invisibly** — the harness uses a cheaper model for background tasks, keeping the multi-model cost profile efficient.

## ⚡ Why this matters for AI-ASE

Output tokens dominate cost. Cache decays at five minutes. These two facts shape AI-ASE's context strategy more than any other lesson.

- Justifies **V5** (Context is King) — the kernel is 50 lines, not 750. Skills and rules load on-demand
- Justifies **Layer 3** (RAG retriever) — surface only the most relevant rules per turn, not the whole catalog
- Justifies the **Profile system** — a typo fix doesn't get a feature-profile context budget