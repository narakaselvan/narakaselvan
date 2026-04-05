import streamlit as st
import pandas as pd
import requests
from psycopg2.extras import RealDictCursor
from acsl.db import get_connection

# ------------------------------------------------
# 1. FETCH INTERVIEWERS UNDER SUPERVISOR
# ------------------------------------------------
def fetch_interviewers_for_supervisor(supervisor):
    with get_connection() as conn:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT login
            FROM susouser
            WHERE role='interviewer'
            AND supervisor=%s
            ORDER BY login
        """, (supervisor,))
        rows = cur.fetchall()
        return [r["login"] for r in rows]

# ------------------------------------------------
# 2. FETCH ALL ASSIGNMENTS FOR SUPERVISOR (SINGLE QUERY)
# ------------------------------------------------
@st.cache_data(show_spinner=False, ttl=30)
def fetch_supervisor_assignments(me):
    """
    Fetches ALL assignments currently sitting with the logged-in supervisor.
    Extracts the Block and GN Code directly in SQL, and joins the real GN Name.
    """
    # FIXED: Removed 'm.' from gn_name in the ORDER BY clause
    sql = """
        WITH MyAssignments AS (
            SELECT 
                meta_id AS assignmentid,
                (COALESCE(preload_a0::VARCHAR, '') || COALESCE(preload_a01::VARCHAR, '')) AS block,
                SUBSTRING(COALESCE(preload_a0::VARCHAR, '') || COALESCE(preload_a01::VARCHAR, ''), 1, 7) AS gn_code,
                preload_a15 AS "L_Form_No",
                preload_b7 AS "Household Name",
                preload_b8 AS "Address"
            FROM assignments
            WHERE meta_responsiblename = %s
        )
        SELECT 
            m.*,
            COALESCE(g.name, 'Unknown GN') AS gn_name
        FROM MyAssignments m
        LEFT JOIN gndivision g ON m.gn_code = g.code::VARCHAR
        ORDER BY gn_name, m.block, m."L_Form_No"
    """
    conn = get_connection()
    try:
        return pd.read_sql(sql, conn, params=[me])
    finally:
        conn.close()

# ------------------------------------------------
# 3. UPDATE RESPONSIBLE
# ------------------------------------------------
def update_responsibles(assign_ids, interviewer):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE assignments
            SET meta_responsiblename=%s
            WHERE meta_id = ANY(%s)
        """, (interviewer, assign_ids))
        conn.commit()
        return cur.rowcount

# ------------------------------------------------
# 4. ADD TO SYNC QUEUE
# ------------------------------------------------
def queue_assignments(assign_ids, interviewer, created_by):
    with get_connection() as conn:
        cur = conn.cursor()
        for aid in assign_ids:
            cur.execute("""
                INSERT INTO sync_queue 
                (assignmentid, new_responsible, created_by, status, created_at)
                VALUES (%s, %s, %s, 'pending', now())
            """, (aid, interviewer, created_by))
        conn.commit()

# ------------------------------------------------
# CUSTOM ASSIGN UI
# ------------------------------------------------
def custom_assign(me):

    st.markdown(
        """
        <h1 style='text-align: left; color: #2c3e50; font-size: 24px;'>
            🎯 Custom Assignment by Household
        </h1>
        <p style='color: gray; font-size: 14px;'>Select an interviewer, then filter your available assignments by GN and Block to handpick specific households.</p>
        <hr style='margin-top: 0px; margin-bottom: 15px;'>
        """,
        unsafe_allow_html=True
    )

    # --- 1. SELECT INTERVIEWER ---
    interviewers = fetch_interviewers_for_supervisor(me)
    if not interviewers:
        st.warning("⚠️ No interviewers found under your supervision.")
        return

    target_interviewer = st.selectbox(
        "🧑‍💻 1. Select Interviewer", 
        ["-- Select Interviewer --"] + interviewers, 
        key="custom_assign_int"
    )

    if target_interviewer == "-- Select Interviewer --":
        st.info("👆 Please select an interviewer to begin.")
        return

    # --- 2. FETCH ALL MASTER ASSIGNMENTS ---
    with st.spinner("Fetching your unassigned households..."):
        df_master = fetch_supervisor_assignments(me)

    if df_master.empty:
        st.success("🎉 Great job! You have completely assigned all your available households. There is nothing left to assign right now.")
        return

    # --- 3. DYNAMIC GN DIVISION DROPDOWN ---
    # Extract unique GNs directly from the fetched assignments
    unique_gns = df_master[['gn_code', 'gn_name']].drop_duplicates()
    gn_options = {f"{row['gn_name']} ({row['gn_code']})": row['gn_code'] for _, row in unique_gns.iterrows()}
    
    selected_gn_label = st.selectbox(
        "📍 2. Select GN Division", 
        ["-- Select GN Division --"] + sorted(list(gn_options.keys())), 
        key="custom_assign_gn"
    )

    if selected_gn_label == "-- Select GN Division --":
        return

    selected_gn_code = gn_options[selected_gn_label]

    # --- 4. DYNAMIC BLOCK DROPDOWN ---
    # Filter master dataframe to only assignments in the selected GN
    df_gn_filtered = df_master[df_master['gn_code'] == selected_gn_code]
    
    # Extract unique Blocks from this specific GN
    available_blocks = sorted(df_gn_filtered['block'].unique().tolist())

    selected_blocks = st.multiselect(
        f"🏢 3. Select Block(s) in {selected_gn_label}", 
        available_blocks, 
        key="custom_assign_blocks"
    )

    # --- 5. LOAD AND DISPLAY ASSIGNMENTS ---
    if st.button("📥 Load Households for Selected Blocks", key="custom_assign_btn_load"):
        if not selected_blocks:
            st.warning("Please select at least one block.")
            return
            
        # Filter dataframe down to selected blocks
        df_final = df_gn_filtered[df_gn_filtered['block'].isin(selected_blocks)].copy()
        
        if df_final.empty:
            st.warning("No assignments found for the selected blocks.")
            return

        # Store the clean final dataframe in session state for selection
        display_columns = ["assignmentid", "block", "L_Form_No", "Household Name", "Address"]
        st.session_state["custom_assign_df"] = df_final[display_columns]

    # --- 6. EXECUTE ASSIGNMENT ---
    if "custom_assign_df" in st.session_state:
        st.markdown("---")
        df_display = st.session_state["custom_assign_df"]

        st.markdown(f"**🏠 Unassigned Households Found: {len(df_display)}**")
        st.caption("Click the checkboxes on the left to select which households to assign.")

        # Interactive Multi-Select DataFrame
        selected_rows_event = st.dataframe(
            df_display,
            use_container_width=True,
            hide_index=True,
            selection_mode="multi-row",
            on_select="rerun"
        )

        if hasattr(selected_rows_event, "selection") and selected_rows_event.selection.rows:
            selected_indices = selected_rows_event.selection.rows
            selected_ids = df_display.iloc[selected_indices]["assignmentid"].tolist()
            
            st.success(f"**{len(selected_ids)}** households selected for assignment.")

            if st.button(f"🚀 Assign Selected Households to {target_interviewer}", key="custom_assign_btn_exec"):
                with st.spinner("Assigning..."):
                    
                    # Update local database immediately
                    updated_count = update_responsibles(selected_ids, target_interviewer)
                    
                    # Add to HQ sync queue
                    queue_assignments(selected_ids, target_interviewer, me)

                st.success(f"✅ Successfully assigned {updated_count} households to **{target_interviewer}**! They are queued for HQ sync.")
                
                # Clear session state cache to force fresh reload
                del st.session_state["custom_assign_df"]
                st.cache_data.clear()
                
                if st.button("🔄 Refresh Application", key="custom_assign_btn_ref"):
                    st.rerun()