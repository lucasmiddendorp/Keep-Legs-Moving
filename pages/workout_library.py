from pathlib import Path
import streamlit as st
from helpers.style import apply_global_style
from helpers.dashboard_css import inject_card_css
from helpers.workout_builder import plot_workout_summary, workout_builder_dialog
from helpers.training_plan_functions import load_workouts, workout_to_plot_steps, generate_workout_fit

apply_global_style()
inject_card_css()

# =========================================================
# Library paths and filters
# =========================================================

ROOT = Path(__file__).resolve().parent.parent
LIBRARY_PATH = ROOT / "workouts"

DURATION_RANGES = {
    "0–30 min": (0, 30),
    "30–60 min": (30, 60),
    "1–1.5 hours": (60, 90),
    "1.5–2 hours": (90, 120),
    "2–3 hours": (120, 180),
    "3+ hours": (180, float("inf")),
}

@st.cache_data
def get_library(sport, category):
    sport_path = LIBRARY_PATH / sport.lower()
    return [w for w in load_workouts(sport_path) if w.get("_category") == category]

def get_duration(workout):
    if workout.get("duration_seconds") is not None:
        return float(workout.get("duration_seconds", 0) or 0) / 60
    return sum(float(s.get("duration_seconds", 0) or 0) + float(s.get("duration_minutes", 0) or 0) * 60 for s in workout.get("steps", [])) / 60

def render_preview(workout, key, sport):
    steps = workout_to_plot_steps(workout)
    if not steps:
        return
    fig = plot_workout_summary(steps, sport=sport)
    fig.update_layout(
        height=100,
        margin=dict(l=5, r=5, t=3, b=3),
        xaxis=dict(showticklabels=False, showgrid=False, title=None),
        yaxis=dict(showticklabels=False, showgrid=False, title=None),
    )
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False}, key=key)

@st.dialog("Workout details")
def workout_details(workout, sport):
    duration = round(get_duration(workout))
    tss = float(workout.get("target_tss", workout.get("estimated_tss", 0)) or 0)
    target_if = float(workout.get("target_if", 0) or 0)
    st.subheader(workout.get("name", "Workout"))
    st.caption(f"{workout.get('_category', 'Workout')} · {duration} min · IF {target_if:.2f} · {tss:.0f} TSS")
    render_preview(workout, f"details_{workout.get('_file', workout.get('name'))}", sport)

=======
    render_preview(workout, f"details_{workout.get('_file', workout.get('name'))}", sport)
>>>>>>> Stashed changes
    try:
        fit_bytes, filename = generate_workout_fit(workout)
        st.download_button(
            "Download FIT",
            data=fit_bytes,
            file_name=filename,
            mime="application/octet-stream",
            use_container_width=True,
        )
    except Exception:
        st.warning("FIT file unavailable for this workout.")

# =========================================================
# Page header
# =========================================================

st.markdown('<div class="dashboard-title">Workout Library</div>', unsafe_allow_html=True)
st.caption("Find a workout based on the sport, type and time you have available.")

sport = st.segmented_control(
    "Sport",
    ["Cycling", "Running"],
    default="Cycling",
    key="workout_library_sport",
)

if sport is None:
    sport = "Cycling"

sport_path = LIBRARY_PATH / sport.lower()

if not sport_path.exists():
    st.warning(f"No {sport.lower()} workout library found.")
    st.stop()

categories = sorted({
    w.get("_category")
    for w in load_workouts(sport_path)
    if w.get("_category")
})

col1, col2 = st.columns(2)

with col1:
    category = st.selectbox(
        "Workout type",
        ["Select a type"] + categories,
        key="library_category",
    )

with col2:
    duration_range = st.selectbox(
        "Duration",
        ["Select a duration"] + list(DURATION_RANGES),
        key="library_duration",
    )

if category == "Select a type" or duration_range == "Select a duration":
    st.info("Select a workout type and duration to browse the library.")
    st.stop()

workouts = get_library(sport, category)
min_duration, max_duration = DURATION_RANGES[duration_range]

workouts = [
    w for w in workouts
    if min_duration <= get_duration(w) < max_duration
]

st.caption(f"{len(workouts)} workouts")

if not workouts:
    st.info("No workouts found for this type and duration.")
    st.stop()

# =========================================================
# Workout cards
# =========================================================

cols = st.columns(3, gap="small")

for i, workout in enumerate(workouts):
    with cols[i % 3]:
        duration = round(get_duration(workout))
        tss = float(workout.get("target_tss", workout.get("estimated_tss", 0)) or 0)
        target_if = float(workout.get("target_if", 0) or 0)
        st.markdown(
            f"""
            <div style="border:1px solid #e1e6ea;border-radius:10px;background:#fff;padding:10px 10px 5px;">
                <div style="font-size:13px;font-weight:700;color:#17212b;">{workout.get("name","Workout")}</div>
                <div style="font-size:10px;color:#64748B;margin-top:3px;">
                    {duration} min · IF {target_if:.2f} · {tss:.0f} TSS
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
<<<<<<< Updated upstream

        render_preview(workout, f"preview_{sport}_{i}", sport)

=======
        render_preview(workout, f"preview_{sport}_{i}", sport)
>>>>>>> Stashed changes
        if st.button(
            "View workout",
            key=f"view_{sport}_{i}",
            use_container_width=True,
        ):
            workout_details(workout, sport)