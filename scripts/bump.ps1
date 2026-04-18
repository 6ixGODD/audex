# ============================================================================
# Version Bump Script (PowerShell)
# ============================================================================
# Description: Bump version across multiple files and git tag
# Usage: .\bump.ps1 <new_version> [-DryRun] [-NoGit] [-NoPush]
# Example: .\scripts\bump.ps1 0.2.0
#          .\scripts\bump.ps1 0.2.0 -DryRun
#          .\scripts\bump.ps1 0.2.0 -NoGit
# ============================================================================

[CmdletBinding()]
param(
    [Parameter(Mandatory=$true, Position=0)]
    [string]$NewVersion,
    
    [Parameter(Mandatory=$false)]
    [switch]$DryRun,
    
    [Parameter(Mandatory=$false)]
    [switch]$NoGit,
    
    [Parameter(Mandatory=$false)]
    [switch]$NoPush,
    
    [Parameter(Mandatory=$false)]
    [switch]$Help
)

# ============================================================================
# Configuration
# ============================================================================

$ErrorActionPreference = "Stop"
$ScriptDir = $PSScriptRoot
$ProjectRoot = Split-Path -Parent $ScriptDir

$VERSION_FILE = Join-Path $ProjectRoot "VERSION"
$PYPROJECT_FILE = Join-Path $ProjectRoot "pyproject.toml"
$PROJECT_NAME = "audex"
$INIT_FILE = Join-Path $ProjectRoot "$PROJECT_NAME\__init__.py"
$CONFIG_EXAMPLE_YML = Join-Path $ProjectRoot ".config.example.yml"
$CONFIG_SYSTEM_LINUX = Join-Path $ProjectRoot ".config.system.linux.yml"
$CONFIG_SYSTEM_WINDOWS = Join-Path $ProjectRoot ".config.system.windows.yml"
$ENV_EXAMPLE_FILE = Join-Path $ProjectRoot ".env.example"

$PYTHON = "uv run python"

# ============================================================================
# Color Functions
# ============================================================================

function Write-ColorOutput {
    param(
        [string]$Message,
        [string]$ForegroundColor = "White"
    )
    Write-Host $Message -ForegroundColor $ForegroundColor
}

function Write-Info {
    param([string]$Message)
    Write-ColorOutput "[INFO] $Message" -ForegroundColor Green
}

function Write-Error {
    param([string]$Message)
    Write-ColorOutput "[ERROR] $Message" -ForegroundColor Red
}

function Write-Warn {
    param([string]$Message)
    Write-ColorOutput "[WARN] $Message" -ForegroundColor Yellow
}

function Write-Step {
    param([string]$Message)
    Write-ColorOutput "[STEP] $Message" -ForegroundColor Cyan
}

function Write-Success {
    param([string]$Message)
    Write-ColorOutput "[SUCCESS] $Message" -ForegroundColor Green
}

# ============================================================================
# Utility Functions
# ============================================================================

function Write-Separator {
    Write-Host "========================================="
}

function Write-Header {
    param([string]$Title)
    Write-Host ""
    Write-Separator
    Write-Host $Title
    Write-Separator
    Write-Host ""
}

function Test-CommandExists {
    param([string]$Command)
    $null -ne (Get-Command $Command -ErrorAction SilentlyContinue)
}

function Request-Confirmation {
    param([string]$Prompt = "Are you sure?")
    $response = Read-Host "$Prompt (y/N)"
    return $response -match '^[yY](es)?$'
}

function Exit-WithError {
    param(
        [string]$Message,
        [int]$ExitCode = 1
    )
    Write-Error $Message
    exit $ExitCode
}

# ============================================================================
# Help Function
# ============================================================================

function Show-Usage {
    @"
Usage: bump.ps1 <new_version> [options]

Arguments:
  new_version           New version number (e.g., 0.2.0)

Options:
  -DryRun              Show what would be changed without making changes
  -NoGit               Skip git operations (commit and tag)
  -NoPush              Skip git push operations
  -Help                Show this help message

Examples:
  .\scripts\bump.ps1 0.2.0
  .\scripts\bump.ps1 0.2.0 -DryRun
  .\scripts\bump.ps1 0.2.0 -NoGit
  .\scripts\bump.ps1 0.2.0 -NoPush
"@
}

if ($Help) {
    Show-Usage
    exit 0
}

# ============================================================================
# Validation Functions
# ============================================================================

function Test-VersionFormat {
    param([string]$Version)
    
    # Check semantic versioning format (X.Y.Z or X.Y.Z-suffix)
    if ($Version -notmatch '^[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9.]+)?$') {
        Exit-WithError "Invalid version format: $Version (expected: X.Y.Z or X.Y.Z-suffix)"
    }
    
    Write-Success "Version format validated: $Version"
}

function Get-CurrentVersion {
    if (Test-Path $VERSION_FILE) {
        return (Get-Content $VERSION_FILE -Raw).Trim()
    }
    return "unknown"
}

# ============================================================================
# Update Functions
# ============================================================================

function Update-VersionFile {
    param([string]$Version)
    
    Write-Step "Updating VERSION file..."
    
    if ($DryRun) {
        Write-Info "[DRY-RUN] Would write '$Version' to $VERSION_FILE"
        return
    }
    
    Set-Content -Path $VERSION_FILE -Value $Version -NoNewline
    Write-Success "✓ Updated: $VERSION_FILE"
}

function Update-PyProject {
    param([string]$Version)
    
    Write-Step "Updating pyproject.toml..."
    
    if (-not (Test-Path $PYPROJECT_FILE)) {
        Write-Warn "File not found: $PYPROJECT_FILE"
        return
    }
    
    if ($DryRun) {
        Write-Info "[DRY-RUN] Would update version in $PYPROJECT_FILE"
        return
    }
    
    # Read file content
    $content = Get-Content $PYPROJECT_FILE -Raw
    
    # Update version in [project] section
    if ($content -match '(?ms)\[project\].*?^version\s*=\s*"[^"]*"') {
        $content = $content -replace '(?m)(?<=\[project\].*?^version\s*=\s*")[^"]*', $Version
        Set-Content -Path $PYPROJECT_FILE -Value $content -NoNewline
        Write-Success "✓ Updated: $PYPROJECT_FILE ([project] section)"
    }
}

function Update-InitPy {
    param([string]$Version)
    
    Write-Step "Updating $PROJECT_NAME/__init__.py..."
    
    if (-not (Test-Path $INIT_FILE)) {
        Write-Warn "File not found: $INIT_FILE"
        return
    }
    
    if ($DryRun) {
        Write-Info "[DRY-RUN] Would update __version__ in $INIT_FILE"
        return
    }
    
    # Read file content
    $content = Get-Content $INIT_FILE -Raw
    
    # Update __version__ variable
    $content = $content -replace '(?m)^__version__\s*=\s*"[^"]*"', "__version__ = `"$Version`""
    Set-Content -Path $INIT_FILE -Value $content -NoNewline
    Write-Success "✓ Updated: $INIT_FILE"
}

function Update-ConfigFiles {
    Write-Step "Updating configuration files..."
    
    if ($DryRun) {
        Write-Info "[DRY-RUN] Would update $CONFIG_EXAMPLE_YML, $CONFIG_SYSTEM_LINUX, $CONFIG_SYSTEM_WINDOWS, $ENV_EXAMPLE_FILE"
        return
    }
    
    try {
        # Update config.example.yml
        "y" | & $PYTHON.Split() -m audex init gencfg -o $CONFIG_EXAMPLE_YML --format yaml 2>&1 | Out-Null
        Write-Success "✓ Updated: $CONFIG_EXAMPLE_YML"
        
        # Update config.system.linux.yml
        "y" | & $PYTHON.Split() -m audex init gencfg -o $CONFIG_SYSTEM_LINUX --format system --platform linux 2>&1 | Out-Null
        Write-Success "✓ Updated: $CONFIG_SYSTEM_LINUX"
        
        # Update config.system.windows.yml
        "y" | & $PYTHON.Split() -m audex init gencfg -o $CONFIG_SYSTEM_WINDOWS --format system --platform windows 2>&1 | Out-Null
        Write-Success "✓ Updated: $CONFIG_SYSTEM_WINDOWS"
        
        # Update .env.example
        "y" | & $PYTHON.Split() -m audex init gencfg -o $ENV_EXAMPLE_FILE --format dotenv 2>&1 | Out-Null
        Write-Success "✓ Updated: $ENV_EXAMPLE_FILE"
    }
    catch {
        Write-Warn "Failed to update some configuration files: $_"
    }
}

# ============================================================================
# Git Functions
# ============================================================================

function New-GitCommit {
    param([string]$Version)
    
    if ($NoGit) {
        Write-Info "Skipping git commit (-NoGit flag)"
        return
    }
    
    if (-not (Test-CommandExists git)) {
        Write-Warn "Git is not installed, skipping git operations"
        return
    }
    
    # Check if we're in a git repository
    try {
        git rev-parse --git-dir 2>&1 | Out-Null
    }
    catch {
        Write-Warn "Not a git repository, skipping git operations"
        return
    }
    
    Write-Step "Creating git commit..."
    
    if ($DryRun) {
        Write-Info "[DRY-RUN] Would commit with message: 'chore: bump version to $Version'"
        return
    }
    
    # Add files
    git add $VERSION_FILE $PYPROJECT_FILE $INIT_FILE 2>&1 | Out-Null
    
    # Create commit
    $diff = git diff --staged --quiet
    if ($LASTEXITCODE -eq 0) {
        Write-Warn "No changes to commit"
    }
    else {
        git commit -m "chore: bump version to $Version" 2>&1 | Out-Null
        Write-Success "✓ Git commit created"
    }
}

function New-GitTag {
    param([string]$Version)
    
    if ($NoGit) {
        Write-Info "Skipping git tag (-NoGit flag)"
        return
    }
    
    if (-not (Test-CommandExists git)) {
        Write-Warn "Git is not installed, skipping git tag"
        return
    }
    
    try {
        git rev-parse --git-dir 2>&1 | Out-Null
    }
    catch {
        Write-Warn "Not a git repository, skipping git tag"
        return
    }
    
    Write-Step "Creating git tag..."
    
    $tagName = "v$Version"
    
    # Check if tag already exists
    try {
        git rev-parse $tagName 2>&1 | Out-Null
        Write-Warn "Tag $tagName already exists"
        
        if (-not $DryRun) {
            if (Request-Confirmation "Do you want to delete and recreate the tag?") {
                git tag -d $tagName 2>&1 | Out-Null
                Write-Info "Deleted existing tag: $tagName"
            }
            else {
                return
            }
        }
        else {
            return
        }
    }
    catch {
        # Tag doesn't exist, continue
    }
    
    if ($DryRun) {
        Write-Info "[DRY-RUN] Would create tag: $tagName"
        return
    }
    
    # Create annotated tag
    git tag -a $tagName -m "Release version $Version"
    Write-Success "✓ Git tag created: $tagName"
    Write-Host ""
    Write-Info "To push the tag, run: git push origin $tagName"
}

function Push-GitTag {
    param([string]$Version)
    
    if ($NoGit -or $NoPush) {
        Write-Info "Skipping git push"
        return
    }
    
    if (-not (Test-CommandExists git)) {
        return
    }
    
    try {
        git rev-parse --git-dir 2>&1 | Out-Null
    }
    catch {
        return
    }
    
    Write-Step "Pushing to remote..."
    
    $tagName = "v$Version"
    
    if ($DryRun) {
        Write-Info "[DRY-RUN] Would push: git push origin main"
        Write-Info "[DRY-RUN] Would push: git push origin $tagName"
        return
    }
    
    # Ask for confirmation
    if (-not (Request-Confirmation "Do you want to push commit and tag to remote?")) {
        Write-Info "Skipping push. Run manually:"
        Write-Host "  git push origin main"
        Write-Host "  git push origin $tagName"
        return
    }
    
    # Get current branch
    $currentBranch = git branch --show-current
    
    # Push commit
    try {
        git push origin $currentBranch 2>&1 | Out-Null
        Write-Success "✓ Pushed commit to remote"
    }
    catch {
        Write-Error "Failed to push commit"
        return
    }
    
    # Push tag
    try {
        git push origin $tagName 2>&1 | Out-Null
        Write-Success "✓ Pushed tag to remote: $tagName"
    }
    catch {
        Write-Error "Failed to push tag"
    }
}

# ============================================================================
# Verification Function
# ============================================================================

function Test-Updates {
    param([string]$Version)
    
    if ($DryRun) {
        return $true
    }
    
    Write-Step "Verifying updates..."
    
    $errors = 0
    
    # Check VERSION file
    if (Test-Path $VERSION_FILE) {
        $current = (Get-Content $VERSION_FILE -Raw).Trim()
        if ($current -eq $Version) {
            Write-Success "✓ VERSION file: $current"
        }
        else {
            Write-Error "✗ VERSION file: expected $Version, found $current"
            $errors++
        }
    }
    
    # Check pyproject.toml
    if (Test-Path $PYPROJECT_FILE) {
        $content = Get-Content $PYPROJECT_FILE -Raw
        if ($content -match "version\s*=\s*`"$([regex]::Escape($Version))`"") {
            Write-Success "✓ pyproject.toml: $Version"
        }
        else {
            Write-Error "✗ pyproject.toml: version not found or incorrect"
            $errors++
        }
    }
    
    # Check __init__.py
    if (Test-Path $INIT_FILE) {
        $content = Get-Content $INIT_FILE -Raw
        if ($content -match "__version__\s*=\s*`"$([regex]::Escape($Version))`"") {
            Write-Success "✓ __init__.py: $Version"
        }
        else {
            Write-Error "✗ __init__.py: version not found or incorrect"
            $errors++
        }
    }
    
    if ($errors -gt 0) {
        Write-Host ""
        Write-Error "Verification failed with $errors error(s)"
        return $false
    }
    
    Write-Host ""
    Write-Success "All files verified successfully"
    return $true
}

# ============================================================================
# Summary Function
# ============================================================================

function Show-Summary {
    param(
        [string]$OldVersion,
        [string]$NewVersion
    )
    
    Write-Separator
    Write-Info "Version Bump Summary:"
    Write-Host ""
    Write-Host "  Old Version: $OldVersion"
    Write-Host "  New Version: $NewVersion"
    Write-Host ""
    Write-Host "  Updated files:"
    Write-Host "    - $VERSION_FILE"
    Write-Host "    - $PYPROJECT_FILE"
    Write-Host "    - $INIT_FILE"
    Write-Host ""
    
    if (-not $NoGit) {
        Write-Host "  Git operations:"
        Write-Host "    - Commit created"
        Write-Host "    - Tag created: v$NewVersion"
        Write-Host ""
        Write-Info "Next steps:"
        Write-Host "    git push origin main"
        Write-Host "    git push origin v$NewVersion"
    }
    
    Write-Separator
}

# ============================================================================
# Main
# ============================================================================

function Main {
    Write-Header "Version Bump"
    
    # Validate version format
    Test-VersionFormat $NewVersion
    Write-Host ""
    
    # Get current version
    $currentVersion = Get-CurrentVersion
    Write-Info "Current version: $currentVersion"
    Write-Info "New version: $NewVersion"
    Write-Host ""
    
    # Flags info
    if ($DryRun) {
        Write-Info "Dry-run mode enabled"
    }
    if ($NoGit) {
        Write-Info "Git operations disabled"
    }
    if ($NoPush) {
        Write-Info "Git push disabled"
    }
    Write-Host ""
    
    # Confirm if not dry-run
    if (-not $DryRun) {
        if (-not (Request-Confirmation "Do you want to proceed with version bump?")) {
            Write-Info "Version bump cancelled"
            exit 0
        }
        Write-Host ""
    }
    
    # Update files
    Update-VersionFile $NewVersion
    Update-PyProject $NewVersion
    Update-InitPy $NewVersion
    Update-ConfigFiles
    Write-Host ""
    
    # Verify updates
    $verified = Test-Updates $NewVersion
    if (-not $verified) {
        exit 1
    }
    
    # Git operations
    if (-not $DryRun) {
        Write-Host ""
        New-GitCommit $NewVersion
        New-GitTag $NewVersion
        Push-GitTag $NewVersion
    }
    
    # Show summary
    Write-Host ""
    if ($DryRun) {
        Write-Info "Dry-run complete. No files were modified."
    }
    else {
        Show-Summary $currentVersion $NewVersion
        Write-Success "Version bump complete!"
    }
}

# Run main function
try {
    Main
}
catch {
    Write-Error "An error occurred: $_"
    exit 1
}
