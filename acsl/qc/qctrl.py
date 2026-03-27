import streamlit as st
import pandas as pd
from acsl.db import get_connection

def show_qctrl_progress():
    st.markdown(
        """
        <h1 style='text-align: left; color: #2c3e50; font-size: 20px;'>
            📈 Progress & Quality Dashboard
        </h1>
        """,
        unsafe_allow_html=True
    )

    current_login_user = st.session_state.get("login")
    if not current_login_user:
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

    user_role, user_wa = get_user_info(current_login_user)
    
    prefix = "" 
    if user_wa:
        if user_wa == '0000000':
            prefix = ''
        elif user_wa.endswith('000000'):
            prefix = user_wa[:1]
        elif user_wa.endswith('00000'):
            prefix = user_wa[:2]
        elif user_wa.endswith('000'):
            prefix = user_wa[:4]
        else:
            prefix = user_wa
    else:
        st.error("Error: Could not determine working area for the current user.")
        return

    # ==========================================
    # 2. FETCH MASTER DATASET (STRICTLY 1-TO-1)
    # ==========================================
    @st.cache_data(show_spinner=False, ttl=60)
    def fetch_progress_data(area_prefix):
        # FIXED: Changed Diag alias to 'diag' to prevent collision with district 'd'
        sql = """
        WITH OriginalInterviewer AS (
            SELECT interview__key::VARCHAR AS int_key, responsible__name,
                   ROW_NUMBER() OVER(PARTITION BY interview__key ORDER BY "date" ASC, "time" ASC) as rn
            FROM interview__actions
            WHERE responsible__name IS NOT NULL AND TRIM(responsible__name) != ''
        ),
        Diag AS (
            SELECT interview__key::VARCHAR AS int_key, 
                   MAX(interview__status::FLOAT) AS status,
                   MAX(n_questions_unanswered::FLOAT) AS unanswered
            FROM interview__diagnostics
            GROUP BY interview__key
        ),
        MainData AS (
            SELECT interview__key::VARCHAR AS int_key, MAX(assignment__id::VARCHAR) AS assignment_id
            FROM srilanka_agcensus2025
            GROUP BY interview__key
        ),
        ErrorCounts AS (
            SELECT interview__key::VARCHAR AS int_key, COUNT(*) as err_count
            FROM interview__errors
            GROUP BY interview__key
        )
        SELECT DISTINCT
            diag.int_key AS "Interview Key",
            COALESCE(su.login, oi.responsible__name, 'Unknown') AS "Interviewer",
            COALESCE(su.supervisor, 'Unassigned') AS "Supervisor",
            COALESCE(a.preload_a0::VARCHAR, '') || COALESCE(a.preload_a01::VARCHAR, '') AS "Block",
            diag.status,
            COALESCE(diag.unanswered, 0) AS unanswered,
            COALESCE(ec.err_count, 0) AS errors,
            su.workingarea,
            COALESCE(p.name, 'Unknown') AS province_name,
            COALESCE(d.name, 'Unknown') AS district_name,
            COALESCE(v.name, 'Unknown') AS division_name,
            COALESCE(g.name, 'Unknown') AS gndivision_name
        FROM Diag diag
        LEFT JOIN OriginalInterviewer oi ON diag.int_key = oi.int_key AND oi.rn = 1
        LEFT JOIN susouser su ON oi.responsible__name = su.login
        LEFT JOIN MainData m ON diag.int_key = m.int_key
        LEFT JOIN assignments a ON m.assignment_id = a.meta_id::VARCHAR
        LEFT JOIN ErrorCounts ec ON diag.int_key = ec.int_key
        LEFT JOIN province p ON SUBSTRING(su.workingarea, 1, 1) = p.code::VARCHAR
        LEFT JOIN district d ON SUBSTRING(su.workingarea, 1, 2) = d.code::VARCHAR
        LEFT JOIN division v ON SUBSTRING(su.workingarea, 1, 4) = v.code::VARCHAR
        LEFT JOIN gndivision g ON su.workingarea = g.code::VARCHAR
        WHERE (su.workingarea LIKE %(prefix)s || '%%' OR %(prefix)s = '')
        """
        conn = get_connection()
        try:
            return pd.read_sql(sql, conn, params={'prefix': area_prefix})
        finally:
            conn.close()

    with st.spinner("Fetching geographic progress data..."):
        df_master = fetch_progress_data(prefix)

    df_master['Block'] = df_master['Block'].replace('', 'Missing Block Data')

    if df_master.empty:
        st.info("No interview data found for your working area.")
        return

    # ==========================================
    # 3. CASCADING DROPDOWNS
    # ==========================================
    st.markdown(
        """
        <h1 style='text-align: left; color: darkgreen; font-size: 15px;'>
            🔍 Filter Scope
        </h1>
        """,
        unsafe_allow_html=True
    )

    col1, col2, col3 = st.columns(3)

    if user_role in ['supervisor', '2']:
        selected_supervisor = current_login_user
        col1.text_input("👤 Supervisor (Locked):", value=current_login_user, disabled=True)
    else:
        sup_list = ["All"] + sorted(df_master['Supervisor'].unique().tolist())
        selected_supervisor = col1.selectbox("👤 Select Supervisor:", sup_list, key="prog_sup")

    df_sup_filtered = df_master if selected_supervisor == "All" else df_master[df_master['Supervisor'] == selected_supervisor]

    int_list = ["All"] + sorted(df_sup_filtered['Interviewer'].unique().tolist())
    selected_interviewer = col2.selectbox("🧑‍💻 Select Interviewer:", int_list, key="prog_int")

    df_int_filtered = df_sup_filtered if selected_interviewer == "All" else df_sup_filtered[df_sup_filtered['Interviewer'] == selected_interviewer]

    blk_list = ["All"] + sorted(df_int_filtered['Block'].unique().tolist())
    selected_block = col3.selectbox("🏢 Select Block:", blk_list, key="prog_blk")

    df_filtered = df_int_filtered if selected_block == "All" else df_int_filtered[df_int_filtered['Block'] == selected_block]

    if df_filtered.empty:
        st.warning("No data matches the selected filters.")
        return

    #st.markdown("---")

    # ==========================================
    # 4. TABS SETUP
    # ==========================================
    tab_summary, tab_errors, tab_unanswered = st.tabs(["📊 Summary Table", "⚠️ Errors Details", "📝 Not Answered/Blank"])

    # ==========================================
    # TAB 1: SUMMARY TABLE
    # ==========================================
    with tab_summary:
        if user_wa == '0000000':
            group_col = 'province_name'
            geo_label = 'Province'
            total_label = 'National'
        elif user_wa.endswith('000000'):
            group_col = 'district_name'
            geo_label = 'District'
            total_label = df_filtered['province_name'].iloc[0] if not df_filtered.empty else 'Province'
        elif user_wa.endswith('00000'):
            group_col = 'division_name'
            geo_label = 'Division'
            total_label = df_filtered['district_name'].iloc[0] if not df_filtered.empty else 'District'
        elif user_wa.endswith('000'):
            group_col = 'gndivision_name'
            geo_label = 'GN Division'
            total_label = df_filtered['division_name'].iloc[0] if not df_filtered.empty else 'Division'
        else:
            group_col = 'gndivision_name'
            geo_label = 'GN Division'
            total_label = df_filtered['gndivision_name'].iloc[0] if not df_filtered.empty else 'GN'

        df_calc = df_filtered.copy()
        df_calc['Number of Interviews'] = 1
        df_calc['Sup Rejected'] = (df_calc['status'] == 65).astype(int)
        df_calc['Sup Accepted'] = (df_calc['status'] == 120).astype(int)
        df_calc['HQ Rejected'] = (df_calc['status'] == 125).astype(int)
        df_calc['HQ Accepted'] = (df_calc['status'] == 130).astype(int)
        df_calc['Unanswered/Blank'] = (df_calc['unanswered'] > 0).astype(int)

        summary = df_calc.groupby(group_col).agg({
            'Number of Interviews': 'sum',
            'Sup Rejected': 'sum',
            'Sup Accepted': 'sum',
            'HQ Rejected': 'sum',
            'HQ Accepted': 'sum',
            'Unanswered/Blank': 'sum'
        }).reset_index()

        summary.rename(columns={group_col: geo_label}, inplace=True)

        total_row = summary.sum(numeric_only=True)
        total_row[geo_label] = f"Total ({total_label})"
        summary = pd.concat([summary, pd.DataFrame([total_row])], ignore_index=True)

        def highlight_columns(s):
            is_total_row = (s.name == len(summary) - 1) 
            style = ['font-weight: bold' if is_total_row else ''] * len(s)
            
            if s.name in ['Sup Rejected', 'HQ Rejected', 'Unanswered/Blank']:
                style = ['color: red; font-weight: bold' if is_total_row else 'color: red' for _ in s]
            elif s.name in ['Sup Accepted', 'HQ Accepted']:
                style = ['color: green; font-weight: bold' if is_total_row else 'color: green' for _ in s]
            return style

        styled_summary = summary.style.apply(highlight_columns, axis=0)
        
        st.markdown(f"**Geographic Scope: {geo_label} Level**")
        st.dataframe(styled_summary, use_container_width=True, hide_index=True)

    # ==========================================
    # TAB 2: ERRORS GRAPH
    # ==========================================
    with tab_errors:
        st.markdown("### Number of Errors per Interview")
        df_err_graph = df_filtered[df_filtered['errors'] > 0][['Interview Key', 'errors']].copy()
        if df_err_graph.empty:
            st.success("🎉 No validation errors found in the selected scope!")
        else:
            df_err_graph = df_err_graph.sort_values('errors', ascending=False).set_index('Interview Key')
            st.bar_chart(df_err_graph, color="#d9534f", y_label="Number of Errors", x_label="Interview Keys")

    # ==========================================
    # TAB 3: UNANSWERED GRAPH
    # ==========================================
    with tab_unanswered:
        st.markdown("### Number of Unanswered Questions per Interview")
        df_unans_graph = df_filtered[df_filtered['unanswered'] > 0][['Interview Key', 'unanswered']].copy()
        if df_unans_graph.empty:
            st.success("🎉 No missing/unanswered questions found in the selected scope!")
        else:
            df_unans_graph = df_unans_graph.sort_values('unanswered', ascending=False).set_index('Interview Key')
            st.bar_chart(df_unans_graph, color="#f0ad4e", y_label="Number of Unanswered Questions", x_label="Interview Keys")