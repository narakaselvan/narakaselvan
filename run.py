# run.py

import streamlit as st
from acsl.modules.dashboard import show_dashboard
from acsl.modules.analysis import show_analysis
from acsl.modules.assignments import show_assignments
from acsl.modules.quality import show_quality
from acsl.modules.users import show_users
from acsl.modules.logs import show_logs
from acsl.modules.admin import show_admin
from acsl.modules.login import show_login

import streamlit as st

# --------------------------------------------------
# SESSION INITIALIZATION
# --------------------------------------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "user" not in st.session_state:
    st.session_state.user = None

if "role" not in st.session_state:
    st.session_state.role = None

if "workingarea" not in st.session_state:
    st.session_state.workingarea = None

# --------------------------------------------------
# LOGIN PROTECTION
# --------------------------------------------------

if not st.session_state.logged_in:
    show_login()
    st.stop()

# --------------------------------------------------
# MAIN APPLICATION TABS
# --------------------------------------------------

st.sidebar.write(f"Logged in as: {st.session_state.user}")
if st.sidebar.button("Logout"):
    st.session_state.clear()
    st.rerun()

menu = st.sidebar.selectbox(
    "Menu", ["Admin", "Assignments Management","Dashboard", "Data Analysis", "Quality Control", "User Management", "Activity Log"]
)

if menu == "Admin":
    show_admin()

if menu =="Assignments Management":
    show_assignments()

if menu =="Dashboard":
    show_dashboard()

if menu =="Data Analysis":
    show_analysis()
   
if menu =="Quality Control":
    show_quality()

if menu =="User Management":
    show_users()

if menu =="Activity Log":
     show_logs()

# tabs = st.tabs([
#     "Admin",
#     "Assignments Management",
#     "Dashboard",
#     "Data Analysis",
#     "Quality Control",
#     "User Management",
#     "Activity Log"
# ])

# with tabs[0]:
#     show_admin()

# with tabs[1]:
#     show_assignments()

# with tabs[2]:
#     show_dashboard()

# with tabs[3]:
#     show_analysis()
   
# with tabs[4]:
#     show_quality()

# with tabs[5]:
#     show_users()

# with tabs[6]:
#      show_logs()