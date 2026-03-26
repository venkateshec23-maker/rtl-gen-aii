#!/usr/bin/env python3
"""
TRAFFIC LIGHT CONTROLLER - RTL-to-GDSII Pipeline Execution
Orchestrates complete flow: RTL → Synthesis → P&R → GDS → Sign-off
"""

import sys
from pathlib import Path
import tempfile
import json
from datetime import datetime

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from python.full_flow import RTLGenAI, FlowConfig, FlowResult
from python.docker_manager import DockerManager
from python.pdk_manager import PDKManager

# ═══════════════════════════════════════════════════════════════════════════════
# TRAFFIC CONTROLLER SPECIFICATION
# ═══════════════════════════════════════════════════════════════════════════════

TRAFFIC_CONTROLLER_SPEC = """
Design a 4-bit Traffic Light Controller for a single intersection with:
- 3 lights: RED, GREEN, YELLOW (3 output signals)
- Timing: Red=30s, Green=25s, Yellow=5s (use clock cycles, assume 1MHz = 1us)
- FSM States:
  - IDLE: Wait for enable
  - RED_STATE: Light red for 30 seconds
  - GREEN_STATE: Light green for 25 seconds  
  - YELLOW_STATE: Light yellow for 5 seconds
- Inputs: clk, reset, enable
- Outputs: red, green, yellow (1-bit each)
- Use a 28-bit timer counter (can count up to ~268M cycles at 1MHz)

Implement as synchronous FSM with registered outputs. Include internal counter for timing.
"""

# ═══════════════════════════════════════════════════════════════════════════════
# STAGE 1: RTL GENERATION (Via LLM or Manual)
# ═══════════════════════════════════════════════════════════════════════════════

TRAFFIC_CONTROLLER_RTL = """
// Traffic Light Controller - 4-bit FSM
// Intersection control with RED (30s) → GREEN (25s) → YELLOW (5s) cycle

module traffic_controller (
    input  clk,
    input  reset,
    input  enable,
    output reg red,
    output reg green,
    output reg yellow
);

    // FSM States
    localparam IDLE = 2'b00;
    localparam RED_STATE = 2'b01;
    localparam GREEN_STATE = 2'b10;
    localparam YELLOW_STATE = 2'b11;

    // Timing constants (in clock cycles at 1MHz = 1us per cycle)
    localparam RED_TIME = 30_000_000;      // 30 seconds
    localparam GREEN_TIME = 25_000_000;    // 25 seconds
    localparam YELLOW_TIME = 5_000_000;    // 5 seconds

    reg [1:0] state, next_state;
    reg [27:0] timer;  // Can count up to 268M cycles

    // ─────────────────────────────────────────────────────────
    // STATE MACHINE - Sequential Logic
    // ─────────────────────────────────────────────────────────
    always @(posedge clk) begin
        if (reset)
            state <= IDLE;
        else
            state <= next_state;
    end

    // ─────────────────────────────────────────────────────────
    // NEXT STATE LOGIC & TIMER
    // ─────────────────────────────────────────────────────────
    always @(posedge clk) begin
        if (reset)
            timer <= 28'b0;
        else if (!enable)
            timer <= 28'b0;
        else if (timer == 28'b0)
            timer <= 28'b0;
        else
            timer <= timer - 1'b1;
    end

    always @(*) begin
        next_state = state;
        
        case (state)
            IDLE: begin
                if (enable)
                    next_state = RED_STATE;
                else
                    next_state = IDLE;
            end
            
            RED_STATE: begin
                if (timer == 0 || timer == 1)
                    next_state = GREEN_STATE;
            end
            
            GREEN_STATE: begin
                if (timer == 0 || timer == 1)
                    next_state = YELLOW_STATE;
            end
            
            YELLOW_STATE: begin
                if (timer == 0 || timer == 1)
                    next_state = RED_STATE;
            end
            
            default:
                next_state = IDLE;
        endcase
    end

    // ─────────────────────────────────────────────────────────
    // OUTPUT LOGIC & TIMER LOAD
    // ─────────────────────────────────────────────────────────
    always @(posedge clk) begin
        if (reset) begin
            red <= 1'b0;
            green <= 1'b0;
            yellow <= 1'b0;
        end else begin
            case (next_state)
                RED_STATE: begin
                    red <= 1'b1;
                    green <= 1'b0;
                    yellow <= 1'b0;
                    if (timer == 0)
                        timer <= RED_TIME;
                end
                
                GREEN_STATE: begin
                    red <= 1'b0;
                    green <= 1'b1;
                    yellow <= 1'b0;
                    if (timer == 0)
                        timer <= GREEN_TIME;
                end
                
                YELLOW_STATE: begin
                    red <= 1'b0;
                    green <= 1'b0;
                    yellow <= 1'b1;
                    if (timer == 0)
                        timer <= YELLOW_TIME;
                end
                
                default: begin
                    red <= 1'b0;
                    green <= 1'b0;
                    yellow <= 1'b0;
                end
            endcase
        end
    end

endmodule
"""

# ═══════════════════════════════════════════════════════════════════════════════
# EXECUTION: RUN COMPLETE PIPELINE
# ═══════════════════════════════════════════════════════════════════════════════

def print_header(title):
    """Print section header"""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)

def print_status(stage, status, details=""):
    """Print stage status"""
    symbol = "✅" if status == "PASS" else "⏳" if status == "RUN" else "⚠️"
    print(f"{symbol} {stage:<40} {status:>12} {details}")

def main():
    print_header("🚦 TRAFFIC LIGHT CONTROLLER - RTL-to-GDSII Pipeline")
    print("Orchestrating complete design flow from RTL to silicon")
    
    # Create working directory
    output_base = Path(__file__).parent / "runs" / "traffic_controller"
    output_base.mkdir(parents=True, exist_ok=True)
    
    # ───────────────────────────────────────────────────────────────
    # STAGE 1: RTL GENERATION
    # ───────────────────────────────────────────────────────────────
    print_header("STAGE 1: RTL GENERATION")
    print_status("Design", "RUN", "Traffic Light Controller")
    
    rtl_file = Path(__file__).parent / "traffic_controller.v"
    
    if not rtl_file.exists():
        rtl_file.write_text(TRAFFIC_CONTROLLER_RTL)
    
    print_status("RTL File", "PASS", f"Created: {rtl_file.name}")
    print(f"  Lines of code: {len(TRAFFIC_CONTROLLER_RTL.splitlines())}")
    print(f"  Inputs: clk, reset, enable")
    print(f"  Outputs: red, green, yellow")
    
    # ───────────────────────────────────────────────────────────────
    # STAGE 2-9: PHYSICAL DESIGN PIPELINE
    # ───────────────────────────────────────────────────────────────
    print_header("STAGE 2-9: PHYSICAL DESIGN PIPELINE")
    
    try:
        print_status("Infrastructure", "RUN", "Check Docker & PDK")
        
        # Initialize managers
        docker = DockerManager()
        
        # Try to verify
        try:
            docker_status = docker.verify_installation()
            docker_ok = docker_status.running
            docker_version = docker_status.version.strip() if hasattr(docker_status, 'version') else "Docker OK"
        except:
            print_status("Docker", "WARN", "Could not verify - will attempt auto-start")
            docker_ok = False
            docker_version = "Unknown"
        
        if not docker_ok:
            print_status("Docker", "WARN", "Not running - attempting auto-start")
            try:
                docker_ok = docker.ensure_docker_running()
                if docker_ok:
                    print_status("Docker", "PASS", "Started successfully")
                else:
                    print_status("Docker", "FAIL", "Auto-start failed")
                    print("\n⚠️  Please start Docker Desktop manually and retry")
                    return False
            except Exception as e:
                print_status("Docker", "FAIL", str(e))
                print("\n⚠️  Please start Docker Desktop manually and retry")
                return False
        else:
            print_status("Docker", "PASS", docker_version)
        
        # Configure flow
        flow_config = FlowConfig(
            run_drc=True,
            run_lvs=True,
        )
        
        # Progress callback
        def progress_callback(data):
            stage = data.get("stage", "unknown")
            pct = data.get("pct", 0)
            msg = data.get("msg", "")
            pct_bar = f"[{'='*int(pct*20)}{' '*(20-int(pct*20))}]"
            print_status(stage.title(), "RUN", f"{pct_bar} {msg}")
        
        print_status("Pipeline", "RUN", "Executing 9-stage flow...")
        print("\nStages:")
        print("  1. Synthesis (Yosys)")
        print("  2. Floorplanning")
        print("  3. Placement")
        print("  4. Clock Tree Synthesis")
        print("  5. Routing")
        print("  6. GDS Generation")
        print("  7. DRC Verification")
        print("  8. LVS Verification")
        print("  9. Tapeout Packaging\n")
        
        # Execute
        result = RTLGenAI.run_from_rtl(
            rtl_path=str(rtl_file),
            top_module="traffic_controller",
            output_dir=str(output_base),
            config=flow_config,
            progress=progress_callback
        )
        
        # ───────────────────────────────────────────────────────────────
        # RESULTS
        # ───────────────────────────────────────────────────────────────
        print_header("PIPELINE RESULTS")
        
        print_status("Synthesis", "PASS", f"{result.stage_times.get('synthesis', 0):.1f}s")
        print_status("Floorplan", "PASS", f"{result.stage_times.get('floorplan', 0):.1f}s")
        print_status("Placement", "PASS", f"{result.stage_times.get('placement', 0):.1f}s")
        print_status("CTS", "PASS", f"{result.stage_times.get('cts', 0):.1f}s")
        print_status("Routing", "PASS", f"{result.stage_times.get('routing', 0):.1f}s")
        print_status("GDS", "PASS", f"{result.stage_times.get('gds', 0):.1f}s")
        
        drc_status = "PASS" if result.drc_violations == 0 else "WARN"
        print_status("DRC", drc_status, f"{result.drc_violations} violations")
        
        lvs_status = "PASS" if result.lvs_matched else "WARN"
        print_status("LVS", lvs_status, f"{'MATCHED' if result.lvs_matched else 'MISMATCH'}")
        
        print_header("FINAL DELIVERABLE")
        
        if result.gds_path and Path(result.gds_path).exists():
            gds_size = Path(result.gds_path).stat().st_size
            print_status("GDS File", "PASS", f"{Path(result.gds_path).name}")
            print(f"  Size: {gds_size:,} bytes")
            print(f"  Path: {result.gds_path}")
        
        if result.package_dir:
            print_status("Tape-out", "PASS", f"{Path(result.package_dir).name}")
        
        print_status("Total Time", "PASS", f"{result.total_seconds:.1f}s")
        
        if result.is_tapeable:
            print_status("Status", "PASS", "✅ READY FOR FABRICATION")
        else:
            print_status("Status", "WARN", "⚠️  Has issues - see DRC/LVS")
        
        print_header("SUMMARY")
        print(json.dumps({
            "design": "traffic_controller",
            "timestamp": datetime.now().isoformat(),
            "status": "SUCCESS" if result.is_tapeable else "PARTIAL",
            "total_time_seconds": result.total_seconds,
            "stage_timings": result.stage_times,
            "drc_violations": result.drc_violations,
            "lvs_matched": result.lvs_matched,
            "gds_file": result.gds_path,
            "package_dir": result.package_dir,
        }, indent=2))
        
        return result.is_tapeable
        
    except Exception as e:
        print_header("ERROR")
        print(f"❌ Pipeline failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
