import streamlit as st

st.markdown("""
<style>
.circle{
    width:150px;
    height:150px;
    border-radius:50%;
    background:red;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="circle"></div>
""", unsafe_allow_html=True)