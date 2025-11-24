"""
Race Insights - Post-Race Strategic Analysis

Combines comparative and counterfactual analysis to answer:
1. Why did I finish where I did? (Comparative Analysis)
2. What could I have done better? (Counterfactual Analysis)
"""

import streamlit as st
import pandas as pd
from pathlib import Path
import plotly.graph_objects as go
import plotly.express as px

# Page config
st.set_page_config(
    page_title="Race Insights",
    page_icon="📊",
    layout="wide"
)

# Custom CSS for larger tab labels
st.markdown("""
<style>
    /* Increase tab label font size */
    .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {
        font-size: 20px;
        font-weight: 600;
    }

    /* Increase tab label padding for better spacing */
    .stTabs [data-baseweb="tab-list"] button {
        padding-top: 12px;
        padding-bottom: 12px;
    }
</style>
""", unsafe_allow_html=True)

# Title
st.title("📊 Race Insights")
st.markdown("### Post-Race Strategic Analysis")

# Track and race selection
col1, col2 = st.columns(2)

# Track display names matching other pages
track_display_names = {
    'barber': 'Barber Motorsports Park',
    'cota': 'Circuit of the Americas',
    'indianapolis': 'Indianapolis Motor Speedway',
    'road-america': 'Road America',
    'sebring': 'Sebring International Raceway',
    'sonoma': 'Sonoma Raceway',
    'vir': 'Virginia International Raceway'
}

with col1:
    tracks = sorted([d.name for d in Path('data/raw/tracks').iterdir() if d.is_dir()])
    selected_track = st.selectbox(
        "Track",
        tracks,
        index=tracks.index('indianapolis') if 'indianapolis' in tracks else 0,
        format_func=lambda x: track_display_names.get(x, x)
    )

with col2:
    races = sorted([d.name for d in Path(f'data/raw/tracks/{selected_track}').iterdir() if d.is_dir()])
    selected_race = st.selectbox(
        "Race",
        races,
        format_func=lambda x: x.replace('race', 'Race ').title()
    )

# Load data
@st.cache_data
def load_comparative_data(track, race):
    """Load comparative analysis data"""
    file_path = Path(f'data/processed/{track}/{race}_comparative.parquet')
    if file_path.exists():
        return pd.read_parquet(file_path)
    return None

@st.cache_data
def load_counterfactual_data(track, race):
    """Load counterfactual analysis data"""
    file_path = Path(f'data/processed/{track}/{race}_counterfactuals.parquet')
    if file_path.exists():
        return pd.read_parquet(file_path)
    return None

comparative_df = load_comparative_data(selected_track, selected_race)
counterfactual_df = load_counterfactual_data(selected_track, selected_race)

# Check if data exists
if comparative_df is None and counterfactual_df is None:
    st.error(f"No analysis data found for {selected_track}/{selected_race}")
    st.stop()

# Create tabs
tab1, tab2 = st.tabs(["🔍 Comparative Analysis", "🎯 Counterfactual Analysis"])

# Tab 1: Comparative Analysis
with tab1:
    st.markdown("### Why Did I Finish Where I Did?")
    st.markdown("<p style='font-size: 18px;'>Understand your race result by comparing against the driver directly ahead</p>", unsafe_allow_html=True)

    if comparative_df is not None:
        # Driver selector
        drivers = sorted(comparative_df['vehicle_number'].unique())
        selected_driver = st.selectbox(
            "Select Driver",
            drivers,
            format_func=lambda x: f"Driver #{int(x)} - P{int(comparative_df[comparative_df['vehicle_number']==x]['final_position'].iloc[0])}"
        )

        # Get driver data
        driver_data = comparative_df[comparative_df['vehicle_number'] == selected_driver].iloc[0]

        # Overview metrics
        st.markdown("#### Race Result")
        metric_cols = st.columns(4)

        with metric_cols[0]:
            st.metric("Final Position", f"P{int(driver_data['final_position'])}")

        with metric_cols[1]:
            st.metric("Gap to Winner", f"{driver_data['gap_to_winner']:.2f}s")

        with metric_cols[2]:
            if pd.notna(driver_data.get('ahead_vehicle')):
                st.metric("Gap to P" + str(int(driver_data['final_position'])-1),
                         f"{abs(driver_data['gap_to_ahead']):.2f}s")
            else:
                st.metric("Gap to Ahead", "Winner!")

        with metric_cols[3]:
            if pd.notna(driver_data.get('traffic_cost')):
                st.metric("Traffic Cost", f"{driver_data['traffic_cost']:.2f}s")
            else:
                st.metric("Traffic Cost", "N/A")

        # AI Narrative
        st.markdown("#### AI Analysis")
        if pd.notna(driver_data.get('narrative')) and driver_data['narrative']:
            st.info(driver_data['narrative'])
        else:
            st.warning("No narrative available for this driver")

        # Performance Comparison
        if pd.notna(driver_data.get('ahead_vehicle')):
            st.markdown("#### Performance vs Driver Ahead")

            comp_cols = st.columns(3)

            with comp_cols[0]:
                st.markdown("**Tire Degradation**")
                deg_delta = driver_data.get('ahead_deg_delta', 0)
                if abs(deg_delta) > 0.001:
                    if deg_delta > 0:
                        st.error(f"⚠️ Worse by {abs(deg_delta):.4f} s/lap")
                    else:
                        st.success(f"✅ Better by {abs(deg_delta):.4f} s/lap")
                else:
                    st.info("≈ Similar degradation")

            with comp_cols[1]:
                st.markdown("**Pace Delta**")
                pace_delta = driver_data.get('ahead_pace_delta', 0)
                if abs(pace_delta) > 0.01:
                    if pace_delta > 0:
                        st.error(f"⚠️ Slower by {abs(pace_delta):.3f} s/lap")
                    else:
                        st.success(f"✅ Faster by {abs(pace_delta):.3f} s/lap")
                else:
                    st.info("≈ Similar pace")

            with comp_cols[2]:
                st.markdown("**Traffic Impact**")
                traffic_delta = driver_data.get('ahead_traffic_delta', 0)
                if abs(traffic_delta) > 0.5:
                    if traffic_delta > 0:
                        st.error(f"⚠️ More traffic (+{abs(traffic_delta):.1f} laps)")
                    else:
                        st.success(f"✅ Less traffic (-{abs(traffic_delta):.1f} laps)")
                else:
                    st.info("≈ Similar traffic")

            # Pace progression chart
            if all(pd.notna(driver_data.get(col)) for col in ['early_pace', 'mid_pace', 'late_pace',
                                                                 'ahead_early_pace', 'ahead_mid_pace', 'ahead_late_pace']):
                st.markdown("#### Pace Progression")

                fig = go.Figure()

                # Driver pace
                fig.add_trace(go.Scatter(
                    x=['Early Stint', 'Mid Stint', 'Late Stint'],
                    y=[driver_data['early_pace'], driver_data['mid_pace'], driver_data['late_pace']],
                    name=f"You (#{int(selected_driver)})",
                    mode='lines+markers',
                    line=dict(color='#667eea', width=4),
                    marker=dict(size=12, line=dict(color='white', width=2)),
                    hovertemplate='<b>You</b><br>%{y:.3f}s<extra></extra>'
                ))

                # Ahead driver pace
                fig.add_trace(go.Scatter(
                    x=['Early Stint', 'Mid Stint', 'Late Stint'],
                    y=[driver_data['ahead_early_pace'], driver_data['ahead_mid_pace'], driver_data['ahead_late_pace']],
                    name=f"P{int(driver_data['final_position'])-1} (#{int(driver_data['ahead_vehicle'])})",
                    mode='lines+markers',
                    line=dict(color='#f87171', width=4, dash='dash'),
                    marker=dict(size=12, line=dict(color='white', width=2)),
                    hovertemplate='<b>P%{customdata}</b><br>%{y:.3f}s<extra></extra>',
                    customdata=[int(driver_data['final_position'])-1]*3
                ))

                fig.update_layout(
                    title=dict(
                        text="<b>Pace Evolution: Early → Mid → Late</b>",
                        font=dict(size=20, family="Arial, sans-serif", color='#1f2937')
                    ),
                    xaxis=dict(
                        title=dict(text="<b>Race Phase</b>", font=dict(size=16, color='#374151')),
                        tickfont=dict(size=13, color='#1f2937'),
                        showgrid=True,
                        gridcolor='rgba(128,128,128,0.1)'
                    ),
                    yaxis=dict(
                        title=dict(text="<b>Average Lap Time (seconds)</b>", font=dict(size=16, color='#374151')),
                        tickfont=dict(size=13, color='#1f2937'),
                        showgrid=True,
                        gridcolor='rgba(128,128,128,0.2)'
                    ),
                    hovermode='x unified',
                    height=450,
                    legend=dict(
                        font=dict(size=13),
                        bgcolor='rgba(255,255,255,0.8)',
                        bordercolor='rgba(0,0,0,0.1)',
                        borderwidth=1
                    ),
                    plot_bgcolor='rgba(250,250,250,0.5)',
                    margin=dict(t=70, b=70, l=80, r=40)
                )

                st.plotly_chart(fig, use_container_width=True)

        # Field comparison
        st.markdown("#### Field Benchmarks")

        # Degradation - simpler gauge-style visualization
        if 'driver_deg' in comparative_df.columns and pd.notna(driver_data.get('driver_deg')):
            deg_cols = st.columns([1, 2])

            with deg_cols[0]:
                st.markdown("**Tire Degradation**")
                driver_deg = driver_data['driver_deg']
                field_median = comparative_df['driver_deg'].median()
                field_p25 = comparative_df['driver_deg'].quantile(0.25)  # Top 25% (lower is better)

                # Show driver value with context
                st.metric(
                    "Your Rate",
                    f"{driver_deg:.4f} s/lap",
                    delta=f"{(driver_deg - field_median):.4f} vs median",
                    delta_color="inverse"  # Red when higher (worse)
                )

                # Performance assessment
                if driver_deg <= field_p25:
                    st.success("✅ Top 25% tire management")
                elif driver_deg <= field_median:
                    st.info("📊 Above average tire management")
                else:
                    st.warning("⚠️ Room for improvement")

            with deg_cols[1]:
                # Histogram showing field distribution
                fig = go.Figure()
                fig.add_trace(go.Histogram(
                    x=comparative_df['driver_deg'],
                    nbinsx=15,
                    marker=dict(
                        color='#cbd5e1',
                        line=dict(color='white', width=1)
                    ),
                    name='Field',
                    hovertemplate='<b>%{y} drivers</b><br>Degradation: %{x:.4f}s/lap<extra></extra>'
                ))

                # Add driver's position as vertical line
                fig.add_vline(
                    x=driver_deg,
                    line_dash="dash",
                    line_color="#667eea",
                    line_width=4,
                    annotation=dict(
                        text="<b>You</b>",
                        font=dict(size=13, color="#667eea"),
                        yshift=10
                    )
                )

                # Add median line
                fig.add_vline(
                    x=field_median,
                    line_dash="dot",
                    line_color="#64748b",
                    line_width=3,
                    annotation=dict(
                        text="<b>Median</b>",
                        font=dict(size=13, color="#64748b"),
                        yshift=-10
                    )
                )

                fig.update_layout(
                    title=dict(
                        text="<b>Degradation Rate Distribution</b>",
                        font=dict(size=18, family="Arial, sans-serif", color='#1f2937')
                    ),
                    xaxis=dict(
                        title=dict(text="<b>Degradation Rate (s/lap)</b>", font=dict(size=15, color='#374151')),
                        tickfont=dict(size=12, color='#1f2937'),
                        showgrid=True,
                        gridcolor='rgba(128,128,128,0.1)'
                    ),
                    yaxis=dict(
                        title=dict(text="<b>Driver Count</b>", font=dict(size=15, color='#374151')),
                        tickfont=dict(size=12, color='#1f2937'),
                        showgrid=True,
                        gridcolor='rgba(128,128,128,0.2)'
                    ),
                    showlegend=False,
                    height=300,
                    margin=dict(t=60, b=60, l=60, r=40),
                    plot_bgcolor='rgba(250,250,250,0.5)',
                    bargap=0.1
                )
                st.plotly_chart(fig, use_container_width=True)

        # Traffic analysis
        if 'driver_traffic' in comparative_df.columns and pd.notna(driver_data.get('driver_traffic')):
            st.markdown("**Traffic Impact**")
            traffic_cols = st.columns(3)

            with traffic_cols[0]:
                st.metric("Your Traffic Laps", f"{int(driver_data['driver_traffic'])}")

            with traffic_cols[1]:
                field_median_traffic = comparative_df['driver_traffic'].median()
                st.metric("Field Median", f"{int(field_median_traffic)}")

            with traffic_cols[2]:
                field_min_traffic = comparative_df['driver_traffic'].min()
                st.metric("Field Best", f"{int(field_min_traffic)}")

    else:
        st.warning(f"No comparative analysis data available for {selected_track}/{selected_race}")

# Tab 2: Counterfactual Analysis
with tab2:
    st.markdown("### What Could I Have Done Better?")
    st.markdown("<p style='font-size: 18px;'>Explore \"what if\" scenarios showing potential improvements</p>", unsafe_allow_html=True)

    if counterfactual_df is not None:
        # Driver selector
        drivers = sorted(counterfactual_df['vehicle_number'].unique())
        cf_selected_driver = st.selectbox(
            "Select Driver ",
            drivers,
            format_func=lambda x: f"Driver #{int(x)} - P{int(counterfactual_df[counterfactual_df['vehicle_number']==x]['original_position'].iloc[0])}",
            key='cf_driver_select'
        )

        # Get driver data
        cf_driver_data = counterfactual_df[counterfactual_df['vehicle_number'] == cf_selected_driver].iloc[0]

        # Overview
        st.markdown("#### Current Performance")
        cf_metric_cols = st.columns(4)

        with cf_metric_cols[0]:
            st.metric("Position", f"P{int(cf_driver_data['original_position'])}")

        with cf_metric_cols[1]:
            st.metric("Avg Lap Time", f"{cf_driver_data['original_avg_lap_time']:.3f}s")

        with cf_metric_cols[2]:
            st.metric("Total Time Savings Potential",
                     f"{cf_driver_data['total_time_savings']:.2f}s",
                     delta=f"-{cf_driver_data['total_time_savings']:.2f}s")

        with cf_metric_cols[3]:
            position_gain = int(cf_driver_data['predicted_position_gain'])
            if position_gain > 0:
                st.metric("Potential Position Gain",
                         f"+{position_gain}",
                         delta=f"+{position_gain} positions")
            else:
                st.metric("Potential Position Gain", "0")

        # Model quality
        with st.expander("ℹ️ Model Quality"):
            model_cols = st.columns(2)
            with model_cols[0]:
                st.metric("Model R²", f"{cf_driver_data['model_r2']:.3f}")
            with model_cols[1]:
                st.metric("Model MAE", f"{cf_driver_data['model_mae']:.3f}s")

        # Interventions
        st.markdown("#### Improvement Opportunities")

        # Check which interventions exist
        interventions = []

        if pd.notna(cf_driver_data.get('intervention_degradation_rate_savings')):
            interventions.append({
                'name': 'Tire Management',
                'feature': 'degradation_rate',
                'original': cf_driver_data['intervention_degradation_rate_original'],
                'target': cf_driver_data['intervention_degradation_rate_target'],
                'savings': cf_driver_data['intervention_degradation_rate_savings'],
                'icon': '🛞'
            })

        if pd.notna(cf_driver_data.get('intervention_consistency_savings')):
            interventions.append({
                'name': 'Lap Consistency',
                'feature': 'consistency',
                'original': cf_driver_data['intervention_consistency_original'],
                'target': cf_driver_data['intervention_consistency_target'],
                'savings': cf_driver_data['intervention_consistency_savings'],
                'icon': '🎯'
            })

        if pd.notna(cf_driver_data.get('intervention_traffic_laps_savings')):
            interventions.append({
                'name': 'Traffic Avoidance',
                'feature': 'traffic_laps',
                'original': cf_driver_data['intervention_traffic_laps_original'],
                'target': cf_driver_data['intervention_traffic_laps_target'],
                'savings': cf_driver_data['intervention_traffic_laps_savings'],
                'icon': '🚗'
            })

        if not interventions:
            st.info("✅ Already performing at field benchmarks - no major improvement opportunities identified!")
        else:
            # Sort by savings (highest first)
            interventions.sort(key=lambda x: x['savings'], reverse=True)

            # Display each intervention
            for i, intervention in enumerate(interventions, 1):
                with st.container():
                    st.markdown(f"<p style='font-size: 19px; font-weight: 600; margin-bottom: 8px;'>{i}. {intervention['icon']} {intervention['name']}</p>", unsafe_allow_html=True)

                    int_cols = st.columns([2, 2, 1])

                    with int_cols[0]:
                        if intervention['feature'] == 'traffic_laps':
                            st.write(f"Current: {int(intervention['original'])} laps in traffic")
                            st.write(f"Target: {int(intervention['target'])} laps (field minimum)")
                        elif intervention['feature'] == 'degradation_rate':
                            st.write(f"Current: {intervention['original']:.4f} s/lap degradation")
                            st.write(f"Target: {intervention['target']:.4f} s/lap (field P25)")
                        else:  # consistency
                            st.write(f"Current: {intervention['original']:.3f}s std dev")
                            st.write(f"Target: {intervention['target']:.3f}s (field P25)")

                    with int_cols[1]:
                        improvement_pct = (intervention['savings'] / cf_driver_data['total_time_savings']) * 100
                        st.metric("Time Savings", f"{intervention['savings']:.2f}s")
                        st.caption(f"{improvement_pct:.1f}% of total potential")

                    with int_cols[2]:
                        # Visual indicator
                        st.progress(min(intervention['savings'] / cf_driver_data['total_time_savings'], 1.0))

                    st.divider()

            # Intervention breakdown chart
            st.markdown("#### Improvement Breakdown")

            fig = go.Figure(data=[go.Bar(
                x=[f"{i['icon']} {i['name']}" for i in interventions],
                y=[i['savings'] for i in interventions],
                marker=dict(
                    color=['#667eea', '#f87171', '#fbbf24'][:len(interventions)],
                    line=dict(color='white', width=2)
                ),
                text=[f"<b>{i['savings']:.2f}s</b>" for i in interventions],
                textposition='inside',
                textfont=dict(size=14, color='white'),
                hovertemplate='<b>%{x}</b><br>Time Savings: %{y:.2f}s<extra></extra>'
            )])

            fig.update_layout(
                title=dict(
                    text="<b>Time Savings by Intervention</b>",
                    font=dict(size=20, family="Arial, sans-serif", color='#1f2937')
                ),
                xaxis=dict(
                    title=dict(text="<b>Intervention</b>", font=dict(size=16, color='#374151')),
                    tickfont=dict(size=14, color='#1f2937'),
                    showgrid=False
                ),
                yaxis=dict(
                    title=dict(text="<b>Time Savings (seconds)</b>", font=dict(size=16, color='#374151')),
                    tickfont=dict(size=13, color='#1f2937'),
                    showgrid=True,
                    gridcolor='rgba(128,128,128,0.2)'
                ),
                height=500,
                plot_bgcolor='rgba(250,250,250,0.5)',
                margin=dict(t=80, b=80, l=80, r=50),
                bargap=0.25,
                uniformtext=dict(mode='hide', minsize=10)
            )

            st.plotly_chart(fig, use_container_width=True)

        # Field benchmarks
        st.markdown("#### Field Benchmarks")
        benchmark_cols = st.columns(3)

        with benchmark_cols[0]:
            st.metric("Field P25 Degradation",
                     f"{cf_driver_data['field_p25_degradation']:.4f} s/lap",
                     help="Top 25% performance")

        with benchmark_cols[1]:
            st.metric("Field P25 Consistency",
                     f"{cf_driver_data['field_p25_consistency']:.3f}s",
                     help="Top 25% performance")

        with benchmark_cols[2]:
            st.metric("Field Min Traffic",
                     f"{int(cf_driver_data['field_min_traffic'])} laps",
                     help="Best in field")

    else:
        st.warning(f"No counterfactual analysis data available for {selected_track}/{selected_race}")

# Footer
st.markdown("---")
st.caption("💡 Use comparative analysis to understand your result, then counterfactual analysis to plan improvements")
