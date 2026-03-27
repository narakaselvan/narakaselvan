import streamlit as st
import pandas as pd
from acsl.db import get_connection

try:
    import plotly.express as px
    import plotly.graph_objects as go
except ImportError:
    st.error("⚠️ Plotly is not installed. Please run `pip install plotly` in your terminal.")
    st.stop()

def show_overall_progress():
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
    # 2. FETCH MASTER DATASET (Assignments & Interviews)
    # ==========================================
    @st.cache_data(show_spinner=False, ttl=60)
    def fetch_progress_data(area_prefix):
        conn = get_connection()
        try:
            # --- FETCH ALL ASSIGNMENTS ---
            sql_assign = """
            WITH LatestAssign AS (
                SELECT assignment__id, responsible__name,
                       ROW_NUMBER() OVER(PARTITION BY assignment__id ORDER BY "date" DESC, "time" DESC) as rn
            FROM assignment__actions
            WHERE responsible__name IS NOT NULL AND TRIM(responsible__name) != ''
            )
            SELECT 
                a.meta_id AS "Assignment ID",
                COALESCE(su.login, la.responsible__name, 'Unknown') AS "Interviewer",
                COALESCE(su.supervisor, 'Unassigned') AS "Supervisor",
                COALESCE(a.preload_a0::VARCHAR, '') || COALESCE(a.preload_a01::VARCHAR, '') AS "Block",
                su.workingarea,
                COALESCE(p.name, 'Unknown') AS province_name,
                COALESCE(d_ist.name, 'Unknown') AS district_name,
                COALESCE(v.name, 'Unknown') AS division_name,
                COALESCE(g.name, 'Unknown') AS gndivision_name
            FROM assignments a
            JOIN LatestAssign la ON a.meta_id::VARCHAR = la.assignment__id::VARCHAR AND la.rn = 1
            JOIN susouser su ON la.responsible__name = su.login
            LEFT JOIN province p ON SUBSTRING(su.workingarea, 1, 1) = p.code::VARCHAR
            LEFT JOIN district d_ist ON SUBSTRING(su.workingarea, 1, 2) = d_ist.code::VARCHAR
            LEFT JOIN division v ON SUBSTRING(su.workingarea, 1, 4) = v.code::VARCHAR
            LEFT JOIN gndivision g ON su.workingarea = g.code::VARCHAR
            WHERE (su.workingarea LIKE %(prefix)s || '%%' OR %(prefix)s = '')
            """
            df_assign = pd.read_sql(sql_assign, conn, params={'prefix': area_prefix})

            # --- FETCH ALL INTERVIEWS ---
            sql_interv = """
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
                COALESCE(m.assignment_id, 'No_Assign') AS "Assignment ID",
                COALESCE(su.login, oi.responsible__name, 'Unknown') AS "Interviewer",
                COALESCE(su.supervisor, 'Unassigned') AS "Supervisor",
                COALESCE(a.preload_a0::VARCHAR, '') || COALESCE(a.preload_a01::VARCHAR, '') AS "Block",
                diag.status,
                COALESCE(diag.unanswered, 0) AS unanswered,
                COALESCE(ec.err_count, 0) AS errors,
                CASE WHEN a.preload_a0 IS NULL AND a.preload_a01 IS NULL THEN 1 ELSE 0 END AS is_newly_identified,
                su.workingarea,
                COALESCE(p.name, 'Unknown') AS province_name,
                COALESCE(d_ist.name, 'Unknown') AS district_name,
                COALESCE(v.name, 'Unknown') AS division_name,
                COALESCE(g.name, 'Unknown') AS gndivision_name
            FROM Diag diag
            LEFT JOIN OriginalInterviewer oi ON diag.int_key = oi.int_key AND oi.rn = 1
            LEFT JOIN susouser su ON oi.responsible__name = su.login
            LEFT JOIN MainData m ON diag.int_key = m.int_key
            LEFT JOIN assignments a ON m.assignment_id = a.meta_id::VARCHAR
            LEFT JOIN ErrorCounts ec ON diag.int_key = ec.int_key
            LEFT JOIN province p ON SUBSTRING(su.workingarea, 1, 1) = p.code::VARCHAR
            LEFT JOIN district d_ist ON SUBSTRING(su.workingarea, 1, 2) = d_ist.code::VARCHAR
            LEFT JOIN division v ON SUBSTRING(su.workingarea, 1, 4) = v.code::VARCHAR
            LEFT JOIN gndivision g ON su.workingarea = g.code::VARCHAR
            WHERE (su.workingarea LIKE %(prefix)s || '%%' OR %(prefix)s = '')
            """
            df_interv = pd.read_sql(sql_interv, conn, params={'prefix': area_prefix})
            
            return df_assign, df_interv
        finally:
            conn.close()

    with st.spinner("Fetching geographic progress data..."):
        df_assign, df_interv = fetch_progress_data(prefix)

    # Clean up empty blocks
    df_assign['Block'] = df_assign['Block'].replace('', 'Missing Block Data')
    df_interv['Block'] = df_interv['Block'].replace('', 'Missing Block Data')

    # ==========================================
    # 3. CASCADING DROPDOWNS
    # ==========================================
    #st.subheader("🔍 Filter Scope")
    st.markdown(
    """
    <h1 style='text-align: left; color: #2c3e50; font-size: 15px;'>
        🔍 Filter Scope
    </h1>
    """,
    unsafe_allow_html=True
    )

    col1, col2, col3 = st.columns(3)

    # Combine lists to ensure no one is missed
    all_sups = sorted(list(set(df_assign['Supervisor'].unique()).union(set(df_interv['Supervisor'].unique()))))
    
    if user_role in ['supervisor', '2']:
        selected_supervisor = current_login_user
        col1.text_input("👤 Supervisor (Locked):", value=current_login_user, disabled=True)
    else:
        selected_supervisor = col1.selectbox("👤 Select Supervisor:", ["All"] + all_sups, key="prog_sup")

    # Filter BOTH dataframes
    df_a_sup = df_assign if selected_supervisor == "All" else df_assign[df_assign['Supervisor'] == selected_supervisor]
    df_i_sup = df_interv if selected_supervisor == "All" else df_interv[df_interv['Supervisor'] == selected_supervisor]

    all_ints = sorted(list(set(df_a_sup['Interviewer'].unique()).union(set(df_i_sup['Interviewer'].unique()))))
    selected_interviewer = col2.selectbox("🧑‍💻 Select Interviewer:", ["All"] + all_ints, key="prog_int")

    df_a_int = df_a_sup if selected_interviewer == "All" else df_a_sup[df_a_sup['Interviewer'] == selected_interviewer]
    df_i_int = df_i_sup if selected_interviewer == "All" else df_i_sup[df_i_sup['Interviewer'] == selected_interviewer]

    all_blks = sorted(list(set(df_a_int['Block'].unique()).union(set(df_i_int['Block'].unique()))))
    selected_block = col3.selectbox("🏢 Select Block:", ["All"] + all_blks, key="prog_blk")

    df_filtered_assign = df_a_int if selected_block == "All" else df_a_int[df_a_int['Block'] == selected_block]
    df_filtered_interv = df_i_int if selected_block == "All" else df_i_int[df_i_int['Block'] == selected_block]

    # ==========================================
    # 4. PREPARE GEOGRAPHIC & KPI DATA
    # ==========================================
    if user_wa == '0000000':
        group_col, geo_label, total_label = 'province_name', 'Province', 'National'
    elif user_wa.endswith('000000'):
        group_col, geo_label, total_label = 'district_name', 'District', df_filtered_assign['province_name'].iloc[0] if not df_filtered_assign.empty else 'Province'
    elif user_wa.endswith('00000'):
        group_col, geo_label, total_label = 'division_name', 'Division', df_filtered_assign['district_name'].iloc[0] if not df_filtered_assign.empty else 'District'
    else:
        group_col, geo_label, total_label = 'gndivision_name', 'GN Division', df_filtered_assign['division_name'].iloc[0] if not df_filtered_assign.empty else 'Division'

    # KPI Calculation (Using True Assignment Denominator)
    total_assignments = df_filtered_assign['Assignment ID'].nunique()
    total_interviews = df_filtered_interv['Interview Key'].nunique()
    
    safe_assign = total_assignments if total_assignments > 0 else 1
    safe_interv = total_interviews if total_interviews > 0 else 1

    pct_completion = min((total_interviews / safe_assign) * 100, 100.0) 
    
    newly_identified = df_filtered_interv[df_filtered_interv['is_newly_identified'] == 1]['Interview Key'].nunique()
    pct_newly_identified = (newly_identified / safe_assign) * 100

    sup_rejects = df_filtered_interv[df_filtered_interv['status'] == 65]['Interview Key'].nunique()
    pct_sup_rejects = (sup_rejects / safe_interv) * 100

    hq_rejects = df_filtered_interv[df_filtered_interv['status'] == 125]['Interview Key'].nunique()
    pct_hq_rejects = (hq_rejects / safe_interv) * 100

    sup_approves = df_filtered_interv[df_filtered_interv['status'] == 120]['Interview Key'].nunique()
    pct_sup_approves = (sup_approves / safe_interv) * 100

    hq_approves = df_filtered_interv[df_filtered_interv['status'] == 130]['Interview Key'].nunique()
    pct_hq_approves = (hq_approves / safe_interv) * 100

    errors_count = df_filtered_interv[df_filtered_interv['errors'] > 0]['Interview Key'].nunique()
    pct_errors = (errors_count / safe_interv) * 100

    unans_count = df_filtered_interv[df_filtered_interv['unanswered'] > 0]['Interview Key'].nunique()
    pct_unans = (unans_count / safe_interv) * 100

    # ==========================================
    # 5. RENDER DONUT CHARTS
    # ==========================================
    st.markdown(
    """
    <h1 style='text-align: left; color: #2c3e50; font-size: 15px;'>
        📊 Key Performance Indicators
    </h1>
    """,
    unsafe_allow_html=True
    )
    
    def create_donut(value, title, color):
        fig = go.Figure(go.Pie(
            values=[value, max(100 - value, 0)], 
            labels=['Metric', 'Other'], hole=0.75,
            marker_colors=[color, '#E5E5E6'], textinfo='none', hoverinfo='none'
        ))
        fig.update_layout(
            title=dict(text=title, font=dict(size=14), x=0.5, xanchor='center'),
            showlegend=False, margin=dict(t=40, b=10, l=10, r=10), height=180
        )
        fig.add_annotation(text=f"{value:.1f}%", x=0.5, y=0.5, font_size=20, showarrow=False)
        return fig

    c1, c2, c3, c4 = st.columns(4)
    with c1: st.plotly_chart(create_donut(pct_completion, "Completion (Int/Assign)", "#007bff"), use_container_width=True)
    with c2: st.plotly_chart(create_donut(pct_newly_identified, "Newly Identified", "#17a2b8"), use_container_width=True)
    with c3: st.plotly_chart(create_donut(pct_errors, "Interviews w/ Errors", "#d9534f"), use_container_width=True)
    with c4: st.plotly_chart(create_donut(pct_unans, "Unanswered Questions", "#fd7e14"), use_container_width=True)

    c5, c6, c7, c8 = st.columns(4)
    with c5: st.plotly_chart(create_donut(pct_sup_rejects, "Sup Rejected", "#d9534f"), use_container_width=True)
    with c6: st.plotly_chart(create_donut(pct_sup_approves, "Sup Approved", "#28a745"), use_container_width=True)
    with c7: st.plotly_chart(create_donut(pct_hq_rejects, "HQ Rejected", "#8b0000"), use_container_width=True)
    with c8: st.plotly_chart(create_donut(pct_hq_approves, "HQ Approved", "#218838"), use_container_width=True)

    # ==========================================
    # 6. OVERLAID BAR CHART (Assignments vs Interviews)
    # ==========================================
    st.markdown(
    f"""
    <h1 style='text-align: left; color: #2c3e50; font-size: 15px;'>
        🗺️ Geographic Progress ({geo_label} Level)
    </h1>
    """,
    unsafe_allow_html=True
    )
    
    # Calculate Data for Bar Chart
    df_bar_a = df_filtered_assign.groupby(group_col).agg(Assignments=('Assignment ID', 'nunique')).reset_index()
    df_bar_i = df_filtered_interv.groupby(group_col).agg(Interviews=('Interview Key', 'nunique')).reset_index()
    
    df_bar = pd.merge(df_bar_a, df_bar_i, on=group_col, how='outer').fillna(0)
    df_bar.rename(columns={group_col: geo_label}, inplace=True)
    df_bar.sort_values('Assignments', ascending=True, inplace=True) # Sort for aesthetics

    # Create the Overlaid Bar Chart
    fig_bar = go.Figure()
    
    # 1. Plot Assignments (The Background / Goal Bar)
    fig_bar.add_trace(go.Bar(
        y=df_bar[geo_label],
        x=df_bar['Assignments'],
        name='Total Assignments',
        orientation='h',
        marker=dict(color='#e0e0e0'), # Light Grey
        hoverinfo='x+name'
    ))
    
    # 2. Plot Interviews (The Foreground / Progress Bar)
    fig_bar.add_trace(go.Bar(
        y=df_bar[geo_label],
        x=df_bar['Interviews'],
        name='Completed Interviews',
        orientation='h',
        marker=dict(color='#007bff'), # Blue
        hoverinfo='x+name'
    ))
    
    fig_bar.update_layout(
        barmode='overlay', # THIS IS THE MAGIC THAT PUTS THEM ON THE SAME LINE!
        title="Progress: Completed Interviews vs. Total Assignments",
        xaxis_title="Count",
        yaxis_title=geo_label,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig_bar, use_container_width=True)

    # ==========================================
    # 7. SUMMARY TABLE (Color-Coded)
    # ==========================================
    tab_summary, tab_errors, tab_unanswered = st.tabs(["📑 Summary Table", "⚠️ Errors Details", "📝 Not Answered/Blank"])
    
    with tab_summary:
        df_calc = df_filtered_interv.copy()
        df_calc['Number of Interviews'] = 1
        df_calc['Sup Rejected'] = (df_calc['status'] == 65).astype(int)
        df_calc['Sup Accepted'] = (df_calc['status'] == 120).astype(int)
        df_calc['HQ Rejected'] = (df_calc['status'] == 125).astype(int)
        df_calc['HQ Accepted'] = (df_calc['status'] == 130).astype(int)
        df_calc['Unanswered/Blank'] = (df_calc['unanswered'] > 0).astype(int)

        summary_i = df_calc.groupby(group_col).agg({
            'Number of Interviews': 'sum',
            'Sup Rejected': 'sum',
            'Sup Accepted': 'sum',
            'HQ Rejected': 'sum',
            'HQ Accepted': 'sum',
            'Unanswered/Blank': 'sum'
        }).reset_index()

        summary_a = df_filtered_assign.groupby(group_col).agg({'Assignment ID': 'nunique'}).reset_index()
        summary_a.rename(columns={'Assignment ID': 'Total Assignments'}, inplace=True)

        summary = pd.merge(summary_a, summary_i, on=group_col, how='outer').fillna(0)
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
        st.dataframe(styled_summary, use_container_width=True, hide_index=True)

    with tab_errors:
        st.markdown("### Number of Errors per Interview")
        df_err_graph = df_filtered_interv[df_filtered_interv['errors'] > 0][['Interview Key', 'errors']].copy()
        if df_err_graph.empty:
            st.success("🎉 No validation errors found in the selected scope!")
        else:
            df_err_graph = df_err_graph.sort_values('errors', ascending=False).set_index('Interview Key')
            st.bar_chart(df_err_graph, color="#d9534f", y_label="Number of Errors", x_label="Interview Keys")

    with tab_unanswered:
        st.markdown("### Number of Unanswered Questions per Interview")
        df_unans_graph = df_filtered_interv[df_filtered_interv['unanswered'] > 0][['Interview Key', 'unanswered']].copy()
        if df_unans_graph.empty:
            st.success("🎉 No missing/unanswered questions found in the selected scope!")
        else:
            df_unans_graph = df_unans_graph.sort_values('unanswered', ascending=False).set_index('Interview Key')
            st.bar_chart(df_unans_graph, color="#f0ad4e", y_label="Number of Unanswered Questions", x_label="Interview Keys")