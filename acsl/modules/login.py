import streamlit as st
import bcrypt
from acsl.db import run_query
import psycopg2

# Special login credentials
SPECIAL_USER = "Kalaichelvan"
SPECIAL_PASSWORD = "O4976|574d"


def show_login():

    st.markdown(
    """
    <h1 style='text-align: center; color: darkgreen; font-size: 50px;'>
        Economic Census 2025/26 (Agriculture)
    </h1>
    """,
    unsafe_allow_html=True
    )

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")

    if submit:

        user = None

        # Try normal database login
        try:
            result = run_query(
                "SELECT * FROM susouser WHERE login=%s AND is_active='true'",
                (username,)
            )
            if result:
                user = result[0]

        except psycopg2.errors.UndefinedTable:
            st.warning("User table not found. Attempting special login...")

        except Exception as e:
            st.error(f"Database error: {e}")
            return

        # -------------------------------
        # Normal login
        # -------------------------------
        if user:
            stored_password = user["password"]
            if isinstance(stored_password, str):
                stored_password = stored_password.encode()

            if not bcrypt.checkpw(password.encode(), stored_password):
                st.error("Invalid password")
                return

            st.session_state.logged_in = True
            st.session_state.user = user["login"]
            st.session_state.role = user["role"].lower()
            st.session_state.workingarea = user["workingarea"]
            st.session_state["login"] = username  # username from login form

            st.success(f"Welcome {user['login']}")
            st.rerun()
            return

        # -------------------------------
        # Special login (plain text)
        # -------------------------------
        if username == SPECIAL_USER and password == SPECIAL_PASSWORD:
            st.session_state.logged_in = True
            st.session_state.user = SPECIAL_USER
            st.session_state.role = "headquarters"
            st.session_state.workingarea = "0000000"

            st.success(f"Special login activated ({SPECIAL_USER})")
            st.rerun()
            return

        # -------------------------------
        # Login failed
        # -------------------------------
        st.error("User not found or invalid password")

    st.markdown(
    """
    <h1 style='text-align: center; color: darkblue; font-size:14px;'>
        Powered by: ICT Division, Department of Census and Statistics
    </h1>
    """,
    unsafe_allow_html=True
)