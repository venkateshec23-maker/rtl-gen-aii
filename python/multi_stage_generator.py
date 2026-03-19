"""
Multi-Stage Generation Pipeline

Implements sophisticated multi-stage code generation with:
1. Specification extraction
2. Architecture planning
3. Code generation
4. Verification
5. Refinement

Usage:
    from python.multi_stage_generator import MultiStageGenerator
    
    generator = MultiStageGenerator()
    result = generator.generate_multi_stage(description)
"""

import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

from python.llm_client import LLMClient
from python.advanced_prompt_builder import AdvancedPromptBuilder
from python.rag_system import RAGSystem


class MultiStageGenerator:
    """Multi-stage code generation pipeline."""
    
    def __init__(self, use_mock: bool = False):
        """Initialize multi-stage generator."""
        self.llm_client = LLMClient(use_mock=use_mock)
        self.prompt_builder = AdvancedPromptBuilder()
        self.rag_system = RAGSystem()
        
        # Stage tracking
        self.current_stage = None
        self.stage_results = {}
    
    def stage_1_specification_extraction(
        self,
        description: str
    ) -> Dict:
        """
        Stage 1: Extract detailed specification from description.
        
        Args:
            description: Natural language description
            
        Returns:
            dict: Extracted specification
        """
        self.current_stage = 'specification_extraction'
        print(f"\n[Stage 1/5] Extracting specification...")
        
        prompt = f"""Analyze this hardware design request and extract a detailed specification.

Request: {description}

Please provide:
1. Module name (suggested)
2. Design type (combinational/sequential/FSM/memory)
3. Input ports (name, bit-width, purpose)
4. Output ports (name, bit-width, purpose)
5. Key functionality requirements
6. Constraints or special requirements
7. Potential edge cases to consider

Format your response as JSON with these fields:
- module_name
- design_type
- inputs (array of {{name, width, purpose}})
- outputs (array of {{name, width, purpose}})
- functionality (array of requirements)
- constraints (array of constraints)
- edge_cases (array of cases)

Respond with JSON only, no markdown.
"""
        
        try:
            response = self.llm_client.generate(prompt, max_tokens=1000)
            
            # Handle dict response (from mock)
            if isinstance(response, dict):
                spec = response
            else:
                # Parse JSON response
                # Remove markdown if present
                response_clean = response.strip()
                if response_clean.startswith('```'):
                    # Extract JSON from markdown code block
                    lines = response_clean.split('\n')
                    response_clean = '\n'.join(lines[1:-1])
                
                spec = json.loads(response_clean)
            
            self.stage_results['specification'] = spec
            
            print(f"  [OK] Extracted specification for: {spec.get('module_name', 'unknown')}")
            print(f"  [OK] Design type: {spec.get('design_type', 'unknown')}")
            print(f"  [OK] Inputs: {len(spec.get('inputs', []))}, Outputs: {len(spec.get('outputs', []))}")
            
            return spec
            
        except Exception as e:
            print(f"  [FAIL] Specification extraction failed: {e}")
            
            # Fallback: basic spec
            return {
                'module_name': 'design_module',
                'design_type': 'unknown',
                'inputs': [],
                'outputs': [],
                'functionality': [description],
                'constraints': [],
                'edge_cases': [],
            }
    
    def stage_2_architecture_planning(
        self,
        specification: Dict
    ) -> Dict:
        """
        Stage 2: Plan architecture and implementation strategy.
        
        Args:
            specification: Extracted specification
            
        Returns:
            dict: Architecture plan
        """
        self.current_stage = 'architecture_planning'
        print(f"\n[Stage 2/5] Planning architecture...")
        
        # Retrieve similar designs
        similar_designs = self.rag_system.retrieve_relevant_examples(
            query=specification.get('module_name', ''),
            top_k=2
        )
        
        similar_info = ""
        if similar_designs:
            similar_info = "\n\nSimilar designs for reference:\n"
            for design in similar_designs:
                similar_info += f"- {design['name']}: {design['description']}\n"
        
        prompt = f"""Plan the architecture for this hardware design.

Specification:
{json.dumps(specification, indent=2)}
{similar_info}

Provide an implementation plan including:
1. Overall architecture approach
2. Main components/blocks needed
3. Data flow between components
4. Timing considerations (if sequential)
5. Implementation strategy (coding approach)
6. Potential challenges and solutions

Format as JSON with:
- approach (description)
- components (array of component descriptions)
- data_flow (description)
- timing_notes (description or null)
- strategy (description)
- challenges (array of challenges)

Respond with JSON only.
"""
        
        try:
            response = self.llm_client.generate(prompt, max_tokens=800)
            
            # Handle dict response (from mock)
            if isinstance(response, dict):
                architecture = response
            else:
                # Parse response
                response_clean = response.strip()
                if response_clean.startswith('```'):
                    lines = response_clean.split('\n')
                    response_clean = '\n'.join(lines[1:-1])
                
                architecture = json.loads(response_clean)
            
            self.stage_results['architecture'] = architecture
            
            print(f"  [OK] Architecture approach: {architecture.get('approach', 'N/A')[:60]}...")
            print(f"  [OK] Components identified: {len(architecture.get('components', []))}")
            
            return architecture
            
        except Exception as e:
            print(f"  [FAIL] Architecture planning failed: {e}")
            
            # Fallback
            return {
                'approach': 'Standard implementation',
                'components': [],
                'data_flow': 'Inputs -> Logic -> Outputs',
                'timing_notes': None,
                'strategy': 'Direct implementation',
                'challenges': [],
            }
    
    def stage_3_code_generation(
        self,
        specification: Dict,
        architecture: Dict
    ) -> Dict:
        """
        Stage 3: Generate RTL code based on spec and architecture.
        
        Args:
            specification: Specification from stage 1
            architecture: Architecture from stage 2
            
        Returns:
            dict: Generated code
        """
        self.current_stage = 'code_generation'
        print(f"\n[Stage 3/5] Generating RTL code...")
        
        # Build comprehensive prompt
        prompt = self.prompt_builder.build_context_aware_prompt(
            description=str(specification.get('functionality', [''])[0]),
            design_type=specification.get('design_type'),
            include_examples=True
        )
        
        # Add specification and architecture details
        prompt += f"""

## Detailed Specification
{json.dumps(specification, indent=2)}

## Architecture Plan
{json.dumps(architecture, indent=2)}

Now generate the complete, synthesizable Verilog code following this specification and architecture.
Include proper module declaration, all required logic, and comprehensive comments.
"""
        
        try:
            response = self.llm_client.generate(prompt, max_tokens=2000)
            
            # Extract code
            from python.code_extractor import CodeExtractor
            extractor = CodeExtractor()
            
            # Handle dict response (from mock)
            if isinstance(response, dict):
                extracted = response
            else:
                extracted = extractor.extract(response)
            
            if not extracted['rtl_code']:
                raise ValueError("No RTL code found in response")
            
            self.stage_results['code'] = extracted
            
            print(f"  [OK] RTL code generated: {len(extracted['rtl_code'].split(chr(10)))} lines")
            if extracted['testbench_code']:
                print(f"  [OK] Testbench generated: {len(extracted['testbench_code'].split(chr(10)))} lines")
            
            return extracted
            
        except Exception as e:
            print(f"  [FAIL] Code generation failed: {e}")
            
            return {
                'rtl_code': '',
                'testbench_code': '',
                'module_name': specification.get('module_name', 'unknown'),
            }
    
    def stage_4_verification(
        self,
        code: Dict,
        specification: Dict
    ) -> Dict:
        """
        Stage 4: Verify generated code.
        
        Args:
            code: Generated code
            specification: Original specification
            
        Returns:
            dict: Verification results
        """
        self.current_stage = 'verification'
        print(f"\n[Stage 4/5] Verifying code...")
        
        from python.verification_engine import VerificationEngine
        verifier = VerificationEngine()
        
        try:
            results = verifier.verify(
                rtl_code=code['rtl_code'],
                testbench_code=code['testbench_code'],
                module_name=code['module_name']
            )
            
            self.stage_results['verification'] = results
            
            if results['passed']:
                print(f"  [OK] Verification PASSED")
            else:
                print(f"  [FAIL] Verification FAILED: {results.get('message', 'Unknown error')}")
            
            return results
            
        except Exception as e:
            print(f"  [FAIL] Verification error: {e}")
            
            return {
                'passed': False,
                'message': str(e),
            }
    
    def stage_5_refinement(
        self,
        code: Dict,
        verification: Dict,
        specification: Dict
    ) -> Dict:
        """
        Stage 5: Refine code if verification failed.
        
        Args:
            code: Generated code
            verification: Verification results
            specification: Original specification
            
        Returns:
            dict: Refined code or original if passed
        """
        self.current_stage = 'refinement'
        
        if verification.get('passed'):
            print(f"\n[Stage 5/5] Refinement not needed (verification passed)")
            return code
        
        print(f"\n[Stage 5/5] Refining code...")
        
        # Build refinement prompt
        error_msg = verification.get('message', 'Unknown error')
        
        prompt = self.prompt_builder.build_refinement_prompt(
            original_description=str(specification.get('functionality', [''])[0]),
            original_code=code['rtl_code'],
            error_message=error_msg,
            attempt_number=2
        )
        
        try:
            response = self.llm_client.generate(prompt, max_tokens=2000)
            
            # Extract refined code
            from python.code_extractor import CodeExtractor
            extractor = CodeExtractor()
            
            refined = extractor.extract(response)
            
            if refined['rtl_code']:
                print(f"  [OK] Code refined")
                self.stage_results['refined_code'] = refined
                return refined
            else:
                print(f"  [FAIL] Refinement failed to generate valid code")
                return code
            
        except Exception as e:
            print(f"  [FAIL] Refinement failed: {e}")
            return code
    
    def generate_multi_stage(
        self,
        description: str,
        max_refinements: int = 1
    ) -> Dict:
        """
        Execute complete multi-stage generation pipeline.
        
        Args:
            description: Design description
            max_refinements: Maximum refinement attempts
            
        Returns:
            dict: Complete generation results
        """
        print("=" * 70)
        print("MULTI-STAGE GENERATION PIPELINE")
        print("=" * 70)
        print(f"\nDescription: {description}")
        
        start_time = datetime.now()
        
        # Stage 1: Specification Extraction
        specification = self.stage_1_specification_extraction(description)
        
        # Stage 2: Architecture Planning
        architecture = self.stage_2_architecture_planning(specification)
        
        # Stage 3: Code Generation
        code = self.stage_3_code_generation(specification, architecture)
        
        if not code['rtl_code']:
            return {
                'success': False,
                'message': 'Code generation failed',
                'stages': self.stage_results,
            }
        
        # Stage 4: Verification
        verification = self.stage_4_verification(code, specification)
        
        # Stage 5: Refinement (if needed)
        final_code = code
        refinement_count = 0
        
        while not verification.get('passed') and refinement_count < max_refinements:
            refinement_count += 1
            print(f"\nRefinement attempt {refinement_count}/{max_refinements}")
            
            final_code = self.stage_5_refinement(code, verification, specification)
            verification = self.stage_4_verification(final_code, specification)
            
            if verification.get('passed'):
                break
        
        # Calculate total time
        duration = (datetime.now() - start_time).total_seconds()
        
        print("\n" + "=" * 70)
        print("PIPELINE COMPLETE")
        print("=" * 70)
        print(f"Success: {verification.get('passed', False)}")
        print(f"Duration: {duration:.1f}s")
        print(f"Refinements: {refinement_count}")
        print("=" * 70)
        
        return {
            'success': verification.get('passed', False),
            'rtl_code': final_code['rtl_code'],
            'testbench_code': final_code['testbench_code'],
            'module_name': final_code['module_name'],
            'specification': specification,
            'architecture': architecture,
            'verification': verification,
            'refinement_count': refinement_count,
            'duration_seconds': duration,
            'stages': self.stage_results,
        }


# ============================================================================
# SELF-TEST
# ============================================================================

if __name__ == "__main__":
    print("Multi-Stage Generator Self-Test\n")
    
    generator = MultiStageGenerator(use_mock=True)
    
    # Test with sample description
    description = "8-bit counter with synchronous reset and enable"
    
    result = generator.generate_multi_stage(description)
    
    if result['success']:
        print("\n[OK] Multi-stage generation successful")
        print(f"\nGenerated module: {result['module_name']}")
        print(f"Code length: {len(result['rtl_code'])} characters")
    else:
        print("\n[FAIL] Multi-stage generation failed")
    
    print("\n[OK] Self-test complete")
