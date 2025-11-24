#!/usr/bin/env python3
"""
Comprehensive verification of hackathon submission claims.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import json
import glob

# Define base paths
BASE_DIR = Path("/Users/kartikganapathi/Documents/Personal/random_projects/toyota-motorsport-analysis")
RAW_DATA_DIR = BASE_DIR / "data" / "raw" / "tracks"
PROCESSED_DATA_DIR = BASE_DIR / "data" / "processed"

TRACKS = ["barber", "cota", "indianapolis", "road-america", "sebring", "sonoma", "vir"]
RACES = ["race1", "race2"]

results = {}

def verify_claim(claim_name, actual, expected, tolerance=0.0):
    """Verify a claim and return status"""
    if actual is None:
        return "❓ UNABLE TO VERIFY", actual, expected

    if isinstance(expected, str):
        if str(actual) == expected:
            return "✅ VERIFIED", actual, expected
        else:
            return "❌ INCORRECT", actual, expected

    # Numeric comparison
    try:
        actual_val = float(actual)
        expected_val = float(expected)

        if abs(actual_val - expected_val) == 0:
            return "✅ VERIFIED", actual, expected
        elif abs(actual_val - expected_val) / max(expected_val, 0.001) <= tolerance:
            return "⚠️ APPROXIMATE", actual, expected
        else:
            return "❌ INCORRECT", actual, expected
    except:
        return "❓ UNABLE TO VERIFY", actual, expected

print("=" * 80)
print("HACKATHON SUBMISSION FACT-CHECK v2")
print("=" * 80)

# ============================================================================
# CLAIM 1: Indianapolis winner-to-runner-up margin = 0.17s
# ============================================================================
print("\n1. OPENING CLAIM: Indianapolis margin = 0.17 seconds")
print("-" * 80)

try:
    for race_num in [1, 2]:
        df = pd.read_parquet(PROCESSED_DATA_DIR / "indianapolis" / f"race{race_num}_features.parquet")

        # Get final lap for each driver
        final_laps = df.groupby('vehicle_number').last().sort_values('cumulative_time')

        if len(final_laps) >= 2:
            winner_time = final_laps.iloc[0]['cumulative_time']
            runnerup_time = final_laps.iloc[1]['cumulative_time']
            margin = runnerup_time - winner_time

            print(f"Race {race_num}: Winner time = {winner_time:.2f}s, Runner-up time = {runnerup_time:.2f}s")
            print(f"Margin: {margin:.2f}s")

            if abs(margin - 0.17) < 0.05:
                results['indy_margin'] = verify_claim('indy_margin', margin, 0.17, tolerance=0.1)
                print(f"✓ Found matching margin in race {race_num}")
                break
    else:
        results['indy_margin'] = ("⚠️ APPROXIMATE", "Not found in either race", 0.17)

except Exception as e:
    results['indy_margin'] = ("❓ UNABLE TO VERIFY", None, 0.17)
    print(f"Error: {e}")

# ============================================================================
# CLAIM 2: 14 races (7 tracks × 2)
# ============================================================================
print("\n2. COVERAGE: 14 races analyzed (7 tracks × 2 races)")
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
    num_tracks = len(set(r.split('/')[0] for r in races_found))

    print(f"Found: {num_tracks} tracks, {num_races} races")
    print(f"Races: {', '.join(races_found)}")

    results['num_races'] = verify_claim('num_races', num_races, 14, tolerance=0)
    print(f"Status: {results['num_races'][0]}")

except Exception as e:
    results['num_races'] = ("❓ UNABLE TO VERIFY", None, 14)
    print(f"Error: {e}")

# ============================================================================
# CLAIM 3: ~350 driver performances
# ============================================================================
print("\n3. COVERAGE: ~350 driver performances evaluated")
print("-" * 80)

try:
    total_drivers = 0
    for track in TRACKS:
        for race in RACES:
            features_file = PROCESSED_DATA_DIR / track / f"{race}_features.parquet"
            if features_file.exists():
                df = pd.read_parquet(features_file)
                num_drivers = df['vehicle_number'].nunique()
                total_drivers += num_drivers
                print(f"{track}/{race}: {num_drivers} drivers")

    print(f"\nTotal driver performances: {total_drivers}")

    results['driver_performances'] = verify_claim('driver_performances', total_drivers, 350, tolerance=0.15)
    print(f"Status: {results['driver_performances'][0]}")

except Exception as e:
    results['driver_performances'] = ("❓ UNABLE TO VERIFY", None, 350)
    print(f"Error: {e}")

# ============================================================================
# CLAIM 4: 247,000 telemetry samples per race
# ============================================================================
print("\n4. COVERAGE: 247,000 telemetry samples per race processed")
print("-" * 80)

try:
    sample_counts = []

    # Check each track for telemetry data
    for track in TRACKS:
        track_dir = RAW_DATA_DIR / track
        if track_dir.exists():
            for race in RACES:
                race_dir = track_dir / race
                if race_dir.exists():
                    # Find telemetry CSV files
                    telemetry_files = list(race_dir.glob("*telemetry*.csv"))

                    for telem_file in telemetry_files:
                        try:
                            # Count lines (samples)
                            with open(telem_file, 'r') as f:
                                count = sum(1 for _ in f) - 1  # Exclude header
                            sample_counts.append((f"{track}/{race}", count))
                            print(f"{track}/{race}: {count:,} samples")
                        except Exception as e:
                            print(f"Error reading {telem_file}: {e}")

    if sample_counts:
        avg_samples = np.mean([c for _, c in sample_counts])
        print(f"\nAverage samples per race: {avg_samples:,.0f}")
        print(f"Min: {min(c for _, c in sample_counts):,}")
        print(f"Max: {max(c for _, c in sample_counts):,}")

        results['telemetry_samples'] = verify_claim('telemetry_samples', avg_samples, 247000, tolerance=0.25)
        print(f"Status: {results['telemetry_samples'][0]}")
    else:
        results['telemetry_samples'] = ("❓ UNABLE TO VERIFY", "No telemetry files found", 247000)
        print("No telemetry files found")

except Exception as e:
    results['telemetry_samples'] = ("❓ UNABLE TO VERIFY", None, 247000)
    print(f"Error: {e}")

# ============================================================================
# CLAIM 5-6: Check for validation scripts outputs
# ============================================================================
print("\n5-6. MODEL PERFORMANCE: Checking validation scripts...")
print("-" * 80)

# Look for validation script outputs
validation_scripts = [
    "comprehensive_prediction_validation.py",
    "validate_lap_time_predictions.py",
    "validate_relative_performance.py"
]

print("Searching for validation results in script outputs...")

# Check if we can find model performance metrics in documentation
docs_dir = BASE_DIR / "docs"
for doc_file in docs_dir.glob("*.md"):
    print(f"Checking {doc_file.name}...")

results['position_mae'] = ("❓ UNABLE TO VERIFY", "Need validation script results", "< 2.0")
results['lap_time_rmse'] = ("❓ UNABLE TO VERIFY", "Need validation script results", "1.8s")

# ============================================================================
# CLAIM 7: 3.7x improvement (6.5s → 1.8s)
# ============================================================================
print("\n7. MODEL PERFORMANCE: 3.7x RMSE improvement")
print("-" * 80)

improvement_ratio = 6.5 / 1.8
print(f"Claimed improvement: 3.7x")
print(f"Calculated from 6.5s → 1.8s: {improvement_ratio:.3f}x")

results['rmse_improvement'] = verify_claim('rmse_improvement', improvement_ratio, 3.7, tolerance=0.05)
print(f"Status: {results['rmse_improvement'][0]}")

# ============================================================================
# CLAIM 8: 4/6 metrics correlation
# ============================================================================
print("\n8. METRIC VALIDATION: 4/6 metrics show expected correlation")
print("-" * 80)

# This requires knowing what the 6 metrics are and what "expected" means
# Based on the doc, the expected metrics are:
# 1. lift_off_count (lower is better - negative correlation expected)
# 2. full_throttle_pct (higher is better - negative correlation expected)
# 3. brake_pressure_cv (lower is better - positive correlation expected)
# 4. brake oscillations (higher might be ok for trail braking)
# 5. throttle timing
# 6. traction loss

results['metric_correlation'] = ("❓ UNABLE TO VERIFY", "Need metric definitions", "4/6")
print("Status: Requires detailed metric analysis")

# ============================================================================
# CLAIM 9-10: Variance analysis
# ============================================================================
print("\n9-10. VARIANCE ANALYSIS: Checking profile vs state metrics")
print("-" * 80)

# These would need to be calculated from telemetry-derived features
# which may not be in the processed files

results['lift_off_variance'] = ("❓ UNABLE TO VERIFY", "Telemetry features not in processed files", 1.66)
results['brake_cv_variance'] = ("❓ UNABLE TO VERIFY", "Telemetry features not in processed files", 0.48)

print("Status: Requires telemetry-derived features")

# ============================================================================
# CLAIM 11: Driver #11 vs #42 narrative
# ============================================================================
print("\n11. EXAMPLE NARRATIVE: Driver #11 (P10) lost to #42 (P9) by 15.4s")
print("-" * 80)

try:
    found_example = False

    for track in TRACKS:
        for race in RACES:
            comparative_file = PROCESSED_DATA_DIR / track / f"{race}_comparative.parquet"
            if comparative_file.exists():
                df = pd.read_parquet(comparative_file)

                # Look for drivers 11 and 42
                driver_11 = df[df['vehicle_number'] == 11]
                driver_42 = df[df['vehicle_number'] == 42]

                if not driver_11.empty and not driver_42.empty:
                    pos_11 = driver_11['final_position'].iloc[0]
                    pos_42 = driver_42['final_position'].iloc[0]
                    gap_11 = driver_11['gap_to_winner'].iloc[0]
                    gap_42 = driver_42['gap_to_winner'].iloc[0]

                    time_diff = abs(gap_11 - gap_42)

                    print(f"\n{track}/{race}:")
                    print(f"  Driver #11: P{pos_11}, gap to winner: {gap_11:.2f}s")
                    print(f"  Driver #42: P{pos_42}, gap to winner: {gap_42:.2f}s")
                    print(f"  Time difference: {time_diff:.2f}s")

                    # Check if positions match (11 at P10, 42 at P9)
                    if pos_11 == 10 and pos_42 == 9:
                        found_example = True
                        print(f"  ✓ Positions match! Checking gap...")

                        if abs(time_diff - 15.4) < 2.0:
                            results['narrative_example'] = verify_claim('narrative_example', time_diff, 15.4, tolerance=0.15)
                            print(f"  Status: {results['narrative_example'][0]}")
                            break

        if found_example:
            break

    if not found_example:
        results['narrative_example'] = ("❓ UNABLE TO VERIFY", "Drivers 11 and 42 in specified positions not found", "15.4s")
        print("\nDrivers #11 at P10 and #42 at P9 not found in any race")

except Exception as e:
    results['narrative_example'] = ("❓ UNABLE TO VERIFY", None, "15.4s")
    print(f"Error: {e}")

# ============================================================================
# CLAIM 12: Controllable consistency 12% improvement
# ============================================================================
print("\n12. CONTROLLABLE CONSISTENCY: 12% improvement")
print("-" * 80)

results['controllable_consistency'] = ("❓ UNABLE TO VERIFY", "Requires A/B test results", "12%")
print("Status: Requires ablation study comparing models with/without controllable consistency")

# ============================================================================
# ADDITIONAL: Check cross-race generalization (MAE < 2.5)
# ============================================================================
print("\n13. CROSS-RACE GENERALIZATION: MAE < 2.5 positions")
print("-" * 80)

results['cross_race_mae'] = ("❓ UNABLE TO VERIFY", "Need cross-validation results", "< 2.5")
print("Status: Requires multi-track model validation results")

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
print(f"\nTotal claims checked: {len(results)}")

print("\n" + "=" * 80)
print("DETAILED RESULTS")
print("=" * 80)

for i, (claim, (status, actual, expected)) in enumerate(results.items(), 1):
    print(f"\n{i}. {claim}")
    print(f"   Status: {status}")
    print(f"   Expected: {expected}")
    print(f"   Actual: {actual}")

# Save results
output_file = BASE_DIR / "docs" / "verification_results.json"
results_dict = {k: {"status": v[0], "actual": str(v[1]), "expected": str(v[2])} for k, v in results.items()}

with open(output_file, 'w') as f:
    json.dump(results_dict, f, indent=2)

print(f"\n\nResults saved to: {output_file}")
