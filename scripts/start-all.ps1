# One-shot launcher (Windows): bring the bridge up after a reboot.
#
# Starts the debug Chrome (if not already running) and then the MCP server.
# NOTE: the `claude mcp add` registration is one-time — you do NOT redo it here.
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$repo = Split-Path -Parent $here
$cdpPort = if ($env:PRO_BRIDGE_CDP_PORT) { $env:PRO_BRIDGE_CDP_PORT } else { 9222 }

# 1. Bridge Chrome — only if nothing is already listening on the CDP port.
$inUse = (Test-NetConnection -ComputerName localhost -Port $cdpPort `
            -InformationLevel Quiet -WarningAction SilentlyContinue)
if (-not $inUse) {
    Write-Host "Launching bridge Chrome on CDP port $cdpPort ..."
    Start-Process powershell -ArgumentList `
        "-ExecutionPolicy","Bypass","-File","$here\start-chrome-debug.ps1"
    Start-Sleep -Seconds 3
} else {
    Write-Host "Bridge Chrome already running on port $cdpPort."
}

# 2. MCP server (foreground — Ctrl+C to stop).
Set-Location $repo
Write-Host "Starting pro-bridge MCP server ..."
python -m pro_bridge.server
