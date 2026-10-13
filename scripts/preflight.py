#!/usr/bin/env python3
"""Read-only, conservative Git publishing preflight; prints file names, never secret values."""
from pathlib import Path
import subprocess
import sys
import re

root = Path(__file__).resolve().parents[1]
if not (root / 'backend').is_dir() or not (root / 'frontend').is_dir():
    sys.exit('[STOP] Run this script from the HEXTA project after installation')

patterns = {
    'possible_private_key': re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH |ENCRYPTED )?PRIVATE KEY-----'),
    'possible_jwt': re.compile(r'\beyJ[A-Za-z0-9_=-]{15,}\.eyJ[A-Za-z0-9_=-]{15,}\.'),
    'potential_password_assignment': re.compile(r'(?i)\b(?:BANKKEY_DB_PASSWORD|BANKKEY_USER_PIN|BANKKEY_JWT_SECRET)\s*=\s*["\']?[^\s"\']+'),
}
ignore_dirs = {'.git', '.venv', 'node_modules', 'dist', '__pycache__', '.pytest_cache', '.bankkey-backups', '.mypy_cache'}
allowed_suffixes = {'.py', '.ts', '.tsx', '.js', '.json', '.toml', '.yaml', '.yml', '.md', '.env', '.txt', '.sh', '.sql', '.ini'}
issues = []
for path in root.rglob('*'):
    if not path.is_file() or any(p in ignore_dirs for p in path.relative_to(root).parts):
        continue
    rel = path.relative_to(root)
    if path.name in {'.env', '.env.local', '.env.production', '.env.development'} or path.name.endswith(('.pem', '.key', '.p12', '.pfx')):
        issues.append(('sensitive_filename', str(rel)))
    if path.suffix.lower() not in allowed_suffixes or path.stat().st_size > 2_000_000:
        continue
    try:
        content = path.read_text('utf-8')
    except (UnicodeError, OSError):
        continue
    for label, pattern in patterns.items():
        if pattern.search(content):
            issues.append((label, str(rel)))

print('=== BANKKEY HSM | PUBLISHING PREFLIGHT ===')
try:
    result = subprocess.run(['git', '-C', str(root), 'status', '--short'],
                            capture_output=True, text=True, timeout=5)
    if result.returncode:
        print('[NOTE] No Git repository detected yet')
    else:
        print('[OK] Git repository detected')
except (OSError, subprocess.TimeoutExpired):
    print('[NOTE] Git not available')
if issues:
    print('[STOP] Review these files before pushing (no secret contents displayed):')
    for label, filename in sorted(set(issues)):
        print(f'  {label}: {filename}')
    sys.exit(1)
print('[OK] No matches found by the limited local scan')
print('[NOTE] This is not proof that the repository contains no secrets.')
