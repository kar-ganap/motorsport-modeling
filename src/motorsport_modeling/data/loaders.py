"""
Data loading utilities for motorsport telemetry data.

This module provides functions to load and process telemetry data from
CSV files in long format (one row per measurement).
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Optional, Union, List
import time


def load_telemetry(
    file_path: Union[str, Path],
    vehicle: Optional[int] = None,
    lap: Optional[Union[int, List[int]]] = None,
    parameters: Optional[List[str]] = None,
    wide_format: bool = True,
    verbose: bool = False
) -> pd.DataFrame:
    """
    Load telemetry data from CSV file.

    Parameters
    ----------
    file_path : str or Path
        Path to CSV file containing telemetry data
    vehicle : int, optional
        Filter by vehicle number (e.g., 55 for car #55)
    lap : int or list of int, optional
        Filter by lap number(s)
    parameters : list of str, optional
        Filter by specific telemetry parameters
        (e.g., ['speed', 'ath', 'pbrake_f'])
    wide_format : bool, default=True
        If True, pivot to wide format (one row per timestamp)
        If False, keep long format (one row per measurement)
    verbose : bool, default=False
        Print loading progress and statistics

    Returns
    -------
    pd.DataFrame
        Telemetry data in requested format

    Examples
    --------
    >>> # Load all data for vehicle #55, lap 7
    >>> df = load_telemetry('data.csv', vehicle=55, lap=7)

    >>> # Load speed and throttle for multiple laps
    >>> df = load_telemetry('data.csv', vehicle=55, lap=[5,6,7],
    ...                     parameters=['speed', 'ath'])

    >>> # Load all data in long format
    >>> df = load_telemetry('data.csv', wide_format=False)
    """
    start_time = time.time()

    if verbose:
        print(f"Loading telemetry from: {file_path}")

    # Load CSV
    df = pd.read_csv(file_path)

    if verbose:
        print(f"  Loaded {len(df):,} rows in {time.time() - start_time:.2f}s")

    # Filter by vehicle
    if vehicle is not None:
        df = df[df['vehicle_number'] == vehicle].copy()
        if verbose:
            print(f"  Filtered to vehicle #{vehicle}: {len(df):,} rows")

    # Filter by lap
    if lap is not None:
        if isinstance(lap, int):
            lap = [lap]
        df = df[df['lap'].isin(lap)].copy()
        if verbose:
            print(f"  Filtered to lap(s) {lap}: {len(df):,} rows")

    # Filter by parameters
    if parameters is not None:
        df = df[df['telemetry_name'].isin(parameters)].copy()
        if verbose:
            print(f"  Filtered to {len(parameters)} parameters: {len(df):,} rows")

    # Convert timestamp to datetime
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    if wide_format:
        # Pivot to wide format
        if verbose:
            print("  Pivoting to wide format...")

        # Pivot: rows are timestamps, columns are telemetry parameters
        df_wide = df.pivot_table(
            index=['vehicle_number', 'lap', 'timestamp'],
            columns='telemetry_name',
            values='telemetry_value',
            aggfunc='first'  # Take first value if duplicates
        ).reset_index()

        # Flatten column names
        df_wide.columns.name = None

        # Sort by timestamp
        df_wide = df_wide.sort_values(['vehicle_number', 'lap', 'timestamp'])

        if verbose:
            print(f"  Wide format: {len(df_wide):,} rows × {len(df_wide.columns)} columns")
            print(f"  Total time: {time.time() - start_time:.2f}s")

        return df_wide
    else:
        # Return long format
        df = df.sort_values(['vehicle_number', 'lap', 'timestamp', 'telemetry_name'])

        if verbose:
            print(f"  Total time: {time.time() - start_time:.2f}s")

        return df


def load_gps_data(
    file_path: Union[str, Path],
    vehicle: Optional[int] = None,
    lap: Optional[Union[int, List[int]]] = None,
    verbose: bool = False
) -> pd.DataFrame:
    """
    Load GPS telemetry data (latitude, longitude, lap distance).

    This is a convenience function that loads only GPS-related parameters.

    Parameters
    ----------
    file_path : str or Path
        Path to CSV file containing telemetry data
    vehicle : int, optional
        Filter by vehicle number
    lap : int or list of int, optional
        Filter by lap number(s)
    verbose : bool, default=False
        Print loading progress

    Returns
    -------
    pd.DataFrame
        GPS data with columns: vehicle_number, lap, timestamp,
        VBOX_Lat_Min, VBOX_Long_Minutes, Laptrigger_lapdist_dls

    Examples
    --------
    >>> gps = load_gps_data('data.csv', vehicle=55, lap=7)
    >>> plt.plot(gps['VBOX_Long_Minutes'], gps['VBOX_Lat_Min'])
    """
    gps_params = ['VBOX_Lat_Min', 'VBOX_Long_Minutes', 'Laptrigger_lapdist_dls']

    df = load_telemetry(
        file_path,
        vehicle=vehicle,
        lap=lap,
        parameters=gps_params,
        wide_format=True,
        verbose=verbose
    )

    # Check if GPS data is present
    if 'VBOX_Lat_Min' not in df.columns or 'VBOX_Long_Minutes' not in df.columns:
        raise ValueError(
            "GPS data not found in telemetry. "
            "This dataset may not include GPS parameters."
        )

    # Rename for convenience
    df = df.rename(columns={
        'VBOX_Lat_Min': 'latitude',
        'VBOX_Long_Minutes': 'longitude',
        'Laptrigger_lapdist_dls': 'lap_distance'
    })

    # Remove rows with missing GPS
    df = df.dropna(subset=['latitude', 'longitude'])

    if verbose:
        print(f"GPS data: {len(df):,} points")

    return df


def get_available_vehicles(file_path: Union[str, Path]) -> List[int]:
    """
    Get list of vehicle numbers present in the dataset.

    Parameters
    ----------
    file_path : str or Path
        Path to CSV file

    Returns
    -------
    list of int
        Sorted list of vehicle numbers

    Examples
    --------
    >>> vehicles = get_available_vehicles('data.csv')
    >>> print(f"Found {len(vehicles)} vehicles: {vehicles}")
    """
    df = pd.read_csv(file_path, usecols=['vehicle_number'])
    vehicles = sorted(df['vehicle_number'].dropna().unique())
    return [int(v) for v in vehicles]


def get_available_parameters(file_path: Union[str, Path]) -> List[str]:
    """
    Get list of telemetry parameters present in the dataset.

    Parameters
    ----------
    file_path : str or Path
        Path to CSV file

    Returns
    -------
    list of str
        Sorted list of parameter names

    Examples
    --------
    >>> params = get_available_parameters('data.csv')
    >>> print(f"Found {len(params)} parameters: {params}")
    """
    df = pd.read_csv(file_path, usecols=['telemetry_name'])
    parameters = sorted(df['telemetry_name'].dropna().unique())
    return parameters


def validate_data_completeness(
    file_path: Union[str, Path],
    expected_vehicles: Optional[int] = None,
    expected_parameters: Optional[List[str]] = None,
    verbose: bool = True
) -> dict:
    """
    Validate data completeness and quality.

    Parameters
    ----------
    file_path : str or Path
        Path to CSV file
    expected_vehicles : int, optional
        Expected number of vehicles (e.g., 19 for full race)
    expected_parameters : list of str, optional
        Expected parameter names
    verbose : bool, default=True
        Print validation results

    Returns
    -------
    dict
        Validation results with keys:
        - vehicles_found: list of int
        - parameters_found: list of str
        - has_gps: bool
        - total_rows: int
        - validation_passed: bool

    Examples
    --------
    >>> result = validate_data_completeness('data.csv', expected_vehicles=19)
    >>> if not result['validation_passed']:
    ...     print("Data validation failed!")
    """
    if verbose:
        print("=" * 60)
        print("DATA VALIDATION")
        print("=" * 60)

    # Get vehicles and parameters
    vehicles = get_available_vehicles(file_path)
    parameters = get_available_parameters(file_path)

    # Check for GPS
    has_gps = ('VBOX_Lat_Min' in parameters and
               'VBOX_Long_Minutes' in parameters)

    # Count total rows
    df = pd.read_csv(file_path, usecols=['vehicle_number'])
    total_rows = len(df)

    # Validation checks
    validation_passed = True

    if verbose:
        print(f"\nVehicles found: {len(vehicles)}")
        print(f"  {vehicles}")

        if expected_vehicles is not None:
            if len(vehicles) == expected_vehicles:
                print(f"  ✅ Expected {expected_vehicles} vehicles - PASS")
            else:
                print(f"  ❌ Expected {expected_vehicles} vehicles - FAIL")
                validation_passed = False

        print(f"\nParameters found: {len(parameters)}")
        for param in parameters:
            print(f"  - {param}")

        if expected_parameters is not None:
            missing = set(expected_parameters) - set(parameters)
            if not missing:
                print(f"  ✅ All expected parameters present - PASS")
            else:
                print(f"  ❌ Missing parameters: {missing} - FAIL")
                validation_passed = False

        print(f"\nGPS data: {'✅ PRESENT' if has_gps else '❌ NOT FOUND'}")
        print(f"Total rows: {total_rows:,}")

        print("\n" + "=" * 60)
        if validation_passed:
            print("✅ VALIDATION PASSED")
        else:
            print("❌ VALIDATION FAILED")
        print("=" * 60)

    return {
        'vehicles_found': vehicles,
        'parameters_found': parameters,
        'has_gps': has_gps,
        'total_rows': total_rows,
        'validation_passed': validation_passed
    }
