import streamlit as st
import pandas as pd
from psycopg2.extras import RealDictCursor
from acsl.db import get_connection

# ------------------------------------------------
# DB HELPERS FOR SYNC QUEUE
# ------------------------------------------------
def sync_dashboard(me):
    """
    Display a summary of the sync_queue table filtered by the current login user.
    Shows status, count, and latest updated timestamp.
    """
    with get_connection() as conn:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT 
                status,
                COUNT(*) AS total,
                MAX(updated_at) AS last_updated
            FROM sync_queue
            WHERE created_by = %s
            GROUP BY status
            ORDER BY status
        """, (me,))
        rows = cur.fetchall()

    st.markdown(
        """
        <h1 style='text-align: left; color: darkgreen; font-size: 20px;'>
            📊 Queue Summary for Current User
        </h1>
        """,
        unsafe_allow_html=True
    )

    if not rows:
        st.info(f"No queue records found for user: {me}")
        return

    for r in rows:
        status = r["status"]
        count = r["total"]
        last_updated = r["last_updated"]
        st.markdown(f"**Status:** {status} | **Count:** {count} | **Last Updated:** {last_updated}")


# ------------------------------------------------
# MAIN PROGRESS PAGE WITH CASCADING FILTERS
# ------------------------------------------------
# FIXED: Function now accepts 'me' as a parameter so it matches your main app route
def show_progress(me):
    st.markdown(
        """
        <h1 style='text-align: left; color: #2c3e50; font-size: 24px;'>
            📦 Blocks & Assignment Management
        </h1>
        <hr style='margin-top: 0px; margin-bottom: 15px;'>
        """,
        unsafe_allow_html=True
    )

    if not me:
        st.warning("Please login first.")
        return

    # ==========================================
    # 1. FETCH LOGGED-IN USER INFO
    # ==========================================
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

    user_role, user_wa = get_user_info(me)
    
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
        st.error("Error: Could not determine working area for the current user.")
        return

    # ==========================================
    # 2. FETCH MASTER DATASET
    # ==========================================
    @st.cache_data(show_spinner=False, ttl=60)
    def fetch_assignments_data(area_prefix):
        conn = get_connection()
        try:
            sql = """
            WITH LatestAssign AS (
                SELECT assignment__id, responsible__name,
                       ROW_NUMBER() OVER(PARTITION BY assignment__id ORDER BY "date" DESC, "time" DESC) as rn
                FROM assignment__actions
                WHERE responsible__name IS NOT NULL AND TRIM(responsible__name) != ''
            ),
            LatestInterviewer AS (
                SELECT aa.assignment__id, aa.responsible__name,
                       ROW_NUMBER() OVER(PARTITION BY aa.assignment__id ORDER BY aa."date" DESC, aa."time" DESC) as rn
                FROM assignment__actions aa
                JOIN susouser u ON aa.responsible__name = u.login
                WHERE aa.responsible__name IS NOT NULL 
                  AND TRIM(aa.responsible__name) != '' 
                  AND LOWER(CAST(u.role AS VARCHAR)) IN ('interviewer', '3')
            )
            SELECT 
                a.meta_id AS "Assignment ID",
                COALESCE(la.responsible__name, 'Unassigned') AS "Current Responsible",
                COALESCE(li.responsible__name, 'Unassigned') AS "Interviewer",
                COALESCE(a.preload_a0::VARCHAR, '') || COALESCE(a.preload_a01::VARCHAR, '') AS "Block",
                COALESCE(p.name, 'Unknown') AS province_name,
                COALESCE(d_ist.name, 'Unknown') AS district_name,
                COALESCE(v.name, 'Unknown') AS division_name,
                COALESCE(g.name, 'Unknown') AS gndivision_name
            FROM assignments a
            LEFT JOIN LatestAssign la ON a.meta_id::VARCHAR = la.assignment__id::VARCHAR AND la.rn = 1
            LEFT JOIN LatestInterviewer li ON a.meta_id::VARCHAR = li.assignment__id::VARCHAR AND li.rn = 1
            LEFT JOIN susouser su ON la.responsible__name = su.login
            LEFT JOIN province p ON SUBSTRING(su.workingarea, 1, 1) = p.code::VARCHAR
            LEFT JOIN district d_ist ON SUBSTRING(su.workingarea, 1, 2) = d_ist.code::VARCHAR
            LEFT JOIN division v ON SUBSTRING(su.workingarea, 1, 4) = v.code::VARCHAR
            LEFT JOIN gndivision g ON su.workingarea = g.code::VARCHAR
            WHERE (su.workingarea LIKE %(prefix)s || '%%' OR %(prefix)s = '')
            """
            return pd.read_sql(sql, conn, params={'prefix': area_prefix})
        finally:
            conn.close()

    with st.spinner("Fetching assignments for your area..."):
        df_assign = fetch_assignments_data(prefix)

    df_assign['Block'] = df_assign['Block'].replace('', 'Missing Block Data')

    if df_assign.empty:
        st.info("No assignments found for your working area.")
        return

    # ==========================================
    # 3. CASCADING GEOGRAPHIC FILTERS
    # ==========================================
    st.markdown("<h1 style='text-align: left; color: #2c3e50; font-size: 15px;'>🔍 Filter Scope</h1>", unsafe_allow_html=True)
    
    df_filt = df_assign.copy()

    r1c1, r1c2, r1c3, r1c4 = st.columns(4)
    r2c1, r2c2, r2c3 = st.columns(3)

    r1c1.text_input("📍 Island", value="Sri Lanka", disabled=True, key="myb_filter_isl")

    if len(prefix) >= 1:
        fixed_prov = df_filt['province_name'].iloc[0] if not df_filt.empty else "N/A"
        r1c2.text_input("📍 Province", value=fixed_prov, disabled=True, key="myb_filter_prov_l")
        df_filt = df_filt[df_filt['province_name'] == fixed_prov]
    else:
        provs = sorted([x for x in set(df_filt['province_name']) if x != 'Unknown'])
        sel_prov = r1c2.selectbox("📍 Province", ["All"] + provs, key="myb_filter_prov_s")
        if sel_prov != "All": df_filt = df_filt[df_filt['province_name'] == sel_prov]

    if len(prefix) >= 2:
        fixed_dist = df_filt['district_name'].iloc[0] if not df_filt.empty else "N/A"
        r1c3.text_input("📍 District", value=fixed_dist, disabled=True, key="myb_filter_dist_l")
        df_filt = df_filt[df_filt['district_name'] == fixed_dist]
    else:
        dists = sorted([x for x in set(df_filt['district_name']) if x != 'Unknown'])
        sel_dist = r1c3.selectbox("📍 District", ["All"] + dists, key="myb_filter_dist_s")
        if sel_dist != "All": df_filt = df_filt[df_filt['district_name'] == sel_dist]

    if len(prefix) >= 4:
        fixed_div = df_filt['division_name'].iloc[0] if not df_filt.empty else "N/A"
        r1c4.text_input("📍 Division", value=fixed_div, disabled=True, key="myb_filter_div_l")
        df_filt = df_filt[df_filt['division_name'] == fixed_div]
    else:
        divs = sorted([x for x in set(df_filt['division_name']) if x != 'Unknown'])
        sel_div = r1c4.selectbox("📍 Division", ["All"] + divs, key="myb_filter_div_s")
        if sel_div != "All": df_filt = df_filt[df_filt['division_name'] == sel_div]

    if len(prefix) >= 7:
        fixed_gn = df_filt['gndivision_name'].iloc[0] if not df_filt.empty else "N/A"
        r2c1.text_input("📍 GN Division", value=fixed_gn, disabled=True, key="myb_filter_gn_l")
        df_filt = df_filt[df_filt['gndivision_name'] == fixed_gn]
    else:
        gns = sorted([x for x in set(df_filt['gndivision_name']) if x != 'Unknown'])
        sel_gn = r2c1.selectbox("📍 GN Division", ["All"] + gns, key="myb_filter_gn_s")
        if sel_gn != "All": df_filt = df_filt[df_filt['gndivision_name'] == sel_gn]

    if user_role in ['interviewer', '3']:
        sel_int = me
        r2c2.text_input("🧑‍💻 Interviewer", value=me, disabled=True, key="myb_filter_int_l")
        df_filt = df_filt[df_filt['Interviewer'] == sel_int]
    else:
        ints = sorted(list(set(df_filt['Interviewer'])))
        if "Unassigned" in ints: ints.remove("Unassigned")
        if "Unknown" in ints: ints.remove("Unknown")
        sel_int = r2c2.selectbox("🧑‍💻 Interviewer", ["All"] + ints, key="myb_filter_int_s")
        if sel_int != "All": df_filt = df_filt[df_filt['Interviewer'] == sel_int]

    blks = sorted(list(set(df_filt['Block'])))
    sel_blk = r2c3.selectbox("🏢 Block", ["All"] + blks, key="myb_filter_blk_s")
    if sel_blk != "All": df_filt = df_filt[df_filt['Block'] == sel_blk]

    if df_filt.empty:
        st.warning("No assignments match the selected filters.")
        return

    st.markdown("---")

    # ==========================================
    # 4. MY BLOCKS OVERVIEW
    # ==========================================
    st.markdown("<h1 style='text-align: left; color: darkgreen; font-size: 20px;'>👨‍💼 My Blocks Overview</h1>", unsafe_allow_html=True)

    # Filter for assignments explicitly held by the logged-in user
    df_mine = df_filt[df_filt['Current Responsible'] == me].copy()

    if not df_mine.empty:
        # Group by Block and collect Assignment IDs into a list (same as SQL array_agg)
        my_blocks = df_mine.groupby("Block")['Assignment ID'].apply(lambda x: ', '.join(x.astype(str))).reset_index()
        my_blocks['Count'] = df_mine.groupby("Block")['Assignment ID'].count().values
        
        st.dataframe(
            my_blocks.style.set_properties(
                **{"white-space": "normal", "text-align": "left", "word-wrap": "break-word"}
            ),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No assignments currently assigned directly to you in this filtered area.")

    # ==========================================
    # 5. INTERVIEWERS UNDER ME / OTHERS
    # ==========================================
    st.markdown("<h1 style='text-align: left; color: darkgreen; font-size: 20px;'>🧑‍💻 Interviewers Overview</h1>", unsafe_allow_html=True)

    # Filter for assignments held by others (e.g., Interviewers)
    df_others = df_filt[df_filt['Current Responsible'] != me].copy()

    if not df_others.empty:
        # Group by Block and Responsible
        other_blocks = df_others.groupby(["Block", "Current Responsible"])['Assignment ID'].apply(lambda x: ', '.join(x.astype(str))).reset_index()
        other_blocks['Count'] = df_others.groupby(["Block", "Current Responsible"])['Assignment ID'].count().values
        
        other_blocks.rename(columns={"Current Responsible": "Responsible"}, inplace=True)

        st.dataframe(
            other_blocks.style.set_properties(
                **{"white-space": "normal", "text-align": "left", "word-wrap": "break-word"}
            ),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No assignments found for other interviewers in this filtered area.")

    st.markdown("---")
    
    # Run the separate sync dashboard logic at the bottom
    sync_dashboard(me)