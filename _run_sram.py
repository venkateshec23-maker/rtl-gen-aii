"""Run sram_512 through pipeline"""
from guaranteed_flow import generate_guaranteed_gds
r = generate_guaranteed_gds(
    description='512x8-bit synchronous SRAM with byte write enable and output register',
    module_name='sram_512'
)
print(f'Status: {r.get("status")}')
print(f'Tapeout: {r.get("tapeout_ready")}')
print(f'GDS KB: {r.get("gds_size_kb")}')
print(f'Fmax: {r.get("fmax_mhz")}')
print(f'Method: {r.get("method_used")}')
print(f'Total mW: {r.get("total_mw")}')
