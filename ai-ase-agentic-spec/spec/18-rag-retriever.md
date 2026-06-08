# RAG Retriever

## Purpose

`rag_retriever.py` is the keyword-based relevance scorer used by the MCP server (`get_active_rules`, `get_skill`) and by the context assembler (when budget-constrained, picks the most relevant of competing guardrail documents).

Pure TF-IDF. **No ML model.** No embeddings. No vector database. V4 + V7 — math on text files.

## Why TF-IDF and not embeddings

| Approach | Pros | Cons |
|---|---|---|
| **TF-IDF** | Zero dependencies; transparent (you can read the index); fast; works fine for ≤ 500 documents | Misses semantic synonymy (`db` ≠ `database`) |
| Local embedding (all-MiniLM-L6-v2) | Better semantic recall | Adds ~50 MB model dependency; opaque scores |

For 71 rules + 21 skills + ~20 guardrail docs, TF-IDF is decisively the right call. The migration trigger is somewhere around 500 documents — when that arrives, swap in a local embedder behind the same interface.

## Public interface

```python
@dataclass
class IndexedDoc:
    id: str
    text: str
    tokens: list[str]
    metadata: dict

class TFIDFIndex:
    def __init__(self, docs: list[IndexedDoc]): ...
    def search(self, query: str, top_k: int = 10) -> list[tuple[str, float]]: ...
    def explain(self, query: str, doc_id: str) -> dict: ...

def build_index(*, rules: bool = True, skills: bool = True, docs: bool = True) -> TFIDFIndex: ...
```

## Algorithm: build

```
1. For each indexable item:
2.   text = " ".join([name, description, rationale, fix_guidance])
3.   tokens = tokenize(text)        # see below
4.   tokens = [t for t in tokens if t not in STOPWORDS]
5.   doc = IndexedDoc(id=item.id, text=text, tokens=tokens, metadata={...})
6.   index.add(doc)
7. Compute document frequencies: df[term] = count of docs containing term
8. Compute IDF: idf[term] = log(N / df[term])
```

## Algorithm: search

```
def search(query: str, top_k: int = 10) -> list[tuple[str, float]]:
    q_terms = tokenize(query)
    q_terms = [t for t in q_terms if t not in STOPWORDS]
    scores = {}
    for doc in self.docs:
        score = 0.0
        for term in q_terms:
            if term in doc.tokens:
                score += self.idf.get(term, 0.0)
        if score > 0:
            scores[doc.id] = score
    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    return ranked[:top_k]
```

## Tokenization

```python
import re
TOKEN_RE = re.compile(r"[a-z0-9]+")
def tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())
```

Lowercase, alphanumeric runs, nothing fancy. Stemming is overkill for English technical text.

## Stopwords

A 90-word English stopword list:

```
the a an is are was were be been being have has had do does did
will would could should may might must shall can need to of in
for on with at by from as into through during before after between
under again then once when where why how all each every both few
more most other some such no not only own same so than too very
and but or if this that these those it its use used using file code
```

Plus framework-specific noise: `rule`, `check`, `verify`, `ensure` (they appear in every rule and don't discriminate).

## When the assembler uses it

When `context_for_file(filepath)` returns multiple guardrail docs and the budget cannot fit them all, the assembler:

1. Builds (or reuses) a TF-IDF index over the candidate docs.
2. Uses the filename + nearby code (if available) as the query.
3. Keeps the top-scored docs that fit the budget.

This is what V5 (Context is King) looks like at run-time: the model never sees the "general" version when the "specific" version exists.

## Tests

- Index builds without errors over the bundled corpus.
- Querying for `"hardcoded password"` returns VR-01 first.
- Querying for `"circuit breaker"` returns the resilience rules first.
- Stopword filtering removes noise.
- IDF is correctly higher for rare terms.
- `top_k=3` returns at most 3 results.
- Empty query returns empty list.

## Anti-patterns

| Don't | Because |
|---|---|
| Add stemming / lemmatization in v1 | Marginal value, real complexity. Wait for evidence it's needed. |
| Cache scores globally | Cache is keyed by `(index_version, query)`. Index changes invalidate. |
| Use cosine similarity over raw IDF sum | For tiny corpora it makes no practical difference and obscures the math. |
| Replace TF-IDF before 500-doc threshold | YAGNI. Premature optimization. |

## Ground truth

No vendored file. This spec is the authoritative description.
