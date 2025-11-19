"""
RaceCraft AI - Lap Time Prediction Dashboard

A minimal Streamlit dashboard for:
1. Race overview and lap time visualization
2. Winner prediction at different laps
3. Model performance metrics

Run with: uv run streamlit run app/dashboard.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from motorsport_modeling.models.lap_time_predictor import (
    EnhancedLapPredictor,
    compute_winner_accuracy
)


# Page config
st.set_page_config(
    page_title="RaceCraft AI",
    page_icon="🏎️",
    layout="wide"
)


@st.cache_data
def load_race_data():
    """Load race feature data."""
    data_dir = Path(__file__).parent.parent / 'data' / 'processed'
    r1 = pd.read_csv(data_dir / 'race1_features.csv')
    r2 = pd.read_csv(data_dir / 'race2_features.csv')
    r1['race'] = 'Race 1'
    r2['race'] = 'Race 2'
    return r1, r2


@st.cache_resource
def load_model():
    """Load trained model."""
    model_path = Path(__file__).parent.parent / 'models' / 'enhanced_lap_predictor.pkl'
    if model_path.exists():
        model = EnhancedLapPredictor.load(model_path)
        return model
    return None


def main():
    st.title("🏎️ RaceCraft AI")
    st.markdown("*Toyota Gazoo Racing Cup - Lap Time Prediction*")

    # Load data
    r1, r2 = load_race_data()
    model = load_model()

    # Sidebar - Race selection
    st.sidebar.header("Controls")
    race_selection = st.sidebar.selectbox("Select Race", ["Race 1", "Race 2"])
    race_data = r1 if race_selection == "Race 1" else r2

    # Get actual winner
    final_lap = race_data['lap'].max()
    final_positions = race_data[race_data['lap'] == final_lap].sort_values('position')
    actual_winner = int(final_positions.iloc[0]['vehicle_number'])

    # Overview metrics
    st.header("Race Overview")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Vehicles", race_data['vehicle_number'].nunique())
    with col2:
        st.metric("Total Laps", int(race_data['lap'].max()))
    with col3:
        mean_temp = race_data['air_temp'].iloc[0] if 'air_temp' in race_data.columns else "N/A"
        st.metric("Air Temp", f"{mean_temp:.1f}°C" if isinstance(mean_temp, float) else mean_temp)
    with col4:
        st.metric("Winner", f"#{actual_winner}")

    # Tabs
    tab1, tab2, tab3 = st.tabs(["Lap Times", "Winner Prediction", "Model Info"])

    with tab1:
        st.subheader("Lap Time Progression")

        # Vehicle selection
        vehicles = sorted(race_data['vehicle_number'].unique())
        top_vehicles = final_positions.head(5)['vehicle_number'].tolist()

        selected_vehicles = st.multiselect(
            "Select vehicles to display",
            options=vehicles,
            default=[int(v) for v in top_vehicles[:3]]
        )

        if selected_vehicles:
            # Filter data
            plot_data = race_data[race_data['vehicle_number'].isin(selected_vehicles)]

            # Lap time plot
            fig = px.line(
                plot_data,
                x='lap',
                y='lap_time',
                color='vehicle_number',
                markers=True,
                title="Lap Times by Vehicle"
            )
            fig.update_layout(
                xaxis_title="Lap",
                yaxis_title="Lap Time (s)",
                legend_title="Vehicle #"
            )
            st.plotly_chart(fig, use_container_width=True)

            # Position plot
            fig2 = px.line(
                plot_data,
                x='lap',
                y='position',
                color='vehicle_number',
                markers=True,
                title="Race Position"
            )
            fig2.update_layout(
                xaxis_title="Lap",
                yaxis_title="Position",
                yaxis_autorange="reversed",  # P1 at top
                legend_title="Vehicle #"
            )
            st.plotly_chart(fig2, use_container_width=True)

    with tab2:
        st.subheader("Winner Prediction")

        if model is None:
            st.warning("Model not found. Please run training script first.")
        else:
            # Slider for prediction lap
            max_lap = int(race_data['lap'].max())
            pred_lap = st.slider("Predict winner from lap:", 2, max_lap - 1, 10)

            # Make prediction
            # Get data up to selected lap
            data_to_lap = race_data[race_data['lap'] <= pred_lap].copy()

            # Get predictions for remaining laps
            predictions = []
            for vehicle in data_to_lap['vehicle_number'].unique():
                vehicle_data = data_to_lap[data_to_lap['vehicle_number'] == vehicle]
                if len(vehicle_data) > 0:
                    # Get cumulative time up to pred_lap
                    cum_time = vehicle_data['lap_time'].sum()

                    # Predict remaining laps
                    last_row = vehicle_data.iloc[-1:].copy()
                    predicted_remaining = 0

                    for future_lap in range(pred_lap + 1, max_lap + 1):
                        # Update lap and race progress
                        last_row['lap'] = future_lap
                        last_row['race_progress'] = future_lap / max_lap
                        last_row['fuel_load_estimate'] = 1.0 - (future_lap / max_lap)

                        try:
                            pred_time = model.predict(last_row)[0]
                            predicted_remaining += pred_time
                        except Exception:
                            # Use last known lap time as fallback
                            predicted_remaining += vehicle_data['lap_time'].iloc[-1]

                    total_predicted = cum_time + predicted_remaining
                    predictions.append({
                        'vehicle': int(vehicle),
                        'current_time': cum_time,
                        'predicted_remaining': predicted_remaining,
                        'total_predicted': total_predicted
                    })

            # Sort by predicted total time
            pred_df = pd.DataFrame(predictions).sort_values('total_predicted')

            # Display results
            col1, col2 = st.columns(2)

            with col1:
                predicted_winner = int(pred_df.iloc[0]['vehicle'])
                correct = predicted_winner == actual_winner
                st.metric(
                    "Predicted Winner",
                    f"#{predicted_winner}",
                    delta="✓ Correct" if correct else f"Actual: #{actual_winner}"
                )

            with col2:
                st.metric("Laps Remaining", max_lap - pred_lap)

            # Show top 5 predictions
            st.markdown("**Top 5 Predicted Finish:**")
            for i, row in pred_df.head(5).iterrows():
                vehicle = int(row['vehicle'])
                time = row['total_predicted']
                gap = time - pred_df.iloc[0]['total_predicted']
                st.write(f"P{pred_df.head().index.tolist().index(i) + 1}: #{vehicle} - {time:.1f}s (+{gap:.1f}s)")

    with tab3:
        st.subheader("Model Information")

        if model is None:
            st.warning("Model not found.")
        else:
            # Model parameters
            st.markdown("**Model Type:** Gradient Boosting Regressor")

            # Feature importances
            importances = model.get_feature_importances()

            fig = px.bar(
                importances.head(10),
                x='importance',
                y='feature',
                orientation='h',
                title="Feature Importances (Top 10)"
            )
            fig.update_layout(yaxis={'categoryorder': 'total ascending'})
            st.plotly_chart(fig, use_container_width=True)

            # Performance metrics
            st.markdown("**Performance Metrics:**")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Training RMSE", "0.81s")
                st.metric("Test RMSE", "26.26s")
            with col2:
                st.metric("Winner Accuracy", "7/8 (87.5%)")
                st.metric("Features", len(model.feature_cols))


if __name__ == "__main__":
    main()
