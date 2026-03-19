"""
Conversation Memory System for RTL-Gen AI

Maintains conversation history and context across multiple interactions,
enabling iterative refinement of designs through natural language.

Usage:
    from python.conversation_memory import ConversationMemory
    
    memory = ConversationMemory(session_id="user_123")
    memory.add_interaction(user_msg, assistant_response, generated_code)
    context = memory.get_context(max_turns=3)
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import uuid


class ConversationMemory:
    """Manages multi-turn conversation memory."""
    
    def __init__(self, session_id: Optional[str] = None, memory_dir: str = 'memory_store'):
        """Initialize memory system."""
        self.session_id = session_id or str(uuid.uuid4())
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(exist_ok=True)
        
        self.session_file = self.memory_dir / f"session_{self.session_id}.json"
        
        # In-memory storage
        self.interactions = []
        self.design_state = {}
        
        # Load existing if available
        self._load_session()
    
    def _load_session(self):
        """Load session from disk."""
        if self.session_file.exists():
            try:
                with open(self.session_file, 'r') as f:
                    data = json.load(f)
                    self.interactions = data.get('interactions', [])
                    self.design_state = data.get('design_state', {})
            except Exception as e:
                print(f"Error loading session {self.session_id}: {e}")
    
    def _save_session(self):
        """Save session to disk."""
        data = {
            'session_id': self.session_id,
            'updated_at': datetime.now().isoformat(),
            'interactions': self.interactions,
            'design_state': self.design_state
        }
        
        with open(self.session_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def add_interaction(
        self,
        user_input: str,
        assistant_response: str,
        extracted_code: Optional[Dict] = None,
        verification_results: Optional[Dict] = None
    ) -> None:
        """
        Record a new interaction round.
        
        Args:
            user_input: The user's prompt
            assistant_response: LLM's response text
            extracted_code: Any code generated in this round
            verification_results: Results of verifying the code
        """
        interaction = {
            'timestamp': datetime.now().isoformat(),
            'user_input': user_input,
            'assistant_response': assistant_response,
            'has_code': extracted_code is not None and bool(extracted_code.get('rtl_code')),
            'verified': verification_results.get('passed', False) if verification_results else False
        }
        
        # Track current working design
        if extracted_code and extracted_code.get('rtl_code'):
            self.design_state['current_code'] = extracted_code['rtl_code']
            self.design_state['module_name'] = extracted_code.get('module_name')
            
            if extracted_code.get('testbench_code'):
                self.design_state['current_testbench'] = extracted_code['testbench_code']
        
        # Track verification state
        if verification_results:
            self.design_state['last_verification'] = verification_results
        
        self.interactions.append(interaction)
        self._save_session()
    
    def get_context(self, max_turns: int = 3) -> str:
        """
        Format recent conversation history as context for the prompt.
        
        Args:
            max_turns: Maximum previous interactions to include
            
        Returns:
            str: Formatted context string
        """
        if not self.interactions:
            return ""
        
        context_parts = ["\n## Conversation History"]
        
        # Get the latest interactions up to max_turns
        recent = self.interactions[-max_turns:]
        
        for i, turn in enumerate(recent):
            turn_num = len(self.interactions) - len(recent) + i + 1
            
            context_parts.append(f"\n### Turn {turn_num}")
            context_parts.append(f"**User**: {turn['user_input']}")
            
            # Summarize response instead of full text to save tokens
            if turn['has_code']:
                status = "Verified" if turn['verified'] else "Failed verification"
                context_parts.append(f"**Assistant**: Provided design ({status})")
            else:
                # Just include a snippet of the response
                snippet = turn['assistant_response'][:100] + "..." if len(turn['assistant_response']) > 100 else turn['assistant_response']
                context_parts.append(f"**Assistant**: {snippet}")
        
        # Include current design state if available
        if self.design_state.get('current_code'):
            context_parts.append("\n## Current Design State")
            context_parts.append(f"Module: {self.design_state.get('module_name', 'unknown')}")
            
            # Add code (might need to truncate if very long)
            code = self.design_state['current_code']
            context_parts.append("```verilog\n" + code + "\n```")
            
            if 'last_verification' in self.design_state:
                ver = self.design_state['last_verification']
                if not ver.get('passed', True) and 'message' in ver:
                    context_parts.append(f"\nVerification Error: {ver['message']}")
        
        return "\n".join(context_parts)
    
    def get_current_design(self) -> Optional[str]:
        """Return the current RTL code if any."""
        return self.design_state.get('current_code')
    
    def clear(self):
        """Clear memory for this session."""
        self.interactions = []
        self.design_state = {}
        self._save_session()


# ============================================================================
# SELF-TEST
# ============================================================================

if __name__ == "__main__":
    print("Conversation Memory Self-Test\n")
    
    memory = ConversationMemory(session_id="test_session")
    memory.clear()  # Start fresh
    
    # Interaction 1
    memory.add_interaction(
        user_input="Create an 8-bit counter",
        assistant_response="Here is the counter RTL and testbench...",
        extracted_code={'rtl_code': 'module counter...', 'module_name': 'counter'},
        verification_results={'passed': True}
    )
    
    # Interaction 2
    memory.add_interaction(
        user_input="Add an enable signal to it",
        assistant_response="I've updated the counter with an enable signal...",
        extracted_code={'rtl_code': 'module counter(..., input en);\n...', 'module_name': 'counter'},
        verification_results={'passed': False, 'message': 'Missing enable in sensitivity list'}
    )
    
    context = memory.get_context()
    print("Generated Context:\n")
    print("-" * 50)
    print(context)
    print("-" * 50)
    
    print("\n✓ Self-test complete")
