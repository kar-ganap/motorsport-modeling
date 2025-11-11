"""
Pytest configuration and fixtures for motorsport_modeling tests.
"""

import pytest
import pandas as pd
from pathlib import Path


@pytest.fixture
def sample_data_path():
    """Path to sample telemetry data."""
    return Path(__file__).parent.parent / "data" / "samples" / "indy_telemetry_sample.csv"


@pytest.fixture
def track_config_path():
    """Path to Indianapolis track configuration."""
    return Path(__file__).parent.parent / "data" / "tracks" / "indy.json"


@pytest.fixture
def sample_telemetry(sample_data_path):
    """Load sample telemetry data."""
    if sample_data_path.exists():
        return pd.read_csv(sample_data_path)
    return None


# TODO: Add more fixtures as needed
# - Synthetic telemetry data for unit tests
# - Mock race data
# - Test configurations
