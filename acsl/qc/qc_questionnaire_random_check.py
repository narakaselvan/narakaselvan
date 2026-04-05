import streamlit as st
import pandas as pd
import datetime
import requests
from requests.auth import HTTPBasicAuth
from acsl.db import get_connection

try:
    import plotly.graph_objects as go
except ImportError:
    st.error("⚠️ Plotly is not installed. Please run `pip install plotly` in your terminal.")
    st.stop()

# ==========================================
# ⚙️ SURVEY SOLUTIONS API CONFIGURATION
# ==========================================
SUSO_URL = "https://your-server-name.mysurvey.solutions" 
WORKSPACE = "primary" 
API_USER = "your_api_username"
API_PASS = "your_api_password"

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
# 2. DATABASE INITIALIZATION & HELPERS
# ==========================================
def initialize_verification_tables():
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS random_interview_verification (
            interview_key VARCHAR(50), "user" VARCHAR(100), checking_type VARCHAR(50),
            verified_date DATE, verified_time TIME, PRIMARY KEY (interview_key, "user", checking_type)
        );
        """)
        cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name='random_interview_verification' AND column_name='checking_type';")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE random_interview_verification ADD COLUMN checking_type VARCHAR(50) DEFAULT 'Unknown';")
            cursor.execute("ALTER TABLE random_interview_verification DROP CONSTRAINT IF EXISTS random_interview_verification_pkey;")
            cursor.execute('ALTER TABLE random_interview_verification ADD PRIMARY KEY (interview_key, "user", checking_type);')

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS verification_rejection_suggestions (
            id SERIAL PRIMARY KEY, interview_key VARCHAR(50), interview_guid VARCHAR(50),
            checking_type VARCHAR(50), suggested_by VARCHAR(100), verified_by VARCHAR(100),
            verified_date DATE, verified_time TIME, comments TEXT, status VARCHAR(50) DEFAULT 'Pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS hybrid_api_action_log (
            id SERIAL PRIMARY KEY, interview_key VARCHAR(50), action_by VARCHAR(100),
            action_type VARCHAR(50), api_status VARCHAR(255), timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        conn.commit()
    except Exception: pass
    finally:
        cursor.close()
        conn.close()

def save_verification(interview_key, user, checking_type, v_date, v_time):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
        INSERT INTO random_interview_verification (interview_key, "user", checking_type, verified_date, verified_time)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (interview_key, "user", checking_type) DO UPDATE SET verified_date = EXCLUDED.verified_date, verified_time = EXCLUDED.verified_time;
        """, (interview_key, user, checking_type, v_date, v_time))
        conn.commit()
    finally:
        cur.close()
        conn.close()

def save_rejection_suggestion(int_key, int_guid, chk_type, sugg_by, ver_by, v_date, v_time, comments):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
        INSERT INTO verification_rejection_suggestions (interview_key, interview_guid, checking_type, suggested_by, verified_by, verified_date, verified_time, comments)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (int_key, int_guid, chk_type, sugg_by, ver_by, v_date, v_time, comments))
        conn.commit()
    finally:
        cur.close()
        conn.close()

def execute_api_reject(int_guid, int_key, action_by, comment, suggestion_id=None):
    api_url = f"{SUSO_URL}/api/v1/interviews/{int_guid}/reject"
    payload = {"comment": comment}
    headers = {"Workspace": WORKSPACE}
    
    try:
        resp = requests.patch(api_url, auth=HTTPBasicAuth(API_USER, API_PASS), headers=headers, json=payload, timeout=10)
        api_status = "Success (200)" if resp.status_code == 200 else f"Failed ({resp.status_code}): {resp.text}"
    except Exception as e:
        api_status = f"Error: {str(e)}"
        
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO hybrid_api_action_log (interview_key, action_by, action_type, api_status) VALUES (%s, %s, %s, %s)",
                    (int_key, action_by, "API Reject", api_status))
        if "Success" in api_status and suggestion_id:
            cur.execute("UPDATE verification_rejection_suggestions SET status='Rejected' WHERE id=%s", (suggestion_id,))
        conn.commit()
    finally:
        cur.close()
        conn.close()
    return "Success" in api_status, api_status

# ==========================================
# 3. MAIN DASHBOARD FUNCTION
# ==========================================
def show_generalized_verification_dashboard():
    
    st.markdown(
        """
        <h1 style='text-align: left; color: #2c3e50; font-size: 24px;'>
            ✅ Holding Verification & Quality Control
        </h1>
        <p style='color: gray; font-size: 14px;'>Filter permanently closed (HQ Approved) holdings, execute physical verifications, and manage rejections.</p>
        <hr style='margin-top: 0px; margin-bottom: 15px;'>
        """,
        unsafe_allow_html=True
    )

    initialize_verification_tables()

    current_login_user = st.session_state.get("login")
    if not current_login_user:
        st.warning("Please login first.")
        return

    # --- FACTOR SELECTION ---
    factors_list = list(FACTOR_LOGIC.keys())
    selected_factor = st.selectbox("📌 Select Verification Factor to Analyze:", factors_list)
    
    hide_others = st.checkbox("👁️ Hide interviews already verified by other users", value=False)
    
    st.markdown("---")

    def get_user_info(login):
        sql = "SELECT role, workingarea FROM susouser WHERE login = %(login)s LIMIT 1;"
        conn = get_connection()
        try:
            df = pd.read_sql(sql, conn, params={'login': login})
            return (str(df.iloc[0]['role']).lower().strip(), str(df.iloc[0]['workingarea']).strip()) if not df.empty else (None, None)
        finally:
            conn.close()

    user_role, user_wa = get_user_info(current_login_user)
    AUTHORIZED_ROLES = ['supervisor', 'area supervisor', 'head of district', 'district head', 'zonal supervisor', 'provincial coordinator']
    is_authorized = user_role in AUTHORIZED_ROLES

    prefix = "" 
    if user_wa and user_wa != '0000000':
        prefix = user_wa[:1] if user_wa.endswith('000000') else user_wa[:2] if user_wa.endswith('00000') else user_wa[:4] if user_wa.endswith('000') else user_wa

    # ==========================================
    # 4. DATA FETCHING 
    # ==========================================
    @st.cache_data(show_spinner=False, ttl=30)
    def fetch_holdings_and_verifications(area_prefix, check_type):
        logic = FACTOR_LOGIC[check_type]
        dynamic_cols = ",\n                       ".join(logic["columns"])
        dynamic_where = logic["condition"]
        
        conn = get_connection()
        try:
            sql_holdings = f"""
            WITH LatestAssign AS (
                SELECT assignment__id, responsible__name,
                       ROW_NUMBER() OVER(PARTITION BY assignment__id ORDER BY "date" DESC, "time" DESC) as rn
                FROM assignment__actions
                WHERE responsible__name IS NOT NULL AND TRIM(responsible__name) != ''
            ),
            ServerTime AS (
                SELECT interview__key::VARCHAR AS int_key, 
                       MAX(("date" || ' ' || "time")::TIMESTAMP) AS arrival_time
                FROM interview__actions
                GROUP BY interview__key
            ),
            MainData AS (
                SELECT interview__key::VARCHAR AS int_key, MAX(assignment__id::VARCHAR) AS assignment_id, {dynamic_cols}
                FROM srilanka_agcensus2025 GROUP BY interview__key
            )
            SELECT DISTINCT
                d.interview__key::VARCHAR AS "Interview Key",
                d.interview__id::VARCHAR AS "Interview GUID",
                st.arrival_time AS "Server Time",
                (COALESCE(a.preload_a0::VARCHAR, '') || COALESCE(a.preload_a01::VARCHAR, '')) AS "Block",
                COALESCE(a.preload_b7, 'Unknown') AS "Name of Respondent",
                COALESCE(a.preload_b8, 'Unknown') AS "Address",
                COALESCE(p.name, 'Unknown') AS province_name,
                COALESCE(d_ist.name, 'Unknown') AS district_name,
                COALESCE(v.name, 'Unknown') AS division_name,
                COALESCE(g.name, 'Unknown') AS gndivision_name
            FROM interview__diagnostics d
            JOIN MainData m ON d.interview__key::VARCHAR = m.int_key
            JOIN ServerTime st ON d.interview__key::VARCHAR = st.int_key
            JOIN assignments a ON m.assignment_id = a.meta_id::VARCHAR
            LEFT JOIN LatestAssign la ON a.meta_id::VARCHAR = la.assignment__id::VARCHAR AND la.rn = 1
            LEFT JOIN susouser su ON la.responsible__name = su.login
            LEFT JOIN province p ON SUBSTRING(su.workingarea, 1, 1) = p.code::VARCHAR
            LEFT JOIN district d_ist ON SUBSTRING(su.workingarea, 1, 2) = d_ist.code::VARCHAR
            LEFT JOIN division v ON SUBSTRING(su.workingarea, 1, 4) = v.code::VARCHAR
            LEFT JOIN gndivision g ON su.workingarea = g.code::VARCHAR
            WHERE d.interview__status::FLOAT = 130
              AND (su.workingarea LIKE %(prefix)s || '%%' OR %(prefix)s = '')
              AND ({dynamic_where})
            """
            df_holdings = pd.read_sql(sql_holdings, conn, params={'prefix': area_prefix})

            sql_verifs = """
            SELECT r.interview_key, r."user", LOWER(u.role) AS role, r.verified_date, r.verified_time
            FROM random_interview_verification r
            JOIN susouser u ON r."user" = u.login
            WHERE r.checking_type = %(chk_type)s
            """
            df_verifs = pd.read_sql(sql_verifs, conn, params={'chk_type': check_type})

            return df_holdings, df_verifs
        finally:
            conn.close()

    with st.spinner(f"Loading data for '{selected_factor}'..."):
        df_holdings, df_verifs = fetch_holdings_and_verifications(prefix, selected_factor)

    if df_holdings.empty:
        st.info("No permanently closed holdings matching the criteria were found.")
        return

    if hide_others and not df_verifs.empty:
        others_verifs = df_verifs[df_verifs['user'] != current_login_user]['interview_key'].tolist()
        df_holdings = df_holdings[~df_holdings['Interview Key'].isin(others_verifs)]

    if df_holdings.empty:
        st.success("All visible holdings have already been verified by other users!")
        return

    # ==========================================
    # 5. CASCADING GEOGRAPHIC FILTERS
    # ==========================================
    st.markdown("<h1 style='text-align: left; color: #2c3e50; font-size: 15px;'>🔍 Filter Scope</h1>", unsafe_allow_html=True)
    df_filt = df_holdings.copy()

    r1c1, r1c2, r1c3, r1c4 = st.columns(4)
    r2c1, r2c2 = st.columns(2)

    r1c1.text_input("📍 Island", value="Sri Lanka", disabled=True)
    
    provs = sorted([x for x in set(df_filt['province_name']) if x != 'Unknown'])
    sel_prov = r1c2.selectbox("📍 Province", ["All"] + provs) if len(prefix) < 1 else r1c2.text_input("📍 Province", df_filt['province_name'].iloc[0] if not df_filt.empty else "N/A", disabled=True)
    if sel_prov != "All" and len(prefix) < 1: df_filt = df_filt[df_filt['province_name'] == sel_prov]

    dists = sorted([x for x in set(df_filt['district_name']) if x != 'Unknown'])
    sel_dist = r1c3.selectbox("📍 District", ["All"] + dists) if len(prefix) < 2 else r1c3.text_input("📍 District", df_filt['district_name'].iloc[0] if not df_filt.empty else "N/A", disabled=True)
    if sel_dist != "All" and len(prefix) < 2: df_filt = df_filt[df_filt['district_name'] == sel_dist]

    divs = sorted([x for x in set(df_filt['division_name']) if x != 'Unknown'])
    sel_div = r1c4.selectbox("📍 Division", ["All"] + divs) if len(prefix) < 4 else r1c4.text_input("📍 Division", df_filt['division_name'].iloc[0] if not df_filt.empty else "N/A", disabled=True)
    if sel_div != "All" and len(prefix) < 4: df_filt = df_filt[df_filt['division_name'] == sel_div]

    gns = sorted([x for x in set(df_filt['gndivision_name']) if x != 'Unknown'])
    sel_gn = r2c1.selectbox("📍 GN Division", ["All"] + gns) if len(prefix) < 7 else r2c1.text_input("📍 GN Division", df_filt['gndivision_name'].iloc[0] if not df_filt.empty else "N/A", disabled=True)
    if sel_gn != "All" and len(prefix) < 7: df_filt = df_filt[df_filt['gndivision_name'] == sel_gn]

    blks = sorted(list(set(df_filt['Block'])))
    sel_blk = r2c2.selectbox("🏢 Block", ["All"] + blks)
    if sel_blk != "All": df_filt = df_filt[df_filt['Block'] == sel_blk]

    if df_filt.empty:
        st.warning("No holdings match the selected geographic filters.")
        return

    st.markdown("---")

    # ==========================================
    # 6. PIE CHARTS (PROGRESS TRACKING)
    # ==========================================
    st.markdown(f"<h3 style='text-align: left; color: #2c3e50; font-size: 18px;'>📊 Progress for: {selected_factor}</h3>", unsafe_allow_html=True)
    
    total_holdings = len(df_filt)
    valid_int_keys = df_filt['Interview Key'].tolist()
    df_vf_filtered = df_verifs[df_verifs['interview_key'].isin(valid_int_keys)]
    
    def get_vf_count(role_name):
        return len(df_vf_filtered[df_vf_filtered['role'] == role_name]['interview_key'].unique())

    counts = {
        "Supervisor": get_vf_count('supervisor'),
        "Area Supervisor": get_vf_count('area supervisor'),
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
            marker=dict(colors=['#17a2b8', '#e0e0e0'], line=dict(color='#ffffff', width=2)), 
            textinfo='none'
        ))
        fig.update_layout(
            title=dict(text=f"<b>{title}</b>", x=0.5, font=dict(size=12)),
            margin=dict(t=30, b=0, l=0, r=0),
            showlegend=False,
            height=150
        )
        fig.add_annotation(text=f"{count}/{total_holdings}", x=0.5, y=0.5, font_size=12, showarrow=False)
        cols[i].plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # ==========================================
    # 7. DATA TABLE & ACTIONS
    # ==========================================
    st.markdown(f"<h3 style='text-align: left; color: #2c3e50; font-size: 18px;'>📝 Holdings Verification List</h3>", unsafe_allow_html=True)

    def determine_status(int_key):
        v = df_verifs[df_verifs['interview_key'] == int_key]
        if v.empty: return 'Not Verified ❌'
        if current_login_user in v['user'].tolist(): return 'Verified by Me ✅'
        return 'Verified by Others 🔄'

    def calculate_pending_time(row):
        s_dt = pd.to_datetime(row["Server Time"])
        if pd.isna(s_dt): return "Unknown"
        int_key = row["Interview Key"]
        v = df_verifs[(df_verifs['interview_key'] == int_key) & (df_verifs['user'] == current_login_user)]
        if not v.empty:
            v_date, v_time = v.iloc[0]['verified_date'], v.iloc[0]['verified_time']
            end_dt = datetime.datetime.combine(v_date, v_time) if (v_date and v_time) else datetime.datetime.now()
        else:
            end_dt = datetime.datetime.now()
        elapsed = end_dt - s_dt
        days = elapsed.days
        hours, remainder = divmod(elapsed.seconds, 3600)
        return f"{days}d {hours}h" if days > 0 else f"{hours}h {remainder // 60}m"

    df_filt['Verified'] = df_filt['Interview Key'].apply(determine_status)
    df_filt['Time Elapsed'] = df_filt.apply(calculate_pending_time, axis=1)
    
    display_cols = ["Block", "Interview Key", "Name of Respondent", "Address", "Verified", "Time Elapsed"] if is_authorized else ["Block", "Interview Key", "Name of Respondent", "Address", "Time Elapsed"]

    st.caption("💡 *Click on a row to verify it as Correct, or Reject it as Incorrect.*")
    selected_event = st.dataframe(df_filt[display_cols], use_container_width=True, hide_index=True, selection_mode="single-row", on_select="rerun")

    if is_authorized and hasattr(selected_event, "selection") and selected_event.selection.rows:
        row_idx = selected_event.selection.rows[0]
        sel_row = df_filt.iloc[row_idx]
        int_key, int_guid, name = sel_row["Interview Key"], sel_row["Interview GUID"], sel_row["Name of Respondent"]
        
        st.markdown(f"#### 🔎 Verification Actions for: {name} ({int_key})")

        s_dt = pd.to_datetime(sel_row["Server Time"]) if pd.notna(sel_row["Server Time"]) else None
        if s_dt: st.info(f"📥 **Arrived on Server:** {s_dt.strftime('%Y-%m-%d %I:%M %p')}")

        prev_v = df_verifs[df_verifs['interview_key'] == int_key]
        outcome = st.radio("Verification Outcome:", ["✅ Verification Correct (Accept)", "❌ Verification Incorrect / Data Invalid (Reject)"])
        
        with st.form("verify_action_form"):
            cd, ct = st.columns(2)
            v_date = cd.date_input("Verification Date", datetime.date.today())
            v_time = ct.time_input("Verification Time", datetime.datetime.now().time())
            
            if s_dt:
                v_dt = datetime.datetime.combine(v_date, v_time)
                elapsed = v_dt - s_dt
                st.write(f"⏳ *Time elapsed from server arrival to verification:* **{elapsed}**")

            if outcome == "✅ Verification Correct (Accept)":
                if st.form_submit_button(f"Submit {selected_factor} Verification"):
                    save_verification(int_key, current_login_user, selected_factor, v_date, v_time)
                    st.success("Verification saved successfully!"); st.cache_data.clear(); st.rerun()
            else:
                rej_comment = st.text_area("Reason for Rejection:")
                if user_role == 'supervisor':
                    if st.form_submit_button("🔥 Execute API Rejection Directly"):
                        if rej_comment:
                            with st.spinner("Calling API..."):
                                ok, msg = execute_api_reject(int_guid, int_key, current_login_user, rej_comment)
                            if ok: 
                                save_verification(int_key, current_login_user, selected_factor, v_date, v_time)
                                st.success("Interview rejected and synced to server!"); st.cache_data.clear(); st.rerun()
                            else: st.error(msg)
                        else: st.error("Comment required to reject.")
                else:
                    if st.form_submit_button("📥 Suggest Rejection to Supervisor"):
                        if rej_comment:
                            if not prev_v.empty:
                                v_by = ", ".join(prev_v['user'].unique())
                                v_d, v_t = prev_v.iloc[0]['verified_date'], prev_v.iloc[0]['verified_time']
                            else:
                                v_by, v_d, v_t = current_login_user, v_date, v_time
                                
                            save_rejection_suggestion(int_key, int_guid, selected_factor, current_login_user, v_by, v_d, v_t, rej_comment)
                            save_verification(int_key, current_login_user, selected_factor, v_date, v_time)
                            st.success("Rejection suggestion sent to the Supervisor!"); st.cache_data.clear(); st.rerun()
                        else: st.error("Comment required to suggest rejection.")

    # ==========================================
    # 8. SUPERVISOR INBOX (For Suggestions)
    # ==========================================
    if user_role == 'supervisor':
        st.markdown("---")
        st.markdown("<h3 style='text-align: left; color: #d9534f; font-size: 18px;'>📥 Action Required: Suggested Rejections</h3>", unsafe_allow_html=True)
        st.caption("These interviews were reviewed by Area Supervisors or HQ and were marked as Incorrect. Please review their comments and execute the API rejection.")
        
        conn = get_connection()
        try:
            # FIXED: Added LatestSuggestion CTE to firmly prevent multiple rows for the same interview
            sql_sugg = """
            WITH LatestSuggestion AS (
                SELECT id, interview_key, interview_guid, suggested_by, verified_by, verified_date, verified_time, comments, checking_type, status,
                       ROW_NUMBER() OVER(PARTITION BY interview_key ORDER BY created_at DESC) as rn
                FROM verification_rejection_suggestions
                WHERE status = 'Pending' AND checking_type = %(chk_type)s
            ),
            MainData AS (
                SELECT interview__key::VARCHAR AS int_key, MAX(assignment__id::VARCHAR) AS assignment_id
                FROM srilanka_agcensus2025
                GROUP BY interview__key
            )
            SELECT s.id, s.interview_key, s.interview_guid, 
                   COALESCE(a.preload_b7, 'Unknown') AS "Name of Respondent", 
                   COALESCE(a.preload_b8, 'Unknown') AS "Address",
                   s.suggested_by, s.verified_by, s.verified_date, s.verified_time, s.comments
            FROM LatestSuggestion s
            JOIN MainData m ON s.interview_key = m.int_key
            JOIN assignments a ON m.assignment_id = a.meta_id::VARCHAR
            JOIN susouser su ON a.meta_responsiblename = su.login
            WHERE s.rn = 1 AND su.workingarea LIKE %(prefix)s || '%%'
            """
            df_sugg = pd.read_sql(sql_sugg, conn, params={'chk_type': selected_factor, 'prefix': prefix})
        finally:
            conn.close()

        if df_sugg.empty:
            st.success("No pending rejection suggestions in your area.")
        else:
            # Fallback deduplication just to be 100% safe
            df_sugg = df_sugg.drop_duplicates(subset=['interview_key'])
            
            st.dataframe(df_sugg[["interview_key", "Name of Respondent", "Address", "suggested_by", "verified_by", "verified_date", "verified_time", "comments"]], hide_index=True)
            
            sugg_idx = st.selectbox("Select Interview to Reject via API:", df_sugg['interview_key'].tolist())
            sup_comment = st.text_input("Additional Supervisor Comment (Optional):")
            
            if st.button("🔥 Execute Approved API Rejection"):
                sugg_row = df_sugg[df_sugg['interview_key'] == sugg_idx].iloc[0]
                final_comment = f"HQ/Area Suggestion: {sugg_row['comments']} | Sup: {sup_comment}"
                
                with st.spinner("Calling API..."):
                    ok, msg = execute_api_reject(sugg_row['interview_guid'], sugg_idx, current_login_user, final_comment, suggestion_id=sugg_row['id'])
                
                if ok: 
                    st.success("Rejected and synced!")
                    st.cache_data.clear()
                    st.rerun()
                else: 
                    st.error(msg)

if __name__ == "__main__":
    show_generalized_verification_dashboard()