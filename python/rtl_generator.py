"""
RTL Generator - Main Orchestration Class
Ties together all components into a single easy-to-use interface.

Usage:
    generator = RTLGenerator()
    result = generator.generate("8-bit adder")
    
    if result['success']:
        print(result['rtl_code'])
"""

from typing import Dict, Optional
from pathlib import Path

from python.input_processor import InputProcessor
from python.prompt_builder import PromptBuilder
from python.llm_client import LLMClient
from python.extraction_pipeline import ExtractionPipeline
from python.verification_engine import VerificationEngine
from python.error_handler import error_handler, RTLGenError, ErrorCategory
from python.config import DEBUG_MODE
from python.performance_monitor import PerformanceMonitor
from python.error_tracker import ErrorTracker
from python.learning_engine import LearningEngine


class RTLGenerator:
    """
    Main RTL generation interface.
    
    This is the primary class that users should interact with.
    It orchestrates all the components and handles errors gracefully.
    
    Usage:
        generator = RTLGenerator(use_mock=True)
        result = generator.generate("8-bit adder with carry")
        
        if result['success']:
            print(result['rtl_code'])
            print(result['testbench_code'])
        else:
            print(result['error'])
    """
    
    def __init__(self, use_mock: bool = False, api_key: Optional[str] = None,
                 enable_verification: bool = True, debug: bool = None,
                 enable_monitoring: bool = True, enable_learning: bool = True):
        """
        Initialize RTL Generator.
        
        Args:
            use_mock: Use mock LLM (no API costs)
            api_key: Anthropic API key (if not using mock)
            enable_verification: Run verification after generation
            debug: Enable debug output
            enable_monitoring: Enable performance monitoring
        """
        self.debug = debug if debug is not None else DEBUG_MODE
        self.enable_verification = enable_verification
        self.enable_monitoring = enable_monitoring
        
        # Initialize monitor
        if self.enable_monitoring:
            self.monitor = PerformanceMonitor()
        else:
            self.monitor = None
        
        # Initialize all components
        try:
            self.processor = InputProcessor(debug=self.debug)
            self.builder = PromptBuilder(debug=self.debug)
            self.client = LLMClient(use_mock=use_mock)
            self.extractor = ExtractionPipeline(debug=self.debug)
            
            if self.enable_verification:
                self.verifier = VerificationEngine(debug=self.debug)
            
            # Learning components
            self.enable_learning = enable_learning
            if enable_learning:
                self.error_tracker = ErrorTracker()
                self.learning_engine = LearningEngine()
        
        except Exception as e:
            raise RTLGenError(
                "Failed to initialize RTL Generator",
                ErrorCategory.SYSTEM_ERROR,
                {'original_error': str(e)}
            )
        
        if self.debug:
            print("RTLGenerator initialized")
            print(f"  Mock LLM: {use_mock}")
            print(f"  Verification: {enable_verification}")
    
    def generate(self, description: str, verify: Optional[bool] = None) -> Dict:
        """Generate RTL code from description."""
        
        if self.monitor:
            with self.monitor.measure("total_generation"):
                return self._generate_with_monitoring(description, verify)
        else:
            return self._generate_without_monitoring(description, verify)

    def _generate_with_monitoring(self, description: str, verify: Optional[bool] = None) -> Dict:
        """Generate with performance monitoring."""
        if verify is None:
            verify = self.enable_verification
        
        try:
            # Step 1: Parse input
            with self.monitor.measure("input_parsing"):
                parsed = self._parse_input(description)
                self.monitor.increment("inputs_parsed")
            
            # Step 2: Generate code
            with self.monitor.measure("code_generation"):
                generation = self._generate_code(parsed)
                self.monitor.increment("codes_generated")
            
            # Step 3: Verify (if enabled)
            verification = None
            if verify:
                with self.monitor.measure("verification"):
                    verification = self._verify_code(
                        generation['rtl_code'],
                        generation['testbench_code'],
                        generation['module_name']
                    )
                    self.monitor.increment("verifications_run")
            
            # Combine results
            result = {
                'success': True,
                'module_name': generation['module_name'],
                'rtl_code': generation['rtl_code'],
                'testbench_code': generation['testbench_code'],
                'file_paths': generation.get('file_paths', {}),
                'warnings': generation.get('warnings', []),
                'verification': verification,
                'metadata': {
                    'description': description,
                    'component_type': parsed.get('component_type'),
                    'bit_width': parsed.get('bit_width'),
                },
            }
            
            return result
        
        except RTLGenError as e:
            self.monitor.increment("errors")
            return error_handler.handle_error(e, "Generation")
        
        except Exception as e:
            self.monitor.increment("errors")
            return error_handler.handle_error(e, "Unexpected error in generation")

    def _generate_without_monitoring(self, description: str, verify: Optional[bool] = None) -> Dict:
        """Original generate method without monitoring."""
        if verify is None:
            verify = self.enable_verification
        
        try:
            # Step 1: Parse input
            parsed = self._parse_input(description)
            
            # Step 2: Generate code
            generation = self._generate_code(parsed)
            
            # Step 3: Verify (if enabled)
            verification = None
            if verify:
                verification = self._verify_code(
                    generation['rtl_code'],
                    generation['testbench_code'],
                    generation['module_name']
                )
            
            # Combine results
            result = {
                'success': True,
                'module_name': generation['module_name'],
                'rtl_code': generation['rtl_code'],
                'testbench_code': generation['testbench_code'],
                'file_paths': generation.get('file_paths', {}),
                'warnings': generation.get('warnings', []),
                'verification': verification,
                'metadata': {
                    'description': description,
                    'component_type': parsed.get('component_type'),
                    'bit_width': parsed.get('bit_width'),
                },
            }
            
            return result
        
        except RTLGenError as e:
            return error_handler.handle_error(e, "Generation")
        
        except Exception as e:
            return error_handler.handle_error(e, "Unexpected error in generation")
    
    def _parse_input(self, description: str) -> Dict:
        """Parse and validate input description."""
        try:
            parsed = self.processor.parse_description(description)
            
            if not parsed['valid']:
                raise RTLGenError(
                    f"Invalid description: {parsed['errors']}",
                    ErrorCategory.INPUT_ERROR,
                    {'errors': parsed['errors']}
                )
            
            return parsed
        
        except Exception as e:
            raise RTLGenError(
                "Failed to parse description",
                ErrorCategory.INPUT_ERROR,
                {'original_error': str(e)}
            )
    
    def _generate_code(self, parsed: Dict) -> Dict:
        """Generate code from parsed input."""
        try:
            # Build prompt
            prompt = self.builder.build_prompt(parsed)
            
            # Generate with LLM
            response = self.client.generate(prompt)
            
            # Extract and format
            extraction = self.extractor.process(
                response['content'] if isinstance(response, dict) and 'content' in response else str(response),
                description=parsed.get('original_description', '')
            )
            
            if not extraction['success']:
                raise RTLGenError(
                    f"Code extraction failed: {extraction['errors']}",
                    ErrorCategory.EXTRACTION_ERROR,
                    {'errors': extraction['errors']}
                )
            
            return extraction
        
        except RTLGenError:
            raise
        
        except Exception as e:
            raise RTLGenError(
                "Code generation failed",
                ErrorCategory.LLM_ERROR,
                {'original_error': str(e)}
            )
    
    def _verify_code(self, rtl_code: str, tb_code: str, module_name: str) -> Dict:
        """Verify generated code."""
        try:
            result = self.verifier.verify(rtl_code, tb_code, module_name)
            return result
        
        except Exception as e:
            raise RTLGenError(
                "Verification failed",
                ErrorCategory.VERIFICATION_ERROR,
                {'original_error': str(e)}
            )
    
    def generate_with_learning(self, description: str, max_retries: int = 3, verify: bool = True) -> Dict:
        """
        Generate with learning from failures.
        """
        result = None
        learning_info = {
            'attempts': 0,
            'errors_encountered': [],
            'improvements_applied': [],
        }
        
        for attempt in range(max_retries):
            learning_info['attempts'] = attempt + 1
            
            # Generate
            result = self.generate(description, verify=verify)
            
            # If successful, learn from success
            if result['success']:
                if self.enable_learning and verify and result.get('verification'):
                    self.learning_engine.learn_from_success(
                        description=description,
                        code=result['rtl_code'],
                        quality_score=result['metadata'].get('quality_score', 0),
                        verification_results=result['verification']
                    )
                
                result['learning_info'] = learning_info
                return result
            
            # If failed, learn from failure
            if self.enable_learning:
                error_type = 'unknown'
                error_message = result.get('message', 'Unknown error')
                
                if 'syntax' in error_message.lower():
                    error_type = 'syntax_error'
                elif 'verification' in error_message.lower():
                    error_type = 'verification_failure'
                elif 'simulation' in error_message.lower():
                    error_type = 'simulation_failure'
                
                error_id = self.error_tracker.log_error(
                    description=description,
                    error_type=error_type,
                    error_message=error_message,
                    context={
                        'attempt': attempt + 1,
                        'design_type': result.get('metadata', {}).get('component_type', 'unknown')
                    },
                    generated_code=result.get('rtl_code'),
                    verification_results=result.get('verification')
                )
                
                learning_info['errors_encountered'].append({
                    'attempt': attempt + 1,
                    'error_id': error_id,
                    'error_type': error_type,
                })
                
                if result.get('rtl_code'):
                    self.learning_engine.learn_from_failure(
                        description=description,
                        code=result['rtl_code'],
                        error_type=error_type,
                        error_message=error_message
                    )
                
                suggestions = self.learning_engine.suggest_improvements()
                learning_info['improvements_applied'].extend(suggestions)
        
        if result:
            result['learning_info'] = learning_info
        return result

    def get_learning_statistics(self) -> Dict:
        """Get learning engine statistics."""
        if not getattr(self, 'enable_learning', False):
            return {'learning_enabled': False}
        
        return {
            'learning_enabled': True,
            'error_tracking': self.error_tracker.get_statistics(),
            'learning_progress': self.learning_engine.get_learning_report(),
        }

    def print_learning_report(self):
        """Print learning progress report."""
        if not getattr(self, 'enable_learning', False):
            print("Learning is not enabled")
            return
        
        print("\n" + "=" * 70)
        print("LEARNING STATISTICS")
        print("=" * 70)
        
        self.error_tracker.print_report()
        print()
        self.learning_engine.print_learning_report()

    def get_stats(self) -> Dict:
        """Get generation statistics."""
        return {
            'llm_stats': self.client.get_stats(),
            'verification_stats': self.verifier.get_stats() if self.enable_verification else {},
        }

    def get_performance_report(self) -> Optional[Dict]:
        """Get performance monitoring report."""
        if self.monitor:
            return self.monitor.get_report()
        return None

    def print_performance_report(self):
        """Print performance report."""
        if self.monitor:
            self.monitor.print_report()
        else:
            print("Performance monitoring not enabled")


# ============================================================================
# CONVENIENCE FUNCTION
# ============================================================================

def quick_generate(description: str, use_mock: bool = True) -> Dict:
    """
    Quick generation function for simple use cases.
    
    Args:
        description: Design description
        use_mock: Use mock LLM
        
    Returns:
        dict: Generation result
    """
    generator = RTLGenerator(use_mock=use_mock)
    return generator.generate(description)


# ============================================================================
# SELF-TEST
# ============================================================================

if __name__ == "__main__":
    print("RTL Generator Self-Test\n")
    print("=" * 70)
    
    generator = RTLGenerator(use_mock=True, debug=True)
    
    # Test 1: Simple generation
    print("\nTest 1: Generate 4-bit adder")
    print("-" * 70)
    
    result = generator.generate("4-bit adder with carry")
    
    if result['success']:
        print("[PASS] Generation successful")
        print(f"  Module: {result['module_name']}")
        print(f"  RTL: {len(result['rtl_code'])} chars")
        print(f"  TB: {len(result['testbench_code'])} chars")
        
        if result['verification']:
            print(f"  Verification: {'[PASS]' if result['verification']['passed'] else '[FAIL]'}")
    else:
        print(f"[FAIL] Generation failed: {result['message']}")
    
    # Test 2: Error handling
    print("\n\nTest 2: Error handling (invalid input)")
    print("-" * 70)
    
    result2 = generator.generate("")  # Invalid empty description
    
    print(f"Success: {result2['success']}")
    if not result2['success']:
        print(f"Error: {result2['message']}")
        print(f"Suggestion: {result2['suggestion']}")
    
    print("\n" + "=" * 70)
    print("Self-test complete!")
