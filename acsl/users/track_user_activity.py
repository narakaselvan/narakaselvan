import streamlit as st
import pandas as pd
import numpy as np
import datetime
from acsl.db import get_connection

try:
    import plotly.express as px
    import plotly.graph_objects as go
except ImportError:
    st.error("⚠️ Plotly is not installed. Please run `pip install plotly` in your terminal.")
    st.stop()

def show_track_user_activity():
    
    @st.cache_data(show_spinner=False, ttl=600) 
    def fetch_activity_from_db(current_login):
        sql_query = """
        WITH current_user_area AS (
            SELECT workingarea FROM susouser WHERE login = %(current_login)s
        ),
        allowed_prefix AS (
            SELECT 
                CASE 
                    WHEN workingarea = '0000000' THEN ''
                    WHEN workingarea LIKE '_000000' THEN SUBSTRING(workingarea, 1, 1)  
                    WHEN workingarea LIKE '__00000' THEN SUBSTRING(workingarea, 1, 2)  
                    WHEN workingarea LIKE '____000' THEN SUBSTRING(workingarea, 1, 4)  
                    ELSE workingarea                                                   
                END AS prefix
            FROM current_user_area
        ),
        allowed_users AS (
            SELECT login, workingarea
            FROM susouser
            WHERE workingarea LIKE (SELECT prefix FROM allowed_prefix) || '%%'
        ),
        mapped_users AS (
            SELECT 
                u.login, u.workingarea, d.name AS district_name, v.name AS division_name,
                CASE
                    WHEN u.workingarea = '0000000' THEN 'National (All Areas)'
                    WHEN u.workingarea LIKE '_000000' THEN p.name || ' (Province)'
                    WHEN u.workingarea LIKE '__00000' THEN d.name || ' (District)'
                    WHEN u.workingarea LIKE '____000' THEN v.name || ' (Division)'
                    ELSE g.name  
                END AS area_name
            FROM allowed_users u
            LEFT JOIN province p ON SUBSTRING(u.workingarea, 1, 1) = p.code::VARCHAR
            LEFT JOIN district d ON SUBSTRING(u.workingarea, 1, 2) = d.code::VARCHAR
            LEFT JOIN division v ON SUBSTRING(u.workingarea, 1, 4) = v.code::VARCHAR
            LEFT JOIN gndivision g ON u.workingarea = g.code::VARCHAR
        ),
        combined_actions AS (
            SELECT "date", "time", originator
            FROM assignment__actions
            WHERE originator IS NOT NULL AND TRIM(originator) != '' AND LOWER(originator) != 'system' AND CAST(role AS VARCHAR) = '1'
            UNION ALL
            SELECT "date", "time", originator
            FROM interview__actions
            WHERE originator IS NOT NULL AND TRIM(originator) != '' AND LOWER(originator) != 'system' AND CAST(role AS VARCHAR) = '1'
        )
        SELECT 
            c."date" AS "Date", c.originator AS "Interviewer", 
            COALESCE(m.district_name, 'N/A') AS "District", COALESCE(m.division_name, 'N/A') AS "Division",
            m.area_name AS "Working Area", MIN(c."time") AS "First Activity (Login)", MAX(c."time") AS "Last Activity (Logout)"
        FROM combined_actions c
        INNER JOIN mapped_users m ON c.originator = m.login
        GROUP BY c."date", c.originator, m.district_name, m.division_name, m.area_name
        ORDER BY c."date" DESC, c.originator ASC;
        """
        conn = None
        try:
            conn = get_connection()
            df = pd.read_sql_query(sql_query, conn, params={'current_login': current_login})
            if df.empty: return df
            df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m-%d')
            t1 = pd.to_datetime(df['Date'] + ' ' + df['First Activity (Login)'].astype(str))
            t2 = pd.to_datetime(df['Date'] + ' ' + df['Last Activity (Logout)'].astype(str))
            df['Active Duration'] = (t2 - t1).dt.components.apply(lambda x: f"{x.hours:02d}:{x.minutes:02d}:{x.seconds:02d}", axis=1)
            return df[['Date', 'Interviewer', 'District', 'Division', 'Working Area', 'First Activity (Login)', 'Last Activity (Logout)', 'Active Duration']]
        except Exception as e:
            raise Exception(f"Database Error: {str(e)}")
        finally:
            if conn is not None and hasattr(conn, 'close'): conn.close()

    def fetch_interviewer_details(interviewer_login, activity_date):
        sql_details = """
        WITH touched_assignments AS (
            SELECT assignment__id FROM assignment__actions WHERE originator = %(login)s AND "date" = %(date)s
            UNION
            SELECT s.assignment__id FROM interview__actions ia
            JOIN srilanka_agcensus2025 s ON ia.interview__key::VARCHAR = s.interview__key::VARCHAR WHERE ia.originator = %(login)s AND ia."date" = %(date)s
        ),
        blocks AS (
            SELECT DISTINCT COALESCE(a.preload_a0::VARCHAR, '') || COALESCE(a.preload_a01::VARCHAR, '') AS block_num
            FROM touched_assignments ta JOIN assignments a ON ta.assignment__id::VARCHAR = a.meta_id::VARCHAR
            WHERE a.preload_a0 IS NOT NULL OR a.preload_a01 IS NOT NULL
        )
        SELECT (SELECT supervisor FROM susouser WHERE login = %(login)s LIMIT 1) AS supervisor_name, (SELECT STRING_AGG(block_num, ', ') FROM blocks) AS block_numbers;
        """
        conn = None
        try:
            conn = get_connection()
            df_details = pd.read_sql_query(sql_details, conn, params={'login': interviewer_login, 'date': activity_date})
            if not df_details.empty:
                sup = df_details.iloc[0]['supervisor_name']
                blocks = df_details.iloc[0]['block_numbers']
                return sup if pd.notna(sup) else "Not Assigned", blocks if pd.notna(blocks) else "No Blocks Found"
            return "Not Found", "No Blocks Found"
        except Exception: return "Error", "Error"
        finally:
            if conn is not None and hasattr(conn, 'close'): conn.close()

    @st.cache_data(show_spinner=False, ttl=60)
    def fetch_block_dashboard_data(block_number, interviewer_login):
        sql_status = """
        WITH LatestAssign AS (
            SELECT assignment__id, responsible__name, ROW_NUMBER() OVER(PARTITION BY assignment__id ORDER BY "date" DESC, "time" DESC) as rn
            FROM assignment__actions WHERE responsible__name IS NOT NULL AND TRIM(responsible__name) != ''
        ),
        InterviewerAssignments AS (
            SELECT assignment__id::VARCHAR as assign_id FROM assignment__actions WHERE originator = %(interviewer)s
            UNION
            SELECT s.assignment__id::VARCHAR as assign_id FROM interview__actions ia 
            JOIN srilanka_agcensus2025 s ON ia.interview__key::VARCHAR = s.interview__key::VARCHAR WHERE ia.originator = %(interviewer)s
        )
        SELECT 
            a.meta_id AS "Assignment ID",
            COALESCE(la.responsible__name, 'Unassigned') AS "Currently Assigned To",
            i.interview__key::VARCHAR AS "Interview Key",
            MAX(d.interview__status) AS "Status Code",
            MAX(i."Q1_5"::VARCHAR) AS "eligible",
            MAX(d.interview__duration::VARCHAR) AS "duration"
        FROM assignments a
        LEFT JOIN LatestAssign la ON a.meta_id::VARCHAR = la.assignment__id::VARCHAR AND la.rn = 1
        LEFT JOIN srilanka_agcensus2025 i ON a.meta_id::VARCHAR = i.assignment__id::VARCHAR
        LEFT JOIN interview__diagnostics d ON i.interview__key = d.interview__key
        WHERE (COALESCE(a.preload_a0::VARCHAR, '') || COALESCE(a.preload_a01::VARCHAR, '')) = %(block)s
          AND a.meta_id::VARCHAR IN (SELECT assign_id FROM InterviewerAssignments)
        GROUP BY a.meta_id, la.responsible__name, i.interview__key
        ORDER BY a.meta_id;
        """
        conn = None
        try:
            conn = get_connection()
            return pd.read_sql_query(sql_status, conn, params={'block': block_number, 'interviewer': interviewer_login})
        except Exception as e:
            st.error(f"Error fetching dashboard data: {e}")
            return pd.DataFrame()
        finally:
            if conn is not None and hasattr(conn, 'close'): conn.close()

    @st.cache_data(show_spinner=False, ttl=60)
    def fetch_timeline_data(block_number, interviewer_login):
        sql_timeline = """
        SELECT ia."date" AS activity_date, COUNT(DISTINCT ia.interview__key) as interviews_worked
        FROM interview__actions ia
        JOIN srilanka_agcensus2025 m ON ia.interview__key::VARCHAR = m.interview__key::VARCHAR
        JOIN assignments a ON m.assignment__id::VARCHAR = a.meta_id::VARCHAR
        WHERE ia.originator = %(interviewer)s
          AND (COALESCE(a.preload_a0::VARCHAR, '') || COALESCE(a.preload_a01::VARCHAR, '')) = %(block)s
        GROUP BY ia."date"
        ORDER BY ia."date" ASC;
        """
        conn = None
        try:
            conn = get_connection()
            return pd.read_sql_query(sql_timeline, conn, params={'block': block_number, 'interviewer': interviewer_login})
        except Exception: return pd.DataFrame()
        finally:
            if conn is not None and hasattr(conn, 'close'): conn.close()

    # ==========================================
    # STREAMLIT UI LAYOUT
    # ==========================================
    st.markdown("<h1 style='text-align: left; color: darkgreen; font-size: 20px;'>⏱️ Interviewer Activity Tracker</h1>", unsafe_allow_html=True)
    current_login_user = st.session_state.get("login")
    
    if not current_login_user:
        st.warning("Please login first.")
        st.stop()

    with st.spinner("🔄 Fetching authorized activity data..."):
        df_results = fetch_activity_from_db(current_login_user)

    if df_results.empty:
        st.warning("No Interviewer activity found.")
        st.stop()

    st.markdown("<span style='color:red;'>📅 Select a Date to filter:</span>", unsafe_allow_html=True)
    selected_date = st.date_input(label="", value=datetime.date.today())

    if selected_date:
        date_str = selected_date.strftime("%Y-%m-%d")
        df_filtered = df_results[df_results['Date'] == date_str].copy()
        if 'Date' in df_filtered.columns: df_filtered = df_filtered.drop(columns=['Date'])
    else:
        df_filtered = df_results.copy()

    st.markdown(f"<h1 style='text-align: left; color: blue; font-size: 15px;'>📊 Activity Report ({len(df_filtered)} records)</h1><p style='font-size: 12px; color: red;'><i>💡 Click a row to view the Interviewer's Detailed Dashboard.</i></p>", unsafe_allow_html=True)
    
    if df_filtered.empty:
        st.info("No activity found for the selected date.")
    else:
        selection_event = st.dataframe(df_filtered, use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row")

        if selection_event.selection.rows:
            row_idx = selection_event.selection.rows[0]
            selected_interviewer = df_filtered.iloc[row_idx]['Interviewer']
            activity_date_str = selected_date.strftime("%Y-%m-%d") if selected_date else df_results[
                (df_results['Interviewer'] == selected_interviewer) & 
                (df_results['First Activity (Login)'] == df_filtered.iloc[row_idx]['First Activity (Login)'])
            ].iloc[0]['Date']
            
            supervisor_name, block_numbers = fetch_interviewer_details(selected_interviewer, activity_date_str)
            st.success(f"👤 **Interviewer:** {selected_interviewer} &nbsp; | &nbsp; 🧑‍💼 **Supervisor:** {supervisor_name} &nbsp; | &nbsp; 🏢 **Blocks on {activity_date_str}:** {block_numbers}")
            
            if block_numbers and block_numbers not in ["No Blocks Found", "Error", "Not Found"]:
                blks = [b.strip() for b in block_numbers.split(",")]
                st.markdown(f"### 📋 Dashboard for {selected_interviewer}")
                selected_block = st.selectbox("Select Block to Analyze:", blks)
                
                if selected_block:
                    st.divider()
                    
                    # --- 1. TIMELINE GRAPH ---
                    df_time = fetch_timeline_data(selected_block, selected_interviewer)
                    if not df_time.empty:
                        df_time['activity_date'] = pd.to_datetime(df_time['activity_date'])
                        idx = pd.date_range(df_time['activity_date'].min(), datetime.date.today())
                        df_time = df_time.set_index('activity_date').reindex(idx, fill_value=0).reset_index()
                        df_time.rename(columns={'index': 'Date'}, inplace=True)

                        fig_line = px.line(df_time, x='Date', y='interviews_worked', markers=True, title=f"Interviews Worked On Timeline (Block {selected_block})")
                        fig_line.update_layout(yaxis_title="Number of Interviews", xaxis_title="Date", margin=dict(t=40, b=10, l=10, r=10), height=300)
                        fig_line.update_traces(line_color='#007bff')
                        st.plotly_chart(fig_line, use_container_width=True)
                    else:
                        st.info("No timeline data found for this block.")

                    # --- FETCH MAIN DASHBOARD DATA ---
                    df_data = fetch_block_dashboard_data(selected_block, selected_interviewer)
                    
                    if not df_data.empty:
                        total_assign = df_data['Assignment ID'].nunique()
                        total_interviews = df_data[df_data['Interview Key'].notna()]['Interview Key'].nunique()
                        pending_assign = max(0, total_assign - total_interviews)
                        
                        rejected_count = df_data[df_data['Status Code'] == 65]['Interview Key'].nunique()
                        accepted_pending_count = max(0, total_interviews - rejected_count)
                        
                        df_data['eligible_num'] = pd.to_numeric(df_data['eligible'], errors='coerce').fillna(0)
                        eligible_count = df_data[df_data['eligible_num'] > 0]['Interview Key'].nunique()
                        not_eligible_count = df_data[(df_data['eligible_num'] <= 0) & (df_data['Interview Key'].notna())]['Interview Key'].nunique()

                        # --- 2. PIE CHARTS (3 Columns) ---
                        st.markdown(f"##### 🥧 Block Overview (Filtered for {selected_interviewer})")
                        c1, c2, c3 = st.columns(3)

                        def create_pie(labels, values, title, colors):
                            fig = go.Figure(go.Pie(labels=labels, values=values, hole=0.4, marker=dict(colors=colors, line=dict(color='#fff', width=2)), textinfo='label+percent'))
                            fig.update_layout(title=dict(text=title, x=0.5, font=dict(size=14)), margin=dict(t=40, b=10, l=10, r=10), showlegend=False, height=250)
                            return fig

                        with c1: st.plotly_chart(create_pie(['Interviews', 'Pending Assign.'], [total_interviews, pending_assign], "Assignments vs Interviews", ['#007bff', '#e0e0e0']), use_container_width=True)
                        with c2: st.plotly_chart(create_pie(['Valid/Pending', 'Sup. Rejected'], [accepted_pending_count, rejected_count], "Interviews vs Rejections", ['#28a745', '#dc3545']), use_container_width=True)
                        with c3: st.plotly_chart(create_pie(['Eligible', 'Not Eligible'], [eligible_count, not_eligible_count], "Eligibility", ['#17a2b8', '#ffc107']), use_container_width=True)

                        # --- 3. DURATION STATISTICS TABLE ---
                        st.markdown(f"##### ⏱️ Time Taken per Questionnaire (Analyzed for {selected_interviewer} in Block {selected_block})")
                        
                        df_durations_only = df_data[df_data['Interview Key'].notna()].copy()
                        df_durations_only['Duration_td'] = pd.to_timedelta(df_durations_only['duration'], errors='coerce')
                        df_durations_only['Duration_sec'] = df_durations_only['Duration_td'].dt.total_seconds()
                        
                        valid_durations = df_durations_only['Duration_sec'].dropna()
                        v_resp = len(valid_durations)

                        def format_sec(sec):
                            if pd.isna(sec): return "N/A"
                            m, s = divmod(int(sec), 60)
                            h, m = divmod(m, 60)
                            return f"{h:02d}:{m:02d}:{s:02d}"

                        if v_resp > 0:
                            std_sec = valid_durations.std()
                            std_display = f"{std_sec:.1f}s" if pd.notna(std_sec) else "N/A (Not enough data points)"
                            
                            mode_series = valid_durations.mode()
                            mode_val = mode_series.iloc[0] if not mode_series.empty else np.nan
                            
                            stats = {
                                "Valid Interviews with Duration Logged": v_resp,
                                "Mean (Average Time)": format_sec(valid_durations.mean()),
                                "Median (Middle Time)": format_sec(valid_durations.median()),
                                "Mode (Most Frequent)": format_sec(mode_val),
                                "Standard Deviation (Sec)": std_display,
                                "Minimum Time": format_sec(valid_durations.min()),
                                "Maximum Time": format_sec(valid_durations.max())
                            }
                            st.dataframe(pd.DataFrame(list(stats.items()), columns=["Factor", "Value"]).style.set_properties(**{'text-align': 'right'}, subset=['Value']), hide_index=True, use_container_width=True)
                        else:
                            st.info("No completed interviews with recorded duration metrics available yet for this block by this interviewer.")
                            
                        # --- 4. DETAILS TABLE (FIXED STATUS MAPPING) ---
                        st.markdown("##### 📝 Detailed Record List")
                        
                        status_map = {
                            0: "Restored", 20: "Created", 40: "Sup Assigned", 60: "Int Assigned", 
                            65: "Sup Rejected", 80: "Ready", 85: "Sent to CAPI", 95: "Restarted", 
                            100: "Completed (Pending Sync)", 120: "Sup Approved", 125: "HQ Rejected", 130: "HQ Approved"
                        }
                        
                        # Safe Mapping Function
                        df_data['Status Code Numeric'] = pd.to_numeric(df_data['Status Code'], errors='coerce')
                        
                        def get_readable_status(row):
                            # 1. No Interview Key = Just an assignment
                            if pd.isna(row['Interview Key']) or row['Interview Key'] == "-" or row['Interview Key'] == "":
                                return "Assignment Only (Not Started)"
                            
                            # 2. Try to map the specific numeric Survey Solutions Code
                            code = row['Status Code Numeric']
                            if pd.notna(code):
                                code_int = int(code)
                                if code_int in status_map:
                                    return status_map[code_int]
                                else:
                                    return f"In Progress / Unknown Code ({code_int})"
                                    
                            # 3. Fallback for started interviews with missing diagnostic codes
                            return "Started (In Progress on Device)"

                        df_data['Current Status'] = df_data.apply(get_readable_status, axis=1)
                        
                        # Render Table
                        df_display = df_data[['Assignment ID', 'Interview Key', 'Current Status', 'duration']].rename(columns={'duration': 'Duration Logged'}).fillna("-")
                        st.dataframe(df_display, use_container_width=True, hide_index=True)