#!/usr/bin/env python3
"""
Systematically verify all quantitative claims in the hackathon submission document.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import json

# Define base paths
BASE_DIR = Path("/Users/kartikganapathi/Documents/Personal/random_projects/toyota-motorsport-analysis")
RAW_DATA_DIR = BASE_DIR / "data" / "raw" / "tracks"
PROCESSED_DATA_DIR = BASE_DIR / "data" / "processed"

# Track and race configuration
TRACKS = ["barber", "cota", "indianapolis", "road-america", "sebring", "sonoma", "vir"]
RACES = ["race1", "race2"]

results = {}

def verify_claim(claim_name, actual, expected, tolerance=0.0):
    """Verify a claim and return status"""
    if actual is None:
        return "❓ UNABLE TO VERIFY", actual, expected

    if isinstance(expected, str):
        if actual == expected:
            return "✅ VERIFIED", actual, expected
        else:
            return "❌ INCORRECT", actual, expected

    # Numeric comparison
    try:
        actual_val = float(actual)
        expected_val = float(expected)

        if abs(actual_val - expected_val) == 0:
            return "✅ VERIFIED", actual, expected
        elif abs(actual_val - expected_val) / expected_val <= tolerance:
            return "⚠️ APPROXIMATE", actual, expected
        else:
            return "❌ INCORRECT", actual, expected
    except:
        return "❓ UNABLE TO VERIFY", actual, expected

print("=" * 80)
print("HACKATHON SUBMISSION FACT-CHECK")
print("=" * 80)

# ============================================================================
# CLAIM 1: Indianapolis winner-to-runner-up margin
# ============================================================================
print("\n1. OPENING CLAIM: Indianapolis margin")
print("-" * 80)

try:
    # Try to find race results for Indianapolis
    indy_race1_features = pd.read_parquet(PROCESSED_DATA_DIR / "indianapolis" / "race1_features.parquet")
    indy_race2_features = pd.read_parquet(PROCESSED_DATA_DIR / "indianapolis" / "race2_features.parquet")

    # Check both races for the 0.17 second margin
    for race_num, df in enumerate([indy_race1_features, indy_race2_features], 1):
        # Get final positions (last lap for each driver)
        final_laps = df.groupby('driver_id').tail(1).sort_values('position')

        if len(final_laps) >= 2:
            winner_time = final_laps.iloc[0]['cumulative_time']
            runnerup_time = final_laps.iloc[1]['cumulative_time']
            margin = runnerup_time - winner_time

            print(f"Race {race_num}: Winner-Runner-up margin = {margin:.2f}s")

            if abs(margin - 0.17) < 0.01:
                results['indy_margin'] = verify_claim('indy_margin', margin, 0.17, tolerance=0.1)
                print(f"Status: {results['indy_margin'][0]}")
                print(f"Actual: {results['indy_margin'][1]:.2f}s, Expected: {results['indy_margin'][2]}s")
                break
    else:
        # Neither race had 0.17s margin - report both
        results['indy_margin'] = ("❌ INCORRECT", "Not found in either race", 0.17)
        print(f"Status: {results['indy_margin'][0]}")

except Exception as e:
    results['indy_margin'] = ("❓ UNABLE TO VERIFY", None, 0.17)
    print(f"Error: {e}")

# ============================================================================
# CLAIM 2: Coverage - 14 races (7 tracks × 2 races)
# ============================================================================
print("\n2. COVERAGE CLAIM: 14 races analyzed (7 tracks × 2 races)")
print("-" * 80)

try:
    races_found = []
    for track in TRACKS:
        track_dir = PROCESSED_DATA_DIR / track
        if track_dir.exists():
            for race in RACES:
                features_file = track_dir / f"{race}_features.parquet"
                if features_file.exists():
                    races_found.append(f"{track}/{race}")

    num_races = len(races_found)
    print(f"Races found: {num_races}")
    print(f"Tracks: {len(set(r.split('/')[0] for r in races_found))}")

    results['num_races'] = verify_claim('num_races', num_races, 14, tolerance=0)
    print(f"Status: {results['num_races'][0]}")
    print(f"Actual: {results['num_races'][1]}, Expected: {results['num_races'][2]}")

except Exception as e:
    results['num_races'] = ("❓ UNABLE TO VERIFY", None, 14)
    print(f"Error: {e}")

# ============================================================================
# CLAIM 3: ~350 driver performances evaluated
# ============================================================================
print("\n3. COVERAGE CLAIM: ~350 driver performances evaluated")
print("-" * 80)

try:
    total_drivers = 0
    for track in TRACKS:
        track_dir = PROCESSED_DATA_DIR / track
        if track_dir.exists():
            for race in RACES:
                features_file = track_dir / f"{race}_features.parquet"
                if features_file.exists():
                    df = pd.read_parquet(features_file)
                    num_drivers = df['driver_id'].nunique()
                    total_drivers += num_drivers

    print(f"Total driver performances: {total_drivers}")

    results['driver_performances'] = verify_claim('driver_performances', total_drivers, 350, tolerance=0.15)
    print(f"Status: {results['driver_performances'][0]}")
    print(f"Actual: {results['driver_performances'][1]}, Expected: {results['driver_performances'][2]}")

except Exception as e:
    results['driver_performances'] = ("❓ UNABLE TO VERIFY", None, 350)
    print(f"Error: {e}")

# ============================================================================
# CLAIM 4: 247,000 telemetry samples per race
# ============================================================================
print("\n4. COVERAGE CLAIM: 247,000 telemetry samples per race processed")
print("-" * 80)

try:
    # Check a sample race (VIR race1) for telemetry sample count
    sample_counts = []

    for track in TRACKS[:3]:  # Check first 3 tracks as representative sample
        for race in RACES:
            raw_file = RAW_DATA_DIR / track / f"{race}_telemetry.csv"
            if raw_file.exists():
                df = pd.read_csv(raw_file)
                sample_count = len(df)
                sample_counts.append(sample_count)
                print(f"{track}/{race}: {sample_count:,} samples")

    if sample_counts:
        avg_samples = np.mean(sample_counts)
        print(f"\nAverage samples per race: {avg_samples:,.0f}")

        results['telemetry_samples'] = verify_claim('telemetry_samples', avg_samples, 247000, tolerance=0.20)
        print(f"Status: {results['telemetry_samples'][0]}")
        print(f"Actual: {results['telemetry_samples'][1]:,.0f}, Expected: {results['telemetry_samples'][2]:,}")
    else:
        results['telemetry_samples'] = ("❓ UNABLE TO VERIFY", None, 247000)
        print("No telemetry CSV files found")

except Exception as e:
    results['telemetry_samples'] = ("❓ UNABLE TO VERIFY", None, 247000)
    print(f"Error: {e}")

# ============================================================================
# CLAIM 5: Model Performance - Position predictions MAE < 2
# ============================================================================
print("\n5. MODEL PERFORMANCE: Position predictions MAE < 2 positions")
print("-" * 80)

try:
    # Look for validation parquet files that contain model predictions
    mae_values = []

    for track in TRACKS:
        for race in RACES:
            validation_file = PROCESSED_DATA_DIR / track / f"{race}_validation.parquet"
            if validation_file.exists():
                df = pd.read_parquet(validation_file)

                # Check if it has position predictions
                if 'predicted_position' in df.columns and 'actual_position' in df.columns:
                    mae = np.mean(np.abs(df['predicted_position'] - df['actual_position']))
                    mae_values.append(mae)
                    print(f"{track}/{race}: MAE = {mae:.2f}")

    if mae_values:
        avg_mae = np.mean(mae_values)
        print(f"\nAverage MAE across all races: {avg_mae:.2f}")

        # Check if < 2
        if avg_mae < 2.0:
            results['position_mae'] = ("✅ VERIFIED", f"{avg_mae:.2f}", "< 2.0")
        elif avg_mae < 2.5:
            results['position_mae'] = ("⚠️ APPROXIMATE", f"{avg_mae:.2f}", "< 2.0")
        else:
            results['position_mae'] = ("❌ INCORRECT", f"{avg_mae:.2f}", "< 2.0")

        print(f"Status: {results['position_mae'][0]}")
    else:
        results['position_mae'] = ("❓ UNABLE TO VERIFY", None, "< 2.0")
        print("No validation files with position predictions found")

except Exception as e:
    results['position_mae'] = ("❓ UNABLE TO VERIFY", None, "< 2.0")
    print(f"Error: {e}")

# ============================================================================
# CLAIM 6: Lap time predictions RMSE 1.8s
# ============================================================================
print("\n6. MODEL PERFORMANCE: Lap time predictions RMSE 1.8s")
print("-" * 80)

try:
    rmse_values = []

    for track in TRACKS:
        for race in RACES:
            features_file = PROCESSED_DATA_DIR / track / f"{race}_features.parquet"
            if features_file.exists():
                df = pd.read_parquet(features_file)

                # Check for lap time prediction columns
                if 'predicted_lap_time' in df.columns and 'lap_time' in df.columns:
                    # Filter for normal racing laps (exclude outliers)
                    median_lap = df['lap_time'].median()
                    normal_laps = df[(df['lap_time'] < median_lap * 1.5) & (df['lap_time'] > median_lap * 0.5)]

                    rmse = np.sqrt(np.mean((normal_laps['predicted_lap_time'] - normal_laps['lap_time'])**2))
                    rmse_values.append(rmse)
                    print(f"{track}/{race}: RMSE = {rmse:.2f}s")

    if rmse_values:
        avg_rmse = np.mean(rmse_values)
        print(f"\nAverage RMSE across all races: {avg_rmse:.2f}s")

        results['lap_time_rmse'] = verify_claim('lap_time_rmse', avg_rmse, 1.8, tolerance=0.20)
        print(f"Status: {results['lap_time_rmse'][0]}")
    else:
        results['lap_time_rmse'] = ("❓ UNABLE TO VERIFY", None, 1.8)
        print("No features files with lap time predictions found")

except Exception as e:
    results['lap_time_rmse'] = ("❓ UNABLE TO VERIFY", None, 1.8)
    print(f"Error: {e}")

# ============================================================================
# CLAIM 7: 3.7x RMSE improvement (from 6.5s to 1.8s)
# ============================================================================
print("\n7. MODEL PERFORMANCE: 3.7x RMSE improvement (6.5s → 1.8s)")
print("-" * 80)

improvement_ratio = 6.5 / 1.8
print(f"Claimed improvement: 3.7x")
print(f"Calculated from 6.5s → 1.8s: {improvement_ratio:.2f}x")

results['rmse_improvement'] = verify_claim('rmse_improvement', improvement_ratio, 3.7, tolerance=0.05)
print(f"Status: {results['rmse_improvement'][0]}")

# ============================================================================
# CLAIM 8: 4/6 metrics show expected correlation with lap time
# ============================================================================
print("\n8. METRIC VALIDATION: 4/6 metrics show expected correlation")
print("-" * 80)

try:
    # Read a sample features file to check metric correlations
    sample_df = pd.read_parquet(PROCESSED_DATA_DIR / "vir" / "race1_features.parquet")

    # Define the 6 metrics to check
    metrics = [
        'lift_off_count',
        'full_throttle_pct',
        'brake_pressure_cv',
        'traction_loss_count',
        'throttle_smoothness',
        'brake_smoothness'
    ]

    available_metrics = [m for m in metrics if m in sample_df.columns]
    print(f"Available metrics: {len(available_metrics)}")

    if 'lap_time' in sample_df.columns:
        correlations = []
        for metric in available_metrics:
            corr = sample_df[[metric, 'lap_time']].corr().iloc[0, 1]
            correlations.append((metric, corr))
            print(f"{metric}: r = {corr:.3f}")

        # Count how many have expected direction (this is subjective, need to verify)
        results['metric_correlation'] = ("❓ UNABLE TO VERIFY", f"{len(available_metrics)} metrics found", "4/6")
        print(f"\nStatus: Need to verify expected correlation directions")
    else:
        results['metric_correlation'] = ("❓ UNABLE TO VERIFY", None, "4/6")
        print("Lap time column not found")

except Exception as e:
    results['metric_correlation'] = ("❓ UNABLE TO VERIFY", None, "4/6")
    print(f"Error: {e}")

# ============================================================================
# CLAIM 9: Variance analysis - lift_off_count ratio = 1.66
# ============================================================================
print("\n9. VARIANCE ANALYSIS: lift_off_count cross/within ratio = 1.66")
print("-" * 80)

try:
    # Calculate variance ratio for lift_off_count
    all_data = []

    for track in TRACKS:
        for race in RACES:
            features_file = PROCESSED_DATA_DIR / track / f"{race}_features.parquet"
            if features_file.exists():
                df = pd.read_parquet(features_file)
                if 'lift_off_count' in df.columns and 'driver_id' in df.columns:
                    all_data.append(df[['driver_id', 'lift_off_count', 'lap_number']])

    if all_data:
        combined = pd.concat(all_data, ignore_index=True)

        # Within-driver variance (average variance within each driver)
        within_var = combined.groupby('driver_id')['lift_off_count'].var().mean()

        # Cross-driver variance (variance of driver means)
        driver_means = combined.groupby('driver_id')['lift_off_count'].mean()
        cross_var = driver_means.var()

        ratio = cross_var / within_var

        print(f"Within-driver variance: {within_var:.4f}")
        print(f"Cross-driver variance: {cross_var:.4f}")
        print(f"Ratio: {ratio:.2f}")

        results['lift_off_variance'] = verify_claim('lift_off_variance', ratio, 1.66, tolerance=0.15)
        print(f"Status: {results['lift_off_variance'][0]}")
    else:
        results['lift_off_variance'] = ("❓ UNABLE TO VERIFY", None, 1.66)
        print("No lift_off_count data found")

except Exception as e:
    results['lift_off_variance'] = ("❓ UNABLE TO VERIFY", None, 1.66)
    print(f"Error: {e}")

# ============================================================================
# CLAIM 10: Variance analysis - brake_cv ratio = 0.48
# ============================================================================
print("\n10. VARIANCE ANALYSIS: brake_cv cross/within ratio = 0.48")
print("-" * 80)

try:
    all_data = []

    for track in TRACKS:
        for race in RACES:
            features_file = PROCESSED_DATA_DIR / track / f"{race}_features.parquet"
            if features_file.exists():
                df = pd.read_parquet(features_file)
                if 'brake_pressure_cv' in df.columns and 'driver_id' in df.columns:
                    all_data.append(df[['driver_id', 'brake_pressure_cv', 'lap_number']])

    if all_data:
        combined = pd.concat(all_data, ignore_index=True)

        # Within-driver variance
        within_var = combined.groupby('driver_id')['brake_pressure_cv'].var().mean()

        # Cross-driver variance
        driver_means = combined.groupby('driver_id')['brake_pressure_cv'].mean()
        cross_var = driver_means.var()

        ratio = cross_var / within_var

        print(f"Within-driver variance: {within_var:.4f}")
        print(f"Cross-driver variance: {cross_var:.4f}")
        print(f"Ratio: {ratio:.2f}")

        results['brake_cv_variance'] = verify_claim('brake_cv_variance', ratio, 0.48, tolerance=0.15)
        print(f"Status: {results['brake_cv_variance'][0]}")
    else:
        results['brake_cv_variance'] = ("❓ UNABLE TO VERIFY", None, 0.48)
        print("No brake_pressure_cv data found")

except Exception as e:
    results['brake_cv_variance'] = ("❓ UNABLE TO VERIFY", None, 0.48)
    print(f"Error: {e}")

# ============================================================================
# CLAIM 11: Example narrative - Driver #11 vs #42
# ============================================================================
print("\n11. EXAMPLE NARRATIVE: Driver #11 (P10) lost to #42 (P9) by 15.4s")
print("-" * 80)

try:
    # Search for this specific comparison in comparative analysis files
    found = False

    for track in TRACKS:
        for race in RACES:
            comparative_file = PROCESSED_DATA_DIR / track / f"{race}_comparative.parquet"
            if comparative_file.exists():
                df = pd.read_parquet(comparative_file)

                # Look for driver 11 and 42
                if 'driver_id' in df.columns:
                    driver_11 = df[df['driver_id'] == 11]
                    driver_42 = df[df['driver_id'] == 42]

                    if not driver_11.empty and not driver_42.empty:
                        print(f"Found drivers 11 and 42 in {track}/{race}")

                        # Check positions
                        if 'final_position' in df.columns:
                            pos_11 = driver_11['final_position'].iloc[0] if not driver_11.empty else None
                            pos_42 = driver_42['final_position'].iloc[0] if not driver_42.empty else None
                            print(f"Driver 11 position: {pos_11}, Driver 42 position: {pos_42}")

                        # Check time gap
                        if 'time_gap' in df.columns or 'total_time' in df.columns:
                            found = True
                            break

    if found:
        results['narrative_example'] = ("⚠️ APPROXIMATE", "Drivers found, need detailed verification", "15.4s gap")
    else:
        results['narrative_example'] = ("❓ UNABLE TO VERIFY", "Specific drivers not found", "15.4s gap")

    print(f"Status: {results['narrative_example'][0]}")

except Exception as e:
    results['narrative_example'] = ("❓ UNABLE TO VERIFY", None, "15.4s gap")
    print(f"Error: {e}")

# ============================================================================
# CLAIM 12: Controllable consistency improved accuracy by 12%
# ============================================================================
print("\n12. CONTROLLABLE CONSISTENCY: 12% improvement claim")
print("-" * 80)

results['controllable_consistency'] = ("❓ UNABLE TO VERIFY", "Need ablation study results", "12%")
print("Status: This requires specific A/B test results that may not be saved")

# ============================================================================
# SUMMARY
# ============================================================================
print("\n" + "=" * 80)
print("SUMMARY OF VERIFICATION RESULTS")
print("=" * 80)

verified = sum(1 for r in results.values() if r[0].startswith("✅"))
approximate = sum(1 for r in results.values() if r[0].startswith("⚠️"))
incorrect = sum(1 for r in results.values() if r[0].startswith("❌"))
unable = sum(1 for r in results.values() if r[0].startswith("❓"))

print(f"\n✅ VERIFIED: {verified}")
print(f"⚠️ APPROXIMATE: {approximate}")
print(f"❌ INCORRECT: {incorrect}")
print(f"❓ UNABLE TO VERIFY: {unable}")

print("\nDetailed Results:")
for claim, (status, actual, expected) in results.items():
    print(f"\n{claim}:")
    print(f"  Status: {status}")
    print(f"  Actual: {actual}")
    print(f"  Expected: {expected}")

# Save results to JSON
output_file = BASE_DIR / "docs" / "verification_results.json"
results_dict = {k: {"status": v[0], "actual": str(v[1]), "expected": str(v[2])} for k, v in results.items()}

with open(output_file, 'w') as f:
    json.dump(results_dict, f, indent=2)

print(f"\n\nResults saved to: {output_file}")
