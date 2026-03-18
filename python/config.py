"""
Configuration module for RTL-Gen AII.
Loads settings from .env file and provides project-wide constants.
"""

import os
from pathlib import Path

# Load .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not installed yet; fall back to os.environ

# ============================================================================
# PROJECT PATHS
# ============================================================================

PROJECT_ROOT = Path(__file__).parent.parent
CACHE_DIR = PROJECT_ROOT / os.getenv('CACHE_DIR', 'cache')
LOGS_DIR = PROJECT_ROOT / os.getenv('LOGS_DIR', 'logs')
RTL_OUTPUT_DIR = PROJECT_ROOT / os.getenv('RTL_OUTPUT_DIR', 'outputs')
TEMPLATES_DIR = PROJECT_ROOT / os.getenv('TEMPLATES_DIR', 'templates')
EXAMPLES_DIR = PROJECT_ROOT / os.getenv('EXAMPLES_DIR', 'examples')

# Create directories
for d in [CACHE_DIR, LOGS_DIR, RTL_OUTPUT_DIR, TEMPLATES_DIR, EXAMPLES_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ============================================================================
# NVIDIA / DEEPSEEK CONFIGURATION
# ============================================================================

NVIDIA_API_KEY = os.getenv('NVIDIA_API_KEY', '')
NVIDIA_MODEL = os.getenv('NVIDIA_MODEL', 'deepseek-ai/deepseek-v3.2')
NVIDIA_BASE_URL = os.getenv('NVIDIA_BASE_URL', 'https://integrate.api.nvidia.com/v1')

# Generation parameters
DEFAULT_TEMPERATURE = float(os.getenv('DEFAULT_TEMPERATURE', '0.3'))
MAX_TOKENS = int(os.getenv('MAX_TOKENS', '4000'))

# Rate limiting
MAX_REQUESTS_PER_MINUTE = 60
REQUEST_COOLDOWN = 60.0 / MAX_REQUESTS_PER_MINUTE

# Cost tracking
TOKEN_COST_PER_MILLION = {
    'deepseek-ai/deepseek-v3.2': 0.0,  # Free tier
    'default': 0.0
}

# ============================================================================
# FEATURE FLAGS
# ============================================================================

ENABLE_CACHING = os.getenv('ENABLE_CACHING', 'true').lower() == 'true'
ENABLE_MOCK_LLM = os.getenv('ENABLE_MOCK_LLM', 'false').lower() == 'true'
DEBUG_MODE = os.getenv('DEBUG_MODE', 'false').lower() == 'true'

# ============================================================================
# VALIDATION
# ============================================================================


def validate_config():
    """Validate configuration and print status."""
    print("RTL-Gen AII Configuration")
    print("=" * 40)
    print(f"  API Key set:   {'Yes' if NVIDIA_API_KEY else 'No'}")
    print(f"  Model:         {NVIDIA_MODEL}")
    print(f"  Base URL:      {NVIDIA_BASE_URL}")
    print(f"  Temperature:   {DEFAULT_TEMPERATURE}")
    print(f"  Max Tokens:    {MAX_TOKENS}")
    print(f"  Caching:       {ENABLE_CACHING}")
    print(f"  Mock LLM:      {ENABLE_MOCK_LLM}")
    print(f"  Debug:         {DEBUG_MODE}")
    print(f"  Cache Dir:     {CACHE_DIR}")
    print(f"  Logs Dir:      {LOGS_DIR}")
    print("=" * 40)

    if not NVIDIA_API_KEY and not ENABLE_MOCK_LLM:
        print("WARNING: NVIDIA_API_KEY not set. Use ENABLE_MOCK_LLM=true for testing.")
        return False
    return True

# ============================================================================
# VERIFICATION CONFIGURATION (Day 12)
# ============================================================================

# Icarus Verilog paths (auto-detect or specify)
IVERILOG_PATH = os.getenv('IVERILOG_PATH', 'iverilog')
VVP_PATH = os.getenv('VVP_PATH', 'vvp')

# Simulation settings
SIMULATION_TIMEOUT = int(os.getenv('SIMULATION_TIMEOUT', 30))  # seconds
ENABLE_WAVEFORMS = os.getenv('ENABLE_WAVEFORMS', 'true').lower() == 'true'

# Verification directories
VERIFICATION_DIR = CACHE_DIR / 'verification'
VERIFICATION_DIR.mkdir(exist_ok=True)

# Temporary simulation workspace
SIM_WORKSPACE = VERIFICATION_DIR / 'sim_workspace'
SIM_WORKSPACE.mkdir(exist_ok=True)

# Waveform output directory
WAVEFORM_DIR = VERIFICATION_DIR / 'waveforms'
WAVEFORM_DIR.mkdir(exist_ok=True)


# ============================================================================
# UTILITY FUNCTIONS FOR VERIFICATION (Day 12)
# ============================================================================

def check_iverilog_available() -> bool:
    """Check if Icarus Verilog is available."""
    import shutil
    return shutil.which('iverilog') is not None


def check_vvp_available() -> bool:
    """Check if vvp (Icarus simulator) is available."""
    import shutil
    return shutil.which('vvp') is not None


def get_verification_tools_status() -> dict:
    """Get status of all verification tools."""
    return {
        'iverilog': check_iverilog_available(),
        'vvp': check_vvp_available(),
    }


if __name__ == "__main__":
    validate_config()

