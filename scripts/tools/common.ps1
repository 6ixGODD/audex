# ============================================================================
# Common Utilities Library (PowerShell)
# ============================================================================
# Description: Shared functions and utilities for all PowerShell scripts
# Usage: . "$PSScriptRoot\tools\common.ps1"
# ============================================================================

# Set encoding to UTF-8 to avoid garbled text
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$script:OutputEncoding = [System.Text.Encoding]::UTF8

# ============================================================================
# Color Definitions
# ============================================================================

$script:Colors = @{
    Green   = "Green"
    Red     = "Red"
    Yellow  = "Yellow"
    Blue    = "Blue"
    Cyan    = "Cyan"
    Magenta = "Magenta"
    White   = "White"
}

# ============================================================================
# Logging Functions
# ============================================================================

function Write-ColorOutput {
    <#
    .SYNOPSIS
    Write colored output to console
    .PARAMETER Message
    The message to display
    .PARAMETER ForegroundColor
    The color to use (default: White)
    #>
    param(
        [string]$Message,
        [string]$ForegroundColor = "White"
    )
    Write-Host $Message -ForegroundColor $ForegroundColor
}

function Write-Info {
    <#
    .SYNOPSIS
    Write info message
    .PARAMETER Message
    The message to display
    #>
    param([string]$Message)
    Write-ColorOutput "[INFO] $Message" -ForegroundColor $script:Colors.Green
}

function Write-ErrorMsg {
    <#
    .SYNOPSIS
    Write error message (renamed to avoid conflict with built-in Write-Error)
    .PARAMETER Message
    The message to display
    #>
    param([string]$Message)
    Write-ColorOutput "[ERROR] $Message" -ForegroundColor $script:Colors.Red
}

function Write-Warn {
    <#
    .SYNOPSIS
    Write warning message
    .PARAMETER Message
    The message to display
    #>
    param([string]$Message)
    Write-ColorOutput "[WARN] $Message" -ForegroundColor $script:Colors.Yellow
}

function Write-Step {
    <#
    .SYNOPSIS
    Write step message
    .PARAMETER Message
    The message to display
    #>
    param([string]$Message)
    Write-ColorOutput "[STEP] $Message" -ForegroundColor $script:Colors.Cyan
}

function Write-Success {
    <#
    .SYNOPSIS
    Write success message
    .PARAMETER Message
    The message to display
    #>
    param([string]$Message)
    Write-ColorOutput "[SUCCESS] $Message" -ForegroundColor $script:Colors.Green
}

function Write-Debug {
    <#
    .SYNOPSIS
    Write debug message (only if DEBUG is set)
    .PARAMETER Message
    The message to display
    #>
    param([string]$Message)
    if ($env:DEBUG -eq "1") {
        Write-ColorOutput "[DEBUG] $Message" -ForegroundColor $script:Colors.Blue
    }
}

# ============================================================================
# Utility Functions
# ============================================================================

function Write-Separator {
    <#
    .SYNOPSIS
    Print a separator line
    #>
    Write-Host "========================================="
}

function Write-Header {
    <#
    .SYNOPSIS
    Print a section header
    .PARAMETER Title
    The header title
    #>
    param([string]$Title)
    Write-Host ""
    Write-Separator
    Write-Host $Title
    Write-Separator
    Write-Host ""
}

function Test-CommandExists {
    <#
    .SYNOPSIS
    Check if a command exists
    .PARAMETER Command
    The command name to check
    .OUTPUTS
    Boolean indicating if command exists
    #>
    param([string]$Command)
    $null -ne (Get-Command $Command -ErrorAction SilentlyContinue)
}

function Test-DirectoryExists {
    <#
    .SYNOPSIS
    Check if a directory exists
    .PARAMETER Path
    The directory path to check
    .OUTPUTS
    Boolean indicating if directory exists
    #>
    param([string]$Path)
    Test-Path -Path $Path -PathType Container
}

function Test-FileExists {
    <#
    .SYNOPSIS
    Check if a file exists
    .PARAMETER Path
    The file path to check
    .OUTPUTS
    Boolean indicating if file exists
    #>
    param([string]$Path)
    Test-Path -Path $Path -PathType Leaf
}

function Ensure-Directory {
    <#
    .SYNOPSIS
    Create directory if it doesn't exist
    .PARAMETER Path
    The directory path to create
    #>
    param([string]$Path)
    if (-not (Test-DirectoryExists $Path)) {
        try {
            New-Item -Path $Path -ItemType Directory -Force | Out-Null
        }
        catch {
            Exit-WithError "Failed to create directory: $Path"
        }
    }
}

function Request-Confirmation {
    <#
    .SYNOPSIS
    Ask user for confirmation
    .PARAMETER Prompt
    The prompt message (default: "Are you sure?")
    .OUTPUTS
    Boolean indicating user's response
    #>
    param([string]$Prompt = "Are you sure?")
    $response = Read-Host "$Prompt (y/N)"
    return $response -match '^[yY](es)?$'
}

function Exit-WithError {
    <#
    .SYNOPSIS
    Exit script with error message and code
    .PARAMETER Message
    The error message to display
    .PARAMETER ExitCode
    The exit code (default: 1)
    #>
    param(
        [string]$Message,
        [int]$ExitCode = 1
    )
    Write-ErrorMsg $Message
    exit $ExitCode
}

# ============================================================================
# File Operations
# ============================================================================

function Read-FileContent {
    <#
    .SYNOPSIS
    Read file content safely with UTF-8 encoding
    .PARAMETER Path
    The file path to read
    .OUTPUTS
    File content as array of lines
    #>
    param([string]$Path)
    if (-not (Test-FileExists $Path)) {
        Exit-WithError "File not found: $Path"
    }
    return Get-Content -Path $Path -Encoding UTF8
}

function Read-FileContentRaw {
    <#
    .SYNOPSIS
    Read file content as single string with UTF-8 encoding
    .PARAMETER Path
    The file path to read
    .OUTPUTS
    File content as single string
    #>
    param([string]$Path)
    if (-not (Test-FileExists $Path)) {
        Exit-WithError "File not found: $Path"
    }
    return Get-Content -Path $Path -Encoding UTF8 -Raw
}

function Write-FileContent {
    <#
    .SYNOPSIS
    Write content to file with UTF-8 encoding
    .PARAMETER Path
    The file path to write
    .PARAMETER Content
    The content to write
    #>
    param(
        [string]$Path,
        [string[]]$Content
    )
    try {
        $Content | Set-Content -Path $Path -Encoding UTF8
    }
    catch {
        Exit-WithError "Failed to write file: $Path - $_"
    }
}

function Write-FileContentRaw {
    <#
    .SYNOPSIS
    Write raw content to file with UTF-8 encoding (no newline)
    .PARAMETER Path
    The file path to write
    .PARAMETER Content
    The content to write
    #>
    param(
        [string]$Path,
        [string]$Content
    )
    try {
        Set-Content -Path $Path -Value $Content -Encoding UTF8 -NoNewline
    }
    catch {
        Exit-WithError "Failed to write file: $Path - $_"
    }
}

# ============================================================================
# Git Operations
# ============================================================================

function Test-GitRepository {
    <#
    .SYNOPSIS
    Check if current directory is a git repository
    .OUTPUTS
    Boolean indicating if it's a git repository
    #>
    if (-not (Test-CommandExists git)) {
        return $false
    }
    
    try {
        git rev-parse --git-dir 2>&1 | Out-Null
        return $LASTEXITCODE -eq 0
    }
    catch {
        return $false
    }
}

function Get-GitCurrentBranch {
    <#
    .SYNOPSIS
    Get current git branch name
    .OUTPUTS
    Current branch name or empty string
    #>
    if (-not (Test-GitRepository)) {
        return ""
    }
    
    try {
        return git branch --show-current 2>&1
    }
    catch {
        return ""
    }
}

function Test-GitTagExists {
    <#
    .SYNOPSIS
    Check if a git tag exists
    .PARAMETER TagName
    The tag name to check
    .OUTPUTS
    Boolean indicating if tag exists
    #>
    param([string]$TagName)
    
    if (-not (Test-GitRepository)) {
        return $false
    }
    
    try {
        git rev-parse $TagName 2>&1 | Out-Null
        return $LASTEXITCODE -eq 0
    }
    catch {
        return $false
    }
}

# ============================================================================
# String Utilities
# ============================================================================

function Trim-String {
    <#
    .SYNOPSIS
    Trim whitespace from string
    .PARAMETER String
    The string to trim
    .OUTPUTS
    Trimmed string
    #>
    param([string]$String)
    return $String.Trim()
}

function Test-EmptyString {
    <#
    .SYNOPSIS
    Check if string is null or whitespace
    .PARAMETER String
    The string to check
    .OUTPUTS
    Boolean indicating if string is empty
    #>
    param([string]$String)
    return [string]::IsNullOrWhiteSpace($String)
}

# ============================================================================
# Version Utilities
# ============================================================================

function Test-SemanticVersion {
    <#
    .SYNOPSIS
    Validate semantic version format (X.Y.Z or X.Y.Z-suffix)
    .PARAMETER Version
    The version string to validate
    .OUTPUTS
    Boolean indicating if version is valid
    #>
    param([string]$Version)
    return $Version -match '^[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9.]+)?$'
}

# ============================================================================
# Export Functions
# ============================================================================

# Export all functions for use in other scripts
Export-ModuleMember -Function *

# ============================================================================
# Script Information
# ============================================================================

<#
.SYNOPSIS
Common utilities library for PowerShell scripts

.DESCRIPTION
This module provides common utility functions for PowerShell scripts including:
- Colored logging functions (Info, Warn, Error, Success, Step, Debug)
- File operations with UTF-8 encoding
- Git operations
- String utilities
- Confirmation prompts
- Error handling

.EXAMPLE
# Import the module
. "$PSScriptRoot\tools\common.ps1"

# Use logging functions
Write-Info "Starting process..."
Write-Step "Processing files..."
Write-Success "Process completed!"

# File operations
$content = Read-FileContent "config.yaml"
Write-FileContent "output.txt" $content

# Confirmation
if (Request-Confirmation "Continue?") {
    Write-Info "Continuing..."
}

# Git operations
if (Test-GitRepository) {
    $branch = Get-GitCurrentBranch
    Write-Info "Current branch: $branch"
}

.NOTES
Version: 1.0.0
Author: Audex Project
#>
