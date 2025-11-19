"""
Validate relative performance prediction model.

Instead of predicting absolute lap time (which varies with race events),
predict lap_time - field_median for each lap. This removes the common
mode signal from yellow flags, weather changes, etc.

Target: Predict how much faster/slower a driver is vs field on each lap.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from scipy import stats
from typing import List, Dict
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import GradientBoostingRegressor

from motorsport_modeling.models.feature_engineering import prepare_race_features


def add_relative_performance(data: pd.DataFrame) -> pd.DataFrame:
    """
    Add relative performance target: lap_time - field_median.

    This normalizes out race events that affect all drivers equally.
    """
    df = data.copy()

    # Compute field median per lap
    field_median = df.groupby('lap')['lap_time'].median()
    df['field_median'] = df['lap'].map(field_median)

    # Relative performance (negative = faster than field)
    df['relative_time'] = df['lap_time'] - df['field_median']

    return df


def filter_clean_laps(data: pd.DataFrame, verbose: bool = True) -> pd.DataFrame:
    """Filter out yellow flag laps and outliers."""
    original_count = len(data)

    if 'is_under_yellow' in data.columns:
        data = data[data['is_under_yellow'] == 0].copy()
        if verbose:
            print(f"  Removed {original_count - len(data)} yellow flag laps")

    # Filter outliers per driver
    def filter_outliers(group):
        mean = group['lap_time'].mean()
        std = group['lap_time'].std()
        if std > 0:
            return group[abs(group['lap_time'] - mean) <= 3 * std]
        return group

    before_outlier = len(data)
    data = data.groupby('vehicle_number', group_keys=False).apply(filter_outliers)

    if verbose:
        print(f"  Removed {before_outlier - len(data)} outlier laps")
        print(f"  Clean samples: {len(data)}")

    return data


class RelativePerformancePredictor:
    """
    Predicts relative performance (lap_time - field_median).

    Features:
    - position: current race position
    - gap_to_ahead/behind: pressure from adjacent cars
    - prev_relative: previous lap relative performance
    - driver baseline: average relative performance in early laps
    """

    def __init__(self, use_gbm: bool = False):
        if use_gbm:
            self.model = GradientBoostingRegressor(
                n_estimators=50,
                max_depth=3,
                learning_rate=0.1,
                random_state=42
            )
        else:
            self.model = LinearRegression()

        self.feature_cols = []
        self.driver_baselines = {}
        self.is_fitted = False

    def fit(self, df: pd.DataFrame, verbose: bool = True) -> 'RelativePerformancePredictor':
        """Fit the model."""
        # Compute driver baselines from early laps (laps 3-5)
        early_laps = df[(df['lap'] >= 3) & (df['lap'] <= 5)]
        self.driver_baselines = early_laps.groupby('vehicle_number')['relative_time'].mean().to_dict()

        # Add baseline feature
        df = df.copy()
        df['driver_baseline'] = df['vehicle_number'].map(self.driver_baselines).fillna(0)

        # Add previous relative performance
        df = df.sort_values(['vehicle_number', 'lap'])
        df['prev_relative'] = df.groupby('vehicle_number')['relative_time'].shift(1)
        df['prev_relative'] = df['prev_relative'].fillna(df['driver_baseline'])

        # Select features
        self.feature_cols = [
            'position',
            'gap_to_ahead',
            'gap_to_behind',
            'driver_baseline',
            'prev_relative'
        ]

        # Filter rows with all features available
        valid = df.dropna(subset=self.feature_cols + ['relative_time'])

        X = valid[self.feature_cols].values
        y = valid['relative_time'].values

        self.model.fit(X, y)
        self.is_fitted = True

        if verbose:
            print(f"Fitted on {len(valid)} samples")

            # Show feature importances for GBM
            if hasattr(self.model, 'feature_importances_'):
                importances = list(zip(self.feature_cols, self.model.feature_importances_))
                importances.sort(key=lambda x: -x[1])
                print("Feature importances:")
                for feat, imp in importances:
                    print(f"  {feat}: {imp:.3f}")

        return self

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        """Predict relative performance."""
        if not self.is_fitted:
            raise ValueError("Model not fitted")

        df = df.copy()

        # Add baseline
        df['driver_baseline'] = df['vehicle_number'].map(self.driver_baselines).fillna(0)

        # Add previous relative (for test data, use baseline if not available)
        df = df.sort_values(['vehicle_number', 'lap'])
        df['prev_relative'] = df.groupby('vehicle_number')['relative_time'].shift(1)
        df['prev_relative'] = df['prev_relative'].fillna(df['driver_baseline'])

        X = df[self.feature_cols].values
        return self.model.predict(X)


def expanding_window_validation(
    data: pd.DataFrame,
    min_train_laps: int = 5,
    use_gbm: bool = False,
    verbose: bool = True
) -> Dict:
    """
    Expanding window validation for relative performance.
    """
    max_lap = int(data['lap'].max())

    all_predictions = []
    all_actuals = []
    per_lap_rmse = []

    if verbose:
        print(f"\nExpanding window: train from lap {min_train_laps}, predict one-step-ahead")

    for train_end in range(min_train_laps, max_lap):
        predict_lap = train_end + 1

        train_data = data[data['lap'] <= train_end].copy()
        test_data = data[data['lap'] == predict_lap].copy()

        if len(test_data) == 0:
            continue

        # Fit model
        model = RelativePerformancePredictor(use_gbm=use_gbm)
        model.fit(train_data, verbose=False)

        # Predict
        predictions = model.predict(test_data)
        actuals = test_data['relative_time'].values

        # Store
        all_predictions.extend(predictions)
        all_actuals.extend(actuals)

        # Per-lap RMSE
        lap_rmse = np.sqrt(np.mean((actuals - predictions) ** 2))
        per_lap_rmse.append({
            'train_end': train_end,
            'predict_lap': predict_lap,
            'rmse': lap_rmse,
            'n_samples': len(test_data)
        })

        if verbose and predict_lap % 5 == 0:
            print(f"  Train 1-{train_end}, predict lap {predict_lap}: RMSE = {lap_rmse:.3f}s")

    # Overall metrics
    all_predictions = np.array(all_predictions)
    all_actuals = np.array(all_actuals)
    residuals = all_actuals - all_predictions

    rmse = np.sqrt(np.mean(residuals ** 2))
    mae = np.mean(np.abs(residuals))

    if verbose:
        print(f"\n  Overall RMSE: {rmse:.3f}s")
        print(f"  Overall MAE: {mae:.3f}s")

    return {
        'rmse': rmse,
        'mae': mae,
        'per_lap_rmse': per_lap_rmse,
        'predictions': all_predictions,
        'actuals': all_actuals
    }


def position_prediction_validation(
    data: pd.DataFrame,
    from_lap: int = 15,
    verbose: bool = True
) -> Dict:
    """
    Validate ability to predict final positions from mid-race.

    This is more relevant for race strategy than exact lap times.
    """
    train_data = data[data['lap'] <= from_lap].copy()
    remaining_data = data[data['lap'] > from_lap].copy()

    if len(remaining_data) == 0:
        return {'error': 'No remaining data'}

    # Fit model
    model = RelativePerformancePredictor(use_gbm=True)
    model.fit(train_data, verbose=False)

    # Predict remaining relative performance
    predictions = model.predict(remaining_data)
    remaining_data['predicted_relative'] = predictions

    # Sum predicted relative times per driver
    predicted_total_relative = remaining_data.groupby('vehicle_number')['predicted_relative'].sum()
    actual_total_relative = remaining_data.groupby('vehicle_number')['relative_time'].sum()

    # Current cumulative at from_lap
    current = data[data['lap'] == from_lap].set_index('vehicle_number')['cumulative_time']

    # Predicted final order (lower is better)
    predicted_order = (current + predicted_total_relative).sort_values()
    actual_order = (current + actual_total_relative).sort_values()

    predicted_ranks = {v: i+1 for i, v in enumerate(predicted_order.index)}
    actual_ranks = {v: i+1 for i, v in enumerate(actual_order.index)}

    # Compare ranks
    rank_errors = []
    for v in predicted_ranks:
        if v in actual_ranks:
            error = abs(predicted_ranks[v] - actual_ranks[v])
            rank_errors.append(error)

    mean_rank_error = np.mean(rank_errors)
    winner_correct = list(predicted_order.index)[0] == list(actual_order.index)[0]
    podium_correct = set(list(predicted_order.index)[:3]) == set(list(actual_order.index)[:3])

    if verbose:
        print(f"\n  From lap {from_lap}:")
        print(f"  Mean position error: {mean_rank_error:.1f} positions")
        print(f"  Winner correct: {winner_correct}")
        print(f"  Podium correct (any order): {podium_correct}")
        print(f"  Predicted winner: {list(predicted_order.index)[0]}")
        print(f"  Actual winner: {list(actual_order.index)[0]}")

    return {
        'from_lap': from_lap,
        'mean_rank_error': mean_rank_error,
        'winner_correct': winner_correct,
        'podium_correct': podium_correct,
        'predicted_winner': list(predicted_order.index)[0],
        'actual_winner': list(actual_order.index)[0]
    }


def main():
    print("=" * 70)
    print("RELATIVE PERFORMANCE PREDICTION VALIDATION")
    print("Predicting lap_time - field_median to normalize race events")
    print("=" * 70)

    # Load data
    base_dir = Path(__file__).parent.parent / "data" / "raw" / "tracks" / "indianapolis"

    print("\n--- Loading Race 1 ---")
    race1_file = base_dir / "race1" / "R1_indianapolis_motor_speedway_lap_time.csv"
    race1_weather = base_dir / "race1" / "26_Weather_Race 1.CSV"
    race1_endurance = base_dir / "race1" / "23_AnalysisEnduranceWithSections_Race 1.CSV"

    race1_data = prepare_race_features(
        lap_time_file=race1_file,
        total_laps=26,
        weather_file=race1_weather if race1_weather.exists() else None,
        endurance_file=race1_endurance if race1_endurance.exists() else None,
        verbose=False
    )

    race1_data = race1_data[race1_data['lap_time'].notna()].copy()
    race1_data = filter_clean_laps(race1_data, verbose=True)

    # Add relative performance target
    race1_data = add_relative_performance(race1_data)

    print(f"\nRelative performance stats:")
    print(f"  Mean: {race1_data['relative_time'].mean():.3f}s")
    print(f"  Std:  {race1_data['relative_time'].std():.3f}s")
    print(f"  Range: {race1_data['relative_time'].min():.1f}s to {race1_data['relative_time'].max():.1f}s")

    # Compare to absolute lap time stats
    print(f"\nAbsolute lap time stats (for comparison):")
    print(f"  Mean: {race1_data['lap_time'].mean():.3f}s")
    print(f"  Std:  {race1_data['lap_time'].std():.3f}s")

    # =================================================================
    # Test 1: Expanding Window Validation (Linear)
    # =================================================================
    print("\n" + "=" * 70)
    print("TEST 1: EXPANDING WINDOW (LINEAR REGRESSION)")
    print("=" * 70)

    linear_results = expanding_window_validation(
        race1_data,
        min_train_laps=5,
        use_gbm=False,
        verbose=True
    )

    # =================================================================
    # Test 2: Expanding Window Validation (GBM)
    # =================================================================
    print("\n" + "=" * 70)
    print("TEST 2: EXPANDING WINDOW (GRADIENT BOOSTING)")
    print("=" * 70)

    gbm_results = expanding_window_validation(
        race1_data,
        min_train_laps=5,
        use_gbm=True,
        verbose=True
    )

    # =================================================================
    # Test 3: Position Prediction
    # =================================================================
    print("\n" + "=" * 70)
    print("TEST 3: POSITION PREDICTION FROM MID-RACE")
    print("=" * 70)

    for from_lap in [10, 15, 20]:
        pos_results = position_prediction_validation(
            race1_data,
            from_lap=from_lap,
            verbose=True
        )

    # =================================================================
    # Test 4: Cross-Race Validation
    # =================================================================
    print("\n" + "=" * 70)
    print("TEST 4: CROSS-RACE VALIDATION")
    print("=" * 70)

    # Load Race 2
    race2_file = base_dir / "race2" / "R2_indianapolis_motor_speedway_lap_time.csv"
    race2_weather = base_dir / "race2" / "26_Weather_Race 2.CSV"
    race2_endurance = base_dir / "race2" / "23_AnalysisEnduranceWithSections_Race 2.CSV"

    race2_data = prepare_race_features(
        lap_time_file=race2_file,
        total_laps=26,
        weather_file=race2_weather if race2_weather.exists() else None,
        endurance_file=race2_endurance if race2_endurance.exists() else None,
        verbose=False
    )

    race2_data = race2_data[race2_data['lap_time'].notna()].copy()
    race2_data = filter_clean_laps(race2_data, verbose=True)
    race2_data = add_relative_performance(race2_data)

    # Train on Race 1, test on Race 2
    print("\n--- Training on Race 1, Testing on Race 2 ---")

    model = RelativePerformancePredictor(use_gbm=True)
    model.fit(race1_data, verbose=True)

    predictions = model.predict(race2_data)
    actuals = race2_data['relative_time'].values

    rmse = np.sqrt(np.mean((actuals - predictions) ** 2))
    mae = np.mean(np.abs(actuals - predictions))

    print(f"\nCross-race results:")
    print(f"  RMSE: {rmse:.3f}s")
    print(f"  MAE:  {mae:.3f}s")

    # =================================================================
    # Summary
    # =================================================================
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    print("\n--- RMSE by Model ---")
    print(f"{'Model':<40} {'RMSE':<10}")
    print("-" * 50)
    print(f"{'Linear (relative performance)':<40} {linear_results['rmse']:.3f}s")
    print(f"{'GBM (relative performance)':<40} {gbm_results['rmse']:.3f}s")
    print(f"{'Cross-race GBM':<40} {rmse:.3f}s")

    # Compare to baseline std
    baseline_std = race1_data['relative_time'].std()
    print(f"\nBaseline (std of relative_time): {baseline_std:.3f}s")

    # Success criteria
    print("\n--- SUCCESS CRITERIA ---")

    rel_pass = gbm_results['rmse'] < 1.0
    cross_pass = rmse < 1.5

    print(f"Within-race RMSE < 1.0s: {'PASS' if rel_pass else 'FAIL'} ({gbm_results['rmse']:.3f}s)")
    print(f"Cross-race RMSE < 1.5s: {'PASS' if cross_pass else 'FAIL'} ({rmse:.3f}s)")

    # Improvement over absolute
    print(f"\nImprovement over absolute lap time prediction:")
    print(f"  Relative time std = {baseline_std:.3f}s vs Absolute time std = {race1_data['lap_time'].std():.3f}s")
    print(f"  Variance reduction: {100 * (1 - baseline_std**2 / race1_data['lap_time'].std()**2):.1f}%")


if __name__ == "__main__":
    main()
