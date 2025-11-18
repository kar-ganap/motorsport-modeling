"""
Analyze detected corner positions against known Indianapolis track layout.

This script:
1. Loads the detected corners
2. Compares GPS coordinates with known track features
3. Identifies which corners are likely merged/split
4. Suggests parameter adjustments

Usage:
    uv run python scripts/analyze_corner_positions.py
"""

from pathlib import Path
import pandas as pd
import numpy as np

# Known Indianapolis Road Course reference points (from circuit map)
TRACK_REFERENCE = {
    'finish_line': (39.7931499, -86.2388700),
    'pit_in': (39.7894100, -86.2373000),
    'pit_out': (39.79669, -86.23881),
}

# Approximate corner locations based on track map analysis
# These are estimates - the map doesn't give exact GPS for each corner
EXPECTED_CORNERS = {
    # Sector 1: Corners 1-6 (southern portion, infield entry)
    1: "Entry to infield after main straight - heavy braking",
    2: "Second part of turn 1 complex",
    3: "Chicane entry (tight)",
    4: "Chicane exit (tight)",
    5: "Left-hander before back straight",
    6: "Right kink onto back straight",

    # Sector 2: Corners 7-10 (northern portion)
    7: "End of back straight - heavy braking",
    8: "Left-hander",
    9: "Right-hander approaching oval",
    10: "Entry to oval section",

    # Sector 3: Corners 11-14 (oval and return)
    11: "Oval turn 1",
    12: "Exit oval into infield",
    13: "Tight right before pit straight",
    14: "Final corner onto main straight",
}


def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two GPS points in meters."""
    R = 6371000  # Earth's radius in meters

    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
    c = 2 * np.arcsin(np.sqrt(a))

    return R * c


def main():
    # Load detected corners
    corners_file = Path(__file__).parent.parent / 'data' / 'processed' / 'corners_race1_brake.csv'

    if not corners_file.exists():
        print(f"ERROR: {corners_file} not found")
        print("Run identify_indy_corners_brake.py first")
        return

    corners = pd.read_csv(corners_file)

    print("=" * 70)
    print("INDIANAPOLIS CORNER POSITION ANALYSIS")
    print("=" * 70)

    print(f"\nExpected corners: 14")
    print(f"Detected corners: {len(corners)}")
    print(f"Missing: {14 - len(corners)} corners")

    # Sort corners by track position (approximate using longitude then latitude)
    # The track flows roughly: south (start) -> west -> north -> east -> south
    corners_sorted = corners.sort_values(['longitude', 'latitude']).reset_index(drop=True)

    print("\n" + "-" * 70)
    print("DETECTED CORNERS (sorted by position)")
    print("-" * 70)

    for i, row in corners_sorted.iterrows():
        # Calculate distance to finish line
        dist_to_finish = haversine_distance(
            row['latitude'], row['longitude'],
            TRACK_REFERENCE['finish_line'][0], TRACK_REFERENCE['finish_line'][1]
        )

        print(f"\nCorner {row['corner_id']} ({row['corner_type']}):")
        print(f"  GPS: ({row['latitude']:.5f}, {row['longitude']:.5f})")
        print(f"  Brake: {row['max_brake']:.1f} bar")
        print(f"  Observations: {row['n_observations']}")
        print(f"  Distance to S/F: {dist_to_finish:.0f}m")

    # Analyze corner clustering
    print("\n" + "-" * 70)
    print("CORNER PROXIMITY ANALYSIS")
    print("-" * 70)
    print("\nCorners within 50m of each other (potential duplicates/splits):")

    close_pairs = []
    for i in range(len(corners)):
        for j in range(i+1, len(corners)):
            dist = haversine_distance(
                corners.iloc[i]['latitude'], corners.iloc[i]['longitude'],
                corners.iloc[j]['latitude'], corners.iloc[j]['longitude']
            )
            if dist < 50:
                close_pairs.append((
                    corners.iloc[i]['corner_id'],
                    corners.iloc[j]['corner_id'],
                    dist
                ))
                print(f"  Corner {corners.iloc[i]['corner_id']} <-> Corner {corners.iloc[j]['corner_id']}: {dist:.1f}m")

    if not close_pairs:
        print("  None found")

    # Analyze gaps (potential merged corners)
    print("\n" + "-" * 70)
    print("LARGE GAPS ANALYSIS")
    print("-" * 70)
    print("\nLarge gaps between consecutive corners (potential merged corners):")

    # Sort by lap distance if available, otherwise use rough position
    corners_by_pos = corners.sort_values('corner_id').reset_index(drop=True)

    for i in range(len(corners_by_pos) - 1):
        dist = haversine_distance(
            corners_by_pos.iloc[i]['latitude'], corners_by_pos.iloc[i]['longitude'],
            corners_by_pos.iloc[i+1]['latitude'], corners_by_pos.iloc[i+1]['longitude']
        )
        if dist > 200:  # Large gap
            print(f"  Corner {corners_by_pos.iloc[i]['corner_id']} -> Corner {corners_by_pos.iloc[i+1]['corner_id']}: {dist:.0f}m gap")

    # Recommendations
    print("\n" + "=" * 70)
    print("DIAGNOSIS & RECOMMENDATIONS")
    print("=" * 70)

    if close_pairs:
        print("\n🔴 ISSUE: Multiple corners detected in same location")
        print("   These are likely the turn 1/14 complex near start/finish")
        print("   SOLUTION: Increase DBSCAN eps to merge these")

    print("\n🔴 ISSUE: Missing 4 corners (14 expected, 10 detected)")
    print("   Likely causes:")
    print("   1. Tight chicanes (3-4, 5-6, 12-13) merged into single corners")
    print("   2. Light braking corners filtered out by threshold")
    print("")
    print("   SOLUTIONS:")
    print("   1. Decrease DBSCAN eps to separate tight corner complexes")
    print("   2. Lower brake_threshold_percentile (currently 60)")
    print("   3. Increase min_corners parameter")
    print("   4. Use lap_distance instead of GPS for corner ordering")

    print("\n📋 SUGGESTED PARAMETER CHANGES:")
    print("   - eps: 0.00015 (was ~0.0002) - smaller to separate chicanes")
    print("   - brake_threshold_percentile: 50 (was 60) - catch lighter braking")
    print("   - min_corners: 12 (force algorithm to find more)")
    print("   - Consider using Laptrigger_lapdist_dls for corner ordering")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
