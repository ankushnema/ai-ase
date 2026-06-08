# AI-ASE — Complete Specification

> **AI-generated code is going to production at your company. There is no governance layer between the model and `main`. AI-ASE is that layer.**

A hook-enforced controls layer for AI-assisted coding. Turns the AI's probabilistic "usually follows your rules" into deterministic "always follows your rules." Vendor-agnostic. Files-on-disk. Apache-2.0.

---

## See it in 60 seconds

```bash
pip install ai-ase
cd your-repo
ai-ase init                # installs hooks into your AI IDE
ai-ase scan .              # shows what would be blocked today
```

Then ask your AI to do something that breaks one of your rules. Watch it get blocked, not apologized at.

Full walkthrough: [examples/quickstart.md](examples/quickstart.md).

---

## What's in this folder

```
publish/
├── README.md                  ← you are here
├── READING-GUIDE.md           ← reading paths by persona / time budget
│
├── docs/                      ← the concept layer (what it is, why, how it's shaped)
├── catalogs/                  ← the 71 rules, 21 skills, 9 MCP tools
├── examples/                  ← quickstart + end-to-end walkthrough
├── spec/                      ← module-by-module rebuild specs (22 numbered + build path + source map)
├── artifacts/                 ← the actual YAML / JSON / markdown the engine consumes
└── ai-ide-research/           ← the empirical research that drove every design choice
```

Each folder has its own `README.md` that lists what's inside.

## Where to start

**Just here to figure out what this is?** → [docs/01-what-is-aiase.md](docs/01-what-is-aiase.md), 2 minutes.

**Want to try it?** → [examples/quickstart.md](examples/quickstart.md).

**Need to rebuild the package from scratch?** → [spec/00-build-path.md](spec/00-build-path.md), then [spec/](spec/) in numeric order, with [artifacts/](artifacts/) as the canonical schema source.

A more detailed reading map by persona is in [READING-GUIDE.md](READING-GUIDE.md).

---

## What this folder is — and is not

This folder contains **zero executable code** — only specifications, schemas, algorithms, decisions, and the canonical on-disk artifacts the engine consumes. The promise is:

> A capable AI coding agent, given ONLY this folder and a Python toolchain, can rebuild the entire AI-ASE package such that it passes the test suite described in [spec/02-package-config.md](spec/02-package-config.md).

If you find a section where that promise fails, open an issue. The spec is wrong, not the implementation.

---

## Attribution

- License: Apache-2.0
- Values & principles: based on [arXiv 2604.14228](https://arxiv.org/abs/2604.14228) (VILA Lab / MBZUAI + UCL)
- AI IDE behavior research: see [ai-ide-research/](ai-ide-research/)