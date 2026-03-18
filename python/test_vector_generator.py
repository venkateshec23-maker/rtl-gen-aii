"""
Test Vector Generator for RTL-Gen AI
Generates test vectors (input combinations) for different circuit types.

Features:
1. Exhaustive generation (small circuits)
2. Directed generation (specific cases)
3. Random generation (large circuits)
4. Corner case generation

Usage:
    generator = TestVectorGenerator()
    vectors = generator.generate(
        inputs=[Port('a', 'input', width=2), Port('b', 'input', width=2)],
        strategy='exhaustive'
    )
"""

import random
from typing import List, Dict, Any
from itertools import product

from python.port_analyzer import Port
from python.config import DEBUG_MODE


class TestVectorGenerator:
    """
    Generates test vectors for circuit testing.
    
    Strategies:
    - exhaustive: All combinations (small circuits)
    - directed: Specific important cases
    - random: Random sampling (large circuits)
    - corners: Boundary values only
    
    Usage:
        generator = TestVectorGenerator()
        vectors = generator.generate(inputs, strategy='exhaustive')
    """
    
    def __init__(self, debug: bool = None):
        """
        Initialize test vector generator.
        
        Args:
            debug: Enable debug output
        """
        self.debug = debug if debug is not None else DEBUG_MODE
        
        # Thresholds
        self.exhaustive_threshold = 16  # Max total input bits for exhaustive
        self.random_count = 100  # Number of random vectors
        
        if self.debug:
            print("TestVectorGenerator initialized")
    
    def generate(self, inputs: List[Port], strategy: str = 'auto') -> List[Dict]:
        """
        Generate test vectors.
        
        Args:
            inputs: List of input ports (excluding clock/reset)
            strategy: 'auto', 'exhaustive', 'directed', 'random', 'corners'
            
        Returns:
            list: Test vectors as list of dicts {port_name: value}
        """
        # Filter out clock and reset
        test_inputs = [p for p in inputs if not p.is_clock and not p.is_reset]
        
        if not test_inputs:
            return [{}]  # No inputs to test
        
        # Auto-select strategy
        if strategy == 'auto':
            total_bits = sum(p.width for p in test_inputs)
            if total_bits <= self.exhaustive_threshold:
                strategy = 'exhaustive'
            else:
                strategy = 'directed'  # Corners + random
        
        if self.debug:
            print(f"\nGenerating test vectors (strategy: {strategy})")
            print(f"  Test inputs: {[p.name for p in test_inputs]}")
        
        # Generate based on strategy
        if strategy == 'exhaustive':
            vectors = self._generate_exhaustive(test_inputs)
        elif strategy == 'directed':
            vectors = self._generate_directed(test_inputs)
        elif strategy == 'random':
            vectors = self._generate_random(test_inputs)
        elif strategy == 'corners':
            vectors = self._generate_corners(test_inputs)
        else:
            raise ValueError(f"Unknown strategy: {strategy}")
        
        if self.debug:
            print(f"  Generated {len(vectors)} test vectors")
        
        return vectors
    
    def _generate_exhaustive(self, inputs: List[Port]) -> List[Dict]:
        """Generate all possible combinations."""
        # Create ranges for each input
        ranges = []
        for port in inputs:
            max_val = (1 << port.width) - 1
            ranges.append(range(max_val + 1))
        
        # Generate all combinations
        vectors = []
        for combo in product(*ranges):
            vector = {}
            for port, value in zip(inputs, combo):
                vector[port.name] = value
            vectors.append(vector)
        
        return vectors
    
    def _generate_directed(self, inputs: List[Port]) -> List[Dict]:
        """Generate directed test cases (corners + random)."""
        vectors = []
        
        # Add corner cases
        vectors.extend(self._generate_corners(inputs))
        
        # Add random cases
        random_vectors = self._generate_random(inputs, count=50)
        vectors.extend(random_vectors)
        
        return vectors
    
    def _generate_random(self, inputs: List[Port], count: int = None) -> List[Dict]:
        """Generate random test vectors."""
        if count is None:
            count = self.random_count
        
        vectors = []
        for _ in range(count):
            vector = {}
            for port in inputs:
                max_val = (1 << port.width) - 1
                vector[port.name] = random.randint(0, max_val)
            vectors.append(vector)
        
        return vectors
    
    def _generate_corners(self, inputs: List[Port]) -> List[Dict]:
        """
        Generate corner cases.
        
        Corner cases:
        - All zeros
        - All max values
        - Each input at max, others at 0
        - Each input at 0, others at max
        - Mid-range values
        """
        vectors = []
        
        # All zeros
        vector_zeros = {p.name: 0 for p in inputs}
        vectors.append(vector_zeros)
        
        # All max
        vector_max = {p.name: (1 << p.width) - 1 for p in inputs}
        vectors.append(vector_max)
        
        # Each input at max, others at 0
        for i, port in enumerate(inputs):
            vector = {p.name: 0 for p in inputs}
            vector[port.name] = (1 << port.width) - 1
            vectors.append(vector)
        
        # Mid-range (if multi-bit)
        vector_mid = {}
        for port in inputs:
            if port.width > 1:
                vector_mid[port.name] = 1 << (port.width - 1)
            else:
                vector_mid[port.name] = 1
        if vector_mid:
            vectors.append(vector_mid)
        
        return vectors


# ============================================================================
# SELF-TEST
# ============================================================================

if __name__ == "__main__":
    print("Test Vector Generator Self-Test\n")
    print("=" * 70)
    
    generator = TestVectorGenerator(debug=True)
    
    # Test 1: Small inputs (exhaustive)
    print("\n1. Testing exhaustive (4-bit inputs):")
    print("-" * 70)
    
    inputs1 = [
        Port('a', 'input', width=2),
        Port('b', 'input', width=2),
    ]
    
    vectors1 = generator.generate(inputs1, strategy='exhaustive')
    print(f"\nGenerated {len(vectors1)} vectors")
    print("First 5 vectors:")
    for i, vec in enumerate(vectors1[:5]):
        print(f"  {i}: {vec}")
    
    # Test 2: Large inputs (directed)
    print("\n2. Testing directed (8-bit inputs):")
    print("-" * 70)
    
    inputs2 = [
        Port('a', 'input', width=8),
        Port('b', 'input', width=8),
    ]
    
    vectors2 = generator.generate(inputs2, strategy='directed')
    print(f"\nGenerated {len(vectors2)} vectors")
    print("Sample vectors:")
    for i in [0, 1, 2, -1]:
        print(f"  {vectors2[i]}")
    
    # Test 3: Corner cases
    print("\n3. Testing corners:")
    print("-" * 70)
    
    vectors3 = generator.generate(inputs2, strategy='corners')
    print(f"\nGenerated {len(vectors3)} corner cases:")
    for vec in vectors3:
        print(f"  {vec}")
    
    print("\n" + "=" * 70)
    print("Self-test complete!")
    print("=" * 70)
