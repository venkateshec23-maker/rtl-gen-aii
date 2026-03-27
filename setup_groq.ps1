#!/usr/bin/env powershell
<#
.SYNOPSIS
Groq API setup helper for OpenCode

.DESCRIPTION
Quickly set up Groq (fastest free API) for OpenCode code generation

.EXAMPLE
.\setup_groq.ps1
# Follow prompts to enter API key

# Then test:
.\run_opencode.ps1 "8-bit counter"

.NOTES
Groq is VERY fast (2-5 seconds per generation)
Get free API key at: https://console.groq.com
#>

Write-Host "🚀 Groq API Setup for OpenCode" -ForegroundColor Cyan
Write-Host ""
Write-Host "Groq provides fast, free API access for RTL generation" -ForegroundColor Yellow
Write-Host ""

# Check if API key already set
$currentKey = $env:GROQ_API_KEY
if ($currentKey) {
    Write-Host "✅ Groq API key already configured (set to: $($currentKey.Substring(0, 10))...)" -ForegroundColor Green
    $prompt = Read-Host "Update with new key? (y/n)"
    if ($prompt -ne "y") {
        Write-Host "Using existing key. Testing OpenCode..." -ForegroundColor Green
        & "$PSScriptRoot\run_opencode.ps1" --version
        exit 0
    }
}

Write-Host ""
Write-Host "Step 1: Get your Groq API Key" -ForegroundColor Cyan
Write-Host "  1. Go to: https://console.groq.com" -ForegroundColor White
Write-Host "  2. Sign up or log in" -ForegroundColor White
Write-Host "  3. Copy your API key (starts with 'gsk_')" -ForegroundColor White
Write-Host ""

$apiKey = Read-Host "Paste your Groq API key"

if (-not $apiKey.StartsWith("gsk_")) {
    Write-Host "❌ Invalid API key format (should start with 'gsk_')" -ForegroundColor Red
    exit 1
}

# Set environment variable for current session
$env:GROQ_API_KEY = $apiKey
Write-Host "✅ API key set for this session" -ForegroundColor Green

# Optionally save for future sessions
$savePerm = Read-Host "Save for future sessions? (y/n)"
if ($savePerm -eq "y") {
    [Environment]::SetEnvironmentVariable("GROQ_API_KEY", $apiKey, "User")
    Write-Host "✅ API key saved to user environment" -ForegroundColor Green
}

Write-Host ""
Write-Host "Step 2: Testing OpenCode with Groq" -ForegroundColor Cyan
Write-Host "Command: .\run_opencode.ps1 '--version'" -ForegroundColor Gray
Write-Host ""

& "$PSScriptRoot\run_opencode.ps1" --version

Write-Host ""
Write-Host "✨ Setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Ready to generate Verilog designs:" -ForegroundColor Cyan
Write-Host "  .\run_opencode.ps1 \"8-bit counter with clock and reset\"" -ForegroundColor White
Write-Host ""
Write-Host "Expected speed: 10-15 seconds total (super fast!)" -ForegroundColor Yellow
