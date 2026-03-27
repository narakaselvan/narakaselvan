# acsl/modules/users.py
import streamlit as st
from acsl.users.add_users import add_user
from acsl.users.edit_users import edit_user

def show_users():
    st.markdown(
        """
        <h1 style='text-align: center; color: #2c3e50; font-size: 30px;'>
            👥 User Management
        </h1>
        <hr>
        """,
        unsafe_allow_html=True
    )

    # Create tabs for Add and Edit
    user_tabs = st.tabs(["➕ Add User", "✏️ Edit User"])

    with user_tabs[0]:
        add_user()

    with user_tabs[1]:
        edit_user()