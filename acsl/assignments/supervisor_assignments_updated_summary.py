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

def sync_dashboard():

    with get_connection() as conn:
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Get summary for all supervisors
        cur.execute("""
            SELECT 
                q.created_by AS supervisor,
                q.status,
                COUNT(*) AS total,
                MAX(q.updated_at) AS last_updated
            FROM sync_queue q
            JOIN susouser u 
                ON q.created_by = u.login
            WHERE u.role = 'supervisor'
            GROUP BY q.created_by, q.status
            ORDER BY q.created_by, q.status
        """)

        rows = cur.fetchall()

    # Title
    st.markdown(
        """
        <h1 style='text-align: center; color: darkgreen; font-size: 20px;'>
            📊 Supervisor Queue Summary
        </h1>
        """,
        unsafe_allow_html=True
    )

    if not rows:
        st.info("No queue records found for supervisors.")
        return

    df = pd.DataFrame(rows)

    df.columns = ["Supervisor", "Status", "Count", "Last Updated"]

    st.dataframe(
        df.style.set_properties(
            **{
                "text-align": "center",
                "white-space": "nowrap"
            }
        ),
        use_container_width=True
    )