"""
Data loading and processing module.

Provides loaders for telemetry data, lap times, and track metadata.
"""

from .loaders import (
    load_telemetry,
    load_gps_data,
    get_available_vehicles,
    get_available_parameters,
    validate_data_completeness
)

from .gps_analysis import (
    identify_corners_from_gps,
    get_corner_at_position,
    extract_corner_telemetry,
    validate_corner_identification
)

__all__ = [
    'load_telemetry',
    'load_gps_data',
    'get_available_vehicles',
    'get_available_parameters',
    'validate_data_completeness',
    'identify_corners_from_gps',
    'get_corner_at_position',
    'extract_corner_telemetry',
    'validate_corner_identification'
]
