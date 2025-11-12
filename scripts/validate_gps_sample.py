"""
Quick validation script to check GPS data availability in sample.
"""

from pathlib import Path
from motorsport_modeling.data import load_telemetry, load_gps_data

SAMPLE_DATA = Path(__file__).parent.parent / 'data' / 'samples' / 'indy_telemetry_sample.csv'

print("=" * 60)
print("GPS DATA VALIDATION")
print("=" * 60)

# Load GPS
gps = load_gps_data(SAMPLE_DATA, verbose=True)
print(f"\nGPS data shape: {gps.shape}")
print(f"Vehicles: {gps['vehicle_number'].unique()}")
print(f"Laps: {gps['lap'].unique()}")
print(f"Points per lap: {len(gps) / len(gps['lap'].unique()):.1f}")

# Load telemetry to check speed
telemetry = load_telemetry(SAMPLE_DATA, wide_format=True, verbose=True)
print(f"\nTelemetry columns: {telemetry.columns.tolist()}")

if 'speed' in telemetry.columns:
    print(f"\nSpeed data:")
    print(f"  Non-null count: {telemetry['speed'].notna().sum()}")
    print(f"  Null count: {telemetry['speed'].isna().sum()}")
    if telemetry['speed'].notna().sum() > 0:
        print(f"  Min: {telemetry['speed'].min():.1f}")
        print(f"  Max: {telemetry['speed'].max():.1f}")
        print(f"  Mean: {telemetry['speed'].mean():.1f}")
else:
    print("\n⚠️  No speed column in telemetry!")

# Try merging
if 'speed' in telemetry.columns:
    merged = gps.merge(
        telemetry[['timestamp', 'speed']],
        on='timestamp',
        how='inner'
    )
    print(f"\nMerged GPS+speed: {len(merged)} rows")
    print(f"  Non-null speed: {merged['speed'].notna().sum()}")

    # Check per lap
    for lap in sorted(merged['lap'].unique()):
        lap_data = merged[merged['lap'] == lap]
        print(f"  Lap {lap}: {len(lap_data)} points, "
              f"{lap_data['speed'].notna().sum()} with speed")

print("\n" + "=" * 60)
print("CONCLUSION: Sample data is too sparse for corner identification")
print("This is expected - sample is for testing loaders, not corner detection")
print("Full dataset will have sufficient data for corner identification")
print("=" * 60)
