import streamlit as st
import pandas as pd
from acsl.db import get_connection

# --- Import Verification Dashboard Functions ---
from acsl.qc.qc_questionnaire_random_check import show_generalized_verification_dashboard
from acsl.qc.qc_overview_verification import show_overview_verification_dashboard

# --- Import Agricultural Analytics Functions ---
from acsl.qc.qc_overview_agricultural_analytics import show_overview_agricultural_analytics
from acsl.qc.qc_agricultural_analytics import show_agricultural_analytics


def get_user_role(login):
    """Helper function to fetch the user's role from the database."""
    sql = "SELECT role FROM susouser WHERE login = %(login)s LIMIT 1;"
    conn = get_connection()
    try:
        df = pd.read_sql(sql, conn, params={'login': login})
        if not df.empty:
            return str(df.iloc[0]['role']).lower().strip()
        return None
    except Exception as e:
        st.error(f"Error fetching user role: {e}")
        return None
    finally:
        conn.close()


def show_verification():
    # 1. Get current logged-in user
    current_login_user = st.session_state.get("login")
    if not current_login_user:
        st.warning("Please login first.")
        return

    # 2. Check the user's role securely from the DB
    user_role = get_user_role(current_login_user)
    
    # Define what roles count as "Headquarters" (Case-insensitive 'headquarters' is covered)
    is_hq = user_role in ['headquarters', 'hq', 'admin', '1']

    # 3. Conditionally render the correct tabs and functions
    if is_hq:
        # ==========================================
        # FOR HEADQUARTERS: SHOW ONLY OVERVIEWS
        # ==========================================
        sub_tabs = st.tabs([
            "📊 Verification Overview", 
            "🌍 Analytics Overview"
        ])
        
        with sub_tabs[0]:
            show_overview_verification_dashboard()
            
        with sub_tabs[1]:
            show_overview_agricultural_analytics()
            
    else:
        # ==========================================
        # FOR SUPERVISORS/OTHERS: SHOW ONLY DETAILED
        # ==========================================
        sub_tabs = st.tabs([
            "📝 Detailed Verification", 
            "🌾 Regional Analytics"
        ])
        
        with sub_tabs[0]:
            show_generalized_verification_dashboard()
            
        with sub_tabs[1]:
            show_agricultural_analytics()