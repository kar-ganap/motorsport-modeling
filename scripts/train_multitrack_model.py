"""
Train and evaluate lap time prediction model on multi-track data.

This script:
1. Loads combined features from all tracks
2. Trains with leave-one-track-out cross-validation
3. Evaluates weather feature importance
4. Compares to single-track baseline

Usage:
    uv run python scripts/train_multitrack_model.py
"""

from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import GroupKFold, cross_val_score
from sklearn.metrics import mean_squared_error, mean_absolute_error
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from motorsport_modeling.models.lap_time_predictor import EnhancedLapPredictor


def main():
    data_dir = Path(__file__).parent.parent / 'data' / 'processed'
    model_dir = Path(__file__).parent.parent / 'models'
    output_dir = Path(__file__).parent.parent / 'outputs'
    model_dir.mkdir(exist_ok=True)
    output_dir.mkdir(exist_ok=True)

    # Load multi-track data
    print("=" * 70)
    print("LOADING MULTI-TRACK DATA")
    print("=" * 70)

    df = pd.read_csv(data_dir / 'multitrack_features.csv')

    print(f"Total samples: {len(df)}")
    print(f"Tracks: {df['track'].nunique()}")
    print(f"Races: {df['race_id'].nunique()}")
    print(f"Vehicles: {df['vehicle_number'].nunique()}")

    # Data summary per track
    print("\nPer-track summary:")
    for track in df['track'].unique():
        track_data = df[df['track'] == track]
        print(f"  {track}: {len(track_data)} samples, "
              f"mean lap {track_data['lap_time'].mean():.1f}s, "
              f"temp {track_data['air_temp'].mean():.1f}°C")

    # Feature columns
    feature_cols = [
        'lap',
        'position',
        'gap_to_leader',
        'gap_to_ahead',
        'gap_to_behind',
        'gap_delta_ahead',
        'gap_delta_behind',
        'race_progress',
        'fuel_load_estimate',
        # Weather features
        'air_temp',
        'track_temp',
        'humidity',
        # Flag status
        'is_under_yellow'
    ]

    # Check which features are available
    available_features = [f for f in feature_cols if f in df.columns]
    missing_features = [f for f in feature_cols if f not in df.columns]

    if missing_features:
        print(f"\nMissing features: {missing_features}")

    print(f"\nUsing {len(available_features)} features")

    # =========================================================================
    # LEAVE-ONE-TRACK-OUT CROSS-VALIDATION
    # =========================================================================
    print("\n" + "=" * 70)
    print("LEAVE-ONE-TRACK-OUT CROSS-VALIDATION")
    print("=" * 70)

    results = []

    for test_track in df['track'].unique():
        # Split data
        train = df[df['track'] != test_track].copy()
        test = df[df['track'] == test_track].copy()

        if len(test) == 0:
            continue

        # Train model
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

        # Evaluate
        train_pred = model.predict(X_train)
        test_pred = model.predict(X_test)

        train_rmse = np.sqrt(mean_squared_error(y_train, train_pred))
        test_rmse = np.sqrt(mean_squared_error(y_test, test_pred))
        test_mae = mean_absolute_error(y_test, test_pred)

        results.append({
            'test_track': test_track,
            'train_samples': len(train),
            'test_samples': len(test),
            'train_rmse': train_rmse,
            'test_rmse': test_rmse,
            'test_mae': test_mae,
            'mean_test_lap': test['lap_time'].mean()
        })

        print(f"\nTest track: {test_track}")
        print(f"  Train: {len(train)} samples, RMSE: {train_rmse:.2f}s")
        print(f"  Test: {len(test)} samples, RMSE: {test_rmse:.2f}s, MAE: {test_mae:.2f}s")

    # Summary
    results_df = pd.DataFrame(results)
    print("\n" + "=" * 70)
    print("CROSS-VALIDATION SUMMARY")
    print("=" * 70)

    print(f"\nMean test RMSE: {results_df['test_rmse'].mean():.2f}s")
    print(f"Std test RMSE: {results_df['test_rmse'].std():.2f}s")
    print(f"Best: {results_df.loc[results_df['test_rmse'].idxmin(), 'test_track']} "
          f"({results_df['test_rmse'].min():.2f}s)")
    print(f"Worst: {results_df.loc[results_df['test_rmse'].idxmax(), 'test_track']} "
          f"({results_df['test_rmse'].max():.2f}s)")

    # =========================================================================
    # TRAIN FINAL MODEL ON ALL DATA
    # =========================================================================
    print("\n" + "=" * 70)
    print("TRAINING FINAL MODEL ON ALL DATA")
    print("=" * 70)

    model = GradientBoostingRegressor(
        n_estimators=100,
        max_depth=5,
        learning_rate=0.1,
        random_state=42
    )

    X = df[available_features].values
    y = df['lap_time'].values

    model.fit(X, y)

    # Training performance
    pred = model.predict(X)
    train_rmse = np.sqrt(mean_squared_error(y, pred))
    print(f"\nFinal model training RMSE: {train_rmse:.2f}s")

    # Feature importances
    importances = pd.DataFrame({
        'feature': available_features,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)

    print("\nFeature Importances:")
    for _, row in importances.iterrows():
        print(f"  {row['feature']}: {row['importance']:.4f}")

    # Check weather feature importance
    weather_features = ['air_temp', 'track_temp', 'humidity']
    weather_importance = importances[importances['feature'].isin(weather_features)]['importance'].sum()
    print(f"\nTotal weather importance: {weather_importance:.4f} ({100*weather_importance:.1f}%)")

    # =========================================================================
    # COMPARE WITH SINGLE-TRACK MODEL
    # =========================================================================
    print("\n" + "=" * 70)
    print("COMPARISON: SINGLE-TRACK VS MULTI-TRACK")
    print("=" * 70)

    # Train on Indianapolis only, test on other tracks
    indy_data = df[df['track'] == 'indianapolis'].copy()
    other_data = df[df['track'] != 'indianapolis'].copy()

    single_model = GradientBoostingRegressor(
        n_estimators=100,
        max_depth=5,
        learning_rate=0.1,
        random_state=42
    )

    X_indy = indy_data[available_features].values
    y_indy = indy_data['lap_time'].values

    single_model.fit(X_indy, y_indy)

    # Evaluate on other tracks
    for test_track in other_data['track'].unique():
        track_data = other_data[other_data['track'] == test_track]
        X_test = track_data[available_features].values
        y_test = track_data['lap_time'].values

        pred = single_model.predict(X_test)
        rmse = np.sqrt(mean_squared_error(y_test, pred))

        # Compare with multi-track CV result
        multi_result = results_df[results_df['test_track'] == test_track]
        if len(multi_result) > 0:
            multi_rmse = multi_result['test_rmse'].values[0]
            improvement = rmse - multi_rmse
            print(f"{test_track}: Single-track RMSE: {rmse:.2f}s, "
                  f"Multi-track RMSE: {multi_rmse:.2f}s "
                  f"(improvement: {improvement:.2f}s)")

    # =========================================================================
    # SAVE MODEL AND RESULTS
    # =========================================================================
    print("\n" + "=" * 70)
    print("SAVING RESULTS")
    print("=" * 70)

    # Save cross-validation results
    results_file = output_dir / 'multitrack_cv_results.csv'
    results_df.to_csv(results_file, index=False)
    print(f"Saved: {results_file}")

    # Save feature importances
    importances_file = output_dir / 'multitrack_feature_importances.csv'
    importances.to_csv(importances_file, index=False)
    print(f"Saved: {importances_file}")

    # Create visualization
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # Plot 1: RMSE by track
    ax1 = axes[0, 0]
    ax1.barh(results_df['test_track'], results_df['test_rmse'])
    ax1.set_xlabel('Test RMSE (s)')
    ax1.set_title('Leave-One-Track-Out CV: Test RMSE')
    ax1.axvline(results_df['test_rmse'].mean(), color='r', linestyle='--',
                label=f'Mean: {results_df["test_rmse"].mean():.1f}s')
    ax1.legend()

    # Plot 2: Feature importances
    ax2 = axes[0, 1]
    top_features = importances.head(10)
    ax2.barh(top_features['feature'], top_features['importance'])
    ax2.set_xlabel('Importance')
    ax2.set_title('Top 10 Feature Importances')

    # Plot 3: Actual vs Predicted (all data)
    ax3 = axes[1, 0]
    ax3.scatter(y, pred, alpha=0.3, s=5)
    ax3.plot([80, 250], [80, 250], 'r--', label='Perfect')
    ax3.set_xlabel('Actual Lap Time (s)')
    ax3.set_ylabel('Predicted Lap Time (s)')
    ax3.set_title(f'All Data: Actual vs Predicted (RMSE: {train_rmse:.1f}s)')
    ax3.legend()

    # Plot 4: Weather correlation
    ax4 = axes[1, 1]
    if 'air_temp' in df.columns:
        sc = ax4.scatter(df['air_temp'], df['lap_time'],
                        c=df['track'].astype('category').cat.codes,
                        alpha=0.3, s=5, cmap='tab10')
        ax4.set_xlabel('Air Temperature (°C)')
        ax4.set_ylabel('Lap Time (s)')
        ax4.set_title('Lap Time vs Temperature by Track')

    plt.tight_layout()

    fig_path = output_dir / 'multitrack_model_results.png'
    plt.savefig(fig_path, dpi=150, bbox_inches='tight')
    print(f"Saved: {fig_path}")

    print("\n" + "=" * 70)
    print("DONE")
    print("=" * 70)

    return model, results_df, importances


if __name__ == "__main__":
    main()
