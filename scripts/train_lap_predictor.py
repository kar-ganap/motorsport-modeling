"""
Train and evaluate lap time prediction models.

This script:
1. Loads prepared features for Race 1 and Race 2
2. Trains baseline and enhanced models on Race 1
3. Evaluates on Race 2 (out-of-sample)
4. Computes winner prediction accuracy
5. Saves models and results

Usage:
    uv run python scripts/train_lap_predictor.py
"""

from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from motorsport_modeling.models.lap_time_predictor import (
    BaselineLapPredictor,
    EnhancedLapPredictor,
    compute_winner_accuracy
)


def main():
    data_dir = Path(__file__).parent.parent / 'data' / 'processed'
    model_dir = Path(__file__).parent.parent / 'models'
    output_dir = Path(__file__).parent.parent / 'outputs'
    model_dir.mkdir(exist_ok=True)
    output_dir.mkdir(exist_ok=True)

    # Load data
    print("=" * 70)
    print("LOADING DATA")
    print("=" * 70)

    r1 = pd.read_csv(data_dir / 'race1_features.csv')
    r2 = pd.read_csv(data_dir / 'race2_features.csv')

    print(f"Race 1: {len(r1)} samples, {r1['vehicle_number'].nunique()} vehicles")
    print(f"Race 2: {len(r2)} samples, {r2['vehicle_number'].nunique()} vehicles")
    print(f"Race 1 lap times: {r1['lap_time'].mean():.2f}s ± {r1['lap_time'].std():.2f}s")
    print(f"Race 2 lap times: {r2['lap_time'].mean():.2f}s ± {r2['lap_time'].std():.2f}s")

    # Train-test split: Race 1 = train, Race 2 = test
    train = r1.copy()
    test = r2.copy()

    # =========================================================================
    # BASELINE MODEL
    # =========================================================================
    print("\n" + "=" * 70)
    print("BASELINE MODEL (Linear Degradation)")
    print("=" * 70)

    baseline = BaselineLapPredictor()
    baseline.fit(train, verbose=True)

    print("\n--- Training Performance ---")
    train_metrics_base = baseline.evaluate(train, verbose=True)

    print("\n--- Test Performance (Race 2) ---")
    test_metrics_base = baseline.evaluate(test, verbose=True)

    # Driver parameters
    print("\n--- Driver Parameters (sorted by RMSE) ---")
    driver_params = baseline.get_driver_parameters()
    print(driver_params.head(10).to_string())

    # Save baseline model
    baseline_path = model_dir / 'baseline_lap_predictor.pkl'
    baseline.save(baseline_path)
    print(f"\nSaved: {baseline_path}")

    # =========================================================================
    # ENHANCED MODEL
    # =========================================================================
    print("\n" + "=" * 70)
    print("ENHANCED MODEL (Gradient Boosting)")
    print("=" * 70)

    enhanced = EnhancedLapPredictor(
        n_estimators=100,
        max_depth=5,
        learning_rate=0.1
    )

    # Feature columns including weather and flag status
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
        # Weather features (explain race-to-race variance)
        'air_temp',
        'track_temp',
        'humidity',
        # Flag status
        'is_under_yellow'
    ]
    enhanced.fit(train, feature_cols=feature_cols, verbose=True)

    print("\n--- Training Performance ---")
    train_metrics_enh = enhanced.evaluate(train, verbose=True)

    print("\n--- Test Performance (Race 2) ---")
    test_metrics_enh = enhanced.evaluate(test, verbose=True)

    # Feature importances
    print("\n--- Feature Importances ---")
    importances = enhanced.get_feature_importances()
    print(importances.to_string())

    # Save enhanced model
    enhanced_path = model_dir / 'enhanced_lap_predictor.pkl'
    enhanced.save(enhanced_path)
    print(f"\nSaved: {enhanced_path}")

    # =========================================================================
    # WINNER PREDICTION ACCURACY
    # =========================================================================
    print("\n" + "=" * 70)
    print("WINNER PREDICTION ACCURACY")
    print("=" * 70)

    # Test winner prediction from different laps
    print("\nBaseline Model:")
    for from_lap in [5, 10, 15, 20]:
        # Race 1
        r1_result = compute_winner_accuracy(baseline, train, from_lap, verbose=True)
        # Race 2
        r2_result = compute_winner_accuracy(baseline, test, from_lap, verbose=True)

    print("\nEnhanced Model:")
    for from_lap in [5, 10, 15, 20]:
        r1_result = compute_winner_accuracy(enhanced, train, from_lap, verbose=True)
        r2_result = compute_winner_accuracy(enhanced, test, from_lap, verbose=True)

    # =========================================================================
    # VISUALIZATIONS
    # =========================================================================
    print("\n" + "=" * 70)
    print("CREATING VISUALIZATIONS")
    print("=" * 70)

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # Plot 1: Actual vs Predicted (Test set, Baseline)
    ax1 = axes[0, 0]
    pred_base = baseline.predict(test)
    ax1.scatter(test['lap_time'], pred_base, alpha=0.5, s=10)
    ax1.plot([90, 300], [90, 300], 'r--', label='Perfect')
    ax1.set_xlabel('Actual Lap Time (s)')
    ax1.set_ylabel('Predicted Lap Time (s)')
    ax1.set_title(f'Baseline Model - Test Set (RMSE: {test_metrics_base["rmse"]:.2f}s)')
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # Plot 2: Actual vs Predicted (Test set, Enhanced)
    ax2 = axes[0, 1]
    pred_enh = enhanced.predict(test)
    ax2.scatter(test['lap_time'], pred_enh, alpha=0.5, s=10)
    ax2.plot([90, 300], [90, 300], 'r--', label='Perfect')
    ax2.set_xlabel('Actual Lap Time (s)')
    ax2.set_ylabel('Predicted Lap Time (s)')
    ax2.set_title(f'Enhanced Model - Test Set (RMSE: {test_metrics_enh["rmse"]:.2f}s)')
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    # Plot 3: Residuals by position (Enhanced)
    ax3 = axes[1, 0]
    residuals = test['lap_time'] - pred_enh
    ax3.scatter(test['position'], residuals, alpha=0.5, s=10)
    ax3.axhline(y=0, color='r', linestyle='--')
    ax3.set_xlabel('Position')
    ax3.set_ylabel('Residual (Actual - Predicted)')
    ax3.set_title('Enhanced Model Residuals by Position')
    ax3.grid(True, alpha=0.3)

    # Plot 4: Residuals over laps (Enhanced)
    ax4 = axes[1, 1]
    ax4.scatter(test['lap'], residuals, alpha=0.5, s=10)
    ax4.axhline(y=0, color='r', linestyle='--')
    ax4.set_xlabel('Lap')
    ax4.set_ylabel('Residual (Actual - Predicted)')
    ax4.set_title('Enhanced Model Residuals by Lap')
    ax4.grid(True, alpha=0.3)

    plt.tight_layout()

    fig_path = output_dir / 'lap_predictor_results.png'
    plt.savefig(fig_path, dpi=150, bbox_inches='tight')
    print(f"Saved: {fig_path}")

    # =========================================================================
    # SUMMARY
    # =========================================================================
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    print("\nModel Comparison (Test Set - Race 2):")
    print(f"{'Metric':<25} {'Baseline':<15} {'Enhanced':<15}")
    print("-" * 55)
    print(f"{'RMSE (s)':<25} {test_metrics_base['rmse']:<15.3f} {test_metrics_enh['rmse']:<15.3f}")
    print(f"{'MAE (s)':<25} {test_metrics_base['mae']:<15.3f} {test_metrics_enh['mae']:<15.3f}")
    print(f"{'Weighted RMSE (s)':<25} {test_metrics_base['weighted_rmse']:<15.3f} {test_metrics_enh['weighted_rmse']:<15.3f}")

    # Success criteria check
    print("\n" + "=" * 70)
    print("SUCCESS CRITERIA CHECK")
    print("=" * 70)

    criteria = [
        ("Race 1 RMSE < 1.0s", train_metrics_enh['rmse'] < 1.0, train_metrics_enh['rmse']),
        ("Race 2 RMSE < 1.5s", test_metrics_enh['rmse'] < 1.5, test_metrics_enh['rmse']),
    ]

    for name, passed, value in criteria:
        status = "PASS" if passed else "FAIL"
        print(f"{name}: {status} (actual: {value:.3f}s)")

    print("\n" + "=" * 70)

    return baseline, enhanced, train_metrics_enh, test_metrics_enh


if __name__ == "__main__":
    main()
