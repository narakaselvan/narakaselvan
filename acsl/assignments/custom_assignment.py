import streamlit as st
import pandas as pd
from psycopg2.extras import RealDictCursor
from acsl.db import get_connection


# ------------------------------------------------
# FETCH INTERVIEWERS UNDER SUPERVISOR
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
# FETCH BLOCKS FOR LOGGED USER
# ------------------------------------------------
def fetch_blocks_for_user(me):

    with get_connection() as conn:

        cur = conn.cursor()

        cur.execute("""
            SELECT DISTINCT (preload_a0::text || preload_a01) AS block
            FROM assignments
            WHERE meta_responsiblename = %s
            ORDER BY block
        """, (me,))

        rows = cur.fetchall()

        return [r[0] for r in rows]


# ------------------------------------------------
# FETCH ASSIGNMENTS BY BLOCK IDs
# ------------------------------------------------
def fetch_assignments_by_blocks(block_ids, me):

    with get_connection() as conn:

        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT
                meta_id as assignmentid,
                preload_a15 as L_Form_No,
                preload_a3a AS gndivision,
                preload_b7 as Householdname,
                preload_b8 as address
            FROM assignments
            WHERE (preload_a0::text || preload_a01) = ANY(%s)
            AND meta_responsiblename = %s
            ORDER BY L_Form_No
        """, (block_ids, me))

        rows = cur.fetchall()

        return pd.DataFrame(rows)


# ------------------------------------------------
# UPDATE RESPONSIBLE
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
# ADD TO SYNC QUEUE
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
    <h1 style='text-align: center ; color: darkgreen; font-size: 20px;'>
        Custom Assignment by Block
    </h1>
    """,
    unsafe_allow_html=True
    )

    # --------------------------------------------
    # LOAD INTERVIEWERS
    # --------------------------------------------
    interviewers = fetch_interviewers_for_supervisor(me)

    if not interviewers:
        st.warning("No interviewers found under this supervisor")
        return

    interviewer = st.selectbox("Select Interviewer", interviewers)

    # --------------------------------------------
    # LOAD BLOCKS FOR USER
    # --------------------------------------------
    blocks_available = fetch_blocks_for_user(me)

    if not blocks_available:
        st.warning("No blocks assigned to you")
        return

    selected_blocks = st.multiselect(
        "Select Block(s)",
        blocks_available
    )

    # --------------------------------------------
    # LOAD ASSIGNMENTS
    # --------------------------------------------
    if st.button("Load Assignments"):

        if not selected_blocks:
            st.warning("Please select block(s)")
            return

        df = fetch_assignments_by_blocks(selected_blocks, me)

        if df.empty:
            st.warning("No assignments found for the selected blocks")
            return

        st.session_state["assignments_df"] = df


    # --------------------------------------------
    # DISPLAY ASSIGNMENTS
    # --------------------------------------------
    if "assignments_df" in st.session_state:

        df = st.session_state["assignments_df"]

        st.write("Assignments Found:", len(df))

        selected_rows = st.dataframe(
            df,
            use_container_width=True,
            selection_mode="multi-row",
            on_select="rerun"
        )

        # ----------------------------------------
        # GET SELECTED ROWS
        # ----------------------------------------
        if selected_rows and selected_rows["selection"]["rows"]:

            rows = selected_rows["selection"]["rows"]

            selected_ids = df.iloc[rows]["assignmentid"].tolist()

            st.write("Selected Assignment IDs:", selected_ids)

            # ------------------------------------
            # ASSIGN BUTTON
            # ------------------------------------
            if st.button("Assign Selected"):

                updated = update_responsibles(selected_ids, interviewer)

                queue_assignments(selected_ids, interviewer, me)

                st.success(f"{updated} assignments assigned to {interviewer}")