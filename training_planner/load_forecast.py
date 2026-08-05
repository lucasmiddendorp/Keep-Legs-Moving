import pandas as pd
from datetime import date, timedelta


def forecast_training_load(
    start_date,
    goal_date,
    ctl,
    atl,
    training_plan,
    ctl_constant=42,
    atl_constant=7
):
    """
    Forecast CTL, ATL and TSB until goal date.

    training_plan:
    [
        {
            "date": "2026-08-01",
            "tss": 80
        }
    ]

    """


    forecast = []


    tss_lookup = {
        item["date"]: item["tss"]
        for item in training_plan
    }


    current = start_date


    while current <= goal_date:


        date_string = str(current)


        # planned training stress
        tss = tss_lookup.get(
            date_string,
            0
        )


        # Update CTL
        ctl = (
            ctl +
            (tss - ctl) / ctl_constant
        )


        # Update ATL
        atl = (
            atl +
            (tss - atl) / atl_constant
        )


        tsb = ctl - atl



        forecast.append(
            {
                "date": date_string,
                "TSS": tss,
                "CTL": ctl,
                "ATL": atl,
                "TSB": tsb
            }
        )


        current += timedelta(days=1)



    return pd.DataFrame(forecast)

import plotly.graph_objects as go


def create_load_plot(forecast):

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=forecast["date"],
            y=forecast["CTL"],
            name="CTL",
            line=dict(color="#3b82f6", width=3)
        )
    )

    fig.add_trace(
        go.Scatter(
            x=forecast["date"],
            y=forecast["ATL"],
            name="ATL",
            line=dict(color="#ef4444", width=3)
        )
    )

    fig.add_trace(
        go.Scatter(
            x=forecast["date"],
            y=forecast["TSB"],
            name="TSB",
            line=dict(color="#22c55e", width=3, dash="dash")
        )
    )

    fig.update_layout(
        title="Training Load Forecast",
        height=450,
        template="plotly_white",
        hovermode="x unified",
        legend=dict(
            orientation="h",
            y=1.05,
            x=1,
            xanchor="right"
        ),
        xaxis_title="Date",
        yaxis_title="Training Load"
    )

    return fig