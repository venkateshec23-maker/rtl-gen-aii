"""Run lfsr_prng through pipeline"""
from guaranteed_flow import generate_guaranteed_gds
r = generate_guaranteed_gds(
    description='16-bit linear feedback shift register pseudo-random number generator',
    module_name='lfsr_prng'
)
print(f'Status: {r.get("status")}')
print(f'Tapeout: {r.get("tapeout_ready")}')
print(f'GDS KB: {r.get("gds_size_kb")}')
print(f'Fmax: {r.get("fmax_mhz")}')
print(f'Method: {r.get("method_used")}')
print(f'Total mW: {r.get("total_mw")}')
