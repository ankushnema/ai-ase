# Catalog — The Rules

The canonical rule catalog. Loaded by the scanner, retrieved by RAG, enforced by the PreToolUse hook.

**Status legend.** `BLOCK` = PreToolUse refuses the action. `WARN` = action proceeds but is flagged in the audit log. `STRUCTURAL_CHECK` = a `pattern: STRUCTURAL_CHECK` placeholder on a WARN rule — the scanner skips it because file-level analysis is not yet implemented.

**Total:** 71 unique rules — 21 BLOCK, 50 WARN (of which 8 carry `pattern: STRUCTURAL_CHECK` and are not regex-enforced in v1.3). Authoritative source: [artifacts/rules-registry.yaml](../artifacts/rules-registry.yaml). One ID (`VR-43`) appears twice in the registry as an intentional cross-reference between the `code-quality/logging` and `sre-reliability/observability` rule files; it counts once.

---

## Index by ID

| ID | Name | Action | Category |
|----|------|--------|----------|
| VR-01 | Hardcoded Password | BLOCK | Security |
| VR-02 | Hardcoded API Key | BLOCK | Security |
| VR-03 | AWS Access Key | BLOCK | Security |
| VR-04 | Private Key | BLOCK | Security |
| VR-05 | Connection String with Creds | BLOCK | Security |
| VR-06 | Generic Token/Secret | BLOCK | Security |
| VR-07 | SQL Injection (concat) | BLOCK | Security |
| VR-08 | SQL Injection (f-string) | BLOCK | Security |
| VR-09 | Path Traversal | BLOCK | Security |
| VR-10 | Float for Money | BLOCK | Type Safety |
| VR-10b | Double for Currency | BLOCK | Type Safety |
| VR-11 | Field Injection | WARN | Code Quality |
| VR-12 | Generic Exception Catch | WARN | Code Quality |
| VR-13 | Thread.sleep() | WARN | Performance |
| VR-14 | new Thread() | WARN | Performance |
| VR-15 | Unclosed Resource | WARN | Code Quality |
| VR-16 | String Concat in Loop | WARN | Performance |
| VR-17 | System.out | WARN | Logging |
| VR-18 | Context-Free Logging | WARN | Logging |
| VR-19 | Sensitive Data in Logs | WARN | Logging |
| VR-20 | TLS Below 1.2 | WARN | Security |
| VR-21 | Dockerfile Without USER | STRUCTURAL | Container |
| VR-22 | Nested For Loops | WARN | Performance |
| VR-23 | Bare except (Python) | WARN | Code Quality |
| VR-24 | print() in Python | WARN | Logging |
| VR-25 | console.log | WARN | Logging |
| VR-29 | Hardcoded Service URL | WARN | Config |
| VR-30 | Direct Thread Creation | WARN | Performance |
| VR-31 | Raw JDBC Connection | WARN | Performance |
| VR-32 | Unbounded Queue | WARN | Performance |
| VR-33 | Runtime.exec() | WARN | Code Quality |
| VR-34 | os.system() | WARN | Code Quality |
| VR-35 | Missing HEALTHCHECK | STRUCTURAL | Container |
| VR-36 | Swallowed Exception | WARN | Code Quality |
| VR-37 | Hardcoded Timeout | WARN | Config |
| VR-38 | Unbounded Retry | WARN | Resilience |
| VR-39 | Endpoint Without Metrics | WARN | Observability |
| VR-40 | Sync HTTP in Loop | WARN | Performance |
| VR-41 | HTTP Without Resilience | WARN | Resilience |
| VR-42 | Missing Spring Actuator | STRUCTURAL | Observability |
| VR-43 | String Concat in Logger | WARN | Logging |
| VR-44 | Mutable Shared State | WARN | Code Quality |
| VR-45 | Missing Correlation ID | STRUCTURAL | Observability |
| VR-46 | Dockerfile :latest | WARN | Container |
| VR-48 | Unpinned GH Action | WARN | DevOps |
| VR-50 | Privileged Container | WARN | Container |
| VR-51 | K8s Missing Resource Limits | STRUCTURAL | Container |
| VR-52 | Debug Mode in Config | WARN | Config |
| VR-54 | Weak Crypto | WARN | Security |
| VR-55 | K8s Missing Readiness Probe | STRUCTURAL | Observability |
| VR-58 | Open Security Group (0.0.0.0/0) | WARN | DevOps |
| VR-59 | Artifact :latest | WARN | DevOps |
| VR-60 | Deploy Without Approval | WARN | DevOps |
| VR-61 | No Lockfile Committed | STRUCTURAL | DevOps |
| VR-62 | H2 In-Memory in Non-Test | WARN | Config |
| VR-63 | Deploy Without Monitoring | STRUCTURAL | DevOps |
| VR-64 | Unpinned AI Model | WARN | AI Safety |
| VR-65 | Raw LLM Output Exec | WARN | AI Safety |
| VR-66 | LLM Without Max Tokens | WARN | AI Safety |
| VR-67 | Hardcoded System Prompt | WARN | AI Safety |
| VR-68 | Unrestricted Agent Tools | WARN | AI Safety |

---

## BLOCK rules — Security (9) + Type Safety (2)

These ten rules fail the PreToolUse hook. The agent cannot proceed without remediation.

### VR-01 — Hardcoded Password

- **Pattern (intent):** any literal string assigned to an identifier matching `password|passwd|pwd`
- **Applies to:** all file types
- **Fix:** read from environment variable or secret manager

### VR-02 — Hardcoded API Key

- **Pattern (intent):** identifier matching `api[_-]?key|apikey|access[_-]?token` assigned a string literal of suspicious entropy
- **Applies to:** all
- **Fix:** load from secret manager or env

### VR-03 — AWS Access Key

- **Pattern:** literal matching `AKIA[0-9A-Z]{16}` (AWS access key format)
- **Applies to:** all
- **Fix:** use IAM roles or AWS SSO; remove from source

### VR-04 — Private Key

- **Pattern:** PEM header (`-----BEGIN .* PRIVATE KEY-----`)
- **Applies to:** all
- **Fix:** store outside repo; reference by path/URI

### VR-05 — Connection String with Credentials

- **Pattern (intent):** URI scheme with `user:password@host` embedded
- **Applies to:** all
- **Fix:** split credentials into env vars; build URI at runtime

### VR-06 — Generic Token / Secret

- **Pattern (intent):** identifier matching `token|secret|bearer` assigned a long literal
- **Applies to:** all
- **Fix:** secret manager

### VR-07 — SQL Injection (concatenation)

- **Pattern:** SQL keyword followed by string concatenation with a variable
- **Applies to:** code files
- **Fix:** use parameterized queries / prepared statements

### VR-08 — SQL Injection (f-string / interpolation)

- **Pattern:** Python f-string or JS template literal embedding a variable inside a SQL keyword block
- **Applies to:** Python, JS/TS
- **Fix:** parameterize with `?` / `$1` placeholders

### VR-09 — Path Traversal

- **Pattern (intent):** filesystem call with a parameter not validated against `..` / absolute paths
- **Applies to:** code files
- **Fix:** validate via allowlist or `os.path.realpath` + boundary check

### VR-10 — Float for Money

- **Pattern:** identifier matching `price|amount|cost|balance|fee` declared as `float|Float|Double|double`
- **Applies to:** code files
- **Fix:** use `BigDecimal` / `Decimal` / integer cents

### VR-10b — Double for Currency

- Same as VR-10, additional keyword set: `currency|monetary|financial`
- **Action:** BLOCK

---

## WARN rules — Security & Cryptography (2)

### VR-20 — TLS Below 1.2

```
Pattern: (?i)(TLSv1\.0|TLSv1\.1|SSLv3|SSLv2|ssl\.PROTOCOL_TLSv1(?!_2))
Files:   ALL
Fix:     Configure TLS 1.2 minimum; prefer TLS 1.3.
```

### VR-54 — Weak Cryptographic Algorithm

```
Pattern: (?i)(MessageDigest\.getInstance\(["']\s*MD5|MessageDigest\.getInstance\(["']\s*SHA-?1["']|hashlib\.(md5|sha1)\(|crypto\.createHash\(["'](../catalogs/md5|sha1))
Files:   CODE
Fix:     SHA-256+ for integrity, bcrypt/argon2 for passwords.
```

---

## WARN rules — Code Quality & Error Handling (10)

### VR-11 — Field Injection (`@Autowired`)
```
Pattern: @Autowired\s+(private|protected|public)?\s*\w
Files:   JAVA
Fix:     Use constructor injection.
```

### VR-12 — Generic Exception Catch (Java)
```
Pattern: catch\s*\(\s*(Exception|Throwable|RuntimeException)\s+\w+\s*\)
Files:   JAVA
Fix:     Catch specific exception types.
```

### VR-23 — Bare `except` (Python)
```
Pattern: except\s*:
Files:   PYTHON
Fix:     Use `except Exception:` or more specific.
```

### VR-36 — Swallowed Exception (Empty Catch)
```
Pattern: catch\s*\([^)]+\)\s*\{\s*\}
Files:   JAVA
Fix:     At minimum log; ideally rethrow or handle.
```

### VR-22 — Nested For Loops (O(n²) risk)
```
Pattern: for\s*\([\s\S]{0,100}for\s*\(
Files:   CODE
Fix:     Use HashSet/Map for lookups; stream operations.
```

### VR-44 — Mutable Shared State
```
Pattern: (?<!final\s)static\s+(?!final\b)\s*\w*\s*(Map|List|Set|Collection|HashMap|ArrayList|HashSet)\s*<
Files:   JAVA
Fix:     `static final` + ConcurrentHashMap/unmodifiableList.
```

### VR-15 — Unclosed Resource
```
Pattern: (?<!try\s*\()new\s+(FileInputStream|FileOutputStream|BufferedReader|BufferedWriter|Socket|ServerSocket|DataInputStream|DataOutputStream)\s*\(
Files:   JAVA
Fix:     Wrap in try-with-resources.
```

### VR-16 — String Concat in Loop
```
Pattern: (for|while)\s*\([\s\S]{0,200}\+=
Files:   JAVA
Fix:     Use StringBuilder.append().
```

### VR-29 — Hardcoded Service URL
```
Pattern: ["']https?://[a-zA-Z0-9]
Files:   CODE
Fix:     Move to config / env vars.
```

### VR-37 — Hardcoded Timeout Value
```
Pattern: (?i)(timeout|sleep|delay|wait)\s*\(\s*\d{4,}
Files:   CODE
Fix:     Extract to named constants or config.
```

---

## WARN rules — Logging & Observability (7)

### VR-17 — `System.out` in Production
```
Pattern: System\.(out|err)\.(print|println)\s*\(
Files:   JAVA
Fix:     Use SLF4J logger.
```

### VR-24 — `print()` in Python Production
```
Pattern: ^\s*print\s*\(
Files:   PYTHON
Fix:     Use `logging` module.
```

### VR-25 — `console.log` in Production
```
Pattern: console\.(log|debug|info|warn|error)\s*\(
Files:   JS
Fix:     Use structured logger (winston/pino).
```

### VR-18 — Context-Free Logging
```
Pattern: log\.(info|debug|warn|error)\s*\(\s*"(Done|done|OK|ok|Error|error|Failed|failed|Success|success|Here|here|Start|End|Starting|Ending)"\s*\)
Files:   JAVA
Fix:     Include operation, entity ID, outcome.
```

### VR-19 — Sensitive Data in Logs
```
Pattern: (?i)log\.\w+\(.*\b(password|ssn|social.?security|credit.?card|cardNumber|cvv|secret)\b
Files:   CODE
Fix:     Mask/redact sensitive fields before logging.
```

### VR-43 — String Concat in Logger
```
Pattern: log\.(info|debug|warn|error|trace)\s*\(\s*"[^"]*"\s*\+
Files:   JAVA
Fix:     Parameterized: log.info("Order {}", orderId).
```

### VR-39 — REST Endpoint Without Metrics
```
Pattern: @(GetMapping|PostMapping|PutMapping|DeleteMapping|RequestMapping)
Files:   JAVA
Fix:     Add @Timed / @Counted (Micrometer).
```

---

## WARN rules — Performance & Threading (7)

### VR-13 — `Thread.sleep()` in Production
```
Pattern: Thread\.sleep\s*\(
Files:   JAVA
Fix:     ScheduledExecutorService or async.
```

### VR-14 / VR-30 — Direct Thread Creation
```
Pattern: new\s+Thread\s*\(
Files:   JAVA
Fix:     ExecutorService or virtual threads (Java 21+).
```

### VR-31 — Raw JDBC Connection
```
Pattern: DriverManager\s*\.\s*getConnection\s*\(
Files:   JAVA
Fix:     DataSource + connection pool (HikariCP).
```

### VR-32 — Unbounded Queue
```
Pattern: new\s+LinkedBlockingQueue\s*\(\s*\)
Files:   JAVA
Fix:     Specify capacity: new LinkedBlockingQueue<>(1000).
```

### VR-33 — `Runtime.exec()`
```
Pattern: Runtime\s*\.\s*(getRuntime\s*\(\s*\)\s*\.\s*)?exec\s*\(
Files:   JAVA
Fix:     ProcessBuilder with timeout and stream handling.
```

### VR-34 — `os.system()` in Python
```
Pattern: os\s*\.\s*system\s*\(
Files:   PYTHON
Fix:     subprocess.run(shell=False, timeout=…).
```

### VR-40 — Synchronous HTTP in Loop
```
Pattern: for\s*\(.*\)\s*\{[^}]*(restTemplate|webClient|HttpClient|httpClient|fetch)
Files:   JAVA
Fix:     Batch API or parallelize with CompletableFuture.
```

---

## WARN rules — Resilience (4)

### VR-38 — Unbounded Retry Loop
```
Pattern: while\s*\(\s*true\s*\).*(?i)(retry|attempt|reconnect)
Files:   CODE
Fix:     Max retries + exponential backoff, or circuit breaker.
```

### VR-41 — Raw HTTP Client Without Resilience
```
Pattern: new\s+RestTemplate\s*\(|RestTemplate\s*\(\)|WebClient\s*\.\s*create\s*\(
Files:   JAVA
Fix:     Wrap with Resilience4j @CircuitBreaker, @Retry, @TimeLimiter.
```

### VR-52 — Debug Mode in Config
```
Pattern: (?i)(debug\s*[:=]\s*true|FLASK_DEBUG\s*[:=]\s*1|DEBUG\s*[:=]\s*["']?true)
Files:   CONFIG
Fix:     debug=false in prod; use environment profiles.
```

### VR-58 — Open Security Group (0.0.0.0/0)
```
Pattern: (?i)(cidr_blocks|CidrIp|source_address_prefix)\s*[:=]\s*.*0\.0\.0\.0/0
Files:   CONFIG
Fix:     Restrict CIDR to specific IP ranges.
```

---

## WARN rules — DevOps & Containers (6 regex, 4 structural)

### VR-46 — Dockerfile `:latest` Tag
```
Pattern: (?i)^\s*FROM\s+\S+:(latest)\b
Files:   DOCKER
Fix:     Pin to version/SHA (FROM node:20.11.1-alpine).
```

### VR-48 — GitHub Actions Unpinned Action
```
Pattern: uses\s*:\s*\S+@(main|master|latest|dev|develop)\b
Files:   CONFIG
Fix:     Pin to SHA or @vN tag.
```

### VR-50 — Privileged Container
```
Pattern: (?i)(privileged\s*:\s*true|allowPrivilegeEscalation\s*:\s*true)
Files:   CONFIG
Fix:     Both false; use specific capabilities.
```

### VR-59 — Artifact Tagged `:latest`
```
Pattern: (?i)(image|FROM)\s*[:=]\s*\S+:latest\b
Files:   CONFIG
Fix:     Pin to version tag or digest.
```

### VR-60 — CI Deploy Without Approval Gate
```
Pattern: (?i)(deploy|release).*production(?!.*approv)
Files:   CONFIG
Fix:     Add manual approval / environment protection.
```

### VR-62 — H2 In-Memory Database in Non-Test
```
Pattern: (?i)(jdbc:h2:mem|sqlite.*:memory:|DATABASES.*sqlite3)
Files:   CONFIG
Fix:     Same DB engine as prod; use Testcontainers.
```

### Structural (4): VR-21, VR-35, VR-51, VR-61

| ID | Check |
|---|---|
| VR-21 | Dockerfile has no `USER` directive |
| VR-35 | Dockerfile missing `HEALTHCHECK` |
| VR-51 | K8s pod spec missing resource limits |
| VR-61 | No lockfile (package-lock.json / yarn.lock / poetry.lock) committed |

---

## WARN rules — AI Engineering (5)

### VR-64 — Unpinned AI Model Reference
```
Pattern: (?i)(model\s*[=:]\s*["'](../catalogs/gpt-4|gpt-3/.5|claude|gemini|llama)["'](?!\s*[-_]))
Files:   CODE
Fix:     Pin to version (e.g., gpt-4-0125-preview).
```

### VR-65 — Raw LLM Output Execution
```
Pattern: (?i)(eval|exec|execute|run)\s*\(.*\b(response|completion|output|result)\b.*\.(text|content|message|choices)
Files:   CODE
Fix:     Validate/sanitize through schema before execution.
```

### VR-66 — LLM Call Without Max Tokens
```
Pattern: (?i)(openai|anthropic|bedrock|vertex).*\.(create|complete|generate|invoke)\s*\((?!.*max.?tokens)
Files:   CODE
Fix:     Set max_tokens explicitly.
```

### VR-67 — Hardcoded System Prompt
```
Pattern: (?i)(system|role)\s*[:=]\s*["']{3,}.*\n.*\n.*\n
Files:   CODE
Fix:     Externalize prompts to versioned template files.
```

### VR-68 — Unrestricted AI Agent Tool Access
```
Pattern: (?i)(tools\s*[:=]\s*["']all["']|allow_all_tools\s*[:=]\s*true|unrestricted.*agent)
Files:   CODE
Fix:     Define explicit tool manifest (least privilege).
```

---

## Structural — Observability (4)

| ID | Check | Logic |
|----|-------|-------|
| VR-42 | Missing Spring Actuator | pom.xml lacks `spring-boot-starter-actuator` |
| VR-45 | Missing Correlation ID | No MDC filter / interceptor in web layer |
| VR-55 | K8s Missing Readiness Probe | Pod spec has no `readinessProbe` |
| VR-63 | Deploy Without Monitoring | Deploy script has no monitoring notification step |

These are documented but not enforced by regex in v1.3. Implementation hook: scanner skips when `pattern: STRUCTURAL_CHECK`. Future: AST-level or file-presence checks.

---

## Rule schema

Every rule is a YAML file under `rules/` with the following fields. See [spec/07-rule-schema.md](../spec/07-rule-schema.md) for the full schema.

```yaml
id: VR-01
name: Hardcoded Password
severity: critical          # critical | high | medium | low
action: BLOCK               # BLOCK | WARN
applies_to: [ALL]           # ALL | JAVA | PYTHON | JS | CODE | CONFIG | DOCKER
groups: [security-critical]
guardrails: [G-SDLC-5, G2.1]
pattern: |
  (?i)(password|passwd|pwd)\s*[=:]\s*["'][^"']+["']
fix: Store passwords in a secret manager. Read at runtime.
rationale: Passwords in source code end up in version control.
```

---

## Adding a rule

1. Copy any existing YAML in `rules/`.
2. Assign next free `VR-NN` id.
3. Write the regex. Test against fixtures in `tests/fixtures/`.
4. Set `action: WARN` first. Promote to `BLOCK` only after running against a sample of real repos and confirming the false-positive rate is acceptable.
5. Add to this catalog under the appropriate category.

See [spec/03-core-engine.md](../spec/03-core-engine.md) for how the scanner consumes the YAML.
