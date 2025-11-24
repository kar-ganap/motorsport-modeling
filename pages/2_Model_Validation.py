"""
Model Validation Dashboard

Visualizes prediction quality metrics across all tracks and races.
Shows how prediction accuracy varies by:
- Warmup laps (3, 5, 8, 10, 15)
- Prediction horizons (1, 2, 3, 5 laps ahead)
- Individual drivers
- Top-5 race finish predictions
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from pathlib import Path
from typing import Dict, List, Tuple

# ============================================================================
# CONFIGURATION
# ============================================================================

PROCESSED_DIR = Path(__file__).parent.parent / "data" / "processed"
TRACKS = ['barber', 'cota', 'indianapolis', 'road-america', 'sebring', 'sonoma', 'vir']
RACES = ['race1', 'race2']
WARMUP_LAPS = [3, 5, 8, 10, 15]
HORIZONS = [1, 2, 3, 5]

# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title="Toyota Motorsport - Model Validation",
    page_icon="🏎️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# CSS STYLING
# ============================================================================

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

    * {
        font-family: 'Inter', system-ui, -apple-system, sans-serif;
    }

    .main {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    }

    h1, h2, h3 {
        font-weight: 700;
        color: #0f172a;
    }

    .stSelectbox label, .stMetric label {
        font-weight: 600;
        color: #475569;
    }

    .metric-card {
        background: white;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        margin-bottom: 15px;
    }

    .stDataFrame {
        font-size: 13px;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# DATA LOADING FUNCTIONS
# ============================================================================

@st.cache_data
def load_validation_data(track: str, race: str) -> pd.DataFrame:
    """Load precomputed validation data for a track/race."""
    file_path = PROCESSED_DIR / track / f"{race}_validation.parquet"
    if file_path.exists():
        return pd.read_parquet(file_path)
    return None

@st.cache_data
def load_top5_data(track: str, race: str) -> pd.DataFrame:
    """Load precomputed top-5 predictions for a track/race."""
    file_path = PROCESSED_DIR / track / f"{race}_top5.parquet"
    if file_path.exists():
        return pd.read_parquet(file_path)
    return None

@st.cache_data
def load_driver_stats(track: str, race: str) -> pd.DataFrame:
    """Load per-driver statistics for a track/race."""
    file_path = PROCESSED_DIR / track / f"{race}_driver_stats.parquet"
    if file_path.exists():
        return pd.read_parquet(file_path)
    return None

@st.cache_data
def load_manifest() -> Dict:
    """Load the manifest of all processed races."""
    file_path = PROCESSED_DIR / "manifest.json"
    if file_path.exists():
        import json
        with open(file_path, 'r') as f:
            return json.load(f)
    return {}

# ============================================================================
# VISUALIZATION FUNCTIONS
# ============================================================================

def compute_position_weights(positions: pd.Series, mode: str = 'podium') -> pd.Series:
    """
    Compute weights based on finishing position.

    Args:
        positions: Series of race positions
        mode: 'podium' weights top-3 heavily, 'exponential' decays smoothly

    Returns:
        Series of weights (higher for better positions)
    """
    if mode == 'podium':
        # Top-3 get 3x weight, positions 4-10 get 1.5x, rest get 1x
        weights = positions.apply(lambda p: 3.0 if p <= 3 else (1.5 if p <= 10 else 1.0))
    elif mode == 'exponential':
        # Exponential decay: weight = 1 / (1 + 0.1 * (position - 1))
        weights = 1.0 / (1.0 + 0.1 * (positions - 1))
    else:  # 'uniform'
        weights = pd.Series(1.0, index=positions.index)

    return weights


def create_warmup_horizon_heatmap(validation_data: pd.DataFrame, weight_mode: str = 'podium') -> go.Figure:
    """
    Create heatmap showing MAE by warmup laps (rows) and horizons (columns).

    Args:
        validation_data: DataFrame with validation results
        weight_mode: 'uniform', 'podium', or 'exponential' weighting by position
    """
    # Compute position-weighted MAE for each combination
    if weight_mode != 'uniform':
        # Add weights based on position
        data = validation_data.copy()
        data['weight'] = compute_position_weights(data['position'], mode=weight_mode)
        data['weighted_error'] = data['abs_error'] * data['weight']

        # Compute weighted average
        heatmap_data = data.groupby(['warmup_laps', 'horizon']).apply(
            lambda g: (g['weighted_error'].sum() / g['weight'].sum())
        ).reset_index(name='abs_error')
    else:
        # Uniform weighting (original behavior)
        heatmap_data = validation_data.groupby(['warmup_laps', 'horizon'])['abs_error'].mean().reset_index()

    # Pivot to matrix form
    matrix = heatmap_data.pivot(index='warmup_laps', columns='horizon', values='abs_error')

    fig = go.Figure(data=go.Heatmap(
        z=matrix.values,
        x=[f"{h}L" for h in matrix.columns],
        y=[f"{w}L" for w in matrix.index],
        colorscale='RdYlGn_r',  # Red = bad (high error), Green = good (low error)
        text=matrix.values,
        texttemplate='%{text:.2f}s',
        textfont={"size": 12, "color": "white", "family": "Inter"},
        hovertemplate='Warmup: %{y}<br>Horizon: %{x}<br>MAE: %{z:.3f}s<extra></extra>',
        colorbar=dict(
            title=dict(
                text="MAE (s)",
                font=dict(family="Inter", size=12)
            ),
            tickfont=dict(family="Inter", size=11)
        )
    ))

    fig.update_layout(
        title=dict(
            text="Prediction Quality: Warmup vs Horizon",
            font=dict(size=16, family="Inter", weight=600, color='#0f172a')
        ),
        xaxis=dict(
            title=dict(
                text="Prediction Horizon",
                font=dict(size=13, family="Inter", color='#475569')
            ),
            tickfont=dict(size=11, family="Inter", color='#64748b')
        ),
        yaxis=dict(
            title=dict(
                text="Warmup Laps",
                font=dict(size=13, family="Inter", color='#475569')
            ),
            tickfont=dict(size=11, family="Inter", color='#64748b')
        ),
        height=400,
        plot_bgcolor='white',
        paper_bgcolor='white',
        margin=dict(l=80, r=80, t=60, b=60)
    )

    return fig


def create_top5_accuracy_chart(top5_data: pd.DataFrame) -> go.Figure:
    """
    Create line chart showing top-5 prediction accuracy over laps.
    """
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=top5_data['prediction_lap'],
        y=top5_data['set_accuracy'] * 100,  # Convert to percentage
        mode='lines+markers',
        name='Set Accuracy',
        line=dict(color='#667eea', width=3),
        marker=dict(size=8, color='#667eea', line=dict(width=2, color='white')),
        hovertemplate='<b>Lap %{x}</b><br>Accuracy: %{y:.0f}%<extra></extra>'
    ))

    # Add horizontal line at 100%
    fig.add_hline(
        y=100,
        line_dash="dash",
        line_color="green",
        opacity=0.5,
        annotation_text="Perfect",
        annotation_position="right"
    )

    fig.update_layout(
        title=dict(
            text="Top-5 Finish Prediction Accuracy",
            font=dict(size=16, family="Inter", weight=600, color='#0f172a')
        ),
        xaxis=dict(
            title=dict(
                text="Prediction Lap",
                font=dict(size=13, family="Inter", color='#475569')
            ),
            tickfont=dict(size=11, family="Inter", color='#64748b'),
            dtick=5
        ),
        yaxis=dict(
            title=dict(
                text="Accuracy (%)",
                font=dict(size=13, family="Inter", color='#475569')
            ),
            tickfont=dict(size=11, family="Inter", color='#64748b'),
            range=[0, 105]
        ),
        height=350,
        plot_bgcolor='white',
        paper_bgcolor='white',
        margin=dict(l=60, r=60, t=60, b=60),
        showlegend=False
    )

    return fig


def create_driver_performance_table(driver_stats: pd.DataFrame) -> pd.DataFrame:
    """
    Format driver statistics for display as a clean table.
    Sorted by RMSE (best first).
    """
    df = driver_stats.reset_index()
    df = df.rename(columns={'vehicle_number': 'Driver #'})

    # Format columns
    df['RMSE (s)'] = df['rmse'].apply(lambda x: f"{x:.3f}")
    df['MAE (s)'] = df['mae'].apply(lambda x: f"{x:.3f}")
    df['Avg Position'] = df['avg_position'].apply(lambda x: f"{x:.1f}")
    df['Predictions'] = df['num_predictions'].astype(int)
    df['Worst Lap'] = df['worst_lap'].astype(int)
    df['Worst Error (s)'] = df['worst_error'].apply(lambda x: f"{x:.3f}")

    # Select and reorder columns
    display_df = df[[
        'Driver #', 'RMSE (s)', 'MAE (s)', 'Avg Position',
        'Predictions', 'Worst Lap', 'Worst Error (s)'
    ]]

    return display_df

# ============================================================================
# MAIN APP
# ============================================================================

def main():
    # Header
    st.markdown("""
        <div style='background: linear-gradient(90deg, #eb0a1e 0%, #1a1a1a 50%);
                    padding: 25px;
                    border-radius: 10px;
                    margin-bottom: 30px;'>
            <div style='display: flex; align-items: center;'>
                <span style='font-size: 40px; margin-right: 15px;'>🏎️</span>
                <div>
                    <h1 style='color: white; margin: 0; font-size: 32px;'>
                        TOYOTA GAZOO RACING
                    </h1>
                    <p style='color: #e0e0e0; margin: 5px 0 0 0; font-size: 16px;'>
                        Model Validation Dashboard
                    </p>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Sidebar for race selection
    st.sidebar.title("Race Selection")

    # Track selection
    track_display_names = {
        'barber': 'Barber Motorsports Park',
        'cota': 'Circuit of the Americas',
        'indianapolis': 'Indianapolis Motor Speedway',
        'road-america': 'Road America',
        'sebring': 'Sebring International Raceway',
        'sonoma': 'Sonoma Raceway',
        'vir': 'Virginia International Raceway'
    }

    selected_track_key = st.sidebar.selectbox(
        "Track",
        options=TRACKS,
        format_func=lambda x: track_display_names.get(x, x),
        index=TRACKS.index('indianapolis')
    )

    selected_race = st.sidebar.selectbox(
        "Race",
        options=RACES,
        format_func=lambda x: x.replace('race', 'Race '),
        index=0
    )

    # Load data
    validation_data = load_validation_data(selected_track_key, selected_race)
    top5_data = load_top5_data(selected_track_key, selected_race)
    driver_stats = load_driver_stats(selected_track_key, selected_race)

    if validation_data is None:
        st.error(f"No validation data found for {selected_track_key} / {selected_race}")
        return

    # Display summary metrics
    st.subheader("📊 Overall Performance")

    col1, col2, col3, col4 = st.columns(4)

    overall_mae = validation_data['abs_error'].mean()
    overall_rmse = np.sqrt((validation_data['error'] ** 2).mean())
    total_predictions = len(validation_data)
    num_drivers = validation_data['vehicle_number'].nunique()

    with col1:
        st.metric("Mean Absolute Error", f"{overall_mae:.3f}s")
    with col2:
        st.metric("RMSE", f"{overall_rmse:.3f}s")
    with col3:
        st.metric("Total Predictions", f"{total_predictions:,}")
    with col4:
        st.metric("Drivers", f"{num_drivers}")

    st.markdown("<br>", unsafe_allow_html=True)

    # Weighting mode selector
    st.markdown("### ⚖️ Error Weighting")
    weight_mode = st.selectbox(
        "How to weight prediction errors by position:",
        options=['podium', 'uniform', 'exponential'],
        format_func=lambda x: {
            'podium': 'Podium Focus (Top-3: 3x, Top-10: 1.5x, Rest: 1x)',
            'uniform': 'Uniform (All drivers weighted equally)',
            'exponential': 'Exponential Decay (Smooth gradient)'
        }[x],
        index=0  # Default to podium weighting
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # Main content: Two columns
    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.subheader("🔥 Prediction Quality Heatmap")
        heatmap_fig = create_warmup_horizon_heatmap(validation_data, weight_mode=weight_mode)
        st.plotly_chart(heatmap_fig, use_container_width=True, config={'displayModeBar': False})

        weight_desc = {
            'podium': 'Podium drivers (1-3) errors count 3x more than backmarkers',
            'uniform': 'All drivers weighted equally (classic average)',
            'exponential': 'Smooth decay - leaders weighted more than backmarkers'
        }[weight_mode]

        st.markdown(f"""
        <div style='background: #f8fafc; padding: 12px; border-radius: 6px; border-left: 4px solid #667eea; margin-top: 10px;'>
            <p style='margin: 0; color: #475569; font-size: 13px;'>
                <b>Reading the heatmap:</b><br>
                • <span style='color: #22c55e;'>Green</span> = Low error (good predictions)<br>
                • <span style='color: #eab308;'>Yellow</span> = Medium error<br>
                • <span style='color: #ef4444;'>Red</span> = High error (poor predictions)<br>
                • <b>Weighting:</b> {weight_desc}
            </p>
        </div>
        """, unsafe_allow_html=True)

    with col_right:
        if top5_data is not None and len(top5_data) > 0:
            st.subheader("🏆 Top-5 Finish Predictions")
            top5_fig = create_top5_accuracy_chart(top5_data)
            st.plotly_chart(top5_fig, use_container_width=True, config={'displayModeBar': False})

            # Show average metrics
            avg_set_accuracy = top5_data['set_accuracy'].mean() * 100
            avg_ndcg = top5_data['ndcg'].mean()
            st.markdown(f"""
            <div style='background: #ecfdf5; padding: 12px; border-radius: 6px; border-left: 4px solid #10b981; margin-top: 10px;'>
                <p style='margin: 0; color: #047857; font-size: 13px;'>
                    <b>Set Accuracy: {avg_set_accuracy:.1f}%</b> | <b>NDCG@5: {avg_ndcg:.3f}</b><br>
                    Model correctly identifies {avg_set_accuracy:.0f}% of top-5 finishers. NDCG measures ranking quality (1.0 = perfect).
                </p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info("No top-5 prediction data available for this race.")

    # Driver breakdown table
    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader("👥 Driver Breakdown")

    if driver_stats is not None:
        display_table = create_driver_performance_table(driver_stats)

        st.dataframe(
            display_table,
            use_container_width=True,
            height=400,
            hide_index=True
        )

        st.markdown("""
        <div style='background: #fffbeb; padding: 12px; border-radius: 6px; border-left: 4px solid #f59e0b; margin-top: 10px;'>
            <p style='margin: 0; color: #92400e; font-size: 13px;'>
                <b>Table sorted by RMSE (best first)</b><br>
                Lower RMSE/MAE = more predictable driver. Worst lap shows where model struggled most.
            </p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.info("No driver statistics available for this race.")


if __name__ == "__main__":
    main()
