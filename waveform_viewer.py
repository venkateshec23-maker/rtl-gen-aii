"""
Waveform Viewer - Web-based VCD viewer with Signal.js integration
Converts VCD files to JSON for interactive browser viewing
"""
import re
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

log = logging.getLogger(__name__)


@dataclass
class VCDSignal:
    name: str
    width: int
    scope: str
    timescale: str
    values: List[tuple] = field(default_factory=list)


@dataclass
class VCDWaveformData:
    timescale: str
    time_values: List[int]
    signals: Dict[str, VCDSignal]
    metadata: Dict[str, str]


class VCDParser:
    """Parse VCD files into structured waveform data"""
    
    def __init__(self, vcd_path: str):
        self.vcd_path = Path(vcd_path)
        self.signals: Dict[str, VCDSignal] = {}
        self.current_time = 0
        self.timescale = "1ns"
        self.time_values: List[int] = []
        self.metadata: Dict[str, str] = {}
        self.var_map: Dict[str, str] = {}
        
    def parse(self) -> VCDWaveformData:
        """Parse VCD file and return structured data"""
        if not self.vcd_path.exists():
            raise FileNotFoundError(f"VCD file not found: {self.vcd_path}")
        
        content = self.vcd_path.read_text(errors="ignore")
        
        self._parse_header(content)
        self._parse_values(content)
        
        return VCDWaveformData(
            timescale=self.timescale,
            time_values=self.time_values,
            signals=self.signals,
            metadata=self.metadata
        )
    
    def _parse_header(self, content: str):
        """Parse VCD header section"""
        header_match = re.search(r'(.*?)\$enddefinitions', content, re.DOTALL)
        if not header_match:
            return
        
        header = header_match.group(1)
        
        ts_match = re.search(r'\$timescale\s+(\S+)\s+\$end', header)
        if ts_match:
            self.timescale = ts_match.group(1)
        
        date_match = re.search(r'\$date\s+(.*?)\s+\$end', header, re.DOTALL)
        if date_match:
            self.metadata['date'] = date_match.group(1).strip()
        
        version_match = re.search(r'\$version\s+(.*?)\s+\$end', header, re.DOTALL)
        if version_match:
            self.metadata['version'] = version_match.group(1).strip()
        
        scope_stack = []
        for line in header.split('\n'):
            line = line.strip()
            
            if line.startswith('$scope'):
                scope_match = re.search(r'\$scope\s+\w+\s+(\w+)', line)
                if scope_match:
                    scope_stack.append(scope_match.group(1))
            
            elif line.startswith('$upscope'):
                if scope_stack:
                    scope_stack.pop()
            
            elif line.startswith('$var'):
                var_match = re.search(
                    r'\$var\s+(\w+)\s+(\d+)\s+(\S+)\s+(\S+)',
                    line
                )
                if var_match:
                    var_type = var_match.group(1)
                    width = int(var_match.group(2))
                    var_id = var_match.group(3)
                    var_name = var_match.group(4)
                    
                    full_name = '.'.join(scope_stack + [var_name])
                    
                    self.var_map[var_id] = full_name
                    self.signals[full_name] = VCDSignal(
                        name=var_name,
                        width=width,
                        scope='.'.join(scope_stack),
                        timescale=self.timescale
                    )
    
    def _parse_values(self, content: str):
        """Parse value changes from VCD"""
        value_section_match = re.search(r'\$enddefinitions.*?\$end\s*(.*)', content, re.DOTALL)
        if not value_section_match:
            return
        
        value_section = value_section_match.group(1)
        
        current_values: Dict[str, int] = {}
        for sig_name in self.signals:
            current_values[sig_name] = 0
        
        for line in value_section.split('\n'):
            line = line.strip()
            if not line:
                continue
            
            if line.startswith('#'):
                self.current_time = int(line[1:])
                self.time_values.append(self.current_time)
            
            elif line[0] in '01xz':
                value = line[0]
                var_id = line[1:]
                if var_id in self.var_map:
                    sig_name = self.var_map[var_id]
                    scaled_val = 1 if value == '1' else (0 if value == '0' else -1)
                    current_values[sig_name] = scaled_val
                    self.signals[sig_name].values.append(
                        (self.current_time, scaled_val)
                    )
            
            elif line.startswith('b'):
                parts = line.split()
                if len(parts) >= 2:
                    binary_val = parts[0][1:]
                    var_id = parts[1]
                    if var_id in self.var_map:
                        sig_name = self.var_map[var_id]
                        try:
                            int_val = int(binary_val, 2)
                        except ValueError:
                            int_val = 0
                        current_values[sig_name] = int_val
                        self.signals[sig_name].values.append(
                            (self.current_time, int_val)
                        )


def vcd_to_json(vcd_path: str) -> Dict[str, Any]:
    """Convert VCD file to JSON format for Signal.js"""
    parser = VCDParser(vcd_path)
    try:
        data = parser.parse()
    except Exception as e:
        log.error(f"VCD parse error: {e}")
        return {"error": str(e)}
    
    timescale_mapping = {
        's': 1e9, 'ms': 1e6, 'us': 1e3, 'ns': 1,
        'ps': 1e-3, 'fs': 1e-6
    }
    
    ts_unit = re.search(r'(\d+)(\w+)', data.timescale)
    if ts_unit:
        scale_factor = float(ts_unit.group(1))
        unit = ts_unit.group(2)
        time_scale = scale_factor * timescale_mapping.get(unit, 1)
    else:
        time_scale = 1
    
    signals_json = []
    for sig_name, sig in data.signals.items():
        if sig.width == 1:
            wave_data = []
            for t, v in sig.values:
                wave_data.append([int(t * time_scale), 1 if v else 0])
            signals_json.append({
                'name': sig_name,
                'type': 'digital',
                'width': 1,
                'data': wave_data
            })
        else:
            wave_data = []
            for t, v in sig.values:
                wave_data.append([int(t * time_scale), v])
            signals_json.append({
                'name': sig_name,
                'type': 'bus',
                'width': sig.width,
                'data': wave_data,
                'format': 'hex'
            })
    
    return {
        'timescale': data.timescale,
        'time_scale': time_scale,
        'metadata': data.metadata,
        'signals': signals_json
    }


def waveform_to_html(vcd_path: str, output_path: Optional[str] = None) -> str:
    """Generate HTML viewer for VCD file"""
    json_data = vcd_to_json(vcd_path)
    
    html = '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>RTL Waveform Viewer</title>
    <script src="https://cdn.jsdelivr.net/npm/signal-widgets@1.0.0/dist/signal.min.js"></script>
    <style>
        body { 
            font-family: 'Segoe UI', Tahoma, sans-serif; 
            margin: 0; 
            background: #1a1a2e; 
            color: #eee; 
        }
        .header { 
            background: #16213e; 
            padding: 20px; 
            border-bottom: 2px solid #0f3460; 
        }
        .header h1 { margin: 0; font-size: 1.5em; }
        .header .meta { color: #888; font-size: 0.85em; margin-top: 5px; }
        .controls { 
            background: #16213e; 
            padding: 15px 20px; 
            display: flex; 
            gap: 15px; 
            flex-wrap: wrap;
        }
        .controls button { 
            background: #0f3460; 
            border: none; 
            color: #fff; 
            padding: 8px 16px; 
            border-radius: 4px; 
            cursor: pointer; 
        }
        .controls button:hover { background: #1a4a7a; }
        .controls input { padding: 8px; border-radius: 4px; border: 1px solid #333; background: #222; color: #fff; }
        #waveform-container { padding: 20px; }
        .signal-row { display: flex; border-bottom: 1px solid #333; }
        .signal-name { width: 200px; padding: 10px; background: #0f3460; }
        .signal-wave { flex: 1; min-height: 40px; background: #1a1a2e; position: relative; }
        .signal-bus-value { 
            position: absolute; 
            background: #0f3460; 
            padding: 2px 6px; 
            border-radius: 2px; 
            font-family: monospace; 
            font-size: 0.85em;
        }
        .time-ruler { 
            height: 30px; 
            background: #16213e; 
            position: relative; 
            margin-left: 200px;
        }
        .time-marker { 
            position: absolute; 
            font-size: 0.75em; 
            border-left: 1px solid #555; 
            padding-left: 4px; 
            height: 100%;
        }
        .zoom-info { color: #888; font-size: 0.85em; }
    </style>
</head>
<body>
    <div class="header">
        <h1>RTL Waveform Viewer</h1>
        <div class="meta"></div>
    </div>
    <div class="controls">
        <button onclick="zoomIn()">Zoom In (+)</button>
        <button onclick="zoomOut()">Zoom Out (-)</button>
        <button onclick="resetView()">Reset View</button>
        <input type="text" id="search" placeholder="Filter signals..." onkeyup="filterSignals()">
        <span class="zoom-info">Scale: <span id="zoom-level">1x</span></span>
    </div>
    <div class="time-ruler" id="time-ruler"></div>
    <div id="waveform-container"></div>
    
    <script>
        const waveformData = ''' + json.dumps(json_data, indent=2) + ''';
        
        let currentZoom = 1;
        const container = document.getElementById('waveform-container');
        const ruler = document.getElementById('time-ruler');
        
        function renderWaveforms() {
            container.innerHTML = '';
            ruler.innerHTML = '';
            
            const signals = waveformData.signals;
            const timeScale = waveformData.time_scale || 1;
            
            let maxTime = 0;
            signals.forEach(sig => {
                if (sig.data && sig.data.length > 0) {
                    const last = sig.data[sig.data.length - 1];
                    if (last[0] > maxTime) maxTime = last[0];
                }
            });
            
            const pixelsPerUnit = currentZoom * 2;
            const totalWidth = maxTime * pixelsPerUnit;
            
            for (let t = 0; t <= maxTime; t += Math.ceil(maxTime / 10)) {
                const marker = document.createElement('div');
                marker.className = 'time-marker';
                marker.style.left = (t * pixelsPerUnit) + 'px';
                marker.textContent = t + waveformData.timescale;
                ruler.appendChild(marker);
            }
            
            signals.forEach((signal, idx) => {
                const row = document.createElement('div');
                row.className = 'signal-row';
                row.dataset.name = signal.name.toLowerCase();
                
                const nameDiv = document.createElement('div');
                nameDiv.className = 'signal-name';
                nameDiv.textContent = signal.name;
                row.appendChild(nameDiv);
                
                const waveDiv = document.createElement('div');
                waveDiv.className = 'signal-wave';
                waveDiv.style.width = totalWidth + 'px';
                
                if (signal.type === 'digital' && signal.width === 1) {
                    let lastX = 0;
                    let lastVal = 0;
                    
                    signal.data.forEach((point, i) => {
                        const [time, value] = point;
                        
                        const rect = document.createElement('div');
                        rect.style.position = 'absolute';
                        rect.style.left = lastX + 'px';
                        rect.style.width = ((time - lastX/pixelsPerUnit) * pixelsPerUnit) + 'px';
                        rect.style.top = value ? '5px' : '25px';
                        rect.style.height = '10px';
                        rect.style.background = value ? '#4CAF50' : '#f44336';
                        waveDiv.appendChild(rect);
                        
                        lastX = time * pixelsPerUnit;
                        lastVal = value;
                    });
                    
                    const rect = document.createElement('div');
                    rect.style.position = 'absolute';
                    rect.style.left = lastX + 'px';
                    rect.style.width = (totalWidth - lastX) + 'px';
                    rect.style.top = lastVal ? '5px' : '25px';
                    rect.style.height = '10px';
                    rect.style.background = lastVal ? '#4CAF50' : '#f44336';
                    waveDiv.appendChild(rect);
                    
                } else {
                    signal.data.forEach((point, i) => {
                        const [time, value] = point;
                        const x = time * pixelsPerUnit;
                        
                        const valDiv = document.createElement('div');
                        valDiv.className = 'signal-bus-value';
                        valDiv.style.left = x + 'px';
                        valDiv.style.top = '10px';
                        valDiv.textContent = '0x' + value.toString(16).toUpperCase().padStart(Math.ceil(signal.width/4), '0');
                        waveDiv.appendChild(valDiv);
                    });
                }
                
                row.appendChild(waveDiv);
                container.appendChild(row);
            });
        }
        
        function zoomIn() {
            currentZoom = Math.min(currentZoom * 2, 16);
            document.getElementById('zoom-level').textContent = currentZoom + 'x';
            renderWaveforms();
        }
        
        function zoomOut() {
            currentZoom = Math.max(currentZoom / 2, 0.25);
            document.getElementById('zoom-level').textContent = currentZoom + 'x';
            renderWaveforms();
        }
        
        function resetView() {
            currentZoom = 1;
            document.getElementById('zoom-level').textContent = '1x';
            renderWaveforms();
        }
        
        function filterSignals() {
            const search = document.getElementById('search').value.toLowerCase();
            const rows = container.querySelectorAll('.signal-row');
            rows.forEach(row => {
                const name = row.dataset.name;
                row.style.display = (!search || name.includes(search)) ? 'flex' : 'none';
            });
        }
        
        document.addEventListener('DOMContentLoaded', renderWaveforms);
    </script>
</body>
</html>'''
    
    if output_path:
        Path(output_path).write_text(html)
        log.info(f"Waveform HTML written to {output_path}")
    
    return html


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python waveform_viewer.py <vcd_file> [output_html]")
        sys.exit(1)
    
    vcd_file = sys.argv[1]
    output = sys.argv[2] if len(sys.argv) > 2 else vcd_file.replace('.vcd', '_waveform.html')
    
    html = waveform_to_html(vcd_file, output)
    print(f"Generated: {output}")
