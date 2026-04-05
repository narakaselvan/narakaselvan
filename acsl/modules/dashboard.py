import streamlit as st
from acsl.assignments.assignments_dashboard import show_assignment_dashboard
from acsl.interviews.interwiew_progress import show_interview_progress
from acsl.users.track_user_activity import show_track_user_activity
from acsl.modules.overall import show_overall_progress
from acsl.modules.completion import show_overall_completion

def show_dashboard():

    sub_tabs=st.tabs(["Completion","Overall","Assignments", "Interviews","Users"])

    with sub_tabs[0]:
        show_overall_completion()
    
    with sub_tabs[1]:
        show_overall_progress()    

    with sub_tabs[2]:
        show_assignment_dashboard()

    with sub_tabs[3]:
        show_interview_progress()

    with sub_tabs[4]:
        show_track_user_activity()