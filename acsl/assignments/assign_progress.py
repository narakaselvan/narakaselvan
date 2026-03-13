import streamlit as st
import pandas as pd
from psycopg2.extras import RealDictCursor
from acsl.db import get_connection

me= st.session_state.get("login")

# ------------------------------------------------
# DB HELPERS
# ------------------------------------------------
def fetch_interviewers_for_supervisor(supervisor):
    with get_connection() as conn:
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT login
            FROM susouser
            WHERE supervisor=%s
            ORDER BY login
        """, (supervisor,))

        return [r["login"] for r in cur.fetchall()]


def fetch_grouped_blocks_for_responsible(userid):

    with get_connection() as conn:
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT
                (preload_a0 || preload_a01) AS block,
                array_agg(meta_id) AS assignmentids
            FROM assignments
            WHERE meta_responsiblename=%s
            GROUP BY block
            ORDER BY block
        """, (userid,))

        return cur.fetchall()


def fetch_grouped_blocks_for_my_interviewers(supervisor):

    ints = fetch_interviewers_for_supervisor(supervisor)

    if not ints:
        return []

    with get_connection() as conn:
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT
                (preload_a0 || preload_a01) AS block,
                array_agg(meta_id) AS assignmentids,
                meta_responsiblename AS responsible
            FROM assignments
            WHERE meta_responsiblename = ANY(%s)
            GROUP BY block, responsible
            ORDER BY block
        """, (ints,))

        return cur.fetchall()


def update_responsibles(assign_ids, new_userid):

    with get_connection() as conn:
        cur = conn.cursor()

        cur.execute("""
            UPDATE assignments
            SET meta_responsiblename=%s
            WHERE meta_id=ANY(%s)
        """, (new_userid, assign_ids))

        conn.commit()

        return cur.rowcount


# ------------------------------------------------
# PROGRESS PAGE
# ------------------------------------------------
def show_progress(me):

    st.markdown(
    """
    <h1 style='text-align: left; color: darkgreen; font-size: 20px;'>
        My Blocks Overview
    </h1>
    """,
    unsafe_allow_html=True
    )

    blocks = fetch_grouped_blocks_for_responsible(me)

    if blocks:

        df_blocks = pd.DataFrame(blocks)
        df_blocks.columns = ["Block", "Assignment IDs"]

        df_blocks["Count"] = df_blocks["Assignment IDs"].apply(len)

        st.dataframe(
            df_blocks.style.set_properties(
                **{
                    "white-space": "normal",
                    "text-align": "left",
                    "word-wrap": "break-word"
                }
            ),
            use_container_width=True
        )

    else:
        st.info("No assignments directly assigned to you.")


    # ------------------------------------------------
    # INTERVIEWERS UNDER SUPERVISOR
    # ------------------------------------------------

    st.markdown(
    """
    <h1 style='text-align: left; color: darkgreen; font-size: 20px;'>
        Interviewers under me
    </h1>
    """,
    unsafe_allow_html=True
    )

    under_me = fetch_grouped_blocks_for_my_interviewers(me)

    if under_me:

        df_int = pd.DataFrame(under_me)
        df_int.columns = ["Block", "Assignment IDs", "Responsible"]

        df_int["Count"] = df_int["Assignment IDs"].apply(len)

        st.dataframe(
            df_int.style.set_properties(
                **{
                    "white-space": "normal",
                    "text-align": "left",
                    "word-wrap": "break-word"
                }
            ),
            use_container_width=True
        )

    else:
        st.info("No assignments under your interviewers.")

def sync_dashboard(me):
    """
    Display a summary of the sync_queue table filtered by the current login user.
    Shows status, count, and latest updated timestamp.
    """

    with get_connection() as conn:
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Fetch counts and latest update for current user
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

    # Header
    st.markdown(
        """
        <h1 style='text-align: center; color: darkgreen; font-size: 20px;'>
            📊 Queue Summary for Current User
        </h1>
        """,
        unsafe_allow_html=True
    )

    if not rows:
        st.info(f"No queue records found for user: {me}")
        return

    # Display each status with count and last updated time
    for r in rows:
        status = r["status"]
        count = r["total"]
        last_updated = r["last_updated"]

        st.markdown(f"**Status:** {status} | **Count:** {count} | **Last Updated:** {last_updated}")