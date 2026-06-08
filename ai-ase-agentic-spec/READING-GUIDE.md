# Reading Guide — Pick Your Path

The main [README.md](README.md) is the front door. This guide is the map for readers who want a specific route through the spec.

---

## By persona

| You are... | Start here | Then |
|---|---|---|
| **Curious — never heard of AI-ASE** | [docs/01-what-is-aiase.md](docs/01-what-is-aiase.md) (2 min) | [docs/02-why-it-exists.md](docs/02-why-it-exists.md), then stop. |
| **Engineering leader evaluating it** | [docs/02-why-it-exists.md](docs/02-why-it-exists.md) | [docs/05-architecture.md](docs/05-architecture.md), then [examples/walkthrough.md](examples/walkthrough.md). |
| **Developer about to adopt it** | [examples/quickstart.md](examples/quickstart.md) | [docs/04-eight-immutable-rules.md](docs/04-eight-immutable-rules.md), then [docs/06-five-phases.md](docs/06-five-phases.md). |
| **AI agent rebuilding it** | [spec/00-build-path.md](spec/00-build-path.md) | [spec/](spec/) in numeric order, [artifacts/](artifacts/) as canonical schema source. |
| **Reviewer doing diligence** | docs/ in order | Spot-check [spec/](spec/) against [spec/source-mapping.md](spec/source-mapping.md) and the actual files under [artifacts/](artifacts/). |

---

## By time budget

### 3 minutes — "what is it?"

[docs/01-what-is-aiase.md](docs/01-what-is-aiase.md).

### 10 minutes — "is this real?"

1. [docs/01-what-is-aiase.md](docs/01-what-is-aiase.md)
2. [docs/02-why-it-exists.md](docs/02-why-it-exists.md)
3. [examples/quickstart.md](examples/quickstart.md) — skim, don't run

### 30 minutes — "convince me it works"

Above, plus:

4. [docs/03-core-values.md](docs/03-core-values.md)
5. [docs/05-architecture.md](docs/05-architecture.md)
6. [docs/06-five-phases.md](docs/06-five-phases.md)
7. [examples/walkthrough.md](examples/walkthrough.md)

### Full read — "I want the complete framework"

All of `docs/` in order, then:

- [catalogs/rules.md](catalogs/rules.md), [catalogs/skills.md](catalogs/skills.md), [catalogs/tools.md](catalogs/tools.md)
- [spec/](spec/) in numeric order for the module-by-module rebuild specs
- [artifacts/](artifacts/) for the canonical YAML/JSON the engine actually consumes
- [examples/walkthrough.md](examples/walkthrough.md) for the end-to-end story
- [spec/source-mapping.md](spec/source-mapping.md) to verify completeness
- [ai-ide-research/](ai-ide-research/) for the empirical research behind design decisions