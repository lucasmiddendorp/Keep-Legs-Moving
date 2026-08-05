import streamlit as st
from datetime import date, timedelta


CATEGORY_COLORS = {

    "Recovery": "#9ca3af",

    "Endurance": "#3b82f6",

    "Tempo": "#22c55e",

    "Threshold": "#f97316",

    "VO2 Max": "#ef4444",

}



def render_training_week(training_plan):

    """
    Creates JOIN-style upcoming 7 day training overview.

    training_plan:

    [
        {
            "date": "2026-07-29",
            "category": "VO2 Max",
            "name": "5x5 min VO2",
            "duration": 60
        }
    ]

    """


    st.subheader(
        "Upcoming 7 Days"
    )


    cols = st.columns(7)


    today = date.today()



    for i in range(7):

        current_day = today + timedelta(days=i)

        workout = None


        for item in training_plan:

            if item["date"] == str(current_day):

                workout = item

                break



        with cols[i]:


            day_name = current_day.strftime("%a")

            day_number = current_day.strftime("%d")



            st.markdown(
                f"""
                <div style="
                    text-align:center;
                    font-weight:bold;
                ">
                    {day_name}<br>
                    {day_number}
                </div>
                """,
                unsafe_allow_html=True
            )



            if workout:


                category = workout.get(
                    "category",
                    "Endurance"
                )


                color = CATEGORY_COLORS.get(
                    category,
                    "#6b7280"
                )



                st.markdown(

                    f"""
                    <div style="
                        background-color:{color};
                        color:white;
                        border-radius:12px;
                        padding:10px;
                        height:120px;
                        text-align:center;
                        font-size:13px;
                    ">

                    <b>{category}</b>
                    <br><br>
                    {workout["name"]}
                    <br>
                    {workout["duration"]} min

                    </div>
                    """,

                    unsafe_allow_html=True

                )


            else:


                st.markdown(

                    """
                    <div style="
                        background-color:#e5e7eb;
                        color:#374151;
                        border-radius:12px;
                        padding:10px;
                        height:120px;
                        text-align:center;
                    ">
                    Rest
                    </div>
                    """,

                    unsafe_allow_html=True
                )