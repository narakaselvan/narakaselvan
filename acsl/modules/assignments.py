import streamlit as st
from acsl.assignments.assign_progress import show_progress, sync_dashboard
from acsl.assignments.block_assignments import block_assign
from acsl.assignments.synch_assignments import synchronize
from acsl.assignments.sync_status import sync_result
from acsl.assignments.reassign_assignments import re_assign
from acsl.assignments.custom_assignment import custom_assign
from acsl.assignments.recall_assignments_from_interviewer import recall_blocks

def show_assignments():

    me = st.session_state.get("login")

    if "logged_in" not in st.session_state:
        st.error("User not logged in")
        st.stop()

    sub_tabs=st.tabs(["Summary","Blocks", "Custom", "Reassign","Recall", "Synchronize", "Sync Progress","Sync Queue Monitor"])

    with sub_tabs[0]:
        show_progress(me)

    with sub_tabs[1]:
        block_assign(me)

    with sub_tabs[2]:
        custom_assign(me)

    with sub_tabs[3]:
        re_assign(me)

    with sub_tabs[4]:
        recall_blocks(me)

    with sub_tabs[5]:
        synchronize()

    with sub_tabs[6]:
        sync_result()

    with sub_tabs[7]:
        sync_dashboard(me)