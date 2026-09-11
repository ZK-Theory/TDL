#!/bin/bash
# admin-bypass-guard: refuse the P-049 ruleset bypass, and ruleset or
# branch-protection writes, from agent sessions.
#
# Why (decided by Stephen, 2026-09-11, PR #278): P-049 gives the repository
# admin role a pull-request bypass so gate-file changes stay possible under
# code-owner review. Every agent here acts through the owner's admin `gh` login,
# so without this hook any agent could take that bypass itself -- merge with
# --admin, merge a PR directly past the queue, or rewrite the ruleset. The owner
# runs those commands in their own terminal, where this hook does not apply.
#
# Scope: Bash and PowerShell tool calls. Denied:
#   * `gh pr merge ... --admin`
#   * direct merges past the queue: a non-GET `gh api` to .../pulls/<n>/merge,
#     or a GraphQL mergePullRequest mutation
#   * non-GET `gh api` calls to rulesets or branch protection, and GraphQL
#     mutations on rulesets or branch-protection rules
# Reads (`gh api repos/.../rulesets`) and ordinary queued merges are allowed.
#
# Fails CLOSED when the check itself errors and the command mentions --admin,
# rulesets, protection, or a merge mutation: a bypass guard that fails open is
# not a guard. Otherwise it fails open with the FAILING OPEN marker that
# _receipt-wrap.sh records.

INPUT=$(cat)

printf '%s' "$INPUT" | python -c '
import json, re, shlex, sys

payload = json.load(sys.stdin)
command = str((payload.get("tool_input") or {}).get("command") or "")

OWNER = (
    "Run it yourself in your own terminal: agent sessions may not use the P-049 bypass "
    "or change repository rules (admin-bypass-guard, decided 2026-09-11)."
)
VALUE_FLAGS = {
    "-X", "--method", "-f", "-F", "--field", "--raw-field", "--input", "-H", "--header",
    "-q", "--jq", "-t", "--template", "--hostname", "--cache", "-p", "--preview",
}
BODY_FLAGS = {"-f", "-F", "--field", "--raw-field", "--input"}


def emit(decision, reason=None):
    out = {"hookEventName": "PreToolUse", "permissionDecision": decision}
    if reason:
        out["permissionDecisionReason"] = reason
    print(json.dumps({"hookSpecificOutput": out}))
    sys.exit(0)


# Judge each command in a chain on its own flags.
for segment in re.split(r"&&|\|\||[;|\n]", command):
    text = segment.strip()
    try:
        tokens = shlex.split(text, posix=True)
    except ValueError:
        tokens = text.split()
    start = next(
        (i for i, token in enumerate(tokens) if re.fullmatch(r"(.*[\\/])?gh(\.exe)?", token)),
        None,
    )
    if start is None:
        continue
    args = tokens[start + 1:]

    if args[:2] == ["pr", "merge"] and any(arg == "--admin" or arg.startswith("--admin=") for arg in args):
        emit("deny", "gh pr merge --admin takes the ruleset bypass. " + OWNER)
    if not args or args[0] != "api":
        continue

    method, writes_body, endpoint = None, False, ""
    index = 1
    while index < len(args):
        token = args[index]
        if token in VALUE_FLAGS:
            value = args[index + 1] if index + 1 < len(args) else ""
            if token in ("-X", "--method"):
                method = value.upper()
            if token in BODY_FLAGS:
                writes_body = True
            index += 2
            continue
        if token.startswith("--method="):
            method = token.split("=", 1)[1].upper()
        elif token.startswith("-X") and len(token) > 2:
            method = token[2:].upper()
        elif token.startswith(("--field=", "--raw-field=", "--input=")):
            writes_body = True
        elif not token.startswith("-") and not endpoint:
            endpoint = token
        index += 1
    if method is None:
        method = "POST" if writes_body else "GET"

    if endpoint == "graphql":
        body = " ".join(args)
        if re.search(r"\bmutation\b", body) and re.search(r"mergePullRequest|Ruleset|BranchProtectionRule", body):
            emit("deny", "This GraphQL mutation merges past the queue or changes repository rules. " + OWNER)
        continue
    if method != "GET" and re.search(r"(^|/)rulesets(/|$)|/protection(/|$)", endpoint):
        emit("deny", method + " " + endpoint + " changes repository rules. " + OWNER)
    if method != "GET" and re.search(r"/pulls/\d+/merge$", endpoint):
        emit("deny", method + " " + endpoint + " merges past the merge queue. " + OWNER)

emit("allow")
' 2>/dev/null || {
  if printf '%s' "$INPUT" | grep -qiE -- '--admin|rulesets|protection|mergePullRequest'; then
    printf 'admin-bypass-guard: hook errored on a command that mentions a bypass or repository rules -- FAILING CLOSED (denied).\n' >&2
    printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"admin-bypass-guard could not evaluate this command and it mentions a bypass or repository rules, so it is refused. Run it yourself in your own terminal."}}'
  else
    printf 'admin-bypass-guard: hook errored or timed out -- FAILING OPEN (command allowed).\n' >&2
    printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"allow"}}'
  fi
}
