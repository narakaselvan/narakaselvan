import streamlit as st
from acsl.assignments.assignments_dashboard import show_assignment_dashboard
from acsl.interviews.interwiew_progress import show_interview_progress

def show_dashboard():

    sub_tabs=st.tabs(["Assignments", "Interviews","Users"])

    with sub_tabs[0]:
        show_assignment_dashboard()

    with sub_tabs[1]:
        show_interview_progress()

    with sub_tabs[2]:
        st.write("This is test Users")