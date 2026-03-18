# file_manager.py
"""File management for RTL Assistant"""

import os
import json
import datetime


class FileManager:
    """Handle all file operations"""

    def __init__(self, base_dir="."):
        self.base_dir = base_dir
        self.outputs_dir = os.path.join(base_dir, "outputs")
        self.data_dir = os.path.join(base_dir, "data")
        self.logs_dir = os.path.join(base_dir, "logs")

        for d in [self.outputs_dir, self.data_dir, self.logs_dir]:
            os.makedirs(d, exist_ok=True)

    def save_design(self, design_data, verilog_code):
        """Save design to file system. Returns path to saved design."""
        module_name = design_data.get("module_name", "unknown")
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

        design_dir = os.path.join(self.outputs_dir, f"{module_name}_{timestamp}")
        os.makedirs(design_dir, exist_ok=True)

        verilog_path = os.path.join(design_dir, f"{module_name}.v")
        with open(verilog_path, 'w') as f:
            f.write(verilog_code)

        json_path = os.path.join(design_dir, "spec.json")
        with open(json_path, 'w') as f:
            json.dump(design_data, f, indent=2)

        readme_path = os.path.join(design_dir, "README.md")
        readme = self._create_readme(design_data)
        with open(readme_path, 'w') as f:
            f.write(readme)

        self._add_to_history(design_data, design_dir)
        return design_dir

    def _create_readme(self, design_data):
        ops = ', '.join(design_data.get('operations', []))
        return f"""# {design_data.get('module_name', 'Design')}

Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Specifications
- Component: {design_data.get('component', 'unknown')}
- Bit Width: {design_data.get('bit_width', 8)}
- Has Clock: {design_data.get('has_clock', False)}
- Has Reset: {design_data.get('has_reset', False)}
- Operations: {ops}
"""

    def _add_to_history(self, design_data, design_dir):
        history_file = os.path.join(self.data_dir, "history.json")
        history = []
        if os.path.exists(history_file):
            with open(history_file, 'r') as f:
                history = json.load(f)

        entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "module_name": design_data.get("module_name"),
            "component": design_data.get("component"),
            "bit_width": design_data.get("bit_width"),
            "description": design_data.get("original", "")[:50],
            "location": design_dir
        }
        history.append(entry)

        with open(history_file, 'w') as f:
            json.dump(history[-50:], f, indent=2)

    def get_history(self):
        history_file = os.path.join(self.data_dir, "history.json")
        if os.path.exists(history_file):
            with open(history_file, 'r') as f:
                return json.load(f)
        return []

    def log_activity(self, action, details):
        log_file = os.path.join(
            self.logs_dir,
            f"activity_{datetime.datetime.now().strftime('%Y%m%d')}.log"
        )
        timestamp = datetime.datetime.now().isoformat()
        with open(log_file, 'a') as f:
            f.write(f"[{timestamp}] {action}: {details}\n")

    def load_config(self):
        config_file = os.path.join(self.base_dir, "config.json")
        default_config = {
            "default_bit_width": 8,
            "save_location": "outputs",
            "create_testbench": True,
            "add_comments": True,
            "recent_designs": 10
        }

        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                return json.load(f)
        else:
            with open(config_file, 'w') as f:
                json.dump(default_config, f, indent=2)
            return default_config
