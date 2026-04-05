import streamlit as st
import pandas as pd
import time
from acsl.db import get_connection

def show_interview_progress():
    ACTION_LABELS = {
        0: "Supervisor Assigned",
        1: "Interviewer Assigned",
        3: "Completed",
        4: "Restarted",
        5: "Approved by Supervisor",
        6: "Approved by HQ",
        7: "Rejected by Supervisor",
        8: "Rejected by HQ",
        11: "Unapproved by HQ",
        12: "Created",
        13: "Received by Tablet",
        16: "Translation Switched",
        17: "Opened by Supervisor",
        18: "Closed by Supervisor",
        21: "Received by Supervisor"
    }

    # -----------------------------
    # REFRESH CONTROL
    # -----------------------------
    col1, col2 = st.columns([1, 6])
    with col1:
        if st.button("🔄 Refresh"):
            st.cache_data.clear()
            st.rerun()
    with col2:
        auto_refresh = st.checkbox("Auto Refresh (30s)")

    # -----------------------------
    # 1. FETCH LOGGED-IN USER INFO
    # -----------------------------
    conn = get_connection()
    current_login_user = st.session_state.get("login")

    if not current_login_user:
        st.warning("Please login first.")
        st.stop()

    @st.cache_data(ttl=300)
    def get_user_info(login):
        sql = "SELECT role, workingarea FROM susouser WHERE login = %(login)s LIMIT 1;"
        tmp_conn = get_connection()
        try:
            df = pd.read_sql(sql, tmp_conn, params={'login': login})
            if not df.empty:
                return str(df.iloc[0]['role']).lower().strip(), str(df.iloc[0]['workingarea']).strip()
            return None, None
        finally:
            tmp_conn.close()

    user_role, user_wa = get_user_info(current_login_user)
    
    if user_role == 'circle officer':
        if not user_wa or len(user_wa) != 7:
            st.error("⚠️ Access Denied: Circle Officer profile must have exactly a 7-character working area code.")
            st.stop()

    prefix = "" 
    if user_wa:
        if user_wa == '0000000': prefix = ''
        elif user_wa.endswith('000000'): prefix = user_wa[:1]
        elif user_wa.endswith('00000'): prefix = user_wa[:2]
        elif user_wa.endswith('000'): prefix = user_wa[:4]
        else: prefix = user_wa
    else:
        st.error("Error: Could not determine working area for the current user.")
        st.stop()

    # -----------------------------
    # 2. FETCH MASTER DATA (Single Hit)
    # -----------------------------
    @st.cache_data(ttl=60, show_spinner=False)
    def fetch_interview_data(area_prefix):
        sql = """
            WITH latest_actions AS (
                SELECT 
                    interview__key::VARCHAR,
                    action,
                    ROW_NUMBER() OVER (
                        PARTITION BY interview__key 
                        ORDER BY TO_DATE(date, 'YYYY-MM-DD') DESC, time::time DESC
                    ) AS rn
                FROM interview__actions
            ),
            OriginalInterviewer AS (
                -- Strictly isolate the true interviewer
                SELECT ia.interview__key::VARCHAR AS int_key, ia.responsible__name,
                       ROW_NUMBER() OVER(PARTITION BY ia.interview__key ORDER BY ia."date" ASC, ia."time" ASC) as rn
                FROM interview__actions ia
                JOIN susouser u ON ia.responsible__name = u.login
                WHERE ia.responsible__name IS NOT NULL 
                  AND TRIM(ia.responsible__name) != '' 
                  AND LOWER(CAST(u.role AS VARCHAR)) IN ('interviewer', '3')
            ),
            ag_deduplicated AS (
                SELECT interview__key::VARCHAR, MAX(assignment__id::VARCHAR) AS assignment__id
                FROM srilanka_agcensus2025
                GROUP BY interview__key
            )
            SELECT 
                la.interview__key,
                la.action,
                COALESCE(oi.responsible__name, 'Unknown') AS "Interviewer",
                COALESCE(a.preload_a0::VARCHAR, '') || COALESCE(a.preload_a01::VARCHAR, '') AS "Block",
                COALESCE(p.name, 'Unknown') AS province_name,
                COALESCE(d_ist.name, 'Unknown') AS district_name,
                COALESCE(v.name, 'Unknown') AS division_name,
                COALESCE(g.name, 'Unknown') AS gndivision_name
            FROM latest_actions la
            LEFT JOIN OriginalInterviewer oi ON la.interview__key = oi.int_key AND oi.rn = 1
            LEFT JOIN susouser su ON oi.responsible__name = su.login
            LEFT JOIN ag_deduplicated ag ON la.interview__key = ag.interview__key
            LEFT JOIN assignments a ON ag.assignment__id = a.meta_id::VARCHAR
            LEFT JOIN province p ON SUBSTRING(su.workingarea, 1, 1) = p.code::VARCHAR
            LEFT JOIN district d_ist ON SUBSTRING(su.workingarea, 1, 2) = d_ist.code::VARCHAR
            LEFT JOIN division v ON SUBSTRING(su.workingarea, 1, 4) = v.code::VARCHAR
            LEFT JOIN gndivision g ON su.workingarea = g.code::VARCHAR
            WHERE la.rn = 1 AND (su.workingarea LIKE %(prefix)s || '%%' OR %(prefix)s = '')
        """
        tmp_conn = get_connection()
        try:
            return pd.read_sql(sql, tmp_conn, params={'prefix': area_prefix})
        finally:
            tmp_conn.close()

    with st.spinner("Fetching geographic interview data..."):
        df = fetch_interview_data(prefix)

    df['Block'] = df['Block'].replace('', 'Missing Block Data')

    if df.empty:
        st.info("No interview data found for your working area.")
        st.stop()

    st.markdown("<h1 style='text-align: left; color: #2c3e50; font-size: 20px;'>📊 Interview Progress Dashboard</h1><hr style='margin-top: 0px; margin-bottom: 15px;'>", unsafe_allow_html=True)

    # -----------------------------
    # 3. CASCADING FILTERS
    # -----------------------------
    st.markdown("<h1 style='text-align: left; color: #2c3e50; font-size: 15px;'>🔍 Filter Scope</h1>", unsafe_allow_html=True)
    
    df_filt = df.copy()

    r1c1, r1c2, r1c3, r1c4 = st.columns(4)
    r2c1, r2c2, r2c3 = st.columns(3)

    r1c1.text_input("📍 Island", value="Sri Lanka", disabled=True, key="iprog_island")

    # Province
    sel_prov = "All"
    if len(prefix) >= 1:
        fixed_prov = df_filt['province_name'].iloc[0] if not df_filt.empty else "N/A"
        r1c2.text_input("📍 Province", value=fixed_prov, disabled=True, key="iprog_prov_l")
        df_filt = df_filt[df_filt['province_name'] == fixed_prov]
    else:
        provs = sorted([x for x in set(df_filt['province_name']) if x != 'Unknown'])
        sel_prov = r1c2.selectbox("📍 Province", ["All"] + provs, key="iprog_prov_s")
        if sel_prov != "All":
            df_filt = df_filt[df_filt['province_name'] == sel_prov]

    # District
    sel_dist = "All"
    if len(prefix) >= 2:
        fixed_dist = df_filt['district_name'].iloc[0] if not df_filt.empty else "N/A"
        r1c3.text_input("📍 District", value=fixed_dist, disabled=True, key="iprog_dist_l")
        df_filt = df_filt[df_filt['district_name'] == fixed_dist]
    else:
        dists = sorted([x for x in set(df_filt['district_name']) if x != 'Unknown'])
        sel_dist = r1c3.selectbox("📍 District", ["All"] + dists, key="iprog_dist_s")
        if sel_dist != "All":
            df_filt = df_filt[df_filt['district_name'] == sel_dist]

    # Division
    sel_div = "All"
    if len(prefix) >= 4:
        fixed_div = df_filt['division_name'].iloc[0] if not df_filt.empty else "N/A"
        r1c4.text_input("📍 Division", value=fixed_div, disabled=True, key="iprog_div_l")
        df_filt = df_filt[df_filt['division_name'] == fixed_div]
    else:
        divs = sorted([x for x in set(df_filt['division_name']) if x != 'Unknown'])
        sel_div = r1c4.selectbox("📍 Division", ["All"] + divs, key="iprog_div_s")
        if sel_div != "All":
            df_filt = df_filt[df_filt['division_name'] == sel_div]

    # GN Division
    sel_gn = "All"
    if len(prefix) >= 7:
        fixed_gn = df_filt['gndivision_name'].iloc[0] if not df_filt.empty else "N/A"
        r2c1.text_input("📍 GN Division", value=fixed_gn, disabled=True, key="iprog_gn_l")
        df_filt = df_filt[df_filt['gndivision_name'] == fixed_gn]
    else:
        gns = sorted([x for x in set(df_filt['gndivision_name']) if x != 'Unknown'])
        sel_gn = r2c1.selectbox("📍 GN Division", ["All"] + gns, key="iprog_gn_s")
        if sel_gn != "All":
            df_filt = df_filt[df_filt['gndivision_name'] == sel_gn]

    # Interviewer
    if user_role in ['interviewer', '3']:
        sel_int = current_login_user
        r2c2.text_input("🧑‍💻 Interviewer", value=current_login_user, disabled=True, key="iprog_int_l")
        df_filt = df_filt[df_filt['Interviewer'] == sel_int]
    else:
        ints = sorted(list(set(df_filt['Interviewer'])))
        if "Unknown" in ints: ints.remove("Unknown")
        sel_int = r2c2.selectbox("🧑‍💻 Interviewer", ["All"] + ints, key="iprog_int_s")
        if sel_int != "All":
            df_filt = df_filt[df_filt['Interviewer'] == sel_int]

    # Block
    blks = sorted(list(set(df_filt['Block'])))
    sel_blk = r2c3.selectbox("🏢 Block", ["All"] + blks, key="iprog_blk_s")
    if sel_blk != "All":
        df_filt = df_filt[df_filt['Block'] == sel_blk]

    if df_filt.empty:
        st.warning("No data matches the selected filters.")
        if auto_refresh:
            time.sleep(30)
            st.rerun()
        st.stop()

    # -----------------------------
    # 4. STATUS MAPPING & METRICS
    # -----------------------------
    df_filt["action"] = pd.to_numeric(df_filt["action"], errors="coerce")
    df_filt["status"] = df_filt["action"].map(ACTION_LABELS)

    summary = df_filt["status"].value_counts().reindex(ACTION_LABELS.values(), fill_value=0)

    st.markdown("---")
    st.markdown("<h1 style='text-align: left; color: #2c3e50; font-size: 15px;'>📊 Overall Action Status Counts</h1>", unsafe_allow_html=True)

    cols = st.columns(5)
    for i, (status, count) in enumerate(summary.items()):
        cols[i % 5].metric(status, int(count))

    # -----------------------------
    # 5. DYNAMIC AREA BREAKDOWN
    # -----------------------------
    if sel_blk != "All" or sel_int != "All" or sel_gn != "All" or len(prefix) >= 7:
        group_col, geo_label = 'Block', 'Block'
    elif sel_div != "All" or len(prefix) >= 4:
        group_col, geo_label = 'gndivision_name', 'GN Division'
    elif sel_dist != "All" or len(prefix) >= 2:
        group_col, geo_label = 'division_name', 'Division'
    elif sel_prov != "All" or len(prefix) >= 1:
        group_col, geo_label = 'district_name', 'District'
    else:
        group_col, geo_label = 'province_name', 'Province'

    st.markdown(f"<h3 style='text-align: left; color: #2c3e50; font-size: 18px;'>📍 Geographic Breakdown: {geo_label} Level</h3>", unsafe_allow_html=True)

    pivot = pd.pivot_table(
        df_filt,
        index=group_col,
        columns="status",
        aggfunc="size",
        fill_value=0
    )
    
    pivot.index.name = geo_label
    st.dataframe(pivot, use_container_width=True)

    # -----------------------------
    # AUTO REFRESH
    # -----------------------------
    if auto_refresh:
        time.sleep(30)
        st.rerun()