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