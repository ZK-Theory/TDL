#!/bin/bash
# jcodemunch-guard: block Grep/Glob/Regex when jcodemunch is required for code exploration.
# This hook enforces the repository's code navigation policy.
printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"jcodemunch is required for code exploration. Use jcodemunch MCP tools instead of Grep/Glob/Regex."}}'
exit 0
