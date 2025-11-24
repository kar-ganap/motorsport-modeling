"""
Visualize detected corners on the Indianapolis track layout.

This script:
1. Plots the GPS trace to show the track shape
2. Overlays detected corners
3. Adds reference points (start/finish, pit in/out)
4. Highlights gaps where corners might be missing

Usage:
    uv run python scripts/visualize_corners.py
"""

from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Circle

from motorsport_modeling.data import (
    load_telemetry,
    load_gps_data,
)

# Reference points from the track map
REFERENCE_POINTS = {
    'Start/Finish': (39.7931499, -86.2388700),
    'Pit In': (39.7894100, -86.2373000),
    'Pit Out': (39.79669, -86.23881),
}


def main():
    data_file = Path(__file__).parent.parent / 'data' / 'raw' / 'R1_indianapolis_motor_speedway_telemetry.csv'
    corners_file = Path(__file__).parent.parent / 'data' / 'processed' / 'corners_race1_final.csv'

    if not data_file.exists():
        print(f"ERROR: {data_file} not found")
        return

    if not corners_file.exists():
        print(f"ERROR: {corners_file} not found")
        print("Run identify_corners_tuned_v2.py first")
        return

    print("Loading data...")

    # Load GPS trace for one lap to show track shape
    vehicle = 55
    lap = 10  # Use a mid-race lap

    gps = load_gps_data(data_file, vehicle=vehicle, lap=lap, verbose=False)
    gps = gps.sort_values('timestamp')

    # Load detected corners
    corners = pd.read_csv(corners_file)

    print(f"GPS points: {len(gps)}")
    print(f"Detected corners: {len(corners)}")

    # Create figure
    fig, axes = plt.subplots(1, 2, figsize=(16, 8))

    # === Plot 1: Track overview with corners ===
    ax1 = axes[0]

    # Plot track outline
    ax1.plot(gps['longitude'], gps['latitude'], 'b-', linewidth=1, alpha=0.5, label='Track')

    # Plot corners
    for _, corner in corners.iterrows():
        color = {'light': 'green', 'medium': 'orange', 'heavy': 'red'}[corner['corner_type']]
        ax1.scatter(corner['longitude'], corner['latitude'],
                   c=color, s=100, zorder=5, edgecolors='black', linewidth=1)
        ax1.annotate(f"{corner['corner_id']}",
                    (corner['longitude'], corner['latitude']),
                    xytext=(5, 5), textcoords='offset points',
                    fontsize=8, fontweight='bold')

    # Plot reference points
    for name, (lat, lon) in REFERENCE_POINTS.items():
        ax1.scatter(lon, lat, marker='s', s=80, c='purple', zorder=6, edgecolors='black')
        ax1.annotate(name, (lon, lat), xytext=(5, -10), textcoords='offset points',
                    fontsize=7, color='purple')

    ax1.set_xlabel('Longitude')
    ax1.set_ylabel('Latitude')
    ax1.set_title('Indianapolis Road Course - Detected Corners\n(Red=Heavy, Orange=Medium, Green=Light)')
    ax1.grid(True, alpha=0.3)
    ax1.set_aspect('equal')

    # === Plot 2: Corner spacing analysis ===
    ax2 = axes[1]

    # Calculate distances between consecutive corners
    # Sort by track position (roughly by longitude then latitude)
    corners_sorted = corners.sort_values(['longitude', 'latitude']).reset_index(drop=True)

    # Show corner positions along track
    corner_nums = range(1, len(corners_sorted) + 1)
    brake_pressures = corners_sorted['max_brake'].values

    bars = ax2.bar(corner_nums, brake_pressures,
                   color=[{'light': 'green', 'medium': 'orange', 'heavy': 'red'}[t]
                          for t in corners_sorted['corner_type']])

    ax2.axhline(y=60, color='orange', linestyle='--', alpha=0.5, label='Medium threshold')
    ax2.axhline(y=30, color='green', linestyle='--', alpha=0.5, label='Light threshold')

    ax2.set_xlabel('Corner Number (sorted by position)')
    ax2.set_ylabel('Max Brake Pressure (bar)')
    ax2.set_title('Brake Pressure by Corner')
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()

    # Save figure
    output_dir = Path(__file__).parent.parent / 'outputs'
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / 'corners_visualization.png'
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"\nSaved: {output_file}")

    # === Analysis: Identify potential gaps ===
    print("\n" + "=" * 60)
    print("CORNER ANALYSIS")
    print("=" * 60)

    # Calculate distances between corners
    from math import radians, sin, cos, sqrt, atan2

    def haversine(lat1, lon1, lat2, lon2):
        R = 6371000  # Earth radius in meters
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        return 2 * R * atan2(sqrt(a), sqrt(1-a))

    print("\nCorner distances (in track order):")
    for i in range(len(corners_sorted) - 1):
        c1 = corners_sorted.iloc[i]
        c2 = corners_sorted.iloc[i + 1]
        dist = haversine(c1['latitude'], c1['longitude'],
                        c2['latitude'], c2['longitude'])

        gap_warning = " ⚠️ LARGE GAP" if dist > 300 else ""
        print(f"  Corner {c1['corner_id']} -> {c2['corner_id']}: {dist:.0f}m{gap_warning}")

    # Expected vs actual
    print(f"\n📊 Summary:")
    print(f"   Expected corners: 14")
    print(f"   Detected corners: {len(corners)}")
    print(f"   Missing: {14 - len(corners)}")

    print("\n🔍 Potential issues:")

    # Check for corners near same location
    close_pairs = []
    for i in range(len(corners)):
        for j in range(i + 1, len(corners)):
            dist = haversine(corners.iloc[i]['latitude'], corners.iloc[i]['longitude'],
                           corners.iloc[j]['latitude'], corners.iloc[j]['longitude'])
            if dist < 30:
                close_pairs.append((corners.iloc[i]['corner_id'],
                                   corners.iloc[j]['corner_id'], dist))

    if close_pairs:
        print("   Corners very close together (<30m) - might be over-split:")
        for c1, c2, d in close_pairs:
            print(f"     Corner {c1} <-> Corner {c2}: {d:.0f}m")
    else:
        print("   No over-split corners detected")

    # Check for large gaps
    large_gaps = []
    for i in range(len(corners_sorted) - 1):
        c1 = corners_sorted.iloc[i]
        c2 = corners_sorted.iloc[i + 1]
        dist = haversine(c1['latitude'], c1['longitude'],
                        c2['latitude'], c2['longitude'])
        if dist > 400:
            large_gaps.append((c1['corner_id'], c2['corner_id'], dist))

    if large_gaps:
        print("   Large gaps (>400m) - might be missing corners:")
        for c1, c2, d in large_gaps:
            print(f"     Between corners {c1} and {c2}: {d:.0f}m")
    else:
        print("   No large gaps detected")

    print("\n" + "=" * 60)

    # Don't show interactively - just save
    # plt.show()


if __name__ == "__main__":
    main()
