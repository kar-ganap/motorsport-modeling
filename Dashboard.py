"""
RaceCraft AI - Toyota Gazoo Racing Analytics Platform

Multi-page dashboard with:
- Race Analytics: Real-time driver coaching and race strategy
- Model Validation: Performance analysis across all races

Run with: uv run streamlit run Dashboard.py
"""

import streamlit as st

# Page config
st.set_page_config(
    page_title="RaceCraft AI",
    page_icon="🏎️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Enhanced CSS
st.markdown("""
<style>
    /* Hide default streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display:none;}

    /* Sidebar navigation styling */
    [data-testid="stSidebarNav"] {
        padding-top: 2rem;
    }

    [data-testid="stSidebarNav"] ul {
        padding: 0;
    }

    [data-testid="stSidebarNav"] li {
        margin-bottom: 0.5rem;
    }

    /* Increase font size and capitalize sidebar page links */
    [data-testid="stSidebarNav"] li a,
    [data-testid="stSidebarNav"] li a span,
    [data-testid="stSidebarNav"] li div {
        font-size: 20px !important;
        font-weight: 600 !important;
        text-transform: capitalize !important;
        line-height: 1.6 !important;
    }

    [data-testid="stSidebarNav"] li a:hover {
        background-color: rgba(102, 126, 234, 0.1) !important;
    }

    /* Force larger font on sidebar navigation text */
    section[data-testid="stSidebar"] nav a {
        font-size: 20px !important;
        font-weight: 600 !important;
    }

    /* Hero section */
    .hero {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 60px 40px;
        border-radius: 15px;
        color: white;
        text-align: center;
        margin-bottom: 40px;
    }

    .hero h1 {
        font-size: 3.5em;
        margin-bottom: 10px;
        font-weight: 700;
    }

    .hero p {
        font-size: 1.3em;
        opacity: 0.95;
    }

    /* Feature cards */
    .feature-card {
        background: white;
        padding: 30px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        border-left: 4px solid #667eea;
        margin-bottom: 20px;
    }

    .feature-card h3 {
        color: #667eea;
        margin-bottom: 10px;
    }

    .feature-card p {
        color: #64748b;
        line-height: 1.6;
    }
</style>
""", unsafe_allow_html=True)

# Hero section
st.markdown("""
<div class="hero">
    <h1>🏎️ RaceCraft AI</h1>
    <p>Data-driven coaching and strategy for Toyota Gazoo Racing</p>
</div>
""", unsafe_allow_html=True)

# Introduction
st.markdown("""
Welcome to the RaceCraft AI analytics platform. Use the sidebar to navigate between:

### 📊 Race Analytics
Real-time driver coaching with predictive insights:
- Live race position tracking and gap analysis
- Next-lap performance predictions
- Driver state monitoring and fatigue detection
- Actionable coaching messages

### 🎯 Model Validation
Comprehensive model performance analysis:
- Prediction accuracy across all 14 races
- Position-weighted error metrics
- Top-5 finish prediction tracking
- Per-driver breakdown and diagnostics

""")

# Quick stats
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
    <div class="feature-card">
        <h3>14 Races</h3>
        <p>Complete data from 7 tracks (2 races each)</p>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="feature-card">
        <h3>~25 Drivers</h3>
        <p>Individual performance profiles and predictions</p>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown("""
    <div class="feature-card">
        <h3>Real-time AI</h3>
        <p>Sub-second predictions during live racing</p>
    </div>
    """, unsafe_allow_html=True)

# Getting started
st.markdown("---")
st.markdown("### 🚀 Getting Started")
st.info("""
1. Navigate to **Race Analytics** from the sidebar to view real-time race coaching
2. Use **Model Validation** to explore prediction accuracy and model performance
3. Select different tracks and races to compare performance across events
""")
