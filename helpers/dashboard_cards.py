import streamlit as st
import pandas as pd
from textwrap import dedent
import streamlit.components.v1 as components


def _safe_number(value, default=0.0):
    try:
        if pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default



def render_metric_circle(title, value, percentage, subtitle, color):

    percentage = max(0, min(float(percentage), 100))
    value = float(value)

    components.html(
        dedent(
            f"""
            <style>
                .metric-wrapper {{
                    text-align: center;
                    font-family: "DM Sans", "Segoe UI", sans-serif;
                }}
                .metric-ring {{
                    width: 150px;
                    height: 150px;
                    border-radius: 50%;
                    background: #e6ebef;
                    border: 10px solid #e6ebef;
                    border-top-color: {color};
                    border-right-color: {color};
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    margin: 0 auto;
                }}
                .metric-inner {{
                    width: 120px;
                    height: 120px;
                    border-radius: 50%;
                    background: white;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    box-shadow: 0 2px 8px rgba(23, 33, 43, 0.06);
                }}
                .metric-value {{
                    font-size: 32px;
                    font-weight: 800;
                    color: #17212b;
                }}
                .metric-title {{
                    margin-top: 15px;
                    font-size: 15px;
                    font-weight: 700;
                    color: #526170;
                    text-transform: uppercase;
                    letter-spacing: 0.08em;
                }}
                .metric-subtitle {{
                    margin-top: 5px;
                    color: #6b7785;
                    font-size: 14px;
                }}
            </style>
            <div style="
                display: flex;
                flex-direction: column;
                align-items: center;
            ">
                <div class="metric-wrapper">
                    <div class="metric-ring">
                        <div class="metric-inner">
                            <div class="metric-value">{value:.0f}</div>
                        </div>
                    </div>
                    <div class="metric-title">{title}</div>
                    <div class="metric-subtitle">{subtitle}</div>
                </div>
            </div>
            """
        ),
        height=190
    )



def render_readiness_card(label, note, color):

    components.html(
        dedent(
            f"""
            <style>
                .modern-card {{
                    background: white;
                    border-radius: 8px;
                    padding: 20px;
                    height: 100%;
                    border: 1px solid #dfe5ea;
                    box-shadow: 0 2px 8px rgba(23,33,43,.04);
                    font-family: "DM Sans", "Segoe UI", sans-serif;
                }}
                .card-title {{
                    font-size: 14px;
                    font-weight: 700;
                    color: #6b7785;
                    text-transform: uppercase;
                    letter-spacing: 0.04em;
                }}
                .card-main {{
                    margin-top: 12px;
                    font-size: 28px;
                    font-weight: 800;
                }}
                .card-note {{
                    margin-top: 8px;
                    color: #6b7785;
                    font-size: 14px;
                }}
            </style>
            <div class="modern-card">

                <div class="card-title">
                    Today's Readiness
                </div>

                <div class="card-main"
                style="color:{color}">
                    {label}
                </div>

                <div class="card-note">
                    {note}
                </div>

            </div>
            """
        ),
        height=170,
    )



def render_fatigue_card(fatigue_label, atl, delta):

    colors = {
        "Low":"#22c55e",
        "Moderate":"#eab308",
        "High":"#f97316",
    }

    color = colors.get(
        fatigue_label,
        "#ef4444"
    )


    components.html(
        dedent(
            f"""
            <style>
                .modern-card {{
                    background: white;
                    border-radius: 8px;
                    padding: 20px;
                    height: 100%;
                    border: 1px solid #dfe5ea;
                    box-shadow: 0 2px 8px rgba(23,33,43,.04);
                    font-family: "DM Sans", "Segoe UI", sans-serif;
                }}
                .card-title {{
                    font-size: 14px;
                    font-weight: 700;
                    color: #6b7785;
                    text-transform: uppercase;
                    letter-spacing: 0.04em;
                }}
                .card-main {{
                    margin-top: 12px;
                    font-size: 28px;
                    font-weight: 800;
                }}
                .card-note {{
                    margin-top: 8px;
                    color: #6b7785;
                    font-size: 14px;
                }}
            </style>
            <div class="modern-card">

                <div class="card-title">
                    Fatigue Level
                </div>

                <div class="card-main"
                style="color:{color}">
                    {fatigue_label}
                </div>

                <div class="card-note">
                    ATL {atl:.1f} · {delta:+.1f} this week
                </div>

            </div>
            """
        ),
        height=170,
    )



def render_ramp_card(ramp_label, ramp_rate, position):

    components.html(
        dedent(
            f"""
            <style>
                .modern-card {{
                    background: white;
                    border-radius: 8px;
                    padding: 20px;
                    height: 100%;
                    border: 1px solid #dfe5ea;
                    box-shadow: 0 2px 8px rgba(23,33,43,.04);
                    font-family: "DM Sans", "Segoe UI", sans-serif;
                }}
                .card-title {{
                    font-size: 14px;
                    font-weight: 700;
                    color: #6b7785;
                    text-transform: uppercase;
                    letter-spacing: 0.06em;
                }}
                .card-main {{
                    margin-top: 12px;
                    font-size: 28px;
                    font-weight: 800;
                }}
                .card-note {{
                    margin-top: 8px;
                    color: #6b7785;
                    font-size: 14px;
                }}
                .ramp-container {{
                    display: flex;
                    gap: 5px;
                    margin-top: 25px;
                }}
                .ramp-segment {{
                    height: 8px;
                    flex: 1;
                    border-radius: 20px;
                }}
                .ramp-segment:nth-child(1) {{ background: #ddd6fe; }}
                .ramp-segment:nth-child(2) {{ background: #c4b5fd; }}
                .ramp-segment:nth-child(3) {{ background: #a78bfa; }}
                .ramp-segment:nth-child(4) {{ background: #2f6f8f; }}
                .ramp-labels {{
                    display: flex;
                    justify-content: space-between;
                    margin-top: 8px;
                    color: #6b7785;
                    font-size: 12px;
                }}
            </style>
            <div class="modern-card">

                <div class="card-title">
                    Fitness Momentum
                </div>


                <div class="card-main"
                style="color:#2f6f8f">
                    {ramp_label}
                </div>


                <div class="card-note">
                    {ramp_rate:+.2f} CTL/day over last 7 days
                </div>


                <div class="ramp-container">

                    <div class="ramp-segment"></div>
                    <div class="ramp-segment"></div>
                    <div class="ramp-segment"></div>
                    <div class="ramp-segment"></div>

                </div>


                <div class="ramp-labels">
                    <span>Recover</span>
                    <span>Build</span>
                    <span>Productive</span>
                    <span>Hard</span>
                </div>


            </div>
            """
        ),
        height=220
    )