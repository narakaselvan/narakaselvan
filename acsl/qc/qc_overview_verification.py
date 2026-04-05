import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from acsl.db import get_connection

# ==========================================
# 1. DYNAMIC VERIFICATION FACTOR LOGIC
# ==========================================
FACTOR_LOGIC = {
    "Respondent Unavailable": {
        "columns": ['MAX("A19a"::VARCHAR) AS a19a', 'MAX("Q1_1"::VARCHAR) AS q1_1', 'MAX("A19"::VARCHAR) AS a19'],
        "condition": "(m.a19a = '2' OR m.a19a ILIKE 'no' OR m.q1_1 IN ('2', '3', '4')) AND (m.a19 = '3' OR m.a19 ILIKE '%%unavailable%%')"
    },
    "Non-Agricultural": {
        "columns": ['MAX("ELIGIBLE"::VARCHAR) AS eligible'],
        "condition": "LOWER(TRIM(m.eligible)) = 'not-eligible' OR LOWER(TRIM(m.eligible)) = 'not eligible' OR m.eligible = '0' OR m.eligible IS NULL"
    },
    "Insufficient Land": {
        "columns": ['MAX("Q1_4d"::VARCHAR) AS q1_4d', 'MAX("Q1_3a"::VARCHAR) AS q1_3a', 'MAX("Q1_3b"::VARCHAR) AS q1_3b', 'MAX("Q1_3c"::VARCHAR) AS q1_3c'],
        "condition": "(m.q1_4d = '0' OR m.q1_4d ILIKE 'no') AND (m.q1_3a = '1' OR m.q1_3a ILIKE 'yes') AND (m.q1_3b = '1' OR m.q1_3b ILIKE 'yes' OR m.q1_3c = '1' OR m.q1_3c ILIKE 'yes')"
    },
    "Not Used for Agriculture": {
        "columns": ['MAX("Q1_3a"::VARCHAR) AS q1_3a', 'MAX("Q1_1"::VARCHAR) AS q1_1'],
        "condition": "(m.q1_3a = '0' OR m.q1_3a ILIKE 'no') AND (m.q1_1 = '1' OR m.q1_1 ILIKE 'yes')"
    },
    "No Aquaculture": {
        "columns": ['MAX("Q1_3d"::VARCHAR) AS q1_3d', 'MAX("Q1_1"::VARCHAR) AS q1_1'],
        "condition": "(m.q1_3d = '0' OR m.q1_3d ILIKE 'no') AND (m.q1_1 = '1' OR m.q1_1 ILIKE 'yes')"
    },
    "No Livestock": {
        "columns": ['MAX("Q1_3c"::VARCHAR) AS q1_3c', 'MAX("Q1_1"::VARCHAR) AS q1_1'],
        "condition": "(m.q1_3c = '0' OR m.q1_3c ILIKE 'no') AND (m.q1_1 = '1' OR m.q1_1 ILIKE 'yes')"
    }
}

# ==========================================
# 2. DATA FETCHING (CACHED)
# ==========================================
@st.cache_data(show_spinner=False, ttl=60)
def fetch_holdings_and_verifications(area_prefix, check_type):
    logic = FACTOR_LOGIC[check_type]
    dynamic_cols = ",\n                       ".join(logic["columns"])
    dynamic_where = logic["condition"]
    
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT to_regclass('public.random_interview_verification');")
        table_exists = cur.fetchone()[0] is not None
        cur.close()

        sql_holdings = f"""
        WITH MainData AS (
            SELECT interview__key::VARCHAR AS int_key, 
                   MAX(assignment__id::VARCHAR) AS assignment_id, 
                   {dynamic_cols}
            FROM srilanka_agcensus2025 GROUP BY interview__key
        )
        SELECT DISTINCT d.interview__key::VARCHAR AS "Interview Key"
        FROM interview__diagnostics d
        JOIN MainData m ON d.interview__key::VARCHAR = m.int_key
        JOIN assignments a ON m.assignment_id = a.meta_id::VARCHAR
        LEFT JOIN susouser su ON a.meta_responsiblename = su.login
        WHERE d.interview__status::FLOAT = 130
          AND (su.workingarea LIKE %(prefix)s || '%%' OR %(prefix)s = '')
          AND ({dynamic_where})
        """
        df_holdings = pd.read_sql(sql_holdings, conn, params={'prefix': area_prefix})

        if table_exists:
            sql_verifs = """
            SELECT r.interview_key, LOWER(u.role) AS role
            FROM random_interview_verification r
            JOIN susouser u ON r."user" = u.login
            WHERE r.checking_type = %(chk_type)s
            """
            df_verifs = pd.read_sql(sql_verifs, conn, params={'chk_type': check_type})
        else:
            df_verifs = pd.DataFrame(columns=['interview_key', 'role'])

        return df_holdings, df_verifs
    except Exception as e:
        st.error(f"Error loading {check_type}: {e}")
        return pd.DataFrame(), pd.DataFrame()
    finally:
        conn.close()

# ==========================================
# 3. MAIN DASHBOARD UI
# ==========================================
def show_overview_verification_dashboard():
    st.markdown(
        """
        <h1 style='text-align: left; color: #2c3e50; font-size: 24px;'>
            📊 Verification Progress Summary
        </h1>
        <p style='color: gray; font-size: 14px;'>Overall verification status for all quality control factors in your area.</p>
        <hr style='margin-top: 0px; margin-bottom: 15px;'>
        """,
        unsafe_allow_html=True
    )

    # --- REAL-TIME REFRESH BUTTON ---
    col_a, col_b = st.columns([1, 6])
    with col_a:
        if st.button("🔄 Force Refresh Data"):
            st.cache_data.clear() # Instantly wipes the memory cache
            st.rerun()

    current_login_user = st.session_state.get("login")
    if not current_login_user:
        st.warning("Please login first.")
        return

    def get_user_wa(login):
        sql = "SELECT workingarea FROM susouser WHERE login = %(login)s LIMIT 1;"
        conn = get_connection()
        try:
            df = pd.read_sql(sql, conn, params={'login': login})
            return str(df.iloc[0]['workingarea']).strip() if not df.empty else ""
        finally:
            conn.close()

    user_wa = get_user_wa(current_login_user)
    prefix = "" 
    if user_wa and user_wa != '0000000':
        prefix = user_wa[:1] if user_wa.endswith('000000') else user_wa[:2] if user_wa.endswith('00000') else user_wa[:4] if user_wa.endswith('000') else user_wa

    # --- LOOP THROUGH ALL FACTORS AND DRAW PIE CHARTS ---
    for factor_name in FACTOR_LOGIC.keys():
        st.markdown(f"<h3 style='color: #007bff; font-size: 20px;'>📌 {factor_name}</h3>", unsafe_allow_html=True)

        with st.spinner(f"Loading {factor_name}..."):
            df_holdings, df_verifs = fetch_holdings_and_verifications(prefix, factor_name)

        if df_holdings.empty:
            st.info(f"No permanently closed holdings matching '{factor_name}' found in your area.")
            st.markdown("---")
            continue

        total_holdings = len(df_holdings)
        valid_int_keys = df_holdings['Interview Key'].tolist()
        df_vf_filtered = df_verifs[df_verifs['interview_key'].isin(valid_int_keys)]
        
        def get_vf_count(role_name):
            return len(df_vf_filtered[df_vf_filtered['role'] == role_name]['interview_key'].unique())

        counts = {
            "Supervisor": get_vf_count('supervisor'),
            "Area Supervisor": get_vf_count('area supervisor'),
            # FIXED: Catch both role spellings
            "Head of District": get_vf_count('head of district') + get_vf_count('district head'), 
            "Zonal Supervisor": get_vf_count('zonal supervisor'),
            "Provincial Coord.": get_vf_count('provincial coordinator')
        }

        cols = st.columns(5)
        for i, (title, count) in enumerate(counts.items()):
            fig = go.Figure(go.Pie(
                labels=['Verified', 'Pending'],
                values=[count, total_holdings - count],
                hole=0.4,
                marker=dict(colors=['#28a745', '#e0e0e0'], line=dict(color='#ffffff', width=2)), 
                textinfo='none'
            ))
            fig.update_layout(
                title=dict(text=f"<b>{title}</b>", x=0.5, font=dict(size=12)),
                margin=dict(t=30, b=0, l=0, r=0),
                showlegend=False,
                height=150
            )
            fig.add_annotation(text=f"{count}/{total_holdings}", x=0.5, y=0.5, font_size=12, showarrow=False)
            
            cols[i].plotly_chart(fig, use_container_width=True, key=f"pie_{factor_name}_{i}")

        st.markdown("---")

if __name__ == "__main__":
    show_overview_verification_dashboard()