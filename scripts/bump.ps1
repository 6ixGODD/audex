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
    [Parameter(Mandatory=$false, Position=0)]
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
# Import Common Utilities
# ============================================================================

$ScriptDir = $PSScriptRoot
$CommonScript = Join-Path $ScriptDir "tools\common.ps1"

if (Test-Path $CommonScript) {
    . $CommonScript
} else {
    Write-Host "ERROR: Common utilities not found at $CommonScript" -ForegroundColor Red
    exit 1
}

# ============================================================================
# Configuration
# ============================================================================

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $ScriptDir

$VERSION_FILE = Join-Path $ProjectRoot "VERSION"
$PYPROJECT_FILE = Join-Path $ProjectRoot "pyproject.toml"
$PROJECT_NAME = "audex"
$INIT_FILE = Join-Path $ProjectRoot "$PROJECT_NAME\__init__.py"
$CONFIG_EXAMPLE_YML = Join-Path $ProjectRoot ".config.example.yml"
$CONFIG_SYSTEM_LINUX = Join-Path $ProjectRoot ".config.system.linux.yml"
$CONFIG_SYSTEM_WINDOWS = Join-Path $ProjectRoot ".config.system.windows.yml"
$ENV_EXAMPLE_FILE = Join-Path $ProjectRoot ".env.example"

# ============================================================================
# Help Function
# ============================================================================

function Show-Usage {
    Write-Host @"
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

# Show help if requested or no version provided
if ($Help -or (Test-EmptyString $NewVersion)) {
    Show-Usage
    exit 0
}

# ============================================================================
# Validation Functions
# ============================================================================

function Test-VersionFormat {
    param([string]$Version)
    
    if (-not (Test-SemanticVersion $Version)) {
        Exit-WithError "Invalid version format: $Version (expected: X.Y.Z or X.Y.Z-suffix)"
    }
    
    Write-Success "Version format validated: $Version"
}

function Get-CurrentVersion {
    if (Test-FileExists $VERSION_FILE) {
        return (Trim-String (Read-FileContentRaw $VERSION_FILE))
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
    
    Write-FileContentRaw -Path $VERSION_FILE -Content $Version
    Write-Success "[OK] Updated: $VERSION_FILE"
}

function Update-PyProject {
    param([string]$Version)
    
    Write-Step "Updating pyproject.toml..."
    
    if (-not (Test-FileExists $PYPROJECT_FILE)) {
        Write-Warn "File not found: $PYPROJECT_FILE"
        return
    }
    
    if ($DryRun) {
        Write-Info "[DRY-RUN] Would update version in $PYPROJECT_FILE"
        return
    }
    
    # Read file content
    $content = Read-FileContent $PYPROJECT_FILE
    
    # Find and update version line in [project] section
    $inProjectSection = $false
    $updated = $false
    
    for ($i = 0; $i -lt $content.Length; $i++) {
        if ($content[$i] -match '^\[project\]') {
            $inProjectSection = $true
        }
        elseif ($content[$i] -match '^\[') {
            $inProjectSection = $false
        }
        elseif ($inProjectSection -and $content[$i] -match '^version\s*=\s*"[^"]*"') {
            $content[$i] = "version = `"$Version`""
            $updated = $true
            break
        }
    }
    
    if ($updated) {
        Write-FileContent -Path $PYPROJECT_FILE -Content $content
        Write-Success "[OK] Updated: $PYPROJECT_FILE ([project] section)"
    }
    else {
        Write-Warn "Could not find version in [project] section"
    }
}

function Update-InitPy {
    param([string]$Version)
    
    Write-Step "Updating $PROJECT_NAME/__init__.py..."
    
    if (-not (Test-FileExists $INIT_FILE)) {
        Write-Warn "File not found: $INIT_FILE"
        return
    }
    
    if ($DryRun) {
        Write-Info "[DRY-RUN] Would update __version__ in $INIT_FILE"
        return
    }
    
    # Read file content
    $content = Read-FileContentRaw $INIT_FILE
    
    # Update __version__ variable
    $content = $content -replace '(?m)^__version__\s*=\s*"[^"]*"', "__version__ = `"$Version`""
    Write-FileContentRaw -Path $INIT_FILE -Content $content
    Write-Success "[OK] Updated: $INIT_FILE"
}

function Update-ConfigFiles {
    Write-Step "Updating configuration files..."
    
    if ($DryRun) {
        Write-Info "[DRY-RUN] Would update $CONFIG_EXAMPLE_YML, $CONFIG_SYSTEM_LINUX, $CONFIG_SYSTEM_WINDOWS, $ENV_EXAMPLE_FILE"
        return
    }
    
    try {
        # Update config.example.yml
        "y" | uv run python -m audex init gencfg -o $CONFIG_EXAMPLE_YML --format yaml 2>&1 | Out-Null
        Write-Success "[OK] Updated: $CONFIG_EXAMPLE_YML"
        
        # Update config.system.linux.yml
        "y" | uv run python -m audex init gencfg -o $CONFIG_SYSTEM_LINUX --format system --platform linux 2>&1 | Out-Null
        Write-Success "[OK] Updated: $CONFIG_SYSTEM_LINUX"
        
        # Update config.system.windows.yml
        "y" | uv run python -m audex init gencfg -o $CONFIG_SYSTEM_WINDOWS --format system --platform windows 2>&1 | Out-Null
        Write-Success "[OK] Updated: $CONFIG_SYSTEM_WINDOWS"
        
        # Update .env.example
        "y" | uv run python -m audex init gencfg -o $ENV_EXAMPLE_FILE --format dotenv 2>&1 | Out-Null
        Write-Success "[OK] Updated: $ENV_EXAMPLE_FILE"
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
    
    if (-not (Test-GitRepository)) {
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
        Write-Success "[OK] Git commit created"
    }
}

function New-GitTag {
    param([string]$Version)
    
    if ($NoGit) {
        Write-Info "Skipping git tag (-NoGit flag)"
        return
    }
    
    if (-not (Test-GitRepository)) {
        Write-Warn "Not a git repository, skipping git tag"
        return
    }
    
    Write-Step "Creating git tag..."
    
    $tagName = "v$Version"
    
    # Check if tag already exists
    if (Test-GitTagExists $tagName) {
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
    
    if ($DryRun) {
        Write-Info "[DRY-RUN] Would create tag: $tagName"
        return
    }
    
    # Create annotated tag
    git tag -a $tagName -m "Release version $Version"
    Write-Success "[OK] Git tag created: $tagName"
    Write-Host ""
    Write-Info "To push the tag, run: git push origin $tagName"
}

function Push-GitTag {
    param([string]$Version)
    
    if ($NoGit -or $NoPush) {
        Write-Info "Skipping git push"
        return
    }
    
    if (-not (Test-GitRepository)) {
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
    $currentBranch = Get-GitCurrentBranch
    
    # Push commit
    try {
        git push origin $currentBranch 2>&1 | Out-Null
        Write-Success "[OK] Pushed commit to remote"
    }
    catch {
        Write-ErrorMsg "Failed to push commit"
        return
    }
    
    # Push tag
    try {
        git push origin $tagName 2>&1 | Out-Null
        Write-Success "[OK] Pushed tag to remote: $tagName"
    }
    catch {
        Write-ErrorMsg "Failed to push tag"
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
    if (Test-FileExists $VERSION_FILE) {
        $current = Trim-String (Read-FileContentRaw $VERSION_FILE)
        if ($current -eq $Version) {
            Write-Success "[OK] VERSION file: $current"
        }
        else {
            Write-ErrorMsg "[X] VERSION file: expected $Version, found $current"
            $errors++
        }
    }
    
    # Check pyproject.toml
    if (Test-FileExists $PYPROJECT_FILE) {
        $content = Read-FileContentRaw $PYPROJECT_FILE
        if ($content -match "version\s*=\s*`"$Version`"") {
            Write-Success "[OK] pyproject.toml: $Version"
        }
        else {
            Write-ErrorMsg "[X] pyproject.toml: version not found or incorrect"
            $errors++
        }
    }
    
    # Check __init__.py
    if (Test-FileExists $INIT_FILE) {
        $content = Read-FileContentRaw $INIT_FILE
        if ($content -match "__version__\s*=\s*`"$Version`"") {
            Write-Success "[OK] __init__.py: $Version"
        }
        else {
            Write-ErrorMsg "[X] __init__.py: version not found or incorrect"
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
