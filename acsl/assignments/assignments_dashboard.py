import streamlit as st
import sys
import os
import pandas as pd

# -------------------------------------------------
# PATH FIX
# -------------------------------------------------
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from acsl.db import get_connection

# -------------------------------------------------
# FETCH DATA EFFICIENTLY (SINGLE DATABASE HIT)
# -------------------------------------------------
@st.cache_data(show_spinner=False, ttl=60)
def fetch_dashboard_data(prefix):
    conn = get_connection()
    try:
        # 1. Fetch Users with Geographic Names mapped
        sql_users = """
        SELECT 
            u.login, LOWER(u.role) AS role, u.workingarea,
            COALESCE(p.name, 'Unknown') AS province_name,
            COALESCE(d.name, 'Unknown') AS district_name,
            COALESCE(v.name, 'Unknown') AS division_name,
            COALESCE(g.name, 'Unknown') AS gndivision_name
        FROM susouser u
        LEFT JOIN province p ON SUBSTRING(u.workingarea, 1, 1) = p.code::VARCHAR
        LEFT JOIN district d ON SUBSTRING(u.workingarea, 1, 2) = d.code::VARCHAR
        LEFT JOIN division v ON SUBSTRING(u.workingarea, 1, 4) = v.code::VARCHAR
        LEFT JOIN gndivision g ON u.workingarea = g.code::VARCHAR
        WHERE u.workingarea LIKE %(prefix)s || '%%' OR %(prefix)s = ''
        """
        df_users = pd.read_sql(sql_users, conn, params={'prefix': prefix})

        # 2. Fetch Assignments 
        # STRICT FILTER: Added LatestInterviewer CTE to explicitly isolate only true Interviewers
        sql_assign = """
        WITH LatestAssign AS (
            -- Who holds the assignment currently?
            SELECT assignment__id, responsible__name, action,
                   ROW_NUMBER() OVER(PARTITION BY assignment__id ORDER BY "date" DESC, "time" DESC) as rn
            FROM assignment__actions
            WHERE responsible__name IS NOT NULL AND TRIM(responsible__name) != ''
        ),
        LatestInterviewer AS (
            -- Who is the actual Interviewer for this assignment? (Strictly role '1'/'3')
            SELECT aa.assignment__id, aa.responsible__name,
                   ROW_NUMBER() OVER(PARTITION BY aa.assignment__id ORDER BY aa."date" DESC, aa."time" DESC) as rn
            FROM assignment__actions aa
            JOIN susouser u ON aa.responsible__name = u.login
            WHERE aa.responsible__name IS NOT NULL 
              AND TRIM(aa.responsible__name) != '' 
              AND LOWER(CAST(u.role AS VARCHAR)) IN ('interviewer', '3')
        ),
        ReassignedStats AS (
            SELECT DISTINCT aa.assignment__id 
            FROM assignment__actions aa
            JOIN susouser su ON aa.originator = su.login
            WHERE aa.action = '7' AND LOWER(su.role) = 'supervisor'
        )
        SELECT 
            a.meta_id AS assignment_id, 
            COALESCE(li.responsible__name, 'Unassigned') AS "Interviewer",
            LOWER(su.role) AS current_role,
            la.action AS latest_action,
            COALESCE(a.preload_a0::VARCHAR, '') || COALESCE(a.preload_a01::VARCHAR, '') AS "Block",
            CASE WHEN rs.assignment__id IS NOT NULL THEN 1 ELSE 0 END AS is_reassigned,
            COALESCE(p.name, 'Unknown') AS province_name,
            COALESCE(d.name, 'Unknown') AS district_name,
            COALESCE(v.name, 'Unknown') AS division_name,
            COALESCE(g.name, 'Unknown') AS gndivision_name
        FROM assignments a
        LEFT JOIN LatestAssign la ON a.meta_id::VARCHAR = la.assignment__id::VARCHAR AND la.rn = 1
        LEFT JOIN LatestInterviewer li ON a.meta_id::VARCHAR = li.assignment__id::VARCHAR AND li.rn = 1
        LEFT JOIN susouser su ON la.responsible__name = su.login
        LEFT JOIN ReassignedStats rs ON a.meta_id::VARCHAR = rs.assignment__id::VARCHAR
        LEFT JOIN province p ON SUBSTRING(su.workingarea, 1, 1) = p.code::VARCHAR
        LEFT JOIN district d ON SUBSTRING(su.workingarea, 1, 2) = d.code::VARCHAR
        LEFT JOIN division v ON SUBSTRING(su.workingarea, 1, 4) = v.code::VARCHAR
        LEFT JOIN gndivision g ON su.workingarea = g.code::VARCHAR
        WHERE (su.workingarea LIKE %(prefix)s || '%%' OR %(prefix)s = '')
        """
        df_assign = pd.read_sql(sql_assign, conn, params={'prefix': prefix})
        
        return df_users, df_assign
    finally:
        conn.close()

# -------------------------------------------------
# MAIN DASHBOARD
# -------------------------------------------------
def show_assignment_dashboard():
    st.markdown(
        """
        <h1 style='text-align: left; color: #2c3e50; font-size: 20px;'>
            📊 Assignment Monitoring Dashboard
        </h1>
        <hr style='margin-top: 0px; margin-bottom: 15px;'>
        """,
        unsafe_allow_html=True
    )

    current_login_user = st.session_state.get("login")
    if not current_login_user:
        st.warning("Please login first.")
        return

    def get_user_info(login):
        sql = "SELECT role, workingarea FROM susouser WHERE login = %(login)s LIMIT 1;"
        conn = get_connection()
        try:
            df = pd.read_sql(sql, conn, params={'login': login})
            if not df.empty:
                return str(df.iloc[0]['role']).lower().strip(), str(df.iloc[0]['workingarea']).strip()
            return None, None
        finally:
            conn.close()

    user_role, user_wa = get_user_info(current_login_user)
    
    if user_role == 'circle officer':
        if not user_wa or len(user_wa) != 7:
            st.error("⚠️ Access Denied: Circle Officer profile must have exactly a 7-character working area code.")
            return

    prefix = "" 
    if user_wa:
        if user_wa == '0000000': prefix = ''
        elif user_wa.endswith('000000'): prefix = user_wa[:1]
        elif user_wa.endswith('00000'): prefix = user_wa[:2]
        elif user_wa.endswith('000'): prefix = user_wa[:4]
        else: prefix = user_wa
    else:
        st.error("Error: Could not determine working area.")
        return

    # --- FETCH DATA ---
    with st.spinner("Calculating assignment metrics..."):
        df_users, df_assign = fetch_dashboard_data(prefix)

    df_assign['Block'] = df_assign['Block'].replace('', 'Missing Block Data')

    if df_assign.empty and df_users.empty:
        st.info("No users or assignments found for your working area.")
        return

    # ==========================================
    # CASCADING GEOGRAPHIC FILTERS
    # ==========================================
    st.markdown("<h1 style='text-align: left; color: #2c3e50; font-size: 15px;'>🔍 Filter Scope</h1>", unsafe_allow_html=True)
    
    df_a_filt = df_assign.copy()
    df_u_filt = df_users.copy()

    r1c1, r1c2, r1c3, r1c4 = st.columns(4)
    r2c1, r2c2, r2c3 = st.columns(3)

    r1c1.text_input("📍 Island", value="Sri Lanka", disabled=True, key="asm_filter_island")

    sel_prov = "All"
    if len(prefix) >= 1:
        fixed_prov = df_a_filt['province_name'].iloc[0] if not df_a_filt.empty else "N/A"
        r1c2.text_input("📍 Province", value=fixed_prov, disabled=True, key="asm_filter_prov_l")
        df_a_filt = df_a_filt[df_a_filt['province_name'] == fixed_prov]
        df_u_filt = df_u_filt[df_u_filt['province_name'] == fixed_prov]
    else:
        provs = sorted([x for x in set(df_a_filt['province_name']) if x != 'Unknown'])
        sel_prov = r1c2.selectbox("📍 Province", ["All"] + provs, key="asm_filter_prov_s")
        if sel_prov != "All":
            df_a_filt = df_a_filt[df_a_filt['province_name'] == sel_prov]
            df_u_filt = df_u_filt[df_u_filt['province_name'] == sel_prov]

    sel_dist = "All"
    if len(prefix) >= 2:
        fixed_dist = df_a_filt['district_name'].iloc[0] if not df_a_filt.empty else "N/A"
        r1c3.text_input("📍 District", value=fixed_dist, disabled=True, key="asm_filter_dist_l")
        df_a_filt = df_a_filt[df_a_filt['district_name'] == fixed_dist]
        df_u_filt = df_u_filt[df_u_filt['district_name'] == fixed_dist]
    else:
        dists = sorted([x for x in set(df_a_filt['district_name']) if x != 'Unknown'])
        sel_dist = r1c3.selectbox("📍 District", ["All"] + dists, key="asm_filter_dist_s")
        if sel_dist != "All":
            df_a_filt = df_a_filt[df_a_filt['district_name'] == sel_dist]
            df_u_filt = df_u_filt[df_u_filt['district_name'] == sel_dist]

    sel_div = "All"
    if len(prefix) >= 4:
        fixed_div = df_a_filt['division_name'].iloc[0] if not df_a_filt.empty else "N/A"
        r1c4.text_input("📍 Division", value=fixed_div, disabled=True, key="asm_filter_div_l")
        df_a_filt = df_a_filt[df_a_filt['division_name'] == fixed_div]
        df_u_filt = df_u_filt[df_u_filt['division_name'] == fixed_div]
    else:
        divs = sorted([x for x in set(df_a_filt['division_name']) if x != 'Unknown'])
        sel_div = r1c4.selectbox("📍 Division", ["All"] + divs, key="asm_filter_div_s")
        if sel_div != "All":
            df_a_filt = df_a_filt[df_a_filt['division_name'] == sel_div]
            df_u_filt = df_u_filt[df_u_filt['division_name'] == sel_div]

    sel_gn = "All"
    if len(prefix) >= 7:
        fixed_gn = df_a_filt['gndivision_name'].iloc[0] if not df_a_filt.empty else "N/A"
        r2c1.text_input("📍 GN Division", value=fixed_gn, disabled=True, key="asm_filter_gn_l")
        df_a_filt = df_a_filt[df_a_filt['gndivision_name'] == fixed_gn]
        df_u_filt = df_u_filt[df_u_filt['gndivision_name'] == fixed_gn]
    else:
        gns = sorted([x for x in set(df_a_filt['gndivision_name']) if x != 'Unknown'])
        sel_gn = r2c1.selectbox("📍 GN Division", ["All"] + gns, key="asm_filter_gn_s")
        if sel_gn != "All":
            df_a_filt = df_a_filt[df_a_filt['gndivision_name'] == sel_gn]
            df_u_filt = df_u_filt[df_u_filt['gndivision_name'] == sel_gn]

    if user_role in ['interviewer', '3']:
        sel_int = current_login_user
        r2c2.text_input("🧑‍💻 Interviewer", value=current_login_user, disabled=True, key="asm_filter_int_l")
        df_a_filt = df_a_filt[df_a_filt['Interviewer'] == sel_int]
        df_u_filt = df_u_filt[df_u_filt['login'] == sel_int]
    else:
        ints = sorted(list(set(df_a_filt['Interviewer'])))
        if "Unassigned" in ints: ints.remove("Unassigned")
        if "Unknown" in ints: ints.remove("Unknown")
        sel_int = r2c2.selectbox("🧑‍💻 Interviewer", ["All"] + ints, key="asm_filter_int_s")
        if sel_int != "All":
            df_a_filt = df_a_filt[df_a_filt['Interviewer'] == sel_int]
            df_u_filt = df_u_filt[df_u_filt['login'] == sel_int]

    blks = sorted(list(set(df_a_filt['Block'])))
    sel_blk = r2c3.selectbox("🏢 Block", ["All"] + blks, key="asm_filter_blk_s")
    if sel_blk != "All":
        df_a_filt = df_a_filt[df_a_filt['Block'] == sel_blk]

    if df_a_filt.empty:
        st.warning("No assignments match the selected filters.")
        return

    # ==========================================
    # PREPARE GROUPING & CALCULATE TOP KPIs
    # ==========================================
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

    tot_sup = len(df_u_filt[df_u_filt['role'] == 'supervisor'])
    tot_int = len(df_u_filt[df_u_filt['role'] == 'interviewer'])
    
    # Process Assignments Metrics
    df_a_filt['Assign_Sup'] = (df_a_filt['current_role'] == 'supervisor').astype(int)
    df_a_filt['Assign_Int'] = (df_a_filt['current_role'] == 'interviewer').astype(int)
    df_a_filt['Received_Int'] = ((df_a_filt['current_role'] == 'interviewer') & (df_a_filt['latest_action'] == '4')).astype(int)
    
    tot_a_sup = int(df_a_filt['Assign_Sup'].sum())
    tot_a_int = int(df_a_filt['Assign_Int'].sum())
    tot_r_int = int(df_a_filt['Received_Int'].sum())
    tot_reass = int(df_a_filt['is_reassigned'].sum())

    display_sup_count = 1 if user_role == "supervisor" else tot_sup

    # --- RENDER KPI METRICS ---
    st.markdown("<h1 style='text-align: left; color: #2c3e50; font-size: 15px;'>📊 Overview KPIs</h1>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    c1.metric("👨‍💼 Supervisors", display_sup_count)
    c2.metric("🧑‍💻 Interviewers", tot_int)
    c3.metric("📦 Assignments w/ Supervisors", tot_a_sup)

    c4, c5, c6 = st.columns(3)
    c4.metric("📤 Assigned to Interviewers", tot_a_int)
    c5.metric("📥 Received by Interviewers", tot_r_int)
    c6.metric("🔁 Reassigned Assignments", tot_reass)

    st.markdown("---")

    # ==========================================
    # AREA-WISE BREAKDOWN TABLE
    # ==========================================
    st.markdown(f"<h3 style='text-align: left; color: #2c3e50; font-size: 18px;'>📍 Geographic Breakdown: {geo_label} Level</h3>", unsafe_allow_html=True)

    # 1. Aggregate Assignments Table
    summary_assign = df_a_filt.groupby(group_col).agg(
        Assignments_Sup=("Assign_Sup", "sum"),
        Assigned_to_Int=("Assign_Int", "sum"),
        Received_by_Int=("Received_Int", "sum"),
        Reassigned=("is_reassigned", "sum")
    ).reset_index()

    # 2. Aggregate Users Table (If not at Block level)
    if group_col != 'Block':
        summary_users = df_u_filt.groupby(group_col).agg(
            Supervisors=("role", lambda x: (x == "supervisor").sum()),
            Interviewers=("role", lambda x: (x == "interviewer").sum())
        ).reset_index()
        df_result = pd.merge(summary_assign, summary_users, on=group_col, how="left").fillna(0)
    else:
        df_result = summary_assign.copy()
        df_result["Supervisors"] = 0
        df_result["Interviewers"] = 0

    df_result.rename(columns={group_col: geo_label}, inplace=True)

    cols_to_int = ["Supervisors", "Interviewers", "Assignments_Sup", "Assigned_to_Int", "Received_by_Int", "Reassigned"]
    df_result[cols_to_int] = df_result[cols_to_int].astype(int)

    df_result.rename(columns={
        "Assignments_Sup": "Assignments (Sup)",
        "Assigned_to_Int": "Assigned (Int)",
        "Received_by_Int": "Received (Int)"
    }, inplace=True)
    
    df_result = df_result[[geo_label, "Supervisors", "Interviewers", "Assignments (Sup)", "Assigned (Int)", "Received (Int)", "Reassigned"]]

    total_row = df_result.sum(numeric_only=True)
    total_row[geo_label] = f"Total (Current Selection)"
    df_display = pd.concat([df_result, pd.DataFrame([total_row])], ignore_index=True)

    def highlight_total(s):
        if s.name == len(df_display) - 1:
            return ['font-weight: bold; background-color: #f8f9fa'] * len(s)
        return [''] * len(s)

    st.dataframe(df_display.style.apply(highlight_total, axis=1), use_container_width=True, hide_index=True)

if __name__ == "__main__":
    show_assignment_dashboard()