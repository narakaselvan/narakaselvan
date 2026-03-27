import streamlit as st
import pandas as pd

from acsl.db import get_connection

# IMPORTANT: Import your database connection function here
# For example: from my_database_module import get_connection
# I am setting a placeholder here so the script runs, replace it with your actual import!

def fetch_activity_from_db():
    """Fetches and aggregates user login/logout times directly from PostgreSQL."""
    
    # We use a SQL CTE (WITH clause) to combine both tables, 
    # filter out the system, and find the min/max times in one go.
    sql_query = """
    WITH combined_actions AS (
        SELECT "date", "time", originator, role
        FROM assignment__actions
        WHERE originator IS NOT NULL 
          AND TRIM(originator) != '' 
          AND LOWER(originator) != 'system'
          
        UNION ALL
        
        SELECT "date", "time", originator, role
        FROM interview__actions
        WHERE originator IS NOT NULL 
          AND TRIM(originator) != '' 
          AND LOWER(originator) != 'system'
    )
    SELECT 
        "date" AS "Date", 
        originator AS "User", 
        MAX(role) AS "Role", 
        MIN("time") AS "First Activity (Login)", 
        MAX("time") AS "Last Activity (Logout)"
    FROM combined_actions
    GROUP BY "date", originator
    ORDER BY "date" DESC, "User" ASC;
    """
    
    try:
        # Get the database connection
        conn = get_connection()
        
        # Read directly into a Pandas DataFrame
        df = pd.read_sql_query(sql_query, conn)
        
        # Calculate Active Duration
        # We temporarily convert to datetime to do the math, then format as HH:MM:SS
        t1 = pd.to_datetime(df['Date'].astype(str) + ' ' + df['First Activity (Login)'].astype(str))
        t2 = pd.to_datetime(df['Date'].astype(str) + ' ' + df['Last Activity (Logout)'].astype(str))
        
        duration = t2 - t1
        
        # Format the duration to a clean string (e.g., "08:30:00")
        df['Active Duration'] = duration.dt.components.apply(
            lambda x: f"{x.hours:02d}:{x.minutes:02d}:{x.seconds:02d}", axis=1
        )
        
        return df

    except Exception as e:
        raise Exception(f"Database Error: {str(e)}")
        
    finally:
        # Good practice to ensure the connection closes if your get_connection doesn't use a pool
        if 'conn' in locals() and hasattr(conn, 'close'):
            conn.close()


# ==========================================
# STREAMLIT UI LAYOUT
# ==========================================
st.set_page_config(page_title="SuSo User Activity Tracker", page_icon="⏱️", layout="wide")

st.title("⏱️ Survey Solutions: PostgreSQL User Activity Tracker")
st.markdown("""
This app connects directly to your **PostgreSQL Database** to analyze the `assignment__actions` and `interview__actions` tables. It calculates the first activity (Login) and last activity (Logout) for all users.
""")

if st.button("🔄 Fetch Latest Activity Data from Database", type="primary"):
    with st.spinner("Querying PostgreSQL database..."):
        try:
            df_results = fetch_activity_from_db()
            
            # Save the results to Streamlit's session state so it doesn't disappear when we use filters
            st.session_state['activity_data'] = df_results
            st.success("✅ Data fetched successfully!")
            
        except Exception as e:
            st.error(str(e))

# Display the dashboard if we have data in the session state
if 'activity_data' in st.session_state:
    df_results = st.session_state['activity_data']
    
    st.divider()
    
    # --- Filters ---
    st.subheader("🔍 Filter Results")
    col1, col2 = st.columns(2)
    
    # Date Filter
    dates_available = df_results['Date'].unique().tolist()
    selected_dates = col1.multiselect("Filter by Date:", options=dates_available, default=dates_available)
    
    # Role Filter
    roles_available = df_results['Role'].unique().tolist()
    selected_roles = col2.multiselect("Filter by Role Code:", options=roles_available, default=roles_available)
    
    # Apply Filters
    df_filtered = df_results[
        (df_results['Date'].isin(selected_dates)) & 
        (df_results['Role'].isin(selected_roles))
    ]
    
    # --- Display Results ---
    st.subheader(f"📊 Activity Report ({len(df_filtered)} records)")
    st.dataframe(df_filtered, use_container_width=True, hide_index=True)
    
    # --- Download Button ---
    csv = df_filtered.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="⬇️ Download Report as CSV",
        data=csv,
        file_name='postgres_suso_activity_report.csv',
        mime='text/csv',
    )