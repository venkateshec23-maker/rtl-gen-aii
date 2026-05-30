import os
from typing import Dict, List

def extract_failure_truth_table(vcd_path: str, max_ticks: int = 20) -> str:
    """
    Read a VCD file and return an ASCII truth table of the last state changes.
    Extracts up to max_ticks timestamp changes to provide LLMs with logic context.
    """
    try:
        with open(vcd_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except FileNotFoundError:
        return "No VCD trace found."

    signals = {}  # symbol -> name
    
    # Parse header for variables
    for line in lines:
        if line.startswith("$var"):
            parts = line.strip().split()
            if len(parts) >= 5:
                # $var type width symbol name ...
                symbol = parts[3]
                name = parts[4]
                signals[symbol] = name
        elif line.startswith("$enddefinitions"):
            break
            
    if not signals:
        return "No variables found in VCD."

    # Parse timeline
    timeline = []
    current_time = "0"
    current_state = {sym: "X" for sym in signals.keys()}
    
    in_dumpvars = False
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        if line.startswith("$dumpvars"):
            in_dumpvars = True
            continue
        elif line.startswith("$end") and in_dumpvars:
            in_dumpvars = False
            continue
        elif line.startswith("$"):
            continue

        if line.startswith('#'):
            # New time step
            if current_time is not None:
                # Only append if something has changed from the initial block, 
                # or if it's the first time we see a delta.
                if len(timeline) == 0 or timeline[-1][1] != current_state:
                    timeline.append((current_time, current_state.copy()))
            current_time = line[1:]
        elif line.startswith(('b', 'B')):
            # multi-bit: b0010 !
            parts = line.split()
            if len(parts) == 2:
                val = parts[0][1:]
                sym = parts[1]
                if sym in current_state:
                    current_state[sym] = val
        elif line[0] in '01xXzZ':
            # single bit: 0!
            val = line[0]
            sym = line[1:]
            if sym in current_state:
                current_state[sym] = val
                
    # append last state
    if current_time is not None:
        timeline.append((current_time, current_state.copy()))
        
    if not timeline:
        return "VCD trace is empty."
        
    # Get last events, remove duplicate consecutive states if any
    recent = timeline[-max_ticks:]
    
    # Format table
    signal_symbols = list(signals.keys())
    signal_names = [signals[s] for s in signal_symbols]
    
    header = ["Time"] + signal_names
    col_widths = [max(len(h), 8) for h in header]
    
    rows = []
    for time_val, state_dict in recent:
        row = [f"#{time_val}"]
        for sym in signal_symbols:
            val = state_dict.get(sym, "X")
            row.append(val)
        rows.append(row)
        
    for row in rows:
        for i, cell in enumerate(row):
            if len(cell) > col_widths[i]:
                col_widths[i] = len(cell)
                
    table_lines = []
    hr = "-" * (sum(col_widths) + 3 * len(col_widths) + 1)
    
    def pad(items):
        return "| " + " | ".join(str(item).ljust(w) for item, w in zip(items, col_widths)) + " |"
        
    table_lines.append(hr)
    table_lines.append(pad(header))
    table_lines.append(hr)
    for row in rows:
        table_lines.append(pad(row))
    table_lines.append(hr)
    
    return "\n".join(table_lines)
