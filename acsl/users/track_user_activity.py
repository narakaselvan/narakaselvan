import streamlit as st
import pandas as pd
from acsl.db import get_connection

def show_track_user_activity():
    
    @st.cache_data(show_spinner=False, ttl=600) 
    def fetch_activity_from_db(current_login):
        """
        Fetches activity times FOR INTERVIEWERS ONLY, applies hierarchical 
        geographic security filters based on the current user's workingarea,
        and includes District and Division names.
        """
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
                u.login,
                u.workingarea,
                d.name AS district_name,
                v.name AS division_name,
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
            WHERE originator IS NOT NULL 
              AND TRIM(originator) != '' 
              AND LOWER(originator) != 'system'
              AND CAST(role AS VARCHAR) = '1'
            
            UNION ALL
            
            SELECT "date", "time", originator
            FROM interview__actions
            WHERE originator IS NOT NULL 
              AND TRIM(originator) != '' 
              AND LOWER(originator) != 'system'
              AND CAST(role AS VARCHAR) = '1'
        )
        
        SELECT 
            c."date" AS "Date", 
            c.originator AS "Interviewer", 
            COALESCE(m.district_name, 'N/A') AS "District",
            COALESCE(m.division_name, 'N/A') AS "Division",
            m.area_name AS "Working Area",
            MIN(c."time") AS "First Activity (Login)", 
            MAX(c."time") AS "Last Activity (Logout)"
        FROM combined_actions c
        INNER JOIN mapped_users m ON c.originator = m.login
        GROUP BY c."date", c.originator, m.district_name, m.division_name, m.area_name
        ORDER BY c."date" DESC, c.originator ASC;
        """
        
        conn = None
        try:
            conn = get_connection()
            df = pd.read_sql_query(sql_query, conn, params={'current_login': current_login})
            
            if df.empty:
                return df
                
            df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m-%d')
                
            t1 = pd.to_datetime(df['Date'] + ' ' + df['First Activity (Login)'].astype(str))
            t2 = pd.to_datetime(df['Date'] + ' ' + df['Last Activity (Logout)'].astype(str))
            duration = t2 - t1
            
            df['Active Duration'] = duration.dt.components.apply(
                lambda x: f"{x.hours:02d}:{x.minutes:02d}:{x.seconds:02d}", axis=1
            )
            
            # Added District and Division to the final display ordering
            df = df[['Date', 'Interviewer', 'District', 'Division', 'Working Area', 'First Activity (Login)', 'Last Activity (Logout)', 'Active Duration']]
            return df

        except Exception as e:
            raise Exception(f"Database Error: {str(e)}")
        finally:
            if conn is not None and hasattr(conn, 'close'):
                conn.close()

    # --- UPDATED FUNCTION: Fetch Supervisor & Block using precise table joins ---
    def fetch_interviewer_details(interviewer_login, activity_date):
        """
        Bridges interview actions to assignments via the main questionnaire table 
        to extract the unique Block Numbers.
        Includes ::VARCHAR casting to prevent text = bigint comparison errors.
        """
        sql_details = """
        WITH touched_assignments AS (
            -- 1. Get assignment IDs directly from assignment actions
            SELECT assignment__id
            FROM assignment__actions
            WHERE originator = %(login)s AND "date" = %(date)s
            
            UNION
            
            -- 2. Bridge interview actions through srilanka_agcensus2025 to get assignment IDs
            SELECT s.assignment__id
            FROM interview__actions ia
            JOIN srilanka_agcensus2025 s ON ia.interview__key::VARCHAR = s.interview__key::VARCHAR
            WHERE ia.originator = %(login)s AND ia."date" = %(date)s
        ),
        blocks AS (
            -- 3. Join the resulting assignment IDs to the assignments table to get blocks
            SELECT DISTINCT COALESCE(a.preload_a0::VARCHAR, '') || COALESCE(a.preload_a01::VARCHAR, '') AS block_num
            FROM touched_assignments ta
            JOIN assignments a ON ta.assignment__id::VARCHAR = a.meta_id::VARCHAR
            WHERE a.preload_a0 IS NOT NULL OR a.preload_a01 IS NOT NULL
        )
        -- 4. Return the Supervisor name and aggregated Block numbers in a single row
        SELECT 
            (SELECT supervisor FROM susouser WHERE login = %(login)s LIMIT 1) AS supervisor_name,
            (SELECT STRING_AGG(block_num, ', ') FROM blocks) AS block_numbers;
        """
        
        conn = None
        try:
            conn = get_connection()
            df_details = pd.read_sql_query(
                sql_details, 
                conn, 
                params={'login': interviewer_login, 'date': activity_date}
            )
            
            if not df_details.empty:
                sup = df_details.iloc[0]['supervisor_name']
                blocks = df_details.iloc[0]['block_numbers']
                
                # Clean up display if nulls are returned
                sup = sup if pd.notna(sup) else "Not Assigned"
                blocks = blocks if pd.notna(blocks) else "No Blocks Found"
                
                return sup, blocks
                
            return "Not Found", "No Blocks Found"
            
        except Exception as e:
            st.error(f"Error fetching details: {e}")
            return "Error", "Error"
        finally:
            if conn is not None and hasattr(conn, 'close'):
                conn.close()
                
    # ==========================================
    # STREAMLIT UI LAYOUT
    # ==========================================
    
    st.markdown(
        """
        <h1 style='text-align: left; color: darkgreen; font-size: 20px;'>
            ⏱️ Interviewer Activity Tracker
        </h1>
        """,
        unsafe_allow_html=True
    )

    current_login_user = st.session_state.get("login")

    if not current_login_user:
        st.warning("Please login first.")
        st.stop()

    with st.spinner(f"🔄 Fetching authorized Interviewer activity data for '{current_login_user}'..."):
        try:
            df_results = fetch_activity_from_db(current_login_user)
        except Exception as e:
            st.error(f"Failed to load data: {e}")
            st.stop()

    if df_results.empty:
        st.warning(f"No Interviewer activity found for users within the geographic area assigned to '{current_login_user}'.")
        st.stop()

    # --- Filters ---
    st.markdown(
        "<span style='color:red;'>📅 Select a Date to filter (Leave empty to show all dates):</span>",
        unsafe_allow_html=True
    )
    selected_date = st.date_input(label="", value=None)

    # --- Apply Filters & Logic ---
    if selected_date:
        date_str = selected_date.strftime("%Y-%m-%d")
        df_filtered = df_results[df_results['Date'] == date_str].copy()
        
        if 'Date' in df_filtered.columns:
            df_filtered = df_filtered.drop(columns=['Date'])
    else:
        df_filtered = df_results.copy()

    # --- Display Results ---
    st.markdown(
        f"""
        <h1 style='text-align: left; color: blue; font-size: 15px;'>
            📊 Activity Report ({len(df_filtered)} records)
        </h1>
        <p style='font-size: 12px; color: red;'><i>💡 Click on any row to view the Interviewer's Supervisor and Block Number(s) for that day.</i></p>
        """,
        unsafe_allow_html=True
    )
    
    if df_filtered.empty:
        st.info("No activity found for the selected date.")
    else:
        # Render interactive dataframe
        selection_event = st.dataframe(
            df_filtered, 
            use_container_width=True, 
            hide_index=True,
            on_select="rerun",           
            selection_mode="single-row"  
        )

        # --- Check if a row was clicked ---
        selected_rows = selection_event.selection.rows
        if selected_rows:
            row_idx = selected_rows[0]
            selected_interviewer = df_filtered.iloc[row_idx]['Interviewer']
            
            # Identify the date corresponding to the clicked row
            if selected_date:
                activity_date_str = selected_date.strftime("%Y-%m-%d")
            else:
                # Reconstruct original date by filtering the original result set
                original_row = df_results[
                    (df_results['Interviewer'] == selected_interviewer) & 
                    (df_results['First Activity (Login)'] == df_filtered.iloc[row_idx]['First Activity (Login)']) &
                    (df_results['Last Activity (Logout)'] == df_filtered.iloc[row_idx]['Last Activity (Logout)'])
                ].iloc[0]
                activity_date_str = original_row['Date']
            
            # Query DB for specific details using the bridge query
            supervisor_name, block_numbers = fetch_interviewer_details(selected_interviewer, activity_date_str)
            
            # Display notification box
            st.success(
                f"👤 **Interviewer:** {selected_interviewer} &nbsp; | &nbsp; "
                f"🧑‍💼 **Supervisor:** {supervisor_name} &nbsp; | &nbsp; "
                f"🏢 **Block Number(s) for {activity_date_str}:** {block_numbers}"
            )