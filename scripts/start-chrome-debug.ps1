# Launch a dedicated, logged-in Chrome for the GPT Pro bridge (Windows).
#
# FIRST RUN: a fresh Chrome window opens -> log into chatgpt.com and make sure
# your account has Pro and the Pro model is selected. The profile is stored in
# %USERPROFILE%\chrome-pro-bridge and persists, so later runs stay logged in.
# Keep this window open while debating (you can minimize it).
#
# This uses a SEPARATE profile on purpose, so it never fights your everyday
# Chrome over the same user-data-dir.

$ErrorActionPreference = "Stop"
$port = 9222
$profileDir = "$env:USERPROFILE\chrome-pro-bridge"

$chrome = "$env:ProgramFiles\Google\Chrome\Application\chrome.exe"
if (-not (Test-Path $chrome)) {
    $chrome = "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe"
}
if (-not (Test-Path $chrome)) {
    throw "Chrome not found. Edit `$chrome at the top of this script."
}

Write-Host "Starting bridge Chrome on CDP port $port (profile: $profileDir)"
& $chrome `
    --remote-debugging-port=$port `
    --user-data-dir="$profileDir" `
    --no-first-run --no-default-browser-check `
    "https://chatgpt.com/"
