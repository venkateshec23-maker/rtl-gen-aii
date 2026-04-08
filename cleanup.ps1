#!/usr/bin/env powershell

Write-Host "Cleanup: Removing unwanted files..." -ForegroundColor Yellow

$filesToDelete = @(
    "app_backup.py",
    "app_synthesis_integration.py",
    "complete_integration.py",
    "adder_8bit.v.bak",
    "debug_grok.py",
    "fallback_test_results.txt",
    "final_test_log.txt",
    "flake8_errors.txt",
    "integration_results.txt",
    "output.txt",
    "packages.txt",
    "day1_reflection.txt",
    "day2_decisions.py",
    "day2_practice.py",
    "day2_reflection.txt",
    "day2_variables.py",
    "day3_functions.py",
    "day3_modules.py",
    "day3_practice.py",
    "day3_reflection.txt",
    "day4_errors.py",
    "day4_files.py",
    "day4_practice.py",
    "day4_reflection.txt",
    "day4_strings.py",
    "day5_json_basics.py",
    "day5_llm_client.py",
    "day5_practice.py",
    "day5_reflection.txt",
    "day5_requests.py",
    "DAY_33_COMPLETION.md",
    "DAY_34_COMPLETION.md",
    "DAY_38_COMPLETION.md",
    "DAY_39_COMPLETION.md",
    "DAY_40_COMPLETION.md",
    "DAY_41_COMPLETION.md",
    "DAY_42_COMPLETION.md",
    "DAY_43_COMPLETION.md",
    "DAY_44_COMPLETION.md",
    "DAY_45_COMPLETION.md",
    "DAY_46_COMPLETION.md",
    "DAY_47_COMPLETION.md",
    "DAY_48_COMPLETION.md",
    "DAYS_27-29_COMPLETION.md",
    "DAYS_34_35_IMPLEMENTATION_SUMMARY.md",
    "BETA_PERIOD_SUMMARY.md",
    "00_VERIFICATION_COMPLETE.md",
    "00_WAVEFORM_PHASE2_COMPLETE.md",
    "00_YOSYS_AND_SYNTHESIS_COMPLETE.md",
    "PHASE3_SYNTHESIS_COMPLETE.md",
    "PHASE3_VERIFICATION_SUMMARY.md",
    "CLOUD_DEPLOYMENT_COMPLETE.md",
    "DEPLOYMENT_COMPLETE.md",
    "IMPLEMENTATION_COMPLETE.md",
    "FEATURES_DEPLOYED.md"
)

$deletedCount = 0

foreach ($file in $filesToDelete) {
    if (Test-Path $file) {
        Remove-Item -Path $file -Force
        Write-Host "Deleted: $file" -ForegroundColor Green
        $deletedCount++
    }
}

Write-Host ""
Write-Host "Cleanup complete! Deleted $deletedCount old files" -ForegroundColor Green
Write-Host ""
Write-Host "Important files preserved:" -ForegroundColor Cyan
Write-Host "  - app_final/ (production)"
Write-Host "  - python/ (synthesis)"
Write-Host "  - test_pipeline.py"
Write-Host ""
