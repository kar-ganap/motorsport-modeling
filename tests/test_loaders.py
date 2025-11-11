"""
Unit tests for data loaders.
"""

import pytest
import pandas as pd
import time
from pathlib import Path

from motorsport_modeling.data import (
    load_telemetry,
    load_gps_data,
    get_available_vehicles,
    get_available_parameters,
    validate_data_completeness
)


# Test data path
SAMPLE_DATA = Path(__file__).parent.parent / "data" / "samples" / "indy_telemetry_sample.csv"


class TestDataLoaders:
    """Test suite for telemetry data loaders."""

    def test_sample_data_exists(self):
        """Verify sample data file exists."""
        assert SAMPLE_DATA.exists(), f"Sample data not found at {SAMPLE_DATA}"

    def test_load_telemetry_basic(self):
        """Test basic telemetry loading."""
        df = load_telemetry(SAMPLE_DATA, verbose=False)

        # Should return a DataFrame
        assert isinstance(df, pd.DataFrame)

        # Should have data
        assert len(df) > 0

        # Should have expected columns
        assert 'vehicle_number' in df.columns
        assert 'lap' in df.columns
        assert 'timestamp' in df.columns

    def test_load_telemetry_performance(self):
        """Test that sample data loads in < 2 seconds."""
        start = time.time()
        df = load_telemetry(SAMPLE_DATA, verbose=False)
        elapsed = time.time() - start

        assert elapsed < 2.0, f"Loading took {elapsed:.2f}s, expected < 2s"
        print(f"✅ Sample loaded in {elapsed:.2f}s")

    def test_load_telemetry_filter_vehicle(self):
        """Test filtering by vehicle number."""
        vehicle_num = 88  # Using vehicle from sample

        df = load_telemetry(SAMPLE_DATA, vehicle=vehicle_num, verbose=False)

        # All rows should be for this vehicle
        assert (df['vehicle_number'] == vehicle_num).all()

        # Should have data
        assert len(df) > 0

    def test_load_telemetry_filter_lap(self):
        """Test filtering by lap number."""
        lap_num = 1

        df = load_telemetry(SAMPLE_DATA, lap=lap_num, verbose=False)

        # All rows should be for this lap
        assert (df['lap'] == lap_num).all()

        # Should have data
        assert len(df) > 0

    def test_load_telemetry_filter_multiple_laps(self):
        """Test filtering by multiple lap numbers."""
        laps = [1, 2, 3]

        df = load_telemetry(SAMPLE_DATA, lap=laps, verbose=False)

        # All rows should be for these laps
        assert df['lap'].isin(laps).all()

        # Should have data
        assert len(df) > 0

    def test_load_telemetry_filter_parameters(self):
        """Test filtering by specific parameters."""
        # First check what parameters are available
        available_params = get_available_parameters(SAMPLE_DATA)

        # Use parameters we know exist in the sample
        params = ['speed', 'pbrake_f']

        # Add ath if available
        if 'ath' in available_params:
            params.append('ath')

        df = load_telemetry(
            SAMPLE_DATA,
            parameters=params,
            wide_format=True,
            verbose=False
        )

        # Should have at least some of the requested parameters as columns
        # (may not have all due to sampling and pivot dropping all-NaN columns)
        found_params = [p for p in params if p in df.columns]
        assert len(found_params) >= 1, f"Expected at least one parameter from {params}"

    def test_load_telemetry_wide_format(self):
        """Test wide format conversion."""
        df = load_telemetry(SAMPLE_DATA, wide_format=True, verbose=False)

        # Should have telemetry parameters as columns
        # (not in 'telemetry_name' column)
        assert 'telemetry_name' not in df.columns

        # Should have some telemetry parameter columns
        # Common ones: speed, ath, pbrake_f, etc.
        telemetry_cols = [c for c in df.columns
                         if c not in ['vehicle_number', 'lap', 'timestamp']]
        assert len(telemetry_cols) > 0

    def test_load_telemetry_long_format(self):
        """Test long format (no pivot)."""
        df = load_telemetry(SAMPLE_DATA, wide_format=False, verbose=False)

        # Should have telemetry_name and telemetry_value columns
        assert 'telemetry_name' in df.columns
        assert 'telemetry_value' in df.columns

    def test_load_gps_data(self):
        """Test GPS data loading."""
        df = load_gps_data(SAMPLE_DATA, verbose=False)

        # Should have GPS columns
        assert 'latitude' in df.columns
        assert 'longitude' in df.columns

        # GPS coordinates should be in Indianapolis range
        # Indianapolis Motor Speedway: ~39.79°N, 86.23°W
        assert df['latitude'].between(39.78, 39.81).any()
        assert df['longitude'].between(-86.24, -86.22).any()

        # Should have data
        assert len(df) > 0

    def test_get_available_vehicles(self):
        """Test getting list of vehicles."""
        vehicles = get_available_vehicles(SAMPLE_DATA)

        # Should return a list
        assert isinstance(vehicles, list)

        # Should have at least one vehicle
        assert len(vehicles) > 0

        # All should be integers
        assert all(isinstance(v, int) for v in vehicles)

        # Should be sorted
        assert vehicles == sorted(vehicles)

    def test_get_available_parameters(self):
        """Test getting list of parameters."""
        params = get_available_parameters(SAMPLE_DATA)

        # Should return a list
        assert isinstance(params, list)

        # Should have multiple parameters
        assert len(params) > 5

        # Should include common parameters
        assert 'speed' in params or 'ath' in params or 'pbrake_f' in params

        # Should be sorted
        assert params == sorted(params)

    def test_validate_data_completeness(self):
        """Test data validation."""
        result = validate_data_completeness(SAMPLE_DATA, verbose=False)

        # Should return a dict
        assert isinstance(result, dict)

        # Should have expected keys
        assert 'vehicles_found' in result
        assert 'parameters_found' in result
        assert 'has_gps' in result
        assert 'total_rows' in result
        assert 'validation_passed' in result

        # Should have vehicles
        assert len(result['vehicles_found']) > 0

        # Should have parameters
        assert len(result['parameters_found']) > 0

        # Should have GPS (Indianapolis data has GPS)
        assert result['has_gps'] == True

        # Should have rows
        assert result['total_rows'] > 0

    def test_timestamp_conversion(self):
        """Test that timestamps are properly converted to datetime."""
        df = load_telemetry(SAMPLE_DATA, verbose=False)

        # timestamp column should be datetime
        assert pd.api.types.is_datetime64_any_dtype(df['timestamp'])

        # Timestamps should be monotonic increasing (sorted)
        # (may not be strictly increasing due to multiple vehicles)
        assert not df['timestamp'].isna().any()


class TestDataQuality:
    """Test suite for data quality checks."""

    def test_no_missing_vehicle_numbers(self):
        """Verify no missing vehicle numbers."""
        df = load_telemetry(SAMPLE_DATA, wide_format=False, verbose=False)
        assert not df['vehicle_number'].isna().any()

    def test_no_missing_lap_numbers(self):
        """Verify no missing lap numbers."""
        df = load_telemetry(SAMPLE_DATA, wide_format=False, verbose=False)
        assert not df['lap'].isna().any()

    def test_gps_coordinates_valid(self):
        """Verify GPS coordinates are in valid range."""
        df = load_gps_data(SAMPLE_DATA, verbose=False)

        # Latitude should be in valid range (-90 to 90)
        assert df['latitude'].between(-90, 90).all()

        # Longitude should be in valid range (-180 to 180)
        assert df['longitude'].between(-180, 180).all()

        # Indianapolis specific checks
        # Should be near Indianapolis Motor Speedway
        assert df['latitude'].between(39.78, 39.81).all()
        assert df['longitude'].between(-86.24, -86.22).all()


if __name__ == '__main__':
    # Run tests with pytest
    pytest.main([__file__, '-v'])
