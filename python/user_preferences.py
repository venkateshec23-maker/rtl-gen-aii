"""
User Preference System

Manages user preferences and customization settings.

Usage:
    from python.user_preferences import UserPreferences
    
    prefs = UserPreferences()
    prefs.set_preference(user_id, 'coding_style', 'ieee_standard')
    style = prefs.get_preference(user_id, 'coding_style')
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional


class UserPreferences:
    """Manage user preferences."""
    
    DEFAULT_PREFERENCES = {
        # Code style
        'coding_style': 'ieee_standard',  # 'ieee_standard', 'minimalist', 'verbose'
        'indentation': 2,  # 2 or 4 spaces
        'comment_density': 'medium',  # 'minimal', 'medium', 'high'
        'naming_convention': 'snake_case',  # 'snake_case', 'camelCase'
        
        # Generation
        'verification_level': 'full',  # 'none', 'syntax', 'full'
        'testbench_complexity': 'comprehensive',  # 'simple', 'comprehensive', 'exhaustive'
        'auto_refinement': True,  # Auto-refine on failure
        'max_refinement_attempts': 2,
        
        # Output
        'include_documentation': True,
        'include_synthesis_hints': False,
        'output_format': 'verilog',  # 'verilog', 'systemverilog'
        
        # Interface
        'show_progress': True,
        'show_intermediate_steps': False,
        'notification_level': 'normal',  # 'minimal', 'normal', 'verbose'
        
        # Advanced
        'enable_learning': True,
        'enable_caching': True,
        'context_aware': True,
    }
    
    def __init__(self, storage_dir: str = 'data/preferences'):
        """Initialize user preferences."""
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Cache
        self.cache = {}
    
    def _get_user_file(self, user_id: str) -> Path:
        """Get preference file for user."""
        return self.storage_dir / f"{user_id}_prefs.json"
    
    def _load_preferences(self, user_id: str) -> Dict:
        """Load user preferences."""
        user_file = self._get_user_file(user_id)
        
        if not user_file.exists():
            return self.DEFAULT_PREFERENCES.copy()
        
        try:
            with open(user_file, 'r') as f:
                loaded = json.load(f)
            
            # Merge with defaults (in case new preferences added)
            preferences = self.DEFAULT_PREFERENCES.copy()
            preferences.update(loaded)
            
            return preferences
            
        except:
            return self.DEFAULT_PREFERENCES.copy()
    
    def _save_preferences(self, user_id: str, preferences: Dict):
        """Save user preferences."""
        user_file = self._get_user_file(user_id)
        
        with open(user_file, 'w') as f:
            json.dump(preferences, f, indent=2)
    
    def get_preference(self, user_id: str, key: str) -> Any:
        """
        Get single preference.
        
        Args:
            user_id: User identifier
            key: Preference key
            
        Returns:
            Preference value
        """
        if user_id not in self.cache:
            self.cache[user_id] = self._load_preferences(user_id)
        
        return self.cache[user_id].get(key, self.DEFAULT_PREFERENCES.get(key))
    
    def set_preference(self, user_id: str, key: str, value: Any):
        """
        Set single preference.
        
        Args:
            user_id: User identifier
            key: Preference key
            value: Preference value
        """
        if user_id not in self.cache:
            self.cache[user_id] = self._load_preferences(user_id)
        
        self.cache[user_id][key] = value
        self._save_preferences(user_id, self.cache[user_id])
    
    def get_all_preferences(self, user_id: str) -> Dict:
        """
        Get all preferences for user.
        
        Args:
            user_id: User identifier
            
        Returns:
            dict: All preferences
        """
        if user_id not in self.cache:
            self.cache[user_id] = self._load_preferences(user_id)
        
        return self.cache[user_id].copy()
    
    def update_preferences(self, user_id: str, preferences: Dict):
        """
        Update multiple preferences.
        
        Args:
            user_id: User identifier
            preferences: Dictionary of preferences to update
        """
        if user_id not in self.cache:
            self.cache[user_id] = self._load_preferences(user_id)
        
        self.cache[user_id].update(preferences)
        self._save_preferences(user_id, self.cache[user_id])
    
    def reset_preferences(self, user_id: str):
        """
        Reset preferences to defaults.
        
        Args:
            user_id: User identifier
        """
        self.cache[user_id] = self.DEFAULT_PREFERENCES.copy()
        self._save_preferences(user_id, self.cache[user_id])
    
    def export_preferences(self, user_id: str) -> str:
        """
        Export preferences as JSON string.
        
        Args:
            user_id: User identifier
            
        Returns:
            str: JSON string
        """
        preferences = self.get_all_preferences(user_id)
        return json.dumps(preferences, indent=2)
    
    def import_preferences(self, user_id: str, json_string: str):
        """
        Import preferences from JSON string.
        
        Args:
            user_id: User identifier
            json_string: JSON string of preferences
        """
        try:
            preferences = json.loads(json_string)
            self.update_preferences(user_id, preferences)
            return True
        except:
            return False
    
    def get_generation_config(self, user_id: str) -> Dict:
        """
        Get generation configuration from preferences.
        
        Args:
            user_id: User identifier
            
        Returns:
            dict: Generation config
        """
        prefs = self.get_all_preferences(user_id)
        
        return {
            'enable_verification': prefs['verification_level'] != 'none',
            'verification_level': prefs['verification_level'],
            'enable_refinement': prefs['auto_refinement'],
            'max_refinement_attempts': prefs['max_refinement_attempts'],
            'enable_learning': prefs['enable_learning'],
            'enable_caching': prefs['enable_caching'],
            'coding_style': prefs['coding_style'],
            'testbench_complexity': prefs['testbench_complexity'],
        }


# ============================================================================
# SELF-TEST
# ============================================================================

if __name__ == "__main__":
    print("User Preferences Self-Test\n")
    
    prefs = UserPreferences()
    test_user = "test_user_123"
    
    # Get default preference
    print("Default coding style:", prefs.get_preference(test_user, 'coding_style'))
    
    # Set preference
    prefs.set_preference(test_user, 'coding_style', 'verbose')
    print("Updated coding style:", prefs.get_preference(test_user, 'coding_style'))
    
    # Update multiple
    prefs.update_preferences(test_user, {
        'indentation': 4,
        'comment_density': 'high',
    })
    
    print("\nAll preferences:")
    all_prefs = prefs.get_all_preferences(test_user)
    for key, value in all_prefs.items():
        print(f"  {key}: {value}")
    
    # Get generation config
    print("\nGeneration config:")
    config = prefs.get_generation_config(test_user)
    for key, value in config.items():
        print(f"  {key}: {value}")
    
    # Export/Import
    print("\nExporting preferences...")
    exported = prefs.export_preferences(test_user)
    print(f"Exported {len(exported)} characters")
    
    print("\n✓ Self-test complete")
