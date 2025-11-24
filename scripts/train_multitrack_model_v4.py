"""
Train improved multi-track model with driver potential baseline.

Key insight: Predict DELTA from driver's best pace, not absolute lap time.

Improvements over v3:
1. Use driver's best lap average as baseline
2. Predict delta from potential (should be smaller, more predictable)
3. Better handling of pit laps and yellows

Usage:
    uv run python scripts/train_multitrack_model_v4.py
"""

from pathlib import Path
import pandas as pd
import numpy as np
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_squared_error

# Track lengths in km
TRACK_LENGTHS = {
    'barber': 3.7,
    'cota': 5.5,
    'indianapolis': 4.0,
    'road-america': 6.5,
    'sebring': 5.9,
    'sonoma': 4.0,
    'vir': 5.3,
}


def load_driver_best_laps(tracks_dir: Path) -> pd.DataFrame:
    """Load driver best lap averages from all tracks."""
    all_best = []

    for track_dir in tracks_dir.iterdir():
        if not track_dir.is_dir():
            continue

        track = track_dir.name

        for race_dir in track_dir.iterdir():
            if not race_dir.is_dir():
                continue

            race_num = int(race_dir.name.replace('race', ''))

            # Find best laps file
            best_files = list(race_dir.glob('*Best*Laps*.CSV'))
            if not best_files:
                continue

            try:
                df = pd.read_csv(best_files[0], sep=';')
                df.columns = df.columns.str.strip()

                # Parse the AVERAGE time (format: "1:40.486")
                if 'AVERAGE' in df.columns:
                    def parse_time(t):
                        if pd.isna(t):
                            return np.nan
                        try:
                            parts = str(t).split(':')
                            if len(parts) == 2:
                                return float(parts[0]) * 60 + float(parts[1])
                            return float(t)
                        except:
                            return np.nan

                    df['best_avg_seconds'] = df['AVERAGE'].apply(parse_time)

                    # Also get best single lap
                    if 'BESTLAP_1' in df.columns:
                        df['best_lap_seconds'] = df['BESTLAP_1'].apply(parse_time)

                    # Keep relevant columns
                    result = df[['NUMBER', 'best_avg_seconds', 'best_lap_seconds']].copy()
                    result = result.rename(columns={'NUMBER': 'vehicle_number'})
                    result['track'] = track
                    result['race_num'] = race_num
                    result['race_id'] = f"{track}_r{race_num}"

                    all_best.append(result)
            except Exception as e:
                print(f"Error loading {best_files[0]}: {e}")
                continue

    if all_best:
        return pd.concat(all_best, ignore_index=True)
    return pd.DataFrame()


def main():
    data_dir = Path(__file__).parent.parent / 'data' / 'processed'
    tracks_dir = Path(__file__).parent.parent / 'data' / 'raw' / 'tracks'
    output_dir = Path(__file__).parent.parent / 'outputs'
    output_dir.mkdir(exist_ok=True)

    print("=" * 70)
    print("LOADING DATA WITH DRIVER POTENTIAL")
    print("=" * 70)

    # Load main features
    df = pd.read_csv(data_dir / 'multitrack_features.csv')

    # Load driver best laps
    best_laps = load_driver_best_laps(tracks_dir)

    if len(best_laps) == 0:
        print("ERROR: Could not load driver best laps data")
        return

    print(f"Loaded best lap data for {len(best_laps)} driver-race combinations")

    # Merge best lap data
    df = df.merge(
        best_laps[['vehicle_number', 'race_id', 'best_avg_seconds', 'best_lap_seconds']],
        on=['vehicle_number', 'race_id'],
        how='left'
    )

    # Calculate delta from potential
    df['delta_from_best'] = df['lap_time'] - df['best_avg_seconds']
    df['delta_from_fastest'] = df['lap_time'] - df['best_lap_seconds']

    # Fill missing with track average
    df['best_avg_seconds'] = df.groupby('track')['best_avg_seconds'].transform(
        lambda x: x.fillna(x.median())
    )
    df['best_lap_seconds'] = df.groupby('track')['best_lap_seconds'].transform(
        lambda x: x.fillna(x.median())
    )

    # Add track features
    df['track_length_km'] = df['track'].map(TRACK_LENGTHS)

    # Fill NaN in top_speed
    if 'top_speed' in df.columns:
        df['top_speed'] = df.groupby('track')['top_speed'].transform(
            lambda x: x.fillna(x.median())
        )
        df['top_speed'] = df['top_speed'].fillna(df['top_speed'].median())

    print(f"\nTotal samples: {len(df)}")
    print(f"Samples with best lap data: {df['best_avg_seconds'].notna().sum()}")

    # Show delta statistics
    print("\nDelta from best average:")
    print(f"  Mean: {df['delta_from_best'].mean():.2f}s")
    print(f"  Std: {df['delta_from_best'].std():.2f}s")
    print(f"  Min: {df['delta_from_best'].min():.2f}s")
    print(f"  Max: {df['delta_from_best'].max():.2f}s")

    # Features for predicting DELTA (not absolute time)
    delta_features = [
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
        'is_under_yellow',
        'track_length_km',
        'top_speed',
        # Lag features - but now relative to potential
        'prev_lap_time',
        'rolling_avg_3',
    ]

    # Also try with best lap as feature
    features_with_baseline = delta_features + ['best_avg_seconds']

    # =========================================================================
    # APPROACH 1: Predict absolute lap time with driver baseline
    # =========================================================================
    print("\n" + "=" * 70)
    print("APPROACH 1: ABSOLUTE LAP TIME WITH DRIVER BASELINE")
    print("=" * 70)

    results_baseline = evaluate_cross_race_with_baseline(
        df, features_with_baseline, target='lap_time'
    )

    # =========================================================================
    # APPROACH 2: Predict delta from driver's best
    # =========================================================================
    print("\n" + "=" * 70)
    print("APPROACH 2: PREDICT DELTA FROM DRIVER'S BEST")
    print("=" * 70)

    results_delta = evaluate_cross_race_delta(
        df, delta_features
    )

    # =========================================================================
    # DETAILED ANALYSIS
    # =========================================================================
    print("\n" + "=" * 70)
    print("DETAILED ERROR ANALYSIS (BEST MODEL)")
    print("=" * 70)

    detailed_analysis(df, features_with_baseline)

    print("\n" + "=" * 70)
    print("DONE")
    print("=" * 70)


def evaluate_cross_race_with_baseline(df: pd.DataFrame, feature_cols: list, target: str) -> pd.DataFrame:
    """Evaluate predicting lap time with driver baseline feature."""
    available_features = [f for f in feature_cols if f in df.columns]

    results = []

    for track in df['track'].unique():
        track_data = df[df['track'] == track]
        races = track_data['race_num'].unique()

        if len(races) < 2:
            continue

        train = track_data[track_data['race_num'] == 1].copy()
        test = track_data[track_data['race_num'] == 2].copy()

        if len(train) == 0 or len(test) == 0:
            continue

        # Drop rows with missing features
        train = train.dropna(subset=available_features + [target])
        test = test.dropna(subset=available_features + [target])

        if len(train) == 0 or len(test) == 0:
            continue

        model = GradientBoostingRegressor(
            n_estimators=100,
            max_depth=5,
            learning_rate=0.1,
            random_state=42
        )

        X_train = train[available_features].values
        y_train = train[target].values
        X_test = test[available_features].values
        y_test = test[target].values

        model.fit(X_train, y_train)

        test_pred = model.predict(X_test)
        test_rmse = np.sqrt(mean_squared_error(y_test, test_pred))

        mean_test_lap = test['lap_time'].mean()
        pct_error = 100 * test_rmse / mean_test_lap

        results.append({
            'track': track,
            'test_rmse': test_rmse,
            'pct_error': pct_error
        })

        print(f"  {track}: RMSE: {test_rmse:.2f}s ({pct_error:.1f}%)")

    results_df = pd.DataFrame(results)
    if len(results_df) > 0:
        print(f"\nMean RMSE: {results_df['test_rmse'].mean():.2f}s")
        print(f"Mean pct error: {results_df['pct_error'].mean():.1f}%")

    return results_df


def evaluate_cross_race_delta(df: pd.DataFrame, feature_cols: list) -> pd.DataFrame:
    """Evaluate predicting delta from driver's best pace."""
    available_features = [f for f in feature_cols if f in df.columns]

    results = []

    for track in df['track'].unique():
        track_data = df[df['track'] == track]
        races = track_data['race_num'].unique()

        if len(races) < 2:
            continue

        train = track_data[track_data['race_num'] == 1].copy()
        test = track_data[track_data['race_num'] == 2].copy()

        if len(train) == 0 or len(test) == 0:
            continue

        # Target is delta from best
        target = 'delta_from_best'

        # Drop rows with missing values
        train = train.dropna(subset=available_features + [target, 'best_avg_seconds'])
        test = test.dropna(subset=available_features + [target, 'best_avg_seconds'])

        if len(train) == 0 or len(test) == 0:
            continue

        model = GradientBoostingRegressor(
            n_estimators=100,
            max_depth=5,
            learning_rate=0.1,
            random_state=42
        )

        X_train = train[available_features].values
        y_train = train[target].values
        X_test = test[available_features].values
        y_test = test[target].values

        model.fit(X_train, y_train)

        # Predict delta
        delta_pred = model.predict(X_test)

        # Convert back to absolute lap time
        lap_time_pred = test['best_avg_seconds'].values + delta_pred
        lap_time_actual = test['lap_time'].values

        test_rmse = np.sqrt(mean_squared_error(lap_time_actual, lap_time_pred))

        mean_test_lap = test['lap_time'].mean()
        pct_error = 100 * test_rmse / mean_test_lap

        # Also show delta prediction error
        delta_rmse = np.sqrt(mean_squared_error(y_test, delta_pred))

        results.append({
            'track': track,
            'test_rmse': test_rmse,
            'delta_rmse': delta_rmse,
            'pct_error': pct_error
        })

        print(f"  {track}: Lap RMSE: {test_rmse:.2f}s, Delta RMSE: {delta_rmse:.2f}s ({pct_error:.1f}%)")

    results_df = pd.DataFrame(results)
    if len(results_df) > 0:
        print(f"\nMean Lap RMSE: {results_df['test_rmse'].mean():.2f}s")
        print(f"Mean Delta RMSE: {results_df['delta_rmse'].mean():.2f}s")

    return results_df


def detailed_analysis(df: pd.DataFrame, feature_cols: list):
    """Detailed error breakdown."""
    available_features = [f for f in feature_cols if f in df.columns]

    all_results = []

    for track in df['track'].unique():
        track_data = df[df['track'] == track]
        races = track_data['race_num'].unique()

        if len(races) < 2:
            continue

        train = track_data[track_data['race_num'] == 1].copy()
        test = track_data[track_data['race_num'] == 2].copy()

        train = train.dropna(subset=available_features + ['lap_time'])
        test = test.dropna(subset=available_features + ['lap_time'])

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

        test = test.copy()
        test['predicted'] = model.predict(test[available_features].values)
        test['error'] = test['lap_time'] - test['predicted']
        test['sq_error'] = test['error'] ** 2

        all_results.append(test)

    if not all_results:
        return

    combined = pd.concat(all_results, ignore_index=True)

    # Per-driver analysis
    print("\n1. PER-DRIVER RMSE:")
    driver_rmse = combined.groupby('vehicle_number').apply(
        lambda x: np.sqrt(x['sq_error'].mean()),
        include_groups=False
    ).sort_values()

    print(f"   Best 5: {', '.join([f'#{int(v)}:{r:.1f}s' for v, r in driver_rmse.head().items()])}")
    print(f"   Worst 5: {', '.join([f'#{int(v)}:{r:.1f}s' for v, r in driver_rmse.tail().items()])}")
    print(f"   Mean: {driver_rmse.mean():.2f}s, Median: {driver_rmse.median():.2f}s")

    # By lap
    print("\n2. RMSE BY LAP:")
    lap_rmse = combined.groupby('lap').apply(
        lambda x: np.sqrt(x['sq_error'].mean()),
        include_groups=False
    )
    early = lap_rmse[lap_rmse.index <= 3].mean()
    mid = lap_rmse[(lap_rmse.index > 3) & (lap_rmse.index <= 10)].mean()
    late = lap_rmse[lap_rmse.index > 10].mean()
    print(f"   Early (1-3): {early:.2f}s, Mid (4-10): {mid:.2f}s, Late (11+): {late:.2f}s")

    # By position
    print("\n3. RMSE BY POSITION:")
    top5 = combined[combined['position'] <= 5]
    mid_pack = combined[(combined['position'] > 5) & (combined['position'] <= 15)]
    back = combined[combined['position'] > 15]

    print(f"   Top 5: {np.sqrt(top5['sq_error'].mean()):.2f}s ({len(top5)} samples)")
    print(f"   P6-15: {np.sqrt(mid_pack['sq_error'].mean()):.2f}s ({len(mid_pack)} samples)")
    print(f"   P16+: {np.sqrt(back['sq_error'].mean()):.2f}s ({len(back)} samples)")

    # Yellow flag impact
    print("\n4. YELLOW FLAG IMPACT:")
    green = combined[combined['is_under_yellow'] == 0]
    yellow = combined[combined['is_under_yellow'] == 1]
    print(f"   Green flag: {np.sqrt(green['sq_error'].mean()):.2f}s ({len(green)} samples)")
    print(f"   Yellow flag: {np.sqrt(yellow['sq_error'].mean()):.2f}s ({len(yellow)} samples)")


if __name__ == "__main__":
    main()
