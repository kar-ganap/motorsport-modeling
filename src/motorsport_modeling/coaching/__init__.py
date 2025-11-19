"""
Coaching module for real-time driver analysis.

Contains:
- DriverProfile: Computes and stores driver characteristics
- StateMonitor: Real-time state monitoring and alert generation
"""

from .driver_profile import DriverProfile
from .state_monitor import StateMonitor, Alert

__all__ = ['DriverProfile', 'StateMonitor', 'Alert']
