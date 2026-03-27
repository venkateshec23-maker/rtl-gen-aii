#!/usr/bin/env powershell
<#
.SYNOPSIS
OpenCode helper script - Run OpenCode AI inside Docker

.DESCRIPTION
Simplifies running OpenCode commands via Docker without needing Node.js installed locally.

.EXAMPLE
./run_opencode.ps1 --version
./run_opencode.ps1 "Generate an 8-bit counter"

.NOTES
Requires Docker to be installed and running.
#>

param(
    [Parameter(Position = 0, ValueFromRemainingArguments = $true)]
    [string[]]$Arguments
)

# Check if Docker is available
try {
    docker --version | Out-Null
} catch {
    Write-Host "❌ Docker is not installed or not in PATH"
    Write-Host "Please install Docker from: https://docker.com/get-started/"
    exit 1
}

# Check if Docker daemon is running
try {
    docker ps | Out-Null
} catch {
    Write-Host "❌ Docker daemon is not running"
    Write-Host "Please start Docker Desktop"
    exit 1
}

# Get the project root directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = $ScriptDir

# Run OpenCode in Docker
Write-Host "🚀 Running OpenCode: $Arguments"
Write-Host ""

if ($Arguments.Count -eq 0) {
    # No arguments - start interactive shell
    docker run -it --rm `
        --volume "${ProjectRoot}:/workspace" `
        --workdir /workspace `
        node:25 sh -c "npm install -g opencode-ai@latest && opencode"
} else {
    # Pass arguments to OpenCode
    $ArgString = $Arguments -join " "
    docker run -it --rm `
        --volume "${ProjectRoot}:/workspace" `
        --workdir /workspace `
        node:25 sh -c "npm install -g opencode-ai@latest && opencode $ArgString"
}
