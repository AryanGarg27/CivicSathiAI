param(
    [string]$RepoName = "civicsathi-ai"
)
$ErrorActionPreference = "Stop"

Write-Host "== CivicSathi AI: GitHub one-shot publisher ==" -ForegroundColor Cyan

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw "Git was not found. Install Git for Windows, then reopen PowerShell: https://git-scm.com/download/win"
}
if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    throw "GitHub CLI was not found. Install it, then reopen PowerShell: https://cli.github.com/"
}

$auth = gh auth status 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "You need to sign in to GitHub once. Starting GitHub CLI login..." -ForegroundColor Yellow
    gh auth login
    if ($LASTEXITCODE -ne 0) { throw "GitHub authentication did not complete." }
}

if (-not (Test-Path ".git")) {
    git init
    if ($LASTEXITCODE -ne 0) { throw "git init failed" }
}

# Configure a local commit identity if one is not already set.
$gitUser = git config user.name
$gitEmail = git config user.email
if (-not $gitUser -or -not $gitEmail) {
    $ghUser = gh api user --jq .login
    $ghId = gh api user --jq .id
    if (-not $ghUser -or -not $ghId) { throw "Could not read GitHub account identity. Run gh auth login and retry." }
    if (-not $gitUser) { git config user.name $ghUser }
    if (-not $gitEmail) { git config user.email "$ghId+$ghUser@users.noreply.github.com" }
}

# Set a consistent initial branch. Existing repositories are not overwritten.
git branch -M main
if ($LASTEXITCODE -ne 0) { throw "Could not set main branch" }

git add .
if ($LASTEXITCODE -ne 0) { throw "git add failed" }

$cached = git diff --cached --quiet
if ($LASTEXITCODE -eq 1) {
    git commit -m "Initial CivicSathi AI prototype"
    if ($LASTEXITCODE -ne 0) { throw "git commit failed. Configure git user.name and user.email, then rerun." }
} elseif ($LASTEXITCODE -gt 1) {
    throw "Could not inspect Git staging area"
} else {
    Write-Host "No staged changes to commit; continuing." -ForegroundColor Yellow
}

# If origin exists, do not change it silently.
$origin = git remote get-url origin 2>$null
if ($LASTEXITCODE -eq 0 -and $origin) {
    Write-Host "An origin remote already exists: $origin" -ForegroundColor Yellow
    Write-Host "Attempting to push the current main branch to that remote."
    git push -u origin main
    if ($LASTEXITCODE -ne 0) { throw "Push failed. Inspect the existing remote before retrying." }
    Write-Host "Push complete: $origin" -ForegroundColor Green
    exit 0
}

Write-Host "Creating a new PUBLIC repository: $RepoName" -ForegroundColor Cyan
gh repo create $RepoName --public --source . --remote origin --push
if ($LASTEXITCODE -ne 0) {
    throw "Repository creation/push failed. The repo may already exist. Check with: gh repo view $RepoName"
}
$repoUrl = gh repo view $RepoName --json url --jq .url
Write-Host "SUCCESS: $repoUrl" -ForegroundColor Green
Write-Host "Next: review the public README and run: python -m pytest" -ForegroundColor Cyan
