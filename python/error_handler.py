"""
Centralized Error Handling for RTL-Gen AI
Provides consistent error handling across all components.
"""

import logging
from typing import Dict, Optional
from enum import Enum

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


class ErrorCategory(Enum):
    """Error categories for classification."""
    INPUT_ERROR = "input_error"
    LLM_ERROR = "llm_error"
    EXTRACTION_ERROR = "extraction_error"
    COMPILATION_ERROR = "compilation_error"
    SIMULATION_ERROR = "simulation_error"
    VERIFICATION_ERROR = "verification_error"
    SYSTEM_ERROR = "system_error"


class RTLGenError(Exception):
    """Base exception for RTL-Gen AI."""
    
    def __init__(self, message: str, category: ErrorCategory, 
                 details: Optional[Dict] = None):
        self.message = message
        self.category = category
        self.details = details or {}
        super().__init__(self.message)


class ErrorHandler:
    """Centralized error handler."""
    
    def __init__(self):
        self.logger = logging.getLogger('RTL-Gen-AI')
        self.error_history = []
    
    def handle_error(self, error: Exception, context: str = "") -> Dict:
        """
        Handle an error and return user-friendly message.
        
        Args:
            error: The exception
            context: Where the error occurred
            
        Returns:
            dict: Formatted error info
        """
        self.logger.error(f"{context}: {error}")
        
        error_info = {
            'success': False,
            'error_type': type(error).__name__,
            'message': str(error),
            'context': context,
            'user_message': self._get_user_message(error),
            'suggestion': self._get_suggestion(error),
        }
        
        self.error_history.append(error_info)
        
        return error_info
    
    def _get_user_message(self, error: Exception) -> str:
        """Get user-friendly error message."""
        if isinstance(error, RTLGenError):
            return error.message
        
        # Map common errors to friendly messages
        error_messages = {
            'FileNotFoundError': "File not found. Please check the path.",
            'PermissionError': "Permission denied. Check file permissions.",
            'ValueError': "Invalid value provided. Please check your input.",
            'TimeoutError': "Operation timed out. Please try again.",
            'ConnectionError': "Network error. Check your internet connection.",
        }
        
        return error_messages.get(type(error).__name__, 
                                 "An unexpected error occurred.")
    
    def _get_suggestion(self, error: Exception) -> str:
        """Get suggestion for fixing the error."""
        suggestions = {
            'FileNotFoundError': "Make sure the file exists and the path is correct.",
            'PermissionError': "Run with appropriate permissions or check file ownership.",
            'ValueError': "Verify that all inputs are in the correct format.",
            'TimeoutError': "Try increasing the timeout or check your network connection.",
            'ConnectionError': "Check your internet connection and API credentials.",
        }
        
        return suggestions.get(type(error).__name__, 
                             "Please check the error message and try again.")


# Global error handler instance
error_handler = ErrorHandler()
