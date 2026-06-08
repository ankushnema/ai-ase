# Core Values and Guiding Principles

**Read time:** 6 minutes.

These are the constraints behind every AI-ASE design choice. Not aspirations — engineering rules. A feature that violates one of these does not ship.

Each value below is followed by a real example so it doesn't read as a slogan.

Source: [arXiv 2604.14228](https://arxiv.org/abs/2604.14228).

> If you're wondering "doesn't my AI assistant already do this?" — that's the right question to ask, but it belongs in [docs/02-why-it-exists.md](../docs/02-why-it-exists.md). This doc assumes you've decided enforcement matters and now want the constraints behind every design choice.

---

## The 7 Core Values — the WHY

### V1 — Safety Over Speed

> Guardrails by default, autonomy by exception.

**What it means:** The AI is never allowed to do something risky *just because it's faster*. Risk is opt-in, not opt-out.

**Example.** You ask the AI to "refactor the auth module." It wants to delete an unused-looking helper. Default behavior under AI-ASE: BLOCK and ask. The AI is fast at deleting; humans are slow at recovering. The default is the safer of the two.

---

### V2 — Transparency Over Magic

> If you can't audit it, it shouldn't exist.

**What it means:** Every decision the framework makes — every rule that fires, every BLOCK, every trust drop — must be inspectable after the fact, in plain text.

**Example.** A teammate asks "why did the AI refuse to commit this last Friday?" You open `audit.jsonl`, grep for that file, and see: *PreToolUse hook blocked Write — rule VR-12 (no inline secrets) — line 47.* No hidden state, no black box.

#### Why session logging is the thing, not a thing

V2 lives or dies on the session log. The log is the only artifact that captures **both** the AI's decisions *and* the developer's decisions during a vibe-coding session. That matters because incidents almost always involve both:

> **Scenario.** Six weeks after launch, your billing integration starts double-charging on retries. The bug is in a one-line change. Git blame says "Alex, 6 weeks ago, AI-assisted." Nobody remembers the conversation.
>
> Without the session log: you have the code change and nothing else. The reasoning is gone. The alternatives the AI suggested are gone. Whether Alex overrode a warning is gone.
>
> With the session log:
> ```
> 14:22  user: "make retry idempotent"
> 14:22  ai: proposed using Idempotency-Key header (best practice for billing)
> 14:23  ai: WARN — alternative: in-memory dedup. Faster but loses idempotency on restart.
> 14:23  user: "go with in-memory, we'll fix later"
> 14:23  ai: applied in-memory dedup. Logged WARN: not durable across restart.
> ```
> You now know exactly what happened. The AI proposed the right thing. The human chose speed. The warning was logged. The framework did its job; the decision is auditable. *That's* transparency.

The log captures intent, not just outcome. Without it, every "why does this code exist?" conversation is a forensic dead end.

---

### V3 — User Agency Over Model Autonomy

> The model proposes. The user disposes. Always.

**What it means:** The AI never takes a meaningful action without an explicit human "yes." Silence is not consent.

**Example.** The AI finishes a design and says "ready to implement." It does *not* then start writing code. It waits. You type "go" → it proceeds. If you walk away from your laptop, nothing happens. That's intentional.

---

### V4 — Simplicity Over Sophistication

> Complex domain, simple engineering. Files beat infrastructure.

**What it means:** When two designs solve the same problem, pick the one with fewer moving parts. A file on disk beats a database. A regex beats a model. YAML beats a service.

**Example.** AI-ASE's rule catalog could have been a vector database with embeddings. Instead it's `rules/*.yaml` on disk, retrieved with TF-IDF. No vector DB to host, back up, or version. You can read and edit a rule with a text editor.

---

### V5 — Context is King

> Right info, right time. Not all at once. Not after the fact.

**What it means:** The AI's attention is a budget. Loading the entire rulebook on every turn burns the budget on things irrelevant to the current task.

**Example.** You're editing `auth/login.py`. AI-ASE injects only the 5 most relevant auth-related rules, not all 67. The other 62 rules still exist and still fire when relevant — they just don't compete for the AI's attention right now.

---

### V6 — Trust Must Be Earned

> Zero-trust default. Least privilege. Gradual escalation.

**What it means:** A fresh session, a new agent, a low-trust team — none get full permissions by default. Permissions grow with demonstrated track record.

**Example.** A new project starts with a trust score of 50. After 20 clean writes (no rule violations, no human overrides), trust climbs above 80 and the agent unlocks lighter ceremony for low-risk changes. One bad commit drops trust back down. The system teaches itself who to trust.

---

### V7 — Files Are Universal Interface

> Everything grep-able, git-able, human-readable.

**What it means:** No opaque stores. Every artifact AI-ASE produces is a text file you can read, diff, commit, and inspect with normal tools.

**Example.** Want to know what governance applies to your repo? List `.ai-ase/rules/`. Want to know what happened in yesterday's session? Read `.ai-ase/audit.jsonl`. Want to roll back a rule change? `git revert`. No special UI required.

---

## The 8 Guiding Principles — the HOW

These are how the values get applied in practice — the questions to ask before acting.

### GP1 — Do Less Over Do Wrong

> If unsure, ask. Don't guess.

**Example.** The AI sees `User.email` and `User.email_address` in the same module. Instead of guessing which is canonical, it asks. A wrong guess silently propagates; a clarifying question costs 30 seconds.

---

### GP2 — Match Scope to Request

> Bug fix means bug fix. No refactoring neighbors.

**Example.** You ask "fix the null pointer on line 42." The AI fixes line 42. It does *not* also reformat the file, rename a variable it found confusing, or extract a helper. Anything beyond the ask gets surfaced as a suggestion — never silently included in the diff.

---

### GP3 — Observation Free, Mutation Expensive

> Read freely. Write carefully.

**Example.** Reading 200 files to understand a module: cheap, encouraged. Writing 1 file: requires being in the Reflector phase, having an approved design, and passing the scanner. Asymmetry by design.

---

### GP4 — Local > Shared, Reversible > Permanent

> Choose the less impactful action.

**Example.** Two ways to deploy a fix: (a) push directly to main, (b) open a PR for review. The framework defaults to (b). Reversible. Local. Reviewable.

---

### GP5 — Show Your Work

> Surface decisions, tool calls, reasoning.

**Example.** When the AI moves a function, it doesn't just commit. It writes one line in the session log: *"Moved `validate_email()` from `utils.py` to `auth/validation.py` because…"*. Six months later, the next person knows why.

---

### GP6 — Degrade Gracefully

> Tool fails? Try alternatives. Don't crash.

**Example.** The MCP rule scanner can't reach the rule catalog (file locked). AI-ASE falls back to the bundled default catalog and emits a WARN. It does *not* silently allow everything because its primary check failed.

---

### GP7 — Future Context > Current Convenience

> Logs and audit pay compound interest.

**Example.** Skipping the session log saves 5 seconds now. Six months later, when you need to know "who changed this contract and why," that 5 seconds costs 3 hours of git archaeology. AI-ASE refuses the shortcut.

---

### GP8 — User's Codebase is Sovereign

> Govern, don't dictate. Teams own their rules.

**Example.** AI-ASE ships with a default rule catalog. Your team disagrees with rule VR-34. You edit your local YAML override. AI-ASE respects it. The framework is a host, not a landlord.

---

## How to use these as an agent

If you are operating inside an AI-ASE session, the values are the questions to ask before you act:

- Before writing: *did the user authorize this?* → V3
- Before proposing abstraction: *would a file do?* → V4
- Before loading context: *does the model need this for THIS task?* → V5
- Before a costly action: *has this agent earned the trust?* → V6
- Before using anything opaque: *is there a grep-able alternative?* → V2 / V7
- Before expanding scope: *did the user actually ask for this?* → GP2

The values are *why*. The 8 immutable rules in [docs/04-eight-immutable-rules.md](../docs/04-eight-immutable-rules.md) are the operational *how*.
