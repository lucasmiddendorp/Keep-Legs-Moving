import streamlit as st
import traceback


def debug_log(message):

    if "debug_log" not in st.session_state:
        st.session_state["debug_log"] = []

    st.session_state["debug_log"].append(str(message))


def debug_error(exc):

    if "debug_log" not in st.session_state:
        st.session_state["debug_log"] = []

    st.session_state["debug_log"].append(
        f"❌ {type(exc).__name__}: {exc}"
    )

    st.session_state["debug_log"].append(
        traceback.format_exc()
    )


def show_debug_log():

    if "debug_log" in st.session_state:

        st.subheader("🔧 Debug log")

        st.code(
            "\n".join(st.session_state["debug_log"]),
            language="text"
        )


def clear_debug_log():

    st.session_state["debug_log"] = []