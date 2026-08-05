import streamlit as st
from datetime import date

from training_planner.models import Athlete, Goal
from training_planner.planner import TrainingPlanner
from training_planner.training_plot import render_training_week
from training_planner.load_forecast import forecast_training_load, create_load_plot
from helpers.training_saver import save_training_plan, load_training_plan
from Strava.strava_user import get_training_goal, get_user_settings
from helpers.availability import load_availability
from helpers.metrics import calculate_training_load
import Strava.strava_config as strava_config



st.title("📅 Training Plan")

username = st.session_state["username"]

settings = get_user_settings(username)

availability = load_availability(username)


daily = calculate_training_load(
    username,
    settings["ftp"],
    strava_config.CTL_TIME_CONSTANT,
    strava_config.ATL_TIME_CONSTANT
)

if daily is None or daily.empty:
    st.warning(
        "No training data available yet."
    )
    st.stop()

ctl = daily["CTL"].iloc[-1]
atl = daily["ATL"].iloc[-1]
tsb = daily["TSB"].iloc[-1]

st.subheader("Current Training Status")

col1, col2, col3 = st.columns(3)

col1.metric(
    "Fitness (CTL)",
    f"{ctl:.0f}"
)

col2.metric(
    "Fatigue (ATL)",
    f"{atl:.0f}"
)

col3.metric(
    "Form (TSB)",
    f"{tsb:.0f}"
)

st.divider()

training_goal = get_training_goal(username)

if training_goal["name"] is None:
    st.info(
        "No training plan selected. Select a goal in Settings → Training Goal."
    )
    st.stop()

goal = Goal(
    name=training_goal["name"],
    race_date=date.fromisoformat(
        training_goal["goal_date"]
    ),
    priority="A"
)
st.write(daily.tail(7))
st.write(daily.tail(7).reset_index().columns)
history = daily.tail(7).reset_index().rename(columns={"index": "Date"}).to_dict("records")

athlete = Athlete(
    ftp=settings["ftp"],
    ctl=ctl,
    atl=atl,
    tsb=tsb,
    history=history,
    availability=availability,
    level=settings.get(
        "level",
        "Advanced"
    )
)

plan = load_training_plan(username)

if plan is None:

    st.info(
        "No training plan generated yet."
    )

else:

    weekly_plan = plan[:7]

    render_training_week(
        weekly_plan
    )

    st.divider()

    today_workout = weekly_plan[0]

    st.subheader(
        "Today's Workout"
    )

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Workout",
        today_workout["name"]
    )

    col2.metric(
        "Duration",
        f"{today_workout['duration']} min"
    )

    col3.metric(
        "Intensity",
        f"{today_workout['if']:.2f}"
    )

    st.write(
        f"Category: **{today_workout['category']}**"
    )

    st.write(
        f"Training Stress: **{today_workout['tss']} TSS**"
    )

    forecast = forecast_training_load(
        start_date=date.today(),
        goal_date=goal.race_date,
        ctl=ctl,
        atl=atl,
        training_plan=plan
    )

    fig = create_load_plot(
        forecast
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

if st.button(
    "Update Training Plan",
    type="primary"
):

    planner = TrainingPlanner(
        athlete,
        goal
    )

    plan = planner.generate_plan_until_goal()

    save_training_plan(
        username,
        plan
    )

    st.success(
        "Training plan updated."
    )

    st.rerun()