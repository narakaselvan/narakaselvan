import streamlit as st
import pandas as pd
import numpy as np
from acsl.db import get_connection

try:
    import plotly.express as px
    import plotly.figure_factory as ff
except ImportError:
    st.error("⚠️ Plotly is not installed. Please run `pip install plotly`.")
    st.stop()

# --- Helper to parse Survey Solutions Duration ---
def parse_suso_duration(duration_str):
    if pd.isna(duration_str) or duration_str == '':
        return np.nan
    duration_str = str(duration_str).strip()
    
    try:
        if '.' in duration_str and ':' in duration_str:
            parts = duration_str.split('.')
            if len(parts) == 2:
                days = parts[0]
                time_part = parts[1]
                return pd.to_timedelta(f"{days} days {time_part}").total_seconds() / 60.0
        return pd.to_timedelta(duration_str).total_seconds() / 60.0
    except:
        return np.nan

def normalize_working_area(wa):
    if str(wa) == "0":
        return "0000000"
    return str(wa).zfill(7)

def get_area_level(wa):
    wa = normalize_working_area(wa)
    if wa == "0000000": return "island"
    elif wa[1:] == "000000": return "province"
    elif wa[2:] == "00000": return "district"
    elif wa[4:] == "000": return "division"
    else: return "gn"

def show_interview_time_analysis():
    st.markdown(
        """
        <h1 style='text-align: left; color: #2c3e50; font-size: 24px;'>
            ⏱️ Interview Duration Analysis
        </h1>
        <p style='color: gray; font-size: 14px;'>Analyze how long interviews take and identify suspiciously fast (curb-stoning) or slow submissions.</p>
        <hr>
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

    user_role, user_wa_code = get_user_info(current_login_user)
    
    if user_role not in ['headquarters', 'supervisor', '4', '2', 'admin']:
        st.error(f"🚫 Access Denied: Your role ({user_role}) does not have permission to view analysis.")
        return

    prefix_for_db = "" 
    if user_wa_code:
        if user_wa_code == '0000000': prefix_for_db = ''
        elif user_wa_code.endswith('000000'): prefix_for_db = user_wa_code[:1]
        elif user_wa_code.endswith('00000'): prefix_for_db = user_wa_code[:2]
        elif user_wa_code.endswith('000'): prefix_for_db = user_wa_code[:4]
        else: prefix_for_db = user_wa_code
    else:
        st.error("Error: Could not determine working area for the current user.")
        return

    # ==========================================
    # 2. FETCH DURATION DATA (STRICT 1-TO-1)
    # ==========================================
    @st.cache_data(show_spinner=False, ttl=120)
    def fetch_duration_data(area_prefix):
        # FIXED: Compress all tables before joining to stop the 85-duplicate bug!
        sql = """
        WITH OriginalInterviewer AS (
            SELECT interview__key::VARCHAR AS int_key, responsible__name,
                   ROW_NUMBER() OVER(PARTITION BY interview__key ORDER BY "date" ASC, "time" ASC) as rn
            FROM interview__actions
            WHERE responsible__name IS NOT NULL AND TRIM(responsible__name) != ''
        ),
        Diag AS (
            SELECT interview__key::VARCHAR AS int_key, 
                   MAX(interview__duration) AS interview__duration,
                   MAX(interview__status::FLOAT) AS status
            FROM interview__diagnostics
            GROUP BY interview__key
        ),
        MainData AS (
            SELECT interview__key::VARCHAR AS int_key, MAX(assignment__id::VARCHAR) AS assignment_id
            FROM srilanka_agcensus2025
            GROUP BY interview__key
        )
        SELECT 
            diag.int_key AS "Interview Key",
            COALESCE(su.login, oi.responsible__name, 'Unknown') AS "Interviewer",
            COALESCE(su.supervisor, 'Unassigned') AS "Supervisor",
            -- FIXED: Convert empty strings to "Missing Block Data" directly in SQL
            COALESCE(NULLIF(COALESCE(a.preload_a0::VARCHAR, '') || COALESCE(a.preload_a01::VARCHAR, ''), ''), 'Missing Block Data') AS "Block",
            diag.interview__duration,
            diag.status,
            su.workingarea,
            COALESCE(p.name, 'Unknown') AS "Province",
            COALESCE(d_ist.name, 'Unknown') AS "District",
            COALESCE(v.name, 'Unknown') AS "Division",
            COALESCE(g.name, 'Unknown') AS "GN Division"
        FROM Diag diag
        LEFT JOIN OriginalInterviewer oi ON diag.int_key = oi.int_key AND oi.rn = 1
        LEFT JOIN susouser su ON oi.responsible__name = su.login
        LEFT JOIN MainData m ON diag.int_key = m.int_key
        LEFT JOIN assignments a ON m.assignment_id = a.meta_id::VARCHAR
        LEFT JOIN province p ON SUBSTRING(su.workingarea, 1, 1) = p.code::VARCHAR
        LEFT JOIN district d_ist ON SUBSTRING(su.workingarea, 1, 2) = d_ist.code::VARCHAR
        LEFT JOIN division v ON SUBSTRING(su.workingarea, 1, 4) = v.code::VARCHAR
        LEFT JOIN gndivision g ON su.workingarea = g.code::VARCHAR
        WHERE diag.status >= 100 
          AND (su.workingarea LIKE %(prefix)s || '%%' OR %(prefix)s = '')
          -- FIXED: Strictly only return true interviewers to keep Supervisors off the list!
          AND (su.role::TEXT = '1' OR LOWER(su.role::TEXT) = 'interviewer')
        """
        conn = get_connection()
        try:
            return pd.read_sql(sql, conn, params={'prefix': area_prefix})
        finally:
            conn.close()

    with st.spinner("Fetching interview durations..."):
        df_raw = fetch_duration_data(prefix_for_db)

    if df_raw.empty:
        st.info("No completed interviews found in your assigned area to analyze.")
        return

    # Clean and parse duration
    df_raw['Duration (Minutes)'] = df_raw['interview__duration'].apply(parse_suso_duration)
    df_clean = df_raw.dropna(subset=['Duration (Minutes)']).copy()
    
    if df_clean.empty:
        st.warning("No valid duration data could be parsed.")
        return

    # ==========================================
    # 3. INTERACTIVE FILTERS
    # ==========================================
    st.subheader("⚙️ Analysis Settings")
    col1, col2, col3 = st.columns(3)
    
    min_threshold = col1.number_input(
        "🚨 'Suspiciously Fast' Threshold (Minutes)", 
        min_value=1.0, max_value=60.0, value=10.0, step=1.0
    )

    current_area_level = get_area_level(user_wa_code)
    df_geo_filtered = df_clean.copy()

    with col2:
        if user_role in ['supervisor', '2']:
            selected_sup = current_login_user
            st.text_input("Supervisor (Locked)", value=selected_sup, disabled=True)
            df_geo_filtered = df_geo_filtered[df_geo_filtered['Supervisor'] == selected_sup]
        else:
            sup_list = ["All"] + sorted(df_geo_filtered['Supervisor'].unique().tolist())
            selected_sup = st.selectbox("Filter by Supervisor:", sup_list)
            if selected_sup != "All":
                df_geo_filtered = df_geo_filtered[df_geo_filtered['Supervisor'] == selected_sup]
    
    with col3:
        if current_area_level == "island":
            prov_list = ["All"] + sorted(df_geo_filtered['Province'].unique().tolist())
            selected_prov = st.selectbox("Filter by Province:", prov_list)
            if selected_prov != "All":
                df_geo_filtered = df_geo_filtered[df_geo_filtered['Province'] == selected_prov]
        elif current_area_level == "province":
            dist_list = ["All"] + sorted(df_geo_filtered['District'].unique().tolist())
            selected_dist = st.selectbox("Filter by District:", dist_list)
            if selected_dist != "All":
                df_geo_filtered = df_geo_filtered[df_geo_filtered['District'] == selected_dist]
        elif current_area_level == "district":
            div_list = ["All"] + sorted(df_geo_filtered['Division'].unique().tolist())
            selected_div = st.selectbox("Filter by Division:", div_list)
            if selected_div != "All":
                df_geo_filtered = df_geo_filtered[df_geo_filtered['Division'] == selected_div]
        elif current_area_level == "division":
            gn_list = ["All"] + sorted(df_geo_filtered['GN Division'].unique().tolist())
            selected_gn = st.selectbox("Filter by GN Division:", gn_list)
            if selected_gn != "All":
                df_geo_filtered = df_geo_filtered[df_geo_filtered['GN Division'] == selected_gn]
        else: 
            st.info("No geographic filters below your level.")

    st.markdown("---")
    col4, col5 = st.columns(2)

    with col4:
        int_list = ["All"] + sorted(df_geo_filtered['Interviewer'].unique().tolist())
        selected_int = st.selectbox("Filter by Interviewer:", int_list)
        if selected_int != "All":
            df_geo_filtered = df_geo_filtered[df_geo_filtered['Interviewer'] == selected_int]

    with col5:
        blk_list = ["All"] + sorted(df_geo_filtered['Block'].unique().tolist())
        selected_blk = st.selectbox("Filter by Block:", blk_list)
        if selected_blk != "All":
            df_geo_filtered = df_geo_filtered[df_geo_filtered['Block'] == selected_blk]

    df_filtered = df_geo_filtered.copy()

    if df_filtered.empty:
        st.info("No interviews found matching your filters.")
        return

    # ==========================================
    # 4. KPIs
    # ==========================================
    st.markdown("---")
    
    avg_dur = df_filtered['Duration (Minutes)'].mean()
    med_dur = df_filtered['Duration (Minutes)'].median()
    fast_interviews = df_filtered[df_filtered['Duration (Minutes)'] < min_threshold]
    fast_count = len(fast_interviews)
    pct_fast = (fast_count / len(df_filtered)) * 100 if len(df_filtered) > 0 else 0

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("📊 Total Analyzed", f"{len(df_filtered)}")
    k2.metric("⏱️ Average Duration", f"{avg_dur:.1f} min")
    k3.metric("🎯 Median Duration", f"{med_dur:.1f} min")
    k4.metric("🚨 Suspiciously Fast", f"{fast_count} ({pct_fast:.1f}%)", delta_color="inverse")

    # ==========================================
    # 5. VISUALIZATIONS
    # ==========================================
    st.markdown("---")
    tab1, tab2, tab3 = st.tabs(["📉 Distribution Curve", "🧑‍💻 Interviewer Comparison", "📋 Flagged Interviews"])

    with tab1:
        st.markdown("### Overall Time Distribution")
        st.caption(f"Shows the spread of interview times. The red dashed line is your threshold ({min_threshold}m).")
        
        df_filtered_for_plot = df_filtered[df_filtered['Duration (Minutes)'] <= 300].copy()
        if df_filtered_for_plot['Duration (Minutes)'].nunique() > 1:
            fig_hist = px.histogram(
                df_filtered_for_plot, x="Duration (Minutes)", nbins=50, 
                marginal="box", 
                color_discrete_sequence=['#007bff']
            )
            fig_hist.add_vline(x=min_threshold, line_dash="dash", line_color="red", annotation_text=f"Fast Threshold ({min_threshold}m)")
            st.plotly_chart(fig_hist, use_container_width=True)
        else:
            st.info("Not enough data variation to draw a distribution curve for the selected filters.")

    with tab2:
        st.markdown("### Average Duration by Interviewer")
        
        int_stats = df_filtered.groupby("Interviewer").agg(
            Avg_Duration=('Duration (Minutes)', 'mean'),
            Count=('Interview Key', 'count'),
            Fast_Count=('Duration (Minutes)', lambda x: (x < min_threshold).sum())
        ).reset_index()
        
        int_stats = int_stats.sort_values(by="Avg_Duration")

        if not int_stats.empty:
            fig_bar = px.bar(
                int_stats, x="Avg_Duration", y="Interviewer", orientation='h',
                hover_data=["Count", "Fast_Count"],
                labels={"Avg_Duration": "Average Time (Minutes)"},
                color="Fast_Count", color_continuous_scale=["#28a745", "#f0ad4e", "#d9534f"],
                title="Interviewers Ranked by Average Speed"
            )
            fig_bar.add_vline(x=min_threshold, line_dash="dash", line_color="red")
            st.plotly_chart(fig_bar, use_container_width=True)

    with tab3:
        st.markdown(f"### 🚨 Flagged Interviews (Under {min_threshold} minutes)")
        
        if fast_interviews.empty:
            st.success("No interviews completed under the threshold for the selected filters! Excellent work.")
        else:
            st.warning(f"Found {len(fast_interviews)} interview(s) that were completed suspiciously fast.")
            
            display_cols = ["Interview Key", "Interviewer", "Supervisor", "District", "Block", "Duration (Minutes)"]
            df_display = fast_interviews[display_cols].sort_values(by="Duration (Minutes)", ascending=True)
            df_display['Duration (Minutes)'] = df_display['Duration (Minutes)'].round(2)
            
            st.dataframe(df_display, use_container_width=True, hide_index=True)
            
            csv = df_display.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="⬇️ Download Flagged Interviews",
                data=csv,
                file_name=f"suspicious_interviews_under_{int(min_threshold)}m.csv",
                mime="text/csv"
            )