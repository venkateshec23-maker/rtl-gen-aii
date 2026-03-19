"""
Context Manager Enhancement

Integrates ContextManager with actual ConversationMemory, creating a
unified interface for conversation and design context.

Usage:
    from python.context_manager import ContextManager
    
    ctx = ContextManager()
    ctx.update_context(...)
"""

from typing import Dict, List, Optional
from pathlib import Path
import json

from python.conversation_memory import ConversationMemory
from python.rag_system import RAGSystem

class ContextManager:
    """Manages prompt context, history, and retrieved examples."""
    
    def __init__(self, session_id: Optional[str] = None):
        """Initialize context manager."""
        self.memory = ConversationMemory(session_id=session_id)
        self.rag = RAGSystem()
        self.current_design_type = "unknown"
        
    def add_interaction(self, user_prompt: str, response: str, code_data: Dict = None, verification_results: Dict = None):
        """Register a new interaction."""
        self.memory.add_interaction(
            user_input=user_prompt,
            assistant_response=response,
            extracted_code=code_data,
            verification_results=verification_results
        )
        
    def get_prompt_context(self, user_prompt: str, include_examples: bool = True) -> str:
        """
        Build the prefix context for the next prompt based on memory and RAG.
        """
        context_parts = []
        
        # 1. Conversation History & Current Code
        conv_context = self.memory.get_context()
        if conv_context:
            context_parts.append(conv_context)
            
        # 2. RAG Examples (if requested and we are starting fresh or need ideas)
        if include_examples:
            # Only pull examples if we are not actively debugging an existing file
            if not self.memory.design_state.get('current_code'):
                examples = self.rag.retrieve_relevant_examples(user_prompt, top_k=1)
                if examples:
                    ex = examples[0]
                    context_parts.append(f"\n## Reference Example\nSimilar design '{ex['name']}':\n```verilog\n{ex['rtl']}\n```")
                    
        return "\n".join(context_parts)
    
    def reset(self):
        """Clear context."""
        self.memory.clear()
        self.current_design_type = "unknown"
