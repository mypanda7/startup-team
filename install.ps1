# Install startup-team into the current project folder, then ask the setup question.
# Runs only two commands: `claude plugin marketplace add` (skipped when already added) and
# `claude plugin install startup-team@startup-team --scope local`. Writes nothing else.
# Usage, from the project folder: powershell -ExecutionPolicy Bypass -File install.ps1 [-WhatIf]
param([switch]$WhatIf)

$Marketplace = "mypanda7/startup-team"
$Plugin = "startup-team@startup-team"

function Invoke-Step([string[]]$CommandArgs, [string]$Failure) {
    if ($WhatIf) {
        Write-Output ("[what-if] claude " + ($CommandArgs -join " "))
        return
    }
    & claude @CommandArgs
    if ($LASTEXITCODE -ne 0) {
        # throw, not exit: exit would close a console that ran this through iex.
        throw "install failed: $Failure"
    }
}

if (-not $WhatIf -and -not (Get-Command claude -ErrorAction SilentlyContinue)) {
    throw "install failed: the claude command was not found. Install Claude Code first."
}

# "Already added" means a marketplace NAMED startup-team, whatever its source; never re-add or replace it.
$ours = $null
if (-not $WhatIf) {
    try {
        $ours = (& claude plugin marketplace list --json 2>$null | Out-String | ConvertFrom-Json) |
            Where-Object { $_.name -eq "startup-team" } | Select-Object -First 1
    } catch { $ours = $null }
}
if ($ours) {
    $source = @($ours.repo, $ours.url, $ours.path) | Where-Object { $_ } | Select-Object -First 1
    if ($source -eq $Marketplace) {
        Write-Output "Marketplace startup-team is already added."
    } else {
        if (-not $source) { $source = "another source" }
        Write-Output "Marketplace startup-team is already added from $source; using that source."
    }
} else {
    Invoke-Step @("plugin", "marketplace", "add", $Marketplace) "could not add the marketplace $Marketplace."
}

Invoke-Step @("plugin", "install", $Plugin, "--scope", "local") "could not install $Plugin in this folder."

Write-Output "startup-team installed successfully."
Write-Output "Create the AI Tech Lead session and its six sub sessions (Business Analyst, Designer, Developer, QA Engineer, DevOps, Security) and turn on the companion plugins? 1 = yes, 0 = no."
Write-Output "Claude, if you ran this: ask the owner that question now, with clickable options if you can (in Claude Code: AskUserQuestion) - `"Set up now`" (= 1) and `"Not now`" (= 0) - else as text ending 1 = yes, 0 = no. On 1, on the owner's turn, follow commands/start-team.md from the installed plugin folder (see claude plugin list); in the terminal CLI, say the sessions need the desktop app."
Write-Output "On 0 (Not now), nothing more: the plugin asks again in the next session."
