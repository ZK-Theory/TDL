#!/bin/bash
# results-no-overwrite: block in-place overwrite/edit of an existing results file.
# Project rule (CLAUDE.md APM_RULES "Output file management"): numerical results
# use date-suffixed filenames and are NEVER overwritten — new date suffix, old
# file preserved as historical record.
# Scope: results/**/*.{json,npy,npz}. Allows new files (e.g. a fresh date suffix)
# and byte-identical rewrites (idempotent reruns). Fails open on any error.

INPUT=$(cat)

printf '%s' "$INPUT" | python -c "
import sys, json, os, re

d = json.load(sys.stdin)
tool = d.get('tool_name', '')
ti = d.get('tool_input', {})
fp = ti.get('file_path', ti.get('path', '')) or ''

def emit(decision, reason=None):
    out = {'hookEventName': 'PreToolUse', 'permissionDecision': decision}
    if reason:
        out['permissionDecisionReason'] = reason
    print(json.dumps({'hookSpecificOutput': out}))
    sys.exit(0)

norm = fp.replace('\\\\', '/')
# Scope: under a results/ directory with a results extension.
if not re.search(r'(^|/)results/.*\.(json|npy|npz)\$', norm):
    emit('allow')

# New file (e.g. a fresh date suffix) — fine.
if not os.path.exists(fp):
    emit('allow')

# Existing file. Edit/MultiEdit mutate in place => overwrite of a results record.
if tool in ('Edit', 'MultiEdit'):
    emit('deny', '%s is an existing results file; results are immutable, '
         'date-suffixed records. Write a new <basename>_<YYYY-MM-DD>.<ext> '
         'instead of editing in place (CLAUDE.md APM_RULES, Output file '
         'management).' % fp)

# Write to an existing results file.
ext = norm.rsplit('.', 1)[-1].lower()

# Binary results (.npy/.npz): the Write tool only emits text content, so a Write
# to an existing binary result is always an overwrite. Deny explicitly rather than
# via a misleading text-mode 'content differs' comparison.
if ext in ('npy', 'npz'):
    emit('deny', '%s is an existing binary results file (.%s) and must not be '
         'overwritten in place. Write a new <basename>_<YYYY-MM-DD>.%s and '
         'preserve the old file (CLAUDE.md APM_RULES, Output file management).'
         % (fp, ext, ext))

# Text results (.json): allow only if byte-identical to existing (idempotent rerun).
content = ti.get('content', None)
if content is not None:
    try:
        with open(fp, 'r', encoding='utf-8') as f:
            if f.read() == content:
                emit('allow')
    except Exception:
        pass
    emit('deny', '%s already exists and the new content differs. Results are '
         'never overwritten - write a new <basename>_<YYYY-MM-DD>.<ext> and '
         'preserve the old file (CLAUDE.md APM_RULES, Output file management).'
         % fp)

emit('allow')
" 2>/dev/null || printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"allow"}}'
