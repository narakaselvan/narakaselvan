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
# SIDEBAR HEADER & LOGOUT
# --------------------------------------------------
st.sidebar.write(f"👤 **Logged in as:** {st.session_state.user}")
st.sidebar.write(f"🏷️ **Role:** {str(st.session_state.role).capitalize()}")

if st.sidebar.button("Logout"):
    st.session_state.clear()
    st.rerun()

st.sidebar.markdown("---")

# --------------------------------------------------
# ROLE-BASED ACCESS CONTROL (RBAC)
# --------------------------------------------------
current_role = str(st.session_state.role).lower().strip() if st.session_state.role else ""

# 1. Menus available to ALL roles (Added "User Management" here)
allowed_menus = ["Dashboard", "User Management"]

# 2. Add restricted menus based on the specific role
if current_role == "admin":
    allowed_menus.insert(0, "Admin") 
    
elif current_role == "supervisor":
    allowed_menus.append("Assignments Management")
    
elif current_role in ["headquarters", "admin"]:
    allowed_menus.append("Data Analysis")
    allowed_menus.append("Quality Control")

# --------------------------------------------------
# MENU DISPLAY LOGIC
# --------------------------------------------------
if len(allowed_menus) == 1:
    menu = allowed_menus[0]
    st.sidebar.info(f"📌 Current Module: **{menu}**")
else:
    menu = st.sidebar.selectbox("🧭 Navigation Menu", allowed_menus)

# --------------------------------------------------
# ROUTING TO MODULES
# --------------------------------------------------
if menu == "Admin":
    show_admin()

elif menu == "User Management":
    # Call the new shared module we created!
    show_users() 

elif menu == "Assignments Management":
    show_assignments()

elif menu == "Dashboard":
    show_dashboard()

elif menu == "Data Analysis":
    show_analysis()
   
elif menu == "Quality Control":
    show_quality()