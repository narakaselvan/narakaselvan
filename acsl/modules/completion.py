import streamlit as st
import pandas as pd
from acsl.db import get_connection

try:
    import plotly.graph_objects as go
except ImportError:
    st.error("⚠️ Plotly is not installed. Please run `pip install plotly` in your terminal.")
    st.stop()

def show_overall_completion():
    st.markdown(
        """
        <h1 style='text-align: left; color: #2c3e50; font-size: 22px;'>
            📊 Overall Completion Report
        </h1>
        <p style='color: gray; font-size: 14px;'>Track Assignment Progress, Interview Submissions, and Eligibility.</p>
        <hr style='margin-top: 0px; margin-bottom: 15px;'>
        """,
        unsafe_allow_html=True
    )

    current_login_user = st.session_state.get("login")
    if not current_login_user:
        st.warning("Please login first.")
        return

    # ==========================================
    # 1. FETCH LOGGED-IN USER INFO & AREA
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
    
    # Determine the area prefix length to lock appropriate dropdowns
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
    # 2. FETCH LEAN DATA (Filtered by Prefix)
    # ==========================================
    @st.cache_data(show_spinner=False, ttl=60)
    def fetch_completion_data(area_prefix):
        conn = get_connection()
        try:
            # --- FETCH ASSIGNMENTS ---
            sql_assign = """
            WITH LatestAssign AS (
                SELECT assignment__id, responsible__name,
                       ROW_NUMBER() OVER(PARTITION BY assignment__id ORDER BY "date" DESC, "time" DESC) as rn
                FROM assignment__actions
                WHERE responsible__name IS NOT NULL AND TRIM(responsible__name) != ''
            )
            SELECT 
                a.meta_id AS "Assignment ID",
                COALESCE(a.preload_a0::VARCHAR, '') || COALESCE(a.preload_a01::VARCHAR, '') AS "Block",
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

            # --- FETCH INTERVIEWS ---
            sql_interv = """
            WITH Diag AS (
                SELECT interview__key::VARCHAR AS int_key, 
                       MAX(interview__status::FLOAT) AS status
                FROM interview__diagnostics
                GROUP BY interview__key
            ),
            MainData AS (
                SELECT interview__key::VARCHAR AS int_key, 
                       MAX(assignment__id::VARCHAR) AS assignment_id,
                       MAX("Q1_5"::VARCHAR) AS eligible
                FROM srilanka_agcensus2025
                GROUP BY interview__key
            ),
            OriginalInterviewer AS (
                SELECT interview__key::VARCHAR AS int_key, responsible__name,
                       ROW_NUMBER() OVER(PARTITION BY interview__key ORDER BY "date" ASC, "time" ASC) as rn
                FROM interview__actions
                WHERE responsible__name IS NOT NULL AND TRIM(responsible__name) != ''
            )
            SELECT DISTINCT
                diag.int_key AS "Interview Key",
                COALESCE(a.preload_a0::VARCHAR, '') || COALESCE(a.preload_a01::VARCHAR, '') AS "Block",
                diag.status,
                m.eligible,
                COALESCE(p.name, 'Unknown') AS province_name,
                COALESCE(d_ist.name, 'Unknown') AS district_name,
                COALESCE(v.name, 'Unknown') AS division_name,
                COALESCE(g.name, 'Unknown') AS gndivision_name
            FROM Diag diag
            LEFT JOIN OriginalInterviewer oi ON diag.int_key = oi.int_key AND oi.rn = 1
            LEFT JOIN susouser su ON oi.responsible__name = su.login
            LEFT JOIN MainData m ON diag.int_key = m.int_key
            LEFT JOIN assignments a ON m.assignment_id = a.meta_id::VARCHAR
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

    with st.spinner("Fetching completion data for your working area..."):
        df_assign, df_interv = fetch_completion_data(prefix)

    df_assign['Block'] = df_assign['Block'].replace('', 'Missing Block')
    df_interv['Block'] = df_interv['Block'].replace('', 'Missing Block')
    df_interv['eligible'] = pd.to_numeric(df_interv['eligible'], errors='coerce').fillna(0)

    # ==========================================
    # 3. CASCADING GEOGRAPHIC FILTERS WITH DYNAMIC LOCKING
    # ==========================================
    st.markdown("##### 🌍 Geographic Scope Filters")
    
    df_a_filt = df_assign.copy()
    df_i_filt = df_interv.copy()

    col1, col2, col3, col4, col5, col6 = st.columns(6)

    col1.text_input("📍 Island", value="Sri Lanka", disabled=True)

    if len(prefix) >= 1:
        fixed_prov = df_a_filt['province_name'].iloc[0] if not df_a_filt.empty else (df_i_filt['province_name'].iloc[0] if not df_i_filt.empty else "N/A")
        col2.text_input("📍 Province", value=fixed_prov, disabled=True)
        df_a_filt = df_a_filt[df_a_filt['province_name'] == fixed_prov]
        df_i_filt = df_i_filt[df_i_filt['province_name'] == fixed_prov]
        sel_prov = fixed_prov
    else:
        provs = sorted([x for x in set(df_a_filt['province_name']).union(set(df_i_filt['province_name'])) if x != 'Unknown'])
        sel_prov = col2.selectbox("📍 Province", ["All"] + provs)
        if sel_prov != "All":
            df_a_filt = df_a_filt[df_a_filt['province_name'] == sel_prov]
            df_i_filt = df_i_filt[df_i_filt['province_name'] == sel_prov]

    if len(prefix) >= 2:
        fixed_dist = df_a_filt['district_name'].iloc[0] if not df_a_filt.empty else (df_i_filt['district_name'].iloc[0] if not df_i_filt.empty else "N/A")
        col3.text_input("📍 District", value=fixed_dist, disabled=True)
        df_a_filt = df_a_filt[df_a_filt['district_name'] == fixed_dist]
        df_i_filt = df_i_filt[df_i_filt['district_name'] == fixed_dist]
        sel_dist = fixed_dist
    else:
        dists = sorted([x for x in set(df_a_filt['district_name']).union(set(df_i_filt['district_name'])) if x != 'Unknown'])
        sel_dist = col3.selectbox("📍 District", ["All"] + dists)
        if sel_dist != "All":
            df_a_filt = df_a_filt[df_a_filt['district_name'] == sel_dist]
            df_i_filt = df_i_filt[df_i_filt['district_name'] == sel_dist]

    if len(prefix) >= 4:
        fixed_div = df_a_filt['division_name'].iloc[0] if not df_a_filt.empty else (df_i_filt['division_name'].iloc[0] if not df_i_filt.empty else "N/A")
        col4.text_input("📍 Division", value=fixed_div, disabled=True)
        df_a_filt = df_a_filt[df_a_filt['division_name'] == fixed_div]
        df_i_filt = df_i_filt[df_i_filt['division_name'] == fixed_div]
        sel_div = fixed_div
    else:
        divs = sorted([x for x in set(df_a_filt['division_name']).union(set(df_i_filt['division_name'])) if x != 'Unknown'])
        sel_div = col4.selectbox("📍 Division", ["All"] + divs)
        if sel_div != "All":
            df_a_filt = df_a_filt[df_a_filt['division_name'] == sel_div]
            df_i_filt = df_i_filt[df_i_filt['division_name'] == sel_div]

    if len(prefix) >= 7:
        fixed_gn = df_a_filt['gndivision_name'].iloc[0] if not df_a_filt.empty else (df_i_filt['gndivision_name'].iloc[0] if not df_i_filt.empty else "N/A")
        col5.text_input("📍 GN Division", value=fixed_gn, disabled=True)
        df_a_filt = df_a_filt[df_a_filt['gndivision_name'] == fixed_gn]
        df_i_filt = df_i_filt[df_i_filt['gndivision_name'] == fixed_gn]
        sel_gn = fixed_gn
    else:
        gns = sorted([x for x in set(df_a_filt['gndivision_name']).union(set(df_i_filt['gndivision_name'])) if x != 'Unknown'])
        sel_gn = col5.selectbox("📍 GN Division", ["All"] + gns)
        if sel_gn != "All":
            df_a_filt = df_a_filt[df_a_filt['gndivision_name'] == sel_gn]
            df_i_filt = df_i_filt[df_i_filt['gndivision_name'] == sel_gn]

    blks = sorted(list(set(df_a_filt['Block']).union(set(df_i_filt['Block']))))
    sel_blk = col6.selectbox("🏢 Block", ["All"] + blks)
    if sel_blk != "All":
        df_a_filt = df_a_filt[df_a_filt['Block'] == sel_blk]
        df_i_filt = df_i_filt[df_i_filt['Block'] == sel_blk]

    # ==========================================
    # 4. DETERMINE DYNAMIC CATEGORY FOR CHARTS (FIXED FOR HQ)
    # ==========================================
    # Explicitly checks the dropdown states to determine the correct grouping level
    if sel_blk != "All":
        group_col, geo_label = 'Block', 'Block'
    elif sel_gn != "All":
        group_col, geo_label = 'Block', 'Block'
    elif sel_div != "All":
        group_col, geo_label = 'gndivision_name', 'GN Division'
    elif sel_dist != "All":
        group_col, geo_label = 'division_name', 'Division'
    elif sel_prov != "All":
        group_col, geo_label = 'district_name', 'District'
    else:
        group_col, geo_label = 'province_name', 'Province'

    # ==========================================
    # 5. CALCULATE COMPLETION METRICS
    # ==========================================
    total_assignments = df_a_filt['Assignment ID'].nunique()
    total_interviews = df_i_filt['Interview Key'].nunique()
    
    hq_approved_interviews = df_i_filt[df_i_filt['status'] == 130]['Interview Key'].nunique()
    
    pending_collection = max(0, total_assignments - total_interviews)
    pending_hq_approval = max(0, total_assignments - hq_approved_interviews)
    
    total_eligible = df_i_filt[df_i_filt['eligible'] > 0]['Interview Key'].nunique()
    total_not_eligible = df_i_filt[df_i_filt['eligible'] <= 0]['Interview Key'].nunique()
    
    hq_approved_eligible = df_i_filt[(df_i_filt['eligible'] > 0) & (df_i_filt['status'] == 130)]['Interview Key'].nunique()
    pending_eligible = max(0, total_eligible - hq_approved_eligible)

    st.markdown("---")
    
    st.markdown("##### 📋 Summary Overview")
    m1, m2, m3 = st.columns(3)
    m1.metric(label="Total Assignments Issued", value=f"{total_assignments:,}")
    m2.metric(label="Total Interviews Received", value=f"{total_interviews:,}")
    m3.metric(label="HQ Approved (All)", value=f"{hq_approved_interviews:,}")
    
    st.write("") 
    
    m4, m5, m6 = st.columns(3)
    m4.metric(label="Agriculture Holdings", value=f"{total_eligible:,}")
    m5.metric(label="Non Agriculture Holdings", value=f"{total_not_eligible:,}")
    m6.metric(label="HQ Approved (Agriculture)", value=f"{hq_approved_eligible:,}")

    # ==========================================
    # 6. RENDER PIE CHARTS (2x2 Grid)
    # ==========================================
    st.markdown("---")
    st.markdown("### 📈 Overall Progress Breakdown")
    
    if total_assignments == 0 and total_interviews == 0:
        st.info("No data found for the selected geographic filters.")
    else:
        row1_col1, row1_col2 = st.columns(2)
        row2_col1, row2_col2 = st.columns(2)
        
        with row1_col1:
            fig1 = go.Figure(data=[go.Pie(
                labels=['Interviews Collected', 'Assignments Pending Collection'],
                values=[total_interviews, pending_collection],
                hole=0.4, 
                marker=dict(colors=['#ffc107', '#e0e0e0'], line=dict(color='#ffffff', width=2)),
                textinfo='label+percent'
            )])
            fig1.update_layout(
                title=dict(text="<b>Collection Progress</b><br><sup>Assignments vs. Interviews Received</sup>", x=0.5, font=dict(size=14)),
                margin=dict(t=50, b=20, l=10, r=10),
                legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
                height=350
            )
            st.plotly_chart(fig1, use_container_width=True)

        with row1_col2:
            fig2 = go.Figure(data=[go.Pie(
                labels=['HQ Approved', 'Not Yet Approved'],
                values=[hq_approved_interviews, pending_hq_approval],
                hole=0.4, 
                marker=dict(colors=['#28a745', '#e0e0e0'], line=dict(color='#ffffff', width=2)),
                textinfo='label+percent'
            )])
            fig2.update_layout(
                title=dict(text="<b>Overall HQ Approval</b><br><sup>Total Assignments vs. Final Approved</sup>", x=0.5, font=dict(size=14)),
                margin=dict(t=50, b=20, l=10, r=10),
                legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
                height=350
            )
            st.plotly_chart(fig2, use_container_width=True)

        with row2_col1:
            if total_eligible > 0:
                fig3 = go.Figure(data=[go.Pie(
                    labels=['HQ Approved (Agri)', 'Pending Approval (Agri)'],
                    values=[hq_approved_eligible, pending_eligible],
                    hole=0.4, 
                    marker=dict(colors=['#007bff', '#e0e0e0'], line=dict(color='#ffffff', width=2)),
                    textinfo='label+percent'
                )])
                fig3.update_layout(
                    title=dict(text="<b>Agri Holdings Progress</b><br><sup>Approved vs. Pending</sup>", x=0.5, font=dict(size=14)),
                    margin=dict(t=50, b=20, l=10, r=10),
                    legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
                    height=350
                )
                st.plotly_chart(fig3, use_container_width=True)
            else:
                st.info("No eligible holdings found in this selection.")

        with row2_col2:
            if total_interviews > 0:
                fig4 = go.Figure(data=[go.Pie(
                    labels=['Agri Holding', 'Non Agri Holding'],
                    values=[total_eligible, total_not_eligible],
                    hole=0.4, 
                    marker=dict(colors=['#17a2b8', '#dc3545'], line=dict(color='#ffffff', width=2)),
                    textinfo='label+percent'
                )])
                fig4.update_layout(
                    title=dict(text="<b>Agri Holding Comparison</b><br><sup>Agri vs. Non Agri Interviews</sup>", x=0.5, font=dict(size=14)),
                    margin=dict(t=50, b=20, l=10, r=10),
                    legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
                    height=350
                )
                st.plotly_chart(fig4, use_container_width=True)
            else:
                st.info("No interviews submitted to calculate eligibility.")

    # ==========================================
    # 7. DYNAMIC GEOGRAPHIC BAR CHART (STACKED)
    # ==========================================
    st.markdown("---")
    st.markdown(f"### 🏢 Progress by {geo_label}")
    
    if not df_a_filt.empty or not df_i_filt.empty:
        cat_assign = df_a_filt.groupby(group_col)['Assignment ID'].nunique().reset_index()
        cat_assign.rename(columns={'Assignment ID': 'Total Assignments'}, inplace=True)
        
        cat_collected = df_i_filt.groupby(group_col)['Interview Key'].nunique().reset_index()
        cat_collected.rename(columns={'Interview Key': 'Total Collected'}, inplace=True)
        
        df_i_hq = df_i_filt[df_i_filt['status'] == 130]
        cat_hq = df_i_hq.groupby(group_col)['Interview Key'].nunique().reset_index()
        cat_hq.rename(columns={'Interview Key': 'HQ Approved'}, inplace=True)
        
        df_chart = pd.merge(cat_assign, cat_collected, on=group_col, how='outer')
        df_chart = pd.merge(df_chart, cat_hq, on=group_col, how='outer').fillna(0)
        
        df_chart['HQ Approved'] = df_chart['HQ Approved'].astype(int)
        df_chart['Collected (Pending HQ)'] = (df_chart['Total Collected'] - df_chart['HQ Approved']).clip(lower=0).astype(int)
        df_chart['Pending Collection'] = (df_chart['Total Assignments'] - df_chart['Total Collected']).clip(lower=0).astype(int)
        
        df_chart.sort_values('Total Assignments', ascending=True, inplace=True)
        
        chart_height = max(400, len(df_chart) * 35)

        fig_bar = go.Figure()
        
        fig_bar.add_trace(go.Bar(
            y=df_chart[group_col],
            x=df_chart['HQ Approved'],
            name='HQ Approved',
            orientation='h',
            marker=dict(color='#28a745'), 
            hoverinfo='x+name'
        ))
        
        fig_bar.add_trace(go.Bar(
            y=df_chart[group_col],
            x=df_chart['Collected (Pending HQ)'],
            name='Collected (Pending HQ)',
            orientation='h',
            marker=dict(color='#ffc107'), 
            hoverinfo='x+name'
        ))
        
        fig_bar.add_trace(go.Bar(
            y=df_chart[group_col],
            x=df_chart['Pending Collection'],
            name='Pending Collection',
            orientation='h',
            marker=dict(color='#e0e0e0'), 
            hoverinfo='x+name'
        ))
        
        fig_bar.update_layout(
            barmode='stack', 
            xaxis_title="Number of Households",
            yaxis_title=geo_label,
            height=chart_height,
            margin=dict(t=10, b=10, l=10, r=10),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.info("No data available to display.")

if __name__ == "__main__":
    show_overall_completion()