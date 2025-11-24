"""
Train improved multi-track model with track length and baseline features.

Improvements over v1:
1. Add track length as feature
2. Add track mean lap time as baseline
3. Use track encoding

Usage:
    uv run python scripts/train_multitrack_model_v2.py
"""

from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_squared_error, mean_absolute_error
import sys

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

    # Normalized lap time (for analysis, not prediction target)
    df['lap_time_zscore'] = (df['lap_time'] - df['track_mean_lap']) / df['track_std_lap']

    # Expected lap time based on track length (rough estimate)
    # Assuming ~100s per 4km on average
    df['expected_lap_from_length'] = df['track_length_km'] * 25  # ~100s for 4km

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

    print(f"Total samples: {len(df)}")
    print(f"Tracks: {df['track'].nunique()}")

    # Show track stats
    print("\nTrack statistics:")
    track_stats = df.groupby('track').agg({
        'lap_time': ['mean', 'std', 'count'],
        'track_length_km': 'first',
        'air_temp': 'mean'
    }).round(1)
    track_stats.columns = ['mean_lap', 'std_lap', 'samples', 'length_km', 'mean_temp']
    print(track_stats.to_string())

    # Base feature columns
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

    # New track features
    track_features = [
        'track_length_km',
        'track_mean_lap',  # Baseline from training data
    ]

    # =========================================================================
    # MODEL 1: Base features only (baseline)
    # =========================================================================
    print("\n" + "=" * 70)
    print("MODEL 1: BASE FEATURES (BASELINE)")
    print("=" * 70)

    results_base = evaluate_model(df, base_features, "Base")

    # =========================================================================
    # MODEL 2: Base + Track Length
    # =========================================================================
    print("\n" + "=" * 70)
    print("MODEL 2: BASE + TRACK LENGTH")
    print("=" * 70)

    features_v2 = base_features + ['track_length_km']
    results_length = evaluate_model(df, features_v2, "Base+Length")

    # =========================================================================
    # MODEL 3: Base + Track Length + Track Mean (Best Expected)
    # =========================================================================
    print("\n" + "=" * 70)
    print("MODEL 3: BASE + TRACK LENGTH + TRACK MEAN")
    print("=" * 70)

    features_v3 = base_features + track_features
    results_full = evaluate_model(df, features_v3, "Full")

    # =========================================================================
    # COMPARISON
    # =========================================================================
    print("\n" + "=" * 70)
    print("MODEL COMPARISON")
    print("=" * 70)

    print("\nMean Test RMSE by Model:")
    print(f"  Base features only:     {results_base['test_rmse'].mean():.2f}s")
    print(f"  + Track length:         {results_length['test_rmse'].mean():.2f}s")
    print(f"  + Track mean baseline:  {results_full['test_rmse'].mean():.2f}s")

    improvement = results_base['test_rmse'].mean() - results_full['test_rmse'].mean()
    print(f"\nImprovement from track features: {improvement:.2f}s")

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

    # Save comparison results
    comparison = pd.DataFrame({
        'track': results_base['test_track'],
        'base_rmse': results_base['test_rmse'].values,
        'length_rmse': results_length['test_rmse'].values,
        'full_rmse': results_full['test_rmse'].values
    })

    comparison_file = output_dir / 'multitrack_model_comparison.csv'
    comparison.to_csv(comparison_file, index=False)
    print(f"\nSaved: {comparison_file}")

    # Create visualization
    create_comparison_plot(comparison, output_dir)

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

        # For track_mean_lap, we need to calculate it from training data only
        if 'track_mean_lap' in available_features:
            # Recalculate track means from training data
            train_track_means = train.groupby('track')['lap_time'].mean()

            # For test track, use mean from similar tracks or overall mean
            # Since test track isn't in training, use overall mean as fallback
            test_track_mean = train['lap_time'].mean()

            # Update test data
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


def create_comparison_plot(comparison: pd.DataFrame, output_dir: Path):
    """Create comparison visualization."""
    fig, ax = plt.subplots(figsize=(12, 6))

    x = np.arange(len(comparison))
    width = 0.25

    bars1 = ax.bar(x - width, comparison['base_rmse'], width, label='Base', color='#2196F3')
    bars2 = ax.bar(x, comparison['length_rmse'], width, label='+ Track Length', color='#4CAF50')
    bars3 = ax.bar(x + width, comparison['full_rmse'], width, label='+ Track Mean', color='#FF9800')

    ax.set_xlabel('Test Track')
    ax.set_ylabel('Test RMSE (s)')
    ax.set_title('Multi-Track Model: Leave-One-Track-Out Cross-Validation')
    ax.set_xticks(x)
    ax.set_xticklabels(comparison['track'])
    ax.legend()
    ax.grid(axis='y', alpha=0.3)

    # Add mean lines
    ax.axhline(comparison['base_rmse'].mean(), color='#2196F3', linestyle='--', alpha=0.5)
    ax.axhline(comparison['full_rmse'].mean(), color='#FF9800', linestyle='--', alpha=0.5)

    plt.tight_layout()

    fig_path = output_dir / 'multitrack_model_comparison.png'
    plt.savefig(fig_path, dpi=150, bbox_inches='tight')
    print(f"Saved: {fig_path}")


if __name__ == "__main__":
    main()
