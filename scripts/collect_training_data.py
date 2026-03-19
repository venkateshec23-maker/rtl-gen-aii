"""
Training Data Collection Script

Generates and validates designs for training dataset.

Usage: python scripts/collect_training_data.py [--count 50] [--category combinational]
"""

import argparse
from pathlib import Path
import time
import os
import sys

# Ensure project root is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from python.rtl_generator import RTLGenerator
from python.dataset_manager import DatasetManager
from python.verification_engine import VerificationEngine


# Comprehensive design templates
DESIGN_TEMPLATES = {
    'combinational': [
        # Adders
        "{n}-bit adder",
        "{n}-bit adder with carry",
        "{n}-bit full adder",
        "{n}-bit carry lookahead adder",
        "{n}-bit carry select adder",
        
        # Multiplexers
        "2-to-1 multiplexer {n}-bit",
        "4-to-1 multiplexer {n}-bit",
        "8-to-1 multiplexer {n}-bit",
        "16-to-1 multiplexer {n}-bit",
        
        # Logic gates
        "{n}-bit AND gate",
        "{n}-bit OR gate",
        "{n}-bit XOR gate",
        "{n}-bit NAND gate",
        "{n}-bit NOR gate",
        
        # Comparators
        "{n}-bit comparator",
        "{n}-bit magnitude comparator",
        "{n}-bit equality comparator",
        
        # Encoders/Decoders
        "2-to-4 decoder",
        "3-to-8 decoder",
        "4-to-2 priority encoder",
        "8-to-3 priority encoder",
        
        # Arithmetic
        "{n}-bit subtractor",
        "{n}-bit incrementer",
        "{n}-bit decrementer",
        
        # Parity
        "{n}-bit parity generator",
        "{n}-bit parity checker",
    ],
    
    'sequential': [
        # Counters
        "{n}-bit counter",
        "{n}-bit up counter with reset",
        "{n}-bit down counter with reset",
        "{n}-bit up-down counter with reset and enable",
        "{n}-bit counter with load",
        "{n}-bit counter with parallel load",
        "{n}-bit ring counter",
        "{n}-bit Johnson counter",
        "{n}-bit gray counter",
        
        # Registers
        "{n}-bit register",
        "{n}-bit register with enable",
        "{n}-bit register with reset",
        "{n}-bit register with load enable",
        
        # Shift registers
        "{n}-bit shift register",
        "{n}-bit left shift register",
        "{n}-bit right shift register",
        "{n}-bit universal shift register",
        "{n}-bit LFSR (Linear Feedback Shift Register)",
        
        # Flip-flops
        "D flip-flop with reset",
        "D flip-flop with enable",
        "T flip-flop",
        "JK flip-flop",
        "SR flip-flop",
    ],
    
    'fsm': [
        # Simple FSMs
        "2-state FSM with enable",
        "3-state traffic light controller",
        "4-state sequence detector",
        "Vending machine controller (2 states)",
        "Elevator controller (3 floors)",
        
        # Pattern detectors
        "1010 sequence detector (overlapping)",
        "1010 sequence detector (non-overlapping)",
        "1101 sequence detector",
        "Arbitrary sequence detector",
        
        # Controllers
        "Simple traffic light controller",
        "Pedestrian crossing controller",
        "Washing machine controller",
        "Microwave controller",
    ],
    
    'memory': [
        # FIFOs
        "8-entry FIFO {n}-bit",
        "16-entry FIFO {n}-bit",
        "Synchronous FIFO {n}-bit",
        "Asynchronous FIFO {n}-bit",
        
        # RAM/ROM
        "16x{n} single-port RAM",
        "32x{n} single-port RAM",
        "64x{n} single-port RAM",
        "16x{n} dual-port RAM",
        
        # Buffers
        "Circular buffer {n}-bit",
        "Ring buffer {n}-bit",
    ],
    
    'arithmetic': [
        # ALUs
        "4-bit ALU with 4 operations",
        "8-bit ALU with ADD SUB AND OR",
        "8-bit ALU with shift operations",
        "16-bit ALU with 8 operations",
        
        # Multipliers
        "4x4 multiplier",
        "8x8 multiplier",
        "4-bit array multiplier",
        "8-bit booth multiplier",
        
        # Dividers
        "8-bit divider",
        "16-bit divider",
        
        # Complex arithmetic
        "{n}-bit barrel shifter",
        "{n}-bit rotating shifter",
    ],
    
    'control': [
        # Controllers
        "UART transmitter controller",
        "UART receiver controller",
        "SPI master controller",
        "I2C master controller",
        
        # Arbiters
        "2-way arbiter",
        "4-way round-robin arbiter",
        "Priority arbiter",
        
        # Bus controllers
        "Simple bus controller",
        "Memory controller",
    ]
}


class TrainingDataCollector:
    """Collect and validate training data."""
    
    def __init__(self, use_mock: bool = True):
        """Initialize collector."""
        self.generator = RTLGenerator(use_mock=use_mock, enable_verification=True)
        self.dataset_manager = DatasetManager()
        self.verifier = VerificationEngine()
        
        self.stats = {
            'attempted': 0,
            'successful': 0,
            'failed': 0,
            'verified': 0,
        }
    
    def collect_category(
        self,
        category: str,
        count: int = 20,
        bit_widths: list = [4, 8, 16]
    ):
        """
        Collect designs for a specific category.
        
        Args:
            category: Design category
            count: Number of designs to generate
            bit_widths: Bit widths to use
        """
        if category not in DESIGN_TEMPLATES:
            print(f"❌ Unknown category: {category}")
            return
        
        templates = DESIGN_TEMPLATES[category]
        
        print(f"\n{'='*70}")
        print(f"COLLECTING: {category.upper()} ({count} designs)")
        print(f"{'='*70}\n")
        
        collected = 0
        attempts = 0
        
        while collected < count and attempts < count * 2:
            # Select template
            template = templates[attempts % len(templates)]
            
            # Select bit width
            bit_width = bit_widths[attempts % len(bit_widths)]
            
            # Format description
            description = template.format(n=bit_width)
            
            print(f"\n[{collected+1}/{count}] Generating: {description}")
            
            try:
                # Generate design
                result = self.generator.generate(description, verify=True)
                
                self.stats['attempted'] += 1
                attempts += 1
                
                if not result.get('success'):
                    print(f"  ✗ Generation failed: {result.get('message', 'Unknown error')}")
                    self.stats['failed'] += 1
                    continue
                
                # Check verification
                verified = False
                if result.get('verification'):
                    verified = result['verification'].get('passed', False)
                    if verified:
                        self.stats['verified'] += 1
                
                # Add to dataset
                design_id = self.dataset_manager.add_design(
                    description=description,
                    rtl_code=result['rtl_code'],
                    testbench=result['testbench_code'],
                    verification_results=result.get('verification'),
                    metadata={
                        'module_name': result['module_name'],
                        'component_type': result.get('metadata', {}).get('component_type', 'unknown'),
                    }
                )
                
                self.stats['successful'] += 1
                collected += 1
                
                status = "✓ VERIFIED" if verified else "⚠ NOT VERIFIED"
                print(f"  {status} - Added to dataset")
                
            except Exception as e:
                print(f"  ✗ Error: {e}")
                import traceback
                traceback.print_exc()
                self.stats['failed'] += 1
                attempts += 1
            
            # Small delay to avoid rate limiting
            time.sleep(0.5)
        
        print(f"\n{'='*70}")
        print(f"Category complete: {collected}/{count} designs collected")
        print(f"{'='*70}\n")
    
    def collect_all_categories(self, designs_per_category: int = 20):
        """Collect designs for all categories."""
        print("\n" + "="*70)
        print("COLLECTING COMPLETE TRAINING DATASET")
        print("="*70)
        
        for category in DESIGN_TEMPLATES.keys():
            self.collect_category(category, designs_per_category)
            
            # Print progress
            print(f"\nProgress: {self.stats['successful']}/{self.stats['attempted']} successful")
            time.sleep(1)
        
        # Final statistics
        print("\n" + "="*70)
        print("COLLECTION COMPLETE")
        print("="*70)
        print(f"Attempted: {self.stats['attempted']}")
        print(f"Successful: {self.stats['successful']}")
        print(f"Failed: {self.stats['failed']}")
        print(f"Verified: {self.stats['verified']}")
        print("="*70)
        
        # Show dataset statistics
        self.dataset_manager.print_statistics()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Collect training data')
    parser.add_argument('--count', type=int, default=20, help='Designs per category')
    parser.add_argument('--category', type=str, help='Specific category to collect')
    parser.add_argument('--mock', action='store_true', help='Use mock LLM')
    
    args = parser.parse_args()
    
    collector = TrainingDataCollector(use_mock=args.mock)
    
    if args.category:
        collector.collect_category(args.category, args.count)
    else:
        collector.collect_all_categories(args.count)


if __name__ == "__main__":
    main()
