"""
Diagnose why corners are missing in the eastern section of the track.

The eastern section (Turns 9-14) appears to have no detected corners.
This script investigates:
1. GPS data density in that area
2. Brake pressure levels
3. Whether corners are just light braking (not heavy)

Usage:
    uv run python scripts/diagnose_missing_corners.py
"""

from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from motorsport_modeling.data import (
    load_telemetry,
    load_gps_data,
)


def main():
    data_file = Path(__file__).parent.parent / 'data' / 'raw' / 'R1_indianapolis_motor_speedway_telemetry.csv'

    if not data_file.exists():
        print(f"ERROR: {data_file} not found")
        return

    print("=" * 70)
    print("DIAGNOSING MISSING CORNERS IN EASTERN SECTION")
    print("=" * 70)

    vehicle = 55
    laps = list(range(5, 15))  # 10 laps

    # Load GPS and brake data
    print("\nLoading data...")
    gps = load_gps_data(data_file, vehicle=vehicle, lap=laps, verbose=False)

    telemetry = load_telemetry(
        data_file,
        vehicle=vehicle,
        lap=laps,
        parameters=['pbrake_f', 'speed'],
        wide_format=True,
        verbose=False
    )

    # Merge
    merged = gps.merge(
        telemetry[['timestamp', 'pbrake_f', 'speed']],
        on='timestamp',
        how='inner'
    )

    print(f"Total data points: {len(merged):,}")

    # Define sections based on longitude
    # Eastern section: longitude > -86.235 (right side of track)
    # Western section: longitude < -86.237 (left side)
    # Middle section: in between

    eastern = merged[merged['longitude'] > -86.235]
    western = merged[merged['longitude'] < -86.237]
    middle = merged[(merged['longitude'] >= -86.237) & (merged['longitude'] <= -86.235)]

    print(f"\nData distribution by section:")
    print(f"  Eastern (lon > -86.235): {len(eastern):,} points ({100*len(eastern)/len(merged):.1f}%)")
    print(f"  Western (lon < -86.237): {len(western):,} points ({100*len(western)/len(merged):.1f}%)")
    print(f"  Middle:                  {len(middle):,} points ({100*len(middle)/len(merged):.1f}%)")

    # Analyze brake pressure in each section
    print("\n" + "-" * 70)
    print("BRAKE PRESSURE ANALYSIS BY SECTION")
    print("-" * 70)

    for name, section in [("Eastern", eastern), ("Western", western), ("Middle", middle)]:
        if len(section) == 0:
            print(f"\n{name} section: NO DATA")
            continue

        brake = section['pbrake_f'].dropna()
        if len(brake) == 0:
            print(f"\n{name} section: No brake data")
            continue

        print(f"\n{name} section ({len(section):,} points):")
        print(f"  Brake range: {brake.min():.1f} - {brake.max():.1f} bar")
        print(f"  Mean brake: {brake.mean():.1f} bar")
        print(f"  Median brake: {brake.median():.1f} bar")

        # Count significant braking events
        heavy_braking = (brake > 60).sum()
        medium_braking = ((brake > 30) & (brake <= 60)).sum()
        light_braking = ((brake > 10) & (brake <= 30)).sum()

        print(f"  Heavy braking (>60): {heavy_braking:,} points")
        print(f"  Medium braking (30-60): {medium_braking:,} points")
        print(f"  Light braking (10-30): {light_braking:,} points")

        # Percentiles
        print(f"  90th percentile: {np.percentile(brake, 90):.1f} bar")
        print(f"  95th percentile: {np.percentile(brake, 95):.1f} bar")
        print(f"  Max: {brake.max():.1f} bar")

    # Analyze speed in each section (to understand corner types)
    print("\n" + "-" * 70)
    print("SPEED ANALYSIS BY SECTION")
    print("-" * 70)

    for name, section in [("Eastern", eastern), ("Western", western), ("Middle", middle)]:
        if len(section) == 0:
            continue

        speed = section['speed'].dropna()
        if len(speed) == 0:
            print(f"\n{name} section: No speed data")
            continue

        print(f"\n{name} section:")
        print(f"  Speed range: {speed.min():.1f} - {speed.max():.1f} km/h")
        print(f"  Mean speed: {speed.mean():.1f} km/h")
        print(f"  Min speed: {speed.min():.1f} km/h (potential corner)")

        # Count slow speeds (potential corners)
        slow = (speed < 80).sum()
        medium = ((speed >= 80) & (speed < 120)).sum()
        fast = (speed >= 120).sum()

        print(f"  Slow (<80 km/h): {slow:,} points")
        print(f"  Medium (80-120 km/h): {medium:,} points")
        print(f"  Fast (>120 km/h): {fast:,} points")

    # Create visualization
    print("\n" + "-" * 70)
    print("CREATING DIAGNOSTIC VISUALIZATION")
    print("-" * 70)

    fig, axes = plt.subplots(2, 2, figsize=(14, 12))

    # Plot 1: Track with color-coded brake pressure
    ax1 = axes[0, 0]
    scatter = ax1.scatter(merged['longitude'], merged['latitude'],
                         c=merged['pbrake_f'], cmap='RdYlGn_r',
                         s=2, alpha=0.5)
    plt.colorbar(scatter, ax=ax1, label='Brake Pressure (bar)')
    ax1.set_xlabel('Longitude')
    ax1.set_ylabel('Latitude')
    ax1.set_title('Brake Pressure Around Track')
    ax1.axvline(x=-86.235, color='red', linestyle='--', alpha=0.5, label='Eastern boundary')
    ax1.axvline(x=-86.237, color='blue', linestyle='--', alpha=0.5, label='Western boundary')
    ax1.legend(fontsize=8)

    # Plot 2: Track with color-coded speed
    ax2 = axes[0, 1]
    scatter = ax2.scatter(merged['longitude'], merged['latitude'],
                         c=merged['speed'], cmap='RdYlGn',
                         s=2, alpha=0.5)
    plt.colorbar(scatter, ax=ax2, label='Speed (km/h)')
    ax2.set_xlabel('Longitude')
    ax2.set_ylabel('Latitude')
    ax2.set_title('Speed Around Track')

    # Plot 3: Brake pressure histogram by section
    ax3 = axes[1, 0]
    if len(eastern) > 0:
        ax3.hist(eastern['pbrake_f'].dropna(), bins=50, alpha=0.5, label='Eastern', color='red')
    if len(western) > 0:
        ax3.hist(western['pbrake_f'].dropna(), bins=50, alpha=0.5, label='Western', color='blue')
    if len(middle) > 0:
        ax3.hist(middle['pbrake_f'].dropna(), bins=50, alpha=0.5, label='Middle', color='green')
    ax3.axvline(x=60, color='black', linestyle='--', label='Heavy threshold')
    ax3.axvline(x=30, color='gray', linestyle='--', label='Medium threshold')
    ax3.set_xlabel('Brake Pressure (bar)')
    ax3.set_ylabel('Count')
    ax3.set_title('Brake Pressure Distribution by Section')
    ax3.legend()

    # Plot 4: Data density along track
    ax4 = axes[1, 1]
    lon_bins = np.linspace(merged['longitude'].min(), merged['longitude'].max(), 50)
    lon_centers = (lon_bins[:-1] + lon_bins[1:]) / 2
    counts = pd.cut(merged['longitude'], lon_bins).value_counts().sort_index().values
    ax4.bar(lon_centers, counts, width=(lon_bins[1]-lon_bins[0])*0.8)
    ax4.axvline(x=-86.235, color='red', linestyle='--', alpha=0.5, label='Eastern boundary')
    ax4.axvline(x=-86.237, color='blue', linestyle='--', alpha=0.5, label='Western boundary')
    ax4.set_xlabel('Longitude')
    ax4.set_ylabel('Data Point Count')
    ax4.set_title('GPS Data Density by Longitude')
    ax4.legend()

    plt.tight_layout()

    # Save
    output_dir = Path(__file__).parent.parent / 'outputs'
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / 'missing_corners_diagnosis.png'
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"\nSaved: {output_file}")

    # Conclusion
    print("\n" + "=" * 70)
    print("DIAGNOSIS SUMMARY")
    print("=" * 70)

    if len(eastern) < len(western) * 0.3:
        print("\n⚠️  ISSUE: Eastern section has very sparse GPS data")
        print("   This explains why no corners are detected there")
    else:
        eastern_max_brake = eastern['pbrake_f'].max() if len(eastern) > 0 else 0
        if eastern_max_brake < 60:
            print("\n⚠️  ISSUE: Eastern section has no heavy braking events")
            print(f"   Max brake pressure: {eastern_max_brake:.1f} bar")
            print("   These might be fast corners with light braking")
        else:
            print("\n✅ Eastern section has sufficient data and brake events")
            print("   Corners should be detectable - check clustering parameters")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
