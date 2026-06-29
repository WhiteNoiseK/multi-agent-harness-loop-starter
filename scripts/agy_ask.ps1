<#
  agy_ask.ps1 -- headless Antigravity (agy) ask, Windows-safe. (multi-agent-harness-loop-starter)

  WHY THIS WRAPPER EXISTS
    `agy -p "<prompt>"` authenticates and the model DOES generate a reply, but on Windows agy's transcript
    writer builds a bogus POSIX path (/Users/<user>/.gemini/...) and FAILS to persist the reply when the
    current working directory is on a DIFFERENT DRIVE than HOME (e.g. a project on D:/I: while HOME is on C:).
    Its stdout is also empty in many headless contexts. Net effect: the reply is generated but lost -> it
    looks like "agy never responds". This is the #1 reason headless agy "doesn't work" on Windows.

  THE FIX (all of these together)
    1) HOME set (= USERPROFILE),
    2) cwd forced onto the SAME DRIVE as HOME (a temp dir under USERPROFILE),
    3) a clean EOF on stdin ($null | ...) so print mode COMPLETES (an OPEN stdin that never closes hangs;
       a clean EOF does NOT truncate -- the "EOF truncates" belief was a misdiagnosis of the cross-drive bug),
    4) the whole prompt passed as ONE argv via the call operator (splitting it loses everything after token 1),
    5) an explicit --model (or a default model configured in agy's settings.json) so it never stalls on a picker.
    Then read the reply from the newest transcript_full.jsonl (last PLANNER_RESPONSE / source=MODEL / .content).

  POSIX NOTE (macOS / Linux): there are no drive letters, so the cross-drive fault does not occur -- there the
  plain `agy -p` + transcript capture works. This wrapper is the Windows-safe path.

  USAGE (PowerShell)
    # capture only (agy returns text, the orchestrator integrates it):
    & "$PSScriptRoot\agy_ask.ps1" -PromptFile "$env:TEMP\agy_prompt.txt"
    # let agy write files OUTSIDE its cwd (e.g. docs/** in a project on another drive): grant that dir:
    & "$PSScriptRoot\agy_ask.ps1" -PromptFile <file> -AddDir "<project-root>" -Model 'Gemini 3.1 Pro (High)' -TimeoutSec 180

  -AddDir adds a trusted workspace dir to agy's session (maps to `agy --add-dir`); that dir must also be under
  agy's settings.json `trustedWorkspaces` or `toolPermission = "always-proceed"`. For WRITE tasks the printed
  reply is agy's CLAIM -- the caller must verify the actual files on disk.

  OUTPUT: the reply between '=== AGY REPLY START ===' / '=== AGY REPLY END ===',
          or a single 'AGY_UNAVAILABLE: <reason>' line so the caller can fall back to Claude-only.
#>
param(
  [Parameter(Mandatory = $true)][string]$PromptFile,
  [string]$Model = '',                  # empty = use the default model configured in agy's settings.json
  [int]$TimeoutSec = 120,
  [string]$AddDir = ''                  # optional: a dir outside the cwd that agy may read/write (e.g. project root)
)
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
if (-not (Test-Path $PromptFile)) { Write-Output "AGY_UNAVAILABLE: prompt file not found: $PromptFile"; return }
if (-not (Get-Command agy -ErrorAction SilentlyContinue)) { Write-Output 'AGY_UNAVAILABLE: agy not on PATH (not installed)'; return }

$env:HOME = $env:USERPROFILE                                   # agy reads HOME; keep it = USERPROFILE (same drive as brain)
$brain = Join-Path $env:USERPROFILE '.gemini\antigravity-cli\brain'
if (-not (Test-Path $brain)) { Write-Output 'AGY_UNAVAILABLE: brain dir missing (agy never run / not logged in)'; return }

# Workspace MUST be on the same drive as HOME (the cross-drive transcript bug). USERPROFILE\...\Temp guarantees it.
$ws = Join-Path $env:USERPROFILE 'AppData\Local\Temp\agy_ws'
if (-not (Test-Path $ws)) { New-Item -ItemType Directory -Path $ws -Force | Out-Null }

$prompt = (Get-Content -Raw -Encoding utf8 $PromptFile) -replace '"', ''   # strip quotes (PS native-arg mangling)
$base = @{}; Get-ChildItem $brain -Directory | ForEach-Object { $base[$_.Name] = $true }

$agyArgs = @('-p', $prompt, '--dangerously-skip-permissions', '--print-timeout', ('{0}s' -f $TimeoutSec))
if ($Model)  { $agyArgs += @('--model', $Model) }
if ($AddDir) { $agyArgs += @('--add-dir', $AddDir) }

Push-Location $ws
try { $null | & agy @agyArgs | Out-Null }
catch { Pop-Location; Write-Output "AGY_UNAVAILABLE: agy invocation error: $($_.Exception.Message)"; return }
Pop-Location

$new = Get-ChildItem $brain -Directory | Where-Object { -not $base.ContainsKey($_.Name) } | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $new) { Write-Output 'AGY_UNAVAILABLE: no new transcript produced'; return }
$f = Join-Path $new.FullName '.system_generated\logs\transcript_full.jsonl'
if (-not (Test-Path $f)) { Write-Output "AGY_UNAVAILABLE: transcript_full missing in $($new.Name)"; return }

$m = $null
foreach ($line in Get-Content -Path $f -Encoding utf8) {
  if ([string]::IsNullOrWhiteSpace($line)) { continue }
  try { $o = $line | ConvertFrom-Json } catch { continue }
  if ($o.type -eq 'PLANNER_RESPONSE' -and $o.source -eq 'MODEL' -and $o.content) { $m = $o.content }
}
if ($m) {
  Write-Output '=== AGY REPLY START ==='
  Write-Output $m
  Write-Output '=== AGY REPLY END ==='
}
else { Write-Output "AGY_UNAVAILABLE: no MODEL reply line in transcript $($new.Name)" }
