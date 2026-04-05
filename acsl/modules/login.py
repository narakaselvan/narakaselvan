import streamlit as st
import bcrypt
from acsl.db import run_query
import psycopg2

def show_login():
    # -------------------------------------------------
    # CUSTOM CSS: Hide Streamlit Header, Footer, and remove top space
    # -------------------------------------------------
    hide_streamlit_style = """
    <style>
        #MainMenu {visibility: hidden;}
        header {visibility: hidden;}
        footer {visibility: hidden;}
        .stDeployButton {display:none;}
        /* NEW: Target the main content block and remove top padding/margin */
        .block-container {
            padding-top: 0rem;
            padding-bottom: 1rem;
            padding-left: 1rem;
            padding-right: 1rem;
        }
        /* Further reduce padding for the main area itself if needed */
        .stApp > header {
            padding-top: 0rem;
            padding-bottom: 0rem;
        }
        .stApp {
            margin-top: 0rem;
        }
    </style>
    """
    st.markdown(hide_streamlit_style, unsafe_allow_html=True)

    # -------------------------------------------------
    # LOGIN UI LAYOUT
    # -------------------------------------------------
    # Use columns to squeeze the login box into the middle of the screen
    col1, col2, col3 = st.columns([1, 1.5, 1])

    with col2:
        # Attractive Header with exact requested font sizes
        st.markdown(
            """
            <div style='text-align: center; margin-top: 20px; margin-bottom: 20px;'>
                <h1 style='color: #2e7d32; font-size: 20px; margin-bottom: 0px;'>🌾 Economic Census 2025/26</h1>
                <h5 style='color: red; font-size: 15px; margin-top: 1px; font-weight: normal;'>Agriculture Activities</h5>
            </div>
            """,
            unsafe_allow_html=True
        )

        # The Form Container
        with st.form("login_form", clear_on_submit=False):
            # Form Title
            st.markdown(
                "<h4 style='text-align: center; color: #333; font-size: 15px;'>🔐 Secure Login</h4>", 
                unsafe_allow_html=True
            )
            st.write("") # small gap
            
            username = st.text_input("Username", placeholder="Enter your User ID")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            
            st.write("") # small gap
            
            # Submit Button
            submit = st.form_submit_button("Log In", use_container_width=True)

        # Footer
        st.markdown(
            """
            <div style='text-align: center; margin-top: 10px;'>
                <p style='color: darkblue; font-size: 15px;'>
                    Powered by: ICT Division, Department of Census and Statistics
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )

        # -------------------------------------------------
        # LOGIN LOGIC
        # -------------------------------------------------
        if submit:
            if not username or not password:
                st.error("Please enter both username and password.")
                return

            user = None

            try:
                # Query user
                result = run_query(
                    "SELECT * FROM susouser WHERE login=%s AND is_active=true",
                    (username,)
                )
                if result:
                    user = result[0]

            except psycopg2.errors.UndefinedTable:
                st.error("System error: Database tables are not initialized.")
                return
            except Exception as e:
                st.error(f"Database error: {e}")
                return

            # Verification
            if user:
                stored_password = user["password"]
                if isinstance(stored_password, str):
                    stored_password = stored_password.encode('utf-8')

                if not bcrypt.checkpw(password.encode('utf-8'), stored_password):
                    st.error("Invalid username or password.")
                    return

                # Success!
                st.session_state.logged_in = True
                st.session_state.user = user["login"]
                st.session_state.role = user["role"].lower()
                st.session_state.workingarea = user["workingarea"]
                st.session_state["login"] = username

                st.success("Login successful! Redirecting...")
                st.rerun()

            else:
                st.error("Invalid username or password, or account is disabled.")