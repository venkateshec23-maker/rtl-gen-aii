# update_context.ps1
# Run at end of every session - keeps AGENT_CONTEXT.md current
# Both VS Code and Antigravity agents read this at session start

$WORK    = "C:\tools\OpenLane"
$MAIN    = "C:\Users\venka\Documents\rtl-gen-aii"
$RESULTS = "$WORK\results"
$DATE    = Get-Date -Format "yyyy-MM-dd HH:mm"

Write-Host "Collecting current pipeline state..." -ForegroundColor Cyan

# GDS
$gds_size = if (Test-Path "$RESULTS\adder_8bit.gds") {
    (Get-Item "$RESULTS\adder_8bit.gds").Length
} else { 0 }
$gds_kb = [math]::Round($gds_size / 1024, 1)
$gds_status = if ($gds_size -gt 50000) { "REAL ($gds_kb KB)" }
              elseif ($gds_size -gt 0)  { "STUB ($gds_size bytes)" }
              else                       { "MISSING" }

# Routing
$routed_size = if (Test-Path "$RESULTS\routed.def") {
    (Get-Item "$RESULTS\routed.def").Length } else { 0 }
$cts_size = if (Test-Path "$RESULTS\cts.def") {
    (Get-Item "$RESULTS\cts.def").Length } else { 0 }
$routing_status = if ($routed_size -ne $cts_size -and $routed_size -gt 0) {
    "REAL ($routed_size bytes)"
} elseif ($routed_size -eq $cts_size -and $routed_size -gt 0) {
    "SILENT_FAILURE - equals cts.def"
} else { "MISSING" }

# LVS
$lvs_status = "NOT_RUN"
if (Test-Path "$RESULTS\lvs_report_final.txt") {
    $lvs = Get-Content "$RESULTS\lvs_report_final.txt" -Raw
    $lvs_status = if ($lvs -like "*equivalent*") { "MATCHED" } else { "UNMATCHED" }
}

# Timing
$timing_status = "NOT_RUN"
$slack = "?"
if (Test-Path "$RESULTS\sta_final.txt") {
    $sta = Get-Content "$RESULTS\sta_final.txt" -Raw
    $wns_match = [regex]::Match($sta, "wns\s+([-\d.]+)")
    $slack_match = [regex]::Match($sta, "slack\s+\(MET\)\s+([\d.]+)")
    if ($wns_match.Success) {
        $wns = [float]$wns_match.Groups[1].Value
        $timing_status = if ($wns -ge 0) { "MET" } else { "VIOLATED" }
    }
    if ($slack_match.Success) { $slack = $slack_match.Groups[1].Value + "ns" }
}

# Synthesis
$netlist_status = "MISSING"
$sky130_count = 0
if (Test-Path "$RESULTS\adder_8bit_sky130.v") {
    $n = Get-Content "$RESULTS\adder_8bit_sky130.v" -Raw
    $sky130_count = ([regex]::Matches($n, "sky130_fd_sc_hd__")).Count
    $generic_count = ([regex]::Matches($n, '\$_XOR_|\$_SDFF_')).Count
    $netlist_status = if ($sky130_count -gt 0 -and $generic_count -eq 0) {
        "REAL_SKY130 ($sky130_count cells)"
    } elseif ($generic_count -gt 0) {
        "GENERIC_CELLS - BROKEN"
    } else { "MISSING" }
}

# Tests
Set-Location $MAIN
$unit_out = python -m pytest -m unit -q 2>&1
$unit_pass = ([regex]::Matches($unit_out, " passed")).Count
$unit_fail = ([regex]::Matches($unit_out, " failed")).Count

$int_out = python -m pytest -m integration -q 2>&1
$int_pass = ([regex]::Matches($int_out, " passed")).Count
$int_fail = ([regex]::Matches($int_out, " failed")).Count

# Tapeout verdict
$tapeout = if (
    $gds_size -gt 50000 -and
    $lvs_status -eq "MATCHED" -and
    $timing_status -eq "MET" -and
    $routed_size -ne $cts_size
) { "YES" } else { "NO - check items above" }

# Write AGENT_CONTEXT.md
$ctx = "# RTL-Gen AI - Agent Context File
# READ THIS FIRST BEFORE DOING ANYTHING
# Last Updated: $DATE

CURRENT PIPELINE STATE:
Synthesis: $netlist_status
Routing: $routing_status
GDS: $gds_status
LVS: $lvs_status
Timing: $timing_status ($slack)
Unit Tests: $unit_pass PASS / $unit_fail FAIL
Integration Tests: $int_pass PASS / $int_fail FAIL
TAPE-OUT READY: $tapeout

CRITICAL FILES - DO NOT MODIFY:
- full_flow.py: Main Docker EDA orchestrator
- RealMetricsParser: Reads real tool outputs
- FILE_SIZE_THRESHOLDS: Minimum sizes for real files
- verify_everything.ps1: Complete verification
- tests/test_unit.py: Prevention enforcement

DO NOT REVERT THESE FIVE FIXES:
1. hilomap before opt_clean (prevents DRT-0305)
2. pdngen before global_route (prevents SIGSEGV)
3. make_tracks before placement (prevents PPL-0021)
4. synth_sky130 not synth (prevents generic cells)
5. Dynamic cell name extraction from SPICE (prevents LVS abort)

VERIFICATION COMMANDS:
  cd C:\tools\OpenLane
  powershell -ExecutionPolicy Bypass -File verify_everything.ps1

Expected result: PASS: 55+, FAIL: 0
"

$ctx | Out-File -FilePath "$MAIN\AGENT_CONTEXT.md" -Encoding UTF8 -Force

Write-Host ""
Write-Host "AGENT_CONTEXT.md written successfully" -ForegroundColor Green
Write-Host ""
Write-Host "Current state:" -ForegroundColor Cyan
Write-Host "  Synthesis:  $netlist_status"
Write-Host "  Routing:    $routing_status"
Write-Host "  GDS:        $gds_status"
Write-Host "  LVS:        $lvs_status"
Write-Host "  Timing:     $timing_status ($slack)"
Write-Host "  Unit:       $unit_pass PASS / $unit_fail FAIL"
Write-Host "  Integration: $int_pass PASS / $int_fail FAIL"
Write-Host "  TAPE-OUT:   $tapeout"
Write-Host ""
Write-Host "Run this at end of every session:" -ForegroundColor Yellow
Write-Host "  cd C:\Users\venka\Documents\rtl-gen-aii" -ForegroundColor Yellow
Write-Host "  powershell -ExecutionPolicy Bypass -File update_context.ps1" -ForegroundColor Yellow
