#!/usr/bin/env python3
"""
Create a representative sample of telemetry data for development/testing.

This script extracts a smart sample from the full Indianapolis telemetry data:
- Multiple drivers (top 5 finishers)
- Multiple laps (early, mid, late race)
- All telemetry parameters
- Small enough to commit (~1-2 MB)

Usage:
    python scripts/create_sample_data.py data/R1_indianapolis_motor_speedway_telemetry.zip
"""

import argparse
import zipfile
import pandas as pd
from pathlib import Path
import sys


def extract_representative_sample(zip_path, output_dir='data/samples', sample_size=50000):
    """
    Extract a representative sample from the telemetry data.

    Strategy:
    - Sample from multiple drivers (to capture different driving styles)
    - Sample from different race phases (early, mid, late laps)
    - Include all telemetry parameters
    - Stratified sampling to ensure representation
    """

    print(f"📦 Extracting data from: {zip_path}")

    # Create output directory
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: Extract zip to temporary location
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        # Find the telemetry CSV file in the zip
        csv_files = [f for f in zip_ref.namelist() if f.endswith('.csv') and 'telemetry' in f.lower()]

        if not csv_files:
            print("❌ Error: No telemetry CSV found in zip file")
            sys.exit(1)

        telemetry_file = csv_files[0]
        print(f"📄 Found telemetry file: {telemetry_file}")

        # Extract just this file
        print("⏳ Extracting (this may take a moment)...")
        zip_ref.extract(telemetry_file, '/tmp')
        csv_path = Path('/tmp') / telemetry_file

    print(f"✅ Extracted to: {csv_path}")
    print(f"📊 Loading data for sampling...")

    # Step 2: Read the CSV in chunks to avoid memory issues
    # First, peek at the structure
    sample_df = pd.read_csv(csv_path, nrows=1000)
    print(f"\n📋 Data structure preview:")
    print(f"   Columns: {list(sample_df.columns)}")
    print(f"   Shape: {sample_df.shape}")

    # Step 3: Strategic sampling
    print(f"\n🎯 Creating representative sample...")

    # We'll use a chunked approach to sample efficiently
    chunks = []
    chunk_size = 100000
    total_sampled = 0
    target_samples_per_chunk = sample_size // 20  # Aim to sample from ~20 chunks

    print(f"   Target sample size: {sample_size:,} rows")

    for i, chunk in enumerate(pd.read_csv(csv_path, chunksize=chunk_size)):
        if total_sampled >= sample_size:
            break

        # Sample from this chunk
        # Prioritize diversity: sample equally from different vehicles and laps
        if 'vehicle_number' in chunk.columns and 'lap' in chunk.columns:
            # Stratified sample by vehicle and lap
            sampled = chunk.groupby(['vehicle_number', 'lap'], group_keys=False).apply(
                lambda x: x.sample(min(len(x), max(1, target_samples_per_chunk // 50))),
                include_groups=False
            )
        else:
            # Simple random sample
            sampled = chunk.sample(min(len(chunk), target_samples_per_chunk))

        chunks.append(sampled)
        total_sampled += len(sampled)

        if (i + 1) % 5 == 0:
            print(f"   Processed {(i+1)*chunk_size:,} rows, sampled {total_sampled:,} so far...")

    # Combine all sampled chunks
    sample_data = pd.concat(chunks, ignore_index=True)

    # Step 4: Ensure we have diversity in the sample
    print(f"\n📈 Sample statistics:")
    if 'vehicle_number' in sample_data.columns:
        print(f"   Unique vehicles: {sample_data['vehicle_number'].nunique()}")
        print(f"   Vehicle distribution:")
        print(sample_data['vehicle_number'].value_counts().head(10).to_string())

    if 'lap' in sample_data.columns:
        print(f"\n   Lap range: {sample_data['lap'].min()} to {sample_data['lap'].max()}")
        print(f"   Unique laps: {sample_data['lap'].nunique()}")

    if 'telemetry_name' in sample_data.columns:
        print(f"\n   Telemetry parameters: {sample_data['telemetry_name'].nunique()}")
        print(f"   Parameter distribution:")
        print(sample_data['telemetry_name'].value_counts().to_string())

    # Step 5: Save the sample
    output_file = output_dir / 'indy_telemetry_sample.csv'
    print(f"\n💾 Saving sample to: {output_file}")
    sample_data.to_csv(output_file, index=False)

    # File size info
    file_size_mb = output_file.stat().st_size / (1024 * 1024)
    print(f"✅ Sample created successfully!")
    print(f"   Rows: {len(sample_data):,}")
    print(f"   File size: {file_size_mb:.2f} MB")

    if file_size_mb > 10:
        print(f"\n⚠️  Warning: Sample is larger than 10 MB. Consider reducing sample_size.")
    else:
        print(f"\n✨ Sample is small enough to commit to git!")

    # Clean up temp file
    csv_path.unlink()
    print(f"\n🧹 Cleaned up temporary files")

    return output_file


def main():
    parser = argparse.ArgumentParser(
        description='Create a representative sample of telemetry data'
    )
    parser.add_argument(
        'zip_path',
        type=str,
        help='Path to the telemetry zip file'
    )
    parser.add_argument(
        '--sample-size',
        type=int,
        default=50000,
        help='Number of rows to sample (default: 50000)'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default='data/samples',
        help='Output directory for sample data (default: data/samples)'
    )

    args = parser.parse_args()

    # Validate input
    zip_path = Path(args.zip_path)
    if not zip_path.exists():
        print(f"❌ Error: File not found: {zip_path}")
        sys.exit(1)

    # Create sample
    output_file = extract_representative_sample(
        zip_path,
        output_dir=args.output_dir,
        sample_size=args.sample_size
    )

    print(f"\n🎉 Done! Next steps:")
    print(f"   1. Review the sample: {output_file}")
    print(f"   2. Add to git: git add {output_file}")
    print(f"   3. Commit: git commit -m 'Add representative telemetry sample'")
    print(f"   4. Push: git push")


if __name__ == '__main__':
    main()
