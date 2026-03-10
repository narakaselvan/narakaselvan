import streamlit as st
from acsl.assignments.assign_progress import assign_progress


def show_assignments():

    if "logged_in" not in st.session_state:
        st.error("User not logged in")
        st.stop()

    sub_tabs=st.tabs(["Progress","Block_Assign", "Custom_Assign", "Re_Assign","Synchronize"])

    with sub_tabs[0]:
        assign_progress()

    with sub_tabs[1]:
        st.write("This is Block wise Assignment")

    with sub_tabs[2]:
        st.write("This is custom Assignment")

    with sub_tabs[3]:
        st.write("This is Reassign Assignment")

    with sub_tabs[4]:
        st.write("This is Synchronize the Assignment")