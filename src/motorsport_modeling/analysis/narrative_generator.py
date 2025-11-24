"""
LLM-based Narrative Generator for Comparative Analysis

Uses GPT-4o to generate professional, contextual narratives from structured metrics.
"""

import os
from typing import Optional
from pathlib import Path
from openai import OpenAI
from .comparative import DriverMetrics


def _load_env_file():
    """Load .env file if it exists."""
    env_path = Path('.env')
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()


def generate_comparative_narrative(
    metrics: DriverMetrics,
    api_key: Optional[str] = None,
    model: str = "gpt-4o"
) -> str:
    """
    Generate professional narrative from driver performance metrics using GPT-4o.

    Args:
        metrics: DriverMetrics object with computed performance data
        api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
        model: OpenAI model to use (default: gpt-4o)

    Returns:
        Professional 2-3 sentence analysis string

    Raises:
        ValueError: If API key not provided and not in environment
    """
    # Load .env file if present
    _load_env_file()

    # Get API key - try Streamlit secrets first, then environment
    if api_key is None:
        try:
            import streamlit as st
            api_key = st.secrets.get("OPENAI_API_KEY")
        except (ImportError, FileNotFoundError, KeyError):
            api_key = os.environ.get("OPENAI_API_KEY")

    if not api_key:
        raise ValueError(
            "OpenAI API key required. Set OPENAI_API_KEY environment variable "
            "or pass api_key parameter."
        )

    # Initialize client
    client = OpenAI(api_key=api_key)

    # Build structured prompt
    prompt = _build_prompt(metrics)

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": _get_system_prompt()
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            max_tokens=300,
            temperature=0.7,
        )
        narrative = response.choices[0].message.content.strip()
        return narrative

    except Exception as e:
        # Fallback to template-based narrative if LLM fails
        print(f"Warning: LLM narrative generation failed: {e}")
        return _fallback_narrative(metrics)


def _get_system_prompt() -> str:
    """Get system prompt defining narrative style and requirements."""
    return """You are an expert motorsport analyst providing performance feedback to professional race car drivers.

Your analysis should be:
1. DATA-DRIVEN: Base insights strictly on the provided metrics, no speculation
2. SPECIFIC: Provide concrete numbers and actionable insights
3. PROFESSIONAL: Use proper motorsport terminology, avoid casual language
4. CONCISE: 2-3 sentences maximum
5. ACTIONABLE: Focus on technical factors (tire management, setup, traffic) not effort

AVOID:
- Suggesting drivers "push harder" or "try harder"
- Vague statements like "could improve"
- Emotional language or excessive praise
- Speculation about factors not in the data

FOCUS ON:
- Comparing to field benchmarks (median, top 5, leaders)
- Identifying PRIMARY performance gap (degradation, traffic, baseline pace)
- Quantifying potential gains with realistic estimates
- Technical solutions (tire technique, setup, strategy)"""


def _build_prompt(metrics: DriverMetrics) -> str:
    """Build data-rich prompt from metrics using beat-the-driver-ahead approach."""

    # For P1, compare to P2 to show what made them faster
    if metrics.final_position == 1:
        ahead_info = ""
        if metrics.ahead_vehicle is not None:
            stint_analysis = []

            # Analyze which stint was the advantage
            if metrics.ahead_early_pace is not None:
                early_diff = metrics.early_pace - metrics.ahead_early_pace  # Negative = we were faster
                mid_diff = metrics.mid_pace - metrics.ahead_mid_pace if metrics.ahead_mid_pace else 0
                late_diff = metrics.late_pace - metrics.ahead_late_pace if metrics.ahead_late_pace else 0

                if abs(early_diff) > 0.1:
                    stint_analysis.append(f"Early: {early_diff:+.2f}s/lap")
                if abs(mid_diff) > 0.1:
                    stint_analysis.append(f"Mid: {mid_diff:+.2f}s/lap")
                if abs(late_diff) > 0.1:
                    stint_analysis.append(f"Late: {late_diff:+.2f}s/lap")

            ahead_info = f"""
COMPARISON TO P2 (#{metrics.ahead_vehicle}):
- Winning margin: {abs(metrics.gap_to_ahead):.1f}s
- Average pace advantage: {-metrics.ahead_pace_delta:+.2f}s/lap (negative = we were faster)
- Stint-by-stint: {', '.join(stint_analysis) if stint_analysis else 'Similar pace across stints'}
- Degradation advantage: {-metrics.ahead_deg_delta:+.3f}s/lap (negative = we degraded less)
"""

        prompt = f"""Analyze the WINNING driver's performance vs P2:

DRIVER: #{metrics.vehicle_number}
FINAL RESULT: P1 (Winner)

OUR PACE BY STINT:
- Early stint (laps 1-5): {metrics.early_pace:.2f}s average
- Mid stint (laps 6-15): {metrics.mid_pace:.2f}s average
- Late stint (lap 16+): {metrics.late_pace:.2f}s average

OUR TIRE DEGRADATION:
- Degradation rate: {metrics.driver_deg:+.3f}s/lap
- Field average: {metrics.field_deg:+.3f}s/lap

OUR TRAFFIC:
- Laps in traffic: {metrics.traffic_laps}
{ahead_info}

Generate a 2-3 sentence professional analysis identifying:
1. The PRIMARY factor that gave us the victory over P2
2. QUANTIFIED advantage (in seconds) from this factor
3. Whether the win was dominant (large margin) or closely fought

Be direct and data-focused."""

    else:
        # For all other positions, compare to driver ahead
        ahead_info = ""
        if metrics.ahead_vehicle is not None:
            stint_analysis = []

            # Analyze which stint was the problem
            if metrics.ahead_early_pace is not None:
                early_diff = metrics.early_pace - metrics.ahead_early_pace
                mid_diff = metrics.mid_pace - metrics.ahead_mid_pace if metrics.ahead_mid_pace else 0
                late_diff = metrics.late_pace - metrics.ahead_late_pace if metrics.ahead_late_pace else 0

                if abs(early_diff) > 0.1:
                    stint_analysis.append(f"Early: {early_diff:+.2f}s/lap")
                if abs(mid_diff) > 0.1:
                    stint_analysis.append(f"Mid: {mid_diff:+.2f}s/lap")
                if abs(late_diff) > 0.1:
                    stint_analysis.append(f"Late: {late_diff:+.2f}s/lap")

            ahead_info = f"""
COMPARISON TO DRIVER AHEAD (#{metrics.ahead_vehicle} in P{metrics.final_position-1}):
- Gap to ahead at finish: {metrics.gap_to_ahead:.1f}s
- Average pace delta: {metrics.ahead_pace_delta:+.2f}s/lap (negative = we were slower)
- Stint-by-stint gaps: {', '.join(stint_analysis) if stint_analysis else 'Similar pace across stints'}
- Degradation delta: {metrics.ahead_deg_delta:+.3f}s/lap (positive = we degraded more)
- Traffic laps delta: {metrics.ahead_traffic_delta:+d} laps (positive = we had more traffic)
"""

        prompt = f"""Analyze this driver's race performance by comparing to the driver who finished DIRECTLY AHEAD:

DRIVER: #{metrics.vehicle_number}
FINAL RESULT: P{metrics.final_position}, {metrics.gap_to_winner:.1f}s behind winner

OUR PACE BY STINT:
- Early stint (laps 1-5): {metrics.early_pace:.2f}s average
- Mid stint (laps 6-15): {metrics.mid_pace:.2f}s average
- Late stint (lap 16+): {metrics.late_pace:.2f}s average

OUR TIRE DEGRADATION:
- Degradation rate: {metrics.driver_deg:+.3f}s/lap
- Field average: {metrics.field_deg:+.3f}s/lap

OUR TRAFFIC:
- Laps in traffic: {metrics.traffic_laps}
- Estimated time cost: {metrics.traffic_cost:.1f}s total
{ahead_info}

Generate a 2-3 sentence professional analysis identifying:
1. The PRIMARY factor that caused us to finish behind #{metrics.ahead_vehicle if metrics.ahead_vehicle else 'the driver ahead'}
2. SPECIFIC, QUANTIFIED gap (in seconds) that this factor caused
3. ACTIONABLE technical solution (tire management, pace in specific stints, traffic management)

Focus on THE KEY DIFFERENCE that cost the position. Be direct and data-focused."""

    return prompt


def _fallback_narrative(metrics: DriverMetrics) -> str:
    """Generate template-based narrative as fallback if LLM fails."""

    # Calculate degradation cost
    deg_cost = metrics.deg_delta * 15 if metrics.deg_delta > 0 else 0

    # Determine primary issue
    if abs(deg_cost) > abs(metrics.traffic_cost) and abs(deg_cost) > 3.0:
        return (
            f"Tire degradation was the primary performance limiter, with a "
            f"{metrics.driver_deg:.2f}s/lap degradation rate exceeding the field "
            f"average of {metrics.field_deg:.2f}s/lap. This cost approximately "
            f"{deg_cost:.1f}s over the stint. Tire management technique or setup "
            f"optimization could yield {deg_cost * 0.6:.1f}-{deg_cost * 0.8:.1f}s "
            f"without sacrificing qualifying pace."
        )
    elif metrics.traffic_cost > 2.0:
        return (
            f"Traffic on {metrics.traffic_laps} laps cost {metrics.traffic_cost:.1f}s "
            f"total. Better qualifying position or strategic timing could have avoided "
            f"most of this loss. Baseline pace relative to top 5 was "
            f"{metrics.delta_vs_top5:+.2f}s/lap, suggesting the primary focus should "
            f"be on qualifying performance."
        )
    else:
        return (
            f"Pace relative to top 5 averaged {metrics.delta_vs_top5:+.2f}s/lap. "
            f"Degradation ({metrics.driver_deg:.2f}s/lap) was close to field average "
            f"({metrics.field_deg:.2f}s/lap). The performance gap suggests opportunities "
            f"in setup optimization or driving technique to find {abs(metrics.delta_vs_top5) * 15:.1f}-"
            f"{abs(metrics.delta_vs_top5) * 20:.1f}s over the race distance."
        )


def generate_narrative_batch(
    metrics_list: list[DriverMetrics],
    api_key: Optional[str] = None,
    model: str = "gpt-4o",
    verbose: bool = True
) -> list[str]:
    """
    Generate narratives for multiple drivers (batch processing).

    Args:
        metrics_list: List of DriverMetrics objects
        api_key: OpenAI API key
        model: Model to use
        verbose: Print progress

    Returns:
        List of narrative strings (same order as input)
    """
    narratives = []

    for i, metrics in enumerate(metrics_list):
        if verbose:
            print(f"Generating narrative {i+1}/{len(metrics_list)} for driver #{metrics.vehicle_number}...")

        try:
            narrative = generate_comparative_narrative(metrics, api_key, model)
            narratives.append(narrative)
        except Exception as e:
            print(f"  Warning: Failed for driver #{metrics.vehicle_number}: {e}")
            narratives.append(_fallback_narrative(metrics))

    return narratives
