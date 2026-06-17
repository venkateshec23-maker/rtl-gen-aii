"""Run arb_roundrobin8 through pipeline"""
from guaranteed_flow import generate_guaranteed_gds
r = generate_guaranteed_gds(
    description='8-way round-robin arbiter with grant hold and priority override',
    module_name='arb_roundrobin8'
)
print(f'Status: {r.get("status")}')
print(f'Tapeout: {r.get("tapeout_ready")}')
print(f'GDS KB: {r.get("gds_size_kb")}')
print(f'Fmax: {r.get("fmax_mhz")}')
print(f'Method: {r.get("method_used")}')
print(f'Total mW: {r.get("total_mw")}')
