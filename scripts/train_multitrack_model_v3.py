"""
Train improved multi-track model with lag features and top speed.

Improvements over v2:
1. Add prev_lap_time - shows current momentum
2. Add rolling_avg_3 - smoothed pace
3. Add top_speed - indicates setup/aggression
4. Evaluate cross-race same-track prediction

Usage:
    uv run python scripts/train_multitrack_model_v3.py
"""

from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_squared_error, mean_absolute_error

# Track lengths in km (from public data)
TRACK_LENGTHS = {
    'barber': 3.7,
    'cota': 5.5,
    'indianapolis': 4.0,
    'road-america': 6.5,
    'sebring': 5.9,
    'sonoma': 4.0,
    'vir': 5.3,
}


def add_track_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add track-specific features."""
    df = df.copy()

    # Add track length
    df['track_length_km'] = df['track'].map(TRACK_LENGTHS)

    # Calculate track mean lap times from the data
    track_means = df.groupby('track')['lap_time'].mean()
    track_stds = df.groupby('track')['lap_time'].std()

    df['track_mean_lap'] = df['track'].map(track_means)
    df['track_std_lap'] = df['track'].map(track_stds)

    return df


def main():
    data_dir = Path(__file__).parent.parent / 'data' / 'processed'
    output_dir = Path(__file__).parent.parent / 'outputs'
    output_dir.mkdir(exist_ok=True)

    # Load data
    print("=" * 70)
    print("LOADING AND PREPARING DATA")
    print("=" * 70)

    df = pd.read_csv(data_dir / 'multitrack_features.csv')

    # Add track features
    df = add_track_features(df)

    # Fill NaN values in top_speed with track median
    if 'top_speed' in df.columns:
        df['top_speed'] = df.groupby('track')['top_speed'].transform(
            lambda x: x.fillna(x.median())
        )
        # If still NaN (entire track missing), use overall median
        df['top_speed'] = df['top_speed'].fillna(df['top_speed'].median())

    print(f"Total samples: {len(df)}")
    print(f"Tracks: {df['track'].nunique()}")

    # Show track stats
    print("\nTrack statistics:")
    track_stats = df.groupby('track').agg({
        'lap_time': ['mean', 'std', 'count'],
        'track_length_km': 'first',
    }).round(1)
    track_stats.columns = ['mean_lap', 'std_lap', 'samples', 'length_km']
    print(track_stats.to_string())

    # Base feature columns (from v1)
    base_features = [
        'lap',
        'position',
        'gap_to_leader',
        'gap_to_ahead',
        'gap_to_behind',
        'gap_delta_ahead',
        'gap_delta_behind',
        'race_progress',
        'fuel_load_estimate',
        'air_temp',
        'track_temp',
        'humidity',
        'is_under_yellow'
    ]

    # Track features (from v2)
    track_features = [
        'track_length_km',
        'track_mean_lap',
    ]

    # NEW lag features (v3)
    lag_features = [
        'prev_lap_time',
        'rolling_avg_3',
        'top_speed',
    ]

    # =========================================================================
    # MODEL 1: V2 features (base + track)
    # =========================================================================
    print("\n" + "=" * 70)
    print("MODEL 1: V2 FEATURES (BASE + TRACK)")
    print("=" * 70)

    features_v2 = base_features + track_features
    results_v2 = evaluate_model(df, features_v2, "V2")

    # =========================================================================
    # MODEL 2: V3 features (base + track + lag)
    # =========================================================================
    print("\n" + "=" * 70)
    print("MODEL 2: V3 FEATURES (BASE + TRACK + LAG)")
    print("=" * 70)

    features_v3 = base_features + track_features + lag_features
    results_v3 = evaluate_model(df, features_v3, "V3")

    # =========================================================================
    # COMPARISON
    # =========================================================================
    print("\n" + "=" * 70)
    print("MODEL COMPARISON: CROSS-TRACK")
    print("=" * 70)

    print("\nMean Test RMSE by Model:")
    print(f"  V2 (base + track):       {results_v2['test_rmse'].mean():.2f}s")
    print(f"  V3 (+ lag features):     {results_v3['test_rmse'].mean():.2f}s")

    improvement = results_v2['test_rmse'].mean() - results_v3['test_rmse'].mean()
    print(f"\nImprovement from lag features: {improvement:.2f}s")

    # =========================================================================
    # CROSS-RACE SAME-TRACK EVALUATION
    # =========================================================================
    print("\n" + "=" * 70)
    print("CROSS-RACE SAME-TRACK EVALUATION")
    print("=" * 70)

    # Train on race 1 of each track, test on race 2
    cross_race_results = evaluate_cross_race(df, features_v3)

    # Detailed error analysis
    detailed_error_analysis(df, features_v3)

    # =========================================================================
    # TRAIN FINAL MODEL
    # =========================================================================
    print("\n" + "=" * 70)
    print("FINAL MODEL: FEATURE IMPORTANCES")
    print("=" * 70)

    # Train on all data
    available_features = [f for f in features_v3 if f in df.columns]

    model = GradientBoostingRegressor(
        n_estimators=100,
        max_depth=5,
        learning_rate=0.1,
        random_state=42
    )

    X = df[available_features].values
    y = df['lap_time'].values
    model.fit(X, y)

    importances = pd.DataFrame({
        'feature': available_features,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)

    print("\nFeature Importances (Full Model):")
    for _, row in importances.iterrows():
        print(f"  {row['feature']}: {row['importance']:.4f}")

    # Highlight new features
    print("\nNew lag feature importance:")
    for feat in lag_features:
        if feat in importances['feature'].values:
            imp = importances[importances['feature'] == feat]['importance'].values[0]
            print(f"  {feat}: {imp:.4f}")

    # Save results
    comparison = pd.DataFrame({
        'track': results_v2['test_track'],
        'v2_rmse': results_v2['test_rmse'].values,
        'v3_rmse': results_v3['test_rmse'].values
    })

    comparison_file = output_dir / 'multitrack_model_v3_comparison.csv'
    comparison.to_csv(comparison_file, index=False)
    print(f"\nSaved: {comparison_file}")

    print("\n" + "=" * 70)
    print("DONE")
    print("=" * 70)


def evaluate_model(df: pd.DataFrame, feature_cols: list, model_name: str) -> pd.DataFrame:
    """Evaluate model with leave-one-track-out CV."""
    available_features = [f for f in feature_cols if f in df.columns]

    results = []

    for test_track in df['track'].unique():
        train = df[df['track'] != test_track].copy()
        test = df[df['track'] == test_track].copy()

        if len(test) == 0:
            continue

        # For track_mean_lap, use overall mean as fallback for unseen track
        if 'track_mean_lap' in available_features:
            test_track_mean = train['lap_time'].mean()
            test = test.copy()
            test['track_mean_lap'] = test_track_mean

        model = GradientBoostingRegressor(
            n_estimators=100,
            max_depth=5,
            learning_rate=0.1,
            random_state=42
        )

        X_train = train[available_features].values
        y_train = train['lap_time'].values
        X_test = test[available_features].values
        y_test = test['lap_time'].values

        model.fit(X_train, y_train)

        train_pred = model.predict(X_train)
        test_pred = model.predict(X_test)

        train_rmse = np.sqrt(mean_squared_error(y_train, train_pred))
        test_rmse = np.sqrt(mean_squared_error(y_test, test_pred))

        results.append({
            'test_track': test_track,
            'train_rmse': train_rmse,
            'test_rmse': test_rmse
        })

        print(f"  {test_track}: Train RMSE: {train_rmse:.2f}s, Test RMSE: {test_rmse:.2f}s")

    return pd.DataFrame(results)


def evaluate_cross_race(df: pd.DataFrame, feature_cols: list) -> pd.DataFrame:
    """Evaluate cross-race same-track prediction (train R1, test R2)."""
    available_features = [f for f in feature_cols if f in df.columns]

    # Don't use track_mean_lap for cross-race (would leak)
    if 'track_mean_lap' in available_features:
        available_features = [f for f in available_features if f != 'track_mean_lap']

    results = []

    for track in df['track'].unique():
        track_data = df[df['track'] == track]
        races = track_data['race_num'].unique()

        if len(races) < 2:
            print(f"  {track}: Only 1 race, skipping")
            continue

        # Train on race 1, test on race 2
        train = track_data[track_data['race_num'] == 1].copy()
        test = track_data[track_data['race_num'] == 2].copy()

        if len(train) == 0 or len(test) == 0:
            print(f"  {track}: Missing race data, skipping")
            continue

        model = GradientBoostingRegressor(
            n_estimators=100,
            max_depth=5,
            learning_rate=0.1,
            random_state=42
        )

        X_train = train[available_features].values
        y_train = train['lap_time'].values
        X_test = test[available_features].values
        y_test = test['lap_time'].values

        model.fit(X_train, y_train)

        train_pred = model.predict(X_train)
        test_pred = model.predict(X_test)

        train_rmse = np.sqrt(mean_squared_error(y_train, train_pred))
        test_rmse = np.sqrt(mean_squared_error(y_test, test_pred))

        # Also compute percentage error
        mean_test_lap = test['lap_time'].mean()
        pct_error = 100 * test_rmse / mean_test_lap

        results.append({
            'track': track,
            'train_rmse': train_rmse,
            'test_rmse': test_rmse,
            'mean_test_lap': mean_test_lap,
            'pct_error': pct_error
        })

        print(f"  {track}: Train RMSE: {train_rmse:.2f}s, "
              f"Test RMSE: {test_rmse:.2f}s ({pct_error:.1f}%)")

    results_df = pd.DataFrame(results)

    if len(results_df) > 0:
        print(f"\nMean cross-race RMSE: {results_df['test_rmse'].mean():.2f}s")
        print(f"Mean percentage error: {results_df['pct_error'].mean():.1f}%")

    return results_df


def detailed_error_analysis(df: pd.DataFrame, feature_cols: list):
    """
    Detailed error analysis with:
    1. Per-driver RMSE
    2. RMSE by lap number
    3. Position-weighted RMSE (frontrunners matter more)
    """
    available_features = [f for f in feature_cols if f in df.columns]

    # Don't use track_mean_lap for cross-race
    if 'track_mean_lap' in available_features:
        available_features = [f for f in available_features if f != 'track_mean_lap']

    print("\n" + "=" * 70)
    print("DETAILED ERROR ANALYSIS")
    print("=" * 70)

    all_results = []

    for track in df['track'].unique():
        track_data = df[df['track'] == track]
        races = track_data['race_num'].unique()

        if len(races) < 2:
            continue

        train = track_data[track_data['race_num'] == 1].copy()
        test = track_data[track_data['race_num'] == 2].copy()

        if len(train) == 0 or len(test) == 0:
            continue

        model = GradientBoostingRegressor(
            n_estimators=100,
            max_depth=5,
            learning_rate=0.1,
            random_state=42
        )

        X_train = train[available_features].values
        y_train = train['lap_time'].values

        model.fit(X_train, y_train)

        # Predict on test
        test = test.copy()
        test['predicted'] = model.predict(test[available_features].values)
        test['error'] = test['lap_time'] - test['predicted']
        test['abs_error'] = test['error'].abs()
        test['sq_error'] = test['error'] ** 2

        all_results.append(test)

    if not all_results:
        print("No cross-race data available for analysis")
        return

    combined = pd.concat(all_results, ignore_index=True)

    # 1. Per-driver RMSE
    print("\n1. PER-DRIVER RMSE:")
    driver_rmse = combined.groupby('vehicle_number').apply(
        lambda x: np.sqrt((x['sq_error']).mean())
    ).sort_values()

    print(f"   Best 5 drivers (lowest RMSE):")
    for v, rmse in driver_rmse.head().items():
        n_laps = len(combined[combined['vehicle_number'] == v])
        print(f"     #{int(v)}: {rmse:.2f}s ({n_laps} laps)")

    print(f"   Worst 5 drivers (highest RMSE):")
    for v, rmse in driver_rmse.tail().items():
        n_laps = len(combined[combined['vehicle_number'] == v])
        print(f"     #{int(v)}: {rmse:.2f}s ({n_laps} laps)")

    print(f"\n   Mean per-driver RMSE: {driver_rmse.mean():.2f}s")
    print(f"   Median per-driver RMSE: {driver_rmse.median():.2f}s")

    # 2. RMSE by lap number
    print("\n2. RMSE BY LAP NUMBER:")
    lap_rmse = combined.groupby('lap').apply(
        lambda x: np.sqrt((x['sq_error']).mean())
    )

    # Show early, mid, late
    early_laps = lap_rmse[lap_rmse.index <= 3]
    mid_laps = lap_rmse[(lap_rmse.index > 3) & (lap_rmse.index <= 10)]
    late_laps = lap_rmse[lap_rmse.index > 10]

    print(f"   Early (lap 1-3):  {early_laps.mean():.2f}s")
    print(f"   Mid (lap 4-10):   {mid_laps.mean():.2f}s")
    print(f"   Late (lap 11+):   {late_laps.mean():.2f}s")

    # 3. Position-weighted RMSE
    print("\n3. POSITION-WEIGHTED RMSE:")

    # Weight by inverse position (P1=1.0, P2=0.5, P3=0.33, etc.)
    combined['position_weight'] = 1.0 / combined['position']

    # Normalize weights
    combined['position_weight'] = combined['position_weight'] / combined['position_weight'].sum()

    weighted_mse = (combined['sq_error'] * combined['position_weight']).sum() / combined['position_weight'].sum()
    weighted_rmse = np.sqrt(weighted_mse)

    # Compare with unweighted
    unweighted_rmse = np.sqrt(combined['sq_error'].mean())

    print(f"   Unweighted RMSE:        {unweighted_rmse:.2f}s")
    print(f"   Position-weighted RMSE: {weighted_rmse:.2f}s")

    # RMSE by position group
    top5 = combined[combined['position'] <= 5]
    mid = combined[(combined['position'] > 5) & (combined['position'] <= 15)]
    back = combined[combined['position'] > 15]

    print(f"\n   By position group:")
    print(f"   Top 5:     {np.sqrt(top5['sq_error'].mean()):.2f}s ({len(top5)} samples)")
    print(f"   P6-15:     {np.sqrt(mid['sq_error'].mean()):.2f}s ({len(mid)} samples)")
    print(f"   P16+:      {np.sqrt(back['sq_error'].mean()):.2f}s ({len(back)} samples)")

    return combined


if __name__ == "__main__":
    main()
