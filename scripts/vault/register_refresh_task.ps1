# Research context: TDA-Research/04-Methods/Pipeline-Overview.md
# Purpose: Register a Windows Scheduled Task that keeps the QMD vault index
#          (backing the vault-engine MCP) fresh by running refresh_index.py
#          daily. Uses schtasks.exe, which succeeds for the current user
#          without elevation (the Register-ScheduledTask COM API returns
#          access-denied 0x80070005 in a non-elevated shell). Idempotent (/F).
#
# Usage (from any shell):
#   powershell -ExecutionPolicy Bypass -File scripts\vault\register_refresh_task.ps1
# Remove with:
#   schtasks /Delete /TN "VaultEngine-IndexRefresh" /F
#
# Note: the MCP server (mcp_server.py) also self-refreshes the index hourly on
# tool use, so this task only matters for freshness when no session is running.

$ErrorActionPreference = "Stop"

$taskName = "VaultEngine-IndexRefresh"
$repo     = "C:\Users\steph\TDL"
$script   = Join-Path $repo "scripts\vault\refresh_index.py"
$python   = Join-Path $repo ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) { $python = "python" }   # fall back to PATH

# No env injection needed: refresh_index.py defaults XDG_CACHE_HOME to
# ~/.cache (Path.home()), which resolves to C:\Users\steph\.cache for the
# logged-in user — the same index the MCP server uses.
$run = "`"$python`" `"$script`""

schtasks /Create /TN $taskName /TR $run /SC DAILY /ST 04:30 /F | Out-Null
Write-Output "Registered scheduled task '$taskName' (daily 04:30)."
schtasks /Query /TN $taskName /FO LIST | Select-String "TaskName|Status|Next Run Time"
