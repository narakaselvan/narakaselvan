import streamlit as st
import bcrypt
from acsl.db import run_query


def show_login():

    st.title("ACSL2026 Login")

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")

    if submit:

        result = run_query(
            "SELECT * FROM susouser WHERE login=%s",
            (username,)
        )

        if not result:
            st.error("User not found")
            return

        user = result[0]

        stored_password = user["password"]

        if isinstance(stored_password, str):
            stored_password = stored_password.encode()

        if not bcrypt.checkpw(password.encode(), stored_password):
            st.error("Invalid password")
            return

        # ✅ Set session values
        st.session_state.logged_in = True
        st.session_state.user = user["login"]
        st.session_state.role = user["role"].lower()
        st.session_state.workingarea = user["workingarea"]

        st.rerun()