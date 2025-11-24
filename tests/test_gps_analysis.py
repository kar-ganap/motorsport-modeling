"""
Tests for GPS analysis module.

Tests corner identification, racing line extraction, and GPS utilities.
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path

from motorsport_modeling.data import (
    load_gps_data,
    identify_corners_from_gps,
    get_corner_at_position,
    extract_corner_telemetry,
    validate_corner_identification
)

# Path to sample data
SAMPLE_DATA = Path(__file__).parent.parent / 'data' / 'samples' / 'indy_telemetry_sample.csv'


class TestGPSCornerIdentification:
    """Tests for corner identification from GPS data."""

    def create_synthetic_gps_data(self, n_laps=3, points_per_lap=200):
        """Create synthetic GPS data with simulated corners for testing."""
        # Indianapolis is approximately a rectangle with rounded corners
        # Simulate 4 corners at roughly equal spacing

        data = []
        base_lat = 39.795
        base_lon = -86.235

        for lap in range(1, n_laps + 1):
            for i in range(points_per_lap):
                # Progress around track (0 to 1)
                progress = i / points_per_lap

                # Simulate 4 corners by creating speed dips
                # Corner 1: progress ~0.15 (slow corner)
                # Corner 2: progress ~0.35 (fast corner)
                # Corner 3: progress ~0.65 (medium corner)
                # Corner 4: progress ~0.85 (slow corner)

                # Calculate distance to nearest corner
                corner_positions = [0.15, 0.35, 0.65, 0.85]
                corner_speeds = [55, 120, 80, 50]  # Slow, fast, medium, slow

                # Find nearest corner
                distances = [abs(progress - cp) for cp in corner_positions]
                nearest_corner_idx = distances.index(min(distances))
                distance_to_corner = distances[nearest_corner_idx]

                # Speed profile: base speed with dips at corners
                base_speed = 180  # km/h
                if distance_to_corner < 0.05:  # Within 5% of corner
                    # Interpolate between base speed and corner speed
                    speed = corner_speeds[nearest_corner_idx] + \
                            (base_speed - corner_speeds[nearest_corner_idx]) * \
                            (distance_to_corner / 0.05)
                else:
                    speed = base_speed + np.random.normal(0, 5)  # Add noise

                # GPS coordinates: roughly rectangular track
                if progress < 0.25:  # Straight 1
                    lat = base_lat + progress * 0.004
                    lon = base_lon
                elif progress < 0.5:  # Straight 2
                    lat = base_lat + 0.001
                    lon = base_lon + (progress - 0.25) * 0.004
                elif progress < 0.75:  # Straight 3
                    lat = base_lat + 0.001 - (progress - 0.5) * 0.004
                    lon = base_lon + 0.001
                else:  # Straight 4
                    lat = base_lat
                    lon = base_lon + 0.001 - (progress - 0.75) * 0.004

                # Add some noise
                lat += np.random.normal(0, 0.00005)
                lon += np.random.normal(0, 0.00005)

                timestamp = pd.Timestamp('2024-01-01') + pd.Timedelta(seconds=lap*100 + i*0.5)

                data.append({
                    'vehicle_number': 55,
                    'lap': lap,
                    'timestamp': timestamp,
                    'latitude': lat,
                    'longitude': lon,
                    'speed': speed
                })

        return pd.DataFrame(data)

    def test_identify_corners_synthetic(self):
        """Test corner identification with synthetic data."""
        # Create synthetic data with 4 known corners
        gps_with_speed = self.create_synthetic_gps_data(n_laps=3, points_per_lap=200)

        # Identify corners
        corners = identify_corners_from_gps(
            gps_with_speed,
            min_corners=3,
            max_corners=6,
            verbose=True
        )

        # Should find approximately 4 corners (may find 6 due to noise)
        assert 3 <= len(corners) <= 7, f"Expected 3-7 corners, found {len(corners)}"

        # Check DataFrame structure
        assert 'corner_id' in corners.columns
        assert 'latitude' in corners.columns
        assert 'longitude' in corners.columns
        assert 'min_speed' in corners.columns
        assert 'corner_type' in corners.columns

        # Corner IDs should be 1-indexed
        assert corners['corner_id'].min() == 1

        # Corner types should be valid
        valid_types = {'slow', 'medium', 'fast'}
        assert all(ct in valid_types for ct in corners['corner_type'])

        # Should have at least one slow corner
        assert 'slow' in corners['corner_type'].values

        print(f"\n✓ Found {len(corners)} corners in synthetic data")
        print(corners[['corner_id', 'corner_type', 'min_speed', 'latitude', 'longitude']])

    def test_identify_corners_sample_data(self):
        """Test corner identification with sample data (expected to skip due to sparse data)."""
        # Load GPS data for a vehicle with multiple laps
        gps = load_gps_data(SAMPLE_DATA, verbose=False)

        # Should have GPS data
        assert len(gps) > 0
        assert 'latitude' in gps.columns
        assert 'longitude' in gps.columns

        # Need speed data for corner identification
        # Load full telemetry to get speed
        from motorsport_modeling.data import load_telemetry
        telemetry = load_telemetry(SAMPLE_DATA, wide_format=True)

        # Merge GPS with speed
        if 'speed' not in telemetry.columns:
            pytest.skip("Speed data not available in sample")

        gps_with_speed = gps.merge(
            telemetry[['timestamp', 'speed']],
            on='timestamp',
            how='inner'
        )

        # Check if we have sufficient data
        if len(gps_with_speed) < 100 or gps_with_speed['speed'].notna().sum() < 50:
            pytest.skip("Sample data too sparse for corner identification. "
                       "This is expected - use full dataset for corner detection.")

        # If we get here, try corner identification
        corners = identify_corners_from_gps(
            gps_with_speed,
            min_corners=2,
            max_corners=20,
            verbose=True
        )

        # Should find some corners
        assert len(corners) > 0

    def test_identify_corners_single_lap(self):
        """Test corner identification with single lap using synthetic data."""
        # Create synthetic single lap
        gps_with_speed = self.create_synthetic_gps_data(n_laps=1, points_per_lap=200)

        # Should still work but may find fewer clusters
        with pytest.warns(UserWarning):  # May warn about single lap
            corners = identify_corners_from_gps(
                gps_with_speed,
                min_corners=2,  # Lower expectation for single lap
                verbose=False
            )

        # Should find at least one corner
        assert len(corners) >= 1

    def test_identify_corners_parameters(self):
        """Test corner identification with different parameters."""
        gps_with_speed = self.create_synthetic_gps_data(n_laps=3, points_per_lap=200)

        # Test with different corner count expectations
        corners1 = identify_corners_from_gps(
            gps_with_speed,
            min_corners=2,
            max_corners=20,
            verbose=False
        )

        # Test with different speed threshold
        corners2 = identify_corners_from_gps(
            gps_with_speed,
            min_corners=2,
            max_corners=20,
            speed_threshold_percentile=50,  # Higher threshold
            verbose=False
        )

        # Both should work
        assert len(corners1) > 0
        assert len(corners2) > 0

        # Higher threshold may find more corners (including faster ones)
        # But this depends on data distribution
        print(f"\n✓ Standard threshold: {len(corners1)} corners")
        print(f"✓ Higher threshold: {len(corners2)} corners")

    def test_corner_classification(self):
        """Test that corners are classified by speed correctly."""
        gps_with_speed = self.create_synthetic_gps_data(n_laps=3, points_per_lap=200)

        corners = identify_corners_from_gps(gps_with_speed, verbose=False)

        assert len(corners) > 0

        # Check classification logic
        for _, corner in corners.iterrows():
            speed = corner['min_speed']
            corner_type = corner['corner_type']

            if speed < 60:
                assert corner_type == 'slow', f"Corner at {speed} km/h should be 'slow'"
            elif speed < 90:
                assert corner_type == 'medium', f"Corner at {speed} km/h should be 'medium'"
            else:
                assert corner_type == 'fast', f"Corner at {speed} km/h should be 'fast'"


class TestGetCornerAtPosition:
    """Tests for finding corners at GPS positions."""

    def create_synthetic_gps_data(self, n_laps=3, points_per_lap=200):
        """Create synthetic GPS data - same as in TestGPSCornerIdentification."""
        data = []
        base_lat = 39.795
        base_lon = -86.235

        for lap in range(1, n_laps + 1):
            for i in range(points_per_lap):
                progress = i / points_per_lap
                corner_positions = [0.15, 0.35, 0.65, 0.85]
                corner_speeds = [55, 120, 80, 50]

                distances = [abs(progress - cp) for cp in corner_positions]
                nearest_corner_idx = distances.index(min(distances))
                distance_to_corner = distances[nearest_corner_idx]

                base_speed = 180
                if distance_to_corner < 0.05:
                    speed = corner_speeds[nearest_corner_idx] + \
                            (base_speed - corner_speeds[nearest_corner_idx]) * \
                            (distance_to_corner / 0.05)
                else:
                    speed = base_speed + np.random.normal(0, 5)

                if progress < 0.25:
                    lat = base_lat + progress * 0.004
                    lon = base_lon
                elif progress < 0.5:
                    lat = base_lat + 0.001
                    lon = base_lon + (progress - 0.25) * 0.004
                elif progress < 0.75:
                    lat = base_lat + 0.001 - (progress - 0.5) * 0.004
                    lon = base_lon + 0.001
                else:
                    lat = base_lat
                    lon = base_lon + 0.001 - (progress - 0.75) * 0.004

                lat += np.random.normal(0, 0.00005)
                lon += np.random.normal(0, 0.00005)

                timestamp = pd.Timestamp('2024-01-01') + pd.Timedelta(seconds=lap*100 + i*0.5)

                data.append({
                    'vehicle_number': 55,
                    'lap': lap,
                    'timestamp': timestamp,
                    'latitude': lat,
                    'longitude': lon,
                    'speed': speed
                })

        return pd.DataFrame(data)

    def test_get_corner_at_position_near_corner(self):
        """Test finding corner when position is near a known corner."""
        gps_with_speed = self.create_synthetic_gps_data(n_laps=3, points_per_lap=200)
        corners = identify_corners_from_gps(gps_with_speed, verbose=False)

        # Test with first corner's exact position
        corner1 = corners.iloc[0]
        corner_id = get_corner_at_position(
            corners,
            corner1['latitude'],
            corner1['longitude']
        )

        # Should find the corner
        assert corner_id == corner1['corner_id']

    def test_get_corner_at_position_far_from_corners(self):
        """Test that no corner is found when position is far from any corner."""
        gps_with_speed = self.create_synthetic_gps_data(n_laps=3, points_per_lap=200)
        corners = identify_corners_from_gps(gps_with_speed, verbose=False)

        # Test with position far from track (middle of ocean)
        corner_id = get_corner_at_position(
            corners,
            0.0,  # Equator
            0.0   # Prime meridian
        )

        # Should find no corner
        assert corner_id is None

    def test_get_corner_at_position_custom_distance(self):
        """Test custom max_distance parameter."""
        gps_with_speed = self.create_synthetic_gps_data(n_laps=3, points_per_lap=200)
        corners = identify_corners_from_gps(gps_with_speed, verbose=False)

        corner1 = corners.iloc[0]

        # Offset position slightly
        offset_lat = corner1['latitude'] + 0.0003  # ~33 meters
        offset_lon = corner1['longitude']

        # Should not find with tight tolerance
        corner_id_tight = get_corner_at_position(
            corners,
            offset_lat,
            offset_lon,
            max_distance=0.0001  # ~11 meters
        )
        assert corner_id_tight is None

        # Should find with loose tolerance (might be different corner if closer)
        corner_id_loose = get_corner_at_position(
            corners,
            offset_lat,
            offset_lon,
            max_distance=0.001  # ~111 meters
        )
        assert corner_id_loose is not None  # Should find some corner


class TestExtractCornerTelemetry:
    """Tests for extracting telemetry near corners."""

    def create_synthetic_gps_data(self, n_laps=3, points_per_lap=200):
        """Create synthetic GPS data - same as in other test classes."""
        data = []
        base_lat = 39.795
        base_lon = -86.235

        for lap in range(1, n_laps + 1):
            for i in range(points_per_lap):
                progress = i / points_per_lap
                corner_positions = [0.15, 0.35, 0.65, 0.85]
                corner_speeds = [55, 120, 80, 50]

                distances = [abs(progress - cp) for cp in corner_positions]
                nearest_corner_idx = distances.index(min(distances))
                distance_to_corner = distances[nearest_corner_idx]

                base_speed = 180
                if distance_to_corner < 0.05:
                    speed = corner_speeds[nearest_corner_idx] + \
                            (base_speed - corner_speeds[nearest_corner_idx]) * \
                            (distance_to_corner / 0.05)
                else:
                    speed = base_speed + np.random.normal(0, 5)

                if progress < 0.25:
                    lat = base_lat + progress * 0.004
                    lon = base_lon
                elif progress < 0.5:
                    lat = base_lat + 0.001
                    lon = base_lon + (progress - 0.25) * 0.004
                elif progress < 0.75:
                    lat = base_lat + 0.001 - (progress - 0.5) * 0.004
                    lon = base_lon + 0.001
                else:
                    lat = base_lat
                    lon = base_lon + 0.001 - (progress - 0.75) * 0.004

                lat += np.random.normal(0, 0.00005)
                lon += np.random.normal(0, 0.00005)

                timestamp = pd.Timestamp('2024-01-01') + pd.Timedelta(seconds=lap*100 + i*0.5)

                data.append({
                    'vehicle_number': 55,
                    'lap': lap,
                    'timestamp': timestamp,
                    'latitude': lat,
                    'longitude': lon,
                    'speed': speed
                })

        return pd.DataFrame(data)

    def test_extract_corner_telemetry_basic(self):
        """Test basic corner telemetry extraction."""
        gps_with_speed = self.create_synthetic_gps_data(n_laps=3, points_per_lap=200)
        corners = identify_corners_from_gps(gps_with_speed, verbose=False)

        # Separate into gps and telemetry for function call
        gps = gps_with_speed[['vehicle_number', 'lap', 'timestamp', 'latitude', 'longitude']]
        telemetry = gps_with_speed[['vehicle_number', 'lap', 'timestamp', 'speed']]

        # Extract telemetry for first corner
        corner_telemetry = extract_corner_telemetry(
            telemetry,
            gps,
            corners,
            corner_id=1,
            window_distance=100,  # 100 meters
            verbose=True
        )

        # Should have some data
        assert len(corner_telemetry) > 0

        # Should have GPS coordinates
        assert 'latitude' in corner_telemetry.columns
        assert 'longitude' in corner_telemetry.columns

    def test_extract_corner_telemetry_invalid_corner(self):
        """Test extraction with invalid corner ID."""
        gps_with_speed = self.create_synthetic_gps_data(n_laps=3, points_per_lap=200)
        corners = identify_corners_from_gps(gps_with_speed, verbose=False)

        gps = gps_with_speed[['vehicle_number', 'lap', 'timestamp', 'latitude', 'longitude']]
        telemetry = gps_with_speed[['vehicle_number', 'lap', 'timestamp', 'speed']]

        # Should raise error for invalid corner ID
        with pytest.raises(IndexError):
            extract_corner_telemetry(
                telemetry,
                gps,
                corners,
                corner_id=9999,  # Invalid
                verbose=False
            )


class TestValidateCornerIdentification:
    """Tests for corner identification validation."""

    def create_synthetic_gps_data(self, n_laps=3, points_per_lap=200):
        """Create synthetic GPS data - same as in other test classes."""
        data = []
        base_lat = 39.795
        base_lon = -86.235

        for lap in range(1, n_laps + 1):
            for i in range(points_per_lap):
                progress = i / points_per_lap
                corner_positions = [0.15, 0.35, 0.65, 0.85]
                corner_speeds = [55, 120, 80, 50]

                distances = [abs(progress - cp) for cp in corner_positions]
                nearest_corner_idx = distances.index(min(distances))
                distance_to_corner = distances[nearest_corner_idx]

                base_speed = 180
                if distance_to_corner < 0.05:
                    speed = corner_speeds[nearest_corner_idx] + \
                            (base_speed - corner_speeds[nearest_corner_idx]) * \
                            (distance_to_corner / 0.05)
                else:
                    speed = base_speed + np.random.normal(0, 5)

                if progress < 0.25:
                    lat = base_lat + progress * 0.004
                    lon = base_lon
                elif progress < 0.5:
                    lat = base_lat + 0.001
                    lon = base_lon + (progress - 0.25) * 0.004
                elif progress < 0.75:
                    lat = base_lat + 0.001 - (progress - 0.5) * 0.004
                    lon = base_lon + 0.001
                else:
                    lat = base_lat
                    lon = base_lon + 0.001 - (progress - 0.75) * 0.004

                lat += np.random.normal(0, 0.00005)
                lon += np.random.normal(0, 0.00005)

                timestamp = pd.Timestamp('2024-01-01') + pd.Timedelta(seconds=lap*100 + i*0.5)

                data.append({
                    'vehicle_number': 55,
                    'lap': lap,
                    'timestamp': timestamp,
                    'latitude': lat,
                    'longitude': lon,
                    'speed': speed
                })

        return pd.DataFrame(data)

    def test_validate_corner_identification_pass(self):
        """Test validation with reasonable corner count."""
        gps_with_speed = self.create_synthetic_gps_data(n_laps=3, points_per_lap=200)
        corners = identify_corners_from_gps(gps_with_speed, verbose=False)

        # Should pass validation with relaxed range
        result = validate_corner_identification(
            corners,
            expected_range=(1, 20),
            track_name="Test Track"
        )

        assert result is True

    def test_validate_corner_identification_fail_too_few(self):
        """Test validation fails with too few corners."""
        # Create dummy corners DataFrame
        corners = pd.DataFrame({
            'corner_id': [1, 2],
            'latitude': [39.79, 39.80],
            'longitude': [-86.23, -86.24],
            'min_speed': [80, 85],
            'corner_type': ['medium', 'medium']
        })

        # Should raise ValueError for too few corners
        with pytest.raises(ValueError, match="Found only 2 corners"):
            validate_corner_identification(
                corners,
                expected_range=(8, 15),
                track_name="Indianapolis"
            )

    def test_validate_corner_identification_warn_too_many(self):
        """Test validation warns with too many corners."""
        # Create dummy corners DataFrame with many corners
        corners = pd.DataFrame({
            'corner_id': range(1, 21),
            'latitude': [39.79 + i*0.001 for i in range(20)],
            'longitude': [-86.23 + i*0.001 for i in range(20)],
            'min_speed': [80] * 20,
            'corner_type': ['medium'] * 20
        })

        # Should warn but not fail
        with pytest.warns(UserWarning, match="Found 20 corners"):
            result = validate_corner_identification(
                corners,
                expected_range=(8, 15),
                track_name="Indianapolis"
            )

        # Still returns True (warning, not error)
        assert result is True


class TestGPSDataQuality:
    """Tests for GPS data quality and availability."""

    def test_gps_data_has_required_columns(self):
        """Test that GPS data has required columns after loading."""
        gps = load_gps_data(SAMPLE_DATA, verbose=False)

        required_columns = ['latitude', 'longitude', 'timestamp', 'vehicle_number', 'lap']
        for col in required_columns:
            assert col in gps.columns, f"Missing required column: {col}"

    def test_gps_coordinates_reasonable(self):
        """Test that GPS coordinates are in reasonable range for Indianapolis."""
        gps = load_gps_data(SAMPLE_DATA, verbose=False)

        # Indianapolis Motor Speedway is at approximately:
        # Latitude: 39.79°N, Longitude: -86.23°W

        # Coordinates should be roughly in Indiana
        # Allow wide range for sample data
        assert gps['latitude'].min() > 30, "Latitude too far south"
        assert gps['latitude'].max() < 50, "Latitude too far north"
        assert gps['longitude'].min() > -90, "Longitude too far west"
        assert gps['longitude'].max() < -80, "Longitude too far east"

        print(f"✓ GPS coordinates: lat {gps['latitude'].min():.2f} to {gps['latitude'].max():.2f}, "
              f"lon {gps['longitude'].min():.2f} to {gps['longitude'].max():.2f}")

    def test_gps_no_missing_values(self):
        """Test that GPS data has no missing coordinates (already filtered)."""
        gps = load_gps_data(SAMPLE_DATA, verbose=False)

        # load_gps_data should already filter out missing values
        assert gps['latitude'].notna().all()
        assert gps['longitude'].notna().all()
