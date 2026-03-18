# design_parser.py
"""Design description parser for RTL Assistant"""

import re


class DesignParser:
    """Parse natural language design descriptions"""

    def __init__(self):
        self.components = {
            "adder": ["adder", "add"],
            "counter": ["counter", "count"],
            "alu": ["alu", "arithmetic logic unit"],
            "multiplexer": ["mux", "multiplexer"],
            "register": ["register", "reg", "flip-flop"],
            "subtractor": ["subtractor", "subtract"],
            "multiplier": ["multiplier", "multiply"],
            "divider": ["divider", "divide"]
        }

        self.operations = {
            "ADD": ["add", "addition"],
            "SUB": ["sub", "subtract", "subtraction"],
            "AND": ["and", "bitwise and"],
            "OR": ["or", "bitwise or"],
            "XOR": ["xor", "exclusive or"],
            "NOT": ["not", "invert"],
            "SHL": ["shift left", "shl"],
            "SHR": ["shift right", "shr"]
        }

    def parse(self, description):
        """Extract design information from description"""
        desc = description.lower()

        result = {
            "original": description,
            "component": self._extract_component(desc),
            "bit_width": self._extract_bit_width(desc),
            "has_clock": self._detect_clock(desc),
            "has_reset": self._detect_reset(desc),
            "operations": self._extract_operations(desc),
            "confidence": 0.8
        }

        if result["component"] == "unknown":
            result["confidence"] -= 0.3
        if result["bit_width"] is None:
            result["bit_width"] = 8
            result["confidence"] -= 0.2

        return result

    def _extract_component(self, desc):
        """Extract component type from description"""
        for comp, keywords in self.components.items():
            for kw in keywords:
                if kw in desc:
                    return comp
        return "unknown"

    def _extract_bit_width(self, desc):
        """Extract bit width using regex"""
        patterns = [
            r'(\d+)[-\s]bit',
            r'bit[-\s]width[:\s]*(\d+)',
            r'width[:\s]*(\d+)',
            r'(\d+)\s*bits?'
        ]

        for pattern in patterns:
            match = re.search(pattern, desc)
            if match:
                width = int(match.group(1))
                if 1 <= width <= 64:
                    return width
        return 8

    def _detect_clock(self, desc):
        """Detect if design has clock"""
        return any(word in desc for word in ["clock", "clk", "synchronous"])

    def _detect_reset(self, desc):
        """Detect if design has reset"""
        return any(word in desc for word in ["reset", "rst", "initialize"])

    def _extract_operations(self, desc):
        """Extract operations (for ALU)"""
        found = []
        for op, keywords in self.operations.items():
            for kw in keywords:
                if kw in desc:
                    found.append(op)
                    break
        return found

    def suggest_module_name(self, parsed):
        """Suggest a module name based on parsed data"""
        comp = parsed["component"]
        width = parsed["bit_width"]
        if comp == "unknown":
            return f"design_{width}bit"
        return f"{comp}_{width}bit"
