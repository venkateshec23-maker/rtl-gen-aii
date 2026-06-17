"""Run pipeline_4stage through pipeline"""
from guaranteed_flow import generate_guaranteed_gds
r = generate_guaranteed_gds(
    description='4-stage pipelined 8-bit adder with hazard detection and forwarding',
    module_name='pipeline_4stage'
)
print(f'Status: {r.get("status")}')
print(f'Tapeout: {r.get("tapeout_ready")}')
print(f'GDS KB: {r.get("gds_size_kb")}')
print(f'Fmax: {r.get("fmax_mhz")}')
print(f'Method: {r.get("method_used")}')
print(f'Total mW: {r.get("total_mw")}')
