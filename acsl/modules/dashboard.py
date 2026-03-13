import streamlit as st
from acsl.assignments.assignments_dashboard import assignments_dashboard

def show_dashboard():

    sub_tabs=st.tabs(["Assignments", "Interviews","Users"])

    with sub_tabs[0]:
        assignments_dashboard()

    with sub_tabs[1]:
        st.write("This is test interviews")

    with sub_tabs[2]:
        st.write("This is test Users")