"""
RaceCraft AI Dashboard - Real-time driver coaching for Toyota Gazoo Racing

Run with: uv run streamlit run dashboard.py
"""

import streamlit as st
import time
from pathlib import Path
import plotly.graph_objects as go
import plotly.express as px

from motorsport_modeling.data.telemetry_loader import load_telemetry
from motorsport_modeling.coaching.driver_profile import DriverProfile
from motorsport_modeling.coaching.state_monitor import StateMonitor, FieldMonitor


# Page config
st.set_page_config(
    page_title="RaceCraft AI",
    page_icon="🏎️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS - using Streamlit's default theme with colored alerts
st.markdown("""
<style>
    .alert-critical {
        background-color: #fee2e2;
        color: #991b1b;
        padding: 10px;
        border-radius: 5px;
        margin: 5px 0;
        border-left: 4px solid #ef4444;
    }
    .alert-warning {
        background-color: #fef3c7;
        color: #92400e;
        padding: 10px;
        border-radius: 5px;
        margin: 5px 0;
        border-left: 4px solid #f59e0b;
    }
    .alert-info {
        background-color: #dbeafe;
        color: #1e40af;
        padding: 10px;
        border-radius: 5px;
        margin: 5px 0;
        border-left: 4px solid #3b82f6;
    }
    .driver-selected {
        font-weight: bold;
        color: #2563eb;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_data
def load_race_data(track="indianapolis", race="race1"):
    """Load and cache race telemetry data."""
    data_dir = Path(__file__).parent / "data" / "raw" / "tracks" / track / race
    telemetry = load_telemetry(
        data_dir,
        laps=list(range(1, 21)),
        pivot_to_wide=True,
        verbose=False
    )
    return telemetry


@st.cache_data
def build_profiles(_telemetry, baseline_laps, max_drivers=10):
    """Build and cache driver profiles for top N drivers only."""
    # Get all drivers
    all_vehicles = sorted(_telemetry['vehicle_number'].dropna().unique())

    # Limit to first N for performance
    vehicles_to_process = all_vehicles[:max_drivers]

    profiles = []
    for veh in vehicles_to_process:
        try:
            profile = DriverProfile.from_telemetry(_telemetry, int(veh), baseline_laps)
            if profile.laps_used > 0:
                profiles.append(profile)
        except Exception:
            continue

    return profiles


def get_health_color(status):
    """Get color for health status."""
    colors = {
        'good': '#22c55e',  # Green
        'warning': '#f59e0b',  # Amber
        'critical': '#dc2626'  # Red
    }
    return colors.get(status, '#6b7280')


def create_profile_chart(profile, field_profiles):
    """Create radar chart for profile comparison."""
    comparison = profile.compare_to_field(field_profiles)

    if not comparison:
        return None

    categories = []
    values = []
    hover_text = []

    if 'lift_off_count' in comparison:
        categories.append('Traction')
        values.append(comparison['lift_off_count']['percentile'])
        hover_text.append(f"Lift-offs: {comparison['lift_off_count']['vs_field']}")

    if 'mean_combined_g' in comparison:
        categories.append('Grip')
        values.append(comparison['mean_combined_g']['percentile'])
        hover_text.append(f"G-Force: {comparison['mean_combined_g']['vs_field']}")

    if 'full_throttle_pct' in comparison:
        categories.append('Commitment')
        values.append(comparison['full_throttle_pct']['percentile'])
        hover_text.append(f"Full throttle: {comparison['full_throttle_pct']['vs_field']}")

    if not categories:
        return None

    # Close the radar chart
    categories.append(categories[0])
    values.append(values[0])

    fig = go.Figure()

    fig.add_trace(go.Scatterpolar(
        r=values,
        theta=categories,
        fill='toself',
        fillcolor='rgba(59, 130, 246, 0.3)',
        line=dict(color='#3b82f6', width=2),
        name='Driver'
    ))

    # Add field average (50th percentile)
    avg_values = [50] * len(categories)
    fig.add_trace(go.Scatterpolar(
        r=avg_values,
        theta=categories,
        line=dict(color='#6b7280', width=1, dash='dot'),
        name='Field Avg'
    ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100]
            )
        ),
        showlegend=True,
        margin=dict(l=60, r=60, t=30, b=30),
        height=250
    )

    return fig


def create_trend_chart(values, metric_name, baseline_mean, baseline_std):
    """Create sparkline trend chart."""
    fig = go.Figure()

    # Add trend line
    fig.add_trace(go.Scatter(
        y=values,
        mode='lines+markers',
        line=dict(color='#3b82f6', width=2),
        marker=dict(size=6),
        name=metric_name
    ))

    # Add baseline
    fig.add_hline(
        y=baseline_mean,
        line_dash="dash",
        line_color="#6b7280",
        annotation_text="baseline"
    )

    # Add warning zone
    fig.add_hrect(
        y0=baseline_mean + 2*baseline_std,
        y1=baseline_mean + 4*baseline_std,
        fillcolor="rgba(251, 191, 36, 0.2)",
        line_width=0
    )

    fig.update_layout(
        showlegend=False,
        margin=dict(l=40, r=20, t=10, b=30),
        height=120,
        xaxis=dict(
            showgrid=False,
            title="Lap"
        ),
        yaxis=dict(
            showgrid=True
        )
    )

    return fig


def main():
    # Title
    st.title("🏎️ RaceCraft AI")
    st.markdown("**Real-time Driver Coaching Dashboard**")

    # Sidebar - Race Selection
    with st.sidebar:
        st.header("Race Selection")
        track = st.selectbox("Track", ["indianapolis"])
        race = st.selectbox("Race", ["race1"])

        st.markdown("---")
        st.header("Simulation Controls")

        # Load data
        with st.spinner("Loading telemetry..."):
            telemetry = load_race_data(track, race)

        # Build profiles
        baseline_laps = [1, 2, 3, 4, 5]
        with st.spinner("Building profiles..."):
            field_profiles = build_profiles(telemetry, baseline_laps)

        # Driver selection
        driver_options = {f"#{p.vehicle_number}": p.vehicle_number for p in field_profiles}
        selected_driver_label = st.selectbox(
            "Focus Driver",
            list(driver_options.keys())
        )
        selected_driver = driver_options[selected_driver_label]

        # Simulation speed
        sim_speed = st.slider("Simulation Speed", 0.5, 3.0, 1.0, 0.5)

        # Control buttons
        col1, col2 = st.columns(2)
        start_sim = col1.button("▶️ Start", use_container_width=True)
        reset_sim = col2.button("🔄 Reset", use_container_width=True)

        st.markdown("---")
        st.caption("Toyota Gazoo Racing - Hackathon 2024")

    # Get selected profile
    selected_profile = next(
        (p for p in field_profiles if p.vehicle_number == selected_driver),
        field_profiles[0]
    )

    # Initialize session state
    if 'current_lap' not in st.session_state or reset_sim:
        st.session_state.current_lap = 5
        st.session_state.alerts = []
        st.session_state.monitor = StateMonitor(selected_profile)
        st.session_state.running = False

    if start_sim:
        st.session_state.running = True

    # Main layout - 3 columns
    col_field, col_alerts, col_detail = st.columns([1, 1.5, 2])

    # Field Overview
    with col_field:
        st.subheader("Field Overview")

        # Initialize monitors for all drivers
        field_monitor = FieldMonitor(field_profiles)

        # Process up to current lap
        for lap in range(6, st.session_state.current_lap + 1):
            field_monitor.process_lap(telemetry, lap)

        # Display field status
        statuses = field_monitor.get_field_status()

        for profile in sorted(field_profiles, key=lambda p: p.vehicle_number):
            veh = profile.vehicle_number
            status = statuses.get(veh, 'good')
            color = get_health_color(status)

            # Highlight selected driver
            if veh == selected_driver:
                st.markdown(
                    f"**→ #{veh}** "
                    f"<span style='color:{color}'>●</span>",
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    f"#{veh} "
                    f"<span style='color:{color}'>●</span>",
                    unsafe_allow_html=True
                )

    # Alert Feed
    with col_alerts:
        st.subheader("Alert Feed")
        st.caption(f"Lap {st.session_state.current_lap}")

        # Get alerts from field monitor
        all_alerts = field_monitor.generate_all_alerts()
        all_alerts.extend(st.session_state.alerts)

        # Sort and display recent alerts
        for alert in all_alerts[:5]:
            severity_class = {
                1: "alert-info",
                2: "alert-warning",
                3: "alert-critical"
            }.get(alert.severity.value, "alert-info")

            st.markdown(
                f"""<div class='{severity_class}'>
                <strong>{alert.severity_icon} Lap {alert.lap} | #{alert.vehicle_number}</strong><br/>
                {alert.metric_display}<br/>
                → {alert.action}
                </div>""",
                unsafe_allow_html=True
            )

        if not all_alerts:
            st.info("No alerts yet")

    # Driver Detail
    with col_detail:
        st.subheader(f"Driver Detail: #{selected_driver}")

        # Two columns for Profile and State
        detail_col1, detail_col2 = st.columns(2)

        with detail_col1:
            st.markdown("**Profile vs Field**")

            # Radar chart
            radar_fig = create_profile_chart(selected_profile, field_profiles)
            if radar_fig:
                st.plotly_chart(radar_fig, use_container_width=True)

            # Training recommendations
            recs = selected_profile.get_training_recommendations(field_profiles)
            if recs:
                st.markdown("**Training Focus:**")
                for rec in recs[:2]:
                    st.markdown(f"- {rec['focus']}: {rec['exercise'][:50]}...")

        with detail_col2:
            st.markdown("**State vs Baseline**")

            # Get current state
            monitor = st.session_state.monitor
            current_state = monitor.get_current_state()

            if current_state:
                baselines = selected_profile.state_baselines

                # Brake CV
                brake_cv = current_state.brake_cv
                brake_baseline = baselines['brake_cv']['mean']
                brake_delta = 100 * (brake_cv - brake_baseline) / brake_baseline if brake_baseline > 0 else 0

                st.metric(
                    "Brake Consistency",
                    f"{brake_cv:.1f}%",
                    f"{brake_delta:+.0f}% vs baseline",
                    delta_color="inverse"
                )

                # Trend chart
                brake_trend = monitor.get_trend('brake_cv', 5)
                if brake_trend:
                    trend_fig = create_trend_chart(
                        brake_trend,
                        "Brake CV",
                        baselines['brake_cv']['mean'],
                        baselines['brake_cv']['std']
                    )
                    st.plotly_chart(trend_fig, use_container_width=True)

                # Coasting
                coasting = current_state.coasting_pct
                coast_baseline = baselines['coasting_pct']['mean']
                coast_delta = 100 * (coasting - coast_baseline) / coast_baseline if coast_baseline > 0 else 0

                st.metric(
                    "Coasting",
                    f"{coasting:.1f}%",
                    f"{coast_delta:+.0f}% vs baseline",
                    delta_color="inverse"
                )

            else:
                st.info("Process laps to see state data")

    # Simulation logic
    if st.session_state.running and st.session_state.current_lap < 20:
        time.sleep(2.0 / sim_speed)

        # Advance lap
        st.session_state.current_lap += 1
        lap = st.session_state.current_lap

        # Process lap for selected driver
        state = st.session_state.monitor.process_lap(telemetry, lap)
        alerts = st.session_state.monitor.generate_alerts()
        st.session_state.alerts.extend(alerts)

        # Rerun to update display
        st.rerun()

    elif st.session_state.current_lap >= 20:
        st.session_state.running = False
        st.success("Simulation complete!")


if __name__ == "__main__":
    main()
