[CmdletBinding()]
param(
    [Parameter(Mandatory = $false)]
    [string]$RepoRoot = (Split-Path -Parent $PSScriptRoot),

    [Parameter(Mandatory = $false)]
    [string]$CommitMessage,

    [Parameter(Mandatory = $false)]
    [switch]$DryRun,

    [Parameter(Mandatory = $false)]
    [switch]$NonInteractive
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Invoke-Git {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Arguments,
        [switch]$Capture,
        [switch]$AllowFailure
    )

    if ($Capture) {
        $output = @(& git -c core.safecrlf=false -c core.quotePath=false -C $script:ResolvedRepoRoot @Arguments 2>&1)
        $exitCode = $LASTEXITCODE
        if (-not $AllowFailure -and $exitCode -ne 0) {
            throw "git $($Arguments -join ' ') failed: $($output -join [Environment]::NewLine)"
        }
        return [pscustomobject]@{ ExitCode = $exitCode; Output = $output }
    }

    & git -c core.safecrlf=false -c core.quotePath=false -C $script:ResolvedRepoRoot @Arguments
    $exitCode = $LASTEXITCODE
    if (-not $AllowFailure -and $exitCode -ne 0) {
        throw "git $($Arguments -join ' ') failed with exit code $exitCode"
    }
    return $exitCode
}

function Test-ExcludedPath {
    param([string]$Path, [object[]]$Patterns)
    foreach ($pattern in $Patterns) {
        if ($Path -like [string]$pattern) { return $true }
    }
    return $false
}

function Test-SensitivePath {
    param([string]$Path)

    $normalized = $Path.Replace('\', '/')
    $leaf = [IO.Path]::GetFileName($normalized)
    if ($leaf -match '^\.env\.(example|sample|template)$') { return $false }
    if ($leaf -in @('.server.known_hosts', 'known_hosts')) { return $false }

    return $normalized -match '(?i)(^|/)(\.env($|\.)|\.server\.local\.env$|credentials?($|\.)|secrets?($|\.)|id_(rsa|ed25519)$|[^/]+\.(pem|key|p12|pfx|kdbx|tfstate|dump|sql|sql\.gz|sqlite|sqlite3|db)$)'
}

function Assert-NoHighConfidenceSecret {
    param([string[]]$CandidatePaths)

    $patterns = @(
        '-----BEGIN (RSA |OPENSSH |EC |DSA |PGP )?PRIVATE KEY-----',
        '(?i)github_pat_[A-Za-z0-9_]{40,}',
        '(?i)gh[pousr]_[A-Za-z0-9]{30,}',
        'AKIA[0-9A-Z]{16}',
        '(?<![A-Za-z0-9_-])[0-9]{8,10}:[A-Za-z0-9_-]{35}(?![A-Za-z0-9_-])'
    )

    $diffResult = Invoke-Git -Arguments (@('diff', '--no-ext-diff', '--unified=0', 'HEAD', '--') + $CandidatePaths) -Capture
    $text = $diffResult.Output -join "`n"

    $untracked = @((Invoke-Git -Arguments @('ls-files', '--others', '--exclude-standard') -Capture).Output)
    foreach ($path in $CandidatePaths) {
        if ($untracked -contains $path) {
            $fullPath = Join-Path $script:ResolvedRepoRoot $path
            if ((Test-Path -LiteralPath $fullPath -PathType Leaf) -and (Get-Item -LiteralPath $fullPath).Length -le 1MB) {
                try { $text += "`n" + (Get-Content -LiteralPath $fullPath -Raw -ErrorAction Stop) } catch { }
            }
        }
    }

    foreach ($pattern in $patterns) {
        if ($text -match $pattern) {
            throw "A high-confidence secret pattern was found. Nothing was committed or pushed. Pattern: $pattern"
        }
    }
}

function Get-CandidatePaths {
    param([object[]]$ExcludePatterns)

    $tracked = @((Invoke-Git -Arguments @('diff', '--name-only', '--diff-filter=ACDMRTUXB', 'HEAD', '--') -Capture).Output)
    $untracked = @((Invoke-Git -Arguments @('ls-files', '--others', '--exclude-standard') -Capture).Output)
    $all = @($tracked + $untracked | Where-Object { $_ } | Sort-Object -Unique)
    $selected = [Collections.Generic.List[string]]::new()
    $skipped = [Collections.Generic.List[string]]::new()

    foreach ($path in $all) {
        if (Test-ExcludedPath -Path $path -Patterns $ExcludePatterns) {
            $skipped.Add($path)
            continue
        }
        if (Test-SensitivePath -Path $path) {
            throw "Sensitive path is part of the pending changes: $path"
        }
        $selected.Add($path)
    }

    return [pscustomobject]@{ Selected = @($selected); Skipped = @($skipped) }
}

$script:ResolvedRepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
$configPath = Join-Path $script:ResolvedRepoRoot '.deployment\push-to-production.json'
if (-not (Test-Path -LiteralPath $configPath -PathType Leaf)) {
    throw "Missing release configuration: $configPath"
}

$config = Get-Content -LiteralPath $configPath -Raw | ConvertFrom-Json
$requiredKeys = @('productionBranch', 'remote', 'repository', 'tests')
foreach ($key in $requiredKeys) {
    if (-not $config.PSObject.Properties.Name.Contains($key)) { throw "Missing config key: $key" }
}

$inside = Invoke-Git -Arguments @('rev-parse', '--is-inside-work-tree') -Capture
if (($inside.Output -join '').Trim() -ne 'true') { throw 'RepoRoot is not a Git working tree.' }

$stagedCheck = Invoke-Git -Arguments @('diff', '--cached', '--quiet') -AllowFailure
if ($stagedCheck -ne 0) {
    throw 'The Git index already contains staged changes. Commit or unstage them before using the release button.'
}

$conflicts = @((Invoke-Git -Arguments @('diff', '--name-only', '--diff-filter=U') -Capture).Output)
if ($conflicts.Count -gt 0) { throw "Merge conflicts exist: $($conflicts -join ', ')" }

$branch = ((Invoke-Git -Arguments @('branch', '--show-current') -Capture).Output -join '').Trim()
if ($branch -ne [string]$config.productionBranch) {
    throw "Current branch '$branch' is not the production branch '$($config.productionBranch)'."
}

$remoteUrl = ((Invoke-Git -Arguments @('config', '--get', "remote.$($config.remote).url") -Capture).Output -join '').Trim()
$expectedSuffix = ([string]$config.repository).Trim('/') + '.git'
if ($remoteUrl -notmatch '(?i)github\.com[:/]' -or -not $remoteUrl.TrimEnd('/').EndsWith($expectedSuffix, [StringComparison]::OrdinalIgnoreCase)) {
    throw "Remote '$($config.remote)' does not point to the approved GitHub repository '$($config.repository)'."
}

Write-Host "`n[1/6] Fetching approved production remote..." -ForegroundColor Cyan
Invoke-Git -Arguments @('fetch', [string]$config.remote, [string]$config.productionBranch, '--quiet') | Out-Null
$remoteRef = "$($config.remote)/$($config.productionBranch)"
$remoteExists = Invoke-Git -Arguments @('rev-parse', '--verify', '--quiet', $remoteRef) -AllowFailure
if ($remoteExists -eq 0) {
    $isBehind = Invoke-Git -Arguments @('merge-base', '--is-ancestor', 'HEAD', $remoteRef) -AllowFailure
    $remoteIsAncestor = Invoke-Git -Arguments @('merge-base', '--is-ancestor', $remoteRef, 'HEAD') -AllowFailure
    if ($isBehind -eq 0 -and $remoteIsAncestor -ne 0) {
        throw "Local branch is behind $remoteRef. Pull/rebase intentionally before releasing."
    }
    if ($isBehind -ne 0 -and $remoteIsAncestor -ne 0) {
        throw "Local and $remoteRef have diverged. Automatic merge and force-push are forbidden."
    }
}

$excludePatterns = @($config.excludePaths)
$candidates = Get-CandidatePaths -ExcludePatterns $excludePatterns
if ($candidates.Skipped.Count -gt 0) {
    Write-Host "Excluded local-only paths:" -ForegroundColor DarkYellow
    $candidates.Skipped | ForEach-Object { Write-Host "  - $_" }
}

Write-Host "`n[2/6] Checking paths and secrets..." -ForegroundColor Cyan
if ($candidates.Selected.Count -gt 0) {
    Assert-NoHighConfidenceSecret -CandidatePaths $candidates.Selected
    Write-Host "Files selected for the release commit:" -ForegroundColor Green
    $candidates.Selected | ForEach-Object { Write-Host "  - $_" }
} else {
    Write-Host 'No uncommitted source changes were selected.'
}

Write-Host "`n[3/6] Running project quality gates..." -ForegroundColor Cyan
foreach ($test in @($config.tests)) {
    $name = [string]$test.name
    $workingDirectory = Join-Path $script:ResolvedRepoRoot ([string]$test.workingDirectory)
    if (-not (Test-Path -LiteralPath $workingDirectory -PathType Container)) {
        throw "Test working directory does not exist: $workingDirectory"
    }
    Write-Host "  -> $name" -ForegroundColor Yellow
    Push-Location $workingDirectory
    try {
        & cmd.exe /d /s /c ([string]$test.command)
        if ($LASTEXITCODE -ne 0) { throw "Quality gate failed: $name" }
    } finally {
        Pop-Location
    }
}

Write-Host "`n[4/6] Rechecking changes after tests..." -ForegroundColor Cyan
$candidates = Get-CandidatePaths -ExcludePatterns $excludePatterns
if ($candidates.Selected.Count -gt 0) { Assert-NoHighConfidenceSecret -CandidatePaths $candidates.Selected }

if ($DryRun) {
    Write-Host "`nDRY RUN PASSED. Nothing was staged, committed, or pushed." -ForegroundColor Green
    exit 0
}

if (-not $CommitMessage) {
    $defaultMessage = 'release: ' + (Get-Date -Format 'yyyy-MM-dd HH:mm')
    $entered = Read-Host "Commit message (Enter = '$defaultMessage')"
    $CommitMessage = if ([string]::IsNullOrWhiteSpace($entered)) { $defaultMessage } else { $entered.Trim() }
}
if ([string]::IsNullOrWhiteSpace($CommitMessage)) { throw 'Commit message cannot be empty.' }

if (-not $NonInteractive) {
    $confirmation = Read-Host "Type PUSH to commit and push to $($config.repository):$($config.productionBranch)"
    if ($confirmation -cne 'PUSH') { throw 'Release cancelled. Nothing was staged, committed, or pushed.' }
}

$stagedByScript = $false
try {
    Write-Host "`n[5/6] Creating the release commit..." -ForegroundColor Cyan
    if ($candidates.Selected.Count -gt 0) {
        Invoke-Git -Arguments (@('add', '--') + $candidates.Selected) | Out-Null
        $stagedByScript = $true
        Assert-NoHighConfidenceSecret -CandidatePaths $candidates.Selected
        Invoke-Git -Arguments @('diff', '--cached', '--check') | Out-Null
        Invoke-Git -Arguments @('commit', '-m', $CommitMessage) | Out-Null
        $stagedByScript = $false
    } else {
        Write-Host 'No new commit was required; existing local commits will be pushed.'
    }

    Write-Host "`n[6/6] Pushing without force..." -ForegroundColor Cyan
    Invoke-Git -Arguments @('push', [string]$config.remote, "HEAD:refs/heads/$($config.productionBranch)") | Out-Null
} catch {
    if ($stagedByScript -and $candidates.Selected.Count -gt 0) {
        & git -C $script:ResolvedRepoRoot restore --staged -- $candidates.Selected 2>$null
    }
    throw
}

$sha = ((Invoke-Git -Arguments @('rev-parse', 'HEAD') -Capture).Output -join '').Trim()
Write-Host "`nPUSH SUCCEEDED" -ForegroundColor Green
Write-Host "Repository: $($config.repository)"
Write-Host "Branch:     $($config.productionBranch)"
Write-Host "Commit:     $sha"
Write-Host 'GitHub checks and the deployment gate now control production promotion.'
