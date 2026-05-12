---
description: Session-aware routing and confidence-level workflows for jcodemunch.
alwaysApply: true
---

## Session-Aware Routing

Detailed guidance for confidence-driven code exploration workflows.

### Opening Move Protocol

**For any task, always start with:**
```
plan_turn { 
  "repo": "C:\\Users\\steph\\TDL", 
  "query": "your task description", 
  "model": "claude-sonnet-4-20250514" 
}
```

The `model` parameter narrows the exposed tool list to match your capabilities with zero extra requests.

### Confidence-Level Workflows

**High Confidence (direct execution):**
- Go directly to recommended symbols
- Maximum 2 supplementary reads
- Trust the recommendations and implement immediately

**Medium Confidence (guided exploration):**
- Explore recommended files systematically
- Maximum 5 supplementary reads
- Cross-validate findings before implementation

**Low Confidence (gap reporting):**
- The feature likely doesn't exist
- Report the gap to the user immediately
- Do NOT search further hoping to find it
- Do NOT assume related files implement missing features

### Interpreting Search Results

**Negative Evidence Handling:**
- If `search_symbols` returns `negative_evidence` with `verdict: "no_implementation_found"`:
  - Do NOT re-search with different terms
  - Do NOT assume related files implement the missing feature
  - DO report: "No existing implementation found for X. This would need to be created."
  - DO check `related_existing` files for context, not implementation

**Low Confidence Matches:**
- If `verdict: "low_confidence_matches"`: examine matches critically
- Don't assume they implement the feature you're looking for
- Validate against actual requirements before proceeding

### Token Budget Management

**Budget Warnings:**
- If `_meta` contains `budget_warning`: stop exploring immediately
- Work with information you already have
- Don't attempt additional discovery calls

**Auto-Compaction:**
- If `auto_compacted: true` appears: results were compressed due to turn budget
- This is normal for large results; continue with compressed data

**Session Context:**
- Use `get_session_context` to check what you've already read
- Avoid re-reading the same files unless editing them
- Maintain awareness of exploration history

### After Editing Files

**Index Maintenance:**
- If PostToolUse hooks are installed (Claude Code), files are auto-reindexed
- Otherwise, call `register_edit` with edited file paths
- For bulk edits (5+ files), always use `register_edit` with all paths

### Token Efficiency Guidelines

**Prefer skeleton over full reads:**
- Use `get_skeleton` for understanding code structure
- Reserve `Read` tool only for files you're about to edit
- Use `get_file_outline` before any detailed file inspection

**Batch operations when possible:**
- Use `get_context_bundle` for symbol + imports in one call
- Use array parameters in tools that support batch queries
- Group related discovery operations to minimize round trips

### Model-Driven Tool Tiering

Your jcodemunch-mcp server automatically narrows the exposed tool list based on your model capabilities. The `model` parameter in `plan_turn` enables this optimization.

**Model mapping:**
- Claude Sonnet variants → comprehensive tool access
- Claude Haiku variants → simplified tool subset
- Other models → fallback tool configuration

Always include the correct model identifier to ensure optimal tool exposure.