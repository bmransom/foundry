#!/usr/bin/env bash
# Progressive-disclosure lint: every file under a skill's references/ must be
# transitively reachable from its SKILL.md (SKILL.md -> ref -> ref ...). An
# orphaned reference never loads into context — dead weight the agent is never
# told to read. Resolves a `references/...` token as skill-root-relative and any
# other relative markdown link relative to the linking file's directory, so a
# two-level chain (SKILL.md -> registry -> playbook) still passes.
# Usage: check-skill-references.sh [skills-dir]   (defaults to foundry's skills)
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILLS_DIR="${1:-$REPO/plugins/foundry/skills}"

python3 - "$SKILLS_DIR" <<'PY'
import os, re, sys

skills_dir = sys.argv[1]
ref_token = re.compile(r'references/[A-Za-z0-9._][A-Za-z0-9._/-]*')
md_link = re.compile(r'\]\(([^)]+)\)')


def candidates(text):
    """(kind, raw) pairs: skill-root `references/...` tokens and relative md links."""
    out = set()
    for token in ref_token.findall(text):
        out.add(('root', token.rstrip('.')))
    for target in md_link.findall(text):
        target = target.split('#', 1)[0].strip()
        if not target or target.startswith(('http://', 'https://', 'mailto:')):
            continue
        out.add(('rel', target))
    return out


def reachable_refs(skill_dir, ref_files):
    """Files under references/ reached by BFS from SKILL.md."""
    reached = set()
    seen = {'SKILL.md'}
    frontier = ['SKILL.md']
    while frontier:
        cur = frontier.pop()
        cur_abs = os.path.join(skill_dir, cur)
        if not os.path.isfile(cur_abs):
            continue
        with open(cur_abs, encoding='utf-8', errors='replace') as handle:
            text = handle.read()
        cur_dir = os.path.dirname(cur)
        for kind, raw in candidates(text):
            rel = os.path.normpath(raw if kind == 'root' else os.path.join(cur_dir, raw))
            if rel in ref_files and rel not in reached:
                reached.add(rel)
            if rel not in seen and os.path.isfile(os.path.join(skill_dir, rel)):
                seen.add(rel)
                frontier.append(rel)
    return reached


violations = []
for skill in sorted(os.listdir(skills_dir)):
    skill_dir = os.path.join(skills_dir, skill)
    refs_dir = os.path.join(skill_dir, 'references')
    if not os.path.isdir(refs_dir) or not os.path.isfile(os.path.join(skill_dir, 'SKILL.md')):
        continue
    ref_files = {
        os.path.normpath(os.path.relpath(os.path.join(root, name), skill_dir))
        for root, _, names in os.walk(refs_dir)
        for name in names
    }
    for orphan in sorted(ref_files - reachable_refs(skill_dir, ref_files)):
        violations.append(f"skill-references: ORPHAN {skill}/{orphan} (unreachable from SKILL.md)")

if violations:
    print('\n'.join(violations))
    sys.exit(1)
print("skill-references: PASS")
PY
