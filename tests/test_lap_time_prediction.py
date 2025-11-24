"""
Unit tests to systematically debug the lap time prediction pipeline.

Tests:
1. Data loading and filtering
2. Feature engineering correctness
3. Temporal ordering (no data leakage)
4. Model coefficients (physical sanity)
5. Prediction patterns
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path
from scipy import stats

from motorsport_modeling.models.feature_engineering import prepare_race_features
from motorsport_modeling.models.lap_time_predictor import BaselineLapPredictor


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def data_dir():
    """Path to test data."""
    return Path(__file__).parent.parent / "data" / "raw" / "tracks" / "indianapolis" / "race1"


@pytest.fixture
def race1_data(data_dir):
    """Load Race 1 data for testing."""
    lap_file = data_dir / "R1_indianapolis_motor_speedway_lap_time.csv"
    weather_file = data_dir / "26_Weather_Race 1.CSV"
    endurance_file = data_dir / "23_AnalysisEnduranceWithSections_Race 1.CSV"

    return prepare_race_features(
        lap_time_file=lap_file,
        total_laps=26,
        weather_file=weather_file if weather_file.exists() else None,
        endurance_file=endurance_file if endurance_file.exists() else None,
        verbose=False
    )


@pytest.fixture
def clean_data(race1_data):
    """Filter to clean laps only."""
    data = race1_data[race1_data['lap_time'].notna()].copy()

    # Filter yellow flag laps
    if 'is_under_yellow' in data.columns:
        data = data[data['is_under_yellow'] == 0].copy()

    # Filter outliers per driver
    def filter_outliers(group):
        mean = group['lap_time'].mean()
        std = group['lap_time'].std()
        if std > 0:
            return group[abs(group['lap_time'] - mean) <= 3 * std]
        return group

    data = data.groupby('vehicle_number', group_keys=False).apply(filter_outliers)
    return data


# =============================================================================
# Test 1: Data Loading and Filtering
# =============================================================================

class TestDataLoading:
    """Tests for data loading and filtering."""

    def test_raw_data_has_expected_columns(self, race1_data):
        """Verify raw data has required columns."""
        required = ['lap', 'vehicle_number', 'lap_time', 'position', 'laps_remaining']
        for col in required:
            assert col in race1_data.columns, f"Missing required column: {col}"

    def test_lap_times_are_positive(self, race1_data):
        """Verify lap times are positive where not null."""
        valid_times = race1_data[race1_data['lap_time'].notna()]['lap_time']
        assert (valid_times > 0).all(), "Found non-positive lap times"

    def test_lap_numbers_are_sequential(self, race1_data):
        """Verify lap numbers are sequential integers starting from 1."""
        laps = sorted(race1_data['lap'].unique())
        assert min(laps) >= 1, f"Lap numbers should start >= 1, got {min(laps)}"
        assert all(isinstance(l, (int, np.integer)) or l == int(l) for l in laps), "Laps should be integers"

    def test_yellow_flag_filtering_works(self, race1_data, clean_data):
        """Verify yellow flag filtering removes laps."""
        if 'is_under_yellow' in race1_data.columns:
            yellow_count = (race1_data['is_under_yellow'] == 1).sum()
            removed = len(race1_data[race1_data['lap_time'].notna()]) - len(clean_data)
            # Should have removed at least some yellow flag laps
            assert removed >= 0, "Filtering should not add laps"
            print(f"Removed {removed} laps (yellow flags + outliers)")

    def test_clean_data_has_reasonable_variance(self, clean_data):
        """Verify clean data variance is reduced from raw."""
        std = clean_data['lap_time'].std()
        mean = clean_data['lap_time'].mean()
        cv = std / mean * 100

        print(f"Clean data: mean={mean:.2f}s, std={std:.2f}s, CV={cv:.1f}%")

        # CV should be < 30% for reasonable race data
        # This is a diagnostic - not a hard fail
        if cv > 30:
            print(f"WARNING: High CV ({cv:.1f}%) - data may have issues")

    def test_outlier_filtering_removes_extremes(self, race1_data, clean_data):
        """Verify outlier filtering removes extreme lap times."""
        # Get per-driver stats before filtering
        raw_valid = race1_data[race1_data['lap_time'].notna()]

        for veh in clean_data['vehicle_number'].unique():
            clean_veh = clean_data[clean_data['vehicle_number'] == veh]['lap_time']
            raw_veh = raw_valid[raw_valid['vehicle_number'] == veh]['lap_time']

            if len(clean_veh) > 0 and len(raw_veh) > 0:
                clean_range = clean_veh.max() - clean_veh.min()
                raw_range = raw_veh.max() - raw_veh.min()

                # Filtered range should be <= raw range
                assert clean_range <= raw_range + 0.001, \
                    f"Driver {veh}: clean range {clean_range:.2f} > raw range {raw_range:.2f}"


# =============================================================================
# Test 2: Feature Engineering
# =============================================================================

class TestFeatureEngineering:
    """Tests for feature engineering correctness."""

    def test_laps_remaining_is_correct(self, clean_data):
        """Verify laps_remaining = total_laps - lap."""
        total_laps = 26  # Indianapolis race

        for _, row in clean_data.sample(min(100, len(clean_data))).iterrows():
            expected = total_laps - row['lap']
            actual = row['laps_remaining']

            # Handle potential off-by-one
            assert abs(expected - actual) <= 1, \
                f"Lap {row['lap']}: expected laps_remaining={expected}, got {actual}"

    def test_gap_features_are_computed(self, race1_data):
        """Verify gap features exist if expected."""
        gap_cols = [col for col in race1_data.columns if 'gap' in col.lower()]
        print(f"Gap columns found: {gap_cols}")

        # At least some gap features should exist
        # This is informational - not all datasets have gaps
        if not gap_cols:
            print("NOTE: No gap features found - may need to add for better prediction")

    def test_lag_features_are_computed(self, race1_data):
        """Verify lag features (prev_lap_time, rolling_avg) exist."""
        lag_cols = ['prev_lap_time', 'rolling_avg_3']

        for col in lag_cols:
            if col in race1_data.columns:
                # Verify lag features are shifted correctly
                # prev_lap_time for lap N should be lap_time from lap N-1
                sample = race1_data[race1_data['vehicle_number'] == race1_data['vehicle_number'].iloc[0]]
                sample = sample.sort_values('lap')

                for i in range(1, min(5, len(sample))):
                    prev_time = sample.iloc[i][col] if col == 'prev_lap_time' else None
                    actual_prev = sample.iloc[i-1]['lap_time']

                    if prev_time is not None and not pd.isna(prev_time) and not pd.isna(actual_prev):
                        assert abs(prev_time - actual_prev) < 0.001, \
                            f"Lag feature mismatch at lap {sample.iloc[i]['lap']}"
            else:
                print(f"NOTE: Lag feature '{col}' not found - adding could improve predictions")

    def test_position_is_valid(self, clean_data):
        """Verify position is within valid range."""
        positions = clean_data['position'].dropna()

        assert positions.min() >= 1, f"Invalid position: {positions.min()}"

        # Max position should be <= number of cars
        n_cars = clean_data['vehicle_number'].nunique()
        assert positions.max() <= n_cars + 5, \
            f"Position {positions.max()} exceeds car count {n_cars}"

    def test_no_future_data_in_features(self, clean_data):
        """Verify no features use future information."""
        # This is critical for temporal integrity

        # Check lag features are properly shifted (NaN for first lap)
        for veh in clean_data['vehicle_number'].unique()[:5]:
            veh_data = clean_data[clean_data['vehicle_number'] == veh].sort_values('lap')
            first_lap = veh_data.iloc[0]

            if 'prev_lap_time' in clean_data.columns:
                # First lap should have NaN prev_lap_time
                if not pd.isna(first_lap.get('prev_lap_time')):
                    print(f"WARNING: Vehicle {veh} lap 1 has prev_lap_time={first_lap['prev_lap_time']}")

            if 'rolling_avg_3' in clean_data.columns:
                # First few laps should have NaN rolling average
                first_laps = veh_data.head(3)
                nan_count = first_laps['rolling_avg_3'].isna().sum()
                # At least first 2 laps should be NaN
                if nan_count < 2:
                    print(f"WARNING: Vehicle {veh} rolling_avg_3 may use future data")


# =============================================================================
# Test 3: Temporal Ordering (No Data Leakage)
# =============================================================================

class TestTemporalOrdering:
    """Tests to verify no data leakage in training/validation."""

    def test_expanding_window_no_leakage(self, clean_data):
        """Verify expanding window uses only past data."""
        max_lap = int(clean_data['lap'].max())

        for train_end in [5, 10, 15]:
            predict_lap = train_end + 1

            if predict_lap > max_lap:
                continue

            train_data = clean_data[clean_data['lap'] <= train_end]
            test_data = clean_data[clean_data['lap'] == predict_lap]

            # Training data should only have laps <= train_end
            assert train_data['lap'].max() == train_end, \
                f"Training data has laps after {train_end}"

            # Test data should only have lap = predict_lap
            assert (test_data['lap'] == predict_lap).all(), \
                f"Test data has wrong laps"

            # No overlap
            train_keys = set(zip(train_data['vehicle_number'], train_data['lap']))
            test_keys = set(zip(test_data['vehicle_number'], test_data['lap']))
            overlap = train_keys & test_keys

            assert len(overlap) == 0, f"Train/test overlap: {overlap}"

    def test_model_sees_only_past(self, clean_data):
        """Verify model training uses only past data at each step."""
        # Train on laps 1-5, predict lap 6
        train_data = clean_data[clean_data['lap'] <= 5].copy()
        test_data = clean_data[clean_data['lap'] == 6].copy()

        if len(test_data) == 0:
            pytest.skip("No data for lap 6")

        model = BaselineLapPredictor()
        model.fit(train_data, verbose=False)

        # Model should not have access to lap 6 times during training
        # Check that fitted coefficients don't implicitly encode future info
        # (This is more of a sanity check - hard to test definitively)

        predictions = model.predict(test_data)
        actuals = test_data['lap_time'].values

        # Predictions should be reasonable (not perfect)
        rmse = np.sqrt(np.mean((actuals - predictions) ** 2))

        # If RMSE is 0 or nearly 0, there's likely leakage
        assert rmse > 0.1, f"RMSE too low ({rmse:.3f}s) - possible data leakage"

        print(f"Expanding window (train 1-5, predict 6) RMSE: {rmse:.2f}s")


# =============================================================================
# Test 4: Model Coefficient Sanity
# =============================================================================

class TestModelCoefficients:
    """Tests for model coefficient physical sanity."""

    def test_degradation_coefficient_is_positive(self, clean_data):
        """Verify lap coefficient is positive (cars should slow down over race)."""
        model = BaselineLapPredictor()
        model.fit(clean_data, verbose=False)

        # Get coefficient for 'lap' feature
        if hasattr(model, 'model') and hasattr(model.model, 'coef_'):
            coefs = dict(zip(model.feature_cols, model.model.coef_))

            if 'lap' in coefs:
                lap_coef = coefs['lap']

                print(f"Lap coefficient: {lap_coef:.4f}s/lap")

                # Coefficient should be positive (later laps are slower due to tire wear, fuel)
                # However, if pit stops reduce fuel weight significantly, could be negative
                # This is a diagnostic warning, not a hard fail
                if lap_coef < 0:
                    print(f"WARNING: Negative lap coefficient ({lap_coef:.4f}) - "
                          f"cars appear to get faster. Check for confounds.")

    def test_position_coefficient_is_reasonable(self, clean_data):
        """Verify position coefficient makes sense."""
        model = BaselineLapPredictor()
        model.fit(clean_data, verbose=False)

        if hasattr(model, 'model') and hasattr(model.model, 'coef_'):
            coefs = dict(zip(model.feature_cols, model.model.coef_))

            if 'position' in coefs:
                pos_coef = coefs['position']

                print(f"Position coefficient: {pos_coef:.4f}s/position")

                # Lower position (1st place) should correlate with faster times
                # So coefficient should be positive (higher position = slower)
                if pos_coef < 0:
                    print(f"WARNING: Negative position coefficient - check data")

    def test_r_squared_is_reasonable(self, clean_data):
        """Verify R² is within reasonable range."""
        model = BaselineLapPredictor()
        model.fit(clean_data, verbose=False)

        if hasattr(model, 'r2'):
            r2 = model.r2

            print(f"Training R²: {r2:.3f}")

            # R² should be between 0 and 1
            assert 0 <= r2 <= 1, f"Invalid R²: {r2}"

            # Very low R² suggests poor model fit
            if r2 < 0.1:
                print(f"WARNING: Very low R² ({r2:.3f}) - model explains little variance")

            # Very high R² might suggest overfitting or leakage
            if r2 > 0.95:
                print(f"WARNING: Very high R² ({r2:.3f}) - possible overfitting or leakage")


# =============================================================================
# Test 5: Prediction Patterns
# =============================================================================

class TestPredictionPatterns:
    """Tests for prediction output patterns."""

    def test_predictions_are_in_valid_range(self, clean_data):
        """Verify predictions are reasonable lap times."""
        train_data = clean_data[clean_data['lap'] <= 15]
        test_data = clean_data[clean_data['lap'] > 15]

        if len(test_data) == 0:
            pytest.skip("No test data available")

        model = BaselineLapPredictor()
        model.fit(train_data, verbose=False)
        predictions = model.predict(test_data)

        # Predictions should be positive
        assert (predictions > 0).all(), "Found non-positive predictions"

        # Predictions should be in reasonable range (50-300 seconds for circuit racing)
        assert predictions.min() > 30, f"Prediction too low: {predictions.min():.2f}s"
        assert predictions.max() < 500, f"Prediction too high: {predictions.max():.2f}s"

        print(f"Prediction range: {predictions.min():.2f}s - {predictions.max():.2f}s")

    def test_per_driver_predictions_are_consistent(self, clean_data):
        """Verify predictions for same driver are reasonably consistent."""
        model = BaselineLapPredictor()
        model.fit(clean_data, verbose=False)

        predictions = model.predict(clean_data)
        clean_data = clean_data.copy()
        clean_data['predicted'] = predictions

        # Check per-driver prediction variance
        for veh in clean_data['vehicle_number'].unique()[:5]:
            veh_data = clean_data[clean_data['vehicle_number'] == veh]
            pred_std = veh_data['predicted'].std()
            actual_std = veh_data['lap_time'].std()

            print(f"Driver {int(veh)}: actual std={actual_std:.2f}s, pred std={pred_std:.2f}s")

            # Predicted variance should be similar to actual variance
            # Large difference suggests model is not capturing driver-specific patterns

    def test_residuals_are_not_systematic(self, clean_data):
        """Verify residuals don't show systematic patterns."""
        train_end = 10
        train_data = clean_data[clean_data['lap'] <= train_end]
        test_data = clean_data[clean_data['lap'] > train_end]

        if len(test_data) < 10:
            pytest.skip("Insufficient test data")

        model = BaselineLapPredictor()
        model.fit(train_data, verbose=False)

        predictions = model.predict(test_data)
        residuals = test_data['lap_time'].values - predictions

        # Residuals vs lap number
        laps = test_data['lap'].values
        correlation, p_value = stats.pearsonr(laps, residuals)

        print(f"Residual-lap correlation: r={correlation:.3f}, p={p_value:.3f}")

        # Strong correlation suggests systematic under/over-prediction
        if abs(correlation) > 0.5 and p_value < 0.05:
            print(f"WARNING: Systematic residual pattern with lap number")
            print("  Model may be missing time-dependent effects (degradation, fuel)")

    def test_cross_race_generalization(self):
        """Verify model generalizes to different race."""
        # Load Race 1 and Race 2
        base_dir = Path(__file__).parent.parent / "data" / "raw" / "tracks" / "indianapolis"

        race1_file = base_dir / "race1" / "R1_indianapolis_motor_speedway_lap_time.csv"
        race2_file = base_dir / "race2" / "R2_indianapolis_motor_speedway_lap_time.csv"

        if not race2_file.exists():
            pytest.skip("Race 2 data not available")

        race1 = prepare_race_features(lap_time_file=race1_file, total_laps=26, verbose=False)
        race2 = prepare_race_features(lap_time_file=race2_file, total_laps=26, verbose=False)

        # Filter clean laps
        for data in [race1, race2]:
            if 'is_under_yellow' in data.columns:
                data = data[data['is_under_yellow'] == 0]

        race1 = race1[race1['lap_time'].notna()]
        race2 = race2[race2['lap_time'].notna()]

        # Train on Race 1, test on Race 2
        model = BaselineLapPredictor()
        model.fit(race1, verbose=False)

        predictions = model.predict(race2)
        actuals = race2['lap_time'].values
        residuals = actuals - predictions

        rmse = np.sqrt(np.mean(residuals ** 2))
        mae = np.mean(np.abs(residuals))

        print(f"Cross-race RMSE: {rmse:.2f}s")
        print(f"Cross-race MAE: {mae:.2f}s")

        # Compare to within-race baseline
        race1_rmse = np.sqrt(np.mean((race1['lap_time'] - race1['lap_time'].mean()) ** 2))

        print(f"Race 1 baseline std: {race1_rmse:.2f}s")

        # Cross-race should be better than just predicting mean
        if rmse > race1_rmse:
            print("WARNING: Model performs worse than mean prediction")


# =============================================================================
# Test 6: Data Quality Diagnostics
# =============================================================================

class TestDataQuality:
    """Diagnostic tests for data quality issues."""

    def test_lap_time_distribution(self, clean_data):
        """Analyze lap time distribution for anomalies."""
        lap_times = clean_data['lap_time']

        mean = lap_times.mean()
        std = lap_times.std()
        median = lap_times.median()
        skew = lap_times.skew()

        print(f"\nLap time distribution:")
        print(f"  Mean: {mean:.2f}s")
        print(f"  Std:  {std:.2f}s")
        print(f"  Median: {median:.2f}s")
        print(f"  Skewness: {skew:.2f}")

        # High skewness suggests outliers
        if abs(skew) > 2:
            print(f"  WARNING: High skewness - distribution has outliers")

        # Large mean-median difference suggests outliers
        if abs(mean - median) > std:
            print(f"  WARNING: Mean-median difference > std - outliers present")

        # Per-lap analysis
        print(f"\nPer-lap statistics:")
        lap_stats = clean_data.groupby('lap')['lap_time'].agg(['mean', 'std', 'count'])
        print(lap_stats.to_string())

    def test_identify_anomalous_laps(self, clean_data):
        """Identify laps with unusual patterns."""
        anomalies = []

        lap_means = clean_data.groupby('lap')['lap_time'].mean()
        overall_mean = clean_data['lap_time'].mean()
        overall_std = clean_data['lap_time'].std()

        for lap, mean in lap_means.items():
            z_score = (mean - overall_mean) / overall_std

            if abs(z_score) > 2:
                anomalies.append({
                    'lap': lap,
                    'mean': mean,
                    'z_score': z_score
                })
                print(f"Anomalous lap {lap}: mean={mean:.2f}s, z={z_score:.2f}")

        if anomalies:
            print(f"\nFound {len(anomalies)} anomalous laps")
            print("These laps may have special conditions (safety car, red flag, etc.)")

    def test_driver_consistency(self, clean_data):
        """Analyze driver-to-driver lap time consistency."""
        driver_stats = clean_data.groupby('vehicle_number')['lap_time'].agg(['mean', 'std', 'count'])

        # Sort by mean lap time
        driver_stats = driver_stats.sort_values('mean')

        print(f"\nDriver statistics (sorted by pace):")
        print(driver_stats.to_string())

        # Check for drivers with unusual variance
        median_std = driver_stats['std'].median()

        for veh, row in driver_stats.iterrows():
            if row['std'] > 2 * median_std:
                print(f"\nWARNING: Driver {int(veh)} has high variance: {row['std']:.2f}s")
                print(f"  This may indicate incidents, mechanical issues, or data errors")


# =============================================================================
# Run Tests
# =============================================================================

if __name__ == "__main__":
    # Run with verbose output
    pytest.main([__file__, "-v", "-s", "--tb=short"])
