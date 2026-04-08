# tests/conftest.py
# Shared fixtures and configuration for all tests

import pytest
import subprocess
from pathlib import Path

WORK_DIR = Path(r"C:\tools\OpenLane")


def pytest_configure(config):
    """Register custom markers"""
    config.addinivalue_line(
        "markers",
        "unit: Fast unit tests — no Docker required"
    )
    config.addinivalue_line(
        "markers",
        "integration: Real integration tests — Docker and EDA tools required"
    )


@pytest.fixture(scope="session")
def docker_available():
    """Check Docker is running — skip integration tests if not"""
    result = subprocess.run(
        ["docker", "info"],
        capture_output=True
    )
    return result.returncode == 0


@pytest.fixture(scope="session", autouse=True)
def skip_integration_if_no_docker(request, docker_available):
    """Auto-skip integration tests when Docker is unavailable"""
    if request.node.get_closest_marker("integration"):
        if not docker_available:
            pytest.skip("Docker not running — integration tests skipped")


@pytest.fixture(scope="session")
def results_dir():
    """Path to real tool output files"""
    d = WORK_DIR / "results"
    d.mkdir(parents=True, exist_ok=True)
    return d


@pytest.fixture
def fake_results_dir(tmp_path):
    """Temporary directory for unit test file creation"""
    return tmp_path
