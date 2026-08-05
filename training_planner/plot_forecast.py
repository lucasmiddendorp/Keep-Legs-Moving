import plotly.graph_objects as go



def create_forecast_plot(df):


    fig = go.Figure()



    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=df["CTL"],
            name="Fitness (CTL)",
            line=dict(
                color="#2563eb",
                width=3
            )
        )
    )


    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=df["ATL"],
            name="Fatigue (ATL)",
            line=dict(
                color="#ef4444",
                width=3
            )
        )
    )


    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=df["TSB"],
            name="Form (TSB)",
            line=dict(
                color="#22c55e",
                width=3
            )
        )
    )



    fig.update_layout(

        title="Fitness Forecast",

        xaxis_title="Date",

        yaxis_title="Score",

        height=450,

        plot_bgcolor="white",

        hovermode="x unified"

    )


    return fig