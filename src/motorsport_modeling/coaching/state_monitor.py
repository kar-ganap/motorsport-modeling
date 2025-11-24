"""
StateMonitor - Real-time state monitoring and alert generation.

Monitors state features (brake_cv, coasting_pct) against driver baselines
and generates actionable alerts when deviations occur.

Usage:
    from motorsport_modeling.coaching import StateMonitor, DriverProfile

    # Initialize with driver profile
    profile = DriverProfile.from_telemetry(telemetry, vehicle_number=72, laps=[1,2,3,4,5])
    monitor = StateMonitor(profile)

    # Process each lap during race
    state = monitor.process_lap(telemetry, lap=10)
    alerts = monitor.generate_alerts()

    for alert in alerts:
        print(alert.format_for_radio())
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum
import pandas as pd
import numpy as np

from .driver_profile import DriverProfile
from ..metrics.tier1_metrics import (
    compute_coasting_pct,
    compute_braking_smoothness
)


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = 1      # 1-2 sigma deviation
    WARNING = 2   # 2-3 sigma deviation
    CRITICAL = 3  # >3 sigma deviation


@dataclass
class Alert:
    """
    Actionable alert for driver state deviation.

    Contains the deviation information and specific action to take.
    """
    lap: int
    vehicle_number: int
    metric: str
    severity: AlertSeverity
    current_value: float
    baseline_mean: float
    baseline_std: float
    deviation_sigma: float
    action: str
    why: str

    @property
    def severity_icon(self) -> str:
        """Get icon for severity level."""
        icons = {
            AlertSeverity.INFO: "ℹ️",
            AlertSeverity.WARNING: "⚠️",
            AlertSeverity.CRITICAL: "🔴"
        }
        return icons.get(self.severity, "")

    def format_for_display(self) -> str:
        """Format alert for dashboard display."""
        # Handle combined alerts (no single metric value)
        if self.metric == 'combined' or self.baseline_mean == 0:
            return (
                f"{self.severity_icon} Lap {self.lap} | #{self.vehicle_number}\n"
                f"{self.metric_display}\n"
                f"→ {self.action}"
            )

        change_pct = 100 * (self.current_value - self.baseline_mean) / self.baseline_mean
        direction = "+" if change_pct > 0 else ""

        return (
            f"{self.severity_icon} Lap {self.lap} | #{self.vehicle_number}\n"
            f"{self.metric_display} {direction}{change_pct:.0f}%\n"
            f"→ {self.action}"
        )

    def format_for_radio(self) -> str:
        """Format as brief radio message to driver."""
        return self.action

    @property
    def metric_display(self) -> str:
        """Human-readable metric name."""
        names = {
            'brake_cv': 'Brake consistency',
            'coasting_pct': 'Coasting',
            'combined': 'Multiple metrics degrading'
        }
        return names.get(self.metric, self.metric)


# Alert-to-action mapping
ALERT_ACTIONS = {
    'brake_cv': {
        'action': "Smooth on the brakes, you're getting inconsistent",
        'why': "Inconsistent braking leads to unpredictable car behavior"
    },
    'coasting_pct': {
        'action': "Commit to the throttle earlier on exit",
        'why': "Coasting loses time and indicates hesitation"
    }
}

# Combined degradation (both metrics)
COMBINED_ACTION = {
    'action': "Take a breath, reset your rhythm",
    'why': "Combined degradation suggests mental fatigue"
}


@dataclass
class DriverState:
    """Current state for a driver on a specific lap."""
    lap: int
    vehicle_number: int
    brake_cv: float
    coasting_pct: float

    # Deviations from baseline (in sigma)
    brake_cv_sigma: float = 0.0
    coasting_sigma: float = 0.0


class StateMonitor:
    """
    Monitors driver state and generates alerts.

    Compares state features against driver's own baseline (not field average)
    and generates alerts when significant deviations occur.
    """

    def __init__(
        self,
        profile: DriverProfile,
        warning_threshold: float = 2.0,
        critical_threshold: float = 3.0
    ):
        """
        Initialize state monitor with driver profile.

        Parameters
        ----------
        profile : DriverProfile
            Driver's baseline profile
        warning_threshold : float
            Sigma threshold for warning alerts (default 2.0)
        critical_threshold : float
            Sigma threshold for critical alerts (default 3.0)
        """
        self.profile = profile
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold

        # History for trend detection
        self.state_history: List[DriverState] = []
        self.pending_alerts: List[Alert] = []

    def process_lap(
        self,
        telemetry: pd.DataFrame,
        lap: int
    ) -> DriverState:
        """
        Process a lap and compute current state.

        Parameters
        ----------
        telemetry : pd.DataFrame
            Telemetry data
        lap : int
            Lap number to process

        Returns
        -------
        DriverState
            Current state for this lap
        """
        vehicle_number = self.profile.vehicle_number

        # Compute state features
        try:
            coasting = compute_coasting_pct(telemetry, vehicle_number, lap)
            braking = compute_braking_smoothness(telemetry, vehicle_number, lap)

            brake_cv = braking.get('peak_brake_cv', 0)
            coasting_pct = coasting['coasting_pct']
        except Exception:
            # Use last known values if computation fails
            if self.state_history:
                last = self.state_history[-1]
                brake_cv = last.brake_cv
                coasting_pct = last.coasting_pct
            else:
                brake_cv = self.profile.brake_cv_mean
                coasting_pct = self.profile.coasting_pct_mean

        # Compute deviations from baseline
        baselines = self.profile.state_baselines

        brake_cv_sigma = 0.0
        if baselines['brake_cv']['std'] > 0:
            brake_cv_sigma = (brake_cv - baselines['brake_cv']['mean']) / baselines['brake_cv']['std']

        coasting_sigma = 0.0
        if baselines['coasting_pct']['std'] > 0:
            coasting_sigma = (coasting_pct - baselines['coasting_pct']['mean']) / baselines['coasting_pct']['std']

        # Create state
        state = DriverState(
            lap=lap,
            vehicle_number=vehicle_number,
            brake_cv=brake_cv,
            coasting_pct=coasting_pct,
            brake_cv_sigma=brake_cv_sigma,
            coasting_sigma=coasting_sigma
        )

        # Add to history
        self.state_history.append(state)

        # Generate alerts based on state
        self._check_for_alerts(state)

        return state

    def _check_for_alerts(self, state: DriverState) -> None:
        """Check state for alert conditions and add to pending alerts."""
        baselines = self.profile.state_baselines

        # Check brake CV
        if state.brake_cv_sigma > 1.0:  # Any positive deviation
            severity = self._get_severity(state.brake_cv_sigma)

            if severity:
                alert = Alert(
                    lap=state.lap,
                    vehicle_number=state.vehicle_number,
                    metric='brake_cv',
                    severity=severity,
                    current_value=state.brake_cv,
                    baseline_mean=baselines['brake_cv']['mean'],
                    baseline_std=baselines['brake_cv']['std'],
                    deviation_sigma=state.brake_cv_sigma,
                    action=ALERT_ACTIONS['brake_cv']['action'],
                    why=ALERT_ACTIONS['brake_cv']['why']
                )
                self.pending_alerts.append(alert)

        # Check coasting
        if state.coasting_sigma > 1.0:
            severity = self._get_severity(state.coasting_sigma)

            if severity:
                alert = Alert(
                    lap=state.lap,
                    vehicle_number=state.vehicle_number,
                    metric='coasting_pct',
                    severity=severity,
                    current_value=state.coasting_pct,
                    baseline_mean=baselines['coasting_pct']['mean'],
                    baseline_std=baselines['coasting_pct']['std'],
                    deviation_sigma=state.coasting_sigma,
                    action=ALERT_ACTIONS['coasting_pct']['action'],
                    why=ALERT_ACTIONS['coasting_pct']['why']
                )
                self.pending_alerts.append(alert)

        # Check for combined degradation
        if state.brake_cv_sigma > self.warning_threshold and state.coasting_sigma > self.warning_threshold:
            # Remove individual alerts and add combined
            self.pending_alerts = [
                a for a in self.pending_alerts
                if not (a.lap == state.lap and a.vehicle_number == state.vehicle_number)
            ]

            alert = Alert(
                lap=state.lap,
                vehicle_number=state.vehicle_number,
                metric='combined',
                severity=AlertSeverity.CRITICAL,
                current_value=0,  # N/A for combined
                baseline_mean=0,
                baseline_std=0,
                deviation_sigma=max(state.brake_cv_sigma, state.coasting_sigma),
                action=COMBINED_ACTION['action'],
                why=COMBINED_ACTION['why']
            )
            self.pending_alerts.append(alert)

        # Check for progressive degradation (3+ laps trending worse)
        if len(self.state_history) >= 3:
            self._check_progressive_degradation()

    def _get_severity(self, sigma: float) -> Optional[AlertSeverity]:
        """Get alert severity based on sigma deviation."""
        if sigma >= self.critical_threshold:
            return AlertSeverity.CRITICAL
        elif sigma >= self.warning_threshold:
            return AlertSeverity.WARNING
        elif sigma >= 1.0:
            return AlertSeverity.INFO
        return None

    def _check_progressive_degradation(self) -> None:
        """Check for progressive degradation over multiple laps."""
        recent = self.state_history[-3:]

        # Check brake CV trend
        brake_cvs = [s.brake_cv for s in recent]
        if all(brake_cvs[i] < brake_cvs[i+1] for i in range(len(brake_cvs)-1)):
            # Monotonically increasing (worsening)
            total_increase = brake_cvs[-1] - brake_cvs[0]
            pct_increase = 100 * total_increase / brake_cvs[0] if brake_cvs[0] > 0 else 0

            if pct_increase > 30:  # >30% increase over 3 laps
                # Add trend note to most recent alert
                for alert in reversed(self.pending_alerts):
                    if alert.metric == 'brake_cv' and alert.lap == recent[-1].lap:
                        alert.action = f"{alert.action}. Progressive degradation - consider pit."
                        break

    def generate_alerts(self) -> List[Alert]:
        """
        Get and clear pending alerts.

        Returns
        -------
        list of Alert
            Alerts generated since last call
        """
        alerts = self.pending_alerts.copy()
        self.pending_alerts = []
        return alerts

    def get_current_state(self) -> Optional[DriverState]:
        """Get most recent state."""
        if self.state_history:
            return self.state_history[-1]
        return None

    def get_trend(self, metric: str, n_laps: int = 5) -> List[float]:
        """
        Get trend for a metric over recent laps.

        Parameters
        ----------
        metric : str
            Metric name ('brake_cv' or 'coasting_pct')
        n_laps : int
            Number of recent laps to include

        Returns
        -------
        list of float
            Metric values for recent laps
        """
        recent = self.state_history[-n_laps:] if len(self.state_history) >= n_laps else self.state_history

        if metric == 'brake_cv':
            return [s.brake_cv for s in recent]
        elif metric == 'coasting_pct':
            return [s.coasting_pct for s in recent]
        else:
            return []

    def get_health_status(self) -> str:
        """
        Get overall health status for display.

        Returns
        -------
        str
            'good', 'warning', or 'critical'
        """
        if not self.state_history:
            return 'good'

        current = self.state_history[-1]
        max_sigma = max(abs(current.brake_cv_sigma), abs(current.coasting_sigma))

        if max_sigma >= self.critical_threshold:
            return 'critical'
        elif max_sigma >= self.warning_threshold:
            return 'warning'
        else:
            return 'good'


class FieldMonitor:
    """
    Monitors state for all drivers in the field.

    Convenience class for dashboard that manages StateMonitor instances
    for multiple drivers.
    """

    def __init__(self, profiles: List[DriverProfile]):
        """
        Initialize with driver profiles.

        Parameters
        ----------
        profiles : list of DriverProfile
            Profiles for all drivers
        """
        self.monitors: Dict[int, StateMonitor] = {}

        for profile in profiles:
            self.monitors[profile.vehicle_number] = StateMonitor(profile)

    def process_lap(
        self,
        telemetry: pd.DataFrame,
        lap: int
    ) -> Dict[int, DriverState]:
        """
        Process a lap for all drivers.

        Returns
        -------
        dict
            Map of vehicle_number to DriverState
        """
        states = {}

        for veh, monitor in self.monitors.items():
            try:
                state = monitor.process_lap(telemetry, lap)
                states[veh] = state
            except Exception:
                continue

        return states

    def generate_all_alerts(self) -> List[Alert]:
        """
        Get all pending alerts from all monitors.

        Returns
        -------
        list of Alert
            All alerts, sorted by severity (critical first)
        """
        all_alerts = []

        for monitor in self.monitors.values():
            alerts = monitor.generate_alerts()
            all_alerts.extend(alerts)

        # Sort by severity (critical first) then lap
        all_alerts.sort(
            key=lambda a: (-a.severity.value, -a.lap)
        )

        return all_alerts

    def get_field_status(self) -> Dict[int, str]:
        """
        Get health status for all drivers.

        Returns
        -------
        dict
            Map of vehicle_number to health status
        """
        return {
            veh: monitor.get_health_status()
            for veh, monitor in self.monitors.items()
        }
