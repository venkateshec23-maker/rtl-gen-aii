"""
Batch Processing Engine for RTL-Gen AI (Phase B Implementation)
Safely runs Verilog generation and logic validation via ThreadPoolExecutor.
Restricts to MAX_WORKERS=2 by default to prevent Docker OOM and system crashes.
"""

import sys
import time
import argparse
from typing import List, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed
from verilog_generator import generate_and_validate

# Default batch configuration if none provided
DEFAULT_BATCH = [
    {"desc": "4-bit carry lookahead adder", "name": "cla_4bit"},
    {"desc": "8-bit up/down counter with async reset", "name": "counter_8bit"},
    {"desc": "4-to-1 multiplexer using behavioral logic", "name": "mux4to1"}
]

def process_batch(designs: List[Dict], max_workers: int = 2, llm_provider: str = 'groq') -> List[Dict]:
    """
    Run generate_and_validate for multiple designs in parallel.
    """
    import time
    if llm_provider == "groq" and max_workers > 1:
        print("[WARNING] Groq Free-Tier enforces tight Tokens-Per-Minute restrictions (12,000 TPM).")
        print("          Forcing max_workers=1 to prevent HTTP 429 Rate Limits.")
        max_workers = 1
        
    print(f"[BATCH] Starting Parallel Batch Execution")
    print(f"   Workers: {max_workers} (Restricted to protect system RAM)")
    print(f"   Provider: {llm_provider}")
    print(f"   Designs: {len(designs)}\n")
    
    results = []
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        futures = {}
        for idx, design in enumerate(designs):
            # Using index to preserve output order
            # Add stagger to prevent rapid-fire TPM spikes even globally
            time.sleep(idx * 1.5)
            f = executor.submit(
                generate_and_validate,
                description=design['desc'],
                module_name=design['name'],
                llm_provider=llm_provider,
                max_retries=2
            )
            futures[f] = (idx, design['name'])
            
        # Collect results securely
        for future in as_completed(futures):
            idx, name = futures[future]
            try:
                result_obj = future.result()
                results.append((idx, name, result_obj))
                
                status = "[PASS]" if result_obj.get("status") == "READY_FOR_PIPELINE" else "[FAIL]"
                print(f"{status} Thread finished processing: {name}")
            except Exception as e:
                print(f"[FAIL] Exception processing {name}: {e}")
                results.append((idx, name, {"status": "PYTHON_ERROR", "error": str(e)}))

    # Sort results by execution schedule to retain sanity
    results.sort(key=lambda x: x[0])
    
    print("\n" + "="*50)
    print("BATCH EXECUTION REPORT")
    print("="*50)
    
    success_count = 0
    for idx, name, result in results:
        status_text = result.get('status', 'FAIL')
        if status_text == "READY_FOR_PIPELINE":
            success_count += 1
            print(f"  [PASS] {name.ljust(15)} : PASSED -> Ready for OpenROAD")
        else:
            print(f"  [FAIL] {name.ljust(15)} : FAILED -> {result.get('error', 'Logic or Syntax Issue')}")
            
    elapsed = time.time() - start_time
    print(f"\nCompleted {len(designs)} designs in {elapsed:.1f}s.")
    print(f"Total Success: {success_count}/{len(designs)}")
    
    # We DO NOT automatically launch OpenROAD physical tracking to avoid
    # melting the user's laptop. Return the results for external hooks if needed.
    return [r[2] for r in results]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Parallel RTL Batch Generator")
    parser.add_argument("--workers", type=int, default=2, help="Max parallel threads")
    parser.add_argument("--provider", type=str, default="groq", help="LLM Provider")
    args = parser.parse_args()
    
    process_batch(DEFAULT_BATCH, max_workers=args.workers, llm_provider=args.provider)
