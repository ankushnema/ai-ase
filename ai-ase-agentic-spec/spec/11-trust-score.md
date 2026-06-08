# Trust Score & Policy

## Purpose

Two coupled modules:

- `trust.py` — computes a 0–100 quality score from observable signals.
- `policy.py` — decides allow / deny / escalate for read / write / execute actions, using the trust score as one input.

V6 (Trust Must Be Earned) made concrete: the framework starts at trust 70 and pays for or charges back based on what the agent does in practice.

## `trust.py`

### Public interface

```python
@dataclass
class TrustScore:
    score: int                       # 0–100
    band: str                        # "excellent" | "good" | "acceptable" | "failing" | "critical"
    confidence: str                  # "low" | "medium" | "high"
    components: dict[str, float]     # signal → contribution
    timestamp: str

def compute(signals: dict) -> TrustScore: ...

def current() -> TrustScore: ...     # read .ai-ase/trust.json

def persist(score: TrustScore) -> None: ...
```

### Component weights

| Signal | Weight | Range | Notes |
|---|---|---|---|
| `scanner_pass_rate` | 0.20 | 0.0–1.0 | % rules passing |
| `test_coverage` | 0.20 | 0.0–1.0 | tooling-provided coverage |
| `mutation_kill_rate` | 0.20 | 0.0–1.0 | from `mutation-testing` skill |
| `business_rule_coverage` | 0.15 | 0.0–1.0 | % `[B###]` rules with tests |
| `human_review_depth` | 0.10 | 0–100 | 0=none, 50=glance, 100=deep |
| `drift_delta_count` | 0.10 | 0–100 | 100 − (unplanned_changes × 20) |
| `hallucination_flags` | 0.05 | 0–100 | 100 − (flags × 25) |

### Algorithm: `compute(signals)`

```
1. components = {}
2. available_weights = []
3. for name, weight in WEIGHTS.items():
4.   if name not in signals: continue        # GP6: missing signal, redistribute
5.   value = normalize(name, signals[name])  # → 0–100 scale
6.   components[name] = value * weight
7.   available_weights.append(weight)
8. total_weight = sum(available_weights)
9. score = round(sum(components.values()) / total_weight) if total_weight else 0
10. band = band_of(score)
11. confidence = "high" if total_weight >= 0.70 else "medium" if total_weight >= 0.40 else "low"
12. return TrustScore(score, band, confidence, components, utcnow_iso())
```

### Bands

```python
def band_of(score: int) -> str:
    if score >= 85: return "excellent"
    if score >= 70: return "good"
    if score >= 50: return "acceptable"
    if score >= 30: return "failing"
    return "critical"
```

### Confidence

Without confidence, a score computed from 1/7 signals reads the same as one computed from 7/7. The dashboard prints confidence next to the score. Don't trust an "Excellent" score with `low` confidence.

## `policy.py`

### Public interface

```python
@dataclass
class PolicyDecision:
    decision: str           # "allow" | "deny" | "escalate"
    reason: str
    subject: str            # path, command, etc.
    action: str             # "read" | "write" | "execute"

def decide(action: str, subject: str, *,
           profile: str | None = None,
           trust: int | None = None) -> PolicyDecision: ...
```

### Algorithm: `decide(action, subject, profile, trust)`

```
1. profile = profile or active_profile()["id"]
2. trust = trust if trust is not None else current().score
3. mode = mode_from_trust_and_profile(trust, profile)
4. if action == "read": return allow(subject, action)        # GP3: reads are free
5. if action == "write":
     if mode == "read-only": return deny(subject, action, "trust below threshold")
     if mode == "deny-all": return deny(subject, action, "trust critical")
     return allow(subject, action)
6. if action == "execute":
     if matches_destructive(subject): return deny(subject, action, "destructive command")
     if mode in ("read-only","deny-all"): return deny(...)
     return allow(...)
7. raise ValueError(action)
```

### `mode_from_trust_and_profile`

```
if trust >= 50: return "normal"          # per-profile defaults apply
if trust >= 30: return "read-only"       # forced regardless of profile
return "deny-all"                        # observe only
```

### Destructive command catalog

```python
DESTRUCTIVE_PATTERNS = [
    r"\brm\s+-rf\s+(/|~|\.)\s*$",
    r"\bgit\s+push\s+(--force|-f)\b",
    r"\bgit\s+reset\s+--hard\b",
    r"\bdocker\s+system\s+prune\b",
    r"\bdrop\s+(table|database|schema)\b",
]
```

Word boundaries matter — `rm -rf /some/path` is allowed; `rm -rf /` is not.

## Disk format: `.ai-ase/trust.json`

```json
{
  "score": 82,
  "band": "good",
  "confidence": "medium",
  "components": {
    "scanner_pass_rate": 18.8,
    "mutation_kill_rate": 15.6
  },
  "updated_at": "2026-06-08T10:30:00Z"
}
```

Updated by `trust.persist()` after every recomputation.

## Audit integration

Every `compute()` call writes a `trust_score` event. Every `decide()` call writes a `policy_check` event. See [10-AUDIT-LOG.md](../spec/10-audit-log.md).

## Tests

- Weight redistribution math: 3/7 signals → weights sum to 0.55 → divide accordingly.
- Bands at boundary values (49, 50, 69, 70, 84, 85).
- Confidence: low / medium / high cutoffs.
- `decide(read, ...)` is always allow regardless of trust.
- `decide(write, ...)` with trust=29 → deny.
- `decide(execute, "rm -rf /")` → deny.
- `decide(execute, "rm -rf /home/user/scratch")` → allow (boundary on `/`).

## Anti-patterns

| Don't | Because |
|---|---|
| Penalize the score for a single bad event | Trust is a rolling signal. One blip should not crater it. Use a sliding window. |
| Allow the AI to compute its own trust | The compute function should be called by the framework, not by the agent. |
| Hide low confidence | Surface it loudly. Otherwise scores mislead. |

## Ground truth

No vendored file. The reference implementation has `trust.py` and `policy.py` modules following this shape.