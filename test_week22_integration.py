"""
Week 22 Integration Test Suite

Comprehensive testing of all Week 22 features.

Usage: python test_week22_integration.py
"""

import time
import json
from pathlib import Path

from python.rtl_generator import RTLGenerator
from python.error_tracker import ErrorTracker
from python.learning_engine import LearningEngine
from python.rag_system import RAGSystem
from python.multi_stage_generator import MultiStageGenerator
from python.conversation_memory import ConversationMemory
from python.user_preferences import UserPreferences


class Week22IntegrationTester:
    """Comprehensive integration tester for Week 22."""

    def __init__(self):
        """Initialize tester."""
        self.results = {
            'tests_run': 0,
            'tests_passed': 0,
            'tests_failed': 0,
            'test_details': [],
        }

    def run_test(self, test_name: str, test_func):
        """
        Run single test.

        Args:
            test_name: Test name
            test_func: Test function
        """
        print(f"\n{'='*70}")
        print(f"TEST: {test_name}")
        print(f"{'='*70}")

        self.results['tests_run'] += 1

        try:
            start_time = time.time()
            result = test_func()
            duration = time.time() - start_time

            if result:
                self.results['tests_passed'] += 1
                status = "✓ PASSED"
            else:
                self.results['tests_failed'] += 1
                status = "✗ FAILED"

            print(f"\n{status} ({duration:.1f}s)")

            self.results['test_details'].append({
                'name': test_name,
                'passed': result,
                'duration': duration,
            })

            return result

        except Exception as e:
            self.results['tests_failed'] += 1
            print(f"\n✗ FAILED: {e}")

            self.results['test_details'].append({
                'name': test_name,
                'passed': False,
                'error': str(e),
            })

            return False

    def test_error_tracking(self) -> bool:
        """Test error tracking system."""
        tracker = ErrorTracker()

        # Log errors
        tracker.log_error(
            description="test design",
            error_type="syntax_error",
            error_message="Test error",
            context={'test': True}
        )

        # Get statistics
        stats = tracker.get_statistics()

        # Verify
        success = stats['total_errors'] > 0
        print(f"Logged {stats['total_errors']} errors")

        return success

    def test_learning_engine(self) -> bool:
        """Test learning engine."""
        engine = LearningEngine()

        # Log correction
        engine.log_correction(
            original_description="test",
            original_code="original",
            corrected_code="corrected",
            correction_type="test",
            notes="test correction"
        )

        # Analyze corrections
        analysis = engine.analyze_corrections()

        # Verify
        success = analysis['total_corrections'] > 0
        print(f"Analyzed {analysis['total_corrections']} corrections")

        return success

    def test_rag_system(self) -> bool:
        """Test RAG system."""
        rag = RAGSystem()

        # Get statistics
        stats = rag.get_index_statistics()

        print(f"Indexed designs: {stats['indexed_designs']}")
        print(f"Vector dimension: {stats['vector_dimension']}")

        # Retrieve examples
        if stats['indexed_designs'] > 0:
            results = rag.retrieve_relevant_examples("8-bit adder", top_k=3)
            print(f"Retrieved {len(results)} examples")

            success = len(results) > 0
        else:
            print("No designs indexed yet - creating index...")
            rag.create_index()
            success = True

        return success

    def test_multi_stage_generation(self) -> bool:
        """Test multi-stage generation."""
        generator = MultiStageGenerator(use_mock=True)

        # Generate design
        result = generator.generate_multi_stage(
            description="4-bit adder",
            max_refinements=1
        )

        # Verify
        success = 'stages' in result

        if success:
            print("✓ Multi-stage generation executed")
            print(f"  Final success: {result.get('success', False)}")

        return success

    def test_conversation_memory(self) -> bool:
        """Test conversation memory."""
        memory = ConversationMemory()
        test_user = "test_user_integration"

        # Add interactions
        for i in range(3):
            memory.add_interaction(
                user_id=test_user,
                description=f"test design {i}",
                result={'success': True, 'module_name': f'test_{i}', 'metadata': {'component_type': 'test', 'quality_score': 8.0}}
            )

        # Get history
        history = memory.get_history(test_user)

        # Get statistics
        stats = memory.get_statistics(test_user)

        # Verify
        success = len(history) == 3 and stats['total_interactions'] == 3

        print(f"Stored {len(history)} interactions")
        print(f"Success rate: {stats['success_rate']:.1f}%")

        return success

    def test_user_preferences(self) -> bool:
        """Test user preferences."""
        prefs = UserPreferences()
        test_user = "test_user_prefs"

        # Set preferences
        prefs.set_preference(test_user, 'coding_style', 'verbose')
        prefs.set_preference(test_user, 'indentation', 4)

        # Get preferences
        coding_style = prefs.get_preference(test_user, 'coding_style')
        indentation = prefs.get_preference(test_user, 'indentation')

        # Verify
        success = coding_style == 'verbose' and indentation == 4

        print(f"Coding style: {coding_style}")
        print(f"Indentation: {indentation}")

        return success

    def test_context_aware_generation(self) -> bool:
        """Test context-aware generation."""
        generator = RTLGenerator(
            use_mock=True,
            enable_context=True,
            user_id="test_user_context"
        )

        # Generate design
        result = generator.generate_with_context(
            description="8-bit adder",
            verify=False
        )

        # Verify
        success = result['success']

        if success:
            print(f"✓ Generated: {result['module_name']}")

        # Check user statistics
        user_stats = generator.get_user_statistics()
        print(f"User interactions: {user_stats['statistics']['total_interactions']}")

        return success

    def test_learning_with_refinement(self) -> bool:
        """Test learning with refinement."""
        generator = RTLGenerator(
            use_mock=True,
            enable_learning=True,
            enable_context=True
        )

        # Generate with learning
        result = generator.generate_with_learning(
            description="test design for learning",
            max_retries=2,
            verify=False
        )

        # Check learning info
        success = 'learning_info' in result

        if success:
            info = result['learning_info']
            print(f"Attempts: {info['attempts']}")
            print(f"Errors encountered: {len(info['errors_encountered'])}")

        return success

    def test_end_to_end_workflow(self) -> bool:
        """Test complete end-to-end workflow."""
        print("\nExecuting complete workflow...")

        # Initialize with all features
        generator = RTLGenerator(
            use_mock=True,
            enable_verification=True,
            enable_monitoring=True,
            enable_learning=True,
            enable_context=True,
            user_id="test_user_e2e"
        )

        # Set user preferences
        prefs = UserPreferences()
        prefs.update_preferences("test_user_e2e", {
            'verification_level': 'full',
            'auto_refinement': True,
            'enable_learning': True,
        })

        # Generate design with all features
        result = generator.generate_with_context(
            description="4-bit counter with reset",
            verify=True
        )

        # Verify all components worked
        checks = {
            'generation': result['success'],
            'verification': 'verification' in result,
            'metadata': 'metadata' in result,
        }

        success = all(checks.values())

        for component, status in checks.items():
            symbol = "✓" if status else "✗"
            print(f"  {symbol} {component}")

        return success

    def run_all_tests(self):
        """Run all integration tests."""
        print("=" * 70)
        print("WEEK 22 INTEGRATION TEST SUITE")
        print("=" * 70)
        print("\nTesting all Week 22 features...")

        # Test 1: Error Tracking
        self.run_test("Error Tracking System", self.test_error_tracking)

        # Test 2: Learning Engine
        self.run_test("Learning Engine", self.test_learning_engine)

        # Test 3: RAG System
        self.run_test("RAG System", self.test_rag_system)

        # Test 4: Multi-Stage Generation
        self.run_test("Multi-Stage Generation", self.test_multi_stage_generation)

        # Test 5: Conversation Memory
        self.run_test("Conversation Memory", self.test_conversation_memory)

        # Test 6: User Preferences
        self.run_test("User Preferences", self.test_user_preferences)

        # Test 7: Context-Aware Generation
        self.run_test("Context-Aware Generation", self.test_context_aware_generation)

        # Test 8: Learning with Refinement
        self.run_test("Learning with Refinement", self.test_learning_with_refinement)

        # Test 9: End-to-End Workflow
        self.run_test("End-to-End Workflow", self.test_end_to_end_workflow)

        # Print summary
        self.print_summary()

    def print_summary(self):
        """Print test summary."""
        print("\n" + "=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)

        print(f"\nTotal Tests: {self.results['tests_run']}")
        print(f"Passed: {self.results['tests_passed']} ✓")
        print(f"Failed: {self.results['tests_failed']} ✗")

        if self.results['tests_run'] > 0:
            pass_rate = self.results['tests_passed'] / self.results['tests_run'] * 100
            print(f"Pass Rate: {pass_rate:.1f}%")

        print("\nDetailed Results:")
        for detail in self.results['test_details']:
            status = "✓" if detail['passed'] else "✗"
            duration = detail.get('duration', 0)
            print(f"  {status} {detail['name']:<40} ({duration:.1f}s)")

            if not detail['passed'] and 'error' in detail:
                print(f"      Error: {detail['error']}")

        # Overall status
        print("\n" + "=" * 70)
        if self.results['tests_failed'] == 0:
            print("✓ ALL TESTS PASSED")
        else:
            print(f"✗ {self.results['tests_failed']} TESTS FAILED")
        print("=" * 70)

        # Save results
        results_file = Path('test_results') / 'week22_integration_results.json'
        results_file.parent.mkdir(exist_ok=True)

        with open(results_file, 'w') as f:
            json.dump(self.results, f, indent=2)

        print(f"\n✓ Results saved: {results_file}")


def main():
    """Main entry point."""
    tester = Week22IntegrationTester()
    tester.run_all_tests()


if __name__ == "__main__":
    main()
