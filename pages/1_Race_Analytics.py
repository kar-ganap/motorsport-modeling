"""
RaceCraft AI Dashboard - Real-time driver coaching for Toyota Gazoo Racing

Redesigned from first principles with clear visual hierarchy:
1. NOW - Current state (glanceable)
2. NEXT - Predictions (what's coming)
3. CONTEXT - Race dynamics (gaps, position, sectors combined)
4. DIAGNOSTICS - Technique issues (conditional)
5. RADIO - Coaching message (actionable)

Run with: uv run streamlit run Dashboard.py
"""

import streamlit as st
import time
from pathlib import Path
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd

from motorsport_modeling.data.telemetry_loader import load_telemetry
from motorsport_modeling.coaching.driver_profile import DriverProfile
from motorsport_modeling.coaching.state_monitor import StateMonitor, FieldMonitor
from motorsport_modeling.models.feature_engineering import prepare_race_features
from motorsport_modeling.models.lap_time_predictor import (
    RelativePerformancePredictor,
    StrategicPerformancePredictor
)


# Page config
st.set_page_config(
    page_title="RaceCraft AI",
    page_icon="🏎️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Enhanced CSS for professional racing dashboard
st.markdown("""
<style>
    /* Hide default streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display:none;}

    /* Custom card styling */
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }

    /* Traffic light colors */
    .metric-card-green {
        background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }

    .metric-card-yellow {
        background: linear-gradient(135deg, #facc15 0%, #f59e0b 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }

    .metric-card-red {
        background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }

    .status-header {
        background: linear-gradient(90deg, #1e3c72 0%, #2a5298 100%);
        padding: 15px 30px;
        border-radius: 8px;
        color: white !important;
        margin-bottom: 20px;
    }

    .status-header h1, .status-header span, .status-header * {
        color: white !important;
    }

    /* Override Streamlit's default text color */
    div[data-testid="stMarkdownContainer"] .status-header h1,
    div[data-testid="stMarkdownContainer"] .status-header span {
        color: white !important;
    }

    .radio-message {
        background: #1a1a1a;
        border-left: 5px solid #ff6b35;
        padding: 20px 25px;
        border-radius: 8px;
        color: white;
        font-size: 18px;
        font-weight: 500;
        margin: 15px 0;
    }

    .section-divider {
        height: 2px;
        background: linear-gradient(90deg, transparent, #667eea, transparent);
        margin: 25px 0;
    }

    /* Compact chart titles */
    .js-plotly-plot .plotly .gtitle {
        font-size: 14px !important;
    }

    /* Reduce chart margins */
    .js-plotly-plot {
        margin-top: -10px;
    }

    /* Add subtle borders to plot containers */
    .stPlotlyChart {
        border: 1px solid #e5e7eb;
        border-radius: 4px;
        padding: 5px;
    }

    /* Field forecast title styling - match race context titles */
    .forecast-title {
        font-size: 14px;
        color: #0f172a;
        margin: 10px 0 8px 0;
        font-weight: 600;
        font-family: Inter, system-ui, sans-serif;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_data
def load_race_data(track="indianapolis", race="race1"):
    """Load and cache race telemetry data."""
    # Navigate to project root (pages/../ = project root)
    data_dir = Path(__file__).parent.parent / "data" / "raw" / "tracks" / track / race
    telemetry = load_telemetry(
        data_dir,
        laps=list(range(1, 21)),
        pivot_to_wide=True,
        verbose=False
    )
    return telemetry


@st.cache_data
def load_race_features(track="indianapolis", race="race1", total_laps=26):
    """Load precomputed race features with sectors for fast dashboard loading."""
    # Try to load precomputed analytics file (fast, with sectors)
    processed_dir = Path(__file__).parent.parent / "data" / "processed" / track
    analytics_file = processed_dir / f"{race}_analytics.parquet"

    if analytics_file.exists():
        # Load precomputed analytics (sectors already included)
        race_data = pd.read_parquet(analytics_file)
        return race_data

    # Fall back to on-the-fly computation if precomputed file doesn't exist
    base_dir = Path(__file__).parent.parent / "data" / "raw" / "tracks" / track / race
    # Map race to file paths
    lap_time_file = base_dir / f"R1_{track}_motor_speedway_lap_time.csv"
    if race == "race2":
        lap_time_file = base_dir / f"R2_{track}_motor_speedway_lap_time.csv"

    # Try alternative naming
    if not lap_time_file.exists():
        lap_time_file = base_dir / f"{track}_lap_time_R1.csv"
        if race == "race2":
            lap_time_file = base_dir / f"{track}_lap_time_R2.csv"

    # Indianapolis specific naming
    if track == "indianapolis":
        lap_time_file = base_dir / f"R{race[-1]}_indianapolis_motor_speedway_lap_time.csv"

    if not lap_time_file.exists():
        return None

    race_data = prepare_race_features(
        lap_time_file=lap_time_file,
        total_laps=total_laps,
        endurance_file=endurance_file if endurance_file.exists() else None,
        verbose=False
    )

    # Load sector times from endurance file and merge
    if endurance_file.exists():
        try:
            endurance_df = pd.read_csv(endurance_file, sep=';')
            # Strip whitespace from column names
            endurance_df.columns = endurance_df.columns.str.strip()
            # Select relevant columns
            sector_cols = ['NUMBER', 'LAP_NUMBER', 'S1_SECONDS', 'S2_SECONDS', 'S3_SECONDS']
            if all(col in endurance_df.columns for col in sector_cols):
                sector_data = endurance_df[sector_cols].copy()
                sector_data.columns = ['vehicle_number', 'lap', 's1', 's2', 's3']
                # Convert to numeric
                for col in ['s1', 's2', 's3']:
                    sector_data[col] = pd.to_numeric(sector_data[col], errors='coerce')
                # Deduplicate sector data before merging (take first occurrence)
                sector_data = sector_data.drop_duplicates(subset=['vehicle_number', 'lap'], keep='first')
                # Merge with race_data
                race_data = race_data.merge(
                    sector_data,
                    on=['vehicle_number', 'lap'],
                    how='left'
                )
        except Exception:
            pass  # Sector data not available

    return race_data


@st.cache_resource
def fit_predictor(_race_data, predictor_type="relative"):
    """Fit and cache predictor on race data."""
    if _race_data is None:
        return None

    if predictor_type == "strategic":
        predictor = StrategicPerformancePredictor(alpha=0.3)
    else:
        predictor = RelativePerformancePredictor(alpha=0.3)

    predictor.fit(_race_data, verbose=False)
    return predictor


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


def create_gap_analysis_plot(race_data, selected_driver, current_lap, height=285):
    """Gap Analysis plot with individual legend."""
    fig = go.Figure()

    driver_data = race_data[
        (race_data['vehicle_number'] == selected_driver) &
        (race_data['lap'] <= current_lap)
    ].sort_values('lap')

    if len(driver_data) > 0 and 'gap_to_ahead' in driver_data.columns:
        # Gap to ahead - red line
        fig.add_trace(
            go.Scatter(
                x=driver_data['lap'],
                y=driver_data['gap_to_ahead'],
                mode='lines',
                name='Ahead',
                line=dict(color='#dc2626', width=3),
                fill='tozeroy',
                fillcolor='rgba(220, 38, 38, 0.15)',
                hovertemplate='<b>Lap %{x}</b><br>Gap to ahead: %{y:.2f}s<extra></extra>'
            )
        )

        if 'gap_to_behind' in driver_data.columns:
            # Gap to behind - green line (inverted)
            fig.add_trace(
                go.Scatter(
                    x=driver_data['lap'],
                    y=-driver_data['gap_to_behind'],
                    mode='lines',
                    name='Behind',
                    line=dict(color='#16a34a', width=3),
                    fill='tozeroy',
                    fillcolor='rgba(22, 163, 74, 0.15)',
                    hovertemplate='<b>Lap %{x}</b><br>Gap to behind: %{y:.2f}s<extra></extra>'
                )
            )

        # Battle zone markers (±1 second indicates close racing / fighting zone)
        fig.add_hline(
            y=1, line_dash="dash", line_color="rgba(251, 146, 60, 0.6)",
            line_width=2,
            annotation_text="±1s battle zone",
            annotation_position="right",
            annotation=dict(font=dict(size=9, color='rgba(251, 146, 60, 0.8)'))
        )
        fig.add_hline(
            y=-1, line_dash="dash", line_color="rgba(251, 146, 60, 0.6)",
            line_width=2
        )

    # Brief annotation - inside plot at bottom
    fig.add_annotation(
        text="Red: catching ahead | Green: pulling away | Dashed: ±1s battle zone",
        xref="paper", yref="paper",
        x=0.5, y=0.05,
        showarrow=False,
        font=dict(size=11, color='#475569', family="Inter", weight=600),
        xanchor='center',
        yanchor='bottom',
        bgcolor='rgba(255,255,255,0.85)',
        borderpad=4
    )

    fig.update_layout(
        height=height,
        margin=dict(l=60, r=20, t=50, b=40),
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
            bgcolor='rgba(255,255,255,0.9)',
            bordercolor='rgba(100, 116, 139, 0.3)',
            borderwidth=1,
            font=dict(size=10, color='#1f2937')
        ),
        xaxis=dict(
            title=dict(text="Lap", font=dict(size=11, color='#475569')),
            showgrid=True,
            gridcolor='rgba(100, 116, 139, 0.15)',
            gridwidth=1,
            zeroline=False,
            showline=True,
            linewidth=1,
            linecolor='rgba(100, 116, 139, 0.3)',
            ticks="outside",
            tickfont=dict(size=10, color='#475569')
        ),
        yaxis=dict(
            title=dict(text="Gap (s)", font=dict(size=11, color='#475569')),
            showgrid=True,
            gridcolor='rgba(100, 116, 139, 0.15)',
            gridwidth=1,
            zeroline=True,
            zerolinecolor='rgba(100, 116, 139, 0.4)',
            zerolinewidth=2,
            showline=True,
            linewidth=1,
            linecolor='rgba(100, 116, 139, 0.3)',
            tickfont=dict(size=10, color='#475569')
        ),
        hovermode='closest',
        plot_bgcolor='#f8fafc',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(family="Inter, system-ui, sans-serif", size=11, color='#1f2937')
    )

    return fig


def create_sector_performance_plot(race_data, selected_driver, current_lap, height=285):
    """Sector Performance plot (no legend needed)."""
    fig = go.Figure()

    if 's1' in race_data.columns:
        lap_data = race_data[race_data['lap'] == current_lap]
        driver_lap = lap_data[lap_data['vehicle_number'] == selected_driver]

        if len(driver_lap) > 0 and len(lap_data) > 0:
            s1_median = lap_data['s1'].median()
            s2_median = lap_data['s2'].median()
            s3_median = lap_data['s3'].median()

            deltas = [
                driver_lap['s1'].iloc[0] - s1_median,
                driver_lap['s2'].iloc[0] - s2_median,
                driver_lap['s3'].iloc[0] - s3_median
            ]

            colors = ['#10b981' if d < 0 else '#f43f5e' for d in deltas]

            fig.add_trace(
                go.Bar(
                    x=['Sector 1', 'Sector 2', 'Sector 3'],
                    y=deltas,
                    marker=dict(
                        color=colors,
                        line=dict(color='rgba(31, 41, 55, 0.3)', width=1.5),
                        opacity=0.85
                    ),
                    text=[f"{d:+.3f}s" for d in deltas],
                    textposition='outside',
                    textfont=dict(size=11, color='#1f2937', weight='bold'),
                    cliponaxis=False,
                    showlegend=False,
                    width=0.6,
                    hovertemplate='<b>%{x}</b><br>Delta: %{y:.3f}s<extra></extra>'
                )
            )

            # Zero line
            fig.add_hline(
                y=0, line_color="rgba(100, 116, 139, 0.5)",
                line_width=2
            )

    fig.update_layout(
        height=height,
        margin=dict(l=60, r=20, t=50, b=40),
        showlegend=False,
        xaxis=dict(
            title=dict(text="", font=dict(size=11, color='#475569')),
            showgrid=False,
            showline=True,
            linewidth=1,
            linecolor='rgba(100, 116, 139, 0.3)',
            ticks="outside",
            tickfont=dict(size=10, color='#475569')
        ),
        yaxis=dict(
            title=dict(text="Delta (s)", font=dict(size=11, color='#475569')),
            showgrid=True,
            gridcolor='rgba(100, 116, 139, 0.15)',
            gridwidth=1,
            zeroline=False,
            showline=True,
            linewidth=1,
            linecolor='rgba(100, 116, 139, 0.3)',
            tickfont=dict(size=10, color='#475569')
        ),
        hovermode='closest',
        plot_bgcolor='#f8fafc',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(family="Inter, system-ui, sans-serif", size=11, color='#1f2937')
    )

    return fig


def create_position_progression_plot(race_data, selected_driver, current_lap, height=315):
    """Position Progression plot (no legend for driver lines, only battle markers if needed)."""
    fig = go.Figure()

    lap_data_all = race_data[race_data['lap'] <= current_lap].copy()
    all_drivers = lap_data_all['vehicle_number'].unique()

    for veh in all_drivers:
        veh_data = lap_data_all[lap_data_all['vehicle_number'] == veh].sort_values('lap')

        if veh == selected_driver:
            # Featured driver - bold line
            fig.add_trace(
                go.Scatter(
                    x=veh_data['lap'],
                    y=veh_data['position'],
                    mode='lines+markers',
                    name=f'#{int(veh)}',
                    line=dict(color='#2563eb', width=4),
                    marker=dict(size=8, color='#2563eb', line=dict(color='white', width=2)),
                    showlegend=False,
                    hovertemplate='<b>Lap %{x}</b><br>Position: P%{y}<extra></extra>'
                )
            )
        else:
            # Other drivers - subtle background
            fig.add_trace(
                go.Scatter(
                    x=veh_data['lap'],
                    y=veh_data['position'],
                    mode='lines',
                    name=f'#{int(veh)}',
                    line=dict(color='rgba(148, 163, 184, 0.25)', width=1.5),
                    showlegend=False,
                    hoverinfo='skip'
                )
            )

    # Battle markers
    if 'is_fighting' in lap_data_all.columns:
        driver_fights = lap_data_all[
            (lap_data_all['vehicle_number'] == selected_driver) &
            (lap_data_all['is_fighting'] == True)
        ]
        if len(driver_fights) > 0:
            fig.add_trace(
                go.Scatter(
                    x=driver_fights['lap'],
                    y=driver_fights['position'],
                    mode='markers',
                    name='Battle',
                    marker=dict(
                        size=16,
                        color='#f59e0b',
                        symbol='star',
                        line=dict(color='white', width=2)
                    ),
                    hovertemplate='<b>Lap %{x}</b><br>Battle engaged!<extra></extra>'
                )
            )

    fig.update_layout(
        height=height,
        margin=dict(l=60, r=20, t=50, b=40),
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
            bgcolor='rgba(255,255,255,0.9)',
            bordercolor='rgba(100, 116, 139, 0.3)',
            borderwidth=1,
            font=dict(size=10, color='#1f2937')
        ),
        xaxis=dict(
            title=dict(text="Lap", font=dict(size=11, color='#475569')),
            showgrid=True,
            gridcolor='rgba(100, 116, 139, 0.15)',
            gridwidth=1,
            showline=True,
            linewidth=1,
            linecolor='rgba(100, 116, 139, 0.3)',
            ticks="outside",
            tickfont=dict(size=10, color='#475569'),
            dtick=1  # Integer laps only
        ),
        yaxis=dict(
            title=dict(text="Position", font=dict(size=11, color='#475569')),
            autorange="reversed",
            showgrid=True,
            gridcolor='rgba(100, 116, 139, 0.15)',
            gridwidth=1,
            showline=True,
            linewidth=1,
            linecolor='rgba(100, 116, 139, 0.3)',
            tickfont=dict(size=10, color='#475569'),
            dtick=2
        ),
        hovermode='closest',
        plot_bgcolor='#f8fafc',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(family="Inter, system-ui, sans-serif", size=11, color='#1f2937')
    )

    return fig


def create_compact_prediction_chart(predictions_df, selected_driver, current_positions):
    """Compact horizontal bar chart showing 5 drivers with relative position labels."""
    if predictions_df is None or len(predictions_df) == 0:
        return None

    # Get focused driver's current position
    focused_pos = current_positions.get(selected_driver, None)
    if focused_pos is None:
        # Fallback: show top 5 fastest
        predictions_df = predictions_df.sort_values('predicted_relative').head(5)
        # Create basic labels since we don't have position context
        y_labels = [f"#{int(v)}" for v in predictions_df['vehicle_number']]
        colors = ['#3b82f6' if v == selected_driver else '#64748b' for v in predictions_df['vehicle_number']]
    else:
        # Build position-based data
        position_data = {}
        for rel_pos_offset in [-3, -2, -1, 0, +1, +2, +3]:
            target_pos = focused_pos + rel_pos_offset

            # For position 0 (YOU), always use selected driver
            if rel_pos_offset == 0:
                selected_row = predictions_df[predictions_df['vehicle_number'] == selected_driver]
                if len(selected_row) > 0:
                    position_data[0] = {
                        'vehicle_number': selected_driver,
                        'predicted_relative': selected_row['predicted_relative'].iloc[0],
                        'relative_position': 0
                    }
            else:
                # Find driver(s) at this position (excluding selected driver)
                for _, row in predictions_df.iterrows():
                    veh = row['vehicle_number']
                    if veh == selected_driver:
                        continue  # Skip selected driver for other positions

                    curr_pos = current_positions.get(veh, 999)

                    if curr_pos == target_pos and rel_pos_offset not in position_data:
                        position_data[rel_pos_offset] = {
                            'vehicle_number': veh,
                            'predicted_relative': row['predicted_relative'],
                            'relative_position': rel_pos_offset
                        }
                        break

        if len(position_data) == 0:
            # Fallback if no drivers in vicinity
            predictions_df = predictions_df.sort_values('predicted_relative').head(5)
            y_labels = [f"#{int(v)}" for v in predictions_df['vehicle_number']]
            colors = ['#667eea'] * len(y_labels)  # Use purple for all bars
        else:
            # Ensure position 0 (YOU) always exists
            if 0 not in position_data:
                # Force add selected driver at position 0 if missing
                selected_row = predictions_df[predictions_df['vehicle_number'] == selected_driver]
                if len(selected_row) > 0:
                    position_data[0] = {
                        'vehicle_number': selected_driver,
                        'predicted_relative': selected_row['predicted_relative'].iloc[0],
                        'relative_position': 0
                    }

            # Build chart data from position_data (sorted by position)
            # Important: Must include ALL 7 positions (-3, -2, -1, 0, +1, +2, +3)
            y_labels = []
            x_values = []
            vehicle_numbers = []

            # Get YOU's predicted time to use as baseline
            you_baseline = position_data[0]['predicted_relative'] if 0 in position_data else 0

            # Force include all 7 positions in order
            for rel_pos in [-3, -2, -1, 0, 1, 2, 3]:
                if rel_pos in position_data:
                    data = position_data[rel_pos]
                    pred_time = data['predicted_relative']
                    veh = data['vehicle_number']

                    # Make relative to YOU instead of field median
                    relative_to_you = pred_time - you_baseline
                else:
                    # Position doesn't exist, use placeholder
                    relative_to_you = None
                    veh = None

                # Y-axis label
                if rel_pos == 0:
                    y_labels.append('YOU')
                elif rel_pos < 0:
                    y_labels.append(f'{int(rel_pos)}')
                else:
                    y_labels.append(f'+{int(rel_pos)}')

                x_values.append(relative_to_you if relative_to_you is not None else 0)
                vehicle_numbers.append(veh if veh is not None else 0)

            # Single color for all bars
            colors = ['#667eea'] * len(y_labels)

            # Convert to DataFrame for consistent handling
            predictions_df = pd.DataFrame({
                'predicted_relative': x_values,
                'vehicle_number': vehicle_numbers
            })

    # Create figure - use numeric y-axis with custom labels
    fig = go.Figure()

    # Use numeric indices 0,1,2,3,4 for y-axis to ensure proper ordering
    y_numeric = list(range(len(y_labels)))

    fig.add_trace(go.Bar(
        y=y_numeric,
        x=predictions_df['predicted_relative'].values,
        orientation='h',
        marker=dict(
            color=colors,
            line=dict(color='#1f2937', width=2)
        ),
        width=0.95,
        text=[f"{v:+.1f}s" for v in predictions_df['predicted_relative'].values],
        textposition='outside',
        textfont=dict(size=12, color='#111827', weight='bold'),
        cliponaxis=False,
        showlegend=False,
        hovertemplate='%{text}<extra></extra>',
        customdata=predictions_df['vehicle_number'].values,
        hovertext=[f"{y_labels[i]}: Car #{int(v)}" for i, v in enumerate(predictions_df['vehicle_number'].values)]
    ))

    fig.add_vline(x=0, line_dash="dash", line_color="#6b7280", line_width=2)

    fig.update_layout(
        height=440,  # Card (~160px) + this chart = Race Context height (600px)
        margin=dict(l=70, r=120, t=20, b=40),  # Increased margins to prevent text clipping
        xaxis=dict(
            title=dict(text="Predicted Lap Time vs YOU (s)", font=dict(size=11, color='#475569')),
            showgrid=True,
            gridcolor='rgba(100, 116, 139, 0.15)',
            gridwidth=1,
            showline=True,
            linewidth=1,
            linecolor='rgba(100, 116, 139, 0.3)',
            ticks="outside",
            tickfont=dict(size=10, color='#475569')
        ),
        yaxis=dict(
            title=dict(text="Relative Position", font=dict(size=11, color='#475569')),
            tickmode='array',
            tickvals=y_numeric,
            ticktext=y_labels,
            showgrid=True,
            gridcolor='rgba(100, 116, 139, 0.15)',
            gridwidth=1,
            showline=True,
            linewidth=1,
            linecolor='rgba(100, 116, 139, 0.3)',
            tickfont=dict(size=10, color='#475569')
        ),
        plot_bgcolor='#f8fafc',  # Match race context background
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(family="Inter, system-ui, sans-serif", size=11, color='#1f2937')
    )

    return fig


def generate_coaching_message(pred_row, driver_lap_data, current_positions):
    """Generate actionable coaching radio message."""
    messages = []

    # Position context
    curr_pos = current_positions.get(pred_row['vehicle_number'], '?')
    messages.append(f"P{curr_pos}")

    # Pace assessment
    predicted_rel = pred_row['predicted_relative']
    if predicted_rel < -0.5:
        messages.append("Strong pace - push to gain positions")
    elif predicted_rel < 0:
        messages.append("Slightly faster - maintain pressure")
    elif predicted_rel < 0.5:
        messages.append("On pace - defend position")
    else:
        messages.append("Losing pace - focus on consistency")

    # Sector-specific advice
    if driver_lap_data is not None and len(driver_lap_data) > 0 and 's1' in driver_lap_data.columns:
        # Find weakest sector
        lap_data = driver_lap_data[driver_lap_data['lap'] == driver_lap_data['lap'].max()]
        if len(lap_data) > 0:
            field_medians = {
                's1': lap_data['s1'].median(),
                's2': lap_data['s2'].median(),
                's3': lap_data['s3'].median()
            }

            driver_row = lap_data[lap_data['vehicle_number'] == pred_row['vehicle_number']]
            if len(driver_row) > 0:
                deltas = {
                    'S1': driver_row['s1'].iloc[0] - field_medians['s1'],
                    'S2': driver_row['s2'].iloc[0] - field_medians['s2'],
                    'S3': driver_row['s3'].iloc[0] - field_medians['s3']
                }

                worst_sector = max(deltas, key=deltas.get)
                if deltas[worst_sector] > 0.2:
                    messages.append(f"Focus {worst_sector} (losing {deltas[worst_sector]:.1f}s)")

    return " | ".join(messages)


def main():
    # Compact header with aggressive white text styling
    st.markdown("""
    <div class='status-header' style='display:flex; justify-content:space-between; align-items:center;'>
        <h1 style='margin:0; color:#FFFFFF !important; text-shadow: 0 0 2px rgba(0,0,0,0.5);'>RaceCraft AI</h1>
        <span style='font-size:32px; color:#FFFFFF !important; text-shadow: 0 0 2px rgba(0,0,0,0.5); font-weight:600;'>Toyota Gazoo Racing</span>
    </div>
    """, unsafe_allow_html=True)

    # Sidebar for configuration only
    with st.sidebar:
        st.header("Configuration")

        # Track display names matching Model Validation page
        track_display_names = {
            'barber': 'Barber Motorsports Park',
            'cota': 'Circuit of the Americas',
            'indianapolis': 'Indianapolis Motor Speedway',
            'road-america': 'Road America',
            'sebring': 'Sebring International Raceway',
            'sonoma': 'Sonoma Raceway',
            'vir': 'Virginia International Raceway'
        }

        tracks = ["barber", "cota", "indianapolis", "road-america", "sebring", "sonoma", "vir"]
        track = st.selectbox(
            "Track",
            options=tracks,
            format_func=lambda x: track_display_names.get(x, x),
            index=tracks.index('indianapolis')
        )
        race = st.selectbox("Race", ["race1", "race2"])

        # Load data
        with st.spinner("Loading..."):
            telemetry = load_race_data(track, race)
            race_data = load_race_features(track, race)

            # Check if data loaded successfully
            if race_data is None or telemetry is None:
                st.error(f"⚠️ Could not load data for {track_display_names.get(track, track)} - {race}")
                st.info("This track/race combination may not have processed features yet. Please select a different track or race.")
                st.stop()

            predictor = fit_predictor(race_data, "strategic")
            baseline_laps = [1, 2, 3, 4, 5]
            field_profiles = build_profiles(telemetry, baseline_laps)

        # Driver selection
        driver_options = {f"#{p.vehicle_number}": p.vehicle_number for p in field_profiles}
        selected_driver_label = st.selectbox("Driver", list(driver_options.keys()))
        selected_driver = driver_options[selected_driver_label]

        st.markdown("---")
        sim_speed = st.slider("Sim Speed", 0.5, 3.0, 1.0, 0.5)

        col1, col2 = st.columns(2)
        start_sim = col1.button("▶ Start", use_container_width=True)
        reset_sim = col2.button("↻ Reset", use_container_width=True)

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

    field_monitor = FieldMonitor(field_profiles)
    for lap in range(6, st.session_state.current_lap + 1):
        field_monitor.process_lap(telemetry, lap)

    # ================================================================
    # SECTION 1: NOW - Current State
    # ================================================================
    st.markdown(f"<h2 style='color:#667eea; margin-top:10px;'>Lap {st.session_state.current_lap}/20 | Driver #{selected_driver}</h2>",
                unsafe_allow_html=True)

    if race_data is not None:
        lap_data = race_data[race_data['lap'] == st.session_state.current_lap]
        driver_lap = lap_data[lap_data['vehicle_number'] == selected_driver]

        if len(driver_lap) > 0:
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                pos = driver_lap['position'].iloc[0]
                st.markdown(f"""
                <div class='metric-card'>
                    <div style='font-size:16px; opacity:0.9;'>POSITION</div>
                    <div style='font-size:56px; font-weight:bold; margin:5px 0;'>P{int(pos)}</div>
                </div>
                """, unsafe_allow_html=True)

            with col2:
                gap_ahead = driver_lap['gap_to_ahead'].iloc[0] if 'gap_to_ahead' in driver_lap.columns else 0
                # Green if closing gap (< 1.0s), Yellow if mid (1.0-3.0s), Red if large (> 3.0s)
                if gap_ahead < 1.0:
                    color_class = 'green'
                elif gap_ahead < 3.0:
                    color_class = 'yellow'
                else:
                    color_class = 'red'
                st.markdown(f"""
                <div class='metric-card-{color_class}'>
                    <div style='font-size:16px; opacity:0.9;'>GAP AHEAD</div>
                    <div style='font-size:56px; font-weight:bold; margin:5px 0;'>{gap_ahead:+.1f}s</div>
                </div>
                """, unsafe_allow_html=True)

            with col3:
                gap_behind = driver_lap['gap_to_behind'].iloc[0] if 'gap_to_behind' in driver_lap.columns else 0
                # Green if pulling away (> 3.0s), Yellow if mid (1.0-3.0s), Red if close (< 1.0s)
                if gap_behind > 3.0:
                    color_class = 'green'
                elif gap_behind > 1.0:
                    color_class = 'yellow'
                else:
                    color_class = 'red'
                st.markdown(f"""
                <div class='metric-card-{color_class}'>
                    <div style='font-size:16px; opacity:0.9;'>GAP BEHIND</div>
                    <div style='font-size:56px; font-weight:bold; margin:5px 0;'>{gap_behind:+.1f}s</div>
                </div>
                """, unsafe_allow_html=True)

            with col4:
                lap_time = driver_lap['lap_time'].iloc[0] if 'lap_time' in driver_lap.columns else 0
                field_median = lap_data['lap_time'].median()
                rel_time = lap_time - field_median
                # Green if faster than field (< 0), Yellow if close (0-1.0s), Red if slow (> 1.0s)
                if rel_time < 0:
                    color_class = 'green'
                elif rel_time < 1.0:
                    color_class = 'yellow'
                else:
                    color_class = 'red'
                st.markdown(f"""
                <div class='metric-card-{color_class}'>
                    <div style='font-size:16px; opacity:0.9;'>LAST LAP</div>
                    <div style='font-size:56px; font-weight:bold; margin:5px 0;'>{rel_time:+.1f}s</div>
                </div>
                """, unsafe_allow_html=True)

    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)

    # ================================================================
    # SECTION 2: NEXT + CONTEXT (Side by side)
    # ================================================================
    col_next, col_context = st.columns([1, 2])

    with col_next:
        st.markdown("<h3 style='color:#667eea;'>NEXT LAP FORECAST</h3>", unsafe_allow_html=True)

        if predictor is not None and race_data is not None:
            lap_data = race_data[race_data['lap'] == st.session_state.current_lap]

            if len(lap_data) > 0:
                predictions = predictor.predict(lap_data, return_dataframe=True)
                current_positions = dict(zip(lap_data['vehicle_number'], lap_data['position']))

                driver_pred = predictions[predictions['vehicle_number'] == selected_driver]

                if len(driver_pred) > 0:
                    pred_row = driver_pred.iloc[0]

                    # Big prediction number
                    pace_val = pred_row['predicted_relative']
                    pace_color = "#22c55e" if pace_val < 0 else "#ef4444"
                    confidence = pred_row.get('confidence', 'medium')

                    st.markdown(f"""
                    <div style='text-align:center; padding:20px; background:#f8fafc; border-radius:8px;'>
                        <div style='font-size:14px; color:#6b7280;'>Expected Pace</div>
                        <div style='font-size:64px; font-weight:bold; color:{pace_color}; margin:10px 0;'>{pace_val:+.2f}s</div>
                        <div style='font-size:16px; color:#6b7280;'>Confidence: {confidence.upper()}</div>
                    </div>
                    """, unsafe_allow_html=True)

                    st.markdown("<br>", unsafe_allow_html=True)

                    # Field forecast
                    st.markdown("<div class='forecast-title'>Field Forecast</div>",
                               unsafe_allow_html=True)
                    forecast_fig = create_compact_prediction_chart(predictions, selected_driver, current_positions)
                    if forecast_fig:
                        st.plotly_chart(forecast_fig, use_container_width=True, config={'displayModeBar': False})

    with col_context:
        st.markdown("<h3 style='color:#667eea;'>RACE CONTEXT</h3>", unsafe_allow_html=True)

        # Create three separate plots with individual legends
        # Top row: Gap Analysis and Sector Performance
        context_row1_col1, context_row1_col2 = st.columns(2)

        with context_row1_col1:
            st.markdown("<div style='font-size:14px; color:#0f172a; font-weight:600; margin:10px 0 8px 0; font-family:Inter, system-ui, sans-serif;'>Gap Analysis</div>", unsafe_allow_html=True)
            gap_fig = create_gap_analysis_plot(race_data, selected_driver, st.session_state.current_lap)
            if gap_fig:
                st.plotly_chart(gap_fig, use_container_width=True, config={'displayModeBar': False})

        with context_row1_col2:
            st.markdown("<div style='font-size:14px; color:#0f172a; font-weight:600; margin:10px 0 8px 0; font-family:Inter, system-ui, sans-serif;'>Sector Performance</div>", unsafe_allow_html=True)
            sector_fig = create_sector_performance_plot(race_data, selected_driver, st.session_state.current_lap)
            if sector_fig:
                st.plotly_chart(sector_fig, use_container_width=True, config={'displayModeBar': False})

        # Bottom row: Position Progression (full width)
        st.markdown("<div style='font-size:14px; color:#0f172a; font-weight:600; margin:10px 0 8px 0; font-family:Inter, system-ui, sans-serif;'>Position Progression</div>", unsafe_allow_html=True)
        position_fig = create_position_progression_plot(race_data, selected_driver, st.session_state.current_lap)
        if position_fig:
            st.plotly_chart(position_fig, use_container_width=True, config={'displayModeBar': False})

    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)

    # ================================================================
    # SECTION 3: DIAGNOSTICS (Conditional on alerts)
    # ================================================================
    all_alerts = field_monitor.generate_all_alerts()
    all_alerts.extend(st.session_state.alerts)
    driver_alerts = [a for a in all_alerts if a.vehicle_number == selected_driver]

    if driver_alerts:
        st.markdown("<h3 style='color:#ef4444;'>⚠️ TECHNIQUE DIAGNOSTICS</h3>", unsafe_allow_html=True)

        alert_cols = st.columns(min(len(driver_alerts), 3))
        for i, alert in enumerate(driver_alerts[:3]):
            with alert_cols[i]:
                severity_colors = {1: "#3b82f6", 2: "#f59e0b", 3: "#ef4444"}
                color = severity_colors.get(alert.severity.value, "#6b7280")

                st.markdown(f"""
                <div style='background:#f8fafc; padding:15px; border-radius:8px; border-left:4px solid {color};'>
                    <div style='font-weight:bold; font-size:14px;'>{alert.metric_display}</div>
                    <div style='color:#4b5563; margin-top:8px; font-size:13px;'>{alert.action}</div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)

    # ================================================================
    # SECTION 4: COACHING RADIO
    # ================================================================
    st.markdown("<h3 style='color:#667eea;'>📻 RADIO MESSAGE</h3>", unsafe_allow_html=True)

    if predictor is not None and race_data is not None:
        lap_data = race_data[race_data['lap'] == st.session_state.current_lap]

        if len(lap_data) > 0:
            predictions = predictor.predict(lap_data, return_dataframe=True)
            current_positions = dict(zip(lap_data['vehicle_number'], lap_data['position']))
            driver_pred = predictions[predictions['vehicle_number'] == selected_driver]

            if len(driver_pred) > 0:
                driver_history = race_data[race_data['vehicle_number'] == selected_driver]
                message = generate_coaching_message(driver_pred.iloc[0], driver_history, current_positions)

                st.markdown(f"""
                <div class='radio-message'>
                    {message}
                </div>
                """, unsafe_allow_html=True)

    # Simulation logic
    if st.session_state.running and st.session_state.current_lap < 20:
        time.sleep(2.0 / sim_speed)
        st.session_state.current_lap += 1
        lap = st.session_state.current_lap

        state = st.session_state.monitor.process_lap(telemetry, lap)
        alerts = st.session_state.monitor.generate_alerts()
        st.session_state.alerts.extend(alerts)

        st.rerun()
    elif st.session_state.current_lap >= 20:
        st.session_state.running = False
        st.success("🏁 Race Complete!")


if __name__ == "__main__":
    main()
