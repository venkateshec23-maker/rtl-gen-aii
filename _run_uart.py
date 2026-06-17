"""Run uart_fullduplex through pipeline"""
from guaranteed_flow import generate_guaranteed_gds
r = generate_guaranteed_gds(
    description='Full duplex UART with separate TX and RX at 115200 baud and status registers',
    module_name='uart_fullduplex'
)
print(f'Status: {r.get("status")}')
print(f'Tapeout: {r.get("tapeout_ready")}')
print(f'GDS KB: {r.get("gds_size_kb")}')
print(f'Fmax: {r.get("fmax_mhz")}')
print(f'Method: {r.get("method_used")}')
print(f'Total mW: {r.get("total_mw")}')
