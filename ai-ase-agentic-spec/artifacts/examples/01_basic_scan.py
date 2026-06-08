"""Example: Scan a file for governance violations using AI-ASE programmatically."""

from ai_ase.engine import validate

# Sample code with a hardcoded secret (BLOCK) and a bare except (WARN)
code = '''
import os

DB_PASSWORD = "supersecret123"

def connect():
    try:
        return db.connect(password=DB_PASSWORD)
    except:
        pass
'''

result = validate(code, filename="config.py", profile="feature")

print(f"Scanned with profile: {result.profile}")
print(f"Rules checked: {result.rules_checked}")
print(f"Allowed: {result.allowed}")
print()

for v in result.blocks:
    print(f"[BLOCK] {v.rule_id}: {v.rule_name} (line {v.line})")
    print(f"        Fix: {v.fix_guidance}")

for v in result.warnings:
    print(f"[WARN]  {v.rule_id}: {v.rule_name} (line {v.line})")