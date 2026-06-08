# What Is AI-ASE?

**Read time:** 2 minutes.

---

## The core theme

> **AI-ASE makes AI coding deterministic.**

AI assistants are probabilistic — they *usually* follow your rules. AI-ASE turns "usually" into "always" for everything that matters.

It does this by treating governance as a **coordinated system**, not a single mechanism. Rules, skills, phases, hooks, agents, and audit each cover what the others can't. The point isn't any one of them — the point is that together they close the gaps that let a probabilistic AI ship code your team wouldn't accept.

## What problem is this *really* solving?

AI-ASE is a **controls and risk-reduction layer for AI-assisted coding** — sometimes called *vibe coding*: prompting an assistant, accepting its suggestions, watching code appear without writing it yourself.

Vibe coding is fast. It is not, by default, production-ready. The same AI that writes a beautiful function in 8 seconds will, in the next 8 seconds, hardcode a credential, swallow an exception, or refactor an unrelated module "while it's there." None of that is malicious — it's the statistical nature of the model.

AI-ASE is the layer between "the AI generated something" and "the something is allowed to land." It is not a tool that helps you write better code yourself. It is a tool that makes the AI's output safe enough to keep up with the AI's speed.

## How to think about it

Three ideas, in order:

1. **The AI is a creative partner, not a compliant one.** It will improvise. Plan for that.
2. **Instructions are negotiation; enforcement is not.** Anything that *must* hold has to live outside the AI's reach.
3. **No single guardrail is enough.** Determinism comes from layered, coordinated checks — the right one firing at the right moment.

That's the whole framework. Everything else is detail.

## What it gives you

- Code the AI writes follows your rules — every time, not most of the time.
- When something does slip through, you have a complete record of why.
- The same governance applies in your IDE, your CI, and your commit gate — without rewriting it for each.

## What it is not

- Not an AI model.
- Not a linter.
- Not "just hooks" or "just instructions."
- Not tied to any one AI IDE.
- Not a substitute for code review on production-critical paths — it's the floor, not the ceiling.

## Where to go next

- **Why text-only governance fails** → [docs/02-why-it-exists.md](../docs/02-why-it-exists.md)
- **The values that shape it** → [docs/03-core-values.md](../docs/03-core-values.md)
- **The full architecture** → [docs/05-architecture.md](../docs/05-architecture.md)
- **Try it** → [examples/quickstart.md](../examples/quickstart.md)