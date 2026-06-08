# Core Engine

## Purpose

`engine.py` is the scanner. Both CLI and MCP server import it. Loads YAML rules, scans source code against them, returns `ScanResult`. Pure function — no I/O side effects except rule-file reading.

## Public interface

```python
from dataclasses import dataclass, field

@dataclass
class Violation:
    rule_id: str            # e.g. "VR-01"
    rule_name: str          # "Hardcoded Password"
    action: str             # "BLOCK" | "WARN"
    severity: str           # "critical" | "high" | "medium" | "low"
    line: int               # 1-indexed
    line_content: str       # stripped matched line
    description: str
    fix_guidance: str
    guardrail_ids: list[str] = field(default_factory=list)

@dataclass
class ScanResult:
    filename: str
    profile: str
    allowed: bool                     # True iff zero BLOCK violations
    blocks: list[Violation]
    warnings: list[Violation]
    rules_checked: int

def validate(code: str, filename: str, profile: str = "feature",
             rules_path: Path | None = None) -> ScanResult: ...

def load_rules(rules_path: Path) -> list[dict]: ...

def find_rules_path(start: Path) -> Path: ...

def detect_language(filename: str) -> str: ...

def detect_profile(task_description: str) -> str: ...
```

## Algorithm: `validate(code, filename, profile, rules_path=None)`

```
1. rules_path = rules_path or find_rules_path(Path.cwd())
2. rules = load_rules(rules_path)  # cached
3. language = detect_language(filename)
4. applicable = filter_rules(rules, profile, language)
5. blocks, warnings = [], []
   for rule in applicable:
     pattern = rule["pattern"].strip()                  # strip block-scalar trailing \n
     if pattern in {"", "STRUCTURAL_CHECK", "NO_PATTERN"}: continue
     try: rx = re.compile(pattern)
     except re.error: continue                          # GP6: degrade gracefully
     for lineno, line in enumerate(code.splitlines(), start=1):
       if rx.search(line):
         v = Violation(
           rule_id=rule["id"], rule_name=rule["name"],
           action=rule["action"], severity=rule.get("severity","medium"),
           line=lineno, line_content=line.strip(),
           description=rule.get("description",""),
           fix_guidance=rule.get("fix-guidance",""),
           guardrail_ids=rule.get("guardrail-ids",[]),
         )
         (blocks if v.action == "BLOCK" else warnings).append(v)
6. return ScanResult(
     filename=filename, profile=profile,
     allowed=(len(blocks) == 0),
     blocks=blocks, warnings=warnings,
     rules_checked=len(applicable),
   )
```

## Algorithm: `find_rules_path(start)`

```
1. Try start / "core/rules"          → if exists, return
2. Try start / ".ai-ase/rules"       → if exists, return
3. Walk up to 10 parents, repeat 1+2 at each level
4. Fallback: importlib.resources.files("ai_ase") / "rules"
```

## Algorithm: `detect_language(filename)`

```
EXT_MAP = {
  ".java": "JAVA", ".py": "PYTHON", ".cs": "CSHARP",
  ".js": "JS", ".ts": "JS", ".tsx": "JS", ".jsx": "JS",
  ".go": "GO", ".rs": "RUST", ".rb": "RUBY", ".php": "PHP",
  ".yml": "CONFIG", ".yaml": "CONFIG", ".json": "CONFIG",
  ".properties": "CONFIG", ".xml": "CONFIG", ".env": "CONFIG",
  ".dockerfile": "DOCKER",
}

basename = Path(filename).name.lower()
if basename.startswith("dockerfile"): return "DOCKER"
return EXT_MAP.get(Path(filename).suffix.lower(), "OTHER")
```

## Algorithm: `detect_profile(task_description)`

First-match-wins, ordered:

```
PROFILE_PATTERNS = [
  ("incident",  r"\b(incident|p1|p2|production down|emergency|outage|sev[12]|urgent)\b"),
  ("migration", r"\b(migrate|rewrite|modernize|legacy|greenfield|new service|architecture)\b"),
  ("patch",     r"\b(fix|typo|hotfix|patch|quick fix|one-liner|small change|config update|bug)\b"),
]

text = task_description.lower()
for name, pat in PROFILE_PATTERNS:
  if re.search(pat, text): return name
return "feature"
```

## Algorithm: `filter_rules(rules, profile, language)`

```
def rule_applies(rule, language):
  fts = rule.get("file-types", [])
  if "ALL" in fts: return True
  if "CODE" in fts and language in {"JAVA","PYTHON","CSHARP","JS","GO","RUST"}: return True
  return language in fts

for rule in rules:
  if profile not in rule.get("profiles", ["patch","feature","migration","incident"]): continue
  if not rule_applies(rule, language): continue
  yield rule
```

## Algorithm: `load_rules(rules_path)` — cached

```
1. files = sorted(rules_path.rglob("*.rules.yaml"))   # deterministic order
2. cached_at = (rules_path, max(file.stat().st_mtime for file in files))
3. if cached_at == self._cache_key: return self._cache
4. rules = []
   for path in files:
     doc = yaml.safe_load(path.read_text())
     rules.extend(doc.get("rules", []))
5. self._cache, self._cache_key = rules, cached_at
6. return rules
```

## Tests (target ≥ 44)

- A clean fixture returns `allowed=True`, no blocks, no warnings.
- A fixture containing each BLOCK rule trips exactly that rule.
- `profile="patch"` filters out non-patch-active rules.
- Language detection: `.py`, `.java`, `.yml`, `Dockerfile`, unknown.
- Bad regex in YAML is skipped silently (no crash).
- `find_rules_path()` walks upward and finds project-local rules.
- `find_rules_path()` falls back to bundled when none found.
- `detect_profile()` priority: incident > migration > patch > feature.
- Empty pattern, `STRUCTURAL_CHECK`, `NO_PATTERN` are skipped.

## Anti-patterns to avoid

| Don't | Because |
|---|---|
| Cache forever | Rules change at edit time. Use mtime-based cache key. |
| Use `yaml.load` | Unsafe. Always `yaml.safe_load`. |
| Forget `.strip()` on patterns | YAML block scalars add `\n`. Regex won't match. |
| Treat regex compilation failure as fatal | GP6 (Degrade Gracefully). Skip the rule and continue. |
| Read files inside the regex loop | Read once into `code`, then scan the in-memory string. |

## Ground truth

[artifacts/rules/](../artifacts/rules/) shows the YAML the engine consumes. [artifacts/rules-registry.yaml](../artifacts/rules-registry.yaml) is the index. Tests should load real rules from here.