import streamlit as st
import bcrypt
from acsl.db import run_query
import psycopg2

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

        # -------------------------------
        # Database Authentication
        # -------------------------------
        try:
            result = run_query(
                "SELECT * FROM susouser WHERE login=%s AND is_active='true'",
                (username,)
            )
            if result:
                user = result[0]

        except psycopg2.errors.UndefinedTable:
            st.error("Authentication system unavailable (User table not found). Please contact the administrator.")
            return
        except Exception as e:
            st.error(f"Database error: {e}")
            return

        # -------------------------------
        # Credential Verification
        # -------------------------------
        if user:
            stored_password = user["password"]
            
            # Ensure the stored hash is in bytes for bcrypt
            if isinstance(stored_password, str):
                stored_password = stored_password.encode('utf-8')

            # Verify the typed password against the hash
            if not bcrypt.checkpw(password.encode('utf-8'), stored_password):
                st.error("Invalid password")
                return

            # Login successful: Set session states
            st.session_state.logged_in = True
            st.session_state.user = user["login"]
            st.session_state.role = user["role"].lower()
            st.session_state.workingarea = user["workingarea"]
            st.session_state["login"] = username  # username from login form

            st.success(f"Welcome {user['login']}!")
            st.rerun()
            return

        # -------------------------------
        # Login failed (User not found or inactive)
        # -------------------------------
        st.error("User not found, inactive, or invalid credentials.")

    # Footer
    st.markdown(
        """
        <h1 style='text-align: center; color: darkblue; font-size:14px;'>
            Powered by: ICT Division, Department of Census and Statistics
        </h1>
        """,
        unsafe_allow_html=True
    )